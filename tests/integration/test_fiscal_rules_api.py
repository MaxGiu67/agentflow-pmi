"""
Test suite for ADR-007: Fiscal rules and AccountingEngine.
Tests fiscal rule seeding, DB-based chart of accounts, and date-based rule lookup.
"""

import uuid
from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import ChartAccount, FiscalRule, Tenant, User
from api.modules.fiscal.accounting_engine import AccountingEngine
from api.modules.fiscal.seed_rules import seed_fiscal_rules, DEFAULT_FISCAL_RULES
from tests.conftest import get_auth_token


class TestFiscalRulesSeeded:
    """Fiscal rules are seeded and readable."""

    async def test_fiscal_rules_seeded(self, db_session: AsyncSession):
        """After seeding, all default fiscal rules are readable."""
        count = await seed_fiscal_rules(db_session)
        assert count == len(DEFAULT_FISCAL_RULES)

        engine = AccountingEngine(db_session)
        rules = await engine.list_fiscal_rules()
        assert len(rules) == len(DEFAULT_FISCAL_RULES)

        # Check a specific rule
        iva = await engine.get_fiscal_rule("iva_ordinaria")
        assert iva == "0.22"

    async def test_fiscal_rules_idempotent(self, db_session: AsyncSession):
        """Seeding twice does not create duplicates."""
        count1 = await seed_fiscal_rules(db_session)
        count2 = await seed_fiscal_rules(db_session)
        assert count1 == len(DEFAULT_FISCAL_RULES)
        assert count2 == 0  # No new inserts on second call

    async def test_fiscal_rules_api_endpoint(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession,
    ):
        """GET /api/v1/fiscal/rules returns seeded rules."""
        await seed_fiscal_rules(db_session)
        await db_session.commit()

        response = await client.get(
            "/api/v1/fiscal/rules",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == len(DEFAULT_FISCAL_RULES)
        assert len(data["rules"]) == len(DEFAULT_FISCAL_RULES)

    async def test_fiscal_rules_api_filter_by_key(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession,
    ):
        """GET /api/v1/fiscal/rules?key=iva returns only IVA-related rules."""
        await seed_fiscal_rules(db_session)
        await db_session.commit()

        response = await client.get(
            "/api/v1/fiscal/rules?key=iva",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        # Should contain iva_ordinaria, iva_ridotta, iva_minima,
        # soglia_minima_versamento_iva
        assert data["count"] >= 3
        for rule in data["rules"]:
            assert "iva" in rule["key"]


class TestPianoContiStoredInDB:
    """Chart accounts are persisted in ChartAccount table."""

    async def test_piano_conti_stored_in_db(
        self, db_session: AsyncSession, tenant: Tenant,
    ):
        """After creating piano conti, ChartAccount rows exist for the tenant."""
        engine = AccountingEngine(db_session)
        result = await engine.create_piano_conti(
            tenant_id=tenant.id,
            tipo_azienda="srl",
            regime_fiscale="ordinario",
        )

        # Verify accounts returned
        assert len(result["accounts"]) > 10

        # Verify persisted in DB
        piano = await engine.get_piano_conti(tenant.id)
        assert piano is not None
        assert len(piano["accounts"]) == len(result["accounts"])

        # Verify a specific account
        codes = {a["code"] for a in piano["accounts"]}
        assert "1010" in codes
        assert "4010" in codes

    async def test_piano_conti_force_recreate(
        self, db_session: AsyncSession, tenant: Tenant,
    ):
        """Force recreation deletes old accounts and creates new ones."""
        engine = AccountingEngine(db_session)

        # Create first time
        result1 = await engine.create_piano_conti(
            tenant_id=tenant.id,
            tipo_azienda="srl",
            regime_fiscale="ordinario",
        )

        # Force recreate
        result2 = await engine.create_piano_conti(
            tenant_id=tenant.id,
            tipo_azienda="srl",
            regime_fiscale="ordinario",
            force=True,
        )

        # Same number of accounts (no duplicates)
        piano = await engine.get_piano_conti(tenant.id)
        assert len(piano["accounts"]) == len(result1["accounts"])

    async def test_piano_conti_forfettario_no_iva(
        self, db_session: AsyncSession, tenant: Tenant,
    ):
        """Forfettario piano has no IVA accounts."""
        engine = AccountingEngine(db_session)
        result = await engine.create_piano_conti(
            tenant_id=tenant.id,
            tipo_azienda="piva",
            regime_fiscale="forfettario",
        )
        assert result["tax_codes"] == []
        account_names = {a["name"] for a in result["accounts"]}
        assert "IVA a debito" not in account_names
        assert "Imposta sostitutiva" in account_names


class TestGetFiscalRuleByDate:
    """Date-based fiscal rule lookup works correctly."""

    async def test_get_fiscal_rule_by_date(self, db_session: AsyncSession):
        """Rule valid as of a specific date is returned."""
        await seed_fiscal_rules(db_session)
        engine = AccountingEngine(db_session)

        # IVA ordinaria valid from 2013-10-01
        result = await engine.get_fiscal_rule("iva_ordinaria", as_of_date=date(2024, 1, 1))
        assert result == "0.22"

    async def test_get_fiscal_rule_before_valid_from(self, db_session: AsyncSession):
        """Rule before its valid_from date returns None."""
        await seed_fiscal_rules(db_session)
        engine = AccountingEngine(db_session)

        # Soglia forfettario valid from 2023-01-01 — check before that
        result = await engine.get_fiscal_rule("soglia_forfettario", as_of_date=date(2022, 6, 1))
        assert result is None

    async def test_get_fiscal_rule_nonexistent_key(self, db_session: AsyncSession):
        """Non-existent key returns None."""
        await seed_fiscal_rules(db_session)
        engine = AccountingEngine(db_session)

        result = await engine.get_fiscal_rule("non_existent_key")
        assert result is None

    async def test_get_fiscal_rule_with_valid_to(self, db_session: AsyncSession):
        """Rule with valid_to is respected."""
        # Create a rule with valid_to set
        rule = FiscalRule(
            key="test_rule_expiring",
            value="100",
            value_type="integer",
            valid_from=date(2020, 1, 1),
            valid_to=date(2022, 12, 31),
            law_reference="Test",
        )
        db_session.add(rule)
        await db_session.flush()

        engine = AccountingEngine(db_session)

        # Within range
        result = await engine.get_fiscal_rule("test_rule_expiring", as_of_date=date(2021, 6, 1))
        assert result == "100"

        # After valid_to
        result = await engine.get_fiscal_rule("test_rule_expiring", as_of_date=date(2023, 6, 1))
        assert result is None
