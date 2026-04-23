"""PEC service — manages tenant PEC config, invoice dispatch, receipt polling."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.adapters import pec_client
from api.db.models import (
    ActiveInvoice,
    PecMessage,
    TenantPecConfig,
)
from api.modules.tenant_settings.service import decrypt_value, encrypt_value

logger = logging.getLogger(__name__)


class PecServiceError(Exception):
    pass


class PecService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_config(self, tenant_id: uuid.UUID) -> TenantPecConfig | None:
        res = await self.db.execute(
            select(TenantPecConfig).where(TenantPecConfig.tenant_id == tenant_id)
        )
        return res.scalar_one_or_none()

    async def upsert_config(
        self,
        tenant_id: uuid.UUID,
        provider: str,
        pec_address: str,
        username: str,
        password: str,
        smtp_host: str | None,
        smtp_port: int | None,
        imap_host: str | None,
        imap_port: int | None,
    ) -> TenantPecConfig:
        preset = pec_client.get_provider_preset(provider)
        if preset:
            smtp_host = smtp_host or preset["smtp_host"]
            smtp_port = smtp_port or preset["smtp_port"]
            imap_host = imap_host or preset["imap_host"]
            imap_port = imap_port or preset["imap_port"]

        if not (smtp_host and smtp_port and imap_host and imap_port):
            raise PecServiceError(
                "Provider non riconosciuto: specifica smtp_host, smtp_port, imap_host, imap_port"
            )

        existing = await self.get_config(tenant_id)
        if existing:
            existing.provider = provider
            existing.pec_address = pec_address
            existing.username = username
            existing.password_encrypted = encrypt_value(password)
            existing.smtp_host = smtp_host
            existing.smtp_port = smtp_port
            existing.imap_host = imap_host
            existing.imap_port = imap_port
            existing.verified = False
            existing.last_test_error = None
            cfg = existing
        else:
            cfg = TenantPecConfig(
                tenant_id=tenant_id,
                provider=provider,
                pec_address=pec_address,
                username=username,
                password_encrypted=encrypt_value(password),
                smtp_host=smtp_host,
                smtp_port=smtp_port,
                imap_host=imap_host,
                imap_port=imap_port,
            )
            self.db.add(cfg)

        await self.db.commit()
        await self.db.refresh(cfg)
        return cfg

    async def test_connection(self, tenant_id: uuid.UUID) -> pec_client.PecTestResult:
        cfg = await self.get_config(tenant_id)
        if not cfg:
            raise PecServiceError("Configurazione PEC non presente")
        pw = decrypt_value(cfg.password_encrypted)
        result = await asyncio.to_thread(
            pec_client.test_connection,
            cfg.smtp_host, cfg.smtp_port,
            cfg.imap_host, cfg.imap_port,
            cfg.username, pw,
        )
        cfg.verified = result.smtp_ok and result.imap_ok
        cfg.last_test_at = datetime.utcnow()
        cfg.last_test_error = result.error
        await self.db.commit()
        return result

    async def send_signed_invoice_to_sdi(
        self,
        tenant_id: uuid.UUID,
        invoice_id: uuid.UUID,
        filename: str,
        p7m_content: bytes,
        test_mode: bool = False,
    ) -> PecMessage:
        cfg = await self.get_config(tenant_id)
        if not cfg:
            raise PecServiceError(
                "Configurazione PEC non presente — vai su Impostazioni → PEC"
            )

        # Retrieve the invoice to attach FK
        inv_res = await self.db.execute(
            select(ActiveInvoice).where(
                and_(
                    ActiveInvoice.id == invoice_id,
                    ActiveInvoice.tenant_id == tenant_id,
                )
            )
        )
        inv = inv_res.scalar_one_or_none()
        if not inv:
            raise PecServiceError("Fattura non trovata")

        pw = decrypt_value(cfg.password_encrypted)

        # In test mode: send the PEC to the sender's own address (validates SMTP + firma without
        # touching Agenzia Entrate / SDI)
        recipient = cfg.pec_address if test_mode else pec_client.SDI_PEC_ADDRESS
        subject_prefix = "[TEST] " if test_mode else ""

        try:
            result = await asyncio.to_thread(
                pec_client.send_signed_invoice,
                cfg.smtp_host, cfg.smtp_port,
                cfg.username, pw,
                cfg.pec_address,
                filename, p7m_content,
                recipient,
                f"{subject_prefix}Invio fattura {filename}",
                None,
            )
        except Exception as e:
            logger.exception("PEC send failed")
            msg = PecMessage(
                tenant_id=tenant_id,
                active_invoice_id=invoice_id,
                direction="sent",
                subject=f"{subject_prefix}Invio fattura {filename}",
                recipient=recipient,
                sender=cfg.pec_address,
                attachment_name=filename,
                error=f"{type(e).__name__}: {e}",
            )
            self.db.add(msg)
            await self.db.commit()
            raise PecServiceError(f"Invio PEC fallito: {e}") from e

        msg = PecMessage(
            tenant_id=tenant_id,
            active_invoice_id=invoice_id,
            direction="sent",
            subject=f"{subject_prefix}Invio fattura {filename}",
            message_id=result.message_id,
            recipient=result.recipient,
            sender=cfg.pec_address,
            attachment_name=filename,
            sent_at=result.sent_at,
        )
        self.db.add(msg)

        # Only update invoice status on REAL sends — test sends shouldn't touch fiscal status
        if not test_mode:
            inv.sdi_status = "sent"
            inv.sdi_id = result.message_id
            inv.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(msg)
        return msg

    async def poll_receipts(
        self, tenant_id: uuid.UUID, since_date: datetime | None = None
    ) -> list[PecMessage]:
        cfg = await self.get_config(tenant_id)
        if not cfg:
            raise PecServiceError("Configurazione PEC non presente")

        pw = decrypt_value(cfg.password_encrypted)
        receipts = await asyncio.to_thread(
            pec_client.poll_receipts,
            cfg.imap_host, cfg.imap_port,
            cfg.username, pw,
            since_date,
        )

        # Dedupe by message_id
        existing_ids_res = await self.db.execute(
            select(PecMessage.message_id).where(
                and_(PecMessage.tenant_id == tenant_id, PecMessage.direction == "received")
            )
        )
        existing_ids = {row[0] for row in existing_ids_res.all() if row[0]}

        new_messages: list[PecMessage] = []
        for r in receipts:
            if r.message_id and r.message_id in existing_ids:
                continue

            # Find the active invoice by related filename if possible
            invoice_id: uuid.UUID | None = None
            if r.related_filename:
                # filename pattern: IT{piva}_{progressive}.xml — progressive is last segment
                try:
                    progressive = r.related_filename.replace(".xml", "").split("_")[-1]
                    inv_res = await self.db.execute(
                        select(ActiveInvoice).where(
                            and_(
                                ActiveInvoice.tenant_id == tenant_id,
                                ActiveInvoice.numero_fattura.ilike(f"%{progressive}%"),
                            )
                        )
                    )
                    inv = inv_res.scalars().first()
                    if inv:
                        invoice_id = inv.id
                        # Update SDI status based on receipt
                        inv.sdi_status = _receipt_to_status(r.receipt_type)
                        if r.receipt_type == "NS":
                            inv.sdi_reject_reason = r.subject
                except Exception:
                    logger.warning("Failed to match receipt to invoice: %s", r.related_filename)

            msg = PecMessage(
                tenant_id=tenant_id,
                active_invoice_id=invoice_id,
                direction="received",
                subject=r.subject,
                message_id=r.message_id,
                sender=r.sender,
                attachment_name=r.related_filename,
                receipt_type=r.receipt_type,
                raw_headers=r.raw_headers,
                sent_at=r.received_at,
            )
            self.db.add(msg)
            new_messages.append(msg)

        if new_messages:
            await self.db.commit()

        return new_messages


def _receipt_to_status(receipt_type: str) -> str:
    """Map SDI receipt type to our sdi_status enum."""
    mapping = {
        "RC": "delivered",        # Ricevuta Consegna
        "NS": "rejected",         # Notifica Scarto
        "MC": "not_delivered",    # Mancata Consegna — va bene, cliente riceverà dal cassetto
        "NE": "delivered",        # Notifica Esito (committente) — accettata
        "DT": "delivered",        # Decorrenza Termini
        "AT": "sent",             # Attestazione Trasmissione
    }
    return mapping.get(receipt_type.upper(), "sent")
