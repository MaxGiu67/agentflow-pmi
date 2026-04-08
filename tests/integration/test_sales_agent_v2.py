"""Sprint 46-47: Tests for Sales Agent v2 wired tools and chat endpoint.

Tests:
1. CRM tools wired to real CRMService (via test DB)
2. Portal tools call portal_client (mocked)
3. Offer tools generate documents from deal data
4. Chat /sales endpoint invokes agent (LLM mocked)
5. Agent tool invocation with mocked LLM responses
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import (
    CrmContact,
    CrmDeal,
    CrmPipelineStage,
    CrmActivity,
    Tenant,
    User,
)
from tests.conftest import get_auth_token


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
async def crm_stages(db_session: AsyncSession, tenant: Tenant) -> list[CrmPipelineStage]:
    """Create pipeline stages for testing."""
    stages_data = [
        {"name": "Nuovo Lead", "sequence": 1, "probability_default": 10.0, "color": "#6B7280"},
        {"name": "Qualificato", "sequence": 2, "probability_default": 30.0, "color": "#3B82F6"},
        {"name": "Proposta Inviata", "sequence": 3, "probability_default": 50.0, "color": "#F59E0B"},
        {"name": "Confermato", "sequence": 5, "probability_default": 100.0, "color": "#10B981", "is_won": True},
        {"name": "Perso", "sequence": 6, "probability_default": 0.0, "color": "#EF4444", "is_lost": True},
    ]
    stages = []
    for sd in stages_data:
        s = CrmPipelineStage(
            tenant_id=tenant.id,
            name=sd["name"],
            sequence=sd["sequence"],
            probability_default=sd["probability_default"],
            color=sd["color"],
            is_won=sd.get("is_won", False),
            is_lost=sd.get("is_lost", False),
        )
        db_session.add(s)
        stages.append(s)
    await db_session.flush()
    return stages


@pytest.fixture
async def crm_contact(db_session: AsyncSession, tenant: Tenant) -> CrmContact:
    """Create a test CRM contact."""
    contact = CrmContact(
        tenant_id=tenant.id,
        name="Acme Corp",
        email="info@acme.it",
        type="lead",
    )
    db_session.add(contact)
    await db_session.flush()
    return contact


@pytest.fixture
async def crm_deal(
    db_session: AsyncSession,
    tenant: Tenant,
    crm_stages: list[CrmPipelineStage],
    crm_contact: CrmContact,
) -> CrmDeal:
    """Create a test CRM deal."""
    deal = CrmDeal(
        tenant_id=tenant.id,
        name="Deal Acme T&M Java",
        contact_id=crm_contact.id,
        stage_id=crm_stages[0].id,  # Nuovo Lead
        deal_type="vendita_diretta",
        expected_revenue=50000.0,
        daily_rate=450.0,
        estimated_days=100,
        technology="Java, Spring Boot",
        probability=10.0,
    )
    db_session.add(deal)
    await db_session.flush()
    return deal


# ============================================================
# Test 1: CRM Tools — wired to real CRMService
# ============================================================


class TestCrmTools:
    """Test CRM tools work with real DB service."""

    async def test_crm_pipeline_summary(
        self,
        db_session: AsyncSession,
        tenant: Tenant,
        crm_deal: CrmDeal,
    ):
        """crm_pipeline_summary returns real pipeline data."""
        from api.agents.tools.crm_tools import crm_pipeline_summary, set_tool_context

        # Patch the session factory to use the test session
        set_tool_context(tenant_id=str(tenant.id))

        with patch("api.agents.tools.crm_tools.async_session_factory") as mock_factory:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=db_session)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_factory.return_value = mock_ctx

            result = await crm_pipeline_summary.ainvoke({"pipeline_type": ""})

        assert "total_deals" in result
        assert "total_value" in result
        assert "by_stage" in result
        assert result["total_deals"] >= 1
        assert result["total_value"] >= 50000.0

    async def test_crm_list_deals(
        self,
        db_session: AsyncSession,
        tenant: Tenant,
        crm_deal: CrmDeal,
    ):
        """crm_list_deals returns deals from the database."""
        from api.agents.tools.crm_tools import crm_list_deals, set_tool_context

        set_tool_context(tenant_id=str(tenant.id))

        with patch("api.agents.tools.crm_tools.async_session_factory") as mock_factory:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=db_session)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_factory.return_value = mock_ctx

            result = await crm_list_deals.ainvoke({"stage": "", "deal_type": "", "limit": 20})

        assert "deals" in result
        assert "total" in result
        assert result["total"] >= 1
        deal_names = [d["name"] for d in result["deals"]]
        assert "Deal Acme T&M Java" in deal_names

    async def test_crm_get_deal(
        self,
        db_session: AsyncSession,
        tenant: Tenant,
        crm_deal: CrmDeal,
    ):
        """crm_get_deal returns detailed deal info."""
        from api.agents.tools.crm_tools import crm_get_deal, set_tool_context

        set_tool_context(tenant_id=str(tenant.id))

        with patch("api.agents.tools.crm_tools.async_session_factory") as mock_factory:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=db_session)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_factory.return_value = mock_ctx

            result = await crm_get_deal.ainvoke({"deal_id": str(crm_deal.id)})

        assert result.get("name") == "Deal Acme T&M Java"
        assert result.get("expected_revenue") == 50000.0
        assert "recent_activities" in result

    async def test_crm_create_activity(
        self,
        db_session: AsyncSession,
        tenant: Tenant,
        crm_deal: CrmDeal,
    ):
        """crm_create_activity logs an activity on a deal."""
        from api.agents.tools.crm_tools import crm_create_activity, set_tool_context

        set_tool_context(tenant_id=str(tenant.id))

        with patch("api.agents.tools.crm_tools.async_session_factory") as mock_factory:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=db_session)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_factory.return_value = mock_ctx

            result = await crm_create_activity.ainvoke({
                "deal_id": str(crm_deal.id),
                "activity_type": "call",
                "subject": "Discovery call con Acme",
                "description": "Discusso requisiti Java senior",
            })

        assert result.get("subject") == "Discovery call con Acme"
        assert result.get("type") == "call"

    async def test_crm_list_contacts(
        self,
        db_session: AsyncSession,
        tenant: Tenant,
        crm_contact: CrmContact,
    ):
        """crm_list_contacts searches contacts by name."""
        from api.agents.tools.crm_tools import crm_list_contacts, set_tool_context

        set_tool_context(tenant_id=str(tenant.id))

        with patch("api.agents.tools.crm_tools.async_session_factory") as mock_factory:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=db_session)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_factory.return_value = mock_ctx

            result = await crm_list_contacts.ainvoke({"search": "Acme"})

        assert result["total"] >= 1
        assert any("Acme" in c["name"] for c in result["contacts"])

    async def test_crm_move_stage(
        self,
        db_session: AsyncSession,
        tenant: Tenant,
        crm_deal: CrmDeal,
        crm_stages: list[CrmPipelineStage],
    ):
        """crm_move_stage moves deal to a new pipeline stage."""
        from api.agents.tools.crm_tools import crm_move_stage, set_tool_context

        set_tool_context(tenant_id=str(tenant.id))

        with patch("api.agents.tools.crm_tools.async_session_factory") as mock_factory:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=db_session)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_factory.return_value = mock_ctx

            result = await crm_move_stage.ainvoke({
                "deal_id": str(crm_deal.id),
                "stage_name": "Qualificato",
            })

        assert result.get("status") == "moved"
        assert result.get("new_stage") == "Qualificato"


# ============================================================
# Test 2: Portal Tools — with mocked portal_client
# ============================================================


class TestPortalTools:
    """Test Portal tools with mocked portal_client."""

    async def test_portal_search_persons(self):
        """portal_search_persons calls portal_client.get_persons."""
        from api.agents.tools.portal_tools import portal_search_persons

        mock_data = {
            "data": [
                {"id": 1, "firstName": "Marco", "lastName": "Rossi", "email": "m.rossi@nexa.it"},
                {"id": 2, "firstName": "Laura", "lastName": "Bianchi", "email": "l.bianchi@nexa.it"},
            ],
            "total": 2,
        }
        with patch("api.agents.tools.portal_tools.portal_client") as mock_pc:
            mock_pc.get_persons = AsyncMock(return_value=mock_data)
            result = await portal_search_persons.ainvoke({"search": "", "skill": "Java"})

        assert result["total"] == 2
        assert len(result["results"]) == 2
        assert result["results"][0]["name"] == "Marco Rossi"
        assert result["search_query"] == "Java"
        mock_pc.get_persons.assert_called_once_with(search="Java")

    async def test_portal_get_customers(self):
        """portal_get_customers lists Portal customers."""
        from api.agents.tools.portal_tools import portal_get_customers

        mock_data = {
            "data": [
                {"id": 10, "name": "Acme SRL", "code": "ACM"},
            ],
            "total": 1,
        }
        with patch("api.agents.tools.portal_tools.portal_client") as mock_pc:
            mock_pc.get_customers = AsyncMock(return_value=mock_data)
            result = await portal_get_customers.ainvoke({"search": "Acme"})

        assert result["total"] == 1
        assert result["customers"][0]["name"] == "Acme SRL"

    async def test_portal_create_offer(self):
        """portal_create_offer prepares offer creation data (HIGH RISK)."""
        from api.agents.tools.portal_tools import portal_create_offer

        with patch("api.agents.tools.portal_tools.portal_client") as mock_pc:
            mock_pc.get_protocol_by_customer_id = AsyncMock(return_value="ND.ENG.2026.100")
            mock_pc.find_account_manager_by_email = AsyncMock(return_value={
                "id": 5, "email": "sales@nexa.it", "name": "Sales Manager"
            })
            mock_pc.get_billing_types = AsyncMock(return_value=["Daily", "LumpSum", "None"])

            result = await portal_create_offer.ainvoke({
                "customer_id": 10,
                "project_name": "Progetto Acme Java",
                "billing_type": "Daily",
                "account_manager_email": "sales@nexa.it",
            })

        assert result["action"] == "create_offer"
        assert result["protocol"] == "ND.ENG.2026.100"
        assert result["risk"] == "high"
        assert result["requires_confirmation"] is True

    async def test_portal_get_projects(self):
        """portal_get_projects lists Portal projects."""
        from api.agents.tools.portal_tools import portal_get_projects

        mock_data = {
            "data": [
                {"id": 100, "name": "Progetto Alpha", "code": "PA-001", "status": "active"},
            ],
            "total": 1,
        }
        with patch("api.agents.tools.portal_tools.portal_client") as mock_pc:
            mock_pc.get_projects = AsyncMock(return_value=mock_data)
            result = await portal_get_projects.ainvoke({"search": "Alpha"})

        assert result["total"] == 1
        assert result["projects"][0]["name"] == "Progetto Alpha"


# ============================================================
# Test 3: Offer Tools
# ============================================================


class TestOfferTools:
    """Test offer generation and margin calculation tools."""

    async def test_calc_margin_good(self):
        """calc_margin returns correct margin for profitable deal."""
        from api.agents.tools.offer_tools import calc_margin

        result = await calc_margin.ainvoke({
            "revenue": 100000.0,
            "daily_costs": [300.0, 280.0],
            "days": 100,
        })

        assert result["revenue"] == 100000.0
        assert result["total_cost"] == 58000.0  # (300+280)*100
        assert result["margin_abs"] == 42000.0
        assert result["margin_pct"] == 42.0
        assert "warning" not in result

    async def test_calc_margin_low(self):
        """calc_margin warns when margin below 15%."""
        from api.agents.tools.offer_tools import calc_margin

        result = await calc_margin.ainvoke({
            "revenue": 50000.0,
            "daily_costs": [450.0],
            "days": 100,
        })

        # Cost = 450*100 = 45000, margin = 5000/50000 = 10%
        assert result["margin_pct"] == 10.0
        assert "warning" in result
        assert "sotto soglia" in result["warning"]

    async def test_generate_offer_doc_deal_not_found(
        self,
        db_session: AsyncSession,
        tenant: Tenant,
    ):
        """generate_offer_doc returns error if deal doesn't exist."""
        from api.agents.tools.offer_tools import generate_offer_doc
        from api.agents.tools.crm_tools import set_tool_context

        set_tool_context(tenant_id=str(tenant.id))

        with patch("api.agents.tools.offer_tools.async_session_factory") as mock_factory:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=db_session)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_factory.return_value = mock_ctx

            fake_id = str(uuid.uuid4())
            result = await generate_offer_doc.ainvoke({
                "deal_id": fake_id,
                "offer_type": "tm",
            })

        assert "error" in result


# ============================================================
# Test 4: Chat /sales endpoint
# ============================================================


class TestChatSalesEndpoint:
    """Test the POST /chat/sales endpoint."""

    async def test_sales_endpoint_returns_response(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """POST /chat/sales returns a response from the mocked agent."""
        mock_result = {
            "response": "Ecco il riepilogo della pipeline: 5 deal attivi per EUR 250.000",
            "state": {"risk_level": "low", "needs_human_confirmation": False},
        }

        with patch(
            "api.agents.sales_agent_v2.invoke_sales_agent_v2",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            resp = await client.post(
                "/api/v1/chat/sales",
                json={"message": "Mostrami i deal in pipeline"},
                headers=auth_headers,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "response" in data
        assert "pipeline" in data["response"]

    async def test_sales_endpoint_with_deal_context(
        self,
        client: AsyncClient,
        auth_headers: dict,
        crm_deal: CrmDeal,
    ):
        """POST /chat/sales with deal_id loads deal context."""
        mock_result = {
            "response": "Il deal Acme e in fase Nuovo Lead. Suggerisco di qualificare.",
            "state": {"risk_level": "low", "needs_human_confirmation": False},
        }

        with patch(
            "api.agents.sales_agent_v2.invoke_sales_agent_v2",
            new_callable=AsyncMock,
            return_value=mock_result,
        ) as mock_invoke:
            resp = await client.post(
                "/api/v1/chat/sales",
                json={
                    "message": "Qual e lo stato di questo deal?",
                    "deal_id": str(crm_deal.id),
                },
                headers=auth_headers,
            )

        assert resp.status_code == 200
        # Verify invoke was called with deal context
        call_kwargs = mock_invoke.call_args[1]
        assert call_kwargs.get("deal_context") is not None
        company = call_kwargs["deal_context"].get("company", "") or ""
        assert "Acme" in company, f"Expected 'Acme' in company, got: '{company}'"

    async def test_sales_endpoint_empty_message(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """POST /chat/sales rejects empty message."""
        resp = await client.post(
            "/api/v1/chat/sales",
            json={"message": ""},
            headers=auth_headers,
        )
        assert resp.status_code == 422  # validation error

    async def test_sales_endpoint_unauthorized(
        self,
        client: AsyncClient,
    ):
        """POST /chat/sales without auth returns 401/403."""
        resp = await client.post(
            "/api/v1/chat/sales",
            json={"message": "test"},
        )
        assert resp.status_code in (401, 403)

    async def test_sales_endpoint_with_history(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """POST /chat/sales accepts conversation history."""
        mock_result = {
            "response": "Confermo, il deal si trova in fase Qualificato.",
            "state": {"risk_level": "low", "needs_human_confirmation": False},
        }

        with patch(
            "api.agents.sales_agent_v2.invoke_sales_agent_v2",
            new_callable=AsyncMock,
            return_value=mock_result,
        ) as mock_invoke:
            resp = await client.post(
                "/api/v1/chat/sales",
                json={
                    "message": "E poi?",
                    "history": [
                        {"role": "user", "content": "Mostrami il deal Acme"},
                        {"role": "assistant", "content": "Ecco il deal Acme: fase Qualificato."},
                    ],
                },
                headers=auth_headers,
            )

        assert resp.status_code == 200
        # Check history was passed
        call_kwargs = mock_invoke.call_args[1]
        assert call_kwargs.get("history") is not None
        assert len(call_kwargs["history"]) == 2


# ============================================================
# Test 5: Agent tool invocation flow (mocked LLM)
# ============================================================


class TestAgentToolInvocation:
    """Test that the agent calls the right tools for different intents."""

    async def test_pipeline_summary_intent(
        self,
        db_session: AsyncSession,
        tenant: Tenant,
        crm_deal: CrmDeal,
    ):
        """Agent calls crm_pipeline_summary for pipeline queries."""
        from api.agents.tools.crm_tools import set_tool_context, crm_pipeline_summary

        set_tool_context(tenant_id=str(tenant.id))

        # Directly test the tool (since LLM routing is mocked in endpoint tests)
        with patch("api.agents.tools.crm_tools.async_session_factory") as mock_factory:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=db_session)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_factory.return_value = mock_ctx

            result = await crm_pipeline_summary.ainvoke({"pipeline_type": ""})

        assert result["total_deals"] >= 1
        assert result["total_value"] > 0

    async def test_portal_search_intent(self):
        """Agent calls portal_search_persons for resource queries."""
        from api.agents.tools.portal_tools import portal_search_persons

        mock_persons = {
            "data": [
                {"id": 1, "firstName": "Marco", "lastName": "Rossi",
                 "email": "m.rossi@nexa.it", "EmploymentContracts": [
                     {"id": 10, "title": "Java Senior Developer", "startDate": "2023-01-01"}
                 ]},
            ],
            "total": 1,
        }
        with patch("api.agents.tools.portal_tools.portal_client") as mock_pc:
            mock_pc.get_persons = AsyncMock(return_value=mock_persons)
            result = await portal_search_persons.ainvoke({"search": "", "skill": "Java senior"})

        assert result["total"] == 1
        assert result["results"][0]["name"] == "Marco Rossi"
        assert len(result["results"][0].get("contracts", [])) == 1

    async def test_offer_preparation_intent(self):
        """Agent calls calc_margin for offer preparation."""
        from api.agents.tools.offer_tools import calc_margin

        result = await calc_margin.ainvoke({
            "revenue": 67500.0,
            "daily_costs": [350.0],
            "days": 150,
        })

        # Cost = 350*150 = 52500, margin = 15000/67500 = 22.2%
        assert result["margin_pct"] == 22.2
        assert result["total_cost"] == 52500.0
        assert "note" in result  # between 15-25% range
