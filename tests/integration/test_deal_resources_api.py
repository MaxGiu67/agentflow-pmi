"""Test suite for Deal Resources API — Sprint A.

Tests CRUD operations for assigning Portal persons to deals,
plus check_requires_resources logic.
~50 tests.
"""

import uuid
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import (
    CrmDeal, CrmDealProduct, CrmDealResource, CrmPipelineStage,
    CrmProduct, CrmProductCategory, Tenant, User,
)
from api.modules.crm.service import CRMService
from api.modules.deal_resources.service import DealResourceService
from tests.conftest import _hash_pw, get_auth_token


# ── Fixtures ──────────────────────────────────────

@pytest.fixture
async def owner(db_session: AsyncSession, tenant: Tenant) -> User:
    u = User(
        email="res.owner@test.it", password_hash=_hash_pw("Password1"),
        name="Resource Owner", role="owner", email_verified=True, tenant_id=tenant.id,
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest.fixture
async def owner_headers(client: AsyncClient, owner: User) -> dict:
    token = await get_auth_token(client, "res.owner@test.it", "Password1")
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
async def deal(db_session: AsyncSession, tenant: Tenant, stages) -> CrmDeal:
    d = CrmDeal(
        tenant_id=tenant.id,
        name="Test Resource Deal",
        deal_type="T&M",
        expected_revenue=50000,
        daily_rate=500,
        estimated_days=100,
        stage_id=stages[0].id,
        portal_customer_id=42,
        portal_customer_name="ACME Corp",
    )
    db_session.add(d)
    await db_session.flush()
    return d


@pytest.fixture
async def svc(db_session: AsyncSession) -> DealResourceService:
    return DealResourceService(db_session)


MOCK_PERSON = {
    "id": 101,
    "firstName": "Mario",
    "lastName": "Rossi",
    "privateEmail": "mario.rossi@test.it",
    "Seniority": {"description": "Senior"},
    "EmploymentContracts": [
        {
            "dailyCost": 350.0,
            "endDate": None,  # active contract
        }
    ],
}


# ============================================================
# A. Service Layer — Direct Tests
# ============================================================


class TestDealResourceServiceBasic:

    @pytest.mark.anyio
    async def test_01_list_empty(self, svc: DealResourceService, deal: CrmDeal, tenant: Tenant):
        result = await svc.list_resources(deal.id, tenant.id)
        assert result == []

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_02_add_resource(self, mock_pc, svc: DealResourceService, deal: CrmDeal, tenant: Tenant):
        mock_pc.get_person = AsyncMock(return_value=MOCK_PERSON)
        result = await svc.add_resource(deal.id, tenant.id, {"portal_person_id": 101, "role": "Developer"})
        assert "id" in result
        assert result["portal_person_id"] == 101
        assert result["person_name"] == "Mario Rossi"
        assert result["person_email"] == "mario.rossi@test.it"
        assert result["seniority"] == "Senior"
        assert result["daily_cost"] == 350.0
        assert result["role"] == "Developer"
        assert result["status"] == "assigned"

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_03_add_resource_uses_provided_name_over_portal(self, mock_pc, svc, deal, tenant):
        mock_pc.get_person = AsyncMock(return_value=MOCK_PERSON)
        result = await svc.add_resource(deal.id, tenant.id, {
            "portal_person_id": 101,
            "person_name": "Custom Name",
        })
        # provided name takes precedence (since add_resource uses `person_name or fetched_name`)
        assert result["person_name"] == "Custom Name"

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_04_add_resource_missing_person_id(self, mock_pc, svc, deal, tenant):
        result = await svc.add_resource(deal.id, tenant.id, {})
        assert "error" in result
        assert "portal_person_id" in result["error"]

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_05_add_resource_portal_error_graceful(self, mock_pc, svc, deal, tenant):
        mock_pc.get_person = AsyncMock(side_effect=Exception("Connection refused"))
        result = await svc.add_resource(deal.id, tenant.id, {
            "portal_person_id": 999,
            "person_name": "Fallback Name",
        })
        assert result["person_name"] == "Fallback Name"
        assert result["daily_cost"] is None  # not fetched

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_06_add_resource_with_dates(self, mock_pc, svc, deal, tenant):
        mock_pc.get_person = AsyncMock(return_value={"error": "not found"})
        result = await svc.add_resource(deal.id, tenant.id, {
            "portal_person_id": 200,
            "person_name": "Date Test",
            "start_date": "2026-05-01",
            "end_date": "2026-08-31",
        })
        assert result["start_date"] == "2026-05-01"
        assert result["end_date"] == "2026-08-31"

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_07_list_after_add(self, mock_pc, svc, deal, tenant):
        mock_pc.get_person = AsyncMock(return_value=MOCK_PERSON)
        await svc.add_resource(deal.id, tenant.id, {"portal_person_id": 101, "role": "Dev"})
        await svc.add_resource(deal.id, tenant.id, {"portal_person_id": 102, "role": "PM", "person_name": "PM Test"})
        result = await svc.list_resources(deal.id, tenant.id)
        assert len(result) == 2

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_08_update_resource(self, mock_pc, svc, deal, tenant):
        mock_pc.get_person = AsyncMock(return_value=MOCK_PERSON)
        added = await svc.add_resource(deal.id, tenant.id, {"portal_person_id": 101})
        updated = await svc.update_resource(uuid.UUID(added["id"]), {"status": "active", "role": "Tech Lead"})
        assert updated is not None
        assert updated["status"] == "active"
        assert updated["role"] == "Tech Lead"

    @pytest.mark.anyio
    async def test_09_update_resource_not_found(self, svc):
        result = await svc.update_resource(uuid.uuid4(), {"status": "active"})
        assert result is None

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_10_remove_resource(self, mock_pc, svc, deal, tenant):
        mock_pc.get_person = AsyncMock(return_value=MOCK_PERSON)
        added = await svc.add_resource(deal.id, tenant.id, {"portal_person_id": 101})
        ok = await svc.remove_resource(uuid.UUID(added["id"]))
        assert ok is True
        # Verify removed
        remaining = await svc.list_resources(deal.id, tenant.id)
        assert len(remaining) == 0

    @pytest.mark.anyio
    async def test_11_remove_resource_not_found(self, svc):
        ok = await svc.remove_resource(uuid.uuid4())
        assert ok is False


class TestDealResourceServiceRequires:

    @pytest.mark.anyio
    async def test_12_no_products_no_requires(self, svc, deal, tenant):
        requires = await svc.check_requires_resources(deal.id, tenant.id)
        assert requires is False

    @pytest.mark.anyio
    async def test_13_product_without_requires(self, db_session, svc, deal, tenant):
        prod = CrmProduct(
            tenant_id=tenant.id, name="Standard", code="STD",
            requires_resources=False,
        )
        db_session.add(prod)
        await db_session.flush()
        dp = CrmDealProduct(tenant_id=tenant.id, deal_id=deal.id, product_id=prod.id)
        db_session.add(dp)
        await db_session.flush()
        requires = await svc.check_requires_resources(deal.id, tenant.id)
        assert requires is False

    @pytest.mark.anyio
    async def test_14_product_with_requires(self, db_session, svc, deal, tenant):
        prod = CrmProduct(
            tenant_id=tenant.id, name="T&M Consulting", code="TM",
            requires_resources=True,
        )
        db_session.add(prod)
        await db_session.flush()
        dp = CrmDealProduct(tenant_id=tenant.id, deal_id=deal.id, product_id=prod.id)
        db_session.add(dp)
        await db_session.flush()
        requires = await svc.check_requires_resources(deal.id, tenant.id)
        assert requires is True

    @pytest.mark.anyio
    async def test_15_mixed_products(self, db_session, svc, deal, tenant):
        prod1 = CrmProduct(
            tenant_id=tenant.id, name="Standard", code="STD2",
            requires_resources=False,
        )
        prod2 = CrmProduct(
            tenant_id=tenant.id, name="T&M", code="TM2",
            requires_resources=True,
        )
        db_session.add_all([prod1, prod2])
        await db_session.flush()
        dp1 = CrmDealProduct(tenant_id=tenant.id, deal_id=deal.id, product_id=prod1.id)
        dp2 = CrmDealProduct(tenant_id=tenant.id, deal_id=deal.id, product_id=prod2.id)
        db_session.add_all([dp1, dp2])
        await db_session.flush()
        requires = await svc.check_requires_resources(deal.id, tenant.id)
        assert requires is True


# ============================================================
# B. API Endpoint Tests (HTTP)
# ============================================================


class TestDealResourcesAPI:

    @pytest.mark.anyio
    async def test_20_list_empty(self, client, owner_headers, deal):
        resp = await client.get(f"/api/v1/crm/deals/{deal.id}/resources", headers=owner_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_21_add_resource_api(self, mock_pc, client, owner_headers, deal):
        mock_pc.get_person = AsyncMock(return_value=MOCK_PERSON)
        resp = await client.post(
            f"/api/v1/crm/deals/{deal.id}/resources",
            json={"portal_person_id": 101, "role": "Backend Dev"},
            headers=owner_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["portal_person_id"] == 101
        assert data["person_name"] == "Mario Rossi"
        assert data["role"] == "Backend Dev"

    @pytest.mark.anyio
    async def test_22_add_resource_missing_person_id(self, client, owner_headers, deal):
        resp = await client.post(
            f"/api/v1/crm/deals/{deal.id}/resources",
            json={"role": "Dev"},
            headers=owner_headers,
        )
        assert resp.status_code == 400

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_23_list_after_add(self, mock_pc, client, owner_headers, deal):
        mock_pc.get_person = AsyncMock(return_value=MOCK_PERSON)
        await client.post(
            f"/api/v1/crm/deals/{deal.id}/resources",
            json={"portal_person_id": 101, "role": "Dev"},
            headers=owner_headers,
        )
        resp = await client.get(f"/api/v1/crm/deals/{deal.id}/resources", headers=owner_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_24_update_resource_api(self, mock_pc, client, owner_headers, deal):
        mock_pc.get_person = AsyncMock(return_value=MOCK_PERSON)
        add_resp = await client.post(
            f"/api/v1/crm/deals/{deal.id}/resources",
            json={"portal_person_id": 101},
            headers=owner_headers,
        )
        rid = add_resp.json()["id"]
        resp = await client.patch(
            f"/api/v1/crm/deals/{deal.id}/resources/{rid}",
            json={"status": "active", "role": "Senior Dev"},
            headers=owner_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "active"
        assert resp.json()["role"] == "Senior Dev"

    @pytest.mark.anyio
    async def test_25_update_resource_not_found(self, client, owner_headers, deal):
        fake_id = str(uuid.uuid4())
        resp = await client.patch(
            f"/api/v1/crm/deals/{deal.id}/resources/{fake_id}",
            json={"status": "active"},
            headers=owner_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_26_delete_resource_api(self, mock_pc, client, owner_headers, deal):
        mock_pc.get_person = AsyncMock(return_value=MOCK_PERSON)
        add_resp = await client.post(
            f"/api/v1/crm/deals/{deal.id}/resources",
            json={"portal_person_id": 101},
            headers=owner_headers,
        )
        rid = add_resp.json()["id"]
        resp = await client.delete(
            f"/api/v1/crm/deals/{deal.id}/resources/{rid}",
            headers=owner_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    @pytest.mark.anyio
    async def test_27_delete_resource_not_found(self, client, owner_headers, deal):
        fake_id = str(uuid.uuid4())
        resp = await client.delete(
            f"/api/v1/crm/deals/{deal.id}/resources/{fake_id}",
            headers=owner_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_28_requires_resources_no_products(self, client, owner_headers, deal):
        resp = await client.get(
            f"/api/v1/crm/deals/{deal.id}/resources/requires",
            headers=owner_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["requires_resources"] is False

    @pytest.mark.anyio
    async def test_29_requires_resources_with_tm_product(
        self, db_session, client, owner_headers, deal, tenant,
    ):
        prod = CrmProduct(tenant_id=tenant.id, name="TM Service", code="TMS", requires_resources=True)
        db_session.add(prod)
        await db_session.flush()
        dp = CrmDealProduct(tenant_id=tenant.id, deal_id=deal.id, product_id=prod.id)
        db_session.add(dp)
        await db_session.flush()

        resp = await client.get(
            f"/api/v1/crm/deals/{deal.id}/resources/requires",
            headers=owner_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["requires_resources"] is True

    @pytest.mark.anyio
    async def test_30_unauthenticated_list(self, client, deal):
        resp = await client.get(f"/api/v1/crm/deals/{deal.id}/resources")
        assert resp.status_code in (401, 403)

    @pytest.mark.anyio
    async def test_31_unauthenticated_add(self, client, deal):
        resp = await client.post(
            f"/api/v1/crm/deals/{deal.id}/resources",
            json={"portal_person_id": 1},
        )
        assert resp.status_code in (401, 403)


# ============================================================
# C. Additional Service Edge Cases
# ============================================================


class TestDealResourceEdgeCases:

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_32_add_with_notes(self, mock_pc, svc, deal, tenant):
        mock_pc.get_person = AsyncMock(return_value={"error": "not found"})
        result = await svc.add_resource(deal.id, tenant.id, {
            "portal_person_id": 300,
            "person_name": "Notes Test",
            "notes": "Available only mornings",
        })
        assert result["notes"] == "Available only mornings"

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_33_add_with_portal_activity_id(self, mock_pc, svc, deal, tenant):
        mock_pc.get_person = AsyncMock(return_value={"error": "not found"})
        result = await svc.add_resource(deal.id, tenant.id, {
            "portal_person_id": 301,
            "person_name": "Activity Test",
            "portal_activity_id": 55,
        })
        assert result["portal_activity_id"] == 55

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_34_update_dates(self, mock_pc, svc, deal, tenant):
        mock_pc.get_person = AsyncMock(return_value={"error": "not found"})
        added = await svc.add_resource(deal.id, tenant.id, {
            "portal_person_id": 302,
            "person_name": "Date Update",
        })
        updated = await svc.update_resource(uuid.UUID(added["id"]), {
            "start_date": "2026-06-01",
            "end_date": "2026-12-31",
        })
        assert updated["start_date"] == "2026-06-01"
        assert updated["end_date"] == "2026-12-31"

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_35_update_daily_cost(self, mock_pc, svc, deal, tenant):
        mock_pc.get_person = AsyncMock(return_value={"error": "not found"})
        added = await svc.add_resource(deal.id, tenant.id, {
            "portal_person_id": 303,
            "person_name": "Cost Update",
            "daily_cost": 200,
        })
        updated = await svc.update_resource(uuid.UUID(added["id"]), {"daily_cost": 250})
        assert updated["daily_cost"] == 250

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_36_status_lifecycle(self, mock_pc, svc, deal, tenant):
        mock_pc.get_person = AsyncMock(return_value={"error": "not found"})
        added = await svc.add_resource(deal.id, tenant.id, {
            "portal_person_id": 304,
            "person_name": "Lifecycle",
        })
        assert added["status"] == "assigned"
        updated1 = await svc.update_resource(uuid.UUID(added["id"]), {"status": "active"})
        assert updated1["status"] == "active"
        updated2 = await svc.update_resource(uuid.UUID(added["id"]), {"status": "released"})
        assert updated2["status"] == "released"

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_37_portal_seniority_dict(self, mock_pc, svc, deal, tenant):
        """Portal may return seniority as a dict with 'description'."""
        person_with_dict_seniority = {
            "firstName": "Luca",
            "lastName": "Verdi",
            "Seniority": {"id": 3, "description": "Mid"},
            "EmploymentContracts": [],
        }
        mock_pc.get_person = AsyncMock(return_value=person_with_dict_seniority)
        result = await svc.add_resource(deal.id, tenant.id, {"portal_person_id": 400})
        assert result["seniority"] == "Mid"

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_38_portal_seniority_string(self, mock_pc, svc, deal, tenant):
        person_with_str_seniority = {
            "firstName": "Anna",
            "lastName": "Neri",
            "seniority": "Junior",
            "EmploymentContracts": [],
        }
        mock_pc.get_person = AsyncMock(return_value=person_with_str_seniority)
        result = await svc.add_resource(deal.id, tenant.id, {"portal_person_id": 401})
        assert result["seniority"] == "Junior"

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_39_multiple_resources_same_deal(self, mock_pc, svc, deal, tenant):
        mock_pc.get_person = AsyncMock(return_value={"error": "disabled"})
        for i in range(5):
            await svc.add_resource(deal.id, tenant.id, {
                "portal_person_id": 500 + i,
                "person_name": f"Person {i}",
                "role": f"Role {i}",
            })
        result = await svc.list_resources(deal.id, tenant.id)
        assert len(result) == 5

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_40_resource_isolation_by_tenant(self, db_session, svc, deal, tenant):
        """Resources from one tenant should not leak to another."""
        # Already tested by fixture, but explicit: create resource in tenant A
        from api.modules.deal_resources.service import portal_client as pc
        with patch.object(pc, "get_person", new_callable=AsyncMock, return_value={"error": "off"}):
            await svc.add_resource(deal.id, tenant.id, {
                "portal_person_id": 600,
                "person_name": "Tenant A",
            })
        other_tenant_id = uuid.uuid4()
        result = await svc.list_resources(deal.id, other_tenant_id)
        assert len(result) == 0

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_41_add_resource_custom_status(self, mock_pc, svc, deal, tenant):
        mock_pc.get_person = AsyncMock(return_value={"error": "off"})
        result = await svc.add_resource(deal.id, tenant.id, {
            "portal_person_id": 700,
            "person_name": "Custom Status",
            "status": "active",
        })
        assert result["status"] == "active"

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_42_update_ignores_disallowed_fields(self, mock_pc, svc, deal, tenant):
        mock_pc.get_person = AsyncMock(return_value={"error": "off"})
        added = await svc.add_resource(deal.id, tenant.id, {
            "portal_person_id": 701,
            "person_name": "No Hack",
        })
        updated = await svc.update_resource(uuid.UUID(added["id"]), {
            "portal_person_id": 999,  # should not be updated
            "tenant_id": str(uuid.uuid4()),  # should not be updated
            "role": "Hacker",
        })
        assert updated["portal_person_id"] == 701
        assert updated["role"] == "Hacker"


# ============================================================
# D. API - Multiple Resources & Ordering
# ============================================================


class TestDealResourcesMultiple:

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_43_add_three_list_ordered(self, mock_pc, client, owner_headers, deal):
        mock_pc.get_person = AsyncMock(return_value={"error": "off"})
        for i in range(3):
            await client.post(
                f"/api/v1/crm/deals/{deal.id}/resources",
                json={"portal_person_id": 800 + i, "person_name": f"Person {i}"},
                headers=owner_headers,
            )
        resp = await client.get(f"/api/v1/crm/deals/{deal.id}/resources", headers=owner_headers)
        data = resp.json()
        assert len(data) == 3
        # Should be ordered by created_at
        names = [r["person_name"] for r in data]
        assert names == ["Person 0", "Person 1", "Person 2"]

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_44_delete_middle_resource(self, mock_pc, client, owner_headers, deal):
        mock_pc.get_person = AsyncMock(return_value={"error": "off"})
        ids = []
        for i in range(3):
            r = await client.post(
                f"/api/v1/crm/deals/{deal.id}/resources",
                json={"portal_person_id": 900 + i, "person_name": f"Del {i}"},
                headers=owner_headers,
            )
            ids.append(r.json()["id"])
        # Delete middle
        await client.delete(f"/api/v1/crm/deals/{deal.id}/resources/{ids[1]}", headers=owner_headers)
        resp = await client.get(f"/api/v1/crm/deals/{deal.id}/resources", headers=owner_headers)
        remaining = resp.json()
        assert len(remaining) == 2
        remaining_names = [r["person_name"] for r in remaining]
        assert "Del 0" in remaining_names
        assert "Del 2" in remaining_names

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_45_update_person_email(self, mock_pc, client, owner_headers, deal):
        mock_pc.get_person = AsyncMock(return_value={"error": "off"})
        add_resp = await client.post(
            f"/api/v1/crm/deals/{deal.id}/resources",
            json={"portal_person_id": 950, "person_name": "Email Test"},
            headers=owner_headers,
        )
        rid = add_resp.json()["id"]
        resp = await client.patch(
            f"/api/v1/crm/deals/{deal.id}/resources/{rid}",
            json={"person_email": "new@test.it"},
            headers=owner_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["person_email"] == "new@test.it"


# ============================================================
# E. Database Model Tests
# ============================================================


class TestDealResourceModel:

    @pytest.mark.anyio
    async def test_46_model_defaults(self, db_session, tenant, deal):
        r = CrmDealResource(
            tenant_id=tenant.id,
            deal_id=deal.id,
            portal_person_id=100,
        )
        db_session.add(r)
        await db_session.flush()
        assert r.id is not None
        assert r.status == "assigned"
        assert r.person_name is None
        assert r.daily_cost is None

    @pytest.mark.anyio
    async def test_47_model_full(self, db_session, tenant, deal):
        r = CrmDealResource(
            tenant_id=tenant.id,
            deal_id=deal.id,
            portal_person_id=200,
            person_name="Full Model",
            person_email="full@test.it",
            seniority="Lead",
            daily_cost=500,
            role="Architect",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            status="active",
            notes="Top performer",
            portal_activity_id=77,
        )
        db_session.add(r)
        await db_session.flush()

        result = await db_session.execute(select(CrmDealResource).where(CrmDealResource.id == r.id))
        loaded = result.scalar_one()
        assert loaded.person_name == "Full Model"
        assert loaded.daily_cost == 500
        assert loaded.portal_activity_id == 77

    @pytest.mark.anyio
    async def test_48_deal_has_portal_offer_id(self, db_session, tenant, stages):
        d = CrmDeal(
            tenant_id=tenant.id,
            name="Offer Deal",
            stage_id=stages[0].id,
            portal_offer_id=42,
        )
        db_session.add(d)
        await db_session.flush()
        result = await db_session.execute(select(CrmDeal).where(CrmDeal.id == d.id))
        loaded = result.scalar_one()
        assert loaded.portal_offer_id == 42

    @pytest.mark.anyio
    async def test_49_deal_portal_offer_id_null_by_default(self, db_session, tenant, stages):
        d = CrmDeal(
            tenant_id=tenant.id,
            name="No Offer Deal",
            stage_id=stages[0].id,
        )
        db_session.add(d)
        await db_session.flush()
        result = await db_session.execute(select(CrmDeal).where(CrmDeal.id == d.id))
        loaded = result.scalar_one()
        assert loaded.portal_offer_id is None

    @pytest.mark.anyio
    async def test_50_deal_to_dict_includes_portal_offer_id(self, db_session, tenant, stages, crm):
        d = CrmDeal(
            tenant_id=tenant.id,
            name="Dict Offer Test",
            stage_id=stages[0].id,
            portal_offer_id=123,
        )
        db_session.add(d)
        await db_session.flush()
        result = await crm._deal_to_dict(d, tenant.id)
        assert result["portal_offer_id"] == 123
        assert "requires_resources" in result
