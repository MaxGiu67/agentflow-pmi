"""Mock Google Cloud Vision OCR adapter.

In production this calls Google Cloud Vision API.
For testing/development, returns mock OCR results with realistic
confidence scores per field.
"""

import logging
import random
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class OCRFieldResult:
    """A single extracted field with confidence."""
    field_name: str
    value: str
    confidence: float  # 0.0 - 1.0


@dataclass
class OCRResult:
    """Full OCR extraction result."""
    success: bool
    fields: list[OCRFieldResult] = field(default_factory=list)
    overall_accuracy: float = 0.0
    processing_time_ms: float = 0.0
    error: str | None = None
    needs_review: bool = False
    review_fields: list[str] = field(default_factory=list)


class CloudVisionOCRAdapter:
    """Mock adapter for Google Cloud Vision OCR.

    Simulates OCR extraction from PDF/image files with per-field
    confidence scores.
    """

    # Minimum confidence threshold for "verified" fields
    CONFIDENCE_THRESHOLD = 0.60

    def __init__(self) -> None:
        self._fail_mode: str | None = None  # For testing: "protected_pdf", "corrupted_image"

    def set_fail_mode(self, mode: str | None) -> None:
        """Set failure mode for testing."""
        self._fail_mode = mode

    async def extract_invoice_data(
        self,
        file_content: bytes,
        filename: str,
        content_type: str,
    ) -> OCRResult:
        """Extract invoice data from a PDF or image file.

        Args:
            file_content: Raw file bytes.
            filename: Original filename.
            content_type: MIME type.

        Returns:
            OCRResult with extracted fields and confidence scores.

        Raises:
            ValueError: If the file cannot be read (protected PDF, corrupted image).
        """
        start = time.monotonic()

        # Check for failure modes
        if self._fail_mode == "protected_pdf":
            raise ValueError(
                "PDF protetto da password: impossibile estrarre il testo. "
                "Rimuovere la protezione e riprovare."
            )
        if self._fail_mode == "corrupted_image":
            raise ValueError(
                "Immagine corrotta o formato non riconosciuto: "
                "impossibile elaborare il file."
            )

        # Validate content type
        supported = {
            "application/pdf", "image/jpeg", "image/png",
            "image/jpg", "image/tiff",
        }
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if content_type not in supported and ext not in ("pdf", "jpg", "jpeg", "png", "tiff"):
            raise ValueError(
                f"Formato file non supportato per OCR: {content_type}. "
                f"Formati supportati: PDF, JPG, PNG, TIFF."
            )

        # Check for empty / too-small content
        if len(file_content) < 10:
            raise ValueError(
                "Immagine corrotta o formato non riconosciuto: "
                "impossibile elaborare il file."
            )

        # --- Mock OCR extraction ---
        fields = self._mock_extract(file_content, filename)

        elapsed_ms = (time.monotonic() - start) * 1000

        # Compute overall accuracy
        if fields:
            overall = sum(f.confidence for f in fields) / len(fields)
        else:
            overall = 0.0

        # Identify low-confidence fields
        review_fields = [
            f.field_name for f in fields
            if f.confidence < self.CONFIDENCE_THRESHOLD
        ]

        return OCRResult(
            success=True,
            fields=fields,
            overall_accuracy=overall,
            processing_time_ms=elapsed_ms,
            needs_review=len(review_fields) > 0,
            review_fields=review_fields,
        )

    def _mock_extract(
        self, file_content: bytes, filename: str,
    ) -> list[OCRFieldResult]:
        """Generate mock OCR fields with realistic confidence scores.

        Uses deterministic seeding based on file content length so tests
        are reproducible, but produces realistic-looking data.
        """
        # Seed for reproducibility in tests
        seed = len(file_content) % 1000
        rng = random.Random(seed)

        # Standard invoice fields with base confidence
        field_defs = [
            ("numero_fattura", "FT-2025-0042"),
            ("data_fattura", "2025-03-15"),
            ("emittente_piva", "IT01234567890"),
            ("emittente_nome", "Fornitore Example SRL"),
            ("importo_netto", "1000.00"),
            ("importo_iva", "220.00"),
            ("importo_totale", "1220.00"),
            ("aliquota_iva", "22"),
        ]

        fields: list[OCRFieldResult] = []
        for name, value in field_defs:
            # Generate confidence: mostly high (85-99%) with occasional low
            base = rng.uniform(0.75, 0.99)
            # 15% chance of lower confidence
            if rng.random() < 0.15:
                base = rng.uniform(0.40, 0.65)
            confidence = round(base, 2)
            fields.append(OCRFieldResult(
                field_name=name,
                value=value,
                confidence=confidence,
            ))

        return fields


class MultiAttachmentProcessor:
    """Processes multiple attachments from a single email."""

    def __init__(self, ocr_adapter: CloudVisionOCRAdapter) -> None:
        self.ocr = ocr_adapter

    async def process_attachments(
        self,
        attachments: list[dict],
    ) -> list[OCRResult]:
        """Process multiple email attachments, returning one OCRResult per attachment.

        Args:
            attachments: List of dicts with keys: filename, content_type, content (bytes).

        Returns:
            List of OCRResult, one per attachment.
        """
        results: list[OCRResult] = []
        for att in attachments:
            try:
                result = await self.ocr.extract_invoice_data(
                    file_content=att["content"],
                    filename=att["filename"],
                    content_type=att["content_type"],
                )
                results.append(result)
            except ValueError as e:
                results.append(OCRResult(
                    success=False,
                    error=str(e),
                ))
        return results
