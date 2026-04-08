"""Test suite for Portal Offer Flow — Sprint A.

Tests create-offer-from-deal and create-project-from-deal endpoints.
~40 tests.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import CrmDeal, CrmPipelineStage, Tenant, User
from api.modules.crm.service import CRMService
from tests.conftest import _hash_pw, get_auth_token


# ── Fixtures ──────────────────────────────────────

@pytest.fixture
async def owner(db_session: AsyncSession, tenant: Tenant) -> User:
    u = User(
        email="offer.owner@test.it", password_hash=_hash_pw("Password1"),
        name="Offer Owner", role="owner", email_verified=True, tenant_id=tenant.id,
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest.fixture
async def owner_headers(client: AsyncClient, owner: User) -> dict:
    token = await get_auth_token(client, "offer.owner@test.it", "Password1")
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
async def deal_with_customer(db_session: AsyncSession, tenant: Tenant, stages) -> CrmDeal:
    d = CrmDeal(
        tenant_id=tenant.id,
        name="Offer Flow Deal",
        deal_type="T&M",
        expected_revenue=100000,
        daily_rate=600,
        estimated_days=200,
        stage_id=stages[2].id,  # Proposta Inviata
        portal_customer_id=42,
        portal_customer_name="ACME Corp",
    )
    db_session.add(d)
    await db_session.flush()
    return d


@pytest.fixture
async def deal_without_customer(db_session: AsyncSession, tenant: Tenant, stages) -> CrmDeal:
    d = CrmDeal(
        tenant_id=tenant.id,
        name="No Customer Deal",
        deal_type="fixed",
        expected_revenue=50000,
        stage_id=stages[0].id,
    )
    db_session.add(d)
    await db_session.flush()
    return d


@pytest.fixture
async def deal_with_offer(db_session: AsyncSession, tenant: Tenant, stages) -> CrmDeal:
    d = CrmDeal(
        tenant_id=tenant.id,
        name="Offer Exists Deal",
        deal_type="T&M",
        expected_revenue=80000,
        daily_rate=400,
        estimated_days=200,
        stage_id=stages[2].id,
        portal_customer_id=42,
        portal_customer_name="ACME Corp",
        portal_offer_id=99,
    )
    db_session.add(d)
    await db_session.flush()
    return d


# ============================================================
# A. Create Offer From Deal
# ============================================================


class TestCreateOfferFromDeal:

    @pytest.mark.anyio
    @patch("api.modules.portal.router.portal_client")
    async def test_01_create_offer_success(self, mock_pc, client, owner_headers, deal_with_customer):
        mock_pc.create_offer = AsyncMock(return_value={"id": 777, "name": "Offer Flow Deal"})
        resp = await client.post(
            f"/api/v1/portal/offers/create-from-deal/{deal_with_customer.id}",
            json={"project_code": "ACM-2026-001", "accountManager_id": 5},
            headers=owner_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 777

    @pytest.mark.anyio
    @patch("api.modules.portal.router.portal_client")
    async def test_02_offer_saves_portal_offer_id(self, mock_pc, client, owner_headers, deal_with_customer, db_session):
        mock_pc.create_offer = AsyncMock(return_value={"id": 888})
        await client.post(
            f"/api/v1/portal/offers/create-from-deal/{deal_with_customer.id}",
            json={},
            headers=owner_headers,
        )
        result = await db_session.execute(
            select(CrmDeal).where(CrmDeal.id == deal_with_customer.id)
        )
        deal = result.scalar_one()
        assert deal.portal_offer_id == 888

    @pytest.mark.anyio
    async def test_03_offer_deal_not_found(self, client, owner_headers):
        fake_id = str(uuid.uuid4())
        resp = await client.post(
            f"/api/v1/portal/offers/create-from-deal/{fake_id}",
            json={},
            headers=owner_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["error"] == "Deal not found"

    @pytest.mark.anyio
    async def test_04_offer_no_customer(self, client, owner_headers, deal_without_customer):
        resp = await client.post(
            f"/api/v1/portal/offers/create-from-deal/{deal_without_customer.id}",
            json={},
            headers=owner_headers,
        )
        assert resp.status_code == 200
        assert "no Portal customer" in resp.json()["error"]

    @pytest.mark.anyio
    @patch("api.modules.portal.router.portal_client")
    async def test_05_offer_billing_type_tm(self, mock_pc, client, owner_headers, deal_with_customer):
        captured = {}
        async def capture_offer(payload):
            captured.update(payload)
            return {"id": 100}
        mock_pc.create_offer = AsyncMock(side_effect=capture_offer)
        await client.post(
            f"/api/v1/portal/offers/create-from-deal/{deal_with_customer.id}",
            json={},
            headers=owner_headers,
        )
        assert captured["billing_type"] == "Daily"  # T&M => Daily

    @pytest.mark.anyio
    @patch("api.modules.portal.router.portal_client")
    async def test_06_offer_billing_type_fixed(self, mock_pc, client, owner_headers, db_session, tenant, stages):
        d = CrmDeal(
            tenant_id=tenant.id, name="Fixed Deal", deal_type="fixed",
            expected_revenue=30000, stage_id=stages[0].id,
            portal_customer_id=10, portal_customer_name="Fixed Co",
        )
        db_session.add(d)
        await db_session.flush()

        captured = {}
        async def capture_offer(payload):
            captured.update(payload)
            return {"id": 101}
        mock_pc.create_offer = AsyncMock(side_effect=capture_offer)
        await client.post(
            f"/api/v1/portal/offers/create-from-deal/{d.id}",
            json={},
            headers=owner_headers,
        )
        assert captured["billing_type"] == "LumpSum"

    @pytest.mark.anyio
    @patch("api.modules.portal.router.portal_client")
    async def test_07_offer_custom_billing_override(self, mock_pc, client, owner_headers, deal_with_customer):
        captured = {}
        async def capture_offer(payload):
            captured.update(payload)
            return {"id": 102}
        mock_pc.create_offer = AsyncMock(side_effect=capture_offer)
        await client.post(
            f"/api/v1/portal/offers/create-from-deal/{deal_with_customer.id}",
            json={"billing_type": "CustomRate"},
            headers=owner_headers,
        )
        assert captured["billing_type"] == "CustomRate"

    @pytest.mark.anyio
    @patch("api.modules.portal.router.portal_client")
    async def test_08_offer_includes_deal_financials(self, mock_pc, client, owner_headers, deal_with_customer):
        captured = {}
        async def capture_offer(payload):
            captured.update(payload)
            return {"id": 103}
        mock_pc.create_offer = AsyncMock(side_effect=capture_offer)
        await client.post(
            f"/api/v1/portal/offers/create-from-deal/{deal_with_customer.id}",
            json={},
            headers=owner_headers,
        )
        assert captured["rate"] == 600
        assert captured["days"] == 200
        assert captured["amount"] == 100000

    @pytest.mark.anyio
    @patch("api.modules.portal.router.portal_client")
    async def test_09_offer_uses_deal_name_as_default(self, mock_pc, client, owner_headers, deal_with_customer):
        captured = {}
        async def capture_offer(payload):
            captured.update(payload)
            return {"id": 104}
        mock_pc.create_offer = AsyncMock(side_effect=capture_offer)
        await client.post(
            f"/api/v1/portal/offers/create-from-deal/{deal_with_customer.id}",
            json={},
            headers=owner_headers,
        )
        assert captured["name"] == "Offer Flow Deal"

    @pytest.mark.anyio
    @patch("api.modules.portal.router.portal_client")
    async def test_10_offer_custom_name(self, mock_pc, client, owner_headers, deal_with_customer):
        captured = {}
        async def capture_offer(payload):
            captured.update(payload)
            return {"id": 105}
        mock_pc.create_offer = AsyncMock(side_effect=capture_offer)
        await client.post(
            f"/api/v1/portal/offers/create-from-deal/{deal_with_customer.id}",
            json={"name": "Custom Offer Name"},
            headers=owner_headers,
        )
        assert captured["name"] == "Custom Offer Name"

    @pytest.mark.anyio
    @patch("api.modules.portal.router.portal_client")
    async def test_11_offer_portal_error(self, mock_pc, client, owner_headers, deal_with_customer):
        mock_pc.create_offer = AsyncMock(return_value={"error": "HTTP 500", "detail": "Server error"})
        resp = await client.post(
            f"/api/v1/portal/offers/create-from-deal/{deal_with_customer.id}",
            json={},
            headers=owner_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "error" in data

    @pytest.mark.anyio
    @patch("api.modules.portal.router.portal_client")
    async def test_12_offer_portal_error_no_save(self, mock_pc, client, owner_headers, deal_with_customer, db_session):
        mock_pc.create_offer = AsyncMock(return_value={"error": "HTTP 500"})
        await client.post(
            f"/api/v1/portal/offers/create-from-deal/{deal_with_customer.id}",
            json={},
            headers=owner_headers,
        )
        result = await db_session.execute(
            select(CrmDeal).where(CrmDeal.id == deal_with_customer.id)
        )
        deal = result.scalar_one()
        assert deal.portal_offer_id is None  # not saved

    @pytest.mark.anyio
    @patch("api.modules.portal.router.portal_client")
    async def test_13_offer_includes_customer_id(self, mock_pc, client, owner_headers, deal_with_customer):
        captured = {}
        async def capture_offer(payload):
            captured.update(payload)
            return {"id": 106}
        mock_pc.create_offer = AsyncMock(side_effect=capture_offer)
        await client.post(
            f"/api/v1/portal/offers/create-from-deal/{deal_with_customer.id}",
            json={},
            headers=owner_headers,
        )
        assert captured["customer_id"] == 42

    @pytest.mark.anyio
    @patch("api.modules.portal.router.portal_client")
    async def test_14_offer_outcome_type_w(self, mock_pc, client, owner_headers, deal_with_customer):
        captured = {}
        async def capture_offer(payload):
            captured.update(payload)
            return {"id": 107}
        mock_pc.create_offer = AsyncMock(side_effect=capture_offer)
        await client.post(
            f"/api/v1/portal/offers/create-from-deal/{deal_with_customer.id}",
            json={},
            headers=owner_headers,
        )
        assert captured["OutcomeType"] == "W"

    @pytest.mark.anyio
    @patch("api.modules.portal.router.portal_client")
    async def test_15_offer_year_default(self, mock_pc, client, owner_headers, deal_with_customer):
        from datetime import datetime
        captured = {}
        async def capture_offer(payload):
            captured.update(payload)
            return {"id": 108}
        mock_pc.create_offer = AsyncMock(side_effect=capture_offer)
        await client.post(
            f"/api/v1/portal/offers/create-from-deal/{deal_with_customer.id}",
            json={},
            headers=owner_headers,
        )
        assert captured["year"] == datetime.now().year

    @pytest.mark.anyio
    @patch("api.modules.portal.router.portal_client")
    async def test_16_offer_year_custom(self, mock_pc, client, owner_headers, deal_with_customer):
        captured = {}
        async def capture_offer(payload):
            captured.update(payload)
            return {"id": 109}
        mock_pc.create_offer = AsyncMock(side_effect=capture_offer)
        await client.post(
            f"/api/v1/portal/offers/create-from-deal/{deal_with_customer.id}",
            json={"year": 2027},
            headers=owner_headers,
        )
        assert captured["year"] == 2027

    @pytest.mark.anyio
    async def test_17_offer_unauthenticated(self, client, deal_with_customer):
        resp = await client.post(
            f"/api/v1/portal/offers/create-from-deal/{deal_with_customer.id}",
            json={},
        )
        assert resp.status_code in (401, 403)

    @pytest.mark.anyio
    @patch("api.modules.portal.router.portal_client")
    async def test_18_offer_deal_no_rate(self, mock_pc, client, owner_headers, db_session, tenant, stages):
        d = CrmDeal(
            tenant_id=tenant.id, name="No Rate", deal_type="T&M",
            stage_id=stages[0].id, portal_customer_id=10,
        )
        db_session.add(d)
        await db_session.flush()

        captured = {}
        async def capture_offer(payload):
            captured.update(payload)
            return {"id": 110}
        mock_pc.create_offer = AsyncMock(side_effect=capture_offer)
        await client.post(
            f"/api/v1/portal/offers/create-from-deal/{d.id}",
            json={},
            headers=owner_headers,
        )
        assert captured["rate"] is None
        assert captured["days"] is None

    @pytest.mark.anyio
    @patch("api.modules.portal.router.portal_client")
    async def test_19_offer_project_type_and_location(self, mock_pc, client, owner_headers, deal_with_customer):
        captured = {}
        async def capture_offer(payload):
            captured.update(payload)
            return {"id": 111}
        mock_pc.create_offer = AsyncMock(side_effect=capture_offer)
        await client.post(
            f"/api/v1/portal/offers/create-from-deal/{deal_with_customer.id}",
            json={"project_type_id": 3, "location_id": 7},
            headers=owner_headers,
        )
        assert captured["project_type_id"] == 3
        assert captured["location_id"] == 7

    @pytest.mark.anyio
    @patch("api.modules.portal.router.portal_client")
    async def test_20_offer_other_details(self, mock_pc, client, owner_headers, deal_with_customer):
        captured = {}
        async def capture_offer(payload):
            captured.update(payload)
            return {"id": 112}
        mock_pc.create_offer = AsyncMock(side_effect=capture_offer)
        await client.post(
            f"/api/v1/portal/offers/create-from-deal/{deal_with_customer.id}",
            json={"other_details": "Special terms apply"},
            headers=owner_headers,
        )
        assert captured["other_details"] == "Special terms apply"


# ============================================================
# B. Create Project From Deal
# ============================================================


class TestCreateProjectFromDeal:

    @pytest.mark.anyio
    @patch("api.modules.portal.router.portal_client")
    async def test_21_project_success(self, mock_pc, client, owner_headers, deal_with_offer, db_session):
        mock_pc.get_offer = AsyncMock(return_value={"id": 99, "project_id": 555})
        resp = await client.post(
            f"/api/v1/portal/projects/create-from-deal/{deal_with_offer.id}",
            json={},
            headers=owner_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["project_id"] == 555
        assert data["from"] == "existing_offer"

    @pytest.mark.anyio
    @patch("api.modules.portal.router.portal_client")
    async def test_22_project_saves_portal_project_id(self, mock_pc, client, owner_headers, deal_with_offer, db_session):
        mock_pc.get_offer = AsyncMock(return_value={"id": 99, "project_id": 556})
        await client.post(
            f"/api/v1/portal/projects/create-from-deal/{deal_with_offer.id}",
            json={},
            headers=owner_headers,
        )
        result = await db_session.execute(
            select(CrmDeal).where(CrmDeal.id == deal_with_offer.id)
        )
        deal = result.scalar_one()
        assert deal.portal_project_id == 556

    @pytest.mark.anyio
    async def test_23_project_no_offer(self, client, owner_headers, deal_with_customer):
        resp = await client.post(
            f"/api/v1/portal/projects/create-from-deal/{deal_with_customer.id}",
            json={},
            headers=owner_headers,
        )
        assert resp.status_code == 200
        assert "Create an offer first" in resp.json()["error"]

    @pytest.mark.anyio
    async def test_24_project_deal_not_found(self, client, owner_headers):
        fake_id = str(uuid.uuid4())
        resp = await client.post(
            f"/api/v1/portal/projects/create-from-deal/{fake_id}",
            json={},
            headers=owner_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["error"] == "Deal not found"

    @pytest.mark.anyio
    @patch("api.modules.portal.router.portal_client")
    async def test_25_project_offer_no_project(self, mock_pc, client, owner_headers, deal_with_offer):
        mock_pc.get_offer = AsyncMock(return_value={"id": 99, "name": "No project yet"})
        resp = await client.post(
            f"/api/v1/portal/projects/create-from-deal/{deal_with_offer.id}",
            json={},
            headers=owner_headers,
        )
        assert resp.status_code == 200
        assert "No project found" in resp.json()["error"]

    @pytest.mark.anyio
    @patch("api.modules.portal.router.portal_client")
    async def test_26_project_offer_error(self, mock_pc, client, owner_headers, deal_with_offer):
        mock_pc.get_offer = AsyncMock(return_value={"error": "HTTP 500"})
        resp = await client.post(
            f"/api/v1/portal/projects/create-from-deal/{deal_with_offer.id}",
            json={},
            headers=owner_headers,
        )
        assert resp.status_code == 200
        assert "No project found" in resp.json()["error"]

    @pytest.mark.anyio
    @patch("api.modules.portal.router.portal_client")
    async def test_27_project_with_projectId_camel(self, mock_pc, client, owner_headers, deal_with_offer, db_session):
        mock_pc.get_offer = AsyncMock(return_value={"id": 99, "projectId": 557})
        resp = await client.post(
            f"/api/v1/portal/projects/create-from-deal/{deal_with_offer.id}",
            json={},
            headers=owner_headers,
        )
        data = resp.json()
        assert data["project_id"] == 557

    @pytest.mark.anyio
    async def test_28_project_unauthenticated(self, client, deal_with_offer):
        resp = await client.post(
            f"/api/v1/portal/projects/create-from-deal/{deal_with_offer.id}",
            json={},
        )
        assert resp.status_code in (401, 403)


# ============================================================
# C. Full Offer -> Project Flow
# ============================================================


class TestOfferToProjectFlow:

    @pytest.mark.anyio
    @patch("api.modules.portal.router.portal_client")
    async def test_29_full_flow(self, mock_pc, client, owner_headers, deal_with_customer, db_session):
        # Step 1: Create offer
        mock_pc.create_offer = AsyncMock(return_value={"id": 1000})
        resp1 = await client.post(
            f"/api/v1/portal/offers/create-from-deal/{deal_with_customer.id}",
            json={"project_code": "FLOW-001"},
            headers=owner_headers,
        )
        assert resp1.json()["id"] == 1000

        # Verify offer_id saved
        await db_session.refresh(deal_with_customer)
        assert deal_with_customer.portal_offer_id == 1000

        # Step 2: Create project from offer
        mock_pc.get_offer = AsyncMock(return_value={"id": 1000, "project_id": 2000})
        resp2 = await client.post(
            f"/api/v1/portal/projects/create-from-deal/{deal_with_customer.id}",
            json={},
            headers=owner_headers,
        )
        assert resp2.json()["project_id"] == 2000

        # Verify project_id saved
        await db_session.refresh(deal_with_customer)
        assert deal_with_customer.portal_project_id == 2000

    @pytest.mark.anyio
    @patch("api.modules.portal.router.portal_client")
    async def test_30_deal_dict_after_offer(self, mock_pc, client, owner_headers, deal_with_customer, db_session):
        mock_pc.create_offer = AsyncMock(return_value={"id": 1001})
        await client.post(
            f"/api/v1/portal/offers/create-from-deal/{deal_with_customer.id}",
            json={},
            headers=owner_headers,
        )
        # Get deal via CRM endpoint
        resp = await client.get(
            f"/api/v1/crm/deals/{deal_with_customer.id}",
            headers=owner_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["portal_offer_id"] == 1001


# ============================================================
# D. Update Deal portal_offer_id via CRM
# ============================================================


class TestDealUpdatePortalIds:

    @pytest.mark.anyio
    async def test_31_update_deal_portal_offer_id(self, client, owner_headers, deal_with_customer, db_session):
        resp = await client.patch(
            f"/api/v1/crm/deals/{deal_with_customer.id}",
            json={"portal_offer_id": 999},
            headers=owner_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["portal_offer_id"] == 999

    @pytest.mark.anyio
    async def test_32_update_deal_portal_project_id(self, client, owner_headers, deal_with_customer, db_session):
        resp = await client.patch(
            f"/api/v1/crm/deals/{deal_with_customer.id}",
            json={"portal_project_id": 555},
            headers=owner_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["portal_project_id"] == 555

    @pytest.mark.anyio
    async def test_33_update_both_ids(self, client, owner_headers, deal_with_customer, db_session):
        resp = await client.patch(
            f"/api/v1/crm/deals/{deal_with_customer.id}",
            json={"portal_offer_id": 100, "portal_project_id": 200},
            headers=owner_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["portal_offer_id"] == 100
        assert data["portal_project_id"] == 200

    @pytest.mark.anyio
    async def test_34_deal_keeps_offer_id(self, client, owner_headers, deal_with_offer, db_session):
        resp = await client.get(
            f"/api/v1/crm/deals/{deal_with_offer.id}",
            headers=owner_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["portal_offer_id"] == 99

    @pytest.mark.anyio
    async def test_35_deal_list_includes_offer_id(self, client, owner_headers, deal_with_offer):
        resp = await client.get("/api/v1/crm/deals", headers=owner_headers)
        assert resp.status_code == 200
        deals = resp.json()["deals"]
        found = [d for d in deals if d["portal_offer_id"] == 99]
        assert len(found) == 1


# ============================================================
# E. Edge Cases
# ============================================================


class TestOfferFlowEdgeCases:

    @pytest.mark.anyio
    @patch("api.modules.portal.router.portal_client")
    async def test_36_offer_null_result(self, mock_pc, client, owner_headers, deal_with_customer):
        mock_pc.create_offer = AsyncMock(return_value=None)
        resp = await client.post(
            f"/api/v1/portal/offers/create-from-deal/{deal_with_customer.id}",
            json={},
            headers=owner_headers,
        )
        # Should not crash
        assert resp.status_code == 200

    @pytest.mark.anyio
    @patch("api.modules.portal.router.portal_client")
    async def test_37_offer_empty_dict_result(self, mock_pc, client, owner_headers, deal_with_customer):
        mock_pc.create_offer = AsyncMock(return_value={})
        resp = await client.post(
            f"/api/v1/portal/offers/create-from-deal/{deal_with_customer.id}",
            json={},
            headers=owner_headers,
        )
        assert resp.status_code == 200

    @pytest.mark.anyio
    @patch("api.modules.portal.router.portal_client")
    async def test_38_project_null_offer(self, mock_pc, client, owner_headers, deal_with_offer):
        mock_pc.get_offer = AsyncMock(return_value=None)
        resp = await client.post(
            f"/api/v1/portal/projects/create-from-deal/{deal_with_offer.id}",
            json={},
            headers=owner_headers,
        )
        assert resp.status_code == 200
        assert "No project found" in resp.json()["error"]

    @pytest.mark.anyio
    @patch("api.modules.portal.router.portal_client")
    async def test_39_offer_with_zero_revenue(self, mock_pc, client, owner_headers, db_session, tenant, stages):
        d = CrmDeal(
            tenant_id=tenant.id, name="Zero Rev", deal_type="spot",
            expected_revenue=0, stage_id=stages[0].id,
            portal_customer_id=77,
        )
        db_session.add(d)
        await db_session.flush()

        captured = {}
        async def capture_offer(payload):
            captured.update(payload)
            return {"id": 300}
        mock_pc.create_offer = AsyncMock(side_effect=capture_offer)
        await client.post(
            f"/api/v1/portal/offers/create-from-deal/{d.id}",
            json={},
            headers=owner_headers,
        )
        assert captured["amount"] is None  # 0 is falsy

    @pytest.mark.anyio
    @patch("api.modules.portal.router.portal_client")
    async def test_40_idempotent_offer(self, mock_pc, client, owner_headers, deal_with_customer, db_session):
        """Creating an offer twice should overwrite portal_offer_id."""
        mock_pc.create_offer = AsyncMock(return_value={"id": 111})
        await client.post(
            f"/api/v1/portal/offers/create-from-deal/{deal_with_customer.id}",
            json={},
            headers=owner_headers,
        )
        mock_pc.create_offer = AsyncMock(return_value={"id": 222})
        await client.post(
            f"/api/v1/portal/offers/create-from-deal/{deal_with_customer.id}",
            json={},
            headers=owner_headers,
        )
        await db_session.refresh(deal_with_customer)
        assert deal_with_customer.portal_offer_id == 222
