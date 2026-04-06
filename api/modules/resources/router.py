"""Resources router — CRUD + matching + bench (US-204→US-207).

Prefix: /resources
"""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from api.modules.resources.service import ResourceService

router = APIRouter(prefix="/resources", tags=["resources"])


def _require_tenant(user: User) -> uuid.UUID:
    if not user.tenant_id:
        raise HTTPException(400, "Profilo azienda non configurato")
    return user.tenant_id


@router.get("")
async def list_resources(
    seniority: str = Query(""),
    skill: str = Query(""),
    available_only: bool = Query(False),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tid = _require_tenant(user)
    svc = ResourceService(db)
    return await svc.list_resources(tid, seniority=seniority, skill=skill, available_only=available_only)


@router.post("", status_code=201)
async def create_resource(
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tid = _require_tenant(user)
    svc = ResourceService(db)
    result = await svc.create_resource(tid, body)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.get("/bench")
async def get_bench(
    days: int = Query(30, ge=1, le=180),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """US-207: Resources becoming available within N days."""
    tid = _require_tenant(user)
    svc = ResourceService(db)
    return await svc.get_bench(tid, days_ahead=days)


@router.get("/match")
async def match_resources(
    tech_stack: str = Query("", description="Comma-separated: Java,Spring,Angular"),
    seniority: str = Query(""),
    limit: int = Query(5, ge=1, le=20),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """US-205: Match client request with available resources."""
    tid = _require_tenant(user)
    svc = ResourceService(db)
    stack = [s.strip() for s in tech_stack.split(",") if s.strip()] if tech_stack else []
    return await svc.match_resources(tid, tech_stack=stack, seniority=seniority, limit=limit)


@router.get("/margin")
async def calc_margin(
    daily_rate: float = Query(..., gt=0),
    daily_cost: float = Query(..., ge=0),
    user: User = Depends(get_current_user),
):
    """US-206: Calculate margin for T&M offer."""
    svc = ResourceService(None)  # No DB needed
    return svc.calc_margin(daily_rate, daily_cost)


@router.get("/{resource_id}")
async def get_resource(
    resource_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = ResourceService(db)
    result = await svc.get_resource(resource_id)
    if not result:
        raise HTTPException(404, "Risorsa non trovata")
    return result


@router.patch("/{resource_id}")
async def update_resource(
    resource_id: uuid.UUID,
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = ResourceService(db)
    result = await svc.update_resource(resource_id, body)
    if not result:
        raise HTTPException(404, "Risorsa non trovata")
    return result


@router.post("/{resource_id}/skills", status_code=201)
async def add_skill(
    resource_id: uuid.UUID,
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = ResourceService(db)
    return await svc.add_skill(resource_id, body)


@router.delete("/{resource_id}/skills/{skill_id}")
async def remove_skill(
    skill_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = ResourceService(db)
    ok = await svc.remove_skill(skill_id)
    if not ok:
        raise HTTPException(404, "Skill non trovata")
    return {"status": "deleted"}
