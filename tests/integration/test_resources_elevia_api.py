"""Tests for Resources + Elevia Engine — Sprint 36-38 (US-204→US-210, US-220).

Covers:
- US-204: CRUD resources + skills
- US-205: Resource matching
- US-206: Margin calculation
- US-207: Bench tracking
- US-208: Elevia use case catalog + seed
- US-209: Prospect scoring
- US-210: ROI calculator
- US-220: Discovery brief
"""

import uuid
from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import Resource, ResourceSkill, Tenant
from api.modules.resources.service import ResourceService
from api.modules.elevia.service import EleviaService


# ── Resources ──────────────────────────────────────────


class TestUS204ResourceCRUD:
    @pytest.mark.anyio
    async def test_create_resource(self, db_session: AsyncSession, tenant: Tenant):
        svc = ResourceService(db_session)
        r = await svc.create_resource(tenant.id, {
            "name": "Marco Bianchi", "seniority": "senior", "daily_cost": 400,
            "suggested_daily_rate": 600,
        })
        assert r["name"] == "Marco Bianchi"
        assert r["seniority"] == "senior"
        assert r["daily_cost"] == 400

    @pytest.mark.anyio
    async def test_add_skill(self, db_session: AsyncSession, tenant: Tenant):
        svc = ResourceService(db_session)
        r = await svc.create_resource(tenant.id, {"name": "Luca Verdi", "seniority": "mid"})
        skill = await svc.add_skill(uuid.UUID(r["id"]), {"skill_name": "Java", "skill_level": 4})
        assert skill["skill_name"] == "Java"
        assert skill["skill_level"] == 4

    @pytest.mark.anyio
    async def test_list_filter_by_skill(self, db_session: AsyncSession, tenant: Tenant):
        svc = ResourceService(db_session)
        r1 = await svc.create_resource(tenant.id, {"name": "Java Dev", "seniority": "senior"})
        r2 = await svc.create_resource(tenant.id, {"name": "Angular Dev", "seniority": "mid"})
        await svc.add_skill(uuid.UUID(r1["id"]), {"skill_name": "Java", "skill_level": 5})
        await svc.add_skill(uuid.UUID(r2["id"]), {"skill_name": "Angular", "skill_level": 4})

        java_devs = await svc.list_resources(tenant.id, skill="Java")
        assert len(java_devs) == 1
        assert java_devs[0]["name"] == "Java Dev"


class TestUS205Matching:
    @pytest.mark.anyio
    async def test_match_by_stack(self, db_session: AsyncSession, tenant: Tenant):
        svc = ResourceService(db_session)
        r1 = await svc.create_resource(tenant.id, {"name": "Full Stack", "seniority": "senior"})
        r2 = await svc.create_resource(tenant.id, {"name": "Backend Only", "seniority": "senior"})
        await svc.add_skill(uuid.UUID(r1["id"]), {"skill_name": "Java", "skill_level": 5})
        await svc.add_skill(uuid.UUID(r1["id"]), {"skill_name": "Spring", "skill_level": 4})
        await svc.add_skill(uuid.UUID(r1["id"]), {"skill_name": "Angular", "skill_level": 3})
        await svc.add_skill(uuid.UUID(r2["id"]), {"skill_name": "Java", "skill_level": 4})

        results = await svc.match_resources(tenant.id, tech_stack=["Java", "Spring", "Angular"], seniority="senior")
        assert len(results) >= 1
        assert results[0]["name"] == "Full Stack"  # Higher match score
        assert results[0]["match_score"] > results[1]["match_score"] if len(results) > 1 else True

    @pytest.mark.anyio
    async def test_match_zero_results(self, db_session: AsyncSession, tenant: Tenant):
        svc = ResourceService(db_session)
        results = await svc.match_resources(tenant.id, tech_stack=["Golang"])
        assert len(results) == 0


class TestUS206Margin:
    def test_margin_ok(self):
        svc = ResourceService(None)
        result = svc.calc_margin(600, 400)
        assert result["margin_pct"] == 33.3
        assert result["status"] == "ok"
        assert result["below_threshold"] is False

    def test_margin_below_threshold(self):
        svc = ResourceService(None)
        result = svc.calc_margin(450, 400)
        assert result["margin_pct"] == 11.1
        assert result["status"] == "needs_approval"
        assert result["below_threshold"] is True


class TestUS207Bench:
    @pytest.mark.anyio
    async def test_bench_upcoming(self, db_session: AsyncSession, tenant: Tenant):
        svc = ResourceService(db_session)
        await svc.create_resource(tenant.id, {
            "name": "Liberando", "seniority": "senior",
            "available_from": date.today() + timedelta(days=10),
        })
        await svc.create_resource(tenant.id, {
            "name": "Occupato", "seniority": "mid",
            "available_from": date.today() + timedelta(days=60),
        })

        bench = await svc.get_bench(tenant.id, days_ahead=30)
        names = [r["name"] for r in bench]
        assert "Liberando" in names
        assert "Occupato" not in names


# ── Elevia ─────────────────────────────────────────────


class TestUS208UseCaseCatalog:
    @pytest.mark.anyio
    async def test_seed_use_cases(self, db_session: AsyncSession, tenant: Tenant):
        svc = EleviaService(db_session)
        cases = await svc.list_use_cases(tenant.id)
        assert len(cases) >= 11
        codes = [c["code"] for c in cases]
        assert "UC01" in codes
        assert "UC02" in codes
        assert "UC14" in codes

    @pytest.mark.anyio
    async def test_use_case_has_ateco_matrix(self, db_session: AsyncSession, tenant: Tenant):
        svc = EleviaService(db_session)
        cases = await svc.list_use_cases(tenant.id)
        uc02 = next(c for c in cases if c["code"] == "UC02")
        assert len(uc02["ateco_matrix"]) >= 3


class TestUS209ProspectScoring:
    @pytest.mark.anyio
    async def test_score_metallurgia_qualified(self, db_session: AsyncSession, tenant: Tenant):
        svc = EleviaService(db_session)
        result = await svc.score_prospect(
            tenant.id, ateco_code="25.11", employee_count=80, has_decision_maker=True,
        )
        assert result["total_score"] >= 60
        assert result["is_qualified"] is True
        assert len(result["applicable_use_cases"]) >= 3
        assert result["suggested_bundle"] is not None
        assert result["suggested_bundle"]["name"] == "Metallurgia Standard"

    @pytest.mark.anyio
    async def test_score_off_target(self, db_session: AsyncSession, tenant: Tenant):
        svc = EleviaService(db_session)
        result = await svc.score_prospect(tenant.id, ateco_code="56.10", employee_count=20)
        assert result["total_score"] < 40
        assert result["is_qualified"] is False


class TestUS210ROI:
    def test_roi_calculation(self):
        svc = EleviaService(None)
        result = svc.calc_roi(use_case_count=4, hourly_cost=35, elevia_annual_cost=6000)
        assert result["annual_savings_eur"] > 0
        assert result["roi_pct"] > 0
        assert result["payback_months"] > 0


class TestUS220DiscoveryBrief:
    def test_brief_metallurgia(self):
        svc = EleviaService(None)
        brief = svc.get_discovery_brief("25")
        assert len(brief["pain_points"]) >= 3
        assert len(brief["candidate_use_cases"]) >= 3
        assert len(brief["discovery_questions"]) >= 4
        assert brief["suggested_bundle"]["name"] == "Metallurgia Standard"


# ── API Endpoints ──────────────────────────────────────


class TestResourcesAPI:
    @pytest.mark.anyio
    async def test_api_create_resource(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post("/api/v1/resources", json={
            "name": "API Test Dev", "seniority": "senior", "daily_cost": 350,
        }, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["name"] == "API Test Dev"

    @pytest.mark.anyio
    async def test_api_list_resources(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/resources", headers=auth_headers)
        assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_api_margin(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/resources/margin?daily_rate=600&daily_cost=400", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["margin_pct"] == 33.3

    @pytest.mark.anyio
    async def test_api_match(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/resources/match?tech_stack=Java&seniority=senior", headers=auth_headers)
        assert resp.status_code == 200


class TestEleviaAPI:
    @pytest.mark.anyio
    async def test_api_list_use_cases(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/elevia/use-cases", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 11

    @pytest.mark.anyio
    async def test_api_score_prospect(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post("/api/v1/elevia/score-prospect", json={
            "ateco_code": "25", "employee_count": 80, "has_decision_maker": True,
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["is_qualified"] is True

    @pytest.mark.anyio
    async def test_api_discovery_brief(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/elevia/discovery-brief?ateco=25", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()["pain_points"]) >= 3

    @pytest.mark.anyio
    async def test_api_roi(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/elevia/roi?use_case_count=4", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["roi_pct"] > 0
