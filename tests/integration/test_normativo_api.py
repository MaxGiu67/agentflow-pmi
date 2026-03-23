"""
Test suite for US-28: Monitor aggiornamenti normativi
Tests for 4 Acceptance Criteria (AC-28.1 through AC-28.4)
"""

import uuid
from datetime import date, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import FiscalRule, NormativeAlert, Tenant


# ============================================================
# AC-28.1 — Alert su circolare AdE (feed RSS GU mock)
# ============================================================


class TestAC281AlertCircolare:
    """AC-28.1: Alert su circolare AdE (feed RSS GU mock)."""

    async def test_ac_281_check_feed_returns_alerts(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-28.1: DATO feed RSS disponibile,
        QUANDO POST /normativo/check,
        ALLORA nuovi alert creati da circolari."""
        resp = await client.post(
            "/api/v1/normativo/check",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert len(data["alerts"]) >= 1

        # Check alert has required fields
        alert = data["alerts"][0]
        assert "title" in alert
        assert "source" in alert
        assert alert["source"] in ("agenzia_entrate", "gazzetta_ufficiale")

    async def test_ac_281_list_alerts(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-28.1: DATO alert generati, QUANDO GET /normativo/alerts,
        ALLORA lista alert."""
        # First check feed to create alerts
        await client.post("/api/v1/normativo/check", headers=auth_headers)

        resp = await client.get(
            "/api/v1/normativo/alerts",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1

    async def test_ac_281_idempotent_check(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-28.1: DATO feed gia verificato, QUANDO secondo check,
        ALLORA non duplica alert."""
        # First check
        resp1 = await client.post("/api/v1/normativo/check", headers=auth_headers)
        count1 = len(resp1.json()["alerts"])

        # Second check
        resp2 = await client.post("/api/v1/normativo/check", headers=auth_headers)
        count2 = len(resp2.json()["alerts"])

        # Second check should find 0 new alerts
        assert count2 == 0


# ============================================================
# AC-28.2 — Propone aggiornamento regole con preview impatto
# ============================================================


class TestAC282PreviewImpatto:
    """AC-28.2: Propone aggiornamento regole con preview impatto."""

    async def test_ac_282_impact_preview_generated(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-28.2: DATO nuova norma rilevata,
        QUANDO check feed, ALLORA preview impatto generata."""
        resp = await client.post(
            "/api/v1/normativo/check",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["alerts"]) >= 1

        # All alerts should have impact preview
        for alert in data["alerts"]:
            assert alert["impact_preview"] is not None
            assert len(alert["impact_preview"]) > 0

    async def test_ac_282_proposed_rule_change(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-28.2: DATO norma con proposta modifica regola,
        QUANDO check, ALLORA regola proposta con chiave e valore."""
        resp = await client.post(
            "/api/v1/normativo/check",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()

        # At least one alert should have proposed rule
        alerts_with_rules = [
            a for a in data["alerts"]
            if a.get("proposed_rule_key")
        ]
        assert len(alerts_with_rules) >= 1

        alert = alerts_with_rules[0]
        assert alert["proposed_rule_key"] is not None
        assert alert["proposed_rule_value"] is not None


# ============================================================
# AC-28.3 — Feed non disponibile -> retry backoff
# ============================================================


class TestAC283FeedNonDisponibile:
    """AC-28.3: Feed non disponibile -> retry backoff."""

    async def test_ac_283_feed_unavailable_retry(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-28.3: DATO feed RSS non disponibile,
        QUANDO check, ALLORA status feed_unavailable con retry."""
        from api.agents.normativo_agent import NormativoAgent

        # Use the service directly to control feed availability
        agent = NormativoAgent(db_session)
        agent.set_feed_available(False)

        result = await agent.check_feed(tenant.id)
        assert result["status"] == "feed_unavailable"
        assert result["retry_scheduled"] is True
        assert "non disponibile" in result["message"].lower()
        assert len(result["alerts"]) == 0


# ============================================================
# AC-28.4 — Norma con decorrenza futura -> schedula
# ============================================================


class TestAC284DecorrenzaFutura:
    """AC-28.4: Norma con decorrenza futura -> schedula, non modifica regole correnti."""

    async def test_ac_284_future_effective_date_scheduled(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-28.4: DATO norma con decorrenza futura,
        QUANDO check, ALLORA alert status=scheduled, regola futura creata."""
        resp = await client.post(
            "/api/v1/normativo/check",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()

        # Find alert with future effective date
        scheduled_alerts = [
            a for a in data["alerts"]
            if a.get("status") == "scheduled"
        ]
        assert len(scheduled_alerts) >= 1

        scheduled = scheduled_alerts[0]
        assert scheduled["effective_date"] is not None
        effective = date.fromisoformat(scheduled["effective_date"])
        assert effective > date.today()

    async def test_ac_284_future_rule_not_applied_now(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-28.4: DATO regola con decorrenza futura,
        QUANDO creata, ALLORA valid_from futuro, non sovrascrive regole correnti."""
        # Check feed to create scheduled rules
        await client.post("/api/v1/normativo/check", headers=auth_headers)

        # Verify FiscalRule with future valid_from was created
        result = await db_session.execute(
            select(FiscalRule).where(
                FiscalRule.valid_from > date.today(),
            )
        )
        future_rules = result.scalars().all()
        assert len(future_rules) >= 1

        # The rule should have future valid_from
        for rule in future_rules:
            assert rule.valid_from > date.today()
            assert "programmato" in rule.description.lower() or "decorrenza" in rule.description.lower()

    async def test_ac_284_past_effective_date_applied(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-28.4: DATO norma con decorrenza passata,
        QUANDO check, ALLORA regola applicata immediatamente."""
        from api.agents.normativo_agent import NormativoAgent

        agent = NormativoAgent(db_session)

        # Set mock items with past effective date
        agent.set_mock_items([
            {
                "source": "agenzia_entrate",
                "title": "Circolare test passata - Bollo elettronico",
                "description": "Aggiornamento importo bollo virtuale.",
                "url": "https://example.com/test",
                "published_at": "2026-01-01T10:00:00",
                "effective_date": "2026-01-01",  # Past date
                "proposed_rule_key": "bollo_virtuale",
                "proposed_rule_value": "2.50",
            },
        ])

        result = await agent.check_feed(tenant.id)
        assert len(result["alerts"]) >= 1

        # Rule with past date should be applied
        applied_alerts = [a for a in result["alerts"] if a["status"] == "applied"]
        assert len(applied_alerts) >= 1

        # Verify FiscalRule was created with past date
        rule_result = await db_session.execute(
            select(FiscalRule).where(
                FiscalRule.key == "bollo_virtuale",
            )
        )
        rule = rule_result.scalar_one_or_none()
        assert rule is not None
        assert rule.value == "2.50"
        assert rule.valid_from <= date.today()
