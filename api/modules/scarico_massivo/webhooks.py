"""Webhook receivers A-Cube Cassetto Fiscale (Scarico Massivo).

A-Cube notifica nuove fatture scaricate — riusa lo stesso pattern dei webhook
Open Banking: verify HMAC → persist evento → background processor.

Eventi attesi (da Antonio 2026-04-27 + docs):
- invoice-downloaded: nuova fattura disponibile per una P.IVA
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from api.db.models import ScaricoMassivoConfig, WebhookEvent
from api.db.session import get_db
from api.security.webhook_signature import (
    InvalidSignatureError,
    ReplayAttackError,
    SignatureConfig,
    verify_signature,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks/acube/cassetto-fiscale", tags=["webhooks-acube-cf"])

SOURCE = "acube_cassetto_fiscale"
MAX_BODY_BYTES = 1 * 1024 * 1024


def _build_signature_config() -> SignatureConfig:
    return SignatureConfig(
        header_name=settings.acube_ob_webhook_signature_header,
        secret=settings.acube_ob_webhook_secret,
        algorithm=settings.acube_ob_webhook_signature_algo,
        prefix=settings.acube_ob_webhook_signature_prefix,
        max_age_seconds=None,
    )


async def _verify_and_parse(request: Request) -> tuple[bytes, dict[str, Any], bool]:
    body = await request.body()
    if len(body) > MAX_BODY_BYTES:
        raise InvalidSignatureError(f"Body troppo grande: {len(body)} bytes")

    signature_verified = False
    if settings.acube_ob_webhook_verify_signature:
        cfg = _build_signature_config()
        received = request.headers.get(cfg.header_name)
        verify_signature(body, received, cfg)
        signature_verified = True
    else:
        logger.warning(
            "⚠️  Webhook cassetto-fiscale signature DISABLED — sandbox/dev only."
        )

    try:
        parsed = json.loads(body.decode("utf-8")) if body else {}
    except json.JSONDecodeError as e:
        raise InvalidSignatureError(f"Payload non JSON: {e}") from e

    return body, parsed, signature_verified


def _compute_external_id(payload: dict[str, Any], body: bytes) -> str:
    if (eid := payload.get("eventId") or payload.get("uuid") or payload.get("id")):
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
    external_id = _compute_external_id(payload, body)
    fiscal_id = payload.get("fiscal_id") or payload.get("fiscalId")
    event = WebhookEvent(
        source=SOURCE,
        event_type=event_type,
        external_id=external_id,
        fiscal_id=fiscal_id,
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
        existing = await db.execute(
            select(WebhookEvent).where(
                WebhookEvent.source == SOURCE,
                WebhookEvent.event_type == event_type,
                WebhookEvent.external_id == external_id,
            )
        )
        return existing.scalar_one(), True


@router.post("/invoice-downloaded", response_model=None)
async def webhook_invoice_downloaded(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str] | Response:
    """A-Cube notifica nuova fattura scaricata per una P.IVA cliente."""
    try:
        body, payload, sig_verified = await _verify_and_parse(request)
    except (InvalidSignatureError, ReplayAttackError) as exc:
        logger.warning("Webhook cassetto-fiscale rejected: %s", exc)
        return Response(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=json.dumps({"error": str(exc)}),
            media_type="application/json",
        )

    sig_header = request.headers.get(settings.acube_ob_webhook_signature_header)
    event, is_duplicate = await _persist_event(
        db,
        event_type="invoice-downloaded",
        payload=payload,
        body=body,
        signature=sig_header,
        signature_verified=sig_verified,
    )

    if is_duplicate:
        logger.info(
            "Webhook cassetto-fiscale duplicato (external_id=%s)", event.external_id
        )
        return {"status": "duplicate_ignored", "event_id": str(event.id)}

    background_tasks.add_task(_process_invoice_downloaded, event.id)
    return {"status": "accepted", "event_id": str(event.id)}


async def _process_invoice_downloaded(event_id: uuid.UUID) -> None:
    """Background processor: trigger sync per la P.IVA notificata.

    Mantiene la logica di download centralizzata nel service.sync_now() —
    il webhook è solo un trigger event-driven (no polling).
    """
    from api.db.session import async_session_factory
    from api.modules.scarico_massivo.service import (
        ScaricoMassivoService,
        ScaricoMassivoServiceError,
    )

    async with async_session_factory() as db:
        try:
            ev = await db.get(WebhookEvent, event_id)
            if not ev:
                logger.error("WebhookEvent %s sparito prima del processing", event_id)
                return

            fiscal_id = ev.fiscal_id or (ev.payload or {}).get("fiscal_id")
            if not fiscal_id:
                logger.warning("Webhook %s senza fiscal_id — skip", event_id)
                return

            cfg_res = await db.execute(
                select(ScaricoMassivoConfig).where(
                    ScaricoMassivoConfig.client_fiscal_id == fiscal_id
                )
            )
            configs = list(cfg_res.scalars().all())
            if not configs:
                logger.info(
                    "Webhook fiscal_id=%s ricevuto ma nessuna config attiva — ignore",
                    fiscal_id,
                )
                return

            service = ScaricoMassivoService(db)
            for cfg in configs:
                try:
                    result = await service.sync_now(
                        config_id=cfg.id, tenant_id=cfg.tenant_id
                    )
                    logger.info(
                        "Webhook-driven sync completato per piva=%s tenant=%s: %s",
                        fiscal_id,
                        cfg.tenant_id,
                        result.get("message"),
                    )
                except ScaricoMassivoServiceError as e:
                    logger.warning(
                        "Webhook-driven sync fallito per piva=%s: %s", fiscal_id, e
                    )
        except Exception:
            logger.exception("invoice-downloaded processor failed for %s", event_id)
