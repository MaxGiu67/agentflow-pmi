"""Router for Controller Agent — Budget Wizard + Consuntivo + Summary (US-60, US-61, US-62)."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from api.modules.controller.service import ControllerService
from api.modules.controller.wizard_service import (
    check_historical_data,
    generate_ce_preview,
    get_sector_questions,
    get_sectors_list,
    load_wizard_budget,
    save_wizard_budget,
)

router = APIRouter(prefix="/controller", tags=["controller"])


def get_service(db: AsyncSession = Depends(get_db)) -> ControllerService:
    return ControllerService(db)


# ── Budget Wizard endpoints ──


@router.get("/budget/wizard/sectors")
async def wizard_sectors(
    user: User = Depends(get_current_user),
) -> list[dict]:
    """List available sectors for the budget wizard."""
    return get_sectors_list()


@router.get("/budget/wizard/questions")
async def wizard_questions(
    sector: str = Query(..., description="Sector ID (e.g., 'it', 'ristorazione')"),
    user: User = Depends(get_current_user),
) -> dict:
    """Get sector-specific questions and cost structure."""
    result = get_sector_questions(sector)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/budget/wizard/history")
async def wizard_history(
    year: int = Query(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Check if tenant has historical data for the budget year."""
    if not user.tenant_id:
        raise HTTPException(status_code=400, detail="Profilo azienda non configurato")
    return await check_historical_data(db, user.tenant_id, year)


class WizardGenerateRequest(BaseModel):
    sector_id: str
    fatturato: float
    n_dipendenti: int = 0
    ral_media: float = 0
    year: int
    overrides: dict[str, float] | None = None
    costo_personale_diretto: float | None = None
    custom_costs: list[dict[str, Any]] | None = None
    extra_revenues: list[dict[str, Any]] | None = None


@router.post("/budget/wizard/generate")
async def wizard_generate(
    request: WizardGenerateRequest,
    user: User = Depends(get_current_user),
) -> dict:
    """Generate CE previsionale from wizard inputs."""
    result = generate_ce_preview(
        sector_id=request.sector_id,
        fatturato=request.fatturato,
        n_dipendenti=request.n_dipendenti,
        ral_media=request.ral_media,
        year=request.year,
        overrides=request.overrides,
        costo_personale_diretto=request.costo_personale_diretto,
        custom_costs=request.custom_costs,
        extra_revenues=request.extra_revenues,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


class WizardSaveRequest(BaseModel):
    year: int
    budget_lines: list[dict[str, Any]]
    meta: dict[str, Any] | None = None


@router.post("/budget/wizard/save")
async def wizard_save(
    request: WizardSaveRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Save budget from wizard CE preview."""
    if not user.tenant_id:
        raise HTTPException(status_code=400, detail="Profilo azienda non configurato")
    return await save_wizard_budget(
        db, user.tenant_id, request.year, request.budget_lines, request.meta
    )


@router.get("/budget/wizard/load")
async def wizard_load(
    year: int = Query(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Load saved budget for re-editing in wizard."""
    if not user.tenant_id:
        raise HTTPException(status_code=400, detail="Profilo azienda non configurato")
    return await load_wizard_budget(db, user.tenant_id, year)


@router.get("/budget/categories")
async def budget_categories(
    year: int = Query(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get budget categories for a year, grouped by type (revenue/cost).

    Used to populate category dropdowns in invoice creation and expense forms.
    """
    if not user.tenant_id:
        raise HTTPException(status_code=400, detail="Profilo azienda non configurato")

    from api.db.models import Budget
    from sqlalchemy import select, distinct

    result = await db.execute(
        select(distinct(Budget.category), Budget.label).where(
            Budget.tenant_id == user.tenant_id,
            Budget.year == year,
            Budget.month == 1,  # all months have same categories
        )
    )
    rows = result.fetchall()

    revenues = []
    costs = []
    for row in rows:
        cat_id = row[0]
        label = row[1] or cat_id
        entry = {"id": cat_id, "label": label}
        if cat_id.startswith("ricavi"):
            revenues.append(entry)
        else:
            costs.append(entry)

    return {
        "year": year,
        "revenues": revenues,
        "costs": costs,
        "all": revenues + costs,
    }


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


# ── US-63: Cost Analysis — "Dove perdo soldi?" ──

@router.get("/cost-analysis")
async def cost_analysis(
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    user: User = Depends(get_current_user),
    service: ControllerService = Depends(get_service),
) -> dict:
    """Cost analysis — top 5 categories, comparison with prev period, anomalies (US-63)."""
    if not user.tenant_id:
        raise HTTPException(status_code=400, detail="Profilo azienda non configurato")
    return await service.cost_analysis(user.tenant_id, year, month)
