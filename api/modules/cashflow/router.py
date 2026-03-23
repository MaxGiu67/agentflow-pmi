"""Router for cash flow prediction (US-25)."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from api.modules.cashflow.schemas import (
    CashFlowAlertsResponse,
    CashFlowPredictionResponse,
)
from api.modules.cashflow.service import CashFlowService

router = APIRouter(prefix="/cashflow", tags=["cashflow"])


def get_service(db: AsyncSession = Depends(get_db)) -> CashFlowService:
    return CashFlowService(db)


@router.get("/prediction", response_model=CashFlowPredictionResponse)
async def get_cashflow_prediction(
    days: int = Query(default=90, ge=1, le=365, description="Prediction horizon in days"),
    user: User = Depends(get_current_user),
    service: CashFlowService = Depends(get_service),
) -> CashFlowPredictionResponse:
    """Get cash flow prediction for the next N days.

    AC-25.1: Graph with current balance + expected income/expenses + projected balance.
    AC-25.3: Insufficient data -> show available + warning.
    AC-25.4: Stale bank data -> banner warning.
    """
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    result = await service.predict(tenant_id=user.tenant_id, days=days)
    return CashFlowPredictionResponse(**result)


@router.get("/alerts", response_model=CashFlowAlertsResponse)
async def get_cashflow_alerts(
    soglia: float | None = Query(
        default=None,
        description="Critical threshold in EUR (default: 5000)",
    ),
    days: int = Query(default=90, ge=1, le=365),
    user: User = Depends(get_current_user),
    service: CashFlowService = Depends(get_service),
) -> CashFlowAlertsResponse:
    """Get cash flow alerts.

    AC-25.2: Alert on critical balance threshold (default 5000 EUR, configurable).
    AC-25.5: Late payments highlighted with optimistic/pessimistic scenarios.
    """
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    result = await service.get_alerts(
        tenant_id=user.tenant_id,
        soglia_critica=soglia,
        days=days,
    )
    return CashFlowAlertsResponse(**result)
