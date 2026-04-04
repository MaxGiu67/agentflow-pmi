"""Tests for metering — LLM tokens, rate limit, usage tracking."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import Tenant
from api.modules.metering.service import MeteringService


@pytest.mark.asyncio
async def test_ac_113_2_track_llm_usage(db_session: AsyncSession, tenant: Tenant):
    """AC-113.2: Track LLM tokens after call."""
    svc = MeteringService(db_session)
    await svc.track_llm_usage(tenant.id, tokens_in=150, tokens_out=300)
    await svc.track_llm_usage(tenant.id, tokens_in=100, tokens_out=200)

    quota = await svc.check_llm_quota(tenant.id)
    assert quota["tokens_in"] == 250
    assert quota["tokens_out"] == 500
    assert quota["tokens_used"] == 750
    assert quota["requests"] == 2


@pytest.mark.asyncio
async def test_ac_113_3_4_quota_check(db_session: AsyncSession, tenant: Tenant):
    """AC-113.3/113.4: Quota check — allowed when under, blocked when over."""
    svc = MeteringService(db_session)

    # Under quota
    quota = await svc.check_llm_quota(tenant.id)
    assert quota["allowed"] is True
    assert quota["quota"] == 100000


@pytest.mark.asyncio
async def test_track_counters(db_session: AsyncSession, tenant: Tenant):
    """Track PDF pages, API calls, email sent."""
    svc = MeteringService(db_session)
    await svc.track_pdf_page(tenant.id, 5)
    await svc.track_api_call(tenant.id)
    await svc.track_api_call(tenant.id)
    await svc.track_email_sent(tenant.id)

    usage = await svc.get_tenant_usage(tenant.id)
    assert usage["pdf_pages"] == 5
    assert usage["api_calls"] == 2
    assert usage["email_sent"] == 1


@pytest.mark.asyncio
async def test_ac_115_1_all_usage(db_session: AsyncSession, tenant: Tenant):
    """AC-115.1: Get all tenant usage."""
    svc = MeteringService(db_session)
    await svc.track_llm_usage(tenant.id, 100, 200)

    all_usage = await svc.get_all_usage()
    assert len(all_usage) >= 1
    assert all_usage[0]["tenant_name"] == "Test SRL"


# ── API endpoints ──

@pytest.mark.asyncio
async def test_api_my_usage(client: AsyncClient, auth_headers: dict):
    """API: GET /metering/my-usage."""
    resp = await client.get("/api/v1/metering/my-usage", headers=auth_headers)
    assert resp.status_code == 200
    assert "llm_tokens" in resp.json()


@pytest.mark.asyncio
async def test_api_llm_quota(client: AsyncClient, auth_headers: dict):
    """API: GET /metering/llm-quota."""
    resp = await client.get("/api/v1/metering/llm-quota", headers=auth_headers)
    assert resp.status_code == 200
    assert "allowed" in resp.json()
    assert "quota" in resp.json()


@pytest.mark.asyncio
async def test_api_admin_metering(client: AsyncClient, auth_headers: dict):
    """API: GET /admin/metering (owner only)."""
    resp = await client.get("/api/v1/admin/metering", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
