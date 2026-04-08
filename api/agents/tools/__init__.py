"""Sales Agent v2 tools — LangChain tool functions organized by category.

Categories:
- CRM Core: deal CRUD, pipeline, contacts, activities
- Portal: resource search, projects, offers, timesheets
- Offer Generation: Word doc from template (python-docx) + margin calc
- Search: resource matching by skill/seniority (in sales_agent_v2.py)
"""

from api.agents.tools.offer_generator import generate_offer_document

from api.agents.tools.crm_tools import (
    CRM_TOOLS,
    crm_get_deal,
    crm_list_deals,
    crm_update_deal,
    crm_move_stage,
    crm_pipeline_summary,
    crm_list_contacts,
    crm_create_activity,
    crm_get_activities,
    set_tool_context,
)

from api.agents.tools.portal_tools import (
    PORTAL_TOOLS,
    portal_search_persons,
    portal_get_projects,
    portal_get_project_detail,
    portal_get_customers,
    portal_get_offers,
    portal_get_timesheets,
    portal_create_offer,
    portal_approve_offer,
    portal_create_activity,
    portal_assign_employee,
)

from api.agents.tools.offer_tools import (
    OFFER_TOOLS,
    generate_offer_doc,
    calc_margin,
)

__all__ = [
    # Offer generator (legacy)
    "generate_offer_document",
    # CRM tools
    "CRM_TOOLS",
    "crm_get_deal",
    "crm_list_deals",
    "crm_update_deal",
    "crm_move_stage",
    "crm_pipeline_summary",
    "crm_list_contacts",
    "crm_create_activity",
    "crm_get_activities",
    "set_tool_context",
    # Portal tools
    "PORTAL_TOOLS",
    "portal_search_persons",
    "portal_get_projects",
    "portal_get_project_detail",
    "portal_get_customers",
    "portal_get_offers",
    "portal_get_timesheets",
    "portal_create_offer",
    "portal_approve_offer",
    "portal_create_activity",
    "portal_assign_employee",
    # Offer tools
    "OFFER_TOOLS",
    "generate_offer_doc",
    "calc_margin",
]
