"""
Test suite for US-09: OCR fattura PDF/immagine
Tests for 4 Acceptance Criteria (AC-09.1 through AC-09.4)
"""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from api.adapters.ocr import CloudVisionOCRAdapter, MultiAttachmentProcessor
from api.agents.ocr_agent import OCRAgent
from api.db.models import Tenant


# ============================================================
# AC-09.1 — OCR via Cloud Vision mock, accuracy >=85%,
#            confidence score per campo, <=10s
# ============================================================


class TestAC091OCRBasic:
    """AC-09.1: OCR extraction with accuracy and confidence."""

    async def test_ac_091_ocr_pdf_extraction(self, db_session: AsyncSession, tenant: Tenant):
        """AC-09.1: DATO un file PDF di fattura, QUANDO esegue OCR,
        ALLORA estrae i campi con accuracy >= 85% e confidence per campo."""
        agent = OCRAgent(db_session)
        # Simulate a PDF with enough content for the mock
        pdf_content = b"%PDF-1.4 mock invoice content " + b"x" * 200

        result = await agent.process_file(
            file_content=pdf_content,
            filename="fattura_test.pdf",
            content_type="application/pdf",
            tenant_id=tenant.id,
        )

        assert result["success"] is True
        assert result["overall_accuracy"] >= 0.85
        assert "confidence_scores" in result
        assert len(result["confidence_scores"]) > 0

        # Each field should have a confidence score
        for field_name, confidence in result["confidence_scores"].items():
            assert 0.0 <= confidence <= 1.0, f"Invalid confidence for {field_name}"

    async def test_ac_091_ocr_image_extraction(self, db_session: AsyncSession, tenant: Tenant):
        """AC-09.1: DATO un file immagine JPG, QUANDO esegue OCR,
        ALLORA estrae i dati fattura con confidence per campo."""
        agent = OCRAgent(db_session)
        jpg_content = b"\xff\xd8\xff\xe0 mock jpg invoice " + b"y" * 150

        result = await agent.process_file(
            file_content=jpg_content,
            filename="fattura_scan.jpg",
            content_type="image/jpeg",
            tenant_id=tenant.id,
        )

        assert result["success"] is True
        assert "fields" in result
        assert "numero_fattura" in result["fields"]
        assert "importo_totale" in result["fields"]
        assert "emittente_piva" in result["fields"]

    async def test_ac_091_ocr_processing_time(self, db_session: AsyncSession, tenant: Tenant):
        """AC-09.1: DATO un file, QUANDO esegue OCR,
        ALLORA completa in <= 10 secondi."""
        agent = OCRAgent(db_session)
        content = b"%PDF-1.4 performance test " + b"a" * 100

        result = await agent.process_file(
            file_content=content,
            filename="perf_test.pdf",
            content_type="application/pdf",
            tenant_id=tenant.id,
        )

        assert result["processing_time_ms"] < 10_000  # < 10s

    async def test_ac_091_ocr_adapter_directly(self):
        """AC-09.1: Test OCR adapter directly returns per-field confidence."""
        adapter = CloudVisionOCRAdapter()
        result = await adapter.extract_invoice_data(
            file_content=b"mock pdf content " + b"z" * 100,
            filename="test.pdf",
            content_type="application/pdf",
        )

        assert result.success is True
        assert result.overall_accuracy > 0
        assert len(result.fields) > 0
        for f in result.fields:
            assert f.field_name
            assert f.value
            assert 0.0 <= f.confidence <= 1.0


# ============================================================
# AC-09.2 — Confidence <60% -> "verifica richiesta",
#            campi evidenziati
# ============================================================


class TestAC092LowConfidence:
    """AC-09.2: Low confidence fields trigger review request."""

    async def test_ac_092_low_confidence_needs_review(self):
        """AC-09.2: DATO un campo con confidence < 60%,
        QUANDO OCR completa, ALLORA status 'verifica richiesta' e campi evidenziati."""
        adapter = CloudVisionOCRAdapter()

        # Try various content sizes to find one that produces low confidence
        # The mock uses seed = len(content) % 1000 with 15% chance of low confidence
        found_low = False
        for size in range(50, 500):
            content = b"x" * size
            result = await adapter.extract_invoice_data(
                file_content=content,
                filename="test.pdf",
                content_type="application/pdf",
            )
            if result.needs_review:
                found_low = True
                assert len(result.review_fields) > 0
                # Review fields should have confidence < 60%
                low_fields = {f.field_name: f.confidence for f in result.fields
                              if f.confidence < 0.60}
                for rf in result.review_fields:
                    assert rf in low_fields
                break

        assert found_low, "Should find at least one input that produces low-confidence fields"

    async def test_ac_092_invoice_status_verifica_richiesta(
        self, db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-09.2: DATO OCR con bassa confidence,
        QUANDO crea record fattura, ALLORA status = verifica_richiesta."""
        agent = OCRAgent(db_session)

        # Find content that triggers low confidence
        for size in range(50, 500):
            content = b"x" * size
            try:
                result = await agent.process_file(
                    file_content=content,
                    filename="low_conf.pdf",
                    content_type="application/pdf",
                    tenant_id=tenant.id,
                )
                if result["needs_review"]:
                    assert len(result["review_fields"]) > 0
                    # Verify all review fields have confidence < 60%
                    for rf in result["review_fields"]:
                        assert result["confidence_scores"][rf] < 0.60
                    return
            except ValueError:
                continue

        pytest.fail("Could not generate low-confidence OCR result in test range")


# ============================================================
# AC-09.3 — File non leggibile (PDF protetto, immagine corrotta)
#            -> errore specifico
# ============================================================


class TestAC093FileNonLeggibile:
    """AC-09.3: Unreadable files return specific errors."""

    async def test_ac_093_pdf_protetto(self, db_session: AsyncSession, tenant: Tenant):
        """AC-09.3: DATO un PDF protetto da password,
        QUANDO tenta OCR, ALLORA errore specifico 'PDF protetto'."""
        agent = OCRAgent(db_session)
        agent.ocr.set_fail_mode("protected_pdf")

        with pytest.raises(ValueError, match="PDF protetto da password"):
            await agent.process_file(
                file_content=b"encrypted pdf content",
                filename="protected.pdf",
                content_type="application/pdf",
                tenant_id=tenant.id,
            )

    async def test_ac_093_immagine_corrotta(self, db_session: AsyncSession, tenant: Tenant):
        """AC-09.3: DATO un'immagine corrotta,
        QUANDO tenta OCR, ALLORA errore specifico 'immagine corrotta'."""
        agent = OCRAgent(db_session)
        agent.ocr.set_fail_mode("corrupted_image")

        with pytest.raises(ValueError, match="[Ii]mmagine corrotta"):
            await agent.process_file(
                file_content=b"corrupted data",
                filename="broken.jpg",
                content_type="image/jpeg",
                tenant_id=tenant.id,
            )

    async def test_ac_093_file_troppo_piccolo(self):
        """AC-09.3: DATO un file vuoto/troppo piccolo,
        QUANDO tenta OCR, ALLORA errore specifico."""
        adapter = CloudVisionOCRAdapter()

        with pytest.raises(ValueError, match="[Ii]mmagine corrotta"):
            await adapter.extract_invoice_data(
                file_content=b"tiny",
                filename="empty.png",
                content_type="image/png",
            )

    async def test_ac_093_formato_non_supportato_ocr(self):
        """AC-09.3: DATO un formato non supportato per OCR,
        QUANDO tenta OCR, ALLORA errore specifico."""
        adapter = CloudVisionOCRAdapter()

        with pytest.raises(ValueError, match="non supportato"):
            await adapter.extract_invoice_data(
                file_content=b"word doc content " + b"a" * 100,
                filename="document.doc",
                content_type="application/msword",
            )


# ============================================================
# AC-09.4 — Email con piu allegati -> crea record per ciascuna
# ============================================================


class TestAC094MultipleAttachments:
    """AC-09.4: Multiple attachments create separate invoice records."""

    async def test_ac_094_multi_allegati_crea_record(
        self, db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-09.4: DATO un'email con 3 allegati fattura,
        QUANDO processa, ALLORA crea 3 record separati."""
        agent = OCRAgent(db_session)

        attachments = [
            {
                "filename": "fattura_1.pdf",
                "content_type": "application/pdf",
                "content": b"%PDF-1.4 fattura uno " + b"a" * 100,
            },
            {
                "filename": "fattura_2.jpg",
                "content_type": "image/jpeg",
                "content": b"\xff\xd8\xff fattura due " + b"b" * 150,
            },
            {
                "filename": "fattura_3.png",
                "content_type": "image/png",
                "content": b"\x89PNG fattura tre " + b"c" * 200,
            },
        ]

        results = await agent.process_email_attachments(
            attachments=attachments,
            tenant_id=tenant.id,
        )

        assert len(results) == 3
        for r in results:
            assert r["invoice_id"] is not None
            assert r["filename"] in ("fattura_1.pdf", "fattura_2.jpg", "fattura_3.png")
            assert r["overall_accuracy"] > 0

    async def test_ac_094_allegato_con_errore_non_blocca_altri(
        self, db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-09.4: DATO un allegato corrotto tra altri validi,
        QUANDO processa, ALLORA i validi vengono elaborati, il corrotto segnalato."""
        agent = OCRAgent(db_session)

        attachments = [
            {
                "filename": "fattura_ok.pdf",
                "content_type": "application/pdf",
                "content": b"%PDF-1.4 good content " + b"x" * 100,
            },
            {
                "filename": "fattura_bad.pdf",
                "content_type": "application/pdf",
                "content": b"tiny",  # Too small, will fail
            },
            {
                "filename": "fattura_ok2.png",
                "content_type": "image/png",
                "content": b"\x89PNG valid image " + b"y" * 120,
            },
        ]

        results = await agent.process_email_attachments(
            attachments=attachments,
            tenant_id=tenant.id,
        )

        assert len(results) == 3

        # First and third should succeed
        assert results[0]["invoice_id"] is not None
        assert results[0]["status"] != "error"

        # Second should fail
        assert results[1]["invoice_id"] is None
        assert results[1]["status"] == "error"
        assert results[1]["error"] is not None

        # Third should succeed
        assert results[2]["invoice_id"] is not None
        assert results[2]["status"] != "error"

    async def test_ac_094_multi_attachment_processor_standalone(self):
        """AC-09.4: Test MultiAttachmentProcessor independently."""
        adapter = CloudVisionOCRAdapter()
        processor = MultiAttachmentProcessor(adapter)

        attachments = [
            {
                "filename": "inv1.pdf",
                "content_type": "application/pdf",
                "content": b"pdf content one " + b"a" * 50,
            },
            {
                "filename": "inv2.pdf",
                "content_type": "application/pdf",
                "content": b"pdf content two " + b"b" * 60,
            },
        ]

        results = await processor.process_attachments(attachments)
        assert len(results) == 2
        assert all(r.success for r in results)
