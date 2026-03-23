"""
Test suite for US-15: Dashboard scritture contabili
Tests for 5 Acceptance Criteria (AC-15.1 through AC-15.5)
"""

import uuid
from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import Invoice, JournalEntry, JournalLine, Tenant, User
from tests.conftest import create_invoice, get_auth_token


# ============================================================
# AC-15.1 — Lista scritture dare/avere
# ============================================================


class TestAC151ListaScritture:
    """AC-15.1: Lista scritture con dare/avere, data, descrizione, conti, importi, link fattura."""

    async def test_ac_151_lista_scritture(
        self,
        client: AsyncClient,
        spid_auth_headers: dict,
        db_session: AsyncSession,
        tenant: Tenant,
        journal_entry_in_db: JournalEntry,
    ):
        """AC-15.1: DATO scritture presenti,
        QUANDO lista scritture, ALLORA dare/avere con dettagli."""
        response = await client.get(
            "/api/v1/accounting/journal-entries",
            headers=spid_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        assert data["total"] >= 1
        assert len(data["items"]) >= 1

        entry = data["items"][0]
        assert "total_debit" in entry
        assert "total_credit" in entry
        assert "description" in entry
        assert "entry_date" in entry
        assert "invoice_id" in entry
        assert "status" in entry

    async def test_ac_151_entry_detail_with_lines(
        self,
        client: AsyncClient,
        spid_auth_headers: dict,
        db_session: AsyncSession,
        tenant: Tenant,
        journal_entry_in_db: JournalEntry,
    ):
        """AC-15.1: Entry detail includes journal lines with account codes and amounts."""
        response = await client.get(
            f"/api/v1/accounting/journal-entries/{journal_entry_in_db.id}",
            headers=spid_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        assert data["id"] == str(journal_entry_in_db.id)
        assert "lines" in data
        assert len(data["lines"]) == 3

        for line in data["lines"]:
            assert "account_code" in line
            assert "account_name" in line
            assert "debit" in line
            assert "credit" in line


# ============================================================
# AC-15.2 — Quadratura dare=avere sempre
# ============================================================


class TestAC152Quadratura:
    """AC-15.2: Total debit always equals total credit."""

    async def test_ac_152_quadratura(
        self,
        client: AsyncClient,
        spid_auth_headers: dict,
        db_session: AsyncSession,
        tenant: Tenant,
        journal_entry_in_db: JournalEntry,
    ):
        """AC-15.2: DATO scritture contabili,
        QUANDO visualizzo, ALLORA dare == avere sempre."""
        response = await client.get(
            f"/api/v1/accounting/journal-entries/{journal_entry_in_db.id}",
            headers=spid_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        assert data["total_debit"] == data["total_credit"]

        # Also verify summing the lines
        total_d = sum(line["debit"] for line in data["lines"])
        total_c = sum(line["credit"] for line in data["lines"])
        assert abs(total_d - total_c) < 0.01


# ============================================================
# AC-15.3 — Scrittura con errore Odoo → stato "Errore" con messaggio
# ============================================================


class TestAC153ErroreOdoo:
    """AC-15.3: Error entries show error state with message."""

    async def test_ac_153_errore_odoo(
        self,
        client: AsyncClient,
        spid_auth_headers: dict,
        db_session: AsyncSession,
        tenant: Tenant,
    ):
        """AC-15.3: DATO scrittura con errore,
        QUANDO visualizzo, ALLORA stato 'error' con messaggio."""
        # Create an error entry
        error_entry = JournalEntry(
            tenant_id=tenant.id,
            description="Fattura FT-ERR-001 - Errore Odoo",
            entry_date=date(2025, 3, 15),
            total_debit=0.0,
            total_credit=0.0,
            status="error",
            error_message="Errore connessione Odoo: timeout dopo 30s",
        )
        db_session.add(error_entry)
        await db_session.flush()

        response = await client.get(
            f"/api/v1/accounting/journal-entries/{error_entry.id}",
            headers=spid_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "error"
        assert data["error_message"] is not None
        assert "odoo" in data["error_message"].lower() or "errore" in data["error_message"].lower()


# ============================================================
# AC-15.4 — Empty state → "Nessuna scrittura" con link a "da verificare"
# ============================================================


class TestAC154EmptyState:
    """AC-15.4: Empty state when no journal entries exist."""

    async def test_ac_154_empty_state(
        self,
        client: AsyncClient,
        spid_auth_headers: dict,
    ):
        """AC-15.4: DATO nessuna scrittura,
        QUANDO lista scritture, ALLORA 'Nessuna scrittura' con link da verificare."""
        response = await client.get(
            "/api/v1/accounting/journal-entries",
            headers=spid_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 0
        assert len(data["items"]) == 0
        assert "nessuna" in data["message"].lower()


# ============================================================
# AC-15.5 — Filtro per periodo contabile
# ============================================================


class TestAC155FiltroPeriodo:
    """AC-15.5: Filter journal entries by accounting period."""

    async def test_ac_155_filtro_periodo(
        self,
        client: AsyncClient,
        spid_auth_headers: dict,
        db_session: AsyncSession,
        tenant: Tenant,
    ):
        """AC-15.5: DATO scritture in diversi periodi,
        QUANDO filtro per periodo, ALLORA solo scritture del periodo."""
        # Create entries in different periods
        entry_jan = JournalEntry(
            tenant_id=tenant.id,
            description="Fattura gennaio",
            entry_date=date(2025, 1, 15),
            total_debit=1000.0,
            total_credit=1000.0,
            status="posted",
        )
        entry_mar = JournalEntry(
            tenant_id=tenant.id,
            description="Fattura marzo",
            entry_date=date(2025, 3, 20),
            total_debit=2000.0,
            total_credit=2000.0,
            status="posted",
        )
        entry_jun = JournalEntry(
            tenant_id=tenant.id,
            description="Fattura giugno",
            entry_date=date(2025, 6, 1),
            total_debit=3000.0,
            total_credit=3000.0,
            status="posted",
        )
        db_session.add_all([entry_jan, entry_mar, entry_jun])
        await db_session.flush()

        # Filter Q1
        response = await client.get(
            "/api/v1/accounting/journal-entries?date_from=2025-01-01&date_to=2025-03-31",
            headers=spid_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

        # Filter only March
        response = await client.get(
            "/api/v1/accounting/journal-entries?date_from=2025-03-01&date_to=2025-03-31",
            headers=spid_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["description"] == "Fattura marzo"

        # Filter by status
        response = await client.get(
            "/api/v1/accounting/journal-entries?status=posted",
            headers=spid_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
