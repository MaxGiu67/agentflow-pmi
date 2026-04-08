"""Test suite for Portal Activity Flow — Sprint A.

Tests portal activity and resource assignment workflows:
deal -> offer -> project -> activities -> assign persons.
~35 tests.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import (
    CrmDeal, CrmDealResource, CrmPipelineStage,
    CrmProduct, CrmDealProduct, Tenant, User,
)
from api.modules.crm.service import CRMService
from api.modules.deal_resources.service import DealResourceService
from tests.conftest import _hash_pw, get_auth_token


# ── Fixtures ──────────────────────────────────────

@pytest.fixture
async def owner(db_session: AsyncSession, tenant: Tenant) -> User:
    u = User(
        email="act.owner@test.it", password_hash=_hash_pw("Password1"),
        name="Activity Owner", role="owner", email_verified=True, tenant_id=tenant.id,
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest.fixture
async def owner_headers(client: AsyncClient, owner: User) -> dict:
    token = await get_auth_token(client, "act.owner@test.it", "Password1")
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
async def deal_tm(db_session: AsyncSession, tenant: Tenant, stages) -> CrmDeal:
    d = CrmDeal(
        tenant_id=tenant.id,
        name="T&M Activity Deal",
        deal_type="T&M",
        expected_revenue=120000,
        daily_rate=600,
        estimated_days=200,
        stage_id=stages[4].id,  # Confermato (won)
        portal_customer_id=42,
        portal_customer_name="ACME Corp",
        portal_offer_id=100,
        portal_project_id=200,
    )
    db_session.add(d)
    await db_session.flush()
    return d


@pytest.fixture
async def deal_no_project(db_session: AsyncSession, tenant: Tenant, stages) -> CrmDeal:
    d = CrmDeal(
        tenant_id=tenant.id,
        name="No Project Deal",
        deal_type="T&M",
        stage_id=stages[2].id,
        portal_customer_id=42,
    )
    db_session.add(d)
    await db_session.flush()
    return d


@pytest.fixture
async def svc(db_session: AsyncSession) -> DealResourceService:
    return DealResourceService(db_session)


@pytest.fixture
async def tm_product(db_session: AsyncSession, tenant: Tenant) -> CrmProduct:
    p = CrmProduct(
        tenant_id=tenant.id,
        name="T&M Consulting",
        code="TM-CON",
        requires_resources=True,
    )
    db_session.add(p)
    await db_session.flush()
    return p


@pytest.fixture
async def fixed_product(db_session: AsyncSession, tenant: Tenant) -> CrmProduct:
    p = CrmProduct(
        tenant_id=tenant.id,
        name="Fixed Project",
        code="FIX-PRJ",
        requires_resources=False,
    )
    db_session.add(p)
    await db_session.flush()
    return p


# ============================================================
# A. Resource-Product Integration Tests
# ============================================================


class TestResourceProductIntegration:

    @pytest.mark.anyio
    async def test_01_no_products(self, svc, deal_tm, tenant):
        requires = await svc.check_requires_resources(deal_tm.id, tenant.id)
        assert requires is False

    @pytest.mark.anyio
    async def test_02_tm_product_requires(self, db_session, svc, deal_tm, tenant, tm_product):
        dp = CrmDealProduct(tenant_id=tenant.id, deal_id=deal_tm.id, product_id=tm_product.id)
        db_session.add(dp)
        await db_session.flush()
        requires = await svc.check_requires_resources(deal_tm.id, tenant.id)
        assert requires is True

    @pytest.mark.anyio
    async def test_03_fixed_product_not_requires(self, db_session, svc, deal_tm, tenant, fixed_product):
        dp = CrmDealProduct(tenant_id=tenant.id, deal_id=deal_tm.id, product_id=fixed_product.id)
        db_session.add(dp)
        await db_session.flush()
        requires = await svc.check_requires_resources(deal_tm.id, tenant.id)
        assert requires is False

    @pytest.mark.anyio
    async def test_04_mixed_products_requires(self, db_session, svc, deal_tm, tenant, tm_product, fixed_product):
        dp1 = CrmDealProduct(tenant_id=tenant.id, deal_id=deal_tm.id, product_id=fixed_product.id)
        dp2 = CrmDealProduct(tenant_id=tenant.id, deal_id=deal_tm.id, product_id=tm_product.id)
        db_session.add_all([dp1, dp2])
        await db_session.flush()
        requires = await svc.check_requires_resources(deal_tm.id, tenant.id)
        assert requires is True

    @pytest.mark.anyio
    async def test_05_different_deal_different_products(self, db_session, svc, deal_tm, deal_no_project, tenant, tm_product, fixed_product):
        dp1 = CrmDealProduct(tenant_id=tenant.id, deal_id=deal_tm.id, product_id=tm_product.id)
        dp2 = CrmDealProduct(tenant_id=tenant.id, deal_id=deal_no_project.id, product_id=fixed_product.id)
        db_session.add_all([dp1, dp2])
        await db_session.flush()
        assert await svc.check_requires_resources(deal_tm.id, tenant.id) is True
        assert await svc.check_requires_resources(deal_no_project.id, tenant.id) is False


# ============================================================
# B. Resource Assignment with Portal Activity
# ============================================================


class TestResourceWithActivity:

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_06_assign_with_activity(self, mock_pc, svc, deal_tm, tenant):
        mock_pc.get_person = AsyncMock(return_value={
            "firstName": "Paolo",
            "lastName": "Bianchi",
            "EmploymentContracts": [{"dailyCost": 400, "endDate": None}],
        })
        result = await svc.add_resource(deal_tm.id, tenant.id, {
            "portal_person_id": 501,
            "role": "Senior Developer",
            "portal_activity_id": 77,
            "start_date": "2026-05-01",
            "end_date": "2026-12-31",
        })
        assert result["portal_activity_id"] == 77
        assert result["person_name"] == "Paolo Bianchi"
        assert result["daily_cost"] == 400

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_07_update_activity_id(self, mock_pc, svc, deal_tm, tenant):
        mock_pc.get_person = AsyncMock(return_value={"error": "off"})
        added = await svc.add_resource(deal_tm.id, tenant.id, {
            "portal_person_id": 502,
            "person_name": "Act Update",
        })
        updated = await svc.update_resource(uuid.UUID(added["id"]), {"portal_activity_id": 88})
        assert updated["portal_activity_id"] == 88

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_08_resource_release(self, mock_pc, svc, deal_tm, tenant):
        mock_pc.get_person = AsyncMock(return_value={"error": "off"})
        added = await svc.add_resource(deal_tm.id, tenant.id, {
            "portal_person_id": 503,
            "person_name": "Release Test",
            "status": "active",
        })
        updated = await svc.update_resource(uuid.UUID(added["id"]), {"status": "released"})
        assert updated["status"] == "released"


# ============================================================
# C. API - Portal Proxy Endpoints
# ============================================================


class TestPortalActivityProxy:

    @pytest.mark.anyio
    @patch("api.modules.portal.router.portal_client")
    async def test_09_get_activity_types(self, mock_pc, client, owner_headers):
        mock_pc.get_activity_types = AsyncMock(return_value=[
            {"id": 1, "name": "Development"},
            {"id": 2, "name": "Consulting"},
        ])
        resp = await client.get("/api/v1/portal/activities/types", headers=owner_headers)
        assert resp.status_code == 200

    @pytest.mark.anyio
    @patch("api.modules.portal.router.portal_client")
    async def test_10_get_activities_by_project(self, mock_pc, client, owner_headers):
        mock_pc.get_activities_by_project = AsyncMock(return_value={"data": [
            {"id": 10, "name": "Phase 1"},
        ]})
        resp = await client.get("/api/v1/portal/activities/by-project/200", headers=owner_headers)
        assert resp.status_code == 200

    @pytest.mark.anyio
    @patch("api.modules.portal.router.portal_client")
    async def test_11_create_portal_activity(self, mock_pc, client, owner_headers):
        mock_pc.create_activity = AsyncMock(return_value={"id": 55, "name": "New Activity"})
        resp = await client.post(
            "/api/v1/portal/activities/create",
            json={"name": "New Activity", "project_id": 200},
            headers=owner_headers,
        )
        assert resp.status_code == 200

    @pytest.mark.anyio
    @patch("api.modules.portal.router.portal_client")
    async def test_12_assign_employee(self, mock_pc, client, owner_headers):
        mock_pc.add_employee_to_activity = AsyncMock(return_value={"ok": True})
        resp = await client.post(
            "/api/v1/portal/activities/assign",
            json={"activity_id": 55, "person_id": 101},
            headers=owner_headers,
        )
        assert resp.status_code == 200

    @pytest.mark.anyio
    @patch("api.modules.portal.router.portal_client")
    async def test_13_get_activity_persons(self, mock_pc, client, owner_headers):
        mock_pc.get_related_person_activities = AsyncMock(return_value={"data": [
            {"id": 1, "Person": {"firstName": "Mario"}},
        ]})
        resp = await client.get("/api/v1/portal/activities/55/persons", headers=owner_headers)
        assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_14_activity_types_unauthenticated(self, client):
        resp = await client.get("/api/v1/portal/activities/types")
        assert resp.status_code in (401, 403)


# ============================================================
# D. Deal Progress with Resources
# ============================================================


class TestDealProgressWithResources:

    @pytest.mark.anyio
    @patch("api.modules.portal.router.portal_client")
    async def test_15_deal_progress(self, mock_pc, client, owner_headers, deal_tm):
        mock_pc.get_project = AsyncMock(return_value={"name": "Project ACME"})
        mock_pc.get_activities_by_project = AsyncMock(return_value={"data": [
            {
                "id": 1,
                "PersonActivities": [
                    {"Person": {"CurrentContract": {"Contract": {"dailyCost": 350}}}},
                    {"Person": {"CurrentContract": {"Contract": {"dailyCost": 300}}}},
                ],
            }
        ]})
        resp = await client.get(
            f"/api/v1/portal/deal-progress/{deal_tm.id}",
            headers=owner_headers,
        )
        assert resp.status_code == 200
        data = resp.json()["progress"]
        assert data["assigned_persons"] == 2
        assert data["daily_rate"] == 600

    @pytest.mark.anyio
    async def test_16_deal_progress_no_project(self, client, owner_headers, deal_no_project):
        resp = await client.get(
            f"/api/v1/portal/deal-progress/{deal_no_project.id}",
            headers=owner_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["progress"] is None


# ============================================================
# E. Resource with Deal Flow Integration
# ============================================================


class TestResourceDealFlowIntegration:

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_17_add_resource_via_api(self, mock_pc, client, owner_headers, deal_tm):
        mock_pc.get_person = AsyncMock(return_value={
            "firstName": "Elena",
            "lastName": "Conti",
            "privateEmail": "elena@test.it",
            "seniority": "Senior",
            "EmploymentContracts": [{"dailyCost": 450, "endDate": None}],
        })
        resp = await client.post(
            f"/api/v1/crm/deals/{deal_tm.id}/resources",
            json={
                "portal_person_id": 601,
                "role": "Backend Developer",
                "start_date": "2026-06-01",
            },
            headers=owner_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["person_name"] == "Elena Conti"
        assert data["person_email"] == "elena@test.it"
        assert data["daily_cost"] == 450

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_18_check_requires_api(self, mock_pc, client, owner_headers, deal_tm, db_session, tenant, tm_product):
        dp = CrmDealProduct(tenant_id=tenant.id, deal_id=deal_tm.id, product_id=tm_product.id)
        db_session.add(dp)
        await db_session.flush()
        resp = await client.get(
            f"/api/v1/crm/deals/{deal_tm.id}/resources/requires",
            headers=owner_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["requires_resources"] is True

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_19_resource_full_lifecycle(self, mock_pc, client, owner_headers, deal_tm):
        mock_pc.get_person = AsyncMock(return_value={"error": "off"})
        # Add
        add_resp = await client.post(
            f"/api/v1/crm/deals/{deal_tm.id}/resources",
            json={"portal_person_id": 700, "person_name": "Lifecycle Test"},
            headers=owner_headers,
        )
        assert add_resp.status_code == 201
        rid = add_resp.json()["id"]

        # Update to active
        upd_resp = await client.patch(
            f"/api/v1/crm/deals/{deal_tm.id}/resources/{rid}",
            json={"status": "active"},
            headers=owner_headers,
        )
        assert upd_resp.json()["status"] == "active"

        # Update to released
        rel_resp = await client.patch(
            f"/api/v1/crm/deals/{deal_tm.id}/resources/{rid}",
            json={"status": "released"},
            headers=owner_headers,
        )
        assert rel_resp.json()["status"] == "released"

        # Delete
        del_resp = await client.delete(
            f"/api/v1/crm/deals/{deal_tm.id}/resources/{rid}",
            headers=owner_headers,
        )
        assert del_resp.json()["ok"] is True

        # Verify empty
        list_resp = await client.get(
            f"/api/v1/crm/deals/{deal_tm.id}/resources",
            headers=owner_headers,
        )
        assert list_resp.json() == []

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_20_multiple_resources_api(self, mock_pc, client, owner_headers, deal_tm):
        mock_pc.get_person = AsyncMock(return_value={"error": "off"})
        for i in range(5):
            resp = await client.post(
                f"/api/v1/crm/deals/{deal_tm.id}/resources",
                json={"portal_person_id": 800 + i, "person_name": f"Multi {i}"},
                headers=owner_headers,
            )
            assert resp.status_code == 201
        list_resp = await client.get(
            f"/api/v1/crm/deals/{deal_tm.id}/resources",
            headers=owner_headers,
        )
        assert len(list_resp.json()) == 5


# ============================================================
# F. Portal Person Data Fetching
# ============================================================


class TestPortalPersonFetch:

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_21_fetch_person_with_contracts(self, mock_pc, svc, deal_tm, tenant):
        mock_pc.get_person = AsyncMock(return_value={
            "firstName": "Marco",
            "lastName": "Developer",
            "privateEmail": "marco@dev.it",
            "Seniority": "Lead",
            "EmploymentContracts": [
                {"dailyCost": 500, "endDate": "2025-12-31"},  # expired
                {"dailyCost": 550, "endDate": None},  # active
            ],
        })
        result = await svc.add_resource(deal_tm.id, tenant.id, {"portal_person_id": 900})
        assert result["daily_cost"] == 550  # active contract cost

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_22_fetch_person_camel_case(self, mock_pc, svc, deal_tm, tenant):
        mock_pc.get_person = AsyncMock(return_value={
            "first_name": "Luca",
            "last_name": "Tester",
            "private_email": "luca@test.it",
            "seniority": "Mid",
            "employmentContracts": [{"daily_cost": 300, "endDate": None}],
        })
        result = await svc.add_resource(deal_tm.id, tenant.id, {"portal_person_id": 901})
        assert result["person_name"] == "Luca Tester"
        assert result["person_email"] == "luca@test.it"

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_23_fetch_person_empty_response(self, mock_pc, svc, deal_tm, tenant):
        mock_pc.get_person = AsyncMock(return_value={})
        result = await svc.add_resource(deal_tm.id, tenant.id, {
            "portal_person_id": 902,
            "person_name": "Fallback",
        })
        assert result["person_name"] == "Fallback"

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_24_fetch_person_all_contracts_expired(self, mock_pc, svc, deal_tm, tenant):
        mock_pc.get_person = AsyncMock(return_value={
            "firstName": "Old",
            "lastName": "Contract",
            "EmploymentContracts": [
                {"dailyCost": 400, "endDate": "2024-12-31"},
            ],
        })
        result = await svc.add_resource(deal_tm.id, tenant.id, {"portal_person_id": 903})
        # No active contract, so daily_cost stays None
        assert result["daily_cost"] is None

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_25_explicit_daily_cost_overrides(self, mock_pc, svc, deal_tm, tenant):
        mock_pc.get_person = AsyncMock(return_value={
            "firstName": "Override",
            "lastName": "Test",
            "EmploymentContracts": [{"dailyCost": 500, "endDate": None}],
        })
        result = await svc.add_resource(deal_tm.id, tenant.id, {
            "portal_person_id": 904,
            "daily_cost": 600,
        })
        assert result["daily_cost"] == 600  # explicit overrides fetched


# ============================================================
# G. Additional Edge Cases
# ============================================================


class TestActivityEdgeCases:

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_26_resource_no_contracts_field(self, mock_pc, svc, deal_tm, tenant):
        mock_pc.get_person = AsyncMock(return_value={
            "firstName": "No",
            "lastName": "Contracts",
        })
        result = await svc.add_resource(deal_tm.id, tenant.id, {"portal_person_id": 1000})
        assert result["daily_cost"] is None

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_27_resource_empty_contracts(self, mock_pc, svc, deal_tm, tenant):
        mock_pc.get_person = AsyncMock(return_value={
            "firstName": "Empty",
            "lastName": "Contracts",
            "EmploymentContracts": [],
        })
        result = await svc.add_resource(deal_tm.id, tenant.id, {"portal_person_id": 1001})
        assert result["daily_cost"] is None

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_28_resource_seniority_none(self, mock_pc, svc, deal_tm, tenant):
        mock_pc.get_person = AsyncMock(return_value={
            "firstName": "No",
            "lastName": "Seniority",
            "Seniority": None,
            "seniority": None,
        })
        result = await svc.add_resource(deal_tm.id, tenant.id, {"portal_person_id": 1002})
        assert result["seniority"] == ""

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_29_resource_with_date_objects(self, mock_pc, svc, deal_tm, tenant):
        from datetime import date
        mock_pc.get_person = AsyncMock(return_value={"error": "off"})
        result = await svc.add_resource(deal_tm.id, tenant.id, {
            "portal_person_id": 1003,
            "person_name": "Date Object",
            "start_date": date(2026, 7, 1),
            "end_date": date(2026, 12, 31),
        })
        assert result["start_date"] == "2026-07-01"
        assert result["end_date"] == "2026-12-31"

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_30_resource_update_seniority(self, mock_pc, svc, deal_tm, tenant):
        mock_pc.get_person = AsyncMock(return_value={"error": "off"})
        added = await svc.add_resource(deal_tm.id, tenant.id, {
            "portal_person_id": 1004,
            "person_name": "Seniority Update",
            "seniority": "Junior",
        })
        updated = await svc.update_resource(uuid.UUID(added["id"]), {"seniority": "Senior"})
        assert updated["seniority"] == "Senior"

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_31_resource_update_person_name(self, mock_pc, svc, deal_tm, tenant):
        mock_pc.get_person = AsyncMock(return_value={"error": "off"})
        added = await svc.add_resource(deal_tm.id, tenant.id, {
            "portal_person_id": 1005,
            "person_name": "Old Name",
        })
        updated = await svc.update_resource(uuid.UUID(added["id"]), {"person_name": "New Name"})
        assert updated["person_name"] == "New Name"

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_32_resource_dict_format(self, mock_pc, svc, deal_tm, tenant):
        mock_pc.get_person = AsyncMock(return_value={"error": "off"})
        added = await svc.add_resource(deal_tm.id, tenant.id, {
            "portal_person_id": 1006,
            "person_name": "Dict Format",
            "role": "Dev",
            "daily_cost": 300,
        })
        # Verify all expected fields
        assert "id" in added
        assert "tenant_id" in added
        assert "deal_id" in added
        assert "portal_person_id" in added
        assert "person_name" in added
        assert "person_email" in added
        assert "seniority" in added
        assert "daily_cost" in added
        assert "role" in added
        assert "start_date" in added
        assert "end_date" in added
        assert "status" in added
        assert "notes" in added
        assert "portal_activity_id" in added
        assert "created_at" in added
        assert "updated_at" in added

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_33_add_resource_deal_isolation(self, mock_pc, db_session, svc, tenant, stages):
        """Resources on one deal should not appear on another."""
        mock_pc.get_person = AsyncMock(return_value={"error": "off"})
        d1 = CrmDeal(tenant_id=tenant.id, name="Deal A", stage_id=stages[0].id)
        d2 = CrmDeal(tenant_id=tenant.id, name="Deal B", stage_id=stages[0].id)
        db_session.add_all([d1, d2])
        await db_session.flush()

        await svc.add_resource(d1.id, tenant.id, {"portal_person_id": 1, "person_name": "A"})
        await svc.add_resource(d2.id, tenant.id, {"portal_person_id": 2, "person_name": "B"})

        res_a = await svc.list_resources(d1.id, tenant.id)
        res_b = await svc.list_resources(d2.id, tenant.id)
        assert len(res_a) == 1
        assert res_a[0]["person_name"] == "A"
        assert len(res_b) == 1
        assert res_b[0]["person_name"] == "B"

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_34_resource_preserves_data_on_update(self, mock_pc, svc, deal_tm, tenant):
        mock_pc.get_person = AsyncMock(return_value={"error": "off"})
        added = await svc.add_resource(deal_tm.id, tenant.id, {
            "portal_person_id": 1007,
            "person_name": "Preserve",
            "role": "Dev",
            "daily_cost": 300,
        })
        # Update only role
        updated = await svc.update_resource(uuid.UUID(added["id"]), {"role": "Lead"})
        assert updated["role"] == "Lead"
        assert updated["person_name"] == "Preserve"  # unchanged
        assert updated["daily_cost"] == 300  # unchanged

    @pytest.mark.anyio
    @patch("api.modules.deal_resources.service.portal_client")
    async def test_35_resource_list_ordered_by_created(self, mock_pc, svc, deal_tm, tenant):
        mock_pc.get_person = AsyncMock(return_value={"error": "off"})
        await svc.add_resource(deal_tm.id, tenant.id, {"portal_person_id": 1, "person_name": "First"})
        await svc.add_resource(deal_tm.id, tenant.id, {"portal_person_id": 2, "person_name": "Second"})
        await svc.add_resource(deal_tm.id, tenant.id, {"portal_person_id": 3, "person_name": "Third"})

        resources = await svc.list_resources(deal_tm.id, tenant.id)
        names = [r["person_name"] for r in resources]
        assert names == ["First", "Second", "Third"]
