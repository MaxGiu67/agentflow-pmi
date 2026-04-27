"""Test snapshot endpoints state — banking, invoicing, sales, all."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_state_banking_returns_snapshot(client: AsyncClient, auth_headers):
    r = await client.get("/api/v1/state/banking", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "tenant_piva" in data
    assert "accounts_total" in data
    assert "tx_30d_in" in data
    assert "flags" in data
    assert isinstance(data["accounts"], list)
    assert isinstance(data["top_categories_30d"], list)


@pytest.mark.asyncio
async def test_state_invoicing_returns_snapshot(client: AsyncClient, auth_headers):
    r = await client.get("/api/v1/state/invoicing", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "active_ytd" in data
    assert "passive_ytd" in data
    assert "iva_saldo_q" in data
    assert isinstance(data["due_30d"], list)


@pytest.mark.asyncio
async def test_state_sales_returns_snapshot(client: AsyncClient, auth_headers):
    r = await client.get("/api/v1/state/sales", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "open_deals_count" in data
    assert "open_pipeline_value" in data
    assert "stages" in data
    assert isinstance(data["next_activities"], list)


@pytest.mark.asyncio
async def test_state_all_combines_three(client: AsyncClient, auth_headers):
    r = await client.get("/api/v1/state/all", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "banking" in data
    assert "invoicing" in data
    assert "sales" in data
    assert "all_flags" in data
    # Each subsection has its own structure
    assert "tx_30d_in" in data["banking"]
    assert "active_ytd" in data["invoicing"]
    assert "open_deals_count" in data["sales"]


@pytest.mark.asyncio
async def test_state_requires_auth(client: AsyncClient):
    r = await client.get("/api/v1/state/all")
    assert r.status_code in (401, 403)
