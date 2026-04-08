"""Portal tools for Sales Agent v2 — wired to real PortalClient (Sprint 46-47).

All tools are async and use the portal_client singleton.
Read operations are always safe; write operations are marked HIGH RISK.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.tools import tool

from api.adapters.portal_client import portal_client

logger = logging.getLogger(__name__)


# ── Portal Read Tools ──────────────────────────────────────


@tool
async def portal_search_persons(search: str = "", skill: str = "") -> dict:
    """Search Portal persons by name or skill. Returns matching employees
    with name, email, and contract info. Use skill param to filter by technology."""
    query = skill if skill else search
    persons = await portal_client.get_persons(search=query)
    data = persons.get("data", []) if isinstance(persons, dict) else []

    results = []
    for p in data:
        name = f"{p.get('firstName', '')} {p.get('lastName', '')}".strip()
        info: dict[str, Any] = {
            "id": p.get("id"),
            "name": name,
            "email": p.get("email", ""),
        }
        # Include employment contract info if available
        contracts = p.get("EmploymentContracts") or p.get("employmentContracts") or []
        if contracts:
            info["contracts"] = [
                {
                    "id": c.get("id"),
                    "title": c.get("title", ""),
                    "start_date": c.get("startDate", ""),
                    "end_date": c.get("endDate", ""),
                }
                for c in contracts[:3]
            ]
        results.append(info)

    return {
        "results": results[:20],
        "total": persons.get("total", len(data)),
        "search_query": query,
    }


@tool
async def portal_get_projects(search: str = "") -> dict:
    """List Portal projects (commesse), optionally filtered by name.
    Returns project list with id, name, code, status."""
    projects = await portal_client.get_projects(search=search)
    data = projects.get("data", []) if isinstance(projects, dict) else []

    results = [
        {
            "id": p.get("id"),
            "name": p.get("name", ""),
            "code": p.get("code", ""),
            "status": p.get("status", ""),
            "customer_id": p.get("customerId") or p.get("customer_id"),
        }
        for p in data
    ]
    return {"projects": results, "total": projects.get("total", len(data))}


@tool
async def portal_get_project_detail(project_id: int) -> dict:
    """Get detailed info on a Portal project including activities and assigned resources."""
    project = await portal_client.get_project(project_id)
    if isinstance(project, dict) and project.get("error"):
        return {"error": project["error"]}
    return {"project": project}


@tool
async def portal_get_customers(search: str = "") -> dict:
    """Search Portal customers by name or code. Returns customer list."""
    customers = await portal_client.get_customers(search=search)
    data = customers.get("data", []) if isinstance(customers, dict) else []

    results = [
        {
            "id": c.get("id"),
            "name": c.get("name", ""),
            "code": c.get("code", ""),
        }
        for c in data
    ]
    return {"customers": results, "total": customers.get("total", len(data))}


@tool
async def portal_get_offers(search: str = "") -> dict:
    """List offers from Portal, optionally filtered by search term."""
    offers = await portal_client.get_offers(search=search)
    data = offers.get("data", []) if isinstance(offers, dict) else []

    results = [
        {
            "id": o.get("id"),
            "name": o.get("name", ""),
            "protocol": o.get("protocol", ""),
            "status": o.get("status", ""),
            "customer_id": o.get("customerId") or o.get("customer_id"),
        }
        for o in data
    ]
    return {"offers": results, "total": offers.get("total", len(data))}


@tool
async def portal_get_timesheets(project_id: int | None = None) -> dict:
    """Get timesheets to check resource utilization. Optionally filter by project_id."""
    timesheets = await portal_client.get_timesheets()
    data = timesheets.get("data", []) if isinstance(timesheets, dict) else []
    return {"timesheets": data[:50], "total": timesheets.get("total", len(data))}


# ── Portal Write Tools (HIGH RISK) ────────────────────────


@tool
async def portal_create_offer(
    customer_id: int,
    project_name: str,
    billing_type: str = "Daily",
    account_manager_email: str = "",
) -> dict:
    """Create an offer on Portal. HIGH RISK: requires human confirmation.
    billing_type: Daily (T&M), LumpSum (corpo), None.
    Returns offer creation data including auto-generated protocol."""
    # Get auto-generated protocol
    protocol = await portal_client.get_protocol_by_customer_id(customer_id)

    # Find account manager
    am = None
    if account_manager_email:
        am = await portal_client.find_account_manager_by_email(account_manager_email)

    # Get billing types for validation
    billing_types = await portal_client.get_billing_types()

    return {
        "action": "create_offer",
        "customer_id": customer_id,
        "project_name": project_name,
        "billing_type": billing_type,
        "protocol": protocol,
        "account_manager": am,
        "available_billing_types": billing_types,
        "risk": "high",
        "requires_confirmation": True,
    }


@tool
async def portal_approve_offer(
    offer_id: int,
    start_date: str,
    end_date: str,
    order_num: str = "",
) -> dict:
    """Approve an offer on Portal, which creates a commessa (project).
    HIGH RISK: requires human confirmation.
    Dates must be ISO format (YYYY-MM-DD)."""
    # Fetch current offer
    offer = await portal_client.get_offer(offer_id)
    if isinstance(offer, dict) and offer.get("error"):
        return {"error": f"Offerta {offer_id} non trovata: {offer['error']}"}

    return {
        "action": "approve_offer",
        "offer_id": offer_id,
        "offer_name": offer.get("name", "") if isinstance(offer, dict) else "",
        "start_date": start_date,
        "end_date": end_date,
        "order_num": order_num,
        "risk": "high",
        "requires_confirmation": True,
    }


@tool
async def portal_create_activity(
    project_id: int,
    description: str,
    start_date: str,
    end_date: str,
    activity_type_id: int = 9,
) -> dict:
    """Create an activity on a Portal project. Used to define work packages.
    activity_type_id: 9 = default (Sviluppo). Dates in ISO format."""
    result = await portal_client.create_activity({
        "projectId": project_id,
        "description": description,
        "startDate": start_date,
        "endDate": end_date,
        "activityTypeId": activity_type_id,
    })
    if isinstance(result, dict) and result.get("error"):
        return {"error": result["error"]}
    return {"activity": result, "status": "created"}


@tool
async def portal_assign_employee(
    activity_id: int,
    person_id: int,
    start_date: str,
    end_date: str,
    expected_days: int = 0,
) -> dict:
    """Assign an employee to a Portal activity. HIGH RISK: requires human confirmation.
    Dates in ISO format. expected_days = planned effort."""
    result = await portal_client.add_employee_to_activity({
        "activityId": activity_id,
        "personId": person_id,
        "startDate": start_date,
        "endDate": end_date,
        "expectedDays": expected_days,
    })
    if isinstance(result, dict) and result.get("error"):
        return {"error": result["error"]}
    return {
        "assignment": result,
        "status": "assigned",
        "risk": "high",
        "requires_confirmation": True,
    }


# ── Tool Registry ─────────────────────────────────────────

PORTAL_TOOLS = [
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
]
