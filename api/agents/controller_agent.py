"""Controller Agent — il ragioniere (US-213).

Wrappa i 17 tool esistenti per fatture, contabilita, scadenze, fisco, budget.
Zero modifiche ai tool — solo raggruppamento.
"""

from api.agents.base import BaseAgent


class ControllerAgent(BaseAgent):
    name = "controller"
    description = "Gestisce fatture, contabilita, scadenze, fisco, budget, spese, cespiti."

    tool_names = [
        # Fisco
        "count_invoices",
        "list_invoices",
        "get_invoice_detail",
        "get_dashboard_summary",
        "get_fiscal_alerts",
        "get_deadlines",
        "sync_cassetto",
        "get_top_clients",
        # Contabilita
        "get_journal_entries",
        "get_balance_sheet_summary",
        "get_pending_review",
        "list_expenses",
        "list_assets",
        "get_period_stats",
        "get_ceo_kpi",
        # Controller
        "apertura_conti",
        "crea_budget",
    ]

    keywords = [
        "fattura", "fatture", "iva", "f24", "scadenz", "bilancio", "budget",
        "spese", "cespiti", "contabil", "registr", "journal", "partita doppia",
        "cassetto", "spid", "fiscale", "fisco", "bolletta", "nota credito",
        "ritenuta", "bollo", "cu ", "dichiarazion", "versament",
        "ammortament", "attiv", "passiv", "dare", "avere",
    ]

    def get_system_prompt(self, context: dict | None = None) -> str:
        return (
            "Sei il controller aziendale di AgentFlow. Gestisci fatture, contabilita, "
            "scadenze fiscali, budget e bilancio. Rispondi in italiano, in modo chiaro "
            "e conciso. Usa dati reali dal database del tenant. Formatta i numeri come "
            "valuta EUR quando appropriato."
        )
