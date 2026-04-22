"""Background processors per eventi webhook A-Cube OB (Pivot 11 US-OB-05).

Logica business separata dai receiver per permettere:
- Processing asincrono (fast return 200 OK)
- Ri-processing manuale da endpoint admin
- Test unitari isolati
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import BankConnection, WebhookEvent

logger = logging.getLogger(__name__)


async def process_connect_event(db: AsyncSession, event_id: uuid.UUID) -> None:
    """Processa evento Connect — update status BankConnection.

    Payload atteso:
    - success=true:  {fiscalId, success, updatedAccounts: [...]}
    - success=false: {fiscalId, success, errorClass, errorMessage}
    """
    event = await _load_event(db, event_id)
    if not event or event.processing_status == "processed":
        return

    try:
        payload = event.payload
        fiscal_id = payload.get("fiscalId")
        if not fiscal_id:
            raise ValueError("Payload Connect senza fiscalId")

        conn = await _get_connection_by_fiscal_id(db, fiscal_id)
        if not conn:
            logger.warning("Connect webhook per fiscal_id=%s non mappato a nessuna BankConnection", fiscal_id)
            event.processing_status = "error"
            event.processing_error = f"No BankConnection for fiscal_id={fiscal_id}"
        elif payload.get("success"):
            conn.status = "active"
            conn.acube_enabled = True
            conn.last_connect_error = None
            event.processing_status = "processed"
            logger.info("BankConnection %s attivata (fiscal_id=%s, accounts=%s)",
                        conn.id, fiscal_id, payload.get("updatedAccounts"))
        else:
            conn.status = "pending"
            conn.last_connect_error = f"{payload.get('errorClass')}: {payload.get('errorMessage')}"
            event.processing_status = "processed"
            logger.warning("Connect fallito per fiscal_id=%s: %s", fiscal_id, conn.last_connect_error)

        event.processed_at = datetime.utcnow()
    except Exception as e:  # noqa: BLE001
        event.processing_status = "error"
        event.processing_error = str(e)[:500]
        logger.exception("Processing Connect event %s failed", event_id)

    await db.commit()


async def process_reconnect_event(db: AsyncSession, event_id: uuid.UUID) -> None:
    """Processa evento Reconnect — salva reconnect_url + notice_level.

    Payload: {fiscalId, connectUrl, providerName, consentExpiresAt, noticeLevel}
    """
    event = await _load_event(db, event_id)
    if not event or event.processing_status == "processed":
        return

    try:
        payload = event.payload
        fiscal_id = payload.get("fiscalId")
        conn = await _get_connection_by_fiscal_id(db, fiscal_id) if fiscal_id else None

        if not conn:
            event.processing_status = "error"
            event.processing_error = f"No BankConnection for fiscal_id={fiscal_id}"
        else:
            conn.reconnect_url = payload.get("connectUrl")
            conn.notice_level = payload.get("noticeLevel")
            conn.last_reconnect_webhook_at = datetime.utcnow()
            # parse consentExpiresAt
            expires_at_str = payload.get("consentExpiresAt")
            if expires_at_str:
                try:
                    # formato ISO 8601 con timezone — strip Z/timezone per Python 3.11
                    clean = expires_at_str.replace("Z", "").split("+")[0].split(".")[0]
                    conn.consent_expires_at = datetime.fromisoformat(clean)
                except Exception:  # noqa: BLE001
                    logger.warning("Impossibile parsare consentExpiresAt: %s", expires_at_str)
            event.processing_status = "processed"
            # TODO: trigger email Brevo + notifica in-app (US-OB-12)
            logger.info("Reconnect webhook processato per fiscal_id=%s notice=%s",
                        fiscal_id, payload.get("noticeLevel"))

        event.processed_at = datetime.utcnow()
    except Exception as e:  # noqa: BLE001
        event.processing_status = "error"
        event.processing_error = str(e)[:500]
        logger.exception("Processing Reconnect event %s failed", event_id)

    await db.commit()


async def process_payment_event(db: AsyncSession, event_id: uuid.UUID) -> None:
    """Processa evento Payment — update stato pagamento.

    Placeholder: logica completa arriverà con Pivot 11 Sprint 53 (PISP).
    """
    event = await _load_event(db, event_id)
    if not event or event.processing_status == "processed":
        return

    try:
        payload = event.payload
        logger.info("Payment webhook ricevuto: fiscal_id=%s success=%s status=%s",
                    payload.get("fiscalId"),
                    payload.get("success"),
                    payload.get("payment", {}).get("status"))
        # TODO: update stato Payment locale + notifica user (Sprint 53)
        event.processing_status = "processed"
        event.processed_at = datetime.utcnow()
    except Exception as e:  # noqa: BLE001
        event.processing_status = "error"
        event.processing_error = str(e)[:500]
        logger.exception("Processing Payment event %s failed", event_id)

    await db.commit()


# ── Helpers ────────────────────────────────────────────────

async def _load_event(db: AsyncSession, event_id: uuid.UUID) -> WebhookEvent | None:
    result = await db.execute(select(WebhookEvent).where(WebhookEvent.id == event_id))
    return result.scalar_one_or_none()


async def _get_connection_by_fiscal_id(db: AsyncSession, fiscal_id: str) -> BankConnection | None:
    result = await db.execute(
        select(BankConnection).where(BankConnection.fiscal_id == fiscal_id.upper())
    )
    return result.scalar_one_or_none()
