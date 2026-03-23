"""Router for Certificazione Unica (CU) annuale (US-34)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from api.modules.cu.schemas import (
    CUExportResponse,
    CUGenerateResponse,
    CUListResponse,
)
from api.modules.cu.service import CUService

router = APIRouter(prefix="/cu", tags=["cu"])


def get_service(db: AsyncSession = Depends(get_db)) -> CUService:
    return CUService(db)


@router.get("", response_model=CUListResponse)
async def list_cu(
    year: int = Query(..., description="Anno di riferimento"),
    user: User = Depends(get_current_user),
    service: CUService = Depends(get_service),
) -> CUListResponse:
    """List all CU records for a given year.

    AC-34.1: Lista CU per anno con compensi lordi, ritenute, netto.
    """
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    result = await service.list_cu(user.tenant_id, year)
    return CUListResponse(**result)


@router.post("/generate/{year}", response_model=CUGenerateResponse)
async def generate_cu(
    year: int,
    user: User = Depends(get_current_user),
    service: CUService = Depends(get_service),
) -> CUGenerateResponse:
    """Generate CU for all professionals paid in the given year.

    AC-34.1: Genera CU per ogni professionista pagato.
    AC-34.3: Ritenute non tutte versate -> warning.
    AC-34.4: Contributo INPS 4% indicato separatamente.
    """
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    result = await service.generate_cu(user.tenant_id, year)
    return CUGenerateResponse(**result)


@router.get("/{cu_id}/export", response_model=CUExportResponse)
async def export_cu(
    cu_id: UUID,
    format: str = Query("csv", description="Formato: csv o telematico"),
    user: User = Depends(get_current_user),
    service: CUService = Depends(get_service),
) -> CUExportResponse:
    """Export a CU record in CSV or telematico format.

    AC-34.2: Export formato telematico/CSV.
    """
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    try:
        result = await service.export_cu(cu_id, user.tenant_id, format)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    return CUExportResponse(**result)
