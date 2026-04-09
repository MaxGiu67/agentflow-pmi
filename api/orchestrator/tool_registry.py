"""Tool registry — wraps existing services as callable tools (US-A04).

Each tool is a dict with: name, description, parameters (JSON Schema), handler (async callable).
Handlers accept db (AsyncSession), tenant_id (UUID), and tool-specific keyword arguments.

This module re-exports the TOOLS list and helper functions assembled from
domain-specific submodules under api.orchestrator.tools/.
"""

from api.orchestrator.tools import ALL_TOOLS

# Re-export individual handler functions for backward compatibility
from api.orchestrator.tools.accounting_tools import (  # noqa: F401
    count_invoices_handler,
    list_invoices_handler,
    get_invoice_detail_handler,
    get_journal_entries_handler,
    get_balance_sheet_summary_handler,
    get_pending_review_handler,
    apertura_conti_handler,
)
from api.orchestrator.tools.fiscal_tools import (  # noqa: F401
    get_deadlines_handler,
    get_fiscal_alerts_handler,
    sync_cassetto_handler,
)
from api.orchestrator.tools.scadenzario_tools import (  # noqa: F401
    predict_cashflow_handler,
)
from api.orchestrator.tools.dashboard_tools import (  # noqa: F401
    get_dashboard_summary_handler,
    get_ceo_kpi_handler,
    modify_dashboard_handler,
    get_top_clients_handler,
    get_period_stats_handler,
    list_expenses_handler,
    list_assets_handler,
    crea_budget_handler,
)
from api.orchestrator.tools.crm_tools import (  # noqa: F401
    crm_pipeline_summary_handler,
    crm_list_deals_handler,
    crm_list_contacts_handler,
    crm_won_deals_handler,
    crm_pending_orders_handler,
    crm_analytics_handler,
)

# The canonical TOOLS list — same as before the split
TOOLS: list[dict] = ALL_TOOLS


def get_tools_by_name() -> dict:
    """Return a dict mapping tool name -> tool definition."""
    return {tool["name"]: tool for tool in TOOLS}


def get_tools_description() -> str:
    """Return a formatted description of all tools for the system prompt."""
    lines = []
    for tool in TOOLS:
        params = tool["parameters"].get("properties", {})
        param_str = ", ".join(
            f"{k}: {v.get('type', 'string')}"
            for k, v in params.items()
        )
        lines.append(f"- {tool['name']}({param_str}): {tool['description']}")
    return "\n".join(lines)
