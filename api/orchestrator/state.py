"""Orchestrator state definition (US-A01)."""

from typing import TypedDict


class OrchestratorState(TypedDict):
    """State passed through the orchestrator graph nodes."""
    messages: list[dict]
    tenant_id: str
    user_id: str
    current_agent: str
    tool_results: list[dict]
    tool_calls: list[dict]
