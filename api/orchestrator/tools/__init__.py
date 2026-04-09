"""Re-export all tool lists from submodules."""

from api.orchestrator.tools.accounting_tools import ACCOUNTING_TOOLS
from api.orchestrator.tools.banking_tools import BANKING_TOOLS
from api.orchestrator.tools.crm_tools import CRM_TOOL_DEFINITIONS as CRM_TOOLS
from api.orchestrator.tools.fiscal_tools import FISCAL_TOOLS
from api.orchestrator.tools.scadenzario_tools import SCADENZARIO_TOOLS
from api.orchestrator.tools.dashboard_tools import DASHBOARD_TOOLS
from api.orchestrator.tools.email_tools import EMAIL_TOOLS
from api.orchestrator.tools.portal_tools import PORTAL_TOOLS
from api.orchestrator.tools.other_tools import OTHER_TOOLS

ALL_TOOLS: list[dict] = (
    ACCOUNTING_TOOLS
    + BANKING_TOOLS
    + FISCAL_TOOLS
    + SCADENZARIO_TOOLS
    + DASHBOARD_TOOLS
    + CRM_TOOLS
    + EMAIL_TOOLS
    + PORTAL_TOOLS
    + OTHER_TOOLS
)

__all__ = [
    "ACCOUNTING_TOOLS",
    "BANKING_TOOLS",
    "CRM_TOOLS",
    "FISCAL_TOOLS",
    "SCADENZARIO_TOOLS",
    "DASHBOARD_TOOLS",
    "EMAIL_TOOLS",
    "PORTAL_TOOLS",
    "OTHER_TOOLS",
    "ALL_TOOLS",
]
