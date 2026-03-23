"""Service layer for SDI webhook (US-07)."""

import hashlib
import hmac
import logging
import uuid
from datetime import date, datetime, UTC

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import Invoice

logger = logging.getLogger(__name__)

# In production this would come from env/config
SDI_WEBHOOK_SECRET = "sdi-webhook-secret-key"


class SDIService:
    """Service for SDI webhook processing."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def validate_payload(self, payload: dict) -> None:
        """Validate that the SDI webhook payload has required fields."""
        required = ["id_sdi", "numero_fattura", "emittente_piva", "data_fattura", "importo_totale"]
        missing = [f for f in required if not payload.get(f)]
        if missing:
            raise ValueError(f"Payload SDI incompleto. Campi mancanti: {', '.join(missing)}")

    async def check_duplicate(
        self,
        tenant_id: uuid.UUID,
        numero_fattura: str,
        emittente_piva: str,
        data_fattura: date,
    ) -> Invoice | None:
        """Check if invoice already exists (dedup with cassetto)."""
        result = await self.db.execute(
            select(Invoice).where(
                and_(
                    Invoice.tenant_id == tenant_id,
                    Invoice.numero_fattura == numero_fattura,
                    Invoice.emittente_piva == emittente_piva,
                    Invoice.data_fattura == data_fattura,
                )
            )
        )
        return result.scalar_one_or_none()

    async def process_webhook(
        self,
        tenant_id: uuid.UUID,
        payload: dict,
    ) -> dict:
        """Process incoming SDI webhook payload.

        Args:
            tenant_id: Target tenant ID (from webhook routing config).
            payload: Validated webhook data.

        Returns:
            Dict with status, invoice_id, message.
        """
        self.validate_payload(payload)

        numero = payload["numero_fattura"]
        piva = payload["emittente_piva"]
        data_f = payload["data_fattura"]
        if isinstance(data_f, str):
            data_f = date.fromisoformat(data_f)

        # Dedup check
        existing = await self.check_duplicate(tenant_id, numero, piva, data_f)
        if existing:
            return {
                "status": "duplicate",
                "invoice_id": existing.id,
                "message": f"Fattura {numero} gia presente (source={existing.source})",
            }

        # Create new invoice from SDI
        invoice = Invoice(
            tenant_id=tenant_id,
            type="passiva",
            document_type=payload.get("tipo_documento", "TD01"),
            source="sdi_realtime",
            numero_fattura=numero,
            emittente_piva=piva,
            emittente_nome=payload.get("emittente_nome"),
            data_fattura=data_f,
            importo_totale=payload["importo_totale"],
            importo_netto=payload.get("importo_netto"),
            importo_iva=payload.get("importo_iva"),
            raw_xml=payload.get("xml_content"),
            processing_status="parsed" if payload.get("xml_content") else "pending",
        )
        self.db.add(invoice)
        await self.db.flush()

        logger.info("SDI invoice received: %s from %s", numero, piva)

        return {
            "status": "accepted",
            "invoice_id": invoice.id,
            "message": f"Fattura {numero} ricevuta via SDI e salvata",
        }
