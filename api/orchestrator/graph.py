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

from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from api.orchestrator.llm_adapter import LLMAdapter, LLM_PROVIDERS
from api.orchestrator.memory_node import MemoryManager
from api.orchestrator.prompts import ORCHESTRATOR_SYSTEM_PROMPT, RESPONSE_SYSTEM_PROMPT
from api.orchestrator.skill_discovery import get_skill_discovery_message
from api.orchestrator.state import OrchestratorState
from api.orchestrator.tool_registry import get_tools_by_name, get_tools_description
from api.agents.registry import get_agent_for_tool

logger = logging.getLogger(__name__)


# ============================================================
# Tool → Agent mapping (US-A07, updated ADR-010)
# Uses agent registry as source of truth, with fallback map for backward compat.
# ============================================================

TOOL_AGENT_MAP: dict[str, str] = {
    "count_invoices": "controller",
    "list_invoices": "controller",
    "get_invoice_detail": "controller",
    "get_dashboard_summary": "controller",
    "get_deadlines": "controller",
    "get_fiscal_alerts": "controller",
    "get_journal_entries": "controller",
    "get_balance_sheet_summary": "controller",
    "get_pending_review": "controller",
    "list_expenses": "controller",
    "list_assets": "controller",
    "get_ceo_kpi": "controller",
    "get_period_stats": "controller",
    "get_top_clients": "controller",
    "sync_cassetto": "controller",
    "apertura_conti": "controller",
    "crea_budget": "controller",
    "predict_cashflow": "analytics",
    "crm_pipeline_summary": "sales",
    "crm_list_deals": "sales",
    "crm_list_contacts": "sales",
    "crm_won_deals": "sales",
    "crm_pending_orders": "sales",
}


def _get_agent_for_tool(tool_name: str) -> str:
    """Get agent name for a tool — registry first, then fallback map."""
    if tool_name in TOOL_AGENT_MAP:
        return TOOL_AGENT_MAP[tool_name]
    return get_agent_for_tool(tool_name)


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


def _page_based_route(page: str, message: str) -> list[dict] | None:
    """Route based on page context BEFORE keyword matching.

    Returns tool calls if the page context provides a clear routing signal,
    or None to fall through to keyword matching.

    Priority routing:
    - CRM pages → Sales Agent (pipeline summary + deal list)
    - Fatture/contabilita pages → Accounting tools
    - Fisco/scadenze pages → Fiscal tools
    - Dashboard/CEO pages → Controller/KPI tools
    """
    if not page:
        return None

    page_lower = page.lower().strip("/")
    msg_lower = message.lower()

    # Don't intercept greetings or help requests — let their handlers deal with them
    greetings = ["ciao", "buongiorno", "buonasera", "salve", "hello", "hey", "grazie"]
    if any(msg_lower.strip() == g or msg_lower.strip().startswith(g + " ") or msg_lower.strip().startswith(g + "!") for g in greetings):
        return None
    help_keywords = ["cosa sai fare", "aiuto", "help", "cosa puoi", "come funziona", "cosa fai"]
    if any(k in msg_lower for k in help_keywords):
        return None

    # CRM pages → route to Sales Agent tools
    if page_lower.startswith("crm") or page_lower.startswith("pipeline") or page_lower.startswith("deal"):
        # If the message has specific CRM keywords, let keyword_route handle it
        # (it already has good CRM matching for "deal vinti", "ordini pendenti", etc.)
        specific_crm_kw = [
            "deal vint", "deal chius", "contratti vint", "ordini in attesa",
            "ordini da confermare", "contatti crm", "clienti crm",
        ]
        if any(k in msg_lower for k in specific_crm_kw):
            return None  # fall through to keyword matching

        # For generic/ambiguous messages on CRM pages, route to pipeline + deals
        return [
            {"tool": "crm_pipeline_summary", "args": {}},
            {"tool": "crm_list_deals", "args": {}},
        ]

    # Fatture/contabilita pages
    if page_lower.startswith("fattur") or page_lower.startswith("contabilit"):
        # Only route if message is generic (no specific keywords already handled)
        generic_kw = [
            "come posso", "continuare", "cosa devo", "situazione",
            "cosa fare", "prossimi passi", "aiutami", "aiuto",
            "come va", "come stiam",
        ]
        if any(k in msg_lower for k in generic_kw):
            if page_lower.startswith("fattur"):
                return [{"tool": "list_invoices", "args": {}}, {"tool": "get_pending_review", "args": {}}]
            else:
                return [{"tool": "get_journal_entries", "args": {}}, {"tool": "get_balance_sheet_summary", "args": {}}]
        return None

    # Fisco/scadenze pages
    if page_lower.startswith("fisco") or page_lower.startswith("scadenz"):
        generic_kw = [
            "come posso", "continuare", "cosa devo", "situazione",
            "cosa fare", "prossimi passi", "aiutami", "aiuto",
            "come va", "come stiam",
        ]
        if any(k in msg_lower for k in generic_kw):
            return [{"tool": "get_deadlines", "args": {}}, {"tool": "get_fiscal_alerts", "args": {}}]
        return None

    # Dashboard/CEO pages
    if page_lower.startswith("dashboard") or page_lower.startswith("ceo"):
        generic_kw = [
            "come posso", "continuare", "cosa devo", "situazione",
            "cosa fare", "prossimi passi", "aiutami", "aiuto",
            "come va", "come stiam",
        ]
        if any(k in msg_lower for k in generic_kw):
            return [
                {"tool": "get_period_stats", "args": {}},
                {"tool": "get_deadlines", "args": {}},
            ]
        return None

    return None


def keyword_route(message: str, context: dict | None = None) -> list[dict]:
    """Smart keyword-matching router with time extraction and page context.

    If context.page is provided, tries page-based routing first for
    generic/ambiguous messages. Falls through to keyword matching for
    specific queries.
    """
    import re as _re
    msg_lower = message.lower()
    time_params = _extract_time_params(message)

    # --- Page-based routing (priority for generic messages) ---
    if context and context.get("page"):
        page_route = _page_based_route(context["page"], message)
        if page_route is not None:
            return page_route

    # --- Helper: extract search query from message (strips known keywords) ---
    def _extract_query(msg: str) -> str | None:
        """Remove known keywords/time refs and return remaining text as search query."""
        noise = [
            "fatture", "fattura", "invoice", "invoices", "emesse", "emessa",
            "ricevute", "ricevuta", "elenco", "lista", "mostrami", "mostra",
            "quante", "quanti", "numero", "cerca", "di", "del", "per", "il",
            "la", "le", "lo", "un", "una", "nel", "nel", "da", "a",
        ]
        tokens = msg.lower().split()
        # Remove known words, time refs, numbers
        filtered = [
            t for t in tokens
            if t not in noise
            and not _re.match(r'^20\d{2}$', t)
            and t not in MONTH_NAMES
        ]
        query = " ".join(filtered).strip()
        return query if len(query) >= 2 else None

    # --- Type mapping ---
    inv_type = None
    if any(kw in msg_lower for kw in ["emess", "attiv"]):
        inv_type = "attiva"
    elif any(kw in msg_lower for kw in ["ricevut", "passiv"]):
        inv_type = "passiva"

    # US-A10: Help / skill discovery (check first)
    help_keywords = ["cosa sai fare", "aiuto", "help", "cosa puoi", "come funziona", "cosa fai"]
    if any(k in msg_lower for k in help_keywords):
        return [{"tool": "direct_response", "args": {"message": get_skill_discovery_message()}}]

    # Guided tools: apertura_conti (bilancio import)
    bilancio_guide_keywords = [
        "importa bilancio", "importare bilancio", "importare i saldi",
        "saldi iniziali", "saldi di apertura", "apertura conti",
        "saldi del bilancio", "aiutami a importare i saldi",
        "importa i saldi", "configura bilancio", "inserire i saldi",
        "inserisco i saldi",
    ]
    if any(k in msg_lower for k in bilancio_guide_keywords):
        args: dict = {}
        if "pdf" in msg_lower:
            args["formato"] = "pdf"
        elif "csv" in msg_lower or "excel" in msg_lower:
            args["formato"] = "csv"
        elif any(k in msg_lower for k in ["mano", "manual", "voce", "wizard"]):
            args["formato"] = "manuale"
        return [{"tool": "apertura_conti", "args": args}]

    # Guided tools: crea_budget
    budget_guide_keywords = [
        "crea budget", "creare budget", "creare il budget",
        "piano economico", "budget annuale", "configura budget",
        "aiutami con il budget", "aiutami a creare il budget",
        "costruiamo il budget", "imposta budget",
    ]
    if any(k in msg_lower for k in budget_guide_keywords):
        args = {}
        if time_params.get("year"):
            args["year"] = time_params["year"]
        return [{"tool": "crea_budget", "args": args}]

    # CRM / Pipeline keywords
    crm_pipeline_keywords = [
        "pipeline", "deal", "opportunit", "prospect", "commerciale",
        "pipeline crm", "stato pipeline", "quanti deal", "nuovi deal",
        "offerte in corso", "trattative",
    ]
    if any(k in msg_lower for k in crm_pipeline_keywords):
        return [{"tool": "crm_pipeline_summary", "args": {}}]

    crm_contacts_keywords = [
        "contatti crm", "clienti crm", "anagrafica crm", "contatti odoo",
        "clienti odoo", "lista clienti crm",
    ]
    if any(k in msg_lower for k in crm_contacts_keywords):
        args = {}
        query = _extract_query(msg_lower)
        if query:
            args["search"] = query
        return [{"tool": "crm_list_contacts", "args": args}]

    crm_won_keywords = [
        "deal vint", "deal chius", "contratti vint", "contratti chius",
        "vinto", "deal won",
    ]
    if any(k in msg_lower for k in crm_won_keywords):
        return [{"tool": "crm_won_deals", "args": {}}]

    crm_orders_keywords = [
        "ordini in attesa", "ordini da confermare", "ordini pendenti",
        "ordine ricevuto", "ordini ricevuti", "po ricevut",
        "conferma ordine", "confermare ordini",
    ]
    if any(k in msg_lower for k in crm_orders_keywords):
        return [{"tool": "crm_pending_orders", "args": {}}]

    # US-A07: Multi-agent detection — broad questions
    broad_keywords = [
        "come sta", "come va", "come stiamo", "panoramica", "riepilogo",
        "situazione", "come vanno", "stato azien", "stato dell",
    ]
    if any(k in msg_lower for k in broad_keywords):
        args: dict = {}
        if time_params.get("year"):
            args["year"] = time_params["year"]
        return [
            {"tool": "get_period_stats", "args": {**args}},
            {"tool": "get_deadlines", "args": {}},
        ]

    # Top clients/suppliers — BEFORE KPI (so "classifica clienti per fatturato" doesn't match "fatturato")
    top_keywords = [
        "top client", "top fornit", "classifica client", "classifica fornit",
        "migliori client", "miglior client", "migliore client",
        "principal client", "principali client", "principale client",
        "miglior fornit", "migliore fornit", "migliori fornit",
        "principal fornit", "principali fornit", "principale fornit",
    ]
    has_top_regex = bool(_re.search(r'\btop\s+\d*\s*client', msg_lower)) or \
                    bool(_re.search(r'\btop\s+\d*\s*fornit', msg_lower))
    if any(kw in msg_lower for kw in top_keywords) or has_top_regex:
        args = {}
        if time_params.get("year"):
            args["year"] = time_params["year"]
        if any(kw in msg_lower for kw in ["fornit"]):
            args["type"] = "passiva"
        else:
            args["type"] = "attiva"
        limit_match = _re.search(r'\btop\s+(\d+)', msg_lower)
        if limit_match:
            args["limit"] = int(limit_match.group(1))
        return [{"tool": "get_top_clients", "args": args}]

    # Period-specific KPI requests
    kpi_keywords = [
        "kpi", "ceo", "fatturato", "ebitda", "margine", "ricav", "cost",
        "guadagn", "utile", "profit", "entrat", "uscit",
    ]
    if any(kw in msg_lower for kw in kpi_keywords):
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

    # Pending review / verification — BEFORE generic invoice queries
    if any(kw in msg_lower for kw in ["da verificare", "da revisionare", "attesa di revision", "pending review"]):
        return [{"tool": "get_pending_review", "args": {}}]

    # Cassetto fiscale — BEFORE cespiti (both start with "c")
    if any(kw in msg_lower for kw in ["cassetto", "sync", "sincronizz"]):
        return [{"tool": "sync_cassetto", "args": {}}]

    # Dashboard summary — BEFORE generic invoice queries
    if any(kw in msg_lower for kw in ["dashboard"]):
        return [{"tool": "get_dashboard_summary", "args": {}}]

    # Bug 7: Invoice detail by number — "fattura numero X", "fattura n. X", "fattura #X"
    detail_match = _re.search(r'fattura\s+(?:numero|n\.?|#)\s*(.+)', msg_lower)
    if detail_match:
        invoice_ref = detail_match.group(1).strip()
        return [{"tool": "get_invoice_detail", "args": {"invoice_id": invoice_ref}}]

    # Invoice queries with time params + query extraction (Bug 2+3)
    if any(kw in msg_lower for kw in ["fattur", "invoice"]):
        args = {}
        if time_params.get("year"):
            args["year"] = time_params["year"]
        if time_params.get("month"):
            args["month"] = time_params["month"]
        if inv_type:
            args["type"] = inv_type
        # Bug 2: extract search query (e.g. "fatture NTT Data" → query="NTT Data")
        search_query = _extract_query(message)
        if search_query:
            args["query"] = search_query
        if any(kw in msg_lower for kw in ["quant", "cont"]):
            return [{"tool": "count_invoices", "args": args}]
        if any(kw in msg_lower for kw in ["elenc", "list", "mostr"]):
            return [{"tool": "list_invoices", "args": args}]
        # Default: if there's a search query, list; otherwise count
        if search_query:
            return [{"tool": "list_invoices", "args": args}]
        return [{"tool": "count_invoices", "args": args}]

    # Alerts/overdue BEFORE generic deadlines (so "scadenze in ritardo" goes to alerts)
    if any(kw in msg_lower for kw in ["alert", "ritardo", "scadut", "overdue"]):
        return [{"tool": "get_fiscal_alerts", "args": {}}]

    if any(kw in msg_lower for kw in ["scadenz", "deadline"]):
        return [{"tool": "get_deadlines", "args": {}}]

    if any(kw in msg_lower for kw in ["prima nota", "registrazi", "journal"]):
        return [{"tool": "get_journal_entries", "args": {}}]

    if any(kw in msg_lower for kw in ["patrimonial", "bilancio", "balance"]):
        # If user is asking to import/configure bilancio, use guided tool instead
        if any(kw in msg_lower for kw in ["import", "saldi", "apertura", "configur", "inserir"]):
            return [{"tool": "apertura_conti", "args": {}}]
        return [{"tool": "get_balance_sheet_summary", "args": {}}]

    if any(kw in msg_lower for kw in ["cash flow", "cashflow", "flusso di cassa", "previsione"]):
        return [{"tool": "predict_cashflow", "args": {}}]

    if any(kw in msg_lower for kw in ["revis", "verifica", "review", "pending"]):
        return [{"tool": "get_pending_review", "args": {}}]

    if any(kw in msg_lower for kw in ["spese", "nota spese", "expense"]):
        return [{"tool": "list_expenses", "args": {}}]

    if any(kw in msg_lower for kw in ["cespiti", "asset", "beni strumentali"]):
        return [{"tool": "list_assets", "args": {}}]

    # Budget — generic keyword catch (after specific budget_guide_keywords above)
    if any(kw in msg_lower for kw in ["budget", "piano economic"]):
        args = {}
        if time_params.get("year"):
            args["year"] = time_params["year"]
        return [{"tool": "crea_budget", "args": args}]

    # Greetings (Bug 14: added buonasera, grazie)
    if any(kw in msg_lower for kw in ["ciao", "buongiorno", "buonasera", "salve", "hello", "hey", "grazie"]):
        if "grazie" in msg_lower:
            return [{"tool": "direct_response", "args": {"message": "Prego! Se hai bisogno di altro, sono qui."}}]
        # Page-aware greeting
        page = (context or {}).get("page", "")
        if page and page.lower().startswith("crm"):
            return [{"tool": "direct_response", "args": {"message": "Ciao! Come posso aiutarti con le vendite e la pipeline oggi?"}}]
        return [{"tool": "direct_response", "args": {"message": "Ciao! Come posso aiutarti oggi?"}}]

    # Page-aware fallback for completely unrecognized messages
    page = (context or {}).get("page", "")
    if page and page.lower().startswith("crm"):
        return [
            {"tool": "crm_pipeline_summary", "args": {}},
            {"tool": "crm_list_deals", "args": {}},
        ]

    return [{"tool": "direct_response", "args": {"message": "Non ho capito la richiesta. Prova con: fatturato 2024, top 5 clienti, elenco fatture, scadenze, pipeline CRM."}}]


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

    Uses page-based routing first (for context-aware routing on CRM/fatture/etc. pages).
    Then tries Claude API, falls back to keyword matching.
    """
    ctx = state.get("context", {})

    # Get the latest user message
    user_messages = [m for m in state["messages"] if m.get("role") == "user"]
    if not user_messages:
        state["tool_calls"] = [
            {"tool": "direct_response", "args": {"message": "Non ho ricevuto un messaggio."}}
        ]
        return state

    latest_message = user_messages[-1]["content"]

    # --- Page-based routing: check BEFORE LLM for unambiguous page contexts ---
    # This ensures CRM pages always route to sales tools, even with generic messages.
    if ctx.get("page"):
        page_route = _page_based_route(ctx["page"], latest_message)
        if page_route is not None:
            state["tool_calls"] = page_route
            return state

    if _has_api_key():
        try:
            tools_desc = get_tools_description()
            # Inject page context into the LLM system prompt for better routing
            page_hint = ""
            if ctx.get("page"):
                page_hint = (
                    f"\n\nCONTESTO PAGINA: L'utente si trova sulla pagina '{ctx['page']}'.\n"
                    f"Se la domanda e generica, privilegia i tool pertinenti alla pagina corrente.\n"
                    f"- Pagine CRM/pipeline/deal → usa tool CRM (crm_pipeline_summary, crm_list_deals)\n"
                    f"- Pagine fatture/contabilita → usa tool contabili (list_invoices, count_invoices)\n"
                    f"- Pagine scadenze/fisco → usa tool fiscali (get_deadlines, get_fiscal_alerts)\n"
                    f"- Pagine dashboard/ceo → usa tool KPI (get_period_stats, get_ceo_kpi)\n"
                )
            system_prompt = ORCHESTRATOR_SYSTEM_PROMPT.format(tools_description=tools_desc) + page_hint
            raw_response = await _call_llm(system_prompt, latest_message)

            # Parse JSON response
            # Claude might wrap in ```json ... ``` — strip that
            cleaned = raw_response.strip()
            if cleaned.startswith("```"):
                # Remove code fences
                lines = cleaned.split("\n")
                lines = [ln for ln in lines if not ln.strip().startswith("```")]
                cleaned = "\n".join(lines).strip()

            tool_calls = json.loads(cleaned)
            if isinstance(tool_calls, list):
                state["tool_calls"] = tool_calls
            else:
                state["tool_calls"] = [tool_calls]

        except Exception as e:
            logger.warning("Claude API call failed in router, using keyword fallback: %s", e)
            state["tool_calls"] = keyword_route(latest_message, context=ctx)
    else:
        state["tool_calls"] = keyword_route(latest_message, context=ctx)

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


def _format_crm_results(tool_results: list[dict]) -> str:
    """Format CRM tool results into an actionable commercial summary.

    Produces Italian-language advice about pipeline status, stale deals,
    and suggested next actions — the kind of response a sales agent would give.
    """
    parts: list[str] = []
    pipeline_data: dict = {}
    deals_data: list[dict] = []

    for tr in tool_results:
        tool_name = tr.get("tool", "")
        result = tr.get("result", {})
        if not isinstance(result, dict):
            continue

        if tool_name == "crm_pipeline_summary":
            pipeline_data = result
        elif tool_name == "crm_list_deals":
            raw_deals = result.get("deals", result.get("items", []))
            if isinstance(raw_deals, list):
                deals_data = raw_deals

    # Pipeline summary
    if pipeline_data:
        total = pipeline_data.get("total_deals", 0)
        total_value = pipeline_data.get("total_value", 0)
        weighted = pipeline_data.get("weighted_value", 0)

        if total == 0:
            return "La pipeline e vuota al momento. Vuoi creare un nuovo deal?"

        parts.append(
            f"Hai **{total} deal** in pipeline per un valore totale di **EUR {total_value:,.0f}**."
        )
        if weighted:
            parts.append(f"Valore pesato (per probabilita): EUR {weighted:,.0f}.")

        # Stage breakdown
        by_stage = pipeline_data.get("by_stage", {})
        if by_stage:
            stage_parts = []
            for stage_name, info in by_stage.items():
                if isinstance(info, dict):
                    count = info.get("count", 0)
                    value = info.get("value", 0)
                    if count > 0:
                        stage_parts.append(f"  - {stage_name}: {count} deal (EUR {value:,.0f})")
            if stage_parts:
                parts.append("\n**Pipeline per fase:**")
                parts.extend(stage_parts)

    # Deal analysis — find stale/urgent deals
    if deals_data:
        stale_deals = []
        high_value_deals = []
        for deal in deals_data:
            if not isinstance(deal, dict):
                continue
            days = deal.get("days_in_stage", 0)
            name = deal.get("name", deal.get("deal_name", ""))
            stage = deal.get("stage", deal.get("stage_name", ""))
            revenue = deal.get("expected_revenue", deal.get("revenue", 0)) or 0

            if days and days > 5:
                stale_deals.append({"name": name, "stage": stage, "days": days, "revenue": revenue})
            if revenue and revenue > 10000:
                high_value_deals.append({"name": name, "stage": stage, "revenue": revenue, "days": days})

        if stale_deals:
            parts.append(f"\n**Attenzione — {len(stale_deals)} deal fermi da troppo tempo:**")
            for d in stale_deals[:5]:
                parts.append(
                    f"  - **{d['name']}** fermo in '{d['stage']}' da {d['days']} giorni "
                    f"(EUR {d['revenue']:,.0f}) — suggerisco un follow-up"
                )

        if high_value_deals and not stale_deals:
            parts.append("\n**Deal di alto valore da seguire:**")
            for d in high_value_deals[:3]:
                action = "follow-up" if (d.get("days") or 0) > 3 else "monitora"
                parts.append(
                    f"  - **{d['name']}** in '{d['stage']}' (EUR {d['revenue']:,.0f}) — {action}"
                )

    if not parts:
        return ""  # Fall through to generic formatting

    # Add actionable suggestion
    parts.append("\nVuoi che analizzi un deal specifico o prepari un follow-up?")

    return "\n".join(parts)


def _format_results_fallback(tool_results: list[dict]) -> str:
    """Format tool results into a smart text response without LLM.

    US-A07: When multiple tools are present, prepend agent badges.
    Smart response logic:
    - CRM pipeline/deals → actionable commercial summary
    - Single value (count, total) -> short text
    - List <= 5 items -> markdown table
    - List > 5 items -> summary with link suggestion
    - Dashboard query -> suggest adding widget
    """
    is_multi = len(tool_results) > 1
    parts: list[str] = []

    # --- CRM-specific formatting ---
    crm_tools = {"crm_pipeline_summary", "crm_list_deals", "crm_list_contacts",
                 "crm_won_deals", "crm_pending_orders", "crm_analytics"}
    is_crm = any(tr.get("tool") in crm_tools for tr in tool_results)

    if is_crm:
        crm_parts = _format_crm_results(tool_results)
        if crm_parts:
            return crm_parts

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

        # Guided tool responses — pass through the message directly
        if "status" in result and result["status"] in ("needs_input", "guide", "proposal", "completed"):
            parts.append(f"{agent_badge}{result.get('message', '')}")
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
    "apertura_conti": "/import/bilancio",
    "crea_budget": "/budget",
    "crm_pipeline_summary": "/crm/pipeline",
    "crm_list_deals": "/crm/pipeline",
    "crm_list_contacts": "/crm/contatti",
    "crm_won_deals": "/crm/pipeline",
    "crm_pending_orders": "/crm/pipeline",
    "crm_analytics": "/crm/pipeline",
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
        page_lower = page.lower() if page else ""

        # Page-specific context hints for the response generation
        page_domain = "contabilita"
        if page_lower.startswith("crm") or page_lower.startswith("pipeline") or page_lower.startswith("deal"):
            page_domain = "vendite e pipeline CRM"
        elif page_lower.startswith("fattur"):
            page_domain = "fatturazione"
        elif page_lower.startswith("fisco") or page_lower.startswith("scadenz"):
            page_domain = "scadenze e adempimenti fiscali"
        elif page_lower.startswith("dashboard") or page_lower.startswith("ceo"):
            page_domain = "KPI e panoramica aziendale"
        elif page_lower.startswith("banca"):
            page_domain = "banca e cash flow"

        context_msg = (
            f"CONTESTO UTENTE:\n"
            f"- Pagina corrente: {page}\n"
            f"- Dominio pagina: {page_domain}\n"
            f"- Anno selezionato: {year}\n\n"
            f"Rispondi in modo pertinente al contesto della pagina ({page_domain}). "
            f"Se l'utente è sulla pagina CRM, parla di deal, pipeline e vendite. "
            f"Se l'utente è sulla dashboard {year}, le domande sui dati si riferiscono al {year}."
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
        "context": context or {},
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

    # Determine agent info (US-A07: multi-agent aware, ADR-010: agent registry)
    agent_name = "orchestrator"
    agent_type = "orchestrator"
    tool_calls_list = state.get("tool_calls", [])
    if tool_calls_list:
        non_direct_tools = [tc for tc in tool_calls_list if tc.get("tool") != "direct_response"]
        if non_direct_tools:
            first_tool = non_direct_tools[0].get("tool", "")
            agent_name = _get_agent_for_tool(first_tool)
            # Multi-agent: different agents used in same response
            agent_names = {_get_agent_for_tool(tc["tool"]) for tc in non_direct_tools}
            if len(agent_names) > 1:
                agent_type = "multi"
            else:
                agent_type = agent_name

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

    # Propagate suggested_actions from guided tools (apertura_conti, crea_budget)
    for tr in state.get("tool_results", []):
        result = tr.get("result", {})
        if isinstance(result, dict) and "suggested_actions" in result:
            existing = response_meta.get("suggested_actions", [])
            existing.extend(result["suggested_actions"])
            response_meta["suggested_actions"] = existing

    # UI Actions — generate highlights for CRM deals mentioned in tool results
    ui_actions = []
    for tr in state.get("tool_results", []):
        result = tr.get("result", {})
        if not isinstance(result, dict):
            continue
        # Highlight deals from pipeline summary or deal list
        deals = result.get("deals", [])
        if isinstance(deals, list):
            for deal in deals:
                if not isinstance(deal, dict) or not deal.get("id"):
                    continue
                # Highlight stale deals (>5 days in stage) with high priority
                days = deal.get("days_in_stage", 0) or 0
                if days > 5:
                    ui_actions.append({
                        "type": "highlight",
                        "target": "deal",
                        "id": str(deal["id"]),
                        "style": "pulse-border",
                        "color": "#ef4444" if days > 10 else "#f59e0b",
                        "tooltip": f"Fermo da {days} giorni — serve follow-up",
                        "navigate": f"/crm/deals/{deal['id']}",
                    })
                # Highlight high-value deals near closing
                elif deal.get("probability", 0) >= 50 and deal.get("expected_revenue", 0) > 5000:
                    ui_actions.append({
                        "type": "highlight",
                        "target": "deal",
                        "id": str(deal["id"]),
                        "style": "glow",
                        "color": "#8b5cf6",
                        "tooltip": f"Deal caldo — {deal.get('probability',0)}% probabilita",
                        "navigate": f"/crm/deals/{deal['id']}",
                    })
    if ui_actions:
        response_meta["ui_actions"] = ui_actions

    return {
        "content": content,
        "tool_calls": state.get("tool_calls"),
        "tool_results": state.get("tool_results"),
        "agent_name": agent_name,
        "agent_type": agent_type,
        "response_meta": response_meta,
    }
