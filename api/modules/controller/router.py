"""Router for Controller Agent — Budget + Consuntivo + Summary (US-60, US-61, US-62)."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from api.modules.controller.service import ControllerService

router = APIRouter(prefix="/controller", tags=["controller"])


def get_service(db: AsyncSession = Depends(get_db)) -> ControllerService:
    return ControllerService(db)


# ── US-60: Budget Agent generate ──

@router.post("/budget/generate")
async def generate_budget(
    year: int = Query(...),
    growth_rate: float = Query(0.05, ge=-0.5, le=1.0),
    user: User = Depends(get_current_user),
    service: ControllerService = Depends(get_service),
) -> dict:
    """Generate budget proposal from historical data (US-60).

    The agent proposes budget based on previous year actuals + growth rate.
    """
    if not user.tenant_id:
        raise HTTPException(status_code=400, detail="Profilo azienda non configurato")
    return await service.generate_budget_proposal(user.tenant_id, year, growth_rate)


class SaveBudgetRequest(BaseModel):
    year: int
    lines: list[dict[str, Any]]


@router.post("/budget/save")
async def save_budget(
    request: SaveBudgetRequest,
    user: User = Depends(get_current_user),
    service: ControllerService = Depends(get_service),
) -> dict:
    """Save budget lines (US-60)."""
    if not user.tenant_id:
        raise HTTPException(status_code=400, detail="Profilo azienda non configurato")
    return await service.save_budget(user.tenant_id, request.year, request.lines)


# ── US-61: Budget vs Consuntivo ──

@router.get("/budget/vs-actual")
async def budget_vs_actual(
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    user: User = Depends(get_current_user),
    service: ControllerService = Depends(get_service),
) -> dict:
    """Compare budget vs actual for a specific month (US-61)."""
    if not user.tenant_id:
        raise HTTPException(status_code=400, detail="Profilo azienda non configurato")
    return await service.get_budget_vs_actual(user.tenant_id, year, month)


# ── US-62: "Come sto andando?" ──

@router.get("/summary")
async def get_summary(
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    user: User = Depends(get_current_user),
    service: ControllerService = Depends(get_service),
) -> dict:
    """Executive summary — 'Come sto andando?' (US-62).

    Returns: ricavi, costi, margine, trend vs mese precedente,
    budget comparison, top costs, anomalies.
    """
    if not user.tenant_id:
        raise HTTPException(status_code=400, detail="Profilo azienda non configurato")
    return await service.get_summary(user.tenant_id, year, month)
