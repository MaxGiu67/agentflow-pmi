"""Tests for Social Selling — Epic 4: Products + Deal Products (US-142→US-145)."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import (
    CrmProduct, CrmDealProduct, CrmDeal, CrmPipelineStage,
    CrmContact, Tenant, User,
)
from tests.conftest import get_auth_token


@pytest.fixture
async def admin_user(db_session: AsyncSession, tenant: Tenant) -> User:
    import bcrypt
    user = User(
        email="admin.epic4@example.com",
        password_hash=bcrypt.hashpw(b"Password1", bcrypt.gensalt()).decode(),
        name="Admin Epic4", role="admin", email_verified=True, tenant_id=tenant.id,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def admin_headers(client: AsyncClient, admin_user: User) -> dict:
    token = await get_auth_token(client, "admin.epic4@example.com", "Password1")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def sample_product(db_session: AsyncSession, tenant: Tenant) -> CrmProduct:
    p = CrmProduct(
        tenant_id=tenant.id, name="Sviluppo Custom", code="custom_dev",
        pricing_model="fixed", base_price=50000, is_active=True,
    )
    db_session.add(p)
    await db_session.flush()
    return p


@pytest.fixture
async def sample_product_2(db_session: AsyncSession, tenant: Tenant) -> CrmProduct:
    p = CrmProduct(
        tenant_id=tenant.id, name="Supporto SLA", code="support_sla",
        pricing_model="fixed", base_price=5000, is_active=True,
    )
    db_session.add(p)
    await db_session.flush()
    return p


@pytest.fixture
async def deal_with_stage(db_session: AsyncSession, tenant: Tenant) -> CrmDeal:
    stage = CrmPipelineStage(
        tenant_id=tenant.id, name="Nuovo Lead", sequence=10,
        probability_default=20, stage_type="pipeline", is_active=True,
    )
    db_session.add(stage)
    await db_session.flush()
    deal = CrmDeal(
        tenant_id=tenant.id, name="Deal Test", stage_id=stage.id,
        expected_revenue=0, probability=20,
    )
    db_session.add(deal)
    await db_session.flush()
    return deal


# ══════════════════════════════════════════════════════
# US-142: Create Product
# ══════════════════════════════════════════════════════


class TestUS142CreateProduct:

    @pytest.mark.anyio
    async def test_ac_142_1_create_product(self, client: AsyncClient, admin_headers: dict):
        resp = await client.post(
            "/api/v1/social/products",
            json={"name": "Consulenza AI", "code": "ai_consult", "pricing_model": "hourly",
                  "hourly_rate": 150, "estimated_duration_days": 20},
            headers=admin_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["code"] == "ai_consult"
        assert resp.json()["pricing_model"] == "hourly"

    @pytest.mark.anyio
    async def test_ac_142_3_duplicate_code(self, client: AsyncClient, admin_headers: dict):
        payload = {"name": "Test", "code": "dup_code"}
        await client.post("/api/v1/social/products", json=payload, headers=admin_headers)
        resp = await client.post("/api/v1/social/products", json=payload, headers=admin_headers)
        assert resp.status_code == 400

    @pytest.mark.anyio
    async def test_ac_142_4_auto_create_category(self, client: AsyncClient, admin_headers: dict):
        resp = await client.post(
            "/api/v1/social/products",
            json={"name": "Prod Cat", "code": "prod_cat", "category_name": "Nuova Categoria"},
            headers=admin_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["category_id"] is not None


# ══════════════════════════════════════════════════════
# US-143: Update / Deactivate Product
# ══════════════════════════════════════════════════════


class TestUS143UpdateProduct:

    @pytest.mark.anyio
    async def test_ac_143_1_update_product(
        self, client: AsyncClient, admin_headers: dict, sample_product: CrmProduct,
    ):
        resp = await client.patch(
            f"/api/v1/social/products/{sample_product.id}",
            json={"name": "Sviluppo Custom v2", "base_price": 55000},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Sviluppo Custom v2"
        assert resp.json()["code"] == "custom_dev"  # immutable

    @pytest.mark.anyio
    async def test_ac_143_2_deactivate_product(
        self, client: AsyncClient, admin_headers: dict, sample_product: CrmProduct,
    ):
        resp = await client.patch(
            f"/api/v1/social/products/{sample_product.id}",
            json={"is_active": False},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    @pytest.mark.anyio
    async def test_ac_143_3_hard_delete_409(
        self, client: AsyncClient, admin_headers: dict, sample_product: CrmProduct,
    ):
        resp = await client.delete(
            f"/api/v1/social/products/{sample_product.id}", headers=admin_headers,
        )
        assert resp.status_code == 409


# ══════════════════════════════════════════════════════
# US-144: Deal Products
# ══════════════════════════════════════════════════════


class TestUS144DealProducts:

    @pytest.mark.anyio
    async def test_ac_144_1_add_product_to_deal(
        self, client: AsyncClient, admin_headers: dict,
        deal_with_stage: CrmDeal, sample_product: CrmProduct,
    ):
        resp = await client.post(
            f"/api/v1/social/deals/{deal_with_stage.id}/products",
            json={"product_id": str(sample_product.id), "quantity": 1},
            headers=admin_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["product_name"] == "Sviluppo Custom"
        assert resp.json()["line_total"] == 50000

    @pytest.mark.anyio
    async def test_ac_144_2_revenue_calculation(
        self, client: AsyncClient, admin_headers: dict,
        db_session: AsyncSession, deal_with_stage: CrmDeal,
        sample_product: CrmProduct, sample_product_2: CrmProduct,
    ):
        """50k + 5k*12 = 110k"""
        await client.post(
            f"/api/v1/social/deals/{deal_with_stage.id}/products",
            json={"product_id": str(sample_product.id), "quantity": 1},
            headers=admin_headers,
        )
        await client.post(
            f"/api/v1/social/deals/{deal_with_stage.id}/products",
            json={"product_id": str(sample_product_2.id), "quantity": 12},
            headers=admin_headers,
        )
        # Check deal revenue updated
        await db_session.refresh(deal_with_stage)
        assert deal_with_stage.expected_revenue == 110000  # 50k + 60k

    @pytest.mark.anyio
    async def test_ac_144_3_cannot_remove_last_product(
        self, client: AsyncClient, admin_headers: dict,
        db_session: AsyncSession, deal_with_stage: CrmDeal, sample_product: CrmProduct,
    ):
        dp = CrmDealProduct(
            tenant_id=deal_with_stage.tenant_id,
            deal_id=deal_with_stage.id,
            product_id=sample_product.id,
            quantity=1,
        )
        db_session.add(dp)
        await db_session.flush()

        resp = await client.delete(
            f"/api/v1/social/deals/{deal_with_stage.id}/products/{dp.id}",
            headers=admin_headers,
        )
        assert resp.status_code == 400
        assert "almeno 1" in resp.json()["detail"].lower()

    @pytest.mark.anyio
    async def test_ac_144_4_duplicate_product_allowed(
        self, client: AsyncClient, admin_headers: dict,
        deal_with_stage: CrmDeal, sample_product: CrmProduct,
    ):
        """Same product can be added multiple times (M1 fix)."""
        await client.post(
            f"/api/v1/social/deals/{deal_with_stage.id}/products",
            json={"product_id": str(sample_product.id), "quantity": 1, "notes": "Phase 1"},
            headers=admin_headers,
        )
        resp = await client.post(
            f"/api/v1/social/deals/{deal_with_stage.id}/products",
            json={"product_id": str(sample_product.id), "quantity": 1, "notes": "Phase 2"},
            headers=admin_headers,
        )
        assert resp.status_code == 201

    @pytest.mark.anyio
    async def test_ac_144_list_deal_products(
        self, client: AsyncClient, admin_headers: dict,
        db_session: AsyncSession, deal_with_stage: CrmDeal, sample_product: CrmProduct,
    ):
        dp = CrmDealProduct(
            tenant_id=deal_with_stage.tenant_id,
            deal_id=deal_with_stage.id,
            product_id=sample_product.id,
            quantity=2,
        )
        db_session.add(dp)
        await db_session.flush()

        resp = await client.get(
            f"/api/v1/social/deals/{deal_with_stage.id}/products",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) >= 1
