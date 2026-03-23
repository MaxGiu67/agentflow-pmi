"""
Test suite for US-32: Cespiti — registro e dismissione
Tests for 5 Acceptance Criteria (AC-32.1 through AC-32.5)
"""

import uuid
from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import Asset, Tenant, User


# ============================================================
# AC-32.1 — Registro cespiti (descrizione, valore, fondo, residuo, %)
# ============================================================


class TestAC321RegistroCespiti:
    """AC-32.1: Registro cespiti con tutti i campi."""

    async def test_ac_321_list_assets_registry(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-32.1: DATO cespiti in DB,
        QUANDO list assets, ALLORA registro con tutti i campi."""
        asset = Asset(
            tenant_id=tenant.id,
            description="Server HP",
            category="Attrezzature informatiche",
            purchase_date=date(2025, 1, 15),
            purchase_amount=3000.0,
            depreciable_amount=3000.0,
            depreciation_rate=20.0,
            accumulated_depreciation=600.0,
            residual_value=2400.0,
            status="active",
        )
        db_session.add(asset)
        await db_session.flush()

        resp = await client.get(
            "/api/v1/assets",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

        item = data["items"][0]
        assert item["description"] == "Server HP"
        assert item["depreciable_amount"] == 3000.0
        assert item["accumulated_depreciation"] == 600.0
        assert item["residual_value"] == 2400.0
        assert item["depreciation_rate"] == 20.0

    async def test_ac_321_get_single_asset(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-32.1: DATO cespite in DB,
        QUANDO GET /assets/{id}, ALLORA dettaglio completo."""
        asset = Asset(
            tenant_id=tenant.id,
            description="Scrivania direzionale",
            category="Mobili",
            purchase_date=date(2025, 6, 1),
            purchase_amount=800.0,
            depreciable_amount=800.0,
            depreciation_rate=12.0,
            accumulated_depreciation=96.0,
            residual_value=704.0,
            status="active",
        )
        db_session.add(asset)
        await db_session.flush()

        resp = await client.get(
            f"/api/v1/assets/{asset.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(asset.id)
        assert data["category"] == "Mobili"


# ============================================================
# AC-32.2 — Vendita -> calcola plus/minusvalenza, scritture chiusura
# ============================================================


class TestAC322Vendita:
    """AC-32.2: Vendita -> calcola plus/minusvalenza."""

    async def test_ac_322_sale_with_plusvalenza(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-32.2: DATO cespite valore residuo 2000 EUR,
        QUANDO vendita a 2500 EUR,
        ALLORA plusvalenza 500 EUR."""
        asset = Asset(
            tenant_id=tenant.id,
            description="Auto aziendale",
            category="Automezzi",
            purchase_date=date(2023, 1, 15),
            purchase_amount=20000.0,
            depreciable_amount=20000.0,
            depreciation_rate=25.0,
            accumulated_depreciation=18000.0,
            residual_value=2000.0,
            status="active",
        )
        db_session.add(asset)
        await db_session.flush()

        resp = await client.post(
            f"/api/v1/assets/{asset.id}/dispose",
            json={
                "disposal_date": "2026-06-30",
                "disposal_amount": 2500.0,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["gain_loss_type"] == "plusvalenza"
        assert data["gain_loss"] > 0
        assert data["status"] == "disposed"

        # Check closing entry has plusvalenza line
        closing_je = [je for je in data["journal_entries"] if "Dismissione" in je["description"]][0]
        plus_lines = [l for l in closing_je["lines"] if l["account_code"] == "7100"]
        assert len(plus_lines) == 1

    async def test_ac_322_sale_with_minusvalenza(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-32.2: DATO cespite valore residuo 10000 EUR,
        QUANDO vendita a 3000 EUR,
        ALLORA minusvalenza."""
        asset = Asset(
            tenant_id=tenant.id,
            description="Furgone",
            category="Automezzi",
            purchase_date=date(2023, 1, 15),
            purchase_amount=20000.0,
            depreciable_amount=20000.0,
            depreciation_rate=25.0,
            accumulated_depreciation=10000.0,
            residual_value=10000.0,
            status="active",
        )
        db_session.add(asset)
        await db_session.flush()

        resp = await client.post(
            f"/api/v1/assets/{asset.id}/dispose",
            json={
                "disposal_date": "2026-06-30",
                "disposal_amount": 3000.0,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["gain_loss_type"] == "minusvalenza"
        assert data["gain_loss"] < 0


# ============================================================
# AC-32.3 — Dismissione in corso d'anno -> ammortamento pro-rata
# ============================================================


class TestAC323ProRata:
    """AC-32.3: Dismissione in corso d'anno -> ammortamento pro-rata."""

    async def test_ac_323_mid_year_disposal_pro_rata(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-32.3: DATO cespite 10000 EUR al 20%,
        QUANDO dismissione 30/06/2026 (meta anno),
        ALLORA ammortamento pro-rata ~1000 EUR (50% di 2000)."""
        asset = Asset(
            tenant_id=tenant.id,
            description="Macchinario industriale",
            category="Macchinari",
            purchase_date=date(2024, 1, 15),
            purchase_amount=10000.0,
            depreciable_amount=10000.0,
            depreciation_rate=20.0,
            accumulated_depreciation=4000.0,  # 2 years
            residual_value=6000.0,
            status="active",
        )
        db_session.add(asset)
        await db_session.flush()

        resp = await client.post(
            f"/api/v1/assets/{asset.id}/dispose",
            json={
                "disposal_date": "2026-06-30",
                "disposal_amount": 5000.0,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["pro_rata_depreciation"] > 0
        # ~50% of 2000 = ~1000 (proportional to days)
        assert 900 < data["pro_rata_depreciation"] < 1100

        # Should have pro-rata journal entry
        pro_rata_je = [je for je in data["journal_entries"] if "pro-rata" in je["description"].lower()]
        assert len(pro_rata_je) == 1


# ============================================================
# AC-32.4 — Rottamazione/furto (prezzo=0) -> minusvalenza = valore residuo
# ============================================================


class TestAC324Rottamazione:
    """AC-32.4: Rottamazione/furto (prezzo=0) -> minusvalenza = residuo."""

    async def test_ac_324_scrapping_loss_equals_residual(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-32.4: DATO cespite valore residuo 3000 EUR,
        QUANDO rottamazione (prezzo=0),
        ALLORA minusvalenza = valore residuo."""
        asset = Asset(
            tenant_id=tenant.id,
            description="PC vecchio",
            category="Attrezzature informatiche",
            purchase_date=date(2022, 1, 15),
            purchase_amount=5000.0,
            depreciable_amount=5000.0,
            depreciation_rate=20.0,
            accumulated_depreciation=2000.0,
            residual_value=3000.0,
            status="active",
        )
        db_session.add(asset)
        await db_session.flush()

        resp = await client.post(
            f"/api/v1/assets/{asset.id}/dispose",
            json={
                "disposal_date": "2026-06-30",
                "disposal_amount": 0.0,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["gain_loss_type"] == "minusvalenza"
        assert data["gain_loss"] < 0
        assert data["status"] == "scrapped"

        # Minusvalenza entry should be present
        closing_je = [je for je in data["journal_entries"] if "Dismissione" in je["description"]][0]
        minus_lines = [l for l in closing_je["lines"] if l["account_code"] == "6500"]
        assert len(minus_lines) == 1
        assert minus_lines[0]["debit"] > 0  # minusvalenza in DARE


# ============================================================
# AC-32.5 — Completamente ammortizzato -> "Ammortizzato, ancora in uso"
# ============================================================


class TestAC325CompletoAmmortizzato:
    """AC-32.5: Completamente ammortizzato -> messaggio."""

    async def test_ac_325_fully_depreciated_message(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-32.5: DATO cespite con valore residuo minimo,
        QUANDO run depreciation e diventa 0,
        ALLORA status 'fully_depreciated' + messaggio."""
        asset = Asset(
            tenant_id=tenant.id,
            description="Monitor vecchio",
            category="Attrezzature informatiche",
            purchase_date=date(2022, 3, 1),  # H1, no pro-rata for this year
            purchase_amount=1000.0,
            depreciable_amount=1000.0,
            depreciation_rate=20.0,
            accumulated_depreciation=900.0,  # only 100 left
            residual_value=100.0,
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
        assert len(data["fully_depreciated"]) == 1
        fd = data["fully_depreciated"][0]
        assert fd["message"] == "Ammortizzato, ancora in uso"
        assert fd["description"] == "Monitor vecchio"
