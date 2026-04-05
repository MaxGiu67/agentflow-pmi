"""Tests for Social Selling — Epic 5: Dashboards, Scorecard, Compensation (US-146→US-150)."""

import uuid
from datetime import date, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import (
    CrmDashboardWidget, CrmCompensationRule, CrmCompensationEntry,
    CrmDeal, CrmPipelineStage, CrmActivity, Tenant, User,
)
from tests.conftest import get_auth_token


@pytest.fixture
async def admin_user(db_session: AsyncSession, tenant: Tenant) -> User:
    import bcrypt
    user = User(
        email="admin.epic5@example.com",
        password_hash=bcrypt.hashpw(b"Password1", bcrypt.gensalt()).decode(),
        name="Admin Epic5", role="admin", email_verified=True, tenant_id=tenant.id,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def admin_headers(client: AsyncClient, admin_user: User) -> dict:
    token = await get_auth_token(client, "admin.epic5@example.com", "Password1")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def sales_user(db_session: AsyncSession, tenant: Tenant) -> User:
    import bcrypt
    user = User(
        email="sales.epic5@example.com",
        password_hash=bcrypt.hashpw(b"Password1", bcrypt.gensalt()).decode(),
        name="Sales Epic5", role="commerciale", email_verified=True, tenant_id=tenant.id,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def won_deals(db_session: AsyncSession, tenant: Tenant, sales_user: User) -> list:
    stage = CrmPipelineStage(
        tenant_id=tenant.id, name="Confermato", sequence=50,
        probability_default=100, is_won=True, stage_type="pipeline", is_active=True,
    )
    db_session.add(stage)
    await db_session.flush()
    deals = []
    for i, rev in enumerate([10000, 15000, 5000]):
        deal = CrmDeal(
            tenant_id=tenant.id, name=f"Deal Won {i}",
            stage_id=stage.id, expected_revenue=rev,
            probability=100, assigned_to=sales_user.id,
        )
        db_session.add(deal)
        deals.append(deal)
    await db_session.flush()
    return deals


@pytest.fixture
async def comp_rule(db_session: AsyncSession, tenant: Tenant, admin_user: User) -> CrmCompensationRule:
    rule = CrmCompensationRule(
        tenant_id=tenant.id, name="Base 5%",
        trigger="deal_won", calculation_method="percent_revenue",
        base_config={"rate": 5}, priority=0, is_active=True,
        created_by=admin_user.id,
    )
    db_session.add(rule)
    await db_session.flush()
    return rule


@pytest.fixture
async def comp_entry(db_session: AsyncSession, tenant: Tenant, sales_user: User) -> CrmCompensationEntry:
    entry = CrmCompensationEntry(
        tenant_id=tenant.id, user_id=sales_user.id,
        month=date(2026, 3, 1), amount_gross=1500,
        rules_applied=[{"rule_name": "Base 5%", "amount": 1500}],
        status="draft",
    )
    db_session.add(entry)
    await db_session.flush()
    return entry


# ══════════════════════════════════════════════════════
# US-146: Dashboards
# ══════════════════════════════════════════════════════


class TestUS146Dashboard:

    @pytest.mark.anyio
    async def test_ac_146_1_create_dashboard(self, client: AsyncClient, admin_headers: dict):
        resp = await client.post(
            "/api/v1/social/dashboards",
            json={
                "name": "Sales Overview",
                "dashboard_layout": [
                    {"widget_id": "revenue_mom", "type": "line", "title": "Revenue MoM", "period": "last_3_months"},
                    {"widget_id": "deal_count", "type": "number", "title": "Deal Count", "period": "ytd"},
                ],
                "is_shared": True,
            },
            headers=admin_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["name"] == "Sales Overview"
        assert len(resp.json()["dashboard_layout"]) == 2

    @pytest.mark.anyio
    async def test_ac_146_3_missing_period_rejected(self, client: AsyncClient, admin_headers: dict):
        resp = await client.post(
            "/api/v1/social/dashboards",
            json={
                "name": "Bad Dashboard",
                "dashboard_layout": [{"widget_id": "revenue", "type": "line", "title": "Rev"}],
            },
            headers=admin_headers,
        )
        assert resp.status_code == 400

    @pytest.mark.anyio
    async def test_ac_146_list_dashboards(self, client: AsyncClient, admin_headers: dict,
                                          db_session: AsyncSession, tenant: Tenant, admin_user: User):
        d = CrmDashboardWidget(
            tenant_id=tenant.id, name="Test Dash",
            dashboard_layout=[{"widget_id": "x", "period": "ytd"}],
            created_by=admin_user.id,
        )
        db_session.add(d)
        await db_session.flush()

        resp = await client.get("/api/v1/social/dashboards", headers=admin_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1


# ══════════════════════════════════════════════════════
# US-147: Scorecard
# ══════════════════════════════════════════════════════


class TestUS147Scorecard:

    @pytest.mark.anyio
    async def test_ac_147_1_scorecard_kpis(
        self, client: AsyncClient, admin_headers: dict,
        sales_user: User, won_deals: list,
    ):
        resp = await client.get(
            f"/api/v1/social/scorecard/{sales_user.id}?start_date=2020-01-01&end_date=2030-12-31",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        kpis = resp.json()["kpis"]
        assert kpis["won_count"] == 3
        assert kpis["revenue_closed"] == 30000

    @pytest.mark.anyio
    async def test_ac_147_3_user_no_data(
        self, client: AsyncClient, admin_headers: dict, admin_user: User,
    ):
        resp = await client.get(
            f"/api/v1/social/scorecard/{admin_user.id}",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        kpis = resp.json()["kpis"]
        assert kpis["deal_count"] == 0
        assert kpis["revenue_closed"] == 0


# ══════════════════════════════════════════════════════
# US-148: Compensation Rules
# ══════════════════════════════════════════════════════


class TestUS148CompensationRules:

    @pytest.mark.anyio
    async def test_ac_148_1_create_rule(self, client: AsyncClient, admin_headers: dict):
        resp = await client.post(
            "/api/v1/social/compensation-rules",
            json={
                "name": "Base 5%",
                "trigger": "deal_won",
                "calculation_method": "percent_revenue",
                "base_config": {"rate": 5},
            },
            headers=admin_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["name"] == "Base 5%"

    @pytest.mark.anyio
    async def test_ac_148_2_tiered_rule(self, client: AsyncClient, admin_headers: dict):
        resp = await client.post(
            "/api/v1/social/compensation-rules",
            json={
                "name": "Tiered",
                "calculation_method": "tiered",
                "base_config": {
                    "tiers": [
                        {"min": 0, "max": 50000, "rate": 5},
                        {"min": 50000, "max": 100000, "rate": 7},
                        {"min": 100000, "max": 999999999, "rate": 10},
                    ]
                },
            },
            headers=admin_headers,
        )
        assert resp.status_code == 201

    @pytest.mark.anyio
    async def test_ac_148_invalid_method(self, client: AsyncClient, admin_headers: dict):
        resp = await client.post(
            "/api/v1/social/compensation-rules",
            json={"name": "Bad", "calculation_method": "formula", "base_config": {}},
            headers=admin_headers,
        )
        assert resp.status_code == 400

    @pytest.mark.anyio
    async def test_ac_148_list_rules(
        self, client: AsyncClient, admin_headers: dict, comp_rule: CrmCompensationRule,
    ):
        resp = await client.get("/api/v1/social/compensation-rules", headers=admin_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1


# ══════════════════════════════════════════════════════
# US-149: Monthly Compensation Calculation
# ══════════════════════════════════════════════════════


class TestUS149MonthlyCompensation:

    @pytest.mark.anyio
    async def test_ac_149_1_calculate_monthly(
        self, client: AsyncClient, admin_headers: dict,
        won_deals: list, comp_rule: CrmCompensationRule,
    ):
        """30k revenue * 5% = 1500."""
        today = date.today()
        month_str = today.strftime("%Y-%m-01")
        resp = await client.post(
            f"/api/v1/social/compensation/calculate?month={month_str}",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        entries = resp.json()
        assert len(entries) >= 1
        assert entries[0]["amount_gross"] == 1500  # 30000 * 5%
        assert entries[0]["status"] == "draft"

    @pytest.mark.anyio
    async def test_ac_149_list_monthly(
        self, client: AsyncClient, admin_headers: dict, comp_entry: CrmCompensationEntry,
    ):
        resp = await client.get("/api/v1/social/compensation/monthly", headers=admin_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1


# ══════════════════════════════════════════════════════
# US-150: Confirm + Pay
# ══════════════════════════════════════════════════════


class TestUS150ConfirmPay:

    @pytest.mark.anyio
    async def test_ac_150_1_confirm_entry(
        self, client: AsyncClient, admin_headers: dict, comp_entry: CrmCompensationEntry,
    ):
        resp = await client.patch(
            f"/api/v1/social/compensation/monthly/{comp_entry.id}/confirm",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "confirmed"
        assert resp.json()["confirmed_at"] is not None

    @pytest.mark.anyio
    async def test_ac_150_3_mark_paid(
        self, client: AsyncClient, admin_headers: dict,
        db_session: AsyncSession, comp_entry: CrmCompensationEntry,
    ):
        comp_entry.status = "confirmed"
        comp_entry.confirmed_at = datetime.utcnow()
        await db_session.flush()

        resp = await client.patch(
            f"/api/v1/social/compensation/monthly/{comp_entry.id}/paid",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "paid"
        assert resp.json()["paid_at"] is not None

    @pytest.mark.anyio
    async def test_ac_150_cannot_pay_draft(
        self, client: AsyncClient, admin_headers: dict, comp_entry: CrmCompensationEntry,
    ):
        resp = await client.patch(
            f"/api/v1/social/compensation/monthly/{comp_entry.id}/paid",
            headers=admin_headers,
        )
        assert resp.status_code == 400
