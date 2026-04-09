"""Base agent class — all agents inherit from this (ADR-010, US-211).

An agent has:
- name: unique identifier
- description: what the agent does (used by router)
- tool_names: list of tool names from tool_registry this agent can use
- keywords: words that trigger routing to this agent
- get_system_prompt(): returns the system prompt for LLM calls
"""

from __future__ import annotations



class BaseAgent:
    """Base class for all AgentFlow agents."""

    name: str = ""
    description: str = ""
    tool_names: list[str] = []
    keywords: list[str] = []

    def get_system_prompt(self, context: dict | None = None) -> str:
        """Return system prompt for this agent. Override in subclasses."""
        return f"Sei l'agente {self.name} di AgentFlow PMI."

    def get_tool_names(self, context: dict | None = None) -> list[str]:
        """Return tool names available for this agent.

        Subclasses can override to filter tools based on context
        (e.g., Sales Agent filters by product/pipeline).
        """
        return self.tool_names

    def matches_intent(self, message: str) -> float:
        """Return a score 0-1 indicating how well this agent matches the user message.

        Higher score = better match. Used by router for keyword fallback.
        """
        msg_lower = message.lower()
        hits = sum(1 for kw in self.keywords if kw in msg_lower)
        if not self.keywords:
            return 0.0
        return min(hits / max(len(self.keywords) * 0.3, 1), 1.0)
