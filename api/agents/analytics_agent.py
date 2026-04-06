"""Analytics Agent — l'analista (US-211).

Previsioni, trend, scenari, pipeline analytics, KPI commerciale.
"""

from api.agents.base import BaseAgent


class AnalyticsAgent(BaseAgent):
    name = "analytics"
    description = "Analizza trend, previsioni cash flow, pipeline analytics, KPI commerciale."

    tool_names = [
        "predict_cashflow",
        "crm_pipeline_summary",
    ]

    keywords = [
        "cashflow", "cash flow", "previsione", "previsioni", "trend",
        "pipeline", "analytics", "kpi", "performance", "conversion",
        "forecast", "scenari", "what-if", "andamento",
    ]

    def get_system_prompt(self, context: dict | None = None) -> str:
        return (
            "Sei l'analista di AgentFlow. Fornisci previsioni di cash flow, analytics "
            "sulla pipeline commerciale, KPI e trend. Rispondi con dati e numeri concreti. "
            "Quando possibile, confronta con il periodo precedente."
        )
