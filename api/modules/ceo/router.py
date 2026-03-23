"""Router for CEO Dashboard (US-39) and Budget (US-40)."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from api.modules.ceo.schemas import (
    AlertsResponse,
    BudgetCreateRequest,
    BudgetCreateResponse,
    BudgetListResponse,
    BudgetProjectionResponse,
    CEODashboardResponse,
    YoYResponse,
)
from api.modules.ceo.service import CEOService

router = APIRouter(prefix="/ceo", tags=["ceo"])


def get_service(db: AsyncSession = Depends(get_db)) -> CEOService:
    return CEOService(db)


# ============================================================
# US-39: Dashboard CEO — KPI
# ============================================================


@router.get("/dashboard", response_model=CEODashboardResponse)
async def get_dashboard(
    year: int | None = Query(None, description="Anno (default: corrente)"),
    month: int | None = Query(None, description="Mese (default: corrente)"),
    user: User = Depends(get_current_user),
    service: CEOService = Depends(get_service),
) -> CEODashboardResponse:
    """Get CEO Dashboard KPIs.

    AC-39.1: KPI principali.
    AC-39.3: DSO/DPO trend.
    AC-39.4: Data sufficiency note.
    """
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    result = await service.get_dashboard(user.tenant_id, year, month)
    return CEODashboardResponse(**result)


@router.get("/dashboard/yoy", response_model=YoYResponse)
async def get_yoy_comparison(
    year: int | None = Query(None, description="Anno corrente (default: corrente)"),
    user: User = Depends(get_current_user),
    service: CEOService = Depends(get_service),
) -> YoYResponse:
    """Year-over-year comparison.

    AC-39.2: Confronto anno precedente con variazione %.
    """
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    result = await service.get_yoy_comparison(user.tenant_id, year)
    return YoYResponse(**result)


@router.get("/alerts", response_model=AlertsResponse)
async def get_alerts(
    year: int | None = Query(None, description="Anno"),
    user: User = Depends(get_current_user),
    service: CEOService = Depends(get_service),
) -> AlertsResponse:
    """Get CEO alerts.

    AC-39.5: Concentrazione clienti (top 3 > 60%).
    """
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    result = await service.get_alerts(user.tenant_id, year)
    return AlertsResponse(**result)


# ============================================================
# US-40: Budget vs Consuntivo
# ============================================================


@router.get("/budget", response_model=BudgetListResponse)
async def get_budget(
    year: int = Query(..., description="Anno"),
    user: User = Depends(get_current_user),
    service: CEOService = Depends(get_service),
) -> BudgetListResponse:
    """Get budget vs consuntivo for a year.

    AC-40.1: Budget per categoria.
    AC-40.2: Confronto mensile.
    AC-40.4: No budget -> wizard.
    AC-40.5: Voci non previste.
    """
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    result = await service.get_budget(user.tenant_id, year)
    return BudgetListResponse(**result)


@router.post("/budget", response_model=BudgetCreateResponse)
async def create_budget(
    request: BudgetCreateRequest,
    user: User = Depends(get_current_user),
    service: CEOService = Depends(get_service),
) -> BudgetCreateResponse:
    """Create/update budget entries.

    AC-40.1: Inserimento budget mensile per categoria.
    """
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    result = await service.create_budget(
        user.tenant_id,
        request.year,
        request.month,
        request.entries,
    )
    return BudgetCreateResponse(**result)


@router.get("/budget/projection", response_model=BudgetProjectionResponse)
async def get_budget_projection(
    year: int = Query(..., description="Anno"),
    user: User = Depends(get_current_user),
    service: CEOService = Depends(get_service),
) -> BudgetProjectionResponse:
    """Get end-of-year projection with moving average.

    AC-40.3: Trend + proiezione fine anno.
    """
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    result = await service.get_projection(user.tenant_id, year)
    return BudgetProjectionResponse(**result)
