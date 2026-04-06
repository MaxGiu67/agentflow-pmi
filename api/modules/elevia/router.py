"""Elevia router — use cases, scoring, bundles, ROI, discovery (US-208→US-210, US-220).

Prefix: /elevia
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from api.modules.elevia.service import EleviaService

router = APIRouter(prefix="/elevia", tags=["elevia"])


def _require_tenant(user: User) -> uuid.UUID:
    if not user.tenant_id:
        raise HTTPException(400, "Profilo azienda non configurato")
    return user.tenant_id


@router.get("/use-cases")
async def list_use_cases(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tid = _require_tenant(user)
    svc = EleviaService(db)
    return await svc.list_use_cases(tid)


@router.post("/score-prospect")
async def score_prospect(
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """US-209: Score a prospect based on ATECO, size, engagement."""
    tid = _require_tenant(user)
    svc = EleviaService(db)
    return await svc.score_prospect(
        tid,
        ateco_code=body.get("ateco_code", ""),
        employee_count=body.get("employee_count", 0),
        has_decision_maker=body.get("has_decision_maker", False),
        engagement_level=body.get("engagement_level", "low"),
    )


@router.get("/discovery-brief")
async def discovery_brief(
    ateco: str = Query(..., description="ATECO prefix (e.g. 25)"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """US-220: Pre-fill discovery brief for sector."""
    svc = EleviaService(db)
    return svc.get_discovery_brief(ateco)


@router.get("/roi")
async def calc_roi(
    use_case_count: int = Query(..., ge=1),
    hourly_cost: float = Query(35),
    elevia_annual_cost: float = Query(6000),
    user: User = Depends(get_current_user),
):
    """US-210: Calculate ROI estimate."""
    svc = EleviaService(None)
    return svc.calc_roi(use_case_count, hourly_cost=hourly_cost, elevia_annual_cost=elevia_annual_cost)
