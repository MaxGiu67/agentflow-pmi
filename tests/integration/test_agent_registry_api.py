"""Tests for Agent Registry — Sprint 34 (US-211, US-213).

Covers:
- Agent registry: list, get, route
- Controller Agent: tool mapping
- Sales Agent: tool filtering by context
- Analytics Agent: routing
"""

import pytest

from api.agents.base import BaseAgent
from api.agents.registry import get_agent, list_agents, route_to_agent, get_agent_for_tool
from api.agents.controller_agent import ControllerAgent
from api.agents.analytics_agent import AnalyticsAgent
from api.agents.sales_agent import SalesAgent


class TestAgentRegistry:
    """US-211: Agent registry e dispatch."""

    def test_ac_211_1_registry_contains_3_agents(self):
        """AC-211.1: Registry has controller, analytics, sales."""
        agents = list_agents()
        names = [a.name for a in agents]
        assert "controller" in names
        assert "analytics" in names
        assert "sales" in names
        assert len(agents) == 3

    def test_ac_211_2_get_agent_by_name(self):
        """Get agent by name returns correct instance."""
        ctrl = get_agent("controller")
        assert ctrl is not None
        assert isinstance(ctrl, ControllerAgent)

        sales = get_agent("sales")
        assert isinstance(sales, SalesAgent)

        none = get_agent("nonexistent")
        assert none is None

    def test_ac_211_3_route_fatture_to_controller(self):
        """Route 'fatture' keyword to controller."""
        agent = route_to_agent("mostra le fatture di marzo")
        assert agent.name == "controller"

    def test_ac_211_3_route_offerta_to_sales(self):
        """Route 'offerta' keyword to sales."""
        agent = route_to_agent("prepara offerta per ACME")
        assert agent.name == "sales"

    def test_ac_211_3_route_cashflow_to_analytics(self):
        """Route 'cashflow' keyword to analytics."""
        agent = route_to_agent("previsione cashflow 90 giorni")
        assert agent.name == "analytics"

    def test_ac_211_3_route_deal_context_to_sales(self):
        """Route with deal context biases toward sales."""
        agent = route_to_agent("come va?", context={"deal": {"id": "123"}})
        assert agent.name == "sales"

    def test_ac_211_3_route_ambiguous_to_controller(self):
        """Route ambiguous message defaults to controller."""
        agent = route_to_agent("buongiorno")
        assert agent.name == "controller"

    def test_ac_211_4_get_agent_for_tool(self):
        """Tool → agent mapping."""
        assert get_agent_for_tool("count_invoices") == "controller"
        assert get_agent_for_tool("crm_pipeline_summary") in ("sales", "analytics")  # shared tool
        assert get_agent_for_tool("predict_cashflow") == "analytics"
        assert get_agent_for_tool("unknown_tool") == "controller"  # fallback


class TestControllerAgent:
    """US-213: Controller Agent wraps 17 existing tools."""

    def test_ac_213_1_has_17_tools(self):
        """Controller has all 17 existing tools."""
        ctrl = ControllerAgent()
        assert len(ctrl.tool_names) == 17

    def test_ac_213_1_includes_key_tools(self):
        """Controller includes critical tools."""
        ctrl = ControllerAgent()
        assert "count_invoices" in ctrl.tool_names
        assert "get_balance_sheet_summary" in ctrl.tool_names
        assert "apertura_conti" in ctrl.tool_names
        assert "get_fiscal_alerts" in ctrl.tool_names

    def test_ac_213_1_system_prompt(self):
        """Controller has Italian system prompt."""
        ctrl = ControllerAgent()
        prompt = ctrl.get_system_prompt()
        assert "controller" in prompt.lower() or "fatture" in prompt.lower()


class TestSalesAgent:
    """US-212: Sales Agent with tool filtering."""

    def test_ac_212_core_tools_always_available(self):
        """Sales Agent always has core CRM tools."""
        sales = SalesAgent()
        tools = sales.get_tool_names()
        assert "crm_pipeline_summary" in tools
        assert "crm_list_deals" in tools

    def test_ac_212_1_tm_tools_with_tm_deal(self):
        """T&M deal context adds T&M tools."""
        sales = SalesAgent()
        context = {"deal": {"pipeline_type": "tm_consulting"}}
        tools = sales.get_tool_names(context)
        # Core tools present
        assert "crm_list_deals" in tools
        # T&M tools will be added when implemented (Sprint 37)
        # For now, PIPELINE_TOOLS["tm_consulting"] is empty

    def test_ac_212_3_no_deal_core_only(self):
        """No deal context = core tools only."""
        sales = SalesAgent()
        tools = sales.get_tool_names(context=None)
        assert tools == sales.get_tool_names()

    def test_ac_212_system_prompt_with_deal(self):
        """System prompt includes deal context."""
        sales = SalesAgent()
        context = {"deal": {
            "company": "ACME SRL",
            "product": "Consulenza Java",
            "pipeline_type": "tm_consulting",
            "current_stage": "qualifica",
            "last_contact": "2026-04-01",
        }}
        prompt = sales.get_system_prompt(context)
        assert "ACME SRL" in prompt
        assert "qualifica" in prompt

    def test_ac_212_system_prompt_without_deal(self):
        """System prompt without deal is generic."""
        sales = SalesAgent()
        prompt = sales.get_system_prompt()
        assert "assistente commerciale" in prompt.lower()
        assert "DEAL CORRENTE" not in prompt


class TestAnalyticsAgent:
    """Analytics Agent routing and tools."""

    def test_analytics_has_tools(self):
        agent = AnalyticsAgent()
        assert "predict_cashflow" in agent.tool_names

    def test_analytics_keywords(self):
        agent = AnalyticsAgent()
        score = agent.matches_intent("previsione cashflow 90 giorni")
        assert score > 0.3

    def test_analytics_no_match_fatture(self):
        agent = AnalyticsAgent()
        score = agent.matches_intent("mostra fatture")
        assert score < 0.2
