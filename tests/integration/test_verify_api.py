"""
Test suite for US-11: Verifica e correzione categoria
Tests for 5 Acceptance Criteria (AC-11.1 through AC-11.5)
"""

import uuid
from datetime import date, datetime, UTC

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import CategorizationFeedback, Invoice, Tenant, User
from tests.conftest import create_invoice, get_auth_token


# ============================================================
# AC-11.1 — Conferma categoria
# ============================================================


class TestAC111ConfermaCategoria:
    """AC-11.1: Conferma categoria marca verified, feedback positivo, passa a registrazione."""

    async def test_ac_111_conferma_categoria(
        self,
        client: AsyncClient,
        spid_auth_headers: dict,
        db_session: AsyncSession,
        tenant: Tenant,
        categorized_invoice: Invoice,
    ):
        """AC-11.1: DATO fattura categorizzata non verificata,
        QUANDO conferma categoria, ALLORA verified=True, feedback positivo."""
        response = await client.patch(
            f"/api/v1/invoices/{categorized_invoice.id}/verify",
            json={"category": "Consulenze", "confirmed": True},
            headers=spid_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        assert data["verified"] is True
        assert data["was_correct"] is True
        assert data["category"] == "Consulenze"
        assert "confermata" in data["message"].lower()

        # Verify in DB
        await db_session.refresh(categorized_invoice)
        assert categorized_invoice.verified is True
        assert categorized_invoice.category == "Consulenze"
        assert categorized_invoice.category_confidence == 1.0

    async def test_ac_111_feedback_created(
        self,
        client: AsyncClient,
        spid_auth_headers: dict,
        db_session: AsyncSession,
        tenant: Tenant,
        categorized_invoice: Invoice,
    ):
        """AC-11.1: Feedback record created with was_correct=True."""
        await client.patch(
            f"/api/v1/invoices/{categorized_invoice.id}/verify",
            json={"category": "Consulenze", "confirmed": True},
            headers=spid_auth_headers,
        )

        result = await db_session.execute(
            select(CategorizationFeedback).where(
                CategorizationFeedback.invoice_id == categorized_invoice.id
            )
        )
        feedback = result.scalar_one_or_none()
        assert feedback is not None
        assert feedback.was_correct is True
        assert feedback.final_category == "Consulenze"


# ============================================================
# AC-11.2 — Correzione categoria
# ============================================================


class TestAC112CorrezioneCategoria:
    """AC-11.2: Correzione categoria aggiorna, feedback negativo, passa a registrazione."""

    async def test_ac_112_correzione_categoria(
        self,
        client: AsyncClient,
        spid_auth_headers: dict,
        db_session: AsyncSession,
        tenant: Tenant,
        categorized_invoice: Invoice,
    ):
        """AC-11.2: DATO fattura categorizzata come 'Consulenze',
        QUANDO correggo a 'Utenze', ALLORA aggiornata, feedback negativo."""
        response = await client.patch(
            f"/api/v1/invoices/{categorized_invoice.id}/verify",
            json={"category": "Utenze", "confirmed": False},
            headers=spid_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        assert data["verified"] is True
        assert data["was_correct"] is False
        assert data["category"] == "Utenze"
        assert "aggiornata" in data["message"].lower()

        # Verify in DB
        await db_session.refresh(categorized_invoice)
        assert categorized_invoice.category == "Utenze"
        assert categorized_invoice.verified is True

    async def test_ac_112_feedback_negativo(
        self,
        client: AsyncClient,
        spid_auth_headers: dict,
        db_session: AsyncSession,
        tenant: Tenant,
        categorized_invoice: Invoice,
    ):
        """AC-11.2: Feedback record created with was_correct=False."""
        await client.patch(
            f"/api/v1/invoices/{categorized_invoice.id}/verify",
            json={"category": "Utenze", "confirmed": False},
            headers=spid_auth_headers,
        )

        result = await db_session.execute(
            select(CategorizationFeedback).where(
                CategorizationFeedback.invoice_id == categorized_invoice.id
            )
        )
        feedback = result.scalar_one_or_none()
        assert feedback is not None
        assert feedback.was_correct is False
        assert feedback.suggested_category == "Consulenze"
        assert feedback.final_category == "Utenze"


# ============================================================
# AC-11.3 — Categoria non in piano conti → suggerisce 3 simili
# ============================================================


class TestAC113CategoriaSuggerita:
    """AC-11.3: Categoria non nel piano conti suggerisce 3 categorie simili."""

    async def test_ac_113_categoria_suggerita(
        self,
        client: AsyncClient,
        spid_auth_headers: dict,
        db_session: AsyncSession,
        tenant: Tenant,
        categorized_invoice: Invoice,
    ):
        """AC-11.3: DATO fattura con categoria sconosciuta,
        QUANDO richiedo suggerimenti, ALLORA 3 categorie simili."""
        # Change category to something not in piano conti
        categorized_invoice.category = "Consulent"  # Typo/unknown
        await db_session.flush()

        response = await client.get(
            f"/api/v1/invoices/{categorized_invoice.id}/suggest-categories",
            headers=spid_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        assert "suggestions" in data
        assert len(data["suggestions"]) == 3
        # "Consulenze" should be among the top suggestions for "Consulent"
        assert "Consulenze" in data["suggestions"]


# ============================================================
# AC-11.4 — Verifica batch → lista "da verificare" con conteggio
# ============================================================


class TestAC114ListaDaVerificare:
    """AC-11.4: Lista fatture 'da verificare' con conteggio."""

    async def test_ac_114_lista_da_verificare(
        self,
        client: AsyncClient,
        spid_auth_headers: dict,
        db_session: AsyncSession,
        tenant: Tenant,
    ):
        """AC-11.4: DATO fatture categorizzate non verificate,
        QUANDO lista da verificare, ALLORA elenco con conteggio."""
        # Create 3 categorized + unverified invoices
        for i in range(3):
            inv = create_invoice(
                tenant_id=tenant.id,
                numero=f"FT-REVIEW-{i:03d}",
                piva=f"IT{70000000000 + i}",
                nome=f"Fornitore Review {i}",
                category="Consulenze",
                verified=False,
                status="categorized",
            )
            db_session.add(inv)

        # Create 1 verified (should not appear)
        verified = create_invoice(
            tenant_id=tenant.id,
            numero="FT-ALREADY-VER",
            piva="IT70000000099",
            nome="Fornitore Verified",
            category="Utenze",
            verified=True,
            status="categorized",
        )
        db_session.add(verified)
        await db_session.flush()

        response = await client.get(
            "/api/v1/invoices/pending-review",
            headers=spid_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 3
        assert len(data["items"]) == 3
        for item in data["items"]:
            assert item["verified"] is False
            assert item["category"] is not None


# ============================================================
# AC-11.5 — Verifica concorrente → last-write-wins con timestamp
# ============================================================


class TestAC115VerificaConcorrente:
    """AC-11.5: Verifica concorrente con last-write-wins."""

    async def test_ac_115_verifica_concorrente(
        self,
        client: AsyncClient,
        spid_auth_headers: dict,
        db_session: AsyncSession,
        tenant: Tenant,
        categorized_invoice: Invoice,
    ):
        """AC-11.5: DATO due utenti che verificano la stessa fattura,
        QUANDO verifica concorrente, ALLORA l'ultimo vince."""
        # First verification
        resp1 = await client.patch(
            f"/api/v1/invoices/{categorized_invoice.id}/verify",
            json={"category": "Utenze", "confirmed": False},
            headers=spid_auth_headers,
        )
        assert resp1.status_code == 200

        # Second verification (last-write-wins)
        resp2 = await client.patch(
            f"/api/v1/invoices/{categorized_invoice.id}/verify",
            json={"category": "Servizi", "confirmed": False},
            headers=spid_auth_headers,
        )
        assert resp2.status_code == 200

        # Last write wins
        await db_session.refresh(categorized_invoice)
        assert categorized_invoice.category == "Servizi"
        assert categorized_invoice.verified is True
