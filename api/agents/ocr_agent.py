"""OCR Agent: processes PDF/image invoices via Cloud Vision mock adapter.

Returns structured data with per-field confidence scores.
Fields with confidence < 60% are flagged for manual review.
"""

import logging
import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.adapters.ocr import CloudVisionOCRAdapter, MultiAttachmentProcessor, OCRResult
from api.agents.base_agent import BaseAgent
from api.db.models import Invoice

logger = logging.getLogger(__name__)


class OCRAgent(BaseAgent):
    """Agent that processes invoice files through OCR."""

    agent_name = "ocr_agent"

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)
        self.ocr = CloudVisionOCRAdapter()

    async def process_file(
        self,
        file_content: bytes,
        filename: str,
        content_type: str,
        tenant_id: uuid.UUID,
    ) -> dict:
        """Run OCR on a single file and return structured invoice data.

        Args:
            file_content: Raw file bytes.
            filename: Original filename.
            content_type: MIME type.
            tenant_id: Owning tenant.

        Returns:
            Dict with extracted fields, confidence scores, review flags.

        Raises:
            ValueError: If file is unreadable (protected PDF, corrupted image).
        """
        try:
            result = await self.ocr.extract_invoice_data(
                file_content=file_content,
                filename=filename,
                content_type=content_type,
            )
        except ValueError:
            # Re-raise file-level errors (protected PDF, corrupted image)
            raise

        # Build structured response
        field_data = {}
        confidence_scores = {}
        for f in result.fields:
            field_data[f.field_name] = f.value
            confidence_scores[f.field_name] = f.confidence

        response = {
            "success": result.success,
            "fields": field_data,
            "confidence_scores": confidence_scores,
            "overall_accuracy": round(result.overall_accuracy, 2),
            "processing_time_ms": round(result.processing_time_ms, 2),
            "needs_review": result.needs_review,
            "review_fields": result.review_fields,
        }

        # Publish event
        await self.publish_event(
            "invoice.ocr_processed",
            {
                "filename": filename,
                "overall_accuracy": response["overall_accuracy"],
                "needs_review": response["needs_review"],
                "review_fields": response["review_fields"],
            },
            tenant_id,
        )

        return response

    async def process_email_attachments(
        self,
        attachments: list[dict],
        tenant_id: uuid.UUID,
    ) -> list[dict]:
        """Process multiple attachments from an email, creating one record per invoice.

        Args:
            attachments: List of dicts with keys: filename, content_type, content.
            tenant_id: Owning tenant.

        Returns:
            List of invoice records created.
        """
        processor = MultiAttachmentProcessor(self.ocr)
        results = await processor.process_attachments(attachments)

        invoice_records: list[dict] = []
        for att, result in zip(attachments, results):
            if result.success:
                field_data = {f.field_name: f.value for f in result.fields}
                confidence_scores = {f.field_name: f.confidence for f in result.fields}

                # Create Invoice record
                invoice = Invoice(
                    tenant_id=tenant_id,
                    type="passiva",
                    document_type="TD01",
                    source="email",
                    numero_fattura=field_data.get("numero_fattura", f"OCR-{uuid.uuid4().hex[:8]}"),
                    emittente_piva=field_data.get("emittente_piva", ""),
                    emittente_nome=field_data.get("emittente_nome", ""),
                    data_fattura=self._parse_date(field_data.get("data_fattura")),
                    importo_netto=self._parse_float(field_data.get("importo_netto")),
                    importo_iva=self._parse_float(field_data.get("importo_iva")),
                    importo_totale=self._parse_float(field_data.get("importo_totale")),
                    processing_status="verifica_richiesta" if result.needs_review else "parsed",
                    structured_data={
                        "ocr_fields": field_data,
                        "confidence_scores": confidence_scores,
                        "overall_accuracy": round(result.overall_accuracy, 2),
                        "needs_review": result.needs_review,
                        "review_fields": result.review_fields,
                        "source_filename": att["filename"],
                    },
                )
                self.db.add(invoice)
                await self.db.flush()

                invoice_records.append({
                    "invoice_id": str(invoice.id),
                    "filename": att["filename"],
                    "status": invoice.processing_status,
                    "needs_review": result.needs_review,
                    "overall_accuracy": round(result.overall_accuracy, 2),
                })
            else:
                invoice_records.append({
                    "invoice_id": None,
                    "filename": att["filename"],
                    "status": "error",
                    "error": result.error,
                    "needs_review": False,
                    "overall_accuracy": 0.0,
                })

        # Publish event
        await self.publish_event(
            "email.attachments_processed",
            {
                "total_attachments": len(attachments),
                "successful": sum(1 for r in invoice_records if r.get("invoice_id")),
                "failed": sum(1 for r in invoice_records if not r.get("invoice_id")),
            },
            tenant_id,
        )

        return invoice_records

    @staticmethod
    def _parse_date(value: str | None) -> date | None:
        """Safely parse a date string."""
        if not value:
            return None
        try:
            return date.fromisoformat(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_float(value: str | None) -> float | None:
        """Safely parse a float string."""
        if not value:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
