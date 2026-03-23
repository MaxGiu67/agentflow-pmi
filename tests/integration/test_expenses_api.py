"""
Test suite for US-29: Note spese — upload e categorizzazione
Tests for 4 Acceptance Criteria (AC-29.1 through AC-29.4)
"""

import uuid
from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import Expense, ExpensePolicy, Tenant, User


# ============================================================
# AC-29.1 — Upload scontrino -> OCR -> propone categoria
# ============================================================


class TestAC291OcrCategoria:
    """AC-29.1: Upload scontrino -> OCR -> propone categoria."""

    async def test_ac_291_ocr_proposes_category_pranzo(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-29.1: DATO scontrino con testo 'Ristorante Da Mario',
        QUANDO upload con OCR text,
        ALLORA categoria proposta = 'Pranzo'."""
        resp = await client.post(
            "/api/v1/expenses",
            json={
                "description": "Pranzo di lavoro",
                "amount": 22.50,
                "expense_date": "2026-03-20",
                "receipt_file": "scontrino_001.jpg",
                "ocr_text": "Ristorante Da Mario - Totale EUR 22,50",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["category"] == "Pranzo"
        assert data["category_confidence"] is not None
        assert data["category_confidence"] >= 0.8

    async def test_ac_291_ocr_proposes_category_trasporto(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-29.1: DATO scontrino taxi,
        QUANDO upload, ALLORA categoria = Trasporto."""
        resp = await client.post(
            "/api/v1/expenses",
            json={
                "description": "Taxi per appuntamento",
                "amount": 35.00,
                "expense_date": "2026-03-20",
                "ocr_text": "Taxi Milano - Corsa EUR 35,00",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["category"] == "Trasporto"

    async def test_ac_291_manual_category_overrides_ocr(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-29.1: DATO categoria fornita manualmente,
        QUANDO upload, ALLORA usa la categoria manuale."""
        resp = await client.post(
            "/api/v1/expenses",
            json={
                "description": "Pranzo di lavoro",
                "amount": 22.50,
                "expense_date": "2026-03-20",
                "category": "Rappresentanza",
                "ocr_text": "Ristorante qualcosa",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["category"] == "Rappresentanza"
        assert data["category_confidence"] == 1.0


# ============================================================
# AC-29.2 — Policy spesa (max EUR 25/pranzo) -> warning
# ============================================================


class TestAC292PolicySpesa:
    """AC-29.2: Policy spesa (max EUR 25/pranzo) -> warning se supera."""

    async def test_ac_292_policy_warning_over_limit(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-29.2: DATO policy max 25 EUR per Pranzo,
        QUANDO spesa 30 EUR per Pranzo,
        ALLORA warning supera limite."""
        # Create policy
        policy = ExpensePolicy(
            tenant_id=tenant.id,
            category="Pranzo",
            max_amount=25.0,
            description="Max pranzo 25 EUR",
        )
        db_session.add(policy)
        await db_session.flush()

        resp = await client.post(
            "/api/v1/expenses",
            json={
                "description": "Pranzo costoso",
                "amount": 30.0,
                "expense_date": "2026-03-20",
                "category": "Pranzo",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["policy_warning"] is not None
        assert "25.00" in data["policy_warning"]
        assert "30.00" in data["policy_warning"]

    async def test_ac_292_no_warning_under_limit(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-29.2: DATO policy max 25 EUR per Pranzo,
        QUANDO spesa 20 EUR per Pranzo,
        ALLORA nessun warning."""
        policy = ExpensePolicy(
            tenant_id=tenant.id,
            category="Pranzo",
            max_amount=25.0,
        )
        db_session.add(policy)
        await db_session.flush()

        resp = await client.post(
            "/api/v1/expenses",
            json={
                "description": "Pranzo normale",
                "amount": 20.0,
                "expense_date": "2026-03-20",
                "category": "Pranzo",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["policy_warning"] is None


# ============================================================
# AC-29.3 — Scontrino illeggibile -> inserimento manuale
# ============================================================


class TestAC293ScontrinoIlleggibile:
    """AC-29.3: Scontrino illeggibile -> inserimento manuale."""

    async def test_ac_293_no_ocr_text_marks_unreadable(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-29.3: DATO scontrino con receipt_file ma senza ocr_text,
        QUANDO upload, ALLORA ocr_readable = False."""
        resp = await client.post(
            "/api/v1/expenses",
            json={
                "description": "Spesa manuale",
                "amount": 15.0,
                "expense_date": "2026-03-20",
                "receipt_file": "scontrino_illeggibile.jpg",
                "category": "Pranzo",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ocr_readable"] is False

    async def test_ac_293_manual_entry_without_receipt(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-29.3: DATO inserimento manuale senza scontrino,
        QUANDO upload, ALLORA spesa creata con categoria manuale."""
        resp = await client.post(
            "/api/v1/expenses",
            json={
                "description": "Spesa senza scontrino",
                "amount": 10.0,
                "expense_date": "2026-03-20",
                "category": "Trasporto",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "submitted"
        assert data["category"] == "Trasporto"


# ============================================================
# AC-29.4 — Spesa in valuta estera -> conversione BCE
# ============================================================


class TestAC294ValutaEstera:
    """AC-29.4: Spesa in valuta estera -> conversione BCE."""

    async def test_ac_294_usd_conversion(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-29.4: DATO spesa 50 USD,
        QUANDO upload, ALLORA amount_eur calcolato con tasso BCE."""
        resp = await client.post(
            "/api/v1/expenses",
            json={
                "description": "Pranzo a New York",
                "amount": 50.0,
                "currency": "USD",
                "expense_date": "2026-03-20",
                "category": "Pranzo",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["currency"] == "USD"
        assert data["amount"] == 50.0
        assert data["exchange_rate"] == 1.08  # USD rate
        assert data["amount_eur"] == round(50.0 / 1.08, 2)

    async def test_ac_294_gbp_conversion(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-29.4: DATO spesa in GBP,
        QUANDO upload, ALLORA conversione BCE."""
        resp = await client.post(
            "/api/v1/expenses",
            json={
                "description": "Taxi Londra",
                "amount": 30.0,
                "currency": "GBP",
                "expense_date": "2026-03-20",
                "category": "Trasporto",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["currency"] == "GBP"
        assert data["exchange_rate"] == 0.86
        assert data["amount_eur"] == round(30.0 / 0.86, 2)

    async def test_ac_294_eur_no_conversion(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-29.4: DATO spesa in EUR,
        QUANDO upload, ALLORA no conversione."""
        resp = await client.post(
            "/api/v1/expenses",
            json={
                "description": "Pranzo Roma",
                "amount": 25.0,
                "expense_date": "2026-03-20",
                "category": "Pranzo",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["currency"] == "EUR"
        assert data["exchange_rate"] is None
        assert data["amount_eur"] == 25.0

    async def test_ac_294_unsupported_currency_error(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-29.4: DATO valuta non supportata,
        QUANDO upload, ALLORA errore."""
        resp = await client.post(
            "/api/v1/expenses",
            json={
                "description": "Spesa in Bitcoin",
                "amount": 0.01,
                "currency": "BTC",
                "expense_date": "2026-03-20",
                "category": "Altro",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 400
