"""Sprint 24 tests — US-90 (Kanban API), US-91 (Pipeline Analytics).

Backend tests for deal stage update (drag-drop API), analytics endpoints.
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import CrmDeal, CrmPipelineStage, CrmContact, Tenant
from api.modules.crm.service import CRMService


# ============================================================
# US-91: Pipeline Analytics
# ============================================================


@pytest.mark.asyncio
async def test_ac_91_1_pipeline_summary(db_session: AsyncSession, tenant: Tenant):
    """AC-91.1: Pipeline summary with total_deals, total_value, by_stage."""
    svc = CRMService(db_session)
    await svc.create_deal(tenant.id, {"name": "Deal A", "expected_revenue": 10000.0})
    await svc.create_deal(tenant.id, {"name": "Deal B", "expected_revenue": 20000.0})

    summary = await svc.get_pipeline_summary(tenant.id)

    assert summary["total_deals"] == 2
    assert summary["total_value"] == 30000.0
    assert "Nuovo Lead" in summary["by_stage"]


@pytest.mark.asyncio
async def test_ac_91_2_weighted_pipeline(db_session: AsyncSession, tenant: Tenant):
    """AC-91.2: Weighted pipeline value = sum(revenue * probability / 100)."""
    svc = CRMService(db_session)

    # Deal A: 10000 at 10% probability = 1000 weighted
    await svc.create_deal(tenant.id, {"name": "Deal A", "expected_revenue": 10000.0})
    # Deal B: 20000, move to Qualificato (30%) = 6000 weighted
    deal_b = await svc.create_deal(tenant.id, {"name": "Deal B", "expected_revenue": 20000.0})
    stages = await svc.get_stages(tenant.id)
    qual_id = next(s["id"] for s in stages if s["name"] == "Qualificato")
    await svc.update_deal(uuid.UUID(deal_b["id"]), tenant.id, {"stage_id": qual_id})

    analytics = await svc.get_pipeline_analytics(tenant.id)

    # Weighted: 10000*0.1 + 20000*0.3 = 1000 + 6000 = 7000
    assert analytics["weighted_pipeline_value"] == 7000.0


@pytest.mark.asyncio
async def test_ac_91_3_conversion_by_stage(db_session: AsyncSession, tenant: Tenant):
    """AC-91.3: Conversion rate per stage."""
    svc = CRMService(db_session)
    await svc.create_deal(tenant.id, {"name": "D1"})
    await svc.create_deal(tenant.id, {"name": "D2"})

    analytics = await svc.get_pipeline_analytics(tenant.id)

    assert len(analytics["conversion_by_stage"]) == 6  # 6 default stages
    nuovo = next(c for c in analytics["conversion_by_stage"] if c["stage"] == "Nuovo Lead")
    assert nuovo["count"] == 2
    assert nuovo["rate"] == 100.0  # both deals in first stage


@pytest.mark.asyncio
async def test_ac_91_5_won_lost_ratio(db_session: AsyncSession, tenant: Tenant):
    """AC-91.5: Won/Lost ratio."""
    svc = CRMService(db_session)

    # Create and win a deal
    deal_w = await svc.create_deal(tenant.id, {"name": "Winner"})
    await svc.confirm_order(uuid.UUID(deal_w["id"]), tenant.id)

    # Create and lose a deal
    deal_l = await svc.create_deal(tenant.id, {"name": "Loser"})
    stages = await svc.get_stages(tenant.id)
    lost_id = next(s["id"] for s in stages if s["is_lost"])
    await svc.update_deal(uuid.UUID(deal_l["id"]), tenant.id, {"stage_id": lost_id})

    analytics = await svc.get_pipeline_analytics(tenant.id)

    assert analytics["won_count"] == 1
    assert analytics["lost_count"] == 1
    assert analytics["won_lost_ratio"] == 50.0  # 1/(1+1)


# ============================================================
# US-90: Kanban — API for drag-and-drop
# ============================================================


@pytest.mark.asyncio
async def test_ac_90_4_patch_stage(db_session: AsyncSession, tenant: Tenant):
    """AC-90.4: PATCH deal stage → probability auto-updated."""
    svc = CRMService(db_session)
    deal = await svc.create_deal(tenant.id, {"name": "Drag Deal", "expected_revenue": 50000.0})
    assert deal["probability"] == 10.0  # Nuovo Lead

    stages = await svc.get_stages(tenant.id)
    proposta_id = next(s["id"] for s in stages if s["name"] == "Proposta Inviata")

    updated = await svc.update_deal(uuid.UUID(deal["id"]), tenant.id, {"stage_id": proposta_id})

    assert updated["stage"] == "Proposta Inviata"
    assert updated["probability"] == 50.0


@pytest.mark.asyncio
async def test_ac_90_api_patch_deal(client: AsyncClient, auth_headers: dict):
    """AC-90.4 API: PATCH /crm/deals/{id} updates stage."""
    # Create a deal
    create_resp = await client.post(
        "/api/v1/crm/deals",
        json={"name": "API Drag Deal", "expected_revenue": 15000.0},
        headers=auth_headers,
    )
    deal_id = create_resp.json()["id"]

    # Get stages
    stages_resp = await client.get("/api/v1/crm/pipeline/stages", headers=auth_headers)
    stages = stages_resp.json()
    qual_id = next(s["id"] for s in stages if s["name"] == "Qualificato")

    # Patch stage (simulates drag-and-drop)
    patch_resp = await client.patch(
        f"/api/v1/crm/deals/{deal_id}",
        json={"stage_id": qual_id},
        headers=auth_headers,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["stage"] == "Qualificato"
    assert patch_resp.json()["probability"] == 30.0


@pytest.mark.asyncio
async def test_ac_90_api_pipeline_analytics(client: AsyncClient, auth_headers: dict):
    """AC-91 API: GET /crm/pipeline/analytics."""
    # Create some deals first
    await client.post(
        "/api/v1/crm/deals",
        json={"name": "Analytics D1", "expected_revenue": 5000.0},
        headers=auth_headers,
    )

    resp = await client.get("/api/v1/crm/pipeline/analytics", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "weighted_pipeline_value" in data
    assert "won_count" in data
    assert "conversion_by_stage" in data


@pytest.mark.asyncio
async def test_ac_90_deals_grouped_by_stage(db_session: AsyncSession, tenant: Tenant):
    """AC-90.1: Deals can be listed and grouped by stage for Kanban."""
    svc = CRMService(db_session)

    # Create deals in different stages
    d1 = await svc.create_deal(tenant.id, {"name": "Lead Deal"})
    d2 = await svc.create_deal(tenant.id, {"name": "Qual Deal"})

    stages = await svc.get_stages(tenant.id)
    qual_id = next(s["id"] for s in stages if s["name"] == "Qualificato")
    await svc.update_deal(uuid.UUID(d2["id"]), tenant.id, {"stage_id": qual_id})

    # List all deals
    all_deals = await svc.list_deals(tenant.id)
    assert all_deals["total"] == 2

    # Filter by stage
    lead_deals = await svc.list_deals(tenant.id, stage="Nuovo Lead")
    assert lead_deals["total"] == 1
    assert lead_deals["deals"][0]["name"] == "Lead Deal"

    qual_deals = await svc.list_deals(tenant.id, stage="Qualificato")
    assert qual_deals["total"] == 1
    assert qual_deals["deals"][0]["name"] == "Qual Deal"
