"""Router for asset management (US-31, US-32)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from api.modules.assets.schemas import (
    AssetCheckRequest,
    AssetCreateRequest,
    AssetDisposeRequest,
    AssetDisposeResponse,
    AssetListResponse,
    AssetResponse,
    DepreciationRunRequest,
    DepreciationRunResponse,
)
from api.modules.assets.service import AssetService

router = APIRouter(prefix="/assets", tags=["assets"])


def get_service(db: AsyncSession = Depends(get_db)) -> AssetService:
    return AssetService(db)


@router.post("", response_model=AssetResponse)
async def create_asset(
    request: AssetCreateRequest,
    user: User = Depends(get_current_user),
    service: AssetService = Depends(get_service),
) -> AssetResponse:
    """Create a fixed asset.

    AC-31.1: Auto-create if amount > threshold
    AC-31.2: Set depreciation rate from ministerial tables
    AC-31.3: Unknown category -> suggest top 3
    AC-31.4: Used asset -> depreciable = gross
    """
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    try:
        result = await service.create_asset(
            tenant_id=user.tenant_id,
            description=request.description,
            category=request.category,
            purchase_date=request.purchase_date,
            purchase_amount=request.purchase_amount,
            is_used=request.is_used,
            invoice_id=request.invoice_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return AssetResponse(**result)


@router.get("", response_model=AssetListResponse)
async def list_assets(
    user: User = Depends(get_current_user),
    service: AssetService = Depends(get_service),
) -> AssetListResponse:
    """AC-32.1: List all assets (registro cespiti)."""
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    result = await service.list_assets(user.tenant_id)
    return AssetListResponse(**result)


@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset(
    asset_id: UUID,
    user: User = Depends(get_current_user),
    service: AssetService = Depends(get_service),
) -> AssetResponse:
    """Get single asset detail."""
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    try:
        result = await service.get_asset(asset_id, user.tenant_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    return AssetResponse(**result)


@router.post("/{asset_id}/dispose", response_model=AssetDisposeResponse)
async def dispose_asset(
    asset_id: UUID,
    request: AssetDisposeRequest,
    user: User = Depends(get_current_user),
    service: AssetService = Depends(get_service),
) -> AssetDisposeResponse:
    """Dispose of an asset.

    AC-32.2: Sale -> gain/loss + closing entries
    AC-32.3: Mid-year -> pro-rata depreciation
    AC-32.4: Scrapping/theft (price=0) -> loss = residual
    """
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    try:
        result = await service.dispose_asset(
            asset_id=asset_id,
            tenant_id=user.tenant_id,
            disposal_date=request.disposal_date,
            disposal_amount=request.disposal_amount,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return AssetDisposeResponse(**result)


@router.post("/depreciation/run", response_model=DepreciationRunResponse)
async def run_depreciation(
    request: DepreciationRunRequest,
    user: User = Depends(get_current_user),
    service: AssetService = Depends(get_service),
) -> DepreciationRunResponse:
    """AC-31.2: Run annual depreciation for all active assets."""
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    result = await service.run_depreciation(
        tenant_id=user.tenant_id,
        fiscal_year=request.fiscal_year,
    )

    return DepreciationRunResponse(**result)
