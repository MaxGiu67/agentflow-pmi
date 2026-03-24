"""
Test suite for ContoEconomicoAgent — personalised income statement onboarding.

Tests:
  - test_get_template_for_ateco_62       IT sector returns correct template
  - test_get_template_for_ateco_unknown  unknown code returns default template
  - test_questions_endpoint              returns questions for tenant
  - test_rule_based_personalization      works without LLM
  - test_create_personalized_chart       saves accounts to DB
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.agents.conto_economico_agent import (
    ATECO_TEMPLATES,
    DEFAULT_TEMPLATE,
    ContoEconomicoAgent,
)
from api.db.models import ChartAccount, Tenant, User
from tests.conftest import get_auth_token


# ============================================================
# Unit-level tests (agent logic, no HTTP)
# ============================================================


class TestGetTemplateForAteco:
    """Template selection based on ATECO code."""

    async def test_get_template_for_ateco_62(self, db_session: AsyncSession) -> None:
        """ATECO 62.xx -> Software e Consulenza IT template."""
        agent = ContoEconomicoAgent(db_session)
        template = agent.get_template_for_ateco("62.01.00")
        assert template["name"] == "Software e Consulenza IT"
        assert "Sviluppo software" in template["ricavi"]
        assert "Personale" in template["costi"]
        assert len(template["domande"]) >= 3

    async def test_get_template_for_ateco_46(self, db_session: AsyncSession) -> None:
        """ATECO 46.xx -> Commercio all'ingrosso."""
        agent = ContoEconomicoAgent(db_session)
        template = agent.get_template_for_ateco("46.90")
        assert template["name"] == "Commercio all'ingrosso"

    async def test_get_template_for_ateco_41(self, db_session: AsyncSession) -> None:
        """ATECO 41.xx -> Costruzioni e edilizia."""
        agent = ContoEconomicoAgent(db_session)
        template = agent.get_template_for_ateco("41.20")
        assert template["name"] == "Costruzioni e edilizia"

    async def test_get_template_for_ateco_56(self, db_session: AsyncSession) -> None:
        """ATECO 56.xx -> Ristorazione."""
        agent = ContoEconomicoAgent(db_session)
        template = agent.get_template_for_ateco("56.10")
        assert template["name"] == "Ristorazione"

    async def test_get_template_for_ateco_69(self, db_session: AsyncSession) -> None:
        """ATECO 69.xx -> Servizi professionali."""
        agent = ContoEconomicoAgent(db_session)
        template = agent.get_template_for_ateco("69.20")
        assert template["name"] == "Servizi professionali"

    async def test_get_template_for_ateco_agriculture(self, db_session: AsyncSession) -> None:
        """ATECO 01.xx -> Agricoltura."""
        agent = ContoEconomicoAgent(db_session)
        template = agent.get_template_for_ateco("01.11")
        assert template["name"] == "Agricoltura"

    async def test_get_template_for_ateco_manufacturing_range(self, db_session: AsyncSession) -> None:
        """ATECO 25.xx -> Manifatturiero (range 10-33)."""
        agent = ContoEconomicoAgent(db_session)
        template = agent.get_template_for_ateco("25.11")
        assert template["name"] == "Manifatturiero"

    async def test_get_template_for_ateco_transport_range(self, db_session: AsyncSession) -> None:
        """ATECO 52.xx -> range goes to specific or parent template."""
        agent = ContoEconomicoAgent(db_session)
        # 52 has its own template
        template = agent.get_template_for_ateco("52.10")
        assert template["name"] == "Magazzinaggio e supporto trasporti"

    async def test_get_template_for_ateco_unknown(self, db_session: AsyncSession) -> None:
        """Unknown ATECO code returns the default template."""
        agent = ContoEconomicoAgent(db_session)
        template = agent.get_template_for_ateco("99.99.99")
        assert template["name"] == DEFAULT_TEMPLATE["name"]
        assert template["ricavi"] == DEFAULT_TEMPLATE["ricavi"]
        assert template["costi"] == DEFAULT_TEMPLATE["costi"]

    async def test_get_template_for_ateco_empty(self, db_session: AsyncSession) -> None:
        """Empty ATECO code returns the default template."""
        agent = ContoEconomicoAgent(db_session)
        template = agent.get_template_for_ateco("")
        assert template["name"] == DEFAULT_TEMPLATE["name"]

    async def test_get_template_for_ateco_none_safe(self, db_session: AsyncSession) -> None:
        """None-ish ATECO code returns the default template without crashing."""
        agent = ContoEconomicoAgent(db_session)
        template = agent.get_template_for_ateco("")
        assert template["name"] == DEFAULT_TEMPLATE["name"]


class TestRuleBasedPersonalization:
    """Rule-based fallback produces sensible results."""

    async def test_rule_based_removes_personale_when_no_employees(
        self, db_session: AsyncSession,
    ) -> None:
        """Answering 'no dipendenti' removes Personale from costi."""
        agent = ContoEconomicoAgent(db_session)
        template = agent.get_template_for_ateco("62.01")
        answers = [
            {"question": "Hai dipendenti? Se si, quanti?", "answer": "No, nessuno"},
            {"question": "Lavori da un ufficio o da remoto?", "answer": "Da remoto"},
            {"question": "Utilizzi servizi cloud?", "answer": "Si, AWS"},
            {"question": "Hai collaboratori esterni?", "answer": "No"},
            {"question": "Vendi prodotti o servizi?", "answer": "Servizi"},
        ]
        result = agent._rule_based_personalization(template, answers)

        assert "Personale" not in result["costi"]
        assert result["has_dipendenti"] is False

    async def test_rule_based_removes_affitto_when_remote(
        self, db_session: AsyncSession,
    ) -> None:
        """Answering 'da remoto' removes rent from costi."""
        agent = ContoEconomicoAgent(db_session)
        template = agent.get_template_for_ateco("62.01")
        answers = [
            {"question": "Hai dipendenti? Se si, quanti?", "answer": "Si, 3 dipendenti"},
            {"question": "Lavori da un ufficio o da remoto?", "answer": "Da remoto, smart working"},
            {"question": "Utilizzi servizi cloud?", "answer": "No"},
            {"question": "Hai collaboratori esterni?", "answer": "No"},
            {"question": "Vendi prodotti o servizi?", "answer": "Servizi"},
        ]
        result = agent._rule_based_personalization(template, answers)

        assert "Affitto ufficio" not in result["costi"]
        assert result["has_dipendenti"] is True

    async def test_rule_based_keeps_affitto_when_office(
        self, db_session: AsyncSession,
    ) -> None:
        """Answering 'ufficio' keeps rent and sets has_affitto."""
        agent = ContoEconomicoAgent(db_session)
        template = agent.get_template_for_ateco("62.01")
        answers = [
            {"question": "Hai dipendenti? Se si, quanti?", "answer": "Si, 5"},
            {"question": "Lavori da un ufficio o da remoto?", "answer": "Ho un ufficio in centro"},
            {"question": "Utilizzi servizi cloud?", "answer": "Si, Azure"},
            {"question": "Hai collaboratori esterni?", "answer": "No"},
            {"question": "Vendi prodotti o servizi?", "answer": "Entrambi"},
        ]
        result = agent._rule_based_personalization(template, answers)

        assert result["has_affitto"] is True
        assert result["has_dipendenti"] is True

    async def test_rule_based_returns_valid_structure(
        self, db_session: AsyncSession,
    ) -> None:
        """Rule-based always returns the expected dict structure."""
        agent = ContoEconomicoAgent(db_session)
        template = agent.get_template_for_ateco("99.99")
        answers = [
            {"question": "Che tipo di attivita svolgi?", "answer": "Vendita online"},
        ]
        result = agent._rule_based_personalization(template, answers)

        assert "ricavi" in result
        assert "costi" in result
        assert "note" in result
        assert "has_dipendenti" in result
        assert "has_affitto" in result
        assert "regime_suggerito" in result
        assert isinstance(result["ricavi"], list)
        assert isinstance(result["costi"], list)


class TestCreatePersonalizedChart:
    """Saving the chart of accounts to DB."""

    async def test_create_personalized_chart(
        self, db_session: AsyncSession, tenant: Tenant,
    ) -> None:
        """Personalized chart creates correct ChartAccount rows."""
        agent = ContoEconomicoAgent(db_session)
        personalized = {
            "ricavi": ["Sviluppo software", "Consulenza IT"],
            "costi": ["Personale", "Servizi cloud e hosting", "Affitto ufficio"],
            "note": "Piano personalizzato per Software e Consulenza IT",
            "has_dipendenti": True,
            "has_affitto": True,
            "regime_suggerito": "ordinario",
        }

        result = await agent.create_personalized_chart(tenant.id, personalized)

        assert result["ricavi_count"] == 2
        assert result["costi_count"] == 3
        # 7 standard + 2 ricavi + 3 costi = 12
        assert result["total"] == 12
        assert len(result["accounts"]) == 12

        # Verify DB entries
        rows = await db_session.execute(
            select(ChartAccount).where(ChartAccount.tenant_id == tenant.id)
        )
        accounts = rows.scalars().all()
        assert len(accounts) == 12

        # Check types
        types = {a.account_type for a in accounts}
        assert "asset" in types
        assert "liability" in types
        assert "equity" in types
        assert "income" in types
        assert "expense" in types

    async def test_create_chart_replaces_existing(
        self, db_session: AsyncSession, tenant: Tenant,
    ) -> None:
        """Calling create_personalized_chart twice replaces existing accounts."""
        agent = ContoEconomicoAgent(db_session)

        # First creation
        plan1 = {
            "ricavi": ["Vendite"],
            "costi": ["Acquisti"],
            "note": "v1",
            "has_dipendenti": False,
            "has_affitto": False,
            "regime_suggerito": "forfettario",
        }
        await agent.create_personalized_chart(tenant.id, plan1)
        rows = await db_session.execute(
            select(func.count(ChartAccount.id)).where(
                ChartAccount.tenant_id == tenant.id
            )
        )
        count1 = rows.scalar_one()

        # Second creation — should replace
        plan2 = {
            "ricavi": ["R1", "R2", "R3"],
            "costi": ["C1", "C2"],
            "note": "v2",
            "has_dipendenti": True,
            "has_affitto": True,
            "regime_suggerito": "ordinario",
        }
        result2 = await agent.create_personalized_chart(tenant.id, plan2)

        rows2 = await db_session.execute(
            select(func.count(ChartAccount.id)).where(
                ChartAccount.tenant_id == tenant.id
            )
        )
        count2 = rows2.scalar_one()

        assert result2["ricavi_count"] == 3
        assert result2["costi_count"] == 2
        # 7 standard + 3 + 2 = 12
        assert count2 == 12

    async def test_cee_code_mapping_for_personnel(
        self, db_session: AsyncSession, tenant: Tenant,
    ) -> None:
        """Personnel costs get CEE code B.9, others get B.7."""
        agent = ContoEconomicoAgent(db_session)
        plan = {
            "ricavi": ["Vendite"],
            "costi": ["Personale dipendenti", "Affitto", "Marketing"],
            "note": "",
            "has_dipendenti": True,
            "has_affitto": True,
            "regime_suggerito": "ordinario",
        }
        result = await agent.create_personalized_chart(tenant.id, plan)

        expense_accounts = [a for a in result["accounts"] if a["account_type"] == "expense"]
        personale = [a for a in expense_accounts if "personal" in a["name"].lower() or "dipendent" in a["name"].lower()]
        altri = [a for a in expense_accounts if a not in personale]

        assert len(personale) == 1
        assert personale[0]["cee_code"] == "B.9"
        for a in altri:
            assert a["cee_code"] == "B.7"


# ============================================================
# Integration tests (HTTP endpoints)
# ============================================================


class TestQuestionsEndpoint:
    """GET /onboarding/conto-economico/questions."""

    async def test_questions_endpoint_returns_questions(
        self,
        client: AsyncClient,
        auth_headers: dict,
        tenant: Tenant,
    ) -> None:
        """Returns template-based questions for tenant's ATECO 62.01.00."""
        resp = await client.get(
            "/api/v1/onboarding/conto-economico/questions",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()

        assert data["template_name"] == "Software e Consulenza IT"
        assert len(data["questions"]) >= 3
        assert "ricavi_suggeriti" in data
        assert "costi_suggeriti" in data
        assert "invoice_analysis" in data

        # Each question has id, question, type
        for q in data["questions"]:
            assert "id" in q
            assert "question" in q
            assert "type" in q

    async def test_questions_endpoint_requires_auth(
        self,
        client: AsyncClient,
    ) -> None:
        """Unauthenticated request gets 403."""
        resp = await client.get("/api/v1/onboarding/conto-economico/questions")
        assert resp.status_code == 403


class TestAnswersEndpoint:
    """POST /onboarding/conto-economico/answers."""

    async def test_answers_returns_personalized_plan(
        self,
        client: AsyncClient,
        auth_headers: dict,
        tenant: Tenant,
    ) -> None:
        """Processing answers returns a personalized plan."""
        resp = await client.post(
            "/api/v1/onboarding/conto-economico/answers",
            headers=auth_headers,
            json={
                "answers": [
                    {"question": "Hai dipendenti? Se si, quanti?", "answer": "Si, 2 dipendenti"},
                    {"question": "Lavori da un ufficio o da remoto?", "answer": "Da remoto"},
                    {"question": "Utilizzi servizi cloud?", "answer": "Si, AWS circa 200 euro/mese"},
                    {"question": "Hai collaboratori esterni?", "answer": "Si, 1 freelance"},
                    {"question": "Vendi prodotti o servizi?", "answer": "Servizi di consulenza"},
                ],
            },
        )
        assert resp.status_code == 200
        data = resp.json()

        assert "ricavi" in data
        assert "costi" in data
        assert "note" in data
        assert "has_dipendenti" in data
        assert "regime_suggerito" in data
        assert isinstance(data["ricavi"], list)
        assert isinstance(data["costi"], list)
        assert len(data["ricavi"]) > 0
        assert len(data["costi"]) > 0


class TestConfirmEndpoint:
    """POST /onboarding/conto-economico/confirm."""

    async def test_confirm_saves_chart(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        tenant: Tenant,
    ) -> None:
        """Confirming a plan saves ChartAccount entries."""
        resp = await client.post(
            "/api/v1/onboarding/conto-economico/confirm",
            headers=auth_headers,
            json={
                "personalized": {
                    "ricavi": ["Sviluppo software", "Consulenza IT"],
                    "costi": ["Personale", "Servizi cloud e hosting"],
                    "note": "Piano personalizzato",
                    "has_dipendenti": True,
                    "has_affitto": False,
                    "regime_suggerito": "ordinario",
                },
            },
        )
        assert resp.status_code == 200
        data = resp.json()

        assert data["ricavi_count"] == 2
        assert data["costi_count"] == 2
        # 7 standard + 2 ricavi + 2 costi = 11
        assert data["total"] == 11
        assert len(data["accounts"]) == 11

    async def test_confirm_requires_auth(
        self,
        client: AsyncClient,
    ) -> None:
        """Unauthenticated request gets 403."""
        resp = await client.post(
            "/api/v1/onboarding/conto-economico/confirm",
            json={"personalized": {}},
        )
        assert resp.status_code == 403
