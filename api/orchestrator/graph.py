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
    "get_period_stats": "conta",
    "get_top_clients": "fisco",
    "sync_cassetto": "fisco",
}


# ============================================================
# Keyword-based fallback router (for tests / no API key)
# ============================================================


MONTH_NAMES = {
    "gennaio": 1, "febbraio": 2, "marzo": 3, "aprile": 4,
    "maggio": 5, "giugno": 6, "luglio": 7, "agosto": 8,
    "settembre": 9, "ottobre": 10, "novembre": 11, "dicembre": 12,
    "gen": 1, "feb": 2, "mar": 3, "apr": 4, "mag": 5, "giu": 6,
    "lug": 7, "ago": 8, "set": 9, "ott": 10, "nov": 11, "dic": 12,
}

QUARTER_NAMES = {
    "q1": (1, 3), "q2": (4, 6), "q3": (7, 9), "q4": (10, 12),
    "1 trimestre": (1, 3), "2 trimestre": (4, 6),
    "3 trimestre": (7, 9), "4 trimestre": (10, 12),
    "primo trimestre": (1, 3), "secondo trimestre": (4, 6),
    "terzo trimestre": (7, 9), "quarto trimestre": (10, 12),
}


def _extract_time_params(message: str) -> dict:
    """Extract year, month, quarter from user message."""
    import re
    msg_lower = message.lower()
    params: dict = {}

    # Extract year (2020-2030)
    year_match = re.search(r'\b(20[2-3]\d)\b', message)
    if year_match:
        params["year"] = int(year_match.group(1))

    # Extract quarter
    for q_name, (m_start, m_end) in QUARTER_NAMES.items():
        if q_name in msg_lower:
            params["month_start"] = m_start
            params["month_end"] = m_end
            params["quarter"] = q_name
            break

    # Extract month (if no quarter found)
    if "month_start" not in params:
        for m_name, m_num in MONTH_NAMES.items():
            if m_name in msg_lower:
                params["month"] = f"{params.get('year', 2024)}-{m_num:02d}"
                params["month_num"] = m_num
                break

    return params


def keyword_route(message: str) -> list[dict]:
    """Smart keyword-matching router with time extraction."""
    msg_lower = message.lower()
    time_params = _extract_time_params(message)

    # US-A10: Help / skill discovery (check first)
    help_keywords = ["cosa sai fare", "aiuto", "help", "cosa puoi", "come funziona", "cosa fai"]
    if any(k in msg_lower for k in help_keywords):
        return [{"tool": "direct_response", "args": {"message": get_skill_discovery_message()}}]

    # US-A07: Multi-agent detection — broad questions
    broad_keywords = ["come sta", "panoramica", "riepilogo", "situazione", "come vanno"]
    if any(k in msg_lower for k in broad_keywords):
        args: dict = {}
        if time_params.get("year"):
            args["year"] = time_params["year"]
        return [
            {"tool": "get_ceo_kpi", "args": {**args}},
            {"tool": "get_dashboard_summary", "args": {}},
            {"tool": "get_deadlines", "args": {}},
        ]

    # Period-specific KPI requests (ebitda Q1, fatturato gennaio, etc.)
    if any(kw in msg_lower for kw in ["kpi", "ceo", "fatturato", "ebitda", "margine", "ricav", "cost"]):
        args = {}
        if time_params.get("year"):
            args["year"] = time_params["year"]
        if time_params.get("month_start"):
            args["month_start"] = time_params["month_start"]
            args["month_end"] = time_params["month_end"]
        elif time_params.get("month_num"):
            args["month_start"] = time_params["month_num"]
            args["month_end"] = time_params["month_num"]
        return [{"tool": "get_period_stats", "args": args}]

    # Top clients/suppliers
    if any(kw in msg_lower for kw in ["top client", "top fornit", "classifica client", "classifica fornit", "migliori client"]):
        args = {}
        if time_params.get("year"):
            args["year"] = time_params["year"]
        if any(kw in msg_lower for kw in ["fornit"]):
            args["type"] = "passiva"
        else:
            args["type"] = "attiva"
        # Extract limit
        import re as _re
        limit_match = _re.search(r'\btop\s+(\d+)', msg_lower)
        if limit_match:
            args["limit"] = int(limit_match.group(1))
        return [{"tool": "get_top_clients", "args": args}]

    # Invoice queries with time params
    if any(kw in msg_lower for kw in ["fattur", "invoice"]):
        args = {}
        if time_params.get("year"):
            args["year"] = time_params["year"]
        if time_params.get("month"):
            args["month"] = time_params["month"]
        if any(kw in msg_lower for kw in ["quant", "cont", "numer"]):
            return [{"tool": "count_invoices", "args": args}]
        if any(kw in msg_lower for kw in ["elenc", "list", "mostr"]):
            return [{"tool": "list_invoices", "args": args}]
        return [{"tool": "count_invoices", "args": args}]

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
    """Format tool results into a smart text response without LLM.

    US-A07: When multiple tools are present, prepend agent badges.
    Smart response logic:
    - Single value (count, total) -> short text
    - List <= 5 items -> markdown table
    - List > 5 items -> summary with link suggestion
    - Dashboard query -> suggest adding widget
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

        # Smart formatting: single value results (count, totals)
        if "count" in result and "items" not in result:
            if "message" in result:
                parts.append(f"{agent_badge}{result['message']}")
            else:
                parts.append(f"{agent_badge}{result['count']} risultati trovati.")
            continue

        # Smart formatting: list results
        if "items" in result:
            items = result["items"]
            count = len(items)

            if count == 0:
                if "message" in result:
                    parts.append(f"{agent_badge}{result['message']}")
                else:
                    parts.append(f"{agent_badge}Nessun risultato trovato.")
            elif count <= 5:
                # Markdown table for small result sets
                if items:
                    # Build table header from keys (excluding id)
                    headers = [k for k in items[0].keys() if k != "id" and items[0][k] is not None]
                    if headers:
                        header_line = " | ".join(h.replace("_", " ").title() for h in headers)
                        separator = " | ".join("---" for _ in headers)
                        parts.append(f"{agent_badge}Trovati {count} risultati:")
                        parts.append(f"| {header_line} |")
                        parts.append(f"| {separator} |")
                        for item in items:
                            row = " | ".join(str(item.get(h, "")) for h in headers)
                            parts.append(f"| {row} |")
                    else:
                        parts.append(f"{agent_badge}Trovati {count} risultati.")
            else:
                # Summary with link suggestion for large result sets
                parts.append(f"{agent_badge}Ho trovato {count} risultati.")
                # Show first 3 as preview
                for item in items[:3]:
                    formatted = ", ".join(
                        f"{k}: {v}" for k, v in item.items()
                        if v is not None and k != "id"
                    )
                    parts.append(f"  - {formatted}")
                parts.append(f"  ... e altri {count - 3}")
                parts.append("Consulta la pagina dedicata per la lista completa.")
            continue

        # Handle message-only results
        if "message" in result:
            parts.append(f"{agent_badge}{result['message']}")

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


def _format_smart_response(tool_results: list[dict]) -> dict:
    """Decide how to format the response based on data quantity."""

    total_records = 0
    for tr in tool_results:
        result = tr.get("result", {})
        if isinstance(result, list):
            total_records += len(result)
        elif isinstance(result, dict):
            # Check if it contains a list (e.g., items, invoices)
            for v in result.values():
                if isinstance(v, list):
                    total_records += len(v)

    response_type = "text"  # default
    if total_records == 0:
        response_type = "text"  # simple text answer
    elif total_records <= 5:
        response_type = "table"  # show inline table in chat
    elif total_records > 5:
        response_type = "link"  # suggest link to filtered page

    return {"response_type": response_type, "record_count": total_records}


# ============================================================
# Action Commands — chatbot controls the UI
# ============================================================

# Map tool names to relevant frontend pages
TOOL_PAGE_MAP: dict[str, str] = {
    "count_invoices": "/fatture",
    "list_invoices": "/fatture",
    "get_invoice_detail": "/fatture",
    "get_dashboard_summary": "/dashboard",
    "get_deadlines": "/scadenze",
    "get_fiscal_alerts": "/scadenze",
    "get_journal_entries": "/contabilita",
    "get_balance_sheet_summary": "/contabilita/bilancio",
    "predict_cashflow": "/banca/cashflow",
    "get_pending_review": "/fatture/verifica",
    "list_expenses": "/spese",
    "list_assets": "/cespiti",
    "get_ceo_kpi": "/ceo",
    "get_period_stats": "/dashboard",
    "get_top_clients": "/dashboard",
    "sync_cassetto": "/impostazioni",
}


def _build_actions(
    tool_calls: list[dict],
    tool_results: list[dict],
    context: dict | None,
    user_message: str,
) -> tuple[list[dict], list[dict]]:
    """Build action commands for the frontend based on tool results and context.

    Returns:
        (actions, suggested_actions) — actions are auto-executed, suggested are buttons.
    """
    actions: list[dict] = []
    suggested_actions: list[dict] = []

    if not context:
        return actions, suggested_actions

    current_page = context.get("page", "dashboard")
    current_year = context.get("year")
    msg_lower = user_message.lower()

    # --- Detect year intent from message ---
    requested_year = None
    import re
    year_match = re.search(r'\b(20[1-3]\d)\b', user_message)
    if year_match:
        requested_year = int(year_match.group(1))

    # Action: set_year if user asks for a different year
    if requested_year and current_year and int(current_year) != requested_year:
        actions.append({
            "type": "set_year",
            "value": requested_year,
            "mode": "auto",
            "label": f"Dashboard impostata su {requested_year}",
        })

    # --- Detect navigation intent ---
    # Explicit navigation keywords
    nav_keywords = {
        "fatture": "/fatture",
        "scadenze": "/scadenze",
        "contabilit": "/contabilita",
        "dashboard": "/dashboard",
        "ceo": "/ceo",
        "spese": "/spese",
        "cespiti": "/cespiti",
        "banca": "/banca",
        "impostazioni": "/impostazioni",
    }

    # Check for explicit "vai a", "mostrami", "apri"
    explicit_nav = any(kw in msg_lower for kw in ["vai a", "vai alle", "apri", "mostrami la pagina", "portami"])
    if explicit_nav:
        for keyword, path in nav_keywords.items():
            if keyword in msg_lower and f"/{current_page}" != path:
                actions.append({
                    "type": "navigate",
                    "path": path,
                    "mode": "auto",
                    "label": f"Navigato a {path.strip('/')}",
                })
                break

    # --- Suggest navigation for large result sets ---
    for tr in tool_results:
        tool_name = tr.get("tool", "")
        result = tr.get("result", {})

        if isinstance(result, dict) and "items" in result:
            items = result["items"]
            count = len(items)

            if count > 5:
                target_page = TOOL_PAGE_MAP.get(tool_name, "")
                if target_page and f"/{current_page}" != target_page:
                    # Build query params from tool args
                    tool_call = next((tc for tc in tool_calls if tc.get("tool") == tool_name), None)
                    query_params = ""
                    if tool_call:
                        args = tool_call.get("args", {})
                        params = []
                        if args.get("query"):
                            params.append(f"emittente={args['query']}")
                        if args.get("type"):
                            params.append(f"type={args['type']}")
                        if args.get("year"):
                            params.append(f"year={args['year']}")
                        if params:
                            query_params = "?" + "&".join(params)

                    suggested_actions.append({
                        "type": "navigate",
                        "path": f"{target_page}{query_params}",
                        "mode": "suggest",
                        "label": f"Vedi tutti i {count} risultati",
                    })

    # --- Suggest filter for specific search queries ---
    for tc in tool_calls:
        args = tc.get("args", {})
        query = args.get("query")
        inv_type = args.get("type")
        if query and inv_type:
            target = TOOL_PAGE_MAP.get(tc.get("tool", ""), "/fatture")
            suggested_actions.append({
                "type": "set_filter",
                "filters": {"emittente": query, "type": inv_type},
                "path": target,
                "mode": "suggest",
                "label": f"Filtra per {query} ({inv_type})",
            })

    return actions, suggested_actions


async def run_orchestrator(
    user_message: str,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession,
    conversation_messages: list[dict] | None = None,
    context: dict | None = None,
) -> dict:
    """Run the full orchestrator pipeline: route -> execute -> respond.

    Args:
        user_message: The user's input message.
        tenant_id: Tenant UUID.
        user_id: User UUID.
        db: Async database session.
        conversation_messages: Previous messages for context (optional).
        context: User context dict with page, year, etc. (optional).

    Returns:
        dict with keys: content, tool_calls, tool_results, agent_name, agent_type, response_meta
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

    # Inject user context (Level 2 Context Engineering)
    if context:
        page = context.get("page", "dashboard")
        year = context.get("year", "")
        context_msg = (
            f"CONTESTO UTENTE:\n"
            f"- Pagina corrente: {page}\n"
            f"- Anno selezionato: {year}\n\n"
            f"Usa queste informazioni per filtrare i dati. Se l'utente è sulla dashboard {year}, "
            f"le domande sulle fatture si riferiscono al {year}."
        )
        messages.append({"role": "system", "content": context_msg})

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
    # For keyword fallback, inject year from context into tool args
    state = await router_node(state)

    # Inject context year into tool args for ALL paths (LLM + keyword fallback)
    if context:
        ctx_year = context.get("year")
        if ctx_year is not None:
            year_tools = (
                "count_invoices", "list_invoices", "get_ceo_kpi",
                "get_period_stats", "get_top_clients",
            )
            for call in state.get("tool_calls", []):
                tool_name = call.get("tool", "")
                if tool_name in year_tools:
                    call.setdefault("args", {})
                    if "year" not in call["args"]:
                        call["args"]["year"] = ctx_year

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

    # Smart response meta (Improvement 4)
    response_meta = _format_smart_response(state.get("tool_results", []))

    # Content Blocks — extract rich content from tool results
    content_blocks = []
    for tr in state.get("tool_results", []):
        result = tr.get("result", {})
        if isinstance(result, dict) and "content_blocks" in result:
            content_blocks.extend(result["content_blocks"])
    if content_blocks:
        response_meta["content_blocks"] = content_blocks

    # Action Commands — build UI actions from context + results
    auto_actions, suggested = _build_actions(
        tool_calls=state.get("tool_calls", []),
        tool_results=state.get("tool_results", []),
        context=context,
        user_message=user_message,
    )
    if auto_actions:
        response_meta["actions"] = auto_actions
    if suggested:
        response_meta["suggested_actions"] = suggested

    return {
        "content": content,
        "tool_calls": state.get("tool_calls"),
        "tool_results": state.get("tool_results"),
        "agent_name": agent_name,
        "agent_type": agent_type,
        "response_meta": response_meta,
    }
