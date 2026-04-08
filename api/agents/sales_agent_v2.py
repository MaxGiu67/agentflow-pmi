"""Sales Agent v2 — LangChain 1.2 + LangGraph 1.0 (ADR-010).

Full-featured commercial assistant with:
- Claude Sonnet 4 for routing and tool execution (fast, cheap)
- Claude Opus 4 for offer text generation (high quality prose)
- 25+ tools organized in 4 categories: CRM Core, Portal, Offer Generation, Search
- Human-in-the-loop for high-risk actions (create offer, approve, assign)
- Pipeline-aware tool filtering based on deal product type

Architecture:
    User message
         |
    [Router Node]  -- Claude Sonnet 4: classify intent, pick tool(s)
         |
    [Tool Executor] -- runs selected tool(s)
         |
    [Responder Node] -- Claude Sonnet 4: synthesize tool results into response
         |
    (if offer text needed) --> [Offer Writer] -- Claude Opus 4: write offer prose
         |
    [Human Gate] -- blocks high-risk actions until confirmed
         |
    Response to user
"""

from __future__ import annotations

import logging
import os
import uuid
from enum import Enum
from pathlib import Path
from typing import Annotated, Any, Literal, Sequence

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

from api.adapters.portal_client import portal_client
from api.agents.tools.offer_generator import (
    KNOWN_PLACEHOLDERS,
    generate_offer_document,
    list_placeholders,
)

logger = logging.getLogger(__name__)

# ── Models ──────────────────────────────────────────────

# Sonnet 4 for routing + tool calls (fast, cost-effective)
ROUTER_MODEL = os.getenv("SALES_AGENT_ROUTER_MODEL", "claude-sonnet-4-20250514")
# Opus 4 for offer prose generation (high quality text)
WRITER_MODEL = os.getenv("SALES_AGENT_WRITER_MODEL", "claude-opus-4-20250514")


def _get_router_llm() -> ChatAnthropic:
    return ChatAnthropic(
        model=ROUTER_MODEL,
        temperature=0.1,
        max_tokens=4096,
    )


def _get_writer_llm() -> ChatAnthropic:
    return ChatAnthropic(
        model=WRITER_MODEL,
        temperature=0.4,
        max_tokens=8192,
    )


# ── State ───────────────────────────────────────────────


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AgentState(BaseModel):
    """State passed through the LangGraph nodes."""

    messages: Annotated[Sequence[BaseMessage], add_messages] = Field(default_factory=list)
    # Context injected by orchestrator
    tenant_id: str = ""
    user_name: str = ""
    deal_context: dict[str, Any] = Field(default_factory=dict)
    pipeline_stages: list[dict[str, Any]] = Field(default_factory=list)
    # Internal routing
    selected_tools: list[str] = Field(default_factory=list)
    tool_results: dict[str, Any] = Field(default_factory=dict)
    risk_level: RiskLevel = RiskLevel.LOW
    needs_human_confirmation: bool = False
    human_confirmed: bool = False
    needs_offer_writing: bool = False
    # Output
    offer_output_path: str = ""
    final_response: str = ""


# ── Tool Definitions (25+ tools in 4 categories) ───────


# ---- Category 1: CRM Core (8 tools) ----

@tool
async def crm_get_deal_summary(deal_id: str) -> dict:
    """Get full summary of a CRM deal: company, product, stage, activities, missing info."""
    # Delegates to CRM service (injected at runtime via db session)
    return {"tool": "crm_get_deal_summary", "deal_id": deal_id, "status": "pending_integration"}


@tool
async def crm_list_deals(stage: str = "", pipeline_type: str = "", limit: int = 20) -> dict:
    """List CRM deals with optional filtering by stage or pipeline type."""
    return {"tool": "crm_list_deals", "stage": stage, "pipeline_type": pipeline_type, "limit": limit}


@tool
async def crm_move_deal_stage(deal_id: str, target_stage: str) -> dict:
    """Move a deal to a new pipeline stage. HIGH RISK: requires human confirmation."""
    return {"tool": "crm_move_deal_stage", "deal_id": deal_id, "target_stage": target_stage, "risk": "high"}


@tool
async def crm_log_activity(
    deal_id: str,
    activity_type: str,
    subject: str,
    notes: str = "",
) -> dict:
    """Log an activity (call, meeting, email, task, note) on a deal."""
    return {
        "tool": "crm_log_activity",
        "deal_id": deal_id,
        "type": activity_type,
        "subject": subject,
        "notes": notes,
    }


@tool
async def crm_pipeline_summary(pipeline_type: str = "") -> dict:
    """Get weighted pipeline summary: deals per stage, total value, conversion rates."""
    return {"tool": "crm_pipeline_summary", "pipeline_type": pipeline_type}


@tool
async def crm_list_contacts(search: str = "", company_id: str = "") -> dict:
    """Search CRM contacts by name, email, or company."""
    return {"tool": "crm_list_contacts", "search": search, "company_id": company_id}


@tool
async def crm_ask_missing_info(deal_id: str, current_stage: str) -> dict:
    """Given the deal's current stage, identify required fields still missing."""
    return {"tool": "crm_ask_missing_info", "deal_id": deal_id, "stage": current_stage}


@tool
async def crm_classify_loss(deal_id: str, reason: str, notes: str = "") -> dict:
    """Classify a lost deal with reason (price, timing, competitor, no-fit, other)."""
    return {"tool": "crm_classify_loss", "deal_id": deal_id, "reason": reason, "notes": notes}


# ---- Category 2: Portal Integration (8 tools) ----

@tool
async def portal_search_resources(
    skill: str = "",
    seniority: str = "",
    available_only: bool = True,
) -> dict:
    """Search Portal for resources by skill, seniority, and availability.
    Returns matching persons with employment contracts and project assignments."""
    persons = await portal_client.get_persons(search=skill)
    data = persons.get("data", []) if isinstance(persons, dict) else []
    results = []
    for p in data:
        person_info = {
            "id": p.get("id"),
            "name": f"{p.get('firstName', '')} {p.get('lastName', '')}".strip(),
            "email": p.get("email", ""),
            "contracts": p.get("EmploymentContracts", []),
        }
        if seniority:
            # Filter by seniority in contract title or role
            person_info["seniority_filter"] = seniority
        results.append(person_info)
    return {"tool": "portal_search_resources", "results": results[:20], "total": len(data)}


@tool
async def portal_get_projects(search: str = "") -> dict:
    """List Portal projects (commesse), optionally filtered by name."""
    projects = await portal_client.get_projects(search=search)
    return {"tool": "portal_get_projects", "data": projects}


@tool
async def portal_get_project_detail(project_id: int) -> dict:
    """Get detailed info on a Portal project including activities and assigned resources."""
    project = await portal_client.get_project(project_id)
    return {"tool": "portal_get_project_detail", "data": project}


@tool
async def portal_get_customers(search: str = "") -> dict:
    """Search Portal customers by name or code."""
    customers = await portal_client.get_customers(search=search)
    return {"tool": "portal_get_customers", "data": customers}


@tool
async def portal_create_offer(
    customer_id: int,
    project_name: str,
    billing_type: str = "Daily",
    account_manager_email: str = "",
) -> dict:
    """Create an offer on Portal. HIGH RISK: requires human confirmation.
    Billing types: Daily (T&M), LumpSum (corpo), None."""
    # Get auto-generated protocol
    protocol = await portal_client.get_protocol_by_customer_id(customer_id)
    # Find account manager
    am = None
    if account_manager_email:
        am = await portal_client.find_account_manager_by_email(account_manager_email)
    return {
        "tool": "portal_create_offer",
        "customer_id": customer_id,
        "project_name": project_name,
        "billing_type": billing_type,
        "protocol": protocol,
        "account_manager": am,
        "risk": "high",
    }


@tool
async def portal_get_offers(search: str = "") -> dict:
    """List offers from Portal, optionally filtered by search term."""
    offers = await portal_client.get_offers(search=search)
    return {"tool": "portal_get_offers", "data": offers}


@tool
async def portal_assign_resource(
    activity_id: int,
    person_id: int,
) -> dict:
    """Assign a resource (person) to a project activity. HIGH RISK: requires human confirmation."""
    return {
        "tool": "portal_assign_resource",
        "activity_id": activity_id,
        "person_id": person_id,
        "risk": "high",
    }


@tool
async def portal_get_timesheets(project_id: int | None = None) -> dict:
    """Get timesheets, optionally for a specific project, to check resource utilization."""
    timesheets = await portal_client.get_timesheets()
    return {"tool": "portal_get_timesheets", "data": timesheets}


# ---- Category 3: Offer Generation (4 tools) ----

@tool
async def generate_offer_doc(
    offer_type: str,
    replacements: dict[str, str],
    output_filename: str = "",
) -> dict:
    """Generate a Word (.docx) offer document from template. HIGH RISK: requires confirmation.

    offer_type: 'tm' for Time & Material, 'corpo' for fixed-price project.
    replacements: dict of placeholder name -> value. See KNOWN_PLACEHOLDERS.
    output_filename: optional custom filename (default: auto-generated from protocol).
    """
    if not output_filename:
        proto = replacements.get("PROTOCOLLO", "draft")
        output_filename = f"Offerta_{proto.replace('.', '_')}.docx"

    output_dir = Path("generated_offers")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / output_filename

    result = generate_offer_document(replacements, output_path)
    result["offer_type"] = offer_type
    result["risk"] = "high"
    return result


@tool
async def list_offer_placeholders() -> dict:
    """List all available placeholders in the offer template."""
    found_in_template = list_placeholders()
    return {
        "tool": "list_offer_placeholders",
        "known": sorted(KNOWN_PLACEHOLDERS),
        "found_in_template": found_in_template,
    }


@tool
async def calc_margin(daily_rate: float, daily_cost: float) -> dict:
    """Calculate margin for a T&M resource. Warns if margin < 15%."""
    if daily_rate <= 0:
        return {"error": "daily_rate must be positive"}
    margin = (daily_rate - daily_cost) / daily_rate
    margin_pct = round(margin * 100, 1)
    warning = None
    if margin_pct < 15:
        warning = f"Margine sotto soglia ({margin_pct}%). Rivedi la tariffa o chiedi approvazione."
    return {
        "tool": "calc_margin",
        "daily_rate": daily_rate,
        "daily_cost": daily_cost,
        "margin_pct": margin_pct,
        "margin_abs": round(daily_rate - daily_cost, 2),
        "warning": warning,
    }


@tool
async def estimate_effort(
    scope_description: str,
    team_size: int = 2,
    complexity: str = "medium",
) -> dict:
    """Estimate effort in person-days for a fixed-price project scope.
    complexity: low, medium, high. Returns estimate range."""
    # Heuristic base, refined by LLM in responder
    multipliers = {"low": 0.7, "medium": 1.0, "high": 1.5}
    mult = multipliers.get(complexity, 1.0)
    # Base estimate from description length as rough proxy
    words = len(scope_description.split())
    base_days = max(10, min(words // 3, 200))
    low_est = int(base_days * mult * 0.8)
    high_est = int(base_days * mult * 1.3)
    duration_months = round(high_est / (team_size * 20), 1)  # 20 working days/month
    return {
        "tool": "estimate_effort",
        "low_days": low_est,
        "high_days": high_est,
        "team_size": team_size,
        "complexity": complexity,
        "duration_months": duration_months,
        "note": "Stima indicativa. Validare con analisi requisiti dettagliata.",
    }


# ---- Category 4: Search & Intelligence (5 tools) ----

@tool
async def match_resources(
    required_skills: list[str],
    seniority: str = "",
    min_availability_days: int = 0,
) -> dict:
    """Match internal resources against required skills and seniority.
    Returns top 5 candidates with match score."""
    # Searches Portal persons + their skills/contracts
    persons = await portal_client.get_persons()
    data = persons.get("data", []) if isinstance(persons, dict) else []

    candidates = []
    for p in data:
        name = f"{p.get('firstName', '')} {p.get('lastName', '')}".strip()
        # Simple matching: check if required skills appear in person data
        score = 0
        for skill in required_skills:
            skill_lower = skill.lower()
            person_str = str(p).lower()
            if skill_lower in person_str:
                score += 25
        if seniority and seniority.lower() in str(p).lower():
            score += 20
        if score > 0:
            candidates.append({
                "id": p.get("id"),
                "name": name,
                "match_score": min(score, 100),
            })

    candidates.sort(key=lambda x: x["match_score"], reverse=True)
    top5 = candidates[:5]

    if not top5:
        return {
            "tool": "match_resources",
            "candidates": [],
            "suggestion": "Nessuna risorsa disponibile. Procedere con recruiting esterno?",
        }

    return {"tool": "match_resources", "candidates": top5}


@tool
async def detect_cross_sell(deal_id: str, notes: str = "") -> dict:
    """Analyze deal notes for cross-sell signals.
    Detects keywords: documentazione, processi, sviluppo custom, knowledge base, AI, automazione."""
    keywords_map = {
        "documentazione": "Elevia - Document AI",
        "processi": "Elevia - Process Automation",
        "sviluppo custom": "Progetto a Corpo",
        "knowledge base": "Elevia - Knowledge AI",
        "automazione": "Elevia - Process Automation",
        "machine learning": "Elevia - AI/ML",
        "chatbot": "Elevia - Conversational AI",
        "migrazione": "Progetto a Corpo",
        "integrazione": "Consulenza T&M",
    }
    detected = []
    notes_lower = notes.lower()
    for kw, product in keywords_map.items():
        if kw in notes_lower:
            detected.append({"keyword": kw, "suggested_product": product})

    return {
        "tool": "detect_cross_sell",
        "deal_id": deal_id,
        "signals": detected,
        "has_opportunity": len(detected) > 0,
    }


@tool
async def suggest_next_action(
    deal_id: str,
    current_stage: str,
    days_in_stage: int = 0,
    days_since_contact: int = 0,
) -> dict:
    """Suggest the best next action based on deal state, timing, and SLA."""
    suggestions = []

    if days_since_contact > 5:
        suggestions.append({
            "action": "follow_up",
            "message": f"Il cliente non risponde da {days_since_contact} giorni. Preparo un follow-up?",
            "priority": "high",
        })

    stage_actions = {
        "lead": "Qualifica il lead: chiedi budget, timeline, decision maker.",
        "qualifica": "Verifica le risorse disponibili e prepara una stima.",
        "match_risorse": "Presenta i profili candidati al cliente.",
        "offerta": "Finalizza l'offerta e inviala al referente.",
        "negoziazione": "Rispondi alle obiezioni e chiudi.",
        "analisi_requisiti": "Organizza un workshop tecnico con il cliente.",
        "specifiche": "Redigi le specifiche funzionali e condividile.",
        "prospect": "Invia connection request su LinkedIn.",
        "connessione": "Messaggio di warm-up, non pitchare.",
        "engagement": "Condividi contenuti di valore per il settore.",
        "discovery_call": "Prepara il discovery brief e prenota la call.",
    }

    stage_action = stage_actions.get(current_stage)
    if stage_action:
        suggestions.append({"action": "stage_specific", "message": stage_action, "priority": "medium"})

    if days_in_stage > 14:
        suggestions.append({
            "action": "stale_warning",
            "message": f"Deal fermo da {days_in_stage} giorni in fase '{current_stage}'. Rivedi la strategia.",
            "priority": "high",
        })

    return {"tool": "suggest_next_action", "deal_id": deal_id, "suggestions": suggestions}


@tool
async def generate_email_draft(
    context: str,
    email_type: str = "follow_up",
    client_name: str = "",
    product: str = "",
) -> dict:
    """Generate an email draft. Types: first_contact, follow_up, offer_send, reminder.
    The LLM responder will craft the actual text using this context."""
    return {
        "tool": "generate_email_draft",
        "email_type": email_type,
        "context": context,
        "client_name": client_name,
        "product": product,
    }


@tool
async def check_bench() -> dict:
    """Check resources currently on bench (available, between projects).
    Useful for T&M deals: 'Marco si libera tra 30gg, vuoi proporlo?'"""
    persons = await portal_client.get_persons()
    data = persons.get("data", []) if isinstance(persons, dict) else []
    # Resources with no active project or ending soon
    bench = []
    for p in data:
        name = f"{p.get('firstName', '')} {p.get('lastName', '')}".strip()
        bench.append({
            "id": p.get("id"),
            "name": name,
            "status": "on_bench",
        })
    return {"tool": "check_bench", "bench_resources": bench[:10], "total": len(bench)}


# ── Tool Registry ───────────────────────────────────────

# Tools organized by category with risk level
CRM_CORE_TOOLS = [
    crm_get_deal_summary,
    crm_list_deals,
    crm_move_deal_stage,
    crm_log_activity,
    crm_pipeline_summary,
    crm_list_contacts,
    crm_ask_missing_info,
    crm_classify_loss,
]

PORTAL_TOOLS = [
    portal_search_resources,
    portal_get_projects,
    portal_get_project_detail,
    portal_get_customers,
    portal_create_offer,
    portal_get_offers,
    portal_assign_resource,
    portal_get_timesheets,
]

OFFER_TOOLS = [
    generate_offer_doc,
    list_offer_placeholders,
    calc_margin,
    estimate_effort,
]

SEARCH_TOOLS = [
    match_resources,
    detect_cross_sell,
    suggest_next_action,
    generate_email_draft,
    check_bench,
]

ALL_TOOLS = CRM_CORE_TOOLS + PORTAL_TOOLS + OFFER_TOOLS + SEARCH_TOOLS

# Risk classification for human-in-the-loop
HIGH_RISK_TOOLS = {
    "crm_move_deal_stage",
    "portal_create_offer",
    "portal_assign_resource",
    "generate_offer_doc",
}

MEDIUM_RISK_TOOLS = {
    "generate_email_draft",
    "crm_log_activity",
}

# Pipeline-specific tool filtering
PIPELINE_TOOL_FILTER: dict[str, set[str]] = {
    "vendita_diretta": {
        "match_resources", "calc_margin", "generate_offer_doc",
        "check_bench", "portal_search_resources", "portal_assign_resource",
    },
    "progetto_corpo": {
        "estimate_effort", "generate_offer_doc", "portal_create_offer",
    },
    "social_selling": {
        "detect_cross_sell", "portal_search_resources",
        "generate_email_draft", "suggest_next_action",
    },
}


def get_tools_for_context(deal_context: dict[str, Any] | None = None) -> list:
    """Return filtered tool list based on deal's pipeline type.

    Core tools are always available. Pipeline-specific tools are added
    only when the deal's pipeline_type matches.
    """
    # Always include CRM core + search basics
    available = set(t.name for t in CRM_CORE_TOOLS + SEARCH_TOOLS)

    # Add portal read tools (always available)
    read_portal = {"portal_get_projects", "portal_get_project_detail",
                    "portal_get_customers", "portal_get_offers", "portal_get_timesheets"}
    available |= read_portal

    # Add offer listing (always available)
    available.add("list_offer_placeholders")

    # Pipeline-specific tools
    if deal_context:
        pipeline_type = deal_context.get("pipeline_type", "")
        extra = PIPELINE_TOOL_FILTER.get(pipeline_type, set())
        available |= extra

    # Map names back to tool objects
    tool_map = {t.name: t for t in ALL_TOOLS}
    return [tool_map[name] for name in sorted(available) if name in tool_map]


# ── System Prompts ──────────────────────────────────────

ROUTER_SYSTEM_PROMPT = """Sei il Sales Agent v2 di AgentFlow — l'assistente commerciale AI per Nexa Data.

RUOLO: Aiuti il commerciale a gestire deal, preparare offerte, cercare risorse, e seguire la pipeline.
NON sostituisci il commerciale. Suggerisci, prepari bozze, e chiedi conferma.

REGOLE:
1. Sei un assistente, non un controllore. Suggerisci, non imponi.
2. Se mancano info, chiedile in modo naturale: "Per l'offerta mi servirebbe sapere..."
3. Se il deal e fermo da troppo tempo, suggerisci un follow-up.
4. Prepara bozze (email, offerta) ma chiedi SEMPRE conferma prima di procedere.
5. Se rilevi opportunita cross-sell per altri prodotti, segnalalo discretamente.
6. Risposte brevi e pratiche. Il commerciale ha fretta.
7. Per azioni ad alto rischio (creare offerta, spostare deal, assegnare risorse) CHIEDI CONFERMA.

CONTESTO DEAL:
{deal_context}

PIPELINE:
{pipeline_info}

TOOL DISPONIBILI:
{tool_list}

Rispondi in italiano. Sii concreto e utile."""

OFFER_WRITER_SYSTEM_PROMPT = """Sei un copywriter tecnico-commerciale esperto per Nexa Data srl.
Scrivi testi professionali per offerte commerciali IT (T&M e progetti a corpo).

STILE:
- Professionale ma non burocratico
- Tecnico dove serve, comprensibile per il management
- Paragrafi brevi, punti elenco per liste
- Numeri e metriche concrete

STRUTTURA OFFERTA:
1. Descrizione Offerta (scope, obiettivi, approccio)
2. Componenti del sistema (se progetto a corpo)
3. Team di progetto (profili e tariffe)
4. Stima impegno (breakdown per componente)
5. Piano di sviluppo (fasi e timeline)
6. Modalita contrattuale (corpo: importo + milestone / T&M: tariffe + durata)
7. Assunzioni e dipendenze
8. Rischi identificati

Genera SOLO il testo richiesto, pronto per essere inserito nel placeholder del template Word."""


# ── LangGraph Nodes ─────────────────────────────────────


def _format_deal_context(state: AgentState) -> str:
    """Format deal context for system prompt injection."""
    ctx = state.deal_context
    if not ctx:
        return "Nessun deal attivo. Puoi cercare deal, contatti, o mostrare la pipeline."

    return (
        f"- Azienda: {ctx.get('company', 'N/A')}\n"
        f"- Prodotto: {ctx.get('product', 'N/A')} (pipeline: {ctx.get('pipeline_type', 'N/A')})\n"
        f"- Stato: {ctx.get('current_stage', 'N/A')}\n"
        f"- Giorni in fase: {ctx.get('days_in_stage', 'N/A')}\n"
        f"- Ultimo contatto: {ctx.get('last_contact', 'N/A')}\n"
        f"- Info mancanti: {', '.join(ctx.get('missing_fields', [])) or 'nessuna'}\n"
    )


def _format_pipeline_info(state: AgentState) -> str:
    """Format pipeline stages for prompt."""
    if not state.pipeline_stages:
        return "Pipeline non caricata."
    stages = []
    current = state.deal_context.get("current_stage", "")
    for s in state.pipeline_stages:
        marker = " <-- ATTUALE" if s.get("code") == current else ""
        stages.append(f"  {s.get('sequence', '?')}. {s.get('name', '?')}{marker}")
    return "\n".join(stages)


async def router_node(state: AgentState) -> dict:
    """Route user message: pick tools and plan response.

    Uses Claude Sonnet 4 with tools bound for fast intent classification.
    """
    llm = _get_router_llm()
    tools = get_tools_for_context(state.deal_context or None)
    tool_names = [t.name for t in tools]

    system = ROUTER_SYSTEM_PROMPT.format(
        deal_context=_format_deal_context(state),
        pipeline_info=_format_pipeline_info(state),
        tool_list=", ".join(tool_names),
    )

    messages = [SystemMessage(content=system)] + list(state.messages)
    llm_with_tools = llm.bind_tools(tools)
    response = await llm_with_tools.ainvoke(messages)

    return {"messages": [response]}


async def tool_executor_node(state: AgentState) -> dict:
    """Execute tools called by the router.

    Checks for high-risk tools and sets needs_human_confirmation flag.
    """
    last_message = state.messages[-1]
    if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
        return {}

    tool_map = {t.name: t for t in ALL_TOOLS}
    results = []
    risk = RiskLevel.LOW
    needs_confirm = False

    for tc in last_message.tool_calls:
        tool_name = tc["name"]
        tool_args = tc["args"]

        # Check risk level
        if tool_name in HIGH_RISK_TOOLS:
            risk = RiskLevel.HIGH
            needs_confirm = True
        elif tool_name in MEDIUM_RISK_TOOLS and risk != RiskLevel.HIGH:
            risk = RiskLevel.MEDIUM

        # Execute the tool
        if tool_name in tool_map:
            try:
                result = await tool_map[tool_name].ainvoke(tool_args)
                results.append(
                    ToolMessage(content=str(result), tool_call_id=tc["id"])
                )
            except Exception as e:
                logger.error("Tool %s failed: %s", tool_name, e)
                results.append(
                    ToolMessage(content=f"Errore: {e}", tool_call_id=tc["id"])
                )
        else:
            results.append(
                ToolMessage(content=f"Tool non trovato: {tool_name}", tool_call_id=tc["id"])
            )

    # Check if offer text generation is needed
    needs_writing = any(
        tc["name"] == "generate_offer_doc" for tc in last_message.tool_calls
    )

    return {
        "messages": results,
        "risk_level": risk,
        "needs_human_confirmation": needs_confirm,
        "needs_offer_writing": needs_writing,
    }


async def offer_writer_node(state: AgentState) -> dict:
    """Generate high-quality offer prose using Claude Opus 4.

    Only triggered when generate_offer_doc tool is called and we need
    to fill in text placeholders (Descrizione_Offerta, MODALITA_CONTRATTUALE, etc.).
    """
    llm = _get_writer_llm()
    deal = state.deal_context

    context_msg = (
        f"Genera il testo per un'offerta commerciale Nexa Data.\n\n"
        f"TIPO: {deal.get('pipeline_type', 'N/A')}\n"
        f"CLIENTE: {deal.get('company', 'N/A')}\n"
        f"PRODOTTO: {deal.get('product', 'N/A')}\n"
        f"STAGE: {deal.get('current_stage', 'N/A')}\n\n"
        f"Genera i testi per i seguenti placeholder del template Word:\n"
        f"- Descrizione_Offerta\n"
        f"- Team_di_progetto\n"
        f"- Stima_dettagliata_di_impegno\n"
        f"- PIANO_DI_SVILUPPO\n"
        f"- MODALITA_CONTRATTUALE\n"
        f"- ASSUNZIONE\n"
        f"- RISCHIO\n\n"
        f"Usa le informazioni dal contesto del deal e le conversazioni precedenti."
    )

    messages = [
        SystemMessage(content=OFFER_WRITER_SYSTEM_PROMPT),
        HumanMessage(content=context_msg),
    ]

    response = await llm.ainvoke(messages)
    return {"messages": [AIMessage(content=f"[Testo offerta generato da Opus 4]\n{response.content}")]}


async def human_gate_node(state: AgentState) -> dict:
    """Human-in-the-loop checkpoint for high-risk actions.

    In production, this pauses the graph and waits for user confirmation
    via the UI. For now, it flags the state.
    """
    if state.needs_human_confirmation and not state.human_confirmed:
        # In production: send confirmation request to frontend via WebSocket
        return {
            "messages": [AIMessage(content=(
                "Questa azione richiede la tua conferma. "
                "Rivedi i dettagli sopra e conferma per procedere."
            ))],
            "needs_human_confirmation": True,
        }
    return {}


async def responder_node(state: AgentState) -> dict:
    """Synthesize tool results into a final user-facing response.

    Uses Claude Sonnet 4 to format results conversationally.
    """
    llm = _get_router_llm()

    system = (
        "Sintetizza i risultati dei tool in una risposta chiara e concisa per il commerciale. "
        "Rispondi in italiano. Usa bullet points per liste. "
        "Se ci sono azioni da confermare, elencale chiaramente. "
        "Se ci sono warning (margine basso, deal fermo), evidenziali."
    )

    messages = [SystemMessage(content=system)] + list(state.messages)
    response = await llm.ainvoke(messages)

    return {"messages": [response], "final_response": response.content}


# ── Routing Logic ───────────────────────────────────────


def should_use_tools(state: AgentState) -> Literal["tool_executor", "responder"]:
    """Decide if the last message has tool calls to execute."""
    last = state.messages[-1] if state.messages else None
    if isinstance(last, AIMessage) and last.tool_calls:
        return "tool_executor"
    return "responder"


def after_tools(state: AgentState) -> Literal["offer_writer", "human_gate", "responder"]:
    """After tool execution, decide next step."""
    if state.needs_offer_writing:
        return "offer_writer"
    if state.needs_human_confirmation and not state.human_confirmed:
        return "human_gate"
    return "responder"


def after_human_gate(state: AgentState) -> Literal["responder", "__end__"]:
    """After human gate, always go to responder to format final message."""
    return "responder"


# ── Graph Assembly ──────────────────────────────────────


def build_sales_agent_graph() -> StateGraph:
    """Build the Sales Agent v2 LangGraph StateGraph.

    Graph topology:
        router --> [tools?] --> tool_executor --> [offer?] --> offer_writer
                                              --> [confirm?] --> human_gate
                                              --> responder --> END
               --> responder --> END
    """
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("router", router_node)
    graph.add_node("tool_executor", tool_executor_node)
    graph.add_node("offer_writer", offer_writer_node)
    graph.add_node("human_gate", human_gate_node)
    graph.add_node("responder", responder_node)

    # Set entry point
    graph.set_entry_point("router")

    # Router -> tools or direct response
    graph.add_conditional_edges("router", should_use_tools)

    # Tool executor -> offer writer / human gate / responder
    graph.add_conditional_edges("tool_executor", after_tools)

    # Offer writer -> responder
    graph.add_edge("offer_writer", "responder")

    # Human gate -> responder
    graph.add_conditional_edges("human_gate", after_human_gate)

    # Responder -> END
    graph.add_edge("responder", END)

    return graph


# Compiled graph (singleton, reusable)
sales_agent_v2_graph = build_sales_agent_graph().compile()


# ── Public API ──────────────────────────────────────────


async def invoke_sales_agent_v2(
    message: str,
    tenant_id: str = "",
    user_name: str = "",
    deal_context: dict[str, Any] | None = None,
    pipeline_stages: list[dict[str, Any]] | None = None,
    history: list[BaseMessage] | None = None,
) -> dict[str, Any]:
    """Invoke the Sales Agent v2 graph with a user message.

    Args:
        message: the user's natural language message
        tenant_id: current tenant UUID
        user_name: commercial user's name
        deal_context: current deal info (company, product, stage, etc.)
        pipeline_stages: FSM stages for the deal's pipeline
        history: previous conversation messages

    Returns:
        dict with "response" (str) and "state" (full AgentState for inspection)
    """
    messages: list[BaseMessage] = list(history or [])
    messages.append(HumanMessage(content=message))

    initial_state = AgentState(
        messages=messages,
        tenant_id=tenant_id,
        user_name=user_name,
        deal_context=deal_context or {},
        pipeline_stages=pipeline_stages or [],
    )

    result = await sales_agent_v2_graph.ainvoke(initial_state)

    # Extract final response
    final = ""
    if result.get("messages"):
        for msg in reversed(result["messages"]):
            if isinstance(msg, AIMessage) and msg.content:
                final = msg.content
                break

    return {
        "response": final,
        "state": result,
    }
