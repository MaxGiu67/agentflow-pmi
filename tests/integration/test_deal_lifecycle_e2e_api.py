"""Test suite for Deal Lifecycle E2E — Sprint A.

End-to-end tests covering the full deal lifecycle:
Lead -> Qualified -> Proposal -> Offer -> Project -> Resources -> Won.
~75 tests.
"""

import uuid
from datetime import date, datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import (
    CrmDeal, CrmDealProduct, CrmDealResource, CrmPipelineStage,
    CrmProduct, CrmContact, Tenant, User,
)
from api.modules.crm.service import CRMService
from api.modules.deal_resources.service import DealResourceService
from tests.conftest import _hash_pw, get_auth_token


# ── Fixtures ──────────────────────────────────────

@pytest.fixture
async def owner(db_session: AsyncSession, tenant: Tenant) -> User:
    u = User(
        email="e2e.owner@test.it", password_hash=_hash_pw("Password1"),
        name="E2E Owner", role="owner", email_verified=True, tenant_id=tenant.id,
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest.fixture
async def commerciale(db_session: AsyncSession, tenant: Tenant) -> User:
    u = User(
        email="e2e.comm@test.it", password_hash=_hash_pw("Password1"),
        name="E2E Commerciale", role="commerciale", email_verified=True, tenant_id=tenant.id,
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest.fixture
async def owner_headers(client: AsyncClient, owner: User) -> dict:
    token = await get_auth_token(client, "e2e.owner@test.it", "Password1")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def comm_headers(client: AsyncClient, commerciale: User) -> dict:
    token = await get_auth_token(client, "e2e.comm@test.it", "Password1")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def crm(db_session: AsyncSession) -> CRMService:
    return CRMService(db_session)


@pytest.fixture
async def stages(db_session: AsyncSession, tenant: Tenant, crm: CRMService) -> list:
    await crm._ensure_default_stages(tenant.id)
    result = await db_session.execute(
        select(CrmPipelineStage).where(CrmPipelineStage.tenant_id == tenant.id)
        .order_by(CrmPipelineStage.sequence)
    )
    return list(result.scalars().all())


@pytest.fixture
async def contact(db_session: AsyncSession, tenant: Tenant) -> CrmContact:
    c = CrmContact(
        tenant_id=tenant.id,
        name="ACME Corp",
        email="info@acme.com",
        type="prospect",
    )
    db_session.add(c)
    await db_session.flush()
    return c


@pytest.fixture
async def tm_product(db_session: AsyncSession, tenant: Tenant) -> CrmProduct:
    p = CrmProduct(
        tenant_id=tenant.id, name="T&M Consulting", code="TM-E2E",
        requires_resources=True, pricing_model="hourly",
    )
    db_session.add(p)
    await db_session.flush()
    return p


@pytest.fixture
async def fixed_product(db_session: AsyncSession, tenant: Tenant) -> CrmProduct:
    p = CrmProduct(
        tenant_id=tenant.id, name="Fixed Project", code="FIX-E2E",
        requires_resources=False, pricing_model="fixed",
    )
    db_session.add(p)
    await db_session.flush()
    return p


# ============================================================
# A. Deal Creation & Portal Customer
# ============================================================


class TestDealCreation:

    @pytest.mark.anyio
    async def test_01_create_deal_basic(self, client, owner_headers, stages, contact):
        resp = await client.post("/api/v1/crm/deals", json={
            "name": "E2E Deal Alpha",
            "contact_id": str(contact.id),
            "deal_type": "T&M",
            "expected_revenue": 100000,
            "daily_rate": 500,
            "estimated_days": 200,
        }, headers=owner_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "E2E Deal Alpha"
        assert data["portal_offer_id"] is None
        assert data["portal_project_id"] is None
        assert data["requires_resources"] is False

    @pytest.mark.anyio
    async def test_02_create_deal_with_portal_customer(self, client, owner_headers, stages):
        resp = await client.post("/api/v1/crm/deals", json={
            "name": "E2E Portal Deal",
            "portal_customer_id": 42,
            "portal_customer_name": "ACME Corp",
            "deal_type": "T&M",
            "expected_revenue": 80000,
        }, headers=owner_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["portal_customer_id"] == 42
        assert data["portal_customer_name"] == "ACME Corp"

    @pytest.mark.anyio
    async def test_03_deal_dict_has_all_fields(self, client, owner_headers, stages):
        resp = await client.post("/api/v1/crm/deals", json={
            "name": "Fields Test",
            "deal_type": "fixed",
        }, headers=owner_headers)
        data = resp.json()
        required_keys = [
            "id", "name", "portal_offer_id", "portal_project_id",
            "portal_customer_id", "portal_customer_name",
            "requires_resources", "deal_type",
        ]
        for key in required_keys:
            assert key in data, f"Missing key: {key}"


# ============================================================
# B. Deal Update with Portal IDs
# ============================================================


class TestDealUpdate:

    @pytest.mark.anyio
    async def test_04_update_portal_offer_id(self, client, owner_headers, stages, db_session, tenant):
        create_resp = await client.post("/api/v1/crm/deals", json={
            "name": "Update Portal IDs",
        }, headers=owner_headers)
        deal_id = create_resp.json()["id"]
        resp = await client.patch(f"/api/v1/crm/deals/{deal_id}", json={
            "portal_offer_id": 777,
        }, headers=owner_headers)
        assert resp.status_code == 200
        assert resp.json()["portal_offer_id"] == 777

    @pytest.mark.anyio
    async def test_05_update_portal_project_id(self, client, owner_headers, stages):
        create_resp = await client.post("/api/v1/crm/deals", json={
            "name": "Update Project ID",
        }, headers=owner_headers)
        deal_id = create_resp.json()["id"]
        resp = await client.patch(f"/api/v1/crm/deals/{deal_id}", json={
            "portal_project_id": 888,
        }, headers=owner_headers)
        assert resp.status_code == 200
        assert resp.json()["portal_project_id"] == 888

    @pytest.mark.anyio
    async def test_06_update_preserves_existing_data(self, client, owner_headers, stages):
        create_resp = await client.post("/api/v1/crm/deals", json={
            "name": "Preserve Data",
            "deal_type": "T&M",
            "expected_revenue": 50000,
        }, headers=owner_headers)
        deal_id = create_resp.json()["id"]
        resp = await client.patch(f"/api/v1/crm/deals/{deal_id}", json={
            "portal_offer_id": 999,
        }, headers=owner_headers)
        data = resp.json()
        assert data["deal_type"] == "T&M"
        assert data["expected_revenue"] == 50000
        assert data["portal_offer_id"] == 999


# ============================================================
# C. Deal Resources CRUD
# ============================================================


class TestDealResourcesCRUD:

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_07_add_resource(self, mock_pc, client, owner_headers, stages, db_session, tenant):
        mock_pc.get_person = AsyncMock(return_value={
            "firstName": "Anna",
            "lastName": "Dev",
            "EmploymentContracts": [{"dailyCost": 400, "endDate": None}],
        })
        deal_resp = await client.post("/api/v1/crm/deals", json={
            "name": "Resource Deal",
            "portal_customer_id": 42,
        }, headers=owner_headers)
        deal_id = deal_resp.json()["id"]
        resp = await client.post(f"/api/v1/crm/deals/{deal_id}/resources", json={
            "portal_person_id": 101,
            "role": "Frontend Dev",
        }, headers=owner_headers)
        assert resp.status_code == 201
        assert resp.json()["person_name"] == "Anna Dev"
        assert resp.json()["daily_cost"] == 400

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_08_list_resources(self, mock_pc, client, owner_headers, stages, db_session, tenant):
        mock_pc.get_person = AsyncMock(return_value={"error": "off"})
        deal_resp = await client.post("/api/v1/crm/deals", json={
            "name": "List Resources Deal",
        }, headers=owner_headers)
        deal_id = deal_resp.json()["id"]
        await client.post(f"/api/v1/crm/deals/{deal_id}/resources", json={
            "portal_person_id": 1, "person_name": "Res 1",
        }, headers=owner_headers)
        await client.post(f"/api/v1/crm/deals/{deal_id}/resources", json={
            "portal_person_id": 2, "person_name": "Res 2",
        }, headers=owner_headers)
        resp = await client.get(f"/api/v1/crm/deals/{deal_id}/resources", headers=owner_headers)
        assert len(resp.json()) == 2

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_09_update_resource(self, mock_pc, client, owner_headers, stages):
        mock_pc.get_person = AsyncMock(return_value={"error": "off"})
        deal_resp = await client.post("/api/v1/crm/deals", json={
            "name": "Update Res Deal",
        }, headers=owner_headers)
        deal_id = deal_resp.json()["id"]
        add_resp = await client.post(f"/api/v1/crm/deals/{deal_id}/resources", json={
            "portal_person_id": 3, "person_name": "Updatable",
        }, headers=owner_headers)
        rid = add_resp.json()["id"]
        resp = await client.patch(f"/api/v1/crm/deals/{deal_id}/resources/{rid}", json={
            "status": "active", "role": "Senior",
        }, headers=owner_headers)
        assert resp.json()["status"] == "active"

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_10_delete_resource(self, mock_pc, client, owner_headers, stages):
        mock_pc.get_person = AsyncMock(return_value={"error": "off"})
        deal_resp = await client.post("/api/v1/crm/deals", json={
            "name": "Delete Res Deal",
        }, headers=owner_headers)
        deal_id = deal_resp.json()["id"]
        add_resp = await client.post(f"/api/v1/crm/deals/{deal_id}/resources", json={
            "portal_person_id": 4, "person_name": "Deletable",
        }, headers=owner_headers)
        rid = add_resp.json()["id"]
        resp = await client.delete(f"/api/v1/crm/deals/{deal_id}/resources/{rid}", headers=owner_headers)
        assert resp.json()["ok"] is True


# ============================================================
# D. Requires Resources
# ============================================================


class TestRequiresResources:

    @pytest.mark.anyio
    async def test_11_no_products(self, client, owner_headers, stages):
        deal_resp = await client.post("/api/v1/crm/deals", json={
            "name": "No Prod Deal",
        }, headers=owner_headers)
        resp = await client.get(
            f"/api/v1/crm/deals/{deal_resp.json()['id']}/resources/requires",
            headers=owner_headers,
        )
        assert resp.json()["requires_resources"] is False

    @pytest.mark.anyio
    async def test_12_with_tm_product(self, client, owner_headers, stages, db_session, tenant, tm_product):
        deal_resp = await client.post("/api/v1/crm/deals", json={
            "name": "TM Product Deal",
        }, headers=owner_headers)
        deal_id = uuid.UUID(deal_resp.json()["id"])
        dp = CrmDealProduct(tenant_id=tenant.id, deal_id=deal_id, product_id=tm_product.id)
        db_session.add(dp)
        await db_session.flush()
        resp = await client.get(
            f"/api/v1/crm/deals/{deal_id}/resources/requires",
            headers=owner_headers,
        )
        assert resp.json()["requires_resources"] is True

    @pytest.mark.anyio
    async def test_13_with_fixed_product(self, client, owner_headers, stages, db_session, tenant, fixed_product):
        deal_resp = await client.post("/api/v1/crm/deals", json={
            "name": "Fixed Product Deal",
        }, headers=owner_headers)
        deal_id = uuid.UUID(deal_resp.json()["id"])
        dp = CrmDealProduct(tenant_id=tenant.id, deal_id=deal_id, product_id=fixed_product.id)
        db_session.add(dp)
        await db_session.flush()
        resp = await client.get(
            f"/api/v1/crm/deals/{deal_id}/resources/requires",
            headers=owner_headers,
        )
        assert resp.json()["requires_resources"] is False


# ============================================================
# E. Full E2E: Deal -> Offer -> Project -> Resources
# ============================================================


class TestFullLifecycle:

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    @patch("api.modules.portal.router.portal_client")
    async def test_14_full_tm_lifecycle(self, mock_portal, mock_res_pc, client, owner_headers, stages, contact):
        # 1. Create deal
        deal_resp = await client.post("/api/v1/crm/deals", json={
            "name": "Full Lifecycle TM",
            "contact_id": str(contact.id),
            "deal_type": "T&M",
            "expected_revenue": 120000,
            "daily_rate": 600,
            "estimated_days": 200,
            "portal_customer_id": 42,
            "portal_customer_name": "ACME Corp",
        }, headers=owner_headers)
        assert deal_resp.status_code == 201
        deal_id = deal_resp.json()["id"]

        # 2. Create offer
        mock_portal.create_offer = AsyncMock(return_value={"id": 1000})
        offer_resp = await client.post(
            f"/api/v1/portal/offers/create-from-deal/{deal_id}",
            json={"project_code": "ACM-E2E-001"},
            headers=owner_headers,
        )
        assert offer_resp.json()["id"] == 1000

        # 3. Link project
        mock_portal.get_offer = AsyncMock(return_value={"id": 1000, "project_id": 2000})
        proj_resp = await client.post(
            f"/api/v1/portal/projects/create-from-deal/{deal_id}",
            json={},
            headers=owner_headers,
        )
        assert proj_resp.json()["project_id"] == 2000

        # 4. Add resources
        mock_res_pc.get_person = AsyncMock(return_value={
            "firstName": "Mario",
            "lastName": "Dev",
            "EmploymentContracts": [{"dailyCost": 350, "endDate": None}],
        })
        res_resp = await client.post(
            f"/api/v1/crm/deals/{deal_id}/resources",
            json={"portal_person_id": 101, "role": "Backend Dev"},
            headers=owner_headers,
        )
        assert res_resp.status_code == 201

        # 5. Verify deal has all IDs
        deal_check = await client.get(f"/api/v1/crm/deals/{deal_id}", headers=owner_headers)
        data = deal_check.json()
        assert data["portal_offer_id"] == 1000
        assert data["portal_project_id"] == 2000

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    @patch("api.modules.portal.router.portal_client")
    async def test_15_full_fixed_lifecycle(self, mock_portal, mock_res_pc, client, owner_headers, stages):
        # 1. Create deal
        deal_resp = await client.post("/api/v1/crm/deals", json={
            "name": "Full Lifecycle Fixed",
            "deal_type": "fixed",
            "expected_revenue": 50000,
            "portal_customer_id": 55,
            "portal_customer_name": "Beta Corp",
        }, headers=owner_headers)
        deal_id = deal_resp.json()["id"]

        # 2. Create offer (should use LumpSum)
        captured = {}
        async def capture_offer(payload):
            captured.update(payload)
            return {"id": 1001}
        mock_portal.create_offer = AsyncMock(side_effect=capture_offer)
        await client.post(
            f"/api/v1/portal/offers/create-from-deal/{deal_id}",
            json={},
            headers=owner_headers,
        )
        assert captured["billing_type"] == "LumpSum"


# ============================================================
# F. Stage Movement
# ============================================================


class TestStageMovement:

    @pytest.mark.anyio
    async def test_16_move_to_proposta(self, client, owner_headers, stages):
        deal_resp = await client.post("/api/v1/crm/deals", json={
            "name": "Move Stage Deal",
        }, headers=owner_headers)
        deal_id = deal_resp.json()["id"]
        proposta_stage = [s for s in stages if s.name == "Proposta Inviata"][0]
        resp = await client.patch(f"/api/v1/crm/deals/{deal_id}", json={
            "stage_id": str(proposta_stage.id),
        }, headers=owner_headers)
        assert resp.json()["stage"] == "Proposta Inviata"

    @pytest.mark.anyio
    async def test_17_move_to_won_with_offer(self, client, owner_headers, stages):
        deal_resp = await client.post("/api/v1/crm/deals", json={
            "name": "Won Deal",
            "portal_customer_id": 42,
        }, headers=owner_headers)
        deal_id = deal_resp.json()["id"]
        # Set offer
        await client.patch(f"/api/v1/crm/deals/{deal_id}", json={
            "portal_offer_id": 999,
        }, headers=owner_headers)
        # Move to won
        won_stage = [s for s in stages if s.is_won][0]
        resp = await client.patch(f"/api/v1/crm/deals/{deal_id}", json={
            "stage_id": str(won_stage.id),
        }, headers=owner_headers)
        assert resp.json()["stage"] == "Confermato"
        assert resp.json()["portal_offer_id"] == 999

    @pytest.mark.anyio
    async def test_18_move_to_lost(self, client, owner_headers, stages):
        deal_resp = await client.post("/api/v1/crm/deals", json={
            "name": "Lost Deal",
        }, headers=owner_headers)
        deal_id = deal_resp.json()["id"]
        lost_stage = [s for s in stages if s.is_lost][0]
        resp = await client.patch(f"/api/v1/crm/deals/{deal_id}", json={
            "stage_id": str(lost_stage.id),
        }, headers=owner_headers)
        assert resp.json()["stage"] == "Perso"


# ============================================================
# G. Order Flow
# ============================================================


class TestOrderFlow:

    @pytest.mark.anyio
    async def test_19_register_order(self, client, owner_headers, stages):
        deal_resp = await client.post("/api/v1/crm/deals", json={
            "name": "Order Deal",
        }, headers=owner_headers)
        deal_id = deal_resp.json()["id"]
        resp = await client.post(f"/api/v1/crm/deals/{deal_id}/order", json={
            "order_type": "po",
            "order_reference": "PO-2026-001",
        }, headers=owner_headers)
        assert resp.json()["status"] == "registered"

    @pytest.mark.anyio
    async def test_20_confirm_order(self, client, owner_headers, stages):
        deal_resp = await client.post("/api/v1/crm/deals", json={
            "name": "Confirm Deal",
        }, headers=owner_headers)
        deal_id = deal_resp.json()["id"]
        await client.post(f"/api/v1/crm/deals/{deal_id}/order", json={
            "order_type": "email",
        }, headers=owner_headers)
        resp = await client.post(f"/api/v1/crm/deals/{deal_id}/order/confirm", headers=owner_headers)
        assert resp.json()["status"] == "confirmed"


# ============================================================
# H. Commerciale User Tests
# ============================================================


class TestCommerciale:

    @pytest.mark.anyio
    async def test_21_commerciale_auto_assign(self, client, comm_headers, stages, commerciale):
        resp = await client.post("/api/v1/crm/deals", json={
            "name": "Comm Deal",
        }, headers=comm_headers)
        assert resp.status_code == 201
        assert resp.json()["assigned_to"] == str(commerciale.id)

    @pytest.mark.anyio
    async def test_22_commerciale_sees_own_deals(self, client, owner_headers, comm_headers, stages, commerciale):
        # Owner creates a deal
        await client.post("/api/v1/crm/deals", json={
            "name": "Owner Deal",
        }, headers=owner_headers)
        # Commerciale creates a deal
        await client.post("/api/v1/crm/deals", json={
            "name": "Comm Deal",
        }, headers=comm_headers)
        # Commerciale should only see their deal
        resp = await client.get("/api/v1/crm/deals", headers=comm_headers)
        deals = resp.json()["deals"]
        assert all(d["assigned_to"] == str(commerciale.id) for d in deals)


# ============================================================
# I. Multiple Deals Resources Isolation
# ============================================================


class TestResourceIsolation:

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_23_resources_isolated_per_deal(self, mock_pc, client, owner_headers, stages):
        mock_pc.get_person = AsyncMock(return_value={"error": "off"})
        # Create two deals
        d1 = await client.post("/api/v1/crm/deals", json={"name": "Iso Deal 1"}, headers=owner_headers)
        d2 = await client.post("/api/v1/crm/deals", json={"name": "Iso Deal 2"}, headers=owner_headers)
        d1_id = d1.json()["id"]
        d2_id = d2.json()["id"]

        # Add resources to each
        await client.post(f"/api/v1/crm/deals/{d1_id}/resources", json={
            "portal_person_id": 1, "person_name": "Deal 1 Res",
        }, headers=owner_headers)
        await client.post(f"/api/v1/crm/deals/{d2_id}/resources", json={
            "portal_person_id": 2, "person_name": "Deal 2 Res",
        }, headers=owner_headers)

        # Check isolation
        r1 = await client.get(f"/api/v1/crm/deals/{d1_id}/resources", headers=owner_headers)
        r2 = await client.get(f"/api/v1/crm/deals/{d2_id}/resources", headers=owner_headers)
        assert len(r1.json()) == 1
        assert r1.json()[0]["person_name"] == "Deal 1 Res"
        assert len(r2.json()) == 1
        assert r2.json()[0]["person_name"] == "Deal 2 Res"


# ============================================================
# J. Deal Listing with Portal IDs
# ============================================================


class TestDealListingPortalIds:

    @pytest.mark.anyio
    async def test_24_deals_list_has_portal_ids(self, client, owner_headers, stages, db_session, tenant):
        d = CrmDeal(
            tenant_id=tenant.id,
            name="Portal IDs Deal",
            stage_id=stages[0].id,
            portal_customer_id=10,
            portal_offer_id=20,
            portal_project_id=30,
        )
        db_session.add(d)
        await db_session.flush()
        resp = await client.get("/api/v1/crm/deals", headers=owner_headers)
        deals = resp.json()["deals"]
        found = [dl for dl in deals if dl["name"] == "Portal IDs Deal"]
        assert len(found) == 1
        assert found[0]["portal_customer_id"] == 10
        assert found[0]["portal_offer_id"] == 20
        assert found[0]["portal_project_id"] == 30

    @pytest.mark.anyio
    async def test_25_won_deals_list_has_portal_ids(self, client, owner_headers, stages, db_session, tenant):
        won_stage = [s for s in stages if s.is_won][0]
        d = CrmDeal(
            tenant_id=tenant.id,
            name="Won Portal Deal",
            stage_id=won_stage.id,
            portal_offer_id=50,
            portal_project_id=60,
        )
        db_session.add(d)
        await db_session.flush()
        resp = await client.get("/api/v1/crm/deals/won", headers=owner_headers)
        deals = resp.json()["deals"]
        found = [dl for dl in deals if dl["name"] == "Won Portal Deal"]
        assert len(found) == 1
        assert found[0]["portal_offer_id"] == 50


# ============================================================
# K. Error Handling
# ============================================================


class TestErrorHandling:

    @pytest.mark.anyio
    async def test_26_deal_not_found(self, client, owner_headers):
        fake_id = str(uuid.uuid4())
        resp = await client.get(f"/api/v1/crm/deals/{fake_id}", headers=owner_headers)
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_27_resource_on_nonexistent_deal(self, client, owner_headers):
        fake_id = str(uuid.uuid4())
        resp = await client.get(f"/api/v1/crm/deals/{fake_id}/resources", headers=owner_headers)
        # Should return empty list (not 404)
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.anyio
    async def test_28_add_resource_no_person_id(self, client, owner_headers, stages):
        deal_resp = await client.post("/api/v1/crm/deals", json={"name": "Err Deal"}, headers=owner_headers)
        resp = await client.post(
            f"/api/v1/crm/deals/{deal_resp.json()['id']}/resources",
            json={"role": "Dev"},
            headers=owner_headers,
        )
        assert resp.status_code == 400

    @pytest.mark.anyio
    async def test_29_update_nonexistent_resource(self, client, owner_headers, stages):
        deal_resp = await client.post("/api/v1/crm/deals", json={"name": "Upd Err Deal"}, headers=owner_headers)
        resp = await client.patch(
            f"/api/v1/crm/deals/{deal_resp.json()['id']}/resources/{uuid.uuid4()}",
            json={"status": "active"},
            headers=owner_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_30_delete_nonexistent_resource(self, client, owner_headers, stages):
        deal_resp = await client.post("/api/v1/crm/deals", json={"name": "Del Err Deal"}, headers=owner_headers)
        resp = await client.delete(
            f"/api/v1/crm/deals/{deal_resp.json()['id']}/resources/{uuid.uuid4()}",
            headers=owner_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_31_offer_invalid_deal_id(self, client, owner_headers):
        resp = await client.post(
            f"/api/v1/portal/offers/create-from-deal/{uuid.uuid4()}",
            json={},
            headers=owner_headers,
        )
        assert resp.json()["error"] == "Deal not found"

    @pytest.mark.anyio
    async def test_32_project_invalid_deal_id(self, client, owner_headers):
        resp = await client.post(
            f"/api/v1/portal/projects/create-from-deal/{uuid.uuid4()}",
            json={},
            headers=owner_headers,
        )
        assert resp.json()["error"] == "Deal not found"


# ============================================================
# L. Pipeline Summary & Analytics
# ============================================================


class TestPipelineSummary:

    @pytest.mark.anyio
    async def test_33_pipeline_summary(self, client, owner_headers, stages):
        await client.post("/api/v1/crm/deals", json={
            "name": "Summary Deal 1", "expected_revenue": 10000,
        }, headers=owner_headers)
        await client.post("/api/v1/crm/deals", json={
            "name": "Summary Deal 2", "expected_revenue": 20000,
        }, headers=owner_headers)
        resp = await client.get("/api/v1/crm/pipeline/summary", headers=owner_headers)
        assert resp.status_code == 200
        assert resp.json()["total_deals"] >= 2

    @pytest.mark.anyio
    async def test_34_pipeline_analytics(self, client, owner_headers, stages):
        resp = await client.get("/api/v1/crm/pipeline/analytics", headers=owner_headers)
        assert resp.status_code == 200


# ============================================================
# M. Model Tests for New Fields
# ============================================================


class TestModelFields:

    @pytest.mark.anyio
    async def test_35_crm_deal_portal_offer_id(self, db_session, tenant, stages):
        d = CrmDeal(tenant_id=tenant.id, name="Model Test", stage_id=stages[0].id, portal_offer_id=42)
        db_session.add(d)
        await db_session.flush()
        loaded = await db_session.get(CrmDeal, d.id)
        assert loaded.portal_offer_id == 42

    @pytest.mark.anyio
    async def test_36_crm_deal_resource_model(self, db_session, tenant, stages):
        d = CrmDeal(tenant_id=tenant.id, name="Res Model", stage_id=stages[0].id)
        db_session.add(d)
        await db_session.flush()
        r = CrmDealResource(
            tenant_id=tenant.id, deal_id=d.id, portal_person_id=100,
            person_name="Model Test", daily_cost=300,
        )
        db_session.add(r)
        await db_session.flush()
        loaded = await db_session.get(CrmDealResource, r.id)
        assert loaded.person_name == "Model Test"
        assert loaded.daily_cost == 300

    @pytest.mark.anyio
    async def test_37_deal_resource_default_status(self, db_session, tenant, stages):
        d = CrmDeal(tenant_id=tenant.id, name="Default Status", stage_id=stages[0].id)
        db_session.add(d)
        await db_session.flush()
        r = CrmDealResource(tenant_id=tenant.id, deal_id=d.id, portal_person_id=200)
        db_session.add(r)
        await db_session.flush()
        assert r.status == "assigned"


# ============================================================
# N. Deal with Products and Resources Combined
# ============================================================


class TestDealProductsResources:

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_38_tm_deal_full(self, mock_pc, client, owner_headers, stages, db_session, tenant, tm_product):
        mock_pc.get_person = AsyncMock(return_value={"error": "off"})
        # Create deal
        deal_resp = await client.post("/api/v1/crm/deals", json={
            "name": "TM Full Deal",
            "deal_type": "T&M",
            "portal_customer_id": 42,
        }, headers=owner_headers)
        deal_id = uuid.UUID(deal_resp.json()["id"])

        # Add TM product
        dp = CrmDealProduct(tenant_id=tenant.id, deal_id=deal_id, product_id=tm_product.id)
        db_session.add(dp)
        await db_session.flush()

        # Check requires
        req_resp = await client.get(f"/api/v1/crm/deals/{deal_id}/resources/requires", headers=owner_headers)
        assert req_resp.json()["requires_resources"] is True

        # Add resources
        await client.post(f"/api/v1/crm/deals/{deal_id}/resources", json={
            "portal_person_id": 1, "person_name": "Dev 1",
        }, headers=owner_headers)
        await client.post(f"/api/v1/crm/deals/{deal_id}/resources", json={
            "portal_person_id": 2, "person_name": "Dev 2",
        }, headers=owner_headers)

        list_resp = await client.get(f"/api/v1/crm/deals/{deal_id}/resources", headers=owner_headers)
        assert len(list_resp.json()) == 2

    @pytest.mark.anyio
    async def test_39_fixed_deal_no_resources(self, client, owner_headers, stages, db_session, tenant, fixed_product):
        deal_resp = await client.post("/api/v1/crm/deals", json={
            "name": "Fixed No Resources",
            "deal_type": "fixed",
        }, headers=owner_headers)
        deal_id = uuid.UUID(deal_resp.json()["id"])
        dp = CrmDealProduct(tenant_id=tenant.id, deal_id=deal_id, product_id=fixed_product.id)
        db_session.add(dp)
        await db_session.flush()
        req_resp = await client.get(f"/api/v1/crm/deals/{deal_id}/resources/requires", headers=owner_headers)
        assert req_resp.json()["requires_resources"] is False


# ============================================================
# O. Concurrency & Multiple Tenants
# ============================================================


class TestMultiTenant:

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_40_resources_tenant_isolated(self, mock_pc, db_session, tenant, stages):
        mock_pc.get_person = AsyncMock(return_value={"error": "off"})
        svc = DealResourceService(db_session)
        d = CrmDeal(tenant_id=tenant.id, name="Tenant A Deal", stage_id=stages[0].id)
        db_session.add(d)
        await db_session.flush()

        await svc.add_resource(d.id, tenant.id, {"portal_person_id": 1, "person_name": "Tenant A"})

        # Query with different tenant
        other_tenant = uuid.uuid4()
        resources = await svc.list_resources(d.id, other_tenant)
        assert len(resources) == 0


# ============================================================
# P. Additional CRUD Edge Cases
# ============================================================


class TestAdditionalCRUD:

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_41_add_many_resources(self, mock_pc, client, owner_headers, stages):
        mock_pc.get_person = AsyncMock(return_value={"error": "off"})
        deal_resp = await client.post("/api/v1/crm/deals", json={"name": "Many Res"}, headers=owner_headers)
        deal_id = deal_resp.json()["id"]
        for i in range(10):
            resp = await client.post(f"/api/v1/crm/deals/{deal_id}/resources", json={
                "portal_person_id": 100 + i, "person_name": f"Res {i}",
            }, headers=owner_headers)
            assert resp.status_code == 201
        list_resp = await client.get(f"/api/v1/crm/deals/{deal_id}/resources", headers=owner_headers)
        assert len(list_resp.json()) == 10

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_42_delete_all_resources(self, mock_pc, client, owner_headers, stages):
        mock_pc.get_person = AsyncMock(return_value={"error": "off"})
        deal_resp = await client.post("/api/v1/crm/deals", json={"name": "Del All"}, headers=owner_headers)
        deal_id = deal_resp.json()["id"]
        ids = []
        for i in range(3):
            r = await client.post(f"/api/v1/crm/deals/{deal_id}/resources", json={
                "portal_person_id": 200 + i, "person_name": f"Del {i}",
            }, headers=owner_headers)
            ids.append(r.json()["id"])
        for rid in ids:
            await client.delete(f"/api/v1/crm/deals/{deal_id}/resources/{rid}", headers=owner_headers)
        list_resp = await client.get(f"/api/v1/crm/deals/{deal_id}/resources", headers=owner_headers)
        assert list_resp.json() == []

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_43_update_resource_partial(self, mock_pc, client, owner_headers, stages):
        mock_pc.get_person = AsyncMock(return_value={"error": "off"})
        deal_resp = await client.post("/api/v1/crm/deals", json={"name": "Partial Upd"}, headers=owner_headers)
        deal_id = deal_resp.json()["id"]
        r = await client.post(f"/api/v1/crm/deals/{deal_id}/resources", json={
            "portal_person_id": 300, "person_name": "Partial", "role": "Dev", "daily_cost": 400,
        }, headers=owner_headers)
        rid = r.json()["id"]
        # Update only notes
        resp = await client.patch(f"/api/v1/crm/deals/{deal_id}/resources/{rid}", json={
            "notes": "Updated notes only",
        }, headers=owner_headers)
        data = resp.json()
        assert data["notes"] == "Updated notes only"
        assert data["role"] == "Dev"  # unchanged
        assert data["daily_cost"] == 400  # unchanged

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_44_resource_with_all_fields(self, mock_pc, client, owner_headers, stages):
        mock_pc.get_person = AsyncMock(return_value={"error": "off"})
        deal_resp = await client.post("/api/v1/crm/deals", json={"name": "All Fields"}, headers=owner_headers)
        deal_id = deal_resp.json()["id"]
        resp = await client.post(f"/api/v1/crm/deals/{deal_id}/resources", json={
            "portal_person_id": 400,
            "person_name": "Full Resource",
            "person_email": "full@test.it",
            "seniority": "Lead",
            "daily_cost": 500,
            "role": "Architect",
            "start_date": "2026-06-01",
            "end_date": "2026-12-31",
            "notes": "Top performer",
            "portal_activity_id": 77,
        }, headers=owner_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["person_name"] == "Full Resource"
        assert data["person_email"] == "full@test.it"
        assert data["seniority"] == "Lead"
        assert data["daily_cost"] == 500
        assert data["role"] == "Architect"
        assert data["start_date"] == "2026-06-01"
        assert data["end_date"] == "2026-12-31"
        assert data["notes"] == "Top performer"
        assert data["portal_activity_id"] == 77


# ============================================================
# Q. Deal List Filtering
# ============================================================


class TestDealListFiltering:

    @pytest.mark.anyio
    async def test_45_list_by_deal_type(self, client, owner_headers, stages):
        await client.post("/api/v1/crm/deals", json={"name": "TM1", "deal_type": "T&M"}, headers=owner_headers)
        await client.post("/api/v1/crm/deals", json={"name": "FX1", "deal_type": "fixed"}, headers=owner_headers)
        resp = await client.get("/api/v1/crm/deals?deal_type=T%26M", headers=owner_headers)
        deals = resp.json()["deals"]
        assert all(d["deal_type"] == "T&M" for d in deals)

    @pytest.mark.anyio
    async def test_46_list_by_stage(self, client, owner_headers, stages):
        resp = await client.get("/api/v1/crm/deals?stage=Nuovo%20Lead", headers=owner_headers)
        assert resp.status_code == 200


# ============================================================
# R. Portal Offer/Project with Stage
# ============================================================


class TestOfferProjectStage:

    @pytest.mark.anyio
    @patch("api.modules.portal.router.portal_client")
    async def test_47_offer_before_proposta(self, mock_pc, client, owner_headers, stages, db_session, tenant):
        d = CrmDeal(
            tenant_id=tenant.id, name="Pre Proposta", stage_id=stages[0].id,
            portal_customer_id=42, deal_type="T&M",
        )
        db_session.add(d)
        await db_session.flush()
        mock_pc.create_offer = AsyncMock(return_value={"id": 500})
        resp = await client.post(
            f"/api/v1/portal/offers/create-from-deal/{d.id}",
            json={},
            headers=owner_headers,
        )
        assert resp.json()["id"] == 500

    @pytest.mark.anyio
    @patch("api.modules.portal.router.portal_client")
    async def test_48_project_after_won(self, mock_pc, client, owner_headers, stages, db_session, tenant):
        won = [s for s in stages if s.is_won][0]
        d = CrmDeal(
            tenant_id=tenant.id, name="Won Project", stage_id=won.id,
            portal_customer_id=42, portal_offer_id=600,
        )
        db_session.add(d)
        await db_session.flush()
        mock_pc.get_offer = AsyncMock(return_value={"id": 600, "project_id": 700})
        resp = await client.post(
            f"/api/v1/portal/projects/create-from-deal/{d.id}",
            json={},
            headers=owner_headers,
        )
        assert resp.json()["project_id"] == 700


# ============================================================
# S. Activities
# ============================================================


class TestActivities:

    @pytest.mark.anyio
    async def test_49_create_activity(self, client, owner_headers, stages):
        deal_resp = await client.post("/api/v1/crm/deals", json={"name": "Activity Deal"}, headers=owner_headers)
        resp = await client.post("/api/v1/crm/activities", json={
            "deal_id": deal_resp.json()["id"],
            "type": "call",
            "subject": "Follow up on offer",
        }, headers=owner_headers)
        assert resp.status_code == 201

    @pytest.mark.anyio
    async def test_50_list_activities(self, client, owner_headers, stages):
        deal_resp = await client.post("/api/v1/crm/deals", json={"name": "Act List Deal"}, headers=owner_headers)
        deal_id = deal_resp.json()["id"]
        await client.post("/api/v1/crm/activities", json={
            "deal_id": deal_id, "type": "email", "subject": "Proposal sent",
        }, headers=owner_headers)
        resp = await client.get(f"/api/v1/crm/activities?deal_id={deal_id}", headers=owner_headers)
        assert resp.status_code == 200
        # At least the auto-logged stage change + our activity
        assert len(resp.json()) >= 1


# ============================================================
# T. Schema Validation
# ============================================================


class TestSchemaValidation:

    @pytest.mark.anyio
    async def test_51_deal_update_schema_accepts_portal_ids(self, client, owner_headers, stages):
        deal_resp = await client.post("/api/v1/crm/deals", json={"name": "Schema Deal"}, headers=owner_headers)
        deal_id = deal_resp.json()["id"]
        resp = await client.patch(f"/api/v1/crm/deals/{deal_id}", json={
            "portal_offer_id": 100,
            "portal_project_id": 200,
            "portal_customer_id": 300,
            "portal_customer_name": "Schema Corp",
        }, headers=owner_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["portal_offer_id"] == 100
        assert data["portal_project_id"] == 200
        assert data["portal_customer_id"] == 300
        assert data["portal_customer_name"] == "Schema Corp"


# ============================================================
# U. Stages & Pipeline
# ============================================================


class TestStagesPipeline:

    @pytest.mark.anyio
    async def test_52_get_stages(self, client, owner_headers, stages):
        resp = await client.get("/api/v1/crm/pipeline/stages", headers=owner_headers)
        assert resp.status_code == 200
        stage_names = [s["name"] for s in resp.json()]
        assert "Nuovo Lead" in stage_names
        assert "Confermato" in stage_names

    @pytest.mark.anyio
    async def test_53_pipeline_summary_structure(self, client, owner_headers, stages):
        resp = await client.get("/api/v1/crm/pipeline/summary", headers=owner_headers)
        data = resp.json()
        assert "total_deals" in data
        assert "total_value" in data
        assert "by_stage" in data


# ============================================================
# V. Documents
# ============================================================


class TestDocuments:

    @pytest.mark.anyio
    async def test_54_add_document(self, client, owner_headers, stages):
        deal_resp = await client.post("/api/v1/crm/deals", json={"name": "Doc Deal"}, headers=owner_headers)
        deal_id = deal_resp.json()["id"]
        resp = await client.post(f"/api/v1/crm/deals/{deal_id}/documents", json={
            "doc_type": "offerta",
            "name": "Offerta v1.pdf",
            "url": "https://drive.google.com/file/123",
        }, headers=owner_headers)
        assert resp.status_code == 201

    @pytest.mark.anyio
    async def test_55_list_documents(self, client, owner_headers, stages):
        deal_resp = await client.post("/api/v1/crm/deals", json={"name": "Doc List"}, headers=owner_headers)
        deal_id = deal_resp.json()["id"]
        await client.post(f"/api/v1/crm/deals/{deal_id}/documents", json={
            "doc_type": "contratto", "name": "Contract.pdf",
        }, headers=owner_headers)
        resp = await client.get(f"/api/v1/crm/deals/{deal_id}/documents", headers=owner_headers)
        assert resp.status_code == 200


# ============================================================
# W. Misc Edge Cases
# ============================================================


class TestMiscEdge:

    @pytest.mark.anyio
    async def test_56_create_deal_minimal(self, client, owner_headers, stages):
        resp = await client.post("/api/v1/crm/deals", json={"name": "Minimal"}, headers=owner_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["portal_offer_id"] is None
        assert data["portal_project_id"] is None
        assert data["portal_customer_id"] is None

    @pytest.mark.anyio
    async def test_57_delete_deal_with_resources(self, client, owner_headers, stages, db_session, tenant):
        deal_resp = await client.post("/api/v1/crm/deals", json={"name": "Del with Res"}, headers=owner_headers)
        deal_id = deal_resp.json()["id"]
        # Add resource directly
        r = CrmDealResource(
            tenant_id=tenant.id, deal_id=uuid.UUID(deal_id),
            portal_person_id=999, person_name="To Delete",
        )
        db_session.add(r)
        await db_session.flush()
        # Delete deal (should work even with resources)
        resp = await client.delete(f"/api/v1/crm/deals/{deal_id}", headers=owner_headers)
        assert resp.status_code == 200

    @pytest.mark.anyio
    @patch("api.modules.portal.router.portal_client")
    async def test_58_offer_no_daily_rate(self, mock_pc, client, owner_headers, stages, db_session, tenant):
        d = CrmDeal(
            tenant_id=tenant.id, name="No Rate", deal_type="spot",
            stage_id=stages[0].id, portal_customer_id=42,
        )
        db_session.add(d)
        await db_session.flush()
        captured = {}
        async def capture(payload):
            captured.update(payload)
            return {"id": 999}
        mock_pc.create_offer = AsyncMock(side_effect=capture)
        await client.post(
            f"/api/v1/portal/offers/create-from-deal/{d.id}",
            json={},
            headers=owner_headers,
        )
        assert captured["rate"] is None

    @pytest.mark.anyio
    async def test_59_pending_orders(self, client, owner_headers, stages):
        resp = await client.get("/api/v1/crm/orders/pending", headers=owner_headers)
        assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_60_deal_companies(self, client, owner_headers):
        resp = await client.get("/api/v1/crm/companies", headers=owner_headers)
        assert resp.status_code == 200


# ============================================================
# X. Combined E2E Scenarios
# ============================================================


class TestCombinedScenarios:

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    @patch("api.modules.portal.router.portal_client")
    async def test_61_tm_deal_complete(self, mock_portal, mock_res, client, owner_headers, stages, db_session, tenant, tm_product):
        mock_res.get_person = AsyncMock(return_value={
            "firstName": "Luca", "lastName": "Expert",
            "EmploymentContracts": [{"dailyCost": 450, "endDate": None}],
        })
        # Create
        d = await client.post("/api/v1/crm/deals", json={
            "name": "Complete TM",
            "deal_type": "T&M",
            "expected_revenue": 90000,
            "daily_rate": 500,
            "estimated_days": 180,
            "portal_customer_id": 42,
            "portal_customer_name": "Complete Corp",
        }, headers=owner_headers)
        did = d.json()["id"]

        # Add product
        dp = CrmDealProduct(tenant_id=tenant.id, deal_id=uuid.UUID(did), product_id=tm_product.id)
        db_session.add(dp)
        await db_session.flush()

        # Check requires
        req = await client.get(f"/api/v1/crm/deals/{did}/resources/requires", headers=owner_headers)
        assert req.json()["requires_resources"] is True

        # Move to Proposta
        proposta = [s for s in stages if s.name == "Proposta Inviata"][0]
        await client.patch(f"/api/v1/crm/deals/{did}", json={"stage_id": str(proposta.id)}, headers=owner_headers)

        # Create offer
        mock_portal.create_offer = AsyncMock(return_value={"id": 5000})
        await client.post(f"/api/v1/portal/offers/create-from-deal/{did}", json={}, headers=owner_headers)

        # Move to Ordine Ricevuto
        await client.post(f"/api/v1/crm/deals/{did}/order", json={"order_type": "po"}, headers=owner_headers)

        # Confirm order
        await client.post(f"/api/v1/crm/deals/{did}/order/confirm", headers=owner_headers)

        # Link project
        mock_portal.get_offer = AsyncMock(return_value={"id": 5000, "project_id": 6000})
        await client.post(f"/api/v1/portal/projects/create-from-deal/{did}", json={}, headers=owner_headers)

        # Add resources
        await client.post(f"/api/v1/crm/deals/{did}/resources", json={
            "portal_person_id": 101, "role": "Lead Dev",
        }, headers=owner_headers)
        await client.post(f"/api/v1/crm/deals/{did}/resources", json={
            "portal_person_id": 102, "role": "Dev",
        }, headers=owner_headers)

        # Final check
        final = await client.get(f"/api/v1/crm/deals/{did}", headers=owner_headers)
        data = final.json()
        assert data["portal_offer_id"] == 5000
        assert data["portal_project_id"] == 6000
        assert data["stage"] == "Confermato"

        res = await client.get(f"/api/v1/crm/deals/{did}/resources", headers=owner_headers)
        assert len(res.json()) == 2

    @pytest.mark.anyio
    @patch("api.modules.portal.router.portal_client")
    async def test_62_fixed_deal_complete(self, mock_portal, client, owner_headers, stages, db_session, tenant, fixed_product):
        # Create
        d = await client.post("/api/v1/crm/deals", json={
            "name": "Complete Fixed",
            "deal_type": "fixed",
            "expected_revenue": 40000,
            "portal_customer_id": 55,
            "portal_customer_name": "Fixed Corp",
        }, headers=owner_headers)
        did = d.json()["id"]

        # Add product
        dp = CrmDealProduct(tenant_id=tenant.id, deal_id=uuid.UUID(did), product_id=fixed_product.id)
        db_session.add(dp)
        await db_session.flush()

        # Check requires
        req = await client.get(f"/api/v1/crm/deals/{did}/resources/requires", headers=owner_headers)
        assert req.json()["requires_resources"] is False

        # Create offer
        captured = {}
        async def capture(p):
            captured.update(p)
            return {"id": 7000}
        mock_portal.create_offer = AsyncMock(side_effect=capture)
        await client.post(f"/api/v1/portal/offers/create-from-deal/{did}", json={}, headers=owner_headers)
        assert captured["billing_type"] == "LumpSum"

    @pytest.mark.anyio
    async def test_63_deal_without_portal_customer(self, client, owner_headers, stages):
        resp = await client.post("/api/v1/crm/deals", json={
            "name": "No Portal Customer",
        }, headers=owner_headers)
        assert resp.status_code == 201
        assert resp.json()["portal_customer_id"] is None

    @pytest.mark.anyio
    async def test_64_deal_get_includes_new_fields(self, client, owner_headers, stages):
        resp = await client.post("/api/v1/crm/deals", json={
            "name": "New Fields Check",
        }, headers=owner_headers)
        deal_id = resp.json()["id"]
        get_resp = await client.get(f"/api/v1/crm/deals/{deal_id}", headers=owner_headers)
        data = get_resp.json()
        assert "portal_offer_id" in data
        assert "requires_resources" in data

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_65_resource_date_range(self, mock_pc, client, owner_headers, stages):
        mock_pc.get_person = AsyncMock(return_value={"error": "off"})
        deal_resp = await client.post("/api/v1/crm/deals", json={"name": "Date Range"}, headers=owner_headers)
        did = deal_resp.json()["id"]
        resp = await client.post(f"/api/v1/crm/deals/{did}/resources", json={
            "portal_person_id": 500,
            "person_name": "Date Range Test",
            "start_date": "2026-01-01",
            "end_date": "2026-06-30",
        }, headers=owner_headers)
        assert resp.json()["start_date"] == "2026-01-01"
        assert resp.json()["end_date"] == "2026-06-30"


# ============================================================
# Y. Additional tests to reach ~75
# ============================================================


class TestAdditionalE2E:

    @pytest.mark.anyio
    async def test_66_deal_delete(self, client, owner_headers, stages):
        resp = await client.post("/api/v1/crm/deals", json={"name": "To Delete"}, headers=owner_headers)
        did = resp.json()["id"]
        del_resp = await client.delete(f"/api/v1/crm/deals/{did}", headers=owner_headers)
        assert del_resp.status_code == 200

    @pytest.mark.anyio
    async def test_67_deal_delete_not_found(self, client, owner_headers):
        resp = await client.delete(f"/api/v1/crm/deals/{uuid.uuid4()}", headers=owner_headers)
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_68_contact_crud(self, client, owner_headers):
        # Create
        resp = await client.post("/api/v1/crm/contacts", json={
            "name": "E2E Contact",
            "email": "e2e@test.it",
            "type": "prospect",
        }, headers=owner_headers)
        assert resp.status_code == 201
        cid = resp.json()["id"]
        # Update
        upd = await client.patch(f"/api/v1/crm/contacts/{cid}", json={"type": "cliente"}, headers=owner_headers)
        assert upd.json()["type"] == "cliente"
        # Delete
        del_resp = await client.delete(f"/api/v1/crm/contacts/{cid}", headers=owner_headers)
        assert del_resp.status_code == 200

    @pytest.mark.anyio
    async def test_69_company_crud(self, client, owner_headers):
        resp = await client.post("/api/v1/crm/companies", json={
            "name": "E2E Company",
            "type": "lead",
        }, headers=owner_headers)
        assert resp.status_code == 201

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_70_resource_response_format(self, mock_pc, client, owner_headers, stages):
        mock_pc.get_person = AsyncMock(return_value={"error": "off"})
        deal_resp = await client.post("/api/v1/crm/deals", json={"name": "Format Check"}, headers=owner_headers)
        did = deal_resp.json()["id"]
        resp = await client.post(f"/api/v1/crm/deals/{did}/resources", json={
            "portal_person_id": 999,
            "person_name": "Format",
        }, headers=owner_headers)
        data = resp.json()
        # Check UUID format
        assert len(data["id"]) == 36
        assert "-" in data["id"]

    @pytest.mark.anyio
    async def test_71_unauthenticated_deal_create(self, client, stages):
        resp = await client.post("/api/v1/crm/deals", json={"name": "Unauth"})
        assert resp.status_code in (401, 403)

    @pytest.mark.anyio
    async def test_72_unauthenticated_resources_list(self, client, stages):
        resp = await client.get(f"/api/v1/crm/deals/{uuid.uuid4()}/resources")
        assert resp.status_code in (401, 403)

    @pytest.mark.anyio
    async def test_73_unauthenticated_offer_create(self, client):
        resp = await client.post(f"/api/v1/portal/offers/create-from-deal/{uuid.uuid4()}", json={})
        assert resp.status_code in (401, 403)

    @pytest.mark.anyio
    async def test_74_unauthenticated_project_create(self, client):
        resp = await client.post(f"/api/v1/portal/projects/create-from-deal/{uuid.uuid4()}", json={})
        assert resp.status_code in (401, 403)

    @pytest.mark.anyio
    async def test_75_deal_update_name(self, client, owner_headers, stages):
        deal_resp = await client.post("/api/v1/crm/deals", json={"name": "Original"}, headers=owner_headers)
        did = deal_resp.json()["id"]
        resp = await client.patch(f"/api/v1/crm/deals/{did}", json={"name": "Renamed"}, headers=owner_headers)
        assert resp.json()["name"] == "Renamed"
