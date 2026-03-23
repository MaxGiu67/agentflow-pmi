"""
Test suite for US-36: Ratei e risconti
Tests for 4 Acceptance Criteria (AC-36.1 through AC-36.4)
"""

import uuid
from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import Accrual, Invoice, Tenant, User


# ============================================================
# AC-36.1 — Identificazione costi pluriennali -> propone risconto
# ============================================================


class TestAC361Risconto:
    """AC-36.1: Identificazione costi pluriennali -> propone risconto."""

    async def test_ac_361_insurance_9_12_deferral(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-36.1: DATO assicurazione 1200 EUR dal 01/04/2026 al 31/03/2027,
        QUANDO propose, ALLORA risconto calcolato pro-rata giorni.
        275 giorni in 2026 (apr-dic) su 365 totali -> quota anno corrente ~904 EUR,
        quota rinviata ~296 EUR."""
        resp = await client.post(
            "/api/v1/fiscal/accruals/propose",
            json={
                "description": "Assicurazione RC annuale",
                "total_amount": 1200.0,
                "period_start": "2026-04-01",
                "period_end": "2027-03-31",
                "fiscal_year": 2026,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["type"] == "risconto_attivo"
        assert data["total_amount"] == 1200.0
        # Day-based: 275/365 of 1200 for current year, remainder deferred
        assert data["current_year_amount"] == pytest.approx(904.11, abs=2.0)
        assert data["deferred_amount"] == pytest.approx(295.89, abs=2.0)
        assert data["current_year_amount"] + data["deferred_amount"] == 1200.0
        assert data["status"] == "proposed"

    async def test_ac_361_full_year_no_deferral(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-36.1: DATO costo interamente nell'anno corrente,
        QUANDO propose, ALLORA quota anno corrente = totale."""
        resp = await client.post(
            "/api/v1/fiscal/accruals/propose",
            json={
                "description": "Abbonamento software annuale",
                "total_amount": 600.0,
                "period_start": "2026-01-01",
                "period_end": "2026-12-31",
                "fiscal_year": 2026,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["current_year_amount"] == 600.0
        assert data["deferred_amount"] == 0.0

    async def test_ac_361_linked_to_invoice(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-36.1: DATO risconto collegato a fattura,
        QUANDO propose con invoice_id,
        ALLORA risconto creato con riferimento fattura."""
        inv = Invoice(
            tenant_id=tenant.id,
            type="passiva",
            document_type="TD01",
            source="upload",
            numero_fattura="FT-ASS-001",
            emittente_piva="IT11111111111",
            emittente_nome="Assicurazioni Generali",
            data_fattura=date(2026, 4, 1),
            importo_netto=1200.0,
            importo_iva=0.0,
            importo_totale=1200.0,
            processing_status="registered",
        )
        db_session.add(inv)
        await db_session.flush()

        resp = await client.post(
            "/api/v1/fiscal/accruals/propose",
            json={
                "invoice_id": str(inv.id),
                "period_start": "2026-04-01",
                "period_end": "2027-03-31",
                "fiscal_year": 2026,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["invoice_id"] == str(inv.id)
        assert data["total_amount"] == 1200.0


# ============================================================
# AC-36.2 — Scritture assestamento 31/12 + riapertura 1/1
# ============================================================


class TestAC362ScrittureAssestamento:
    """AC-36.2: Scritture assestamento 31/12 + riapertura 1/1."""

    async def test_ac_362_confirm_generates_entries(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-36.2: DATO risconto proposto,
        QUANDO confirm, ALLORA scrittura 31/12 + riapertura 1/1."""
        accrual = Accrual(
            tenant_id=tenant.id,
            type="risconto_attivo",
            description="Assicurazione RC",
            total_amount=1200.0,
            current_year_amount=300.0,
            deferred_amount=900.0,
            period_start=date(2026, 4, 1),
            period_end=date(2027, 3, 31),
            fiscal_year=2026,
            status="proposed",
        )
        db_session.add(accrual)
        await db_session.flush()

        resp = await client.patch(
            f"/api/v1/fiscal/accruals/{accrual.id}/confirm",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "confirmed"

        # Adjustment entry (31/12)
        adj = data["adjustment_entry"]
        assert adj is not None
        assert "31/12/2026" in adj["description"]
        adj_lines = adj["lines"]
        assert len(adj_lines) == 2
        # DARE Risconti attivi / AVERE Costi
        debit_line = [l for l in adj_lines if l["debit"] > 0][0]
        assert debit_line["account_code"] == "1060"
        assert debit_line["debit"] == 900.0
        credit_line = [l for l in adj_lines if l["credit"] > 0][0]
        assert credit_line["account_code"] == "6100"
        assert credit_line["credit"] == 900.0

        # Reversal entry (01/01)
        rev = data["reversal_entry"]
        assert rev is not None
        assert "01/01/2027" in rev["description"]
        rev_lines = rev["lines"]
        assert len(rev_lines) == 2
        # DARE Costi / AVERE Risconti attivi (reverse)
        debit_line = [l for l in rev_lines if l["debit"] > 0][0]
        assert debit_line["account_code"] == "6100"
        credit_line = [l for l in rev_lines if l["credit"] > 0][0]
        assert credit_line["account_code"] == "1060"

    async def test_ac_362_cannot_confirm_twice(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-36.2: DATO risconto gia confermato,
        QUANDO confirm di nuovo, ALLORA errore."""
        accrual = Accrual(
            tenant_id=tenant.id,
            type="risconto_attivo",
            description="Test doppia conferma",
            total_amount=500.0,
            current_year_amount=250.0,
            deferred_amount=250.0,
            period_start=date(2026, 7, 1),
            period_end=date(2027, 6, 30),
            fiscal_year=2026,
            status="confirmed",
        )
        db_session.add(accrual)
        await db_session.flush()

        resp = await client.patch(
            f"/api/v1/fiscal/accruals/{accrual.id}/confirm",
            headers=auth_headers,
        )
        assert resp.status_code == 400


# ============================================================
# AC-36.3 — Importo non ripartibile -> chiede periodo competenza
# ============================================================


class TestAC363PeriodoCompetenza:
    """AC-36.3: Importo non ripartibile -> chiede periodo competenza."""

    async def test_ac_363_no_period_returns_needs_period(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-36.3: DATO proposta senza periodo,
        QUANDO propose, ALLORA risposta needs_period."""
        resp = await client.post(
            "/api/v1/fiscal/accruals/propose",
            json={
                "description": "Costo non ripartibile",
                "total_amount": 1000.0,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "needs_period"
        assert "periodo" in data["message"].lower()


# ============================================================
# AC-36.4 — Rateo passivo (costo maturato non fatturato)
# ============================================================


class TestAC364RateoPassivo:
    """AC-36.4: Rateo passivo (costo maturato non fatturato)."""

    async def test_ac_364_rateo_passivo_creation(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-36.4: DATO costo maturato ott-mar per 600 EUR,
        QUANDO propose come rateo_passivo,
        ALLORA quota anno corrente (ott-dic) = 300 EUR."""
        resp = await client.post(
            "/api/v1/fiscal/accruals/propose",
            json={
                "description": "Affitto capannone ott-mar",
                "total_amount": 600.0,
                "period_start": "2026-10-01",
                "period_end": "2027-03-31",
                "accrual_type": "rateo_passivo",
                "fiscal_year": 2026,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["type"] == "rateo_passivo"
        assert data["total_amount"] == 600.0
        # Oct-Dec = 3 months out of 6
        assert data["current_year_amount"] == pytest.approx(300.0, abs=5.0)
        assert data["deferred_amount"] == pytest.approx(300.0, abs=5.0)

    async def test_ac_364_rateo_passivo_confirm_entries(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-36.4: DATO rateo passivo proposto,
        QUANDO confirm, ALLORA DARE Costi / AVERE Ratei passivi."""
        accrual = Accrual(
            tenant_id=tenant.id,
            type="rateo_passivo",
            description="Affitto Q4 non fatturato",
            total_amount=600.0,
            current_year_amount=300.0,
            deferred_amount=300.0,
            period_start=date(2026, 10, 1),
            period_end=date(2027, 3, 31),
            fiscal_year=2026,
            status="proposed",
        )
        db_session.add(accrual)
        await db_session.flush()

        resp = await client.patch(
            f"/api/v1/fiscal/accruals/{accrual.id}/confirm",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()

        adj = data["adjustment_entry"]
        assert adj is not None
        lines = adj["lines"]
        # DARE Costi / AVERE Ratei passivi
        debit_line = [l for l in lines if l["debit"] > 0][0]
        assert debit_line["account_code"] == "6100"
        assert debit_line["debit"] == 300.0
        credit_line = [l for l in lines if l["credit"] > 0][0]
        assert credit_line["account_code"] == "2060"
        assert credit_line["credit"] == 300.0

    async def test_ac_364_list_accruals_by_fiscal_year(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-36: DATO ratei in DB, QUANDO list con fiscal_year,
        ALLORA filtrato per anno."""
        a1 = Accrual(
            tenant_id=tenant.id,
            type="risconto_attivo",
            description="Risconto 2026",
            total_amount=1000.0,
            current_year_amount=500.0,
            deferred_amount=500.0,
            period_start=date(2026, 7, 1),
            period_end=date(2027, 6, 30),
            fiscal_year=2026,
            status="proposed",
        )
        a2 = Accrual(
            tenant_id=tenant.id,
            type="rateo_passivo",
            description="Rateo 2025",
            total_amount=300.0,
            current_year_amount=100.0,
            deferred_amount=200.0,
            period_start=date(2025, 10, 1),
            period_end=date(2026, 3, 31),
            fiscal_year=2025,
            status="confirmed",
        )
        db_session.add_all([a1, a2])
        await db_session.flush()

        resp = await client.get(
            "/api/v1/fiscal/accruals?fiscal_year=2026",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["fiscal_year"] == 2026
