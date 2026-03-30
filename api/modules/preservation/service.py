"""Service layer for digital preservation (conservazione digitale a norma) (US-37)."""

import logging
import uuid
from datetime import datetime, UTC

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.adapters.preservation import (
    MockArubaPreservationAdapter,
    PreservationAdapter,
)
from api.db.models import ActiveInvoice, DigitalPreservation, Invoice

logger = logging.getLogger(__name__)

# Max retry attempts before giving up
MAX_RETRIES = 5
# Backoff base in seconds (doubles each retry)
BACKOFF_BASE = 60
# Threshold for notification (48 hours)
NOTIFICATION_THRESHOLD_HOURS = 48


class PreservationService:
    """Business logic for digital preservation."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.adapter: PreservationAdapter = MockArubaPreservationAdapter()

    async def send_batch(
        self,
        tenant_id: uuid.UUID,
        provider: str = "aruba",
    ) -> dict:
        """Send batch of queued documents to preservation provider.

        AC-37.1: Invio automatico batch giornaliero a provider.
        AC-37.3: Provider non raggiungibile -> retry backoff, notifica >48h.
        """
        # Get invoices not yet sent to preservation
        result = await self.db.execute(
            select(Invoice).where(
                Invoice.tenant_id == tenant_id,
                Invoice.processing_status != "error",
            )
        )
        invoices = result.scalars().all()

        # Check which invoices already have preservation records
        existing_result = await self.db.execute(
            select(DigitalPreservation.invoice_id).where(
                DigitalPreservation.tenant_id == tenant_id,
            )
        )
        existing_ids = {row for row in existing_result.scalars().all()}

        # Filter to invoices that need preservation
        to_preserve = [inv for inv in invoices if inv.id not in existing_ids]

        # Also check for queued items that need retry
        retry_result = await self.db.execute(
            select(DigitalPreservation).where(
                DigitalPreservation.tenant_id == tenant_id,
                DigitalPreservation.status == "queued",
                DigitalPreservation.retry_count < MAX_RETRIES,
            )
        )
        retry_items = retry_result.scalars().all()

        sent = 0
        errors = 0
        details: list[dict] = []

        # Check provider availability
        try:
            available = await self.adapter.is_available()
        except Exception:
            available = False

        if not available:
            # AC-37.3: Provider not reachable, update retry counts
            for item in retry_items:
                item.retry_count += 1
                item.last_attempt_at = datetime.now(UTC).replace(tzinfo=None)
                # Check if we need to send notification (>48h)
                if item.created_at:
                    hours_elapsed = (datetime.now(UTC).replace(tzinfo=None) - item.created_at).total_seconds() / 3600
                    if hours_elapsed > NOTIFICATION_THRESHOLD_HOURS:
                        details.append({
                            "invoice_id": str(item.invoice_id),
                            "status": "notification_required",
                            "message": f"Conservazione in attesa da oltre 48h (tentativi: {item.retry_count})",
                        })

            # Queue new invoices for later
            for inv in to_preserve:
                pres = DigitalPreservation(
                    tenant_id=tenant_id,
                    invoice_id=inv.id,
                    provider=provider,
                    status="queued",
                    retry_count=1,
                    last_attempt_at=datetime.now(UTC).replace(tzinfo=None),
                )
                self.db.add(pres)
                errors += 1
                details.append({
                    "invoice_id": str(inv.id),
                    "status": "queued",
                    "message": "Provider non raggiungibile, in coda per retry",
                })

            await self.db.flush()
            return {"sent": sent, "errors": errors, "details": details}

        # Send new invoices
        for inv in to_preserve:
            try:
                doc_content = inv.raw_xml or f"invoice-{inv.id}"
                send_result = await self.adapter.send_document(doc_content, str(inv.id))

                pres = DigitalPreservation(
                    tenant_id=tenant_id,
                    invoice_id=inv.id,
                    provider=provider,
                    batch_id=send_result.batch_id,
                    package_hash=send_result.package_hash,
                    status="sent",
                    last_attempt_at=datetime.now(UTC).replace(tzinfo=None),
                )
                self.db.add(pres)
                sent += 1
                details.append({
                    "invoice_id": str(inv.id),
                    "status": "sent",
                    "batch_id": send_result.batch_id,
                    "message": send_result.message,
                })
            except ConnectionError:
                pres = DigitalPreservation(
                    tenant_id=tenant_id,
                    invoice_id=inv.id,
                    provider=provider,
                    status="queued",
                    retry_count=1,
                    last_attempt_at=datetime.now(UTC).replace(tzinfo=None),
                )
                self.db.add(pres)
                errors += 1
                details.append({
                    "invoice_id": str(inv.id),
                    "status": "queued",
                    "message": "Errore invio, in coda per retry",
                })

        # Retry queued items
        for item in retry_items:
            try:
                inv_result = await self.db.execute(
                    select(Invoice).where(Invoice.id == item.invoice_id)
                )
                inv = inv_result.scalar_one_or_none()
                if not inv:
                    continue

                doc_content = inv.raw_xml or f"invoice-{inv.id}"
                send_result = await self.adapter.send_document(doc_content, str(inv.id))

                item.batch_id = send_result.batch_id
                item.package_hash = send_result.package_hash
                item.status = "sent"
                item.last_attempt_at = datetime.now(UTC).replace(tzinfo=None)
                sent += 1
            except ConnectionError:
                item.retry_count += 1
                item.last_attempt_at = datetime.now(UTC).replace(tzinfo=None)
                errors += 1

        await self.db.flush()
        return {"sent": sent, "errors": errors, "details": details}

    async def check_status(
        self,
        tenant_id: uuid.UUID,
    ) -> dict:
        """Check preservation status for all sent documents.

        AC-37.2: Verifica stato (conservati, in attesa, errori).
        AC-37.4: Pacchetto rifiutato -> "conservazione rifiutata" con motivo.
        """
        result = await self.db.execute(
            select(DigitalPreservation).where(
                DigitalPreservation.tenant_id == tenant_id,
                DigitalPreservation.status == "sent",
            )
        )
        sent_items = result.scalars().all()

        confirmed = 0
        rejected = 0
        details: list[dict] = []

        for item in sent_items:
            if not item.batch_id:
                continue
            try:
                status_result = await self.adapter.check_status(item.batch_id)

                if status_result.status == "confirmed":
                    item.status = "confirmed"
                    item.confirmed_at = datetime.now(UTC).replace(tzinfo=None)
                    confirmed += 1
                    details.append({
                        "invoice_id": str(item.invoice_id),
                        "batch_id": item.batch_id,
                        "status": "confirmed",
                    })
                elif status_result.status == "rejected":
                    # AC-37.4: rejected with reason
                    item.status = "rejected"
                    item.reject_reason = status_result.reject_reason
                    rejected += 1
                    details.append({
                        "invoice_id": str(item.invoice_id),
                        "batch_id": item.batch_id,
                        "status": "rejected",
                        "reject_reason": status_result.reject_reason,
                    })
            except ConnectionError:
                details.append({
                    "invoice_id": str(item.invoice_id),
                    "batch_id": item.batch_id,
                    "status": "check_failed",
                    "message": "Provider non raggiungibile",
                })

        await self.db.flush()

        return {
            "checked": len(sent_items),
            "confirmed": confirmed,
            "rejected": rejected,
            "details": details,
        }

    async def list_preservation(
        self,
        tenant_id: uuid.UUID,
    ) -> dict:
        """List all preservation records with status summary.

        AC-37.2: Verifica stato (conservati, in attesa, errori).
        """
        result = await self.db.execute(
            select(DigitalPreservation).where(
                DigitalPreservation.tenant_id == tenant_id,
            ).order_by(DigitalPreservation.created_at.desc())
        )
        items = result.scalars().all()

        # Summary by status
        summary: dict[str, int] = {}
        for item in items:
            summary[item.status] = summary.get(item.status, 0) + 1

        return {
            "items": [
                {
                    "id": str(p.id),
                    "tenant_id": str(p.tenant_id),
                    "invoice_id": str(p.invoice_id),
                    "provider": p.provider,
                    "batch_id": p.batch_id,
                    "package_hash": p.package_hash,
                    "status": p.status,
                    "reject_reason": p.reject_reason,
                    "retry_count": p.retry_count,
                    "last_attempt_at": p.last_attempt_at.isoformat() if p.last_attempt_at else None,
                    "confirmed_at": p.confirmed_at.isoformat() if p.confirmed_at else None,
                }
                for p in items
            ],
            "total": len(items),
            "summary": summary,
        }

    async def send_credit_note(
        self,
        tenant_id: uuid.UUID,
        credit_note_id: uuid.UUID,
        provider: str = "aruba",
    ) -> dict:
        """Send credit note linked to preserved invoice.

        AC-37.5: Nota credito post-conservazione -> invia anche NC collegata.
        """
        # Check if the credit note references a preserved invoice
        result = await self.db.execute(
            select(ActiveInvoice).where(
                ActiveInvoice.id == credit_note_id,
                ActiveInvoice.tenant_id == tenant_id,
                ActiveInvoice.document_type == "TD04",
            )
        )
        credit_note = result.scalar_one_or_none()

        if not credit_note:
            # Try from regular invoices
            inv_result = await self.db.execute(
                select(Invoice).where(
                    Invoice.id == credit_note_id,
                    Invoice.tenant_id == tenant_id,
                    Invoice.document_type == "TD04",
                )
            )
            invoice = inv_result.scalar_one_or_none()
            if not invoice:
                raise ValueError("Nota credito non trovata")

            doc_content = invoice.raw_xml or f"credit-note-{invoice.id}"
        else:
            doc_content = credit_note.raw_xml or f"credit-note-{credit_note.id}"

        try:
            send_result = await self.adapter.send_document(doc_content, str(credit_note_id))

            pres = DigitalPreservation(
                tenant_id=tenant_id,
                invoice_id=credit_note_id,
                provider=provider,
                batch_id=send_result.batch_id,
                package_hash=send_result.package_hash,
                status="sent",
                last_attempt_at=datetime.now(UTC).replace(tzinfo=None),
            )
            self.db.add(pres)
            await self.db.flush()

            return {
                "invoice_id": str(credit_note_id),
                "status": "sent",
                "batch_id": send_result.batch_id,
                "message": "Nota credito inviata a conservazione",
            }
        except ConnectionError as e:
            pres = DigitalPreservation(
                tenant_id=tenant_id,
                invoice_id=credit_note_id,
                provider=provider,
                status="queued",
                retry_count=1,
                last_attempt_at=datetime.now(UTC).replace(tzinfo=None),
            )
            self.db.add(pres)
            await self.db.flush()

            return {
                "invoice_id": str(credit_note_id),
                "status": "queued",
                "batch_id": None,
                "message": f"Provider non raggiungibile: {e}",
            }
