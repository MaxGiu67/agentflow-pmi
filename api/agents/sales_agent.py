"""Sales Agent — l'assistente commerciale (US-212, ADR-010).

Un solo agente per tutti i prodotti. I tool si attivano in base al prodotto del deal corrente.
Carica la pipeline dal DB, chiede info mancanti, suggerisce prossime azioni.
Non blocca mai — il commerciale puo saltare stati.
"""

from api.agents.base import BaseAgent


# Tool sempre disponibili (qualsiasi prodotto/pipeline)
CORE_TOOLS = [
    "crm_pipeline_summary",
    "crm_list_deals",
    "crm_list_contacts",
    "crm_won_deals",
    "crm_pending_orders",
]

# Tool specifici per pipeline_type
PIPELINE_TOOLS: dict[str, list[str]] = {
    "vendita_diretta": [
        "match_resources",       # US-205
        "calc_margin",           # US-206
        "generate_tm_offer",     # US-206
        "check_bench",           # US-207
    ],
    "progetto_corpo": [
        "prefill_specs",         # US-219
        "estimate_effort",       # US-219
        "generate_fixed_offer",  # US-219
    ],
    "social_selling": [
        "score_prospect",             # US-209
        "suggest_use_case_bundle",    # US-209
        "generate_linkedin_message",  # US-214
        "suggest_content",            # US-214
        "calc_warmth_score",          # US-215
        "check_linkedin_cadence",     # US-215
        "prefill_discovery_brief",    # US-220
        "prepare_demo",              # US-220
        "plan_onboarding",           # US-221
        "monitor_adoption",          # US-221
        "calc_roi",                  # US-210
    ],
}


class SalesAgent(BaseAgent):
    name = "sales"
    description = "Assistente commerciale. Gestisce deal, offerte, contatti, attivita per qualsiasi prodotto."

    # All possible tools (core + all pipeline-specific)
    tool_names = CORE_TOOLS.copy()

    keywords = [
        "deal", "offerta", "cliente", "contatt", "prospect", "pipeline",
        "commerciale", "vendita", "ordine", "proposta", "risorsa", "margine",
        "linkedin", "connessione", "engagement", "demo", "call",
        "onboarding", "use case", "ateco", "match", "tariffa", "bench",
        "specifiche", "corpo", "effort", "elevia",
    ]

    def get_tool_names(self, context: dict | None = None) -> list[str]:
        """Filter tools based on deal's product/pipeline.

        If context has deal.pipeline_type, add pipeline-specific tools.
        Otherwise, return only core CRM tools.
        """
        tools = CORE_TOOLS.copy()

        if context and context.get("deal"):
            pipeline_type = context["deal"].get("pipeline_type", "")
            extra = PIPELINE_TOOLS.get(pipeline_type, [])
            tools.extend(extra)

        return tools

    def get_system_prompt(self, context: dict | None = None) -> str:
        base = (
            "Sei l'assistente commerciale di AgentFlow. Aiuti il commerciale a gestire "
            "i deal, preparare offerte, tracciare attivita e seguire la pipeline.\n\n"
            "REGOLE:\n"
            "1. Sei un assistente, non un controllore. Suggerisci, non imponi.\n"
            "2. Se mancano info, chiedile in modo naturale.\n"
            "3. Se il deal e fermo da troppo tempo, suggerisci un follow-up.\n"
            "4. Prepara bozze ma chiedi sempre conferma prima di procedere.\n"
            "5. Se rilevi opportunita per altri prodotti, segnalalo discretamente.\n"
            "6. Risposte brevi e pratiche. Il commerciale ha fretta.\n"
        )

        if context and context.get("deal"):
            deal = context["deal"]
            base += (
                f"\nDEAL CORRENTE:\n"
                f"- Azienda: {deal.get('company', 'N/A')}\n"
                f"- Prodotto: {deal.get('product', 'N/A')} (pipeline: {deal.get('pipeline_type', 'N/A')})\n"
                f"- Stato: {deal.get('current_stage', 'N/A')}\n"
                f"- Ultimo contatto: {deal.get('last_contact', 'N/A')}\n"
            )

        return base
