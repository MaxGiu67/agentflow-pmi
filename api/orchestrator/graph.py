"""Orchestrator graph — routes messages, executes tools, generates responses (US-A01, US-A07, US-A08, US-A10).

Uses a simple custom approach:
- Router node: calls Claude API (or keyword fallback) to decide which tools to call
- Execute tools node: runs the selected tools and collects results
- Respond node: calls Claude API (or fallback) to generate a response from tool results

No LangGraph/LangChain tool binding — just direct httpx calls to Claude API.

Sprint 13 additions:
- US-A07: Multi-agent response — broad questions route to multiple tools
- US-A08: Conversation memory — preferences loaded into context, auto-detect & save
- US-A10: Skill discovery — help/aiuto queries return capabilities list
"""

import json
import logging
import os
import uuid

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from api.orchestrator.llm_adapter import LLMAdapter, LLM_PROVIDERS
from api.orchestrator.memory_node import MemoryManager
from api.orchestrator.prompts import ORCHESTRATOR_SYSTEM_PROMPT, RESPONSE_SYSTEM_PROMPT
from api.orchestrator.skill_discovery import get_skill_discovery_message
from api.orchestrator.state import OrchestratorState
from api.orchestrator.tool_registry import TOOLS, get_tools_by_name, get_tools_description

logger = logging.getLogger(__name__)


# ============================================================
# Tool → Agent mapping (US-A07)
# ============================================================

TOOL_AGENT_MAP: dict[str, str] = {
    "count_invoices": "fisco",
    "list_invoices": "fisco",
    "get_invoice_detail": "fisco",
    "get_dashboard_summary": "fisco",
    "get_deadlines": "fisco",
    "get_fiscal_alerts": "fisco",
    "get_journal_entries": "conta",
    "get_balance_sheet_summary": "conta",
    "predict_cashflow": "cashflow",
    "get_pending_review": "conta",
    "list_expenses": "conta",
    "list_assets": "conta",
    "get_ceo_kpi": "conta",
    "sync_cassetto": "fisco",
}


# ============================================================
# Keyword-based fallback router (for tests / no API key)
# ============================================================


def keyword_route(message: str) -> list[dict]:
    """Simple keyword-matching router for when Claude API is not available."""
    msg_lower = message.lower()

    # US-A10: Help / skill discovery (check first)
    help_keywords = ["cosa sai fare", "aiuto", "help", "cosa puoi", "come funziona", "cosa fai"]
    if any(k in msg_lower for k in help_keywords):
        return [{"tool": "direct_response", "args": {"message": get_skill_discovery_message()}}]

    # US-A07: Multi-agent detection — broad questions
    broad_keywords = ["come sta", "panoramica", "riepilogo", "situazione", "come vanno"]
    if any(k in msg_lower for k in broad_keywords):
        return [
            {"tool": "count_invoices", "args": {}},
            {"tool": "get_dashboard_summary", "args": {}},
            {"tool": "get_deadlines", "args": {}},
        ]

    if any(kw in msg_lower for kw in ["fattur", "invoice"]):
        if any(kw in msg_lower for kw in ["quant", "cont", "numer"]):
            return [{"tool": "count_invoices", "args": {}}]
        if any(kw in msg_lower for kw in ["elenc", "list", "mostr"]):
            return [{"tool": "list_invoices", "args": {}}]
        return [{"tool": "count_invoices", "args": {}}]

    if any(kw in msg_lower for kw in ["scadenz", "deadline"]):
        return [{"tool": "get_deadlines", "args": {}}]

    if any(kw in msg_lower for kw in ["dashboard"]):
        return [{"tool": "get_dashboard_summary", "args": {}}]

    if any(kw in msg_lower for kw in ["alert", "ritardo", "scadut"]):
        return [{"tool": "get_fiscal_alerts", "args": {}}]

    if any(kw in msg_lower for kw in ["prima nota", "registrazi", "journal"]):
        return [{"tool": "get_journal_entries", "args": {}}]

    if any(kw in msg_lower for kw in ["patrimonial", "bilancio", "balance"]):
        return [{"tool": "get_balance_sheet_summary", "args": {}}]

    if any(kw in msg_lower for kw in ["cash flow", "cashflow", "flusso di cassa", "previsione"]):
        return [{"tool": "predict_cashflow", "args": {}}]

    if any(kw in msg_lower for kw in ["revis", "verifica", "review", "pending"]):
        return [{"tool": "get_pending_review", "args": {}}]

    if any(kw in msg_lower for kw in ["spese", "nota spese", "expense"]):
        return [{"tool": "list_expenses", "args": {}}]

    if any(kw in msg_lower for kw in ["cespiti", "asset", "beni strumentali"]):
        return [{"tool": "list_assets", "args": {}}]

    if any(kw in msg_lower for kw in ["kpi", "ceo", "fatturato", "ebitda"]):
        return [{"tool": "get_ceo_kpi", "args": {}}]

    if any(kw in msg_lower for kw in ["cassetto", "sync", "sincronizz"]):
        return [{"tool": "sync_cassetto", "args": {}}]

    # Greetings / generic
    if any(kw in msg_lower for kw in ["ciao", "buongiorno", "salve", "hello", "hey"]):
        return [{"tool": "direct_response", "args": {"message": "Ciao! Come posso aiutarti con la contabilit\u00e0 oggi?"}}]

    return [{"tool": "direct_response", "args": {"message": "Non ho capito la richiesta. Puoi riprovare specificando meglio cosa ti serve?"}}]


def _has_api_key() -> bool:
    """Check whether a usable LLM API key is configured (Anthropic or OpenAI)."""
    provider = os.getenv("DEFAULT_LLM_PROVIDER", settings.default_llm_provider)
    provider_config = LLM_PROVIDERS.get(provider)
    if not provider_config:
        # Fallback: check Anthropic key
        key = settings.anthropic_api_key
        return bool(key and key.strip() and key != "")
    key = os.getenv(provider_config["api_key_env"], "")
    return bool(key and key.strip())


def _get_llm_settings() -> tuple[str, str]:
    """Return (provider, model) from env / config defaults."""
    provider = os.getenv("DEFAULT_LLM_PROVIDER", settings.default_llm_provider)
    model = os.getenv("DEFAULT_LLM_MODEL", settings.default_llm_model)
    return provider, model


# ============================================================
# LLM API helper (via LLMAdapter)
# ============================================================


async def _call_llm(system_prompt: str, user_message: str) -> str:
    """Call the configured LLM provider and return the text response."""
    provider, model = _get_llm_settings()
    return await LLMAdapter.call(
        provider=provider,
        model=model,
        system_prompt=system_prompt,
        user_message=user_message,
        max_tokens=1024,
    )


# ============================================================
# Graph node: Router
# ============================================================


async def router_node(state: OrchestratorState) -> OrchestratorState:
    """Analyze user message and decide which tool(s) to call.

    Uses Claude API when available, falls back to keyword matching otherwise.
    """
    # Get the latest user message
    user_messages = [m for m in state["messages"] if m.get("role") == "user"]
    if not user_messages:
        state["tool_calls"] = [
            {"tool": "direct_response", "args": {"message": "Non ho ricevuto un messaggio."}}
        ]
        return state

    latest_message = user_messages[-1]["content"]

    if _has_api_key():
        try:
            tools_desc = get_tools_description()
            system_prompt = ORCHESTRATOR_SYSTEM_PROMPT.format(tools_description=tools_desc)
            raw_response = await _call_llm(system_prompt, latest_message)

            # Parse JSON response
            # Claude might wrap in ```json ... ``` — strip that
            cleaned = raw_response.strip()
            if cleaned.startswith("```"):
                # Remove code fences
                lines = cleaned.split("\n")
                lines = [l for l in lines if not l.strip().startswith("```")]
                cleaned = "\n".join(lines).strip()

            tool_calls = json.loads(cleaned)
            if isinstance(tool_calls, list):
                state["tool_calls"] = tool_calls
            else:
                state["tool_calls"] = [tool_calls]

        except Exception as e:
            logger.warning("Claude API call failed in router, using keyword fallback: %s", e)
            state["tool_calls"] = keyword_route(latest_message)
    else:
        state["tool_calls"] = keyword_route(latest_message)

    return state


# ============================================================
# Graph node: Execute Tools
# ============================================================


async def execute_tools_node(
    state: OrchestratorState, db: AsyncSession
) -> OrchestratorState:
    """Execute the tools selected by the router."""
    tools_by_name = get_tools_by_name()
    results: list[dict] = []

    for call in state.get("tool_calls", []):
        tool_name = call.get("tool", "")
        args = call.get("args", {})

        if tool_name == "direct_response":
            results.append({
                "tool": "direct_response",
                "result": {"message": args.get("message", "")},
            })
            continue

        tool_def = tools_by_name.get(tool_name)
        if not tool_def:
            results.append({
                "tool": tool_name,
                "result": {"error": f"Tool '{tool_name}' non trovato"},
            })
            continue

        try:
            tenant_id = uuid.UUID(state["tenant_id"])
            handler = tool_def["handler"]
            result = await handler(db=db, tenant_id=tenant_id, **args)
            results.append({"tool": tool_name, "result": result})
        except Exception as e:
            logger.error("Tool %s failed: %s", tool_name, e)
            results.append({
                "tool": tool_name,
                "result": {"error": f"Errore nell'esecuzione di {tool_name}: {str(e)}"},
            })

    state["tool_results"] = results
    return state


# ============================================================
# Graph node: Respond
# ============================================================


async def respond_node(state: OrchestratorState) -> OrchestratorState:
    """Generate a natural language response from tool results.

    Uses Claude API when available, falls back to simple formatting otherwise.
    """
    tool_results = state.get("tool_results", [])

    # If it's a direct response, just pass it through
    if len(tool_results) == 1 and tool_results[0].get("tool") == "direct_response":
        response_text = tool_results[0]["result"].get("message", "")
        state["messages"].append({
            "role": "assistant",
            "content": response_text,
        })
        return state

    # Format tool results
    results_str = json.dumps(tool_results, ensure_ascii=False, indent=2, default=str)

    if _has_api_key():
        try:
            system_prompt = RESPONSE_SYSTEM_PROMPT.format(tool_results=results_str)
            user_messages = [m for m in state["messages"] if m.get("role") == "user"]
            user_msg = user_messages[-1]["content"] if user_messages else ""
            response_text = await _call_llm(system_prompt, user_msg)
        except Exception as e:
            logger.warning("Claude API call failed in respond, using fallback: %s", e)
            response_text = _format_results_fallback(tool_results)
    else:
        response_text = _format_results_fallback(tool_results)

    state["messages"].append({
        "role": "assistant",
        "content": response_text,
    })
    return state


def _format_results_fallback(tool_results: list[dict]) -> str:
    """Format tool results into a simple text response without LLM.

    US-A07: When multiple tools are present, prepend agent badges.
    """
    is_multi = len(tool_results) > 1
    parts: list[str] = []

    for tr in tool_results:
        tool_name = tr.get("tool", "unknown")
        result = tr.get("result", {})

        # US-A07: Agent badge prefix for multi-tool responses
        agent_badge = ""
        if is_multi:
            agent_type = TOOL_AGENT_MAP.get(tool_name, "orchestrator")
            agent_badge = f"[{agent_type}] "

        if "error" in result:
            parts.append(f"{agent_badge}Errore ({tool_name}): {result['error']}")
            continue

        if "message" in result:
            parts.append(f"{agent_badge}{result['message']}")

        if "count" in result and "items" not in result and "message" not in result:
            parts.append(f"{agent_badge}{result['count']} risultati trovati.")

        if "items" in result:
            parts.append(f"{agent_badge}Trovati {len(result['items'])} risultati:")
            for item in result["items"][:5]:
                # Format item as key-value pairs
                formatted = ", ".join(
                    f"{k}: {v}" for k, v in item.items()
                    if v is not None and k != "id"
                )
                parts.append(f"  - {formatted}")
            if len(result["items"]) > 5:
                parts.append(f"  ... e altri {len(result['items']) - 5}")

        if "counters" in result:
            parts.append(f"{agent_badge}Totale: {result['counters'].get('total', 0)} fatture")
            for k, v in result["counters"].items():
                if k != "total":
                    parts.append(f"  {k}: {v}")

        # Handle KPI-specific fields
        if "fatturato_ytd" in result:
            parts.append(f"{agent_badge}Fatturato YTD: \u20ac{result['fatturato_ytd']:,.2f}")
            parts.append(f"Costi YTD: \u20ac{result.get('costi_ytd', 0):,.2f}")
            parts.append(f"EBITDA: \u20ac{result.get('ebitda', 0):,.2f}")

        # Handle balance sheet
        if "total_debit" in result and "total_credit" in result and "balanced" in result:
            parts.append(f"{agent_badge}Totale dare: \u20ac{result['total_debit']:,.2f}")
            parts.append(f"Totale avere: \u20ac{result['total_credit']:,.2f}")
            balanced_text = "S\u00ec" if result["balanced"] else "No"
            parts.append(f"Bilanciato: {balanced_text}")

    if not parts:
        return "Operazione completata."

    return "\n".join(parts)


# ============================================================
# Main orchestrator entry point
# ============================================================


async def run_orchestrator(
    user_message: str,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession,
    conversation_messages: list[dict] | None = None,
) -> dict:
    """Run the full orchestrator pipeline: route -> execute -> respond.

    Args:
        user_message: The user's input message.
        tenant_id: Tenant UUID.
        user_id: User UUID.
        db: Async database session.
        conversation_messages: Previous messages for context (optional).

    Returns:
        dict with keys: content, tool_calls, tool_results, agent_name, agent_type
    """
    # US-A08: Memory — load context and detect preferences
    memory_mgr = MemoryManager(db)
    memory_context = await memory_mgr.get_memory_context(tenant_id, user_id)
    await memory_mgr.detect_and_save(user_message, tenant_id, user_id)

    # Build initial state
    messages = []
    if conversation_messages:
        messages.extend(conversation_messages)
    # Inject memory context if present (as a system-style context message)
    if memory_context:
        messages.append({"role": "system", "content": memory_context})
    messages.append({"role": "user", "content": user_message})

    state: OrchestratorState = {
        "messages": messages,
        "tenant_id": str(tenant_id),
        "user_id": str(user_id),
        "current_agent": "orchestrator",
        "tool_results": [],
        "tool_calls": [],
    }

    # Step 1: Router — decide which tools to call
    state = await router_node(state)

    # Step 2: Execute tools
    state = await execute_tools_node(state, db)

    # Step 3: Generate response
    state = await respond_node(state)

    # Extract the assistant response (last assistant message)
    assistant_messages = [m for m in state["messages"] if m.get("role") == "assistant"]
    content = assistant_messages[-1]["content"] if assistant_messages else "Operazione completata."

    # Determine agent info (US-A07: multi-agent aware)
    agent_name = "orchestrator"
    agent_type = "orchestrator"
    tool_calls_list = state.get("tool_calls", [])
    if tool_calls_list:
        first_tool = tool_calls_list[0].get("tool", "")
        if first_tool != "direct_response":
            agent_name = first_tool
        # Multi-agent: set agent_type to "multi" when multiple non-direct tools used
        non_direct_tools = [tc for tc in tool_calls_list if tc.get("tool") != "direct_response"]
        if len(non_direct_tools) > 1:
            agent_type = "multi"

    return {
        "content": content,
        "tool_calls": state.get("tool_calls"),
        "tool_results": state.get("tool_results"),
        "agent_name": agent_name,
        "agent_type": agent_type,
    }
