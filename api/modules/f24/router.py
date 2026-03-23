"""Router for F24 compilazione e generazione (US-38)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from api.modules.f24.schemas import (
    F24ExportResponse,
    F24GenerateRequest,
    F24GenerateResponse,
    F24ListResponse,
    F24Item,
    F24MarkPaidResponse,
)
from api.modules.f24.service import F24Service

router = APIRouter(prefix="/f24", tags=["f24"])


def get_service(db: AsyncSession = Depends(get_db)) -> F24Service:
    return F24Service(db)


@router.post("/generate", response_model=F24GenerateResponse)
async def generate_f24(
    request: F24GenerateRequest,
    user: User = Depends(get_current_user),
    service: F24Service = Depends(get_service),
) -> F24GenerateResponse:
    """Generate F24 for a period — aggregates IVA + ritenute + bollo.

    AC-38.1: F24 da liquidazione IVA.
    AC-38.2: F24 da ritenute.
    AC-38.3: FiscoAPI amount comparison.
    AC-38.4: Compensazione crediti IVA.
    """
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    result = await service.generate_f24(
        tenant_id=user.tenant_id,
        year=request.year,
        month=request.month,
        quarter=request.quarter,
        fisco_api_amount=request.fisco_api_amount,
    )
    return F24GenerateResponse(**result)


@router.get("", response_model=F24ListResponse)
async def list_f24(
    year: int | None = Query(None, description="Filtra per anno"),
    user: User = Depends(get_current_user),
    service: F24Service = Depends(get_service),
) -> F24ListResponse:
    """List all F24 documents."""
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    result = await service.list_f24(user.tenant_id, year)
    return F24ListResponse(**result)


@router.get("/{f24_id}", response_model=F24Item)
async def get_f24(
    f24_id: UUID,
    user: User = Depends(get_current_user),
    service: F24Service = Depends(get_service),
) -> F24Item:
    """Get F24 detail with sections."""
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    try:
        result = await service.get_f24(f24_id, user.tenant_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    return F24Item(**result)


@router.get("/{f24_id}/export", response_model=F24ExportResponse)
async def export_f24(
    f24_id: UUID,
    format: str = Query("pdf", description="Formato: pdf o telematico"),
    user: User = Depends(get_current_user),
    service: F24Service = Depends(get_service),
) -> F24ExportResponse:
    """Export F24 in PDF or telematico format.

    AC-38.1: Export PDF/telematico.
    """
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    try:
        result = await service.export_f24(f24_id, user.tenant_id, format)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    return F24ExportResponse(**result)


@router.patch("/{f24_id}/mark-paid", response_model=F24MarkPaidResponse)
async def mark_f24_paid(
    f24_id: UUID,
    user: User = Depends(get_current_user),
    service: F24Service = Depends(get_service),
) -> F24MarkPaidResponse:
    """Mark F24 as paid."""
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    try:
        result = await service.mark_paid(f24_id, user.tenant_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    return F24MarkPaidResponse(**result)
