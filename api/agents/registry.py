"""Agent Registry — plugin pattern for agent discovery (US-211, ADR-010).

To add a new agent:
1. Create a file in api/agents/ with a class inheriting BaseAgent
2. Import and register it here

The orchestrator uses this registry to route messages to the right agent.
"""

from api.agents.base import BaseAgent
from api.agents.controller_agent import ControllerAgent
from api.agents.analytics_agent import AnalyticsAgent
from api.agents.sales_agent import SalesAgent


# ── Registry ──────────────────────────────────────────

_AGENTS: dict[str, BaseAgent] = {}


def _register(agent: BaseAgent) -> None:
    _AGENTS[agent.name] = agent


# Register built-in agents
_register(ControllerAgent())
_register(AnalyticsAgent())
_register(SalesAgent())


# ── Public API ────────────────────────────────────────


def get_agent(name: str) -> BaseAgent | None:
    """Get agent by name."""
    return _AGENTS.get(name)


def list_agents() -> list[BaseAgent]:
    """List all registered agents."""
    return list(_AGENTS.values())


def route_to_agent(message: str, context: dict | None = None) -> BaseAgent:
    """Route a user message to the best-matching agent.

    Uses keyword matching as fallback. Returns the agent with highest score.
    Default: controller (most common use case for existing users).
    """
    best_agent: BaseAgent | None = None
    best_score = 0.0

    for agent in _AGENTS.values():
        score = agent.matches_intent(message)
        if score > best_score:
            best_score = score
            best_agent = agent

    # If deal context is present, bias toward sales agent
    if context and context.get("deal"):
        sales = _AGENTS.get("sales")
        if sales and best_score < 0.5:
            return sales

    # Default to controller if no clear match
    if best_agent is None or best_score < 0.1:
        return _AGENTS["controller"]

    return best_agent


def get_agent_for_tool(tool_name: str) -> str:
    """Given a tool name, return which agent owns it.

    This maintains backward compatibility with the existing TOOL_AGENT_MAP
    in graph.py while also supporting the new agent registry.
    """
    for agent in _AGENTS.values():
        if tool_name in agent.tool_names:
            return agent.name
    return "controller"  # fallback
