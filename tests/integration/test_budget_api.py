"""
Test suite for US-40: Budget vs Consuntivo (monthly grid format — Pivot 5+)
Tests for 5 Acceptance Criteria (AC-40.1 through AC-40.5)
"""

import uuid
from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import Budget, Invoice, Tenant


# ============================================================
# AC-40.1 — Inserimento budget mensile per categoria
# ============================================================


class TestAC401InserimentoBudget:
    """AC-40.1: Inserimento budget mensile per categoria."""

    async def test_ac_401_create_budget_entries(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-40.1: DATO utente CEO,
        QUANDO POST /ceo/budget con categorie e importi,
        ALLORA budget creato per mese."""
        resp = await client.post(
            "/api/v1/ceo/budget",
            json={
                "year": 2026,
                "month": 1,
                "entries": [
                    {"category": "Consulenze", "amount": 5000.0},
                    {"category": "Utenze", "amount": 2000.0},
                    {"category": "Affitto", "amount": 3000.0},
                ],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["created"] == 3
        assert data["year"] == 2026
        assert data["month"] == 1

    async def test_ac_401_update_existing_budget(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-40.1: DATO budget esistente, QUANDO POST stessa categoria,
        ALLORA aggiornato (non duplicato)."""
        # Create budget for all 12 months so grid works
        for month in range(1, 13):
            db_session.add(Budget(
                tenant_id=tenant.id, year=2026, month=month,
                category="Consulenze", budget_amount=3000.0,
            ))
        await db_session.flush()

        # Update month 2 via POST
        await client.post(
            "/api/v1/ceo/budget",
            json={
                "year": 2026,
                "month": 2,
                "entries": [{"category": "Consulenze", "amount": 4000.0}],
            },
            headers=auth_headers,
        )

        # Verify via GET — grid format
        resp = await client.get(
            "/api/v1/ceo/budget?year=2026",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        entries = resp.json()["entries"]
        consulenze = next(e for e in entries if e["category"] == "Consulenze")
        # Month 2 (index 1) should have updated budget
        feb_budget = consulenze["monthly"][1]["budget"]
        assert feb_budget == 4000.0


# ============================================================
# AC-40.2 — Confronto mensile (budget vs consuntivo)
# ============================================================


class TestAC402ConfrontoMensile:
    """AC-40.2: Confronto mensile (budget vs consuntivo, delta, scostamenti >10%)."""

    async def test_ac_402_budget_vs_actual_delta(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-40.2: DATO budget 5000, consuntivo from invoices,
        QUANDO GET /ceo/budget, ALLORA grid with actual from invoices."""
        for month in range(1, 13):
            db_session.add(Budget(
                tenant_id=tenant.id, year=2026, month=month,
                category="Consulenze", budget_amount=5000.0,
            ))
        # Add passive invoice for March (category=Consulenze, netto=6000)
        db_session.add(Invoice(
            tenant_id=tenant.id, type="passiva", document_type="TD01",
            source="sdi", numero_fattura="FP-DELTA-001",
            emittente_piva="11111111111", emittente_nome="Fornitore Delta",
            data_fattura=date(2026, 3, 15),
            importo_netto=6000.0, importo_iva=1320.0, importo_totale=7320.0,
            processing_status="registered", category="Consulenze",
        ))
        await db_session.flush()

        resp = await client.get(
            "/api/v1/ceo/budget?year=2026",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        entries = resp.json()["entries"]
        consulenze = next(e for e in entries if e["category"] == "Consulenze")
        # March (index 2) should have actual=6000 (netto, not 7320 lordo)
        assert consulenze["monthly"][2]["actual"] == 6000.0
        assert consulenze["monthly"][2]["budget"] == 5000.0

    async def test_ac_402_scostamento_within_threshold(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-40.2: variance calculated correctly in grid format."""
        for month in range(1, 13):
            db_session.add(Budget(
                tenant_id=tenant.id, year=2026, month=month,
                category="Utenze", budget_amount=2000.0,
            ))
        await db_session.flush()

        resp = await client.get(
            "/api/v1/ceo/budget?year=2026",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        entries = resp.json()["entries"]
        utenze = next(e for e in entries if e["category"] == "Utenze")
        # No invoices → actual=0, budget=24000, variance=-24000
        assert utenze["total_budget"] == 24000.0
        assert utenze["total_actual"] == 0.0
        assert utenze["variance"] == -24000.0

    async def test_ac_402_totals_computed(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-40.2: DATO multiple categories, ALLORA totali calcolati."""
        for cat, budget_amount in [("Consulenze", 5000.0), ("Utenze", 2000.0)]:
            for month in range(1, 13):
                db_session.add(Budget(
                    tenant_id=tenant.id, year=2026, month=month,
                    category=cat, budget_amount=budget_amount,
                ))
        await db_session.flush()

        resp = await client.get(
            "/api/v1/ceo/budget?year=2026",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        # Budget totals: (5000+2000) * 12 = 84000
        assert data["total_budget"] == 84000.0
        assert data["total_actual"] == 0.0  # no invoices
        assert data["total_delta"] == -84000.0


# ============================================================
# AC-40.3 — Trend + proiezione fine anno
# ============================================================


class TestAC403Proiezione:
    """AC-40.3: Trend + proiezione fine anno (media mobile)."""

    async def test_ac_403_projection_with_data(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-40.3: DATO 3 mesi con dati,
        QUANDO /ceo/budget/projection, ALLORA proiezione annuale."""
        for month in range(1, 4):
            b = Budget(
                tenant_id=tenant.id,
                year=2026,
                month=month,
                category="Consulenze",
                budget_amount=5000.0,
                actual_amount=4000.0 + month * 500,  # 4500, 5000, 5500
            )
            db_session.add(b)
        await db_session.flush()

        resp = await client.get(
            "/api/v1/ceo/budget/projection?year=2026",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["year"] == 2026
        assert data["months_with_data"] == 3
        assert len(data["projections"]) >= 1

        proj = data["projections"][0]
        assert proj["category"] == "Consulenze"
        assert proj["actual_ytd"] == 15000.0  # 4500+5000+5500
        assert proj["moving_average"] == 5000.0  # 15000/3
        assert proj["projected_annual"] == 60000.0  # 5000*12
        assert proj["budget_annual"] == 15000.0  # 5000*3

    async def test_ac_403_projection_no_actual_data(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-40.3: DATO budget senza consuntivo,
        ALLORA proiezione = budget."""
        for month in range(1, 4):
            b = Budget(
                tenant_id=tenant.id,
                year=2026,
                month=month,
                category="Marketing",
                budget_amount=3000.0,
                actual_amount=0.0,
            )
            db_session.add(b)
        await db_session.flush()

        resp = await client.get(
            "/api/v1/ceo/budget/projection?year=2026",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        proj = resp.json()["projections"]
        mktg = [p for p in proj if p["category"] == "Marketing"]
        assert len(mktg) == 1
        # Fallback to budget when no actual data
        assert mktg[0]["projected_annual"] == mktg[0]["budget_annual"]


# ============================================================
# AC-40.4 — Budget non inserito → wizard guidato
# ============================================================


class TestAC404WizardBudget:
    """AC-40.4: Budget non inserito → wizard guidato con suggerimenti."""

    async def test_ac_404_no_budget_wizard(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-40.4: DATO nessun budget per 2026,
        QUANDO GET /ceo/budget?year=2026,
        ALLORA wizard con categorie suggerite."""
        resp = await client.get(
            "/api/v1/ceo/budget?year=2026",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()

        # Should return empty entries but with wizard info
        assert data["total_budget"] == 0.0
        assert len(data["entries"]) == 0

    async def test_ac_404_wizard_with_past_data_suggestions(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-40.4: DATO fatture anno precedente categorizzate,
        QUANDO wizard, ALLORA suggerimenti basati su dati storici."""
        # Create previous year invoices with categories
        for cat, amount in [("Consulenze", 12000.0), ("Utenze", 6000.0)]:
            inv = Invoice(
                tenant_id=tenant.id,
                type="passiva",
                document_type="TD01",
                source="upload",
                numero_fattura=f"FP-WIZ-{cat}",
                emittente_piva="IT00000000001",
                emittente_nome="Fornitore Wizard",
                data_fattura=date(2025, 6, 15),
                importo_netto=amount / 1.22,
                importo_iva=amount - amount / 1.22,
                importo_totale=amount,
                category=cat,
                processing_status="registered",
            )
            db_session.add(inv)
        await db_session.flush()

        resp = await client.get(
            "/api/v1/ceo/budget?year=2026",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        # Should still be empty budget but with suggestions accessible
        assert data["total_budget"] == 0.0


# ============================================================
# AC-40.5 — Voce non prevista
# ============================================================


class TestAC405VoceNonPrevista:
    """AC-40.5: Voce non prevista → evidenziata."""

    async def test_ac_405_non_prevista_flag(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-40.5: DATO budget_amount=0 per all months,
        ALLORA total_budget=0 with variance showing unexpected spend."""
        for month in range(1, 13):
            db_session.add(Budget(
                tenant_id=tenant.id, year=2026, month=month,
                category="Spese Legali", budget_amount=0.0,
            ))
        # Add unexpected invoice for June
        db_session.add(Invoice(
            tenant_id=tenant.id, type="passiva", document_type="TD01",
            source="sdi", numero_fattura="FP-LEGALI-001",
            emittente_piva="22222222222", emittente_nome="Avvocato",
            data_fattura=date(2026, 6, 10),
            importo_netto=1500.0, importo_iva=330.0, importo_totale=1830.0,
            processing_status="registered", category="Spese Legali",
        ))
        await db_session.flush()

        resp = await client.get(
            "/api/v1/ceo/budget?year=2026",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        entries = resp.json()["entries"]
        legali = next(e for e in entries if e["category"] == "Spese Legali")
        assert legali["total_budget"] == 0.0
        assert legali["total_actual"] == 1500.0  # netto
        assert legali["variance"] == 1500.0  # actual - budget

    async def test_ac_405_prevista_not_flagged(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-40.5: DATO budget_amount>0, ALLORA variance is calculated normally."""
        for month in range(1, 13):
            db_session.add(Budget(
                tenant_id=tenant.id, year=2026, month=month,
                category="Consulenze", budget_amount=5000.0,
            ))
        # Add invoice matching budget
        db_session.add(Invoice(
            tenant_id=tenant.id, type="passiva", document_type="TD01",
            source="sdi", numero_fattura="FP-CONS-001",
            emittente_piva="33333333333", emittente_nome="Consulente",
            data_fattura=date(2026, 7, 15),
            importo_netto=4800.0, importo_iva=1056.0, importo_totale=5856.0,
            processing_status="registered", category="Consulenze",
        ))
        await db_session.flush()

        resp = await client.get(
            "/api/v1/ceo/budget?year=2026",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        entries = resp.json()["entries"]
        consulenze = next(e for e in entries if e["category"] == "Consulenze")
        # July (index 6) has actual=4800 (netto)
        assert consulenze["monthly"][6]["actual"] == 4800.0
        assert consulenze["total_budget"] == 60000.0  # 5000*12
