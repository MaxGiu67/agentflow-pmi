"""Webhook receivers A-Cube Open Banking (Pivot 11 US-OB-05).

Pattern "fast return":
1. Verifica firma (constant-time HMAC)
2. Parsing + idempotency (UNIQUE su webhook_events)
3. Risposta 200 entro < 500ms
4. Processing asincrono via FastAPI BackgroundTasks

Tre eventi: Connect, Reconnect, Payment.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from api.db.models import WebhookEvent
from api.db.session import get_db
from api.modules.banking.acube_ob_processors import (
    process_connect_event,
    process_payment_event,
    process_reconnect_event,
)
from api.security.webhook_signature import (
    InvalidSignatureError,
    ReplayAttackError,
    SignatureConfig,
    verify_signature,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks/acube", tags=["webhooks-acube"])

SOURCE = "acube_ob"
MAX_BODY_BYTES = 1 * 1024 * 1024  # 1MB


def _build_signature_config() -> SignatureConfig:
    """Costruisce config firma dai settings (parametrizzabili via env)."""
    return SignatureConfig(
        header_name=settings.acube_ob_webhook_signature_header,
        secret=settings.acube_ob_webhook_secret,
        algorithm=settings.acube_ob_webhook_signature_algo,
        prefix=settings.acube_ob_webhook_signature_prefix,
        max_age_seconds=None,  # timestamp header non confermato da A-Cube
    )


async def _verify_and_parse(request: Request) -> tuple[bytes, dict[str, Any], bool]:
    """Legge body raw, verifica firma (se abilitata), ritorna (body, parsed_json, signature_verified).

    La firma può essere disabilitata via env flag `ACUBE_OB_WEBHOOK_VERIFY_SIGNATURE=false`
    per sviluppo sandbox — in produzione sempre abilitata.
    """
    body = await request.body()

    if len(body) > MAX_BODY_BYTES:
        raise InvalidSignatureError(f"Body troppo grande: {len(body)} bytes")

    signature_verified = False
    if settings.acube_ob_webhook_verify_signature:
        config = _build_signature_config()
        received_sig = request.headers.get(config.header_name)
        try:
            verify_signature(body, received_sig, config)
            signature_verified = True
        except (InvalidSignatureError, ReplayAttackError):
            raise
    else:
        logger.warning(
            "⚠️  Webhook signature verification DISABLED — dev/sandbox mode only. "
            "Set ACUBE_OB_WEBHOOK_VERIFY_SIGNATURE=true in production."
        )

    try:
        parsed = json.loads(body.decode("utf-8")) if body else {}
    except json.JSONDecodeError as e:
        raise InvalidSignatureError(f"Payload non JSON: {e}")

    return body, parsed, signature_verified


def _compute_external_id(payload: dict[str, Any], body: bytes) -> str:
    """External ID per idempotency.

    A-Cube docs non documentano un event_id nativo → usiamo hash deterministico del body.
    Se in futuro A-Cube espone un event_id, lo useremo direttamente.
    """
    # Possibili campi futuri: payload.get('eventId'), payload.get('uuid')
    if (eid := payload.get("eventId") or payload.get("uuid")):
        return str(eid)
    return hashlib.sha256(body).hexdigest()[:32]


async def _persist_event(
    db: AsyncSession,
    *,
    event_type: str,
    payload: dict[str, Any],
    body: bytes,
    signature: str | None,
    signature_verified: bool,
) -> tuple[WebhookEvent, bool]:
    """Persiste WebhookEvent. Ritorna (event, is_duplicate).

    Idempotency via UNIQUE(source, event_type, external_id).
    """
    external_id = _compute_external_id(payload, body)
    event = WebhookEvent(
        source=SOURCE,
        event_type=event_type,
        external_id=external_id,
        fiscal_id=payload.get("fiscalId"),
        payload=payload,
        signature=signature,
        signature_verified=signature_verified,
    )
    db.add(event)
    try:
        await db.commit()
        await db.refresh(event)
        return event, False
    except IntegrityError:
        await db.rollback()
        # recupera l'evento esistente
        from sqlalchemy import select
        result = await db.execute(
            select(WebhookEvent).where(
                WebhookEvent.source == SOURCE,
                WebhookEvent.event_type == event_type,
                WebhookEvent.external_id == external_id,
            )
        )
        existing = result.scalar_one()
        return existing, True


# ── Endpoint Connect ───────────────────────────────────────

@router.post("/connect")
async def webhook_connect(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Evento: consenso PSD2 stabilito o fallito."""
    return await _handle_webhook(request, background_tasks, db, "connect", process_connect_event)


@router.post("/reconnect")
async def webhook_reconnect(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Evento: consenso PSD2 in scadenza (notice level 0/1/2)."""
    return await _handle_webhook(request, background_tasks, db, "reconnect", process_reconnect_event)


@router.post("/payment")
async def webhook_payment(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Evento: stato pagamento (PISP — placeholder)."""
    return await _handle_webhook(request, background_tasks, db, "payment", process_payment_event)


async def _handle_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession,
    event_type: str,
    processor,
) -> dict[str, str]:
    """Handler comune: verify → persist → enqueue → 200 OK."""
    try:
        body, payload, sig_verified = await _verify_and_parse(request)
    except (InvalidSignatureError, ReplayAttackError) as exc:
        logger.warning("Webhook %s rejected: %s", event_type, exc)
        return Response(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=json.dumps({"error": str(exc)}),
            media_type="application/json",
        )

    signature_header = request.headers.get(settings.acube_ob_webhook_signature_header)
    event, is_duplicate = await _persist_event(
        db,
        event_type=event_type,
        payload=payload,
        body=body,
        signature=signature_header,
        signature_verified=sig_verified,
    )

    if is_duplicate:
        logger.info("Webhook %s duplicato (external_id=%s) — ignored", event_type, event.external_id)
        return {"status": "duplicate_ignored", "event_id": str(event.id)}

    # Background processing (non blocca risposta)
    background_tasks.add_task(_run_processor, processor, event.id)

    return {"status": "accepted", "event_id": str(event.id)}


async def _run_processor(processor, event_id: uuid.UUID) -> None:
    """Esegue processor in background con DB session dedicata."""
    from api.db.session import async_session_factory
    async with async_session_factory() as db:
        try:
            await processor(db, event_id)
        except Exception:  # noqa: BLE001
            logger.exception("Processor %s failed for event %s", processor.__name__, event_id)
