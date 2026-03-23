"""
Test suite for US-06: Upload manuale fattura
Tests for 4 Acceptance Criteria (AC-06.1 through AC-06.4)
"""

import io

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import Invoice, Tenant, User
from tests.conftest import create_invoice, get_auth_token


# ============================================================
# AC-06.1 — Upload PDF/JPG/PNG/XML (max 10MB)
# ============================================================


class TestAC061UploadFormatiSupportati:
    """AC-06.1: Upload file nei formati supportati (PDF, JPG, PNG, XML)."""

    async def test_ac_061_upload_pdf(
        self, client: AsyncClient, auth_headers: dict
    ):
        """AC-06.1: DATO utente autenticato, QUANDO upload PDF,
        ALLORA file accettato e fattura creata con status pending (OCR)."""
        file_content = b"%PDF-1.4 fake pdf content"
        response = await client.post(
            "/api/v1/invoices/upload",
            headers=auth_headers,
            files={"file": ("fattura.pdf", io.BytesIO(file_content), "application/pdf")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["file_type"] == "pdf"
        assert data["source"] == "upload"
        assert data["processing_status"] == "pending"
        assert "OCR" in data["message"]

    async def test_ac_061_upload_jpg(
        self, client: AsyncClient, auth_headers: dict
    ):
        """AC-06.1: DATO utente autenticato, QUANDO upload JPG,
        ALLORA file accettato."""
        file_content = b"\xff\xd8\xff\xe0 fake jpg"
        response = await client.post(
            "/api/v1/invoices/upload",
            headers=auth_headers,
            files={"file": ("fattura.jpg", io.BytesIO(file_content), "image/jpeg")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["file_type"] == "jpg"
        assert data["source"] == "upload"

    async def test_ac_061_upload_png(
        self, client: AsyncClient, auth_headers: dict
    ):
        """AC-06.1: DATO utente autenticato, QUANDO upload PNG,
        ALLORA file accettato."""
        file_content = b"\x89PNG fake png"
        response = await client.post(
            "/api/v1/invoices/upload",
            headers=auth_headers,
            files={"file": ("fattura.png", io.BytesIO(file_content), "image/png")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["file_type"] == "png"

    async def test_ac_061_upload_xml(
        self, client: AsyncClient, auth_headers: dict, sample_fattura_xml: str
    ):
        """AC-06.1: DATO utente autenticato, QUANDO upload XML FatturaPA,
        ALLORA file parsato e fattura creata con status parsed."""
        response = await client.post(
            "/api/v1/invoices/upload",
            headers=auth_headers,
            files={"file": ("fattura.xml", io.BytesIO(sample_fattura_xml.encode()), "application/xml")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["file_type"] == "xml"
        assert data["processing_status"] == "parsed"
        assert "parsata" in data["message"] or "caricata" in data["message"]


# ============================================================
# AC-06.2 — Formato non supportato
# ============================================================


class TestAC062FormatoNonSupportato:
    """AC-06.2: Upload di formato non supportato viene rifiutato."""

    async def test_ac_062_upload_doc_rifiutato(
        self, client: AsyncClient, auth_headers: dict
    ):
        """AC-06.2: DATO utente autenticato, QUANDO upload .doc,
        ALLORA errore formato non supportato."""
        file_content = b"fake doc content"
        response = await client.post(
            "/api/v1/invoices/upload",
            headers=auth_headers,
            files={"file": ("fattura.doc", io.BytesIO(file_content), "application/msword")},
        )
        assert response.status_code == 400
        assert "formato" in response.json()["detail"].lower() or "supportato" in response.json()["detail"].lower()

    async def test_ac_062_upload_exe_rifiutato(
        self, client: AsyncClient, auth_headers: dict
    ):
        """AC-06.2: DATO utente autenticato, QUANDO upload .exe,
        ALLORA errore formato non supportato."""
        response = await client.post(
            "/api/v1/invoices/upload",
            headers=auth_headers,
            files={"file": ("malware.exe", io.BytesIO(b"MZ"), "application/octet-stream")},
        )
        assert response.status_code == 400
        assert "formato" in response.json()["detail"].lower() or "supportato" in response.json()["detail"].lower()


# ============================================================
# AC-06.3 — File troppo grande
# ============================================================


class TestAC063FileTroppoGrande:
    """AC-06.3: File > 10MB viene rifiutato."""

    async def test_ac_063_file_troppo_grande(
        self, client: AsyncClient, auth_headers: dict
    ):
        """AC-06.3: DATO utente autenticato, QUANDO upload file > 10MB,
        ALLORA errore file troppo grande."""
        # Create a file just over 10MB
        big_content = b"x" * (10 * 1024 * 1024 + 1)
        response = await client.post(
            "/api/v1/invoices/upload",
            headers=auth_headers,
            files={"file": ("big.pdf", io.BytesIO(big_content), "application/pdf")},
        )
        assert response.status_code == 400
        assert "grande" in response.json()["detail"].lower() or "10" in response.json()["detail"]


# ============================================================
# AC-06.4 — Dedup upload
# ============================================================


class TestAC064DedupUpload:
    """AC-06.4: Fattura duplicata viene segnalata."""

    async def test_ac_064_dedup_xml_upload(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sample_fattura_xml: str,
        db_session: AsyncSession,
        tenant: Tenant,
    ):
        """AC-06.4: DATO fattura gia presente, QUANDO upload stessa fattura XML,
        ALLORA segnalata come duplicata."""
        # Pre-insert the invoice that the XML would create
        existing = create_invoice(
            tenant_id=tenant.id,
            numero="FT-2025-0001",
            piva="IT01234567890",
            nome="Fornitore Alpha SRL",
            source="cassetto_fiscale",
            data=None,
        )
        existing.data_fattura = __import__("datetime").date(2025, 1, 15)
        db_session.add(existing)
        await db_session.flush()

        # Upload same invoice as XML
        response = await client.post(
            "/api/v1/invoices/upload",
            headers=auth_headers,
            files={"file": ("fattura.xml", io.BytesIO(sample_fattura_xml.encode()), "application/xml")},
        )
        assert response.status_code == 200
        data = response.json()
        assert "duplicata" in data["message"].lower() or "gia presente" in data["message"].lower()
