"""Router for fiscal deadlines / scadenzario (US-17, US-20)."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User, Tenant
from api.db.session import get_db
from api.middleware.auth import get_current_user
from api.modules.deadlines.schemas import DeadlinesResponse, FiscalAlertsResponse
from api.modules.deadlines.service import DeadlineService

router = APIRouter(tags=["deadlines"])


def get_deadline_service(db: AsyncSession = Depends(get_db)) -> DeadlineService:
    return DeadlineService(db)


@router.get("/deadlines", response_model=DeadlinesResponse)
async def get_deadlines(
    year: int = Query(default=None, description="Year for deadlines"),
    user: User = Depends(get_current_user),
    service: DeadlineService = Depends(get_deadline_service),
    db: AsyncSession = Depends(get_db),
) -> DeadlinesResponse:
    """Get fiscal deadlines based on tenant regime."""
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    # Get tenant regime
    from sqlalchemy import select
    result = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant non trovato",
        )

    if year is None:
        year = date.today().year

    try:
        data = service.get_deadlines(
            regime=tenant.regime_fiscale,
            year=year,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return DeadlinesResponse(**data)


@router.get("/deadlines/alerts", response_model=FiscalAlertsResponse)
async def get_fiscal_alerts(
    year: int = Query(default=None, description="Year for alerts"),
    user: User = Depends(get_current_user),
    service: DeadlineService = Depends(get_deadline_service),
    db: AsyncSession = Depends(get_db),
) -> FiscalAlertsResponse:
    """Get personalized fiscal alerts with estimated amounts (US-20)."""
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    from sqlalchemy import select
    result = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant non trovato",
        )

    if year is None:
        year = date.today().year

    try:
        data = await service.get_alerts(
            tenant_id=tenant.id,
            regime=tenant.regime_fiscale,
            year=year,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return FiscalAlertsResponse(**data)
