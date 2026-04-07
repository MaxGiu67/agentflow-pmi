"""Portal proxy router — reads from PortalJS.be via JWT (ADR-011, US-233).

Prefix: /portal
Tags: portal

All endpoints are read-only proxies. Writes (create project, assign resource)
are in separate endpoints that require human confirmation.
"""

from fastapi import APIRouter, Depends, Query

from api.db.models import User
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
    """Proxy: list persons from Portal."""
    result = await portal_client.get_persons(search=search, page=page, page_size=page_size)
    persons = result.get("data", [])
    return {
        "persons": [
            {
                "portal_id": p.get("id"),
                "first_name": p.get("firstName", ""),
                "last_name": p.get("lastName", ""),
                "full_name": f"{p.get('firstName', '')} {p.get('lastName', '')}".strip(),
                "email": p.get("privateEmail", ""),
                "fiscal_code": p.get("taxCode", ""),
                "employee_id": p.get("employee_id", ""),
            }
            for p in persons
        ],
        "total": result.get("total", len(persons)),
        "source": "portal",
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
