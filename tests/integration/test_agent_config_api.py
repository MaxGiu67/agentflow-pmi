"""
Test suite for Sprint 12: Agent Configuration API

US-A03: Agent Config — CRUD for agent display names, personalities, enabled/disabled.

9 tests covering: list with auto-defaults, update name, update enabled,
disable agent, reset defaults, invalid agent_type, unauthorized access,
update personality, idempotent defaults.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import AgentConfig, Tenant, User
from api.modules.agent_config.defaults import DEFAULT_AGENTS
from tests.conftest import get_auth_token


# ============================================================
# US-A03: List Agent Configs
# ============================================================


class TestListAgentConfigs:
    """Tests for GET /agents/config."""

    async def test_list_agent_configs_creates_defaults(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """First call to list configs creates defaults for the tenant."""
        resp = await client.get("/api/v1/agents/config", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] == len(DEFAULT_AGENTS)

        # Verify all default agent types are present
        agent_types = {item["agent_type"] for item in data["items"]}
        expected_types = {d["agent_type"] for d in DEFAULT_AGENTS}
        assert agent_types == expected_types

    async def test_list_agent_configs_idempotent(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Calling list twice doesn't duplicate configs."""
        resp1 = await client.get("/api/v1/agents/config", headers=auth_headers)
        assert resp1.status_code == 200
        total1 = resp1.json()["total"]

        resp2 = await client.get("/api/v1/agents/config", headers=auth_headers)
        assert resp2.status_code == 200
        total2 = resp2.json()["total"]

        assert total1 == total2


# ============================================================
# US-A03: Update Agent Config
# ============================================================


class TestUpdateAgentConfig:
    """Tests for PATCH /agents/config/{agent_type}."""

    async def test_update_agent_display_name(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Can update an agent's display name."""
        resp = await client.patch(
            "/api/v1/agents/config/fisco",
            json={"display_name": "Il Mio Fiscalista"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_type"] == "fisco"
        assert data["display_name"] == "Il Mio Fiscalista"

    async def test_update_agent_enabled(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Can enable/disable an agent."""
        resp = await client.patch(
            "/api/v1/agents/config/cashflow",
            json={"enabled": True},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["enabled"] is True

    async def test_disable_agent(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Disabling an agent sets enabled=False."""
        resp = await client.patch(
            "/api/v1/agents/config/normativo",
            json={"enabled": False},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["enabled"] is False
        assert resp.json()["agent_type"] == "normativo"

    async def test_update_agent_personality(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Can update an agent's personality."""
        new_personality = "Sono un esperto fiscale molto amichevole."
        resp = await client.patch(
            "/api/v1/agents/config/fisco",
            json={"personality": new_personality},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["personality"] == new_personality

    async def test_update_invalid_agent_type(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Updating a non-existent agent type returns 404."""
        resp = await client.patch(
            "/api/v1/agents/config/nonexistent_agent",
            json={"display_name": "Test"},
            headers=auth_headers,
        )
        assert resp.status_code == 404


# ============================================================
# US-A03: Reset Defaults
# ============================================================


class TestResetDefaults:
    """Tests for POST /agents/config/reset."""

    async def test_reset_defaults(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Reset restores all configs to default values."""
        resp = await client.post("/api/v1/agents/config/reset", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == len(DEFAULT_AGENTS)
        assert "ripristinate" in data["message"].lower() or "default" in data["message"].lower()


# ============================================================
# Auth
# ============================================================


class TestAgentConfigAuth:
    """Tests for authentication on agent config endpoints."""

    async def test_unauthorized(
        self,
        client: AsyncClient,
    ):
        """No token returns 401/403 on agent config endpoints."""
        resp = await client.get("/api/v1/agents/config")
        assert resp.status_code in (401, 403)

        resp2 = await client.patch(
            "/api/v1/agents/config/fisco",
            json={"display_name": "Test"},
        )
        assert resp2.status_code in (401, 403)

        resp3 = await client.post("/api/v1/agents/config/reset")
        assert resp3.status_code in (401, 403)
