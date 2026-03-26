"""Router for payroll/personnel costs (US-44)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from api.modules.payroll.schemas import (
    PayrollCostCreate,
    PayrollCostListResponse,
    PayrollCostResponse,
    PayrollSummaryResponse,
)
from api.modules.payroll.service import PayrollService

router = APIRouter(prefix="/payroll", tags=["payroll"])


def get_service(db: AsyncSession = Depends(get_db)) -> PayrollService:
    return PayrollService(db)


@router.post("", response_model=PayrollCostResponse, status_code=status.HTTP_201_CREATED)
async def create_payroll_cost(
    request: PayrollCostCreate,
    user: User = Depends(get_current_user),
    service: PayrollService = Depends(get_service),
) -> PayrollCostResponse:
    """Create a payroll cost entry (cedolino/stipendio)."""
    if not user.tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Profilo azienda non configurato")
    result = await service.create(user.tenant_id, request.model_dump())
    return PayrollCostResponse(**result)


@router.get("", response_model=PayrollCostListResponse)
async def list_payroll_costs(
    year: int | None = None,
    month: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    service: PayrollService = Depends(get_service),
) -> PayrollCostListResponse:
    """List payroll costs with optional year/month filter."""
    if not user.tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Profilo azienda non configurato")
    data = await service.list_costs(user.tenant_id, year=year, month=month, page=page, page_size=page_size)
    return PayrollCostListResponse(
        items=[PayrollCostResponse(**i) for i in data["items"]],
        total=data["total"],
    )


@router.get("/summary", response_model=PayrollSummaryResponse)
async def get_payroll_summary(
    year: int = Query(..., description="Anno di riferimento"),
    user: User = Depends(get_current_user),
    service: PayrollService = Depends(get_service),
) -> PayrollSummaryResponse:
    """Get yearly payroll summary with monthly breakdown."""
    if not user.tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Profilo azienda non configurato")
    data = await service.get_summary(user.tenant_id, year)
    return PayrollSummaryResponse(**data)


@router.delete("/{cost_id}")
async def delete_payroll_cost(
    cost_id: UUID,
    user: User = Depends(get_current_user),
    service: PayrollService = Depends(get_service),
) -> dict:
    """Delete a payroll cost entry."""
    if not user.tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Profilo azienda non configurato")
    try:
        return await service.delete(user.tenant_id, cost_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
