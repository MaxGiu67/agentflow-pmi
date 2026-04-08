"""Portal proxy router — reads from PortalJS.be via JWT (ADR-011, US-233).

Prefix: /portal
Tags: portal

All endpoints are read-only proxies. Writes (create project, assign resource)
are in separate endpoints that require human confirmation.
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User, CrmDeal
from api.db.session import get_db
from api.middleware.auth import get_current_user
from api.adapters.portal_client import portal_client

router = APIRouter(prefix="/portal", tags=["portal"])


@router.get("/status")
async def portal_status(user: User = Depends(get_current_user)):
    """Check Portal connection status."""
    return {
        "enabled": portal_client.is_enabled(),
        "url": portal_client.base_url or "not configured",
        "tenant": portal_client.tenant,
    }


# ── Customers (AC-233.2) ──────────────────────────────


@router.get("/customers")
async def list_customers(
    search: str = Query(""),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    user: User = Depends(get_current_user),
):
    """Proxy: list customers from Portal."""
    result = await portal_client.get_customers(search=search, page=page, page_size=page_size)
    customers = result.get("data", [])
    return {
        "customers": [
            {
                "portal_id": c.get("id"),
                "name": c.get("name", ""),
                "vat": c.get("vatNumber") or c.get("taxCode") or "",
                "city": c.get("city", {}).get("name", "") if isinstance(c.get("city"), dict) else "",
                "email": c.get("email", ""),
                "phone": c.get("phoneNumber", ""),
            }
            for c in customers
        ],
        "total": result.get("total", len(customers)),
        "source": "portal",
    }


@router.get("/customers/{customer_id}")
async def get_customer(
    customer_id: int,
    user: User = Depends(get_current_user),
):
    """Proxy: get single customer from Portal."""
    return await portal_client.get_customer(customer_id)


# ── Persons (AC-233.2) ────────────────────────────────


@router.get("/persons")
async def list_persons(
    search: str = Query(""),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
):
    """Proxy: list persons from Portal with contracts and skills (US-232)."""
    result = await portal_client.get_persons(search=search, page=page, page_size=page_size)
    persons = result.get("data", [])
    return {
        "persons": [_map_person(p) for p in persons],
        "total": result.get("total", len(persons)),
        "source": "portal",
    }


def _map_person(p: dict) -> dict:
    """Map Portal Person to AgentFlow format with contracts and skills."""
    # Extract active contract
    contracts = p.get("EmploymentContracts") or p.get("employmentContracts") or []
    active_contract = None
    for c in contracts:
        end = c.get("end_date") or c.get("endDate") or c.get("effectiveEndDate")
        if not end:  # No end date = still active
            active_contract = c
            break
    if not active_contract and contracts:
        active_contract = contracts[-1]  # Last contract as fallback

    # Extract skills
    skill_areas = p.get("PersonSkillAreas") or p.get("personSkillAreas") or []
    skills = []
    for sa in skill_areas:
        skill = sa.get("SkillArea") or sa.get("skillArea") or {}
        skills.append({
            "name": skill.get("name", ""),
            "seniority": sa.get("seniority", ""),
        })

    return {
        "portal_id": p.get("id"),
        "first_name": p.get("firstName") or p.get("first_name") or "",
        "last_name": p.get("lastName") or p.get("last_name") or "",
        "full_name": f"{p.get('firstName') or p.get('first_name') or ''} {p.get('lastName') or p.get('last_name') or ''}".strip(),
        "email": p.get("privateEmail") or p.get("private_email") or "",
        "fiscal_code": p.get("taxCode") or p.get("tax_code") or "",
        "employee_id": p.get("employee_id", ""),
        "seniority": p.get("Seniority") or p.get("seniority") or "",
        "location": (p.get("Location") or p.get("location") or {}).get("description", ""),
        "skills": skills,
        "contract": {
            "type": (active_contract.get("ContractType") or active_contract.get("contractType") or {}).get("description", "") if active_contract else "",
            "company": (active_contract.get("Company") or active_contract.get("company") or {}).get("name", "") if active_contract else "",
            "start_date": active_contract.get("startDate") or active_contract.get("start_date") or "" if active_contract else "",
            "end_date": active_contract.get("endDate") or active_contract.get("end_date") or active_contract.get("effectiveEndDate") or "" if active_contract else "",
            "daily_cost": active_contract.get("dailyCost") or active_contract.get("daily_cost") or 0 if active_contract else 0,
            "sales_rate": active_contract.get("salesRate") or active_contract.get("sales_rate") or 0 if active_contract else 0,
        } if active_contract else None,
    }


@router.get("/persons/{person_id}")
async def get_person(
    person_id: int,
    user: User = Depends(get_current_user),
):
    """Proxy: get single person with contracts from Portal."""
    return await portal_client.get_person(person_id)


# ── Projects (AC-233.2) ───────────────────────────────


@router.get("/projects")
async def list_projects(
    search: str = Query(""),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
):
    """Proxy: list projects (commesse) from Portal."""
    result = await portal_client.get_projects(search=search, page=page, page_size=page_size)
    projects = result.get("data", [])
    return {
        "projects": [
            {
                "portal_id": p.get("id"),
                "project_code": p.get("project_code", ""),
                "name": p.get("name", ""),
                "billing_type": p.get("billing_type", ""),
                "amount": p.get("amount"),
                "rate": p.get("rate"),
                "start_date": p.get("start_date"),
                "end_date": p.get("end_date"),
                "customer_name": p.get("customer", {}).get("name", "") if isinstance(p.get("customer"), dict) else "",
            }
            for p in projects
        ],
        "total": result.get("total", len(projects)),
        "source": "portal",
    }


@router.get("/projects/{project_id}")
async def get_project(
    project_id: int,
    user: User = Depends(get_current_user),
):
    """Proxy: get single project with activities from Portal."""
    return await portal_client.get_project(project_id)


# ── Timesheets (AC-233.2) ─────────────────────────────


@router.get("/timesheets")
async def list_timesheets(
    year: int = Query(0),
    month: int = Query(0),
    user: User = Depends(get_current_user),
):
    """Proxy: list timesheets from Portal."""
    result = await portal_client.get_timesheets(
        year=year if year > 0 else None,
        month=month if month > 0 else None,
    )
    return result


# ── Offers (US-234) ────────────────────────────────


@router.get("/offers")
async def list_offers(
    search: str = Query(""),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
):
    """Proxy: list offers from Portal."""
    return await portal_client.get_offers(search=search, page=page, page_size=page_size)


@router.get("/offers/{offer_id}")
async def get_offer(
    offer_id: int,
    user: User = Depends(get_current_user),
):
    """Proxy: get single offer."""
    return await portal_client.get_offer(offer_id)


@router.get("/offers/protocol/{customer_code}")
async def get_protocol(
    customer_code: str,
    user: User = Depends(get_current_user),
):
    """Get auto-generated protocol number for a customer."""
    return await portal_client.get_protocol(customer_code)


@router.get("/offers/protocol-by-customer/{customer_id}")
async def get_protocol_by_customer(
    customer_id: int,
    user: User = Depends(get_current_user),
):
    """Get auto-generated protocol number by customer ID."""
    return await portal_client.get_protocol_by_customer_id(customer_id)


@router.get("/offers/billing-types")
async def get_billing_types(
    user: User = Depends(get_current_user),
):
    """Get available billing types."""
    return await portal_client.get_billing_types()


@router.get("/project-types")
async def list_project_types(
    search: str = Query(""),
    user: User = Depends(get_current_user),
):
    """Get available project types for offers."""
    result = await portal_client.get_project_types(search=search)
    data = result.get("data", []) if isinstance(result, dict) else result if isinstance(result, list) else []
    return [
        {"id": pt.get("id"), "code": pt.get("code", ""), "description": pt.get("description", ""), "billing_type": pt.get("billing_type", "")}
        for pt in data
    ]


@router.get("/locations")
async def list_locations(
    user: User = Depends(get_current_user),
):
    """Get available locations (sedi)."""
    result = await portal_client.get_locations()
    data = result.get("data", []) if isinstance(result, dict) else result if isinstance(result, list) else []
    return [
        {"id": loc.get("id"), "code": loc.get("code", ""), "description": loc.get("description", "")}
        for loc in data
    ]


@router.get("/account-managers")
async def list_account_managers(
    user: User = Depends(get_current_user),
):
    """Get users that can be account managers."""
    result = await portal_client.get_account_managers()
    data = result.get("data", []) if isinstance(result, dict) else result if isinstance(result, list) else []
    managers = []
    for u in data:
        person = u.get("Person") or u.get("person") or {}
        first = person.get("firstName") or person.get("first_name") or ""
        last = person.get("lastName") or person.get("last_name") or ""
        managers.append({
            "id": u.get("id"),
            "email": u.get("email", ""),
            "name": f"{first} {last}".strip() or u.get("email", ""),
        })
    return managers


@router.get("/my-account-manager")
async def get_my_account_manager(
    user: User = Depends(get_current_user),
):
    """Find Portal account manager matching current user's email."""
    result = await portal_client.find_account_manager_by_email(user.email)
    if result:
        return result
    return {"id": None, "email": user.email, "name": None, "error": "No matching Portal account found"}


@router.post("/offers/create")
async def create_offer(
    body: dict,
    user: User = Depends(get_current_user),
):
    """Create offer on Portal (requires human confirmation)."""
    return await portal_client.create_offer(body)


@router.patch("/offers/{offer_id}")
async def update_offer(
    offer_id: int,
    body: dict,
    user: User = Depends(get_current_user),
):
    """Update offer on Portal."""
    return await portal_client.update_offer(offer_id, body)


# ── Activities & Assignments (US-237) ──────────────


@router.get("/activities/types")
async def get_activity_types(
    user: User = Depends(get_current_user),
):
    """Get available activity types from Portal."""
    return await portal_client.get_activity_types()


@router.get("/activities/by-project/{project_id}")
async def get_activities_by_project(
    project_id: int,
    user: User = Depends(get_current_user),
):
    """Get activities for a project."""
    return await portal_client.get_activities_by_project(project_id)


@router.post("/activities/create")
async def create_portal_activity(
    body: dict,
    user: User = Depends(get_current_user),
):
    """Create activity in Portal project."""
    return await portal_client.create_activity(body)


@router.post("/activities/assign")
async def assign_employee(
    body: dict,
    user: User = Depends(get_current_user),
):
    """Assign employee to activity on Portal."""
    return await portal_client.add_employee_to_activity(body)


@router.get("/activities/{activity_id}/persons")
async def get_activity_persons(
    activity_id: int,
    user: User = Depends(get_current_user),
):
    """Get employees assigned to an activity."""
    return await portal_client.get_related_person_activities(activity_id)


# ── Customer Matching (US-235) ────────────────────


@router.get("/match-customer")
async def match_customer_by_piva(
    piva: str = Query(..., min_length=5),
    user: User = Depends(get_current_user),
):
    """Match Portal Customer by P.IVA / tax code (US-235).

    Returns: single match (auto), multiple (user choice), or no match.
    """
    result = await portal_client.get_customers(search=piva, page=1, page_size=20)
    customers = result.get("data", [])
    # Filter by exact or partial VAT/tax match
    matches = []
    for c in customers:
        vat = (c.get("vatNumber") or c.get("taxCode") or "").replace(" ", "")
        if piva.replace(" ", "") in vat or vat in piva.replace(" ", ""):
            matches.append({
                "portal_id": c.get("id"),
                "name": c.get("name", ""),
                "vat": vat,
                "city": c.get("city", {}).get("name", "") if isinstance(c.get("city"), dict) else "",
            })
    if len(matches) == 1:
        return {"status": "single_match", "customer": matches[0]}
    elif len(matches) > 1:
        return {"status": "multiple_matches", "customers": matches}
    else:
        return {"status": "no_match", "search": piva}


@router.post("/batch-match")
async def batch_match_customers(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Batch-match legacy deals without portal_customer_id by company P.IVA (US-235)."""
    from api.db.models import CrmCompany
    # Find deals with company_id but no portal_customer_id
    result = await db.execute(
        select(CrmDeal).where(
            CrmDeal.tenant_id == user.tenant_id,
            CrmDeal.company_id.isnot(None),
            CrmDeal.portal_customer_id.is_(None),
        )
    )
    deals = result.scalars().all()
    matched = 0
    skipped = 0
    for deal in deals:
        if not deal.company_id:
            skipped += 1
            continue
        # Get company P.IVA
        comp_result = await db.execute(
            select(CrmCompany).where(CrmCompany.id == deal.company_id)
        )
        company = comp_result.scalar_one_or_none()
        if not company or not company.piva:
            skipped += 1
            continue
        # Search Portal
        portal_result = await portal_client.get_customers(search=company.piva, page=1, page_size=5)
        portal_customers = portal_result.get("data", [])
        for pc in portal_customers:
            vat = (pc.get("vatNumber") or pc.get("taxCode") or "").replace(" ", "")
            if company.piva.replace(" ", "") == vat:
                deal.portal_customer_id = pc.get("id")
                deal.portal_customer_name = pc.get("name", "")
                matched += 1
                break
        else:
            skipped += 1
    await db.commit()
    return {"matched": matched, "skipped": skipped, "total": len(deals)}


# ── Link Deal to Portal Project (US-236) ─────────


@router.post("/link-project")
async def link_deal_to_project(
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Link a deal to a Portal project (commessa) after offer becomes project (US-236)."""
    deal_id = body.get("deal_id")
    portal_project_id = body.get("portal_project_id")
    if not deal_id or not portal_project_id:
        return {"error": "deal_id and portal_project_id required"}
    result = await db.execute(
        select(CrmDeal).where(CrmDeal.id == uuid.UUID(deal_id), CrmDeal.tenant_id == user.tenant_id)
    )
    deal = result.scalar_one_or_none()
    if not deal:
        return {"error": "Deal not found"}
    deal.portal_project_id = portal_project_id
    await db.commit()
    return {"ok": True, "deal_id": deal_id, "portal_project_id": portal_project_id}


@router.get("/deal-project/{deal_id}")
async def get_deal_project(
    deal_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get Portal project linked to a deal, with activities and assigned persons."""
    result = await db.execute(
        select(CrmDeal).where(CrmDeal.id == uuid.UUID(deal_id), CrmDeal.tenant_id == user.tenant_id)
    )
    deal = result.scalar_one_or_none()
    if not deal or not deal.portal_project_id:
        return {"project": None}
    project = await portal_client.get_project(deal.portal_project_id)
    activities = await portal_client.get_activities_by_project(deal.portal_project_id)
    return {"project": project, "activities": activities}


# ── Operational Progress (US-239/240) ─────────────


@router.get("/deal-progress/{deal_id}")
async def get_deal_progress(
    deal_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get operational progress for a deal: hours, cost, margin (US-239/240)."""
    result = await db.execute(
        select(CrmDeal).where(CrmDeal.id == uuid.UUID(deal_id), CrmDeal.tenant_id == user.tenant_id)
    )
    deal = result.scalar_one_or_none()
    if not deal or not deal.portal_project_id:
        return {"progress": None}

    # Fetch project + activities with persons
    project = await portal_client.get_project(deal.portal_project_id)
    activities = await portal_client.get_activities_by_project(deal.portal_project_id)

    # Calculate totals from activities and assigned persons
    total_planned_days = deal.estimated_days or 0
    deal_value = deal.expected_revenue or 0
    daily_rate = deal.daily_rate or 0

    # Count assigned persons and their costs
    total_assigned = 0
    total_daily_cost = 0.0
    activity_list = activities.get("data", []) if isinstance(activities, dict) else activities if isinstance(activities, list) else []
    for act in activity_list:
        persons = act.get("PersonActivities") or []
        for pa in persons:
            total_assigned += 1
            person = pa.get("Person") or {}
            contract = person.get("CurrentContract", {}).get("Contract", {}) if person.get("CurrentContract") else {}
            cost = contract.get("dailyCost") or contract.get("daily_cost") or 0
            total_daily_cost += float(cost)

    # Calculate margin
    budget = deal_value
    estimated_cost = total_daily_cost * total_planned_days if total_planned_days > 0 else 0
    margin_eur = budget - estimated_cost
    margin_pct = (margin_eur / budget * 100) if budget > 0 else 0

    return {
        "progress": {
            "deal_value": deal_value,
            "daily_rate": daily_rate,
            "planned_days": total_planned_days,
            "assigned_persons": total_assigned,
            "avg_daily_cost": round(total_daily_cost / total_assigned, 2) if total_assigned > 0 else 0,
            "total_daily_cost": round(total_daily_cost, 2),
            "estimated_cost": round(estimated_cost, 2),
            "budget": budget,
            "margin_eur": round(margin_eur, 2),
            "margin_pct": round(margin_pct, 1),
            "warning": margin_pct < 15,
            "project_name": project.get("name", "") if isinstance(project, dict) else "",
        }
    }


# ── Create Offer from Deal (Sprint A) ────────────


@router.post("/offers/create-from-deal/{deal_id}")
async def create_offer_from_deal(
    deal_id: str,
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a Portal offer auto-populated from deal data."""
    if not user.tenant_id:
        return {"error": "Tenant not configured"}

    result = await db.execute(
        select(CrmDeal).where(CrmDeal.id == uuid.UUID(deal_id), CrmDeal.tenant_id == user.tenant_id)
    )
    deal = result.scalar_one_or_none()
    if not deal:
        return {"error": "Deal not found"}
    if not deal.portal_customer_id:
        return {"error": "Deal has no Portal customer linked"}

    # Build offer payload
    billing = body.get("billing_type")
    if not billing:
        billing = "Daily" if deal.deal_type == "T&M" else "LumpSum"

    payload = {
        "project_code": body.get("project_code", ""),
        "name": body.get("name", deal.name),
        "customer_id": deal.portal_customer_id,
        "accountManager_id": body.get("accountManager_id"),
        "project_type_id": body.get("project_type_id"),
        "location_id": body.get("location_id"),
        "billing_type": billing,
        "rate": deal.daily_rate if deal.daily_rate else None,
        "days": deal.estimated_days if deal.estimated_days else None,
        "amount": deal.expected_revenue if deal.expected_revenue else None,
        "OutcomeType": "W",
        "year": body.get("year", datetime.now().year),
        "other_details": body.get("other_details", ""),
    }

    offer_result = await portal_client.create_offer(payload)

    # Save portal_offer_id on deal
    if offer_result and isinstance(offer_result, dict) and offer_result.get("id"):
        deal.portal_offer_id = offer_result["id"]
        await db.commit()

    return offer_result


# ── Create Project from Deal (Sprint A) ──────────


@router.post("/projects/create-from-deal/{deal_id}")
async def create_project_from_deal(
    deal_id: str,
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create Portal project from deal's offer."""
    if not user.tenant_id:
        return {"error": "Tenant not configured"}

    result = await db.execute(
        select(CrmDeal).where(CrmDeal.id == uuid.UUID(deal_id), CrmDeal.tenant_id == user.tenant_id)
    )
    deal = result.scalar_one_or_none()
    if not deal:
        return {"error": "Deal not found"}
    if not deal.portal_offer_id:
        return {"error": "Create an offer first"}

    # Check if the offer already has a project on Portal
    offer = await portal_client.get_offer(deal.portal_offer_id)
    project_id = None
    if isinstance(offer, dict) and not offer.get("error"):
        project_id = offer.get("project_id") or offer.get("projectId")

    if project_id:
        deal.portal_project_id = project_id
        await db.commit()
        return {"project_id": project_id, "from": "existing_offer"}

    return {"error": "No project found for this offer. Create it manually on Portal."}
