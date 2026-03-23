"""
Test suite for US-31: Cespiti — scheda e ammortamento
Tests for 5 Acceptance Criteria (AC-31.1 through AC-31.5)
"""

import uuid
from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import Asset, FiscalRule, Tenant, User


# ============================================================
# AC-31.1 — Creazione automatica se importo > 516.46 EUR
# ============================================================


class TestAC311CreazioneCespite:
    """AC-31.1: Creazione automatica se importo > soglia da fiscal_rules."""

    async def test_ac_311_create_asset_above_threshold(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-31.1: DATO importo 1000 EUR > 516.46 soglia,
        QUANDO create asset, ALLORA cespite creato."""
        resp = await client.post(
            "/api/v1/assets",
            json={
                "description": "Notebook Dell XPS",
                "category": "Attrezzature informatiche",
                "purchase_date": "2026-03-01",
                "purchase_amount": 1000.0,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["description"] == "Notebook Dell XPS"
        assert data["purchase_amount"] == 1000.0
        assert data["status"] == "active"

    async def test_ac_311_reject_below_threshold(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-31.1: DATO importo 300 EUR < 516.46,
        QUANDO create asset, ALLORA errore sotto soglia."""
        resp = await client.post(
            "/api/v1/assets",
            json={
                "description": "Mouse",
                "category": "Attrezzature informatiche",
                "purchase_date": "2026-03-01",
                "purchase_amount": 300.0,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 400
        assert "516.46" in resp.json()["detail"]

    async def test_ac_311_threshold_from_fiscal_rules(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-31.1: DATO soglia personalizzata in fiscal_rules,
        QUANDO create asset, ALLORA usa soglia da fiscal_rules."""
        rule = FiscalRule(
            key="soglia_cespite",
            value="1000.00",
            value_type="decimal",
            valid_from=date(2026, 1, 1),
        )
        db_session.add(rule)
        await db_session.flush()

        # 800 EUR is above default 516.46 but below custom 1000
        resp = await client.post(
            "/api/v1/assets",
            json={
                "description": "Monitor",
                "category": "Attrezzature informatiche",
                "purchase_date": "2026-03-01",
                "purchase_amount": 800.0,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 400
        assert "1000.00" in resp.json()["detail"]


# ============================================================
# AC-31.2 — Calcolo ammortamento annuale (DARE Ammortamento / AVERE Fondo)
# ============================================================


class TestAC312AmmortamentoAnnuale:
    """AC-31.2: Calcolo ammortamento annuale con scritture contabili."""

    async def test_ac_312_depreciation_run(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-31.2: DATO cespite informatico 1000 EUR al 20%,
        QUANDO run depreciation 2026,
        ALLORA ammortamento 200 EUR, DARE Ammortamento / AVERE Fondo."""
        # Create asset in H1 (no pro-rata)
        asset = Asset(
            tenant_id=tenant.id,
            description="Server Dell",
            category="Attrezzature informatiche",
            purchase_date=date(2026, 3, 1),
            purchase_amount=1000.0,
            depreciable_amount=1000.0,
            depreciation_rate=20.0,
            accumulated_depreciation=0.0,
            residual_value=1000.0,
            status="active",
        )
        db_session.add(asset)
        await db_session.flush()

        resp = await client.post(
            "/api/v1/assets/depreciation/run",
            json={"fiscal_year": 2026},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["assets_processed"] == 1
        assert data["total_depreciation"] == 200.0

        # Check journal entry
        je = data["journal_entries"][0]
        lines = je["lines"]
        debit_line = [l for l in lines if l["debit"] > 0][0]
        assert debit_line["account_code"] == "6400"
        assert debit_line["debit"] == 200.0
        credit_line = [l for l in lines if l["credit"] > 0][0]
        assert credit_line["account_code"] == "1050"
        assert credit_line["credit"] == 200.0

    async def test_ac_312_pro_rata_first_year_h2(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-31.2: DATO cespite acquistato in H2 (luglio),
        QUANDO run depreciation primo anno,
        ALLORA ammortamento 50% = 100 EUR."""
        asset = Asset(
            tenant_id=tenant.id,
            description="PC Portatile",
            category="Attrezzature informatiche",
            purchase_date=date(2026, 9, 15),  # H2
            purchase_amount=1000.0,
            depreciable_amount=1000.0,
            depreciation_rate=20.0,
            accumulated_depreciation=0.0,
            residual_value=1000.0,
            status="active",
        )
        db_session.add(asset)
        await db_session.flush()

        resp = await client.post(
            "/api/v1/assets/depreciation/run",
            json={"fiscal_year": 2026},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_depreciation"] == 100.0  # 50% of 200


# ============================================================
# AC-31.3 — Categoria non mappata -> propone top 3
# ============================================================


class TestAC313CategoriaNonMappata:
    """AC-31.3: Categoria non mappata -> propone top 3."""

    async def test_ac_313_unknown_category_suggests_top3(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-31.3: DATO categoria 'Oggetti vari' non mappata,
        QUANDO create asset con descrizione 'Notebook aziendale',
        ALLORA propone top 3 categorie (Attrezzature informatiche, ...)."""
        resp = await client.post(
            "/api/v1/assets",
            json={
                "description": "Notebook aziendale per ufficio",
                "category": "Oggetti vari",  # not in ministerial table
                "purchase_date": "2026-03-01",
                "purchase_amount": 1200.0,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        # Should have category suggestions
        assert data["category_suggestions"] is not None
        assert len(data["category_suggestions"]) >= 3
        # First suggestion should be Attrezzature informatiche (notebook keyword)
        assert data["category_suggestions"][0]["category"] == "Attrezzature informatiche"


# ============================================================
# AC-31.4 — Cespite usato (senza IVA) -> valore = lordo
# ============================================================


class TestAC314CespiteUsato:
    """AC-31.4: Cespite usato (senza IVA) -> valore = lordo."""

    async def test_ac_314_used_asset_value_equals_gross(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-31.4: DATO cespite usato (is_used=True) importo 800 EUR,
        QUANDO create asset, ALLORA depreciable_amount = 800 (lordo, no IVA)."""
        resp = await client.post(
            "/api/v1/assets",
            json={
                "description": "Furgone usato",
                "category": "Automezzi",
                "purchase_date": "2026-03-01",
                "purchase_amount": 8000.0,
                "is_used": True,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_used"] is True
        assert data["depreciable_amount"] == 8000.0  # lordo


# ============================================================
# AC-31.5 — Fattura cumulativa -> cespite solo per righe > soglia
# ============================================================


class TestAC315FatturaCumulativa:
    """AC-31.5: Fattura cumulativa -> cespite solo per righe > soglia."""

    async def test_ac_315_line_above_threshold_creates_asset(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-31.5: DATO riga fattura 800 EUR > 516.46,
        QUANDO check, ALLORA should_create = True."""
        from api.modules.assets.service import AssetService
        service = AssetService(db_session)
        result = await service.check_invoice_for_assets(
            tenant_id=tenant.id,
            invoice_id=uuid.uuid4(),
            line_description="Notebook Dell XPS",
            line_amount=800.0,
        )
        assert result["should_create"] is True
        assert result["category_suggestions"] is not None

    async def test_ac_315_line_below_threshold_no_asset(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-31.5: DATO riga fattura 200 EUR < 516.46,
        QUANDO check, ALLORA should_create = False."""
        from api.modules.assets.service import AssetService
        service = AssetService(db_session)
        result = await service.check_invoice_for_assets(
            tenant_id=tenant.id,
            invoice_id=uuid.uuid4(),
            line_description="Mouse USB",
            line_amount=200.0,
        )
        assert result["should_create"] is False
