"""Router for ammortamenti auto (US-59)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from api.modules.ammortamenti.service import AmmortamentiService

router = APIRouter(prefix="/assets", tags=["ammortamenti"])


def get_service(db: AsyncSession = Depends(get_db)) -> AmmortamentiService:
    return AmmortamentiService(db)


@router.post("/auto-detect")
async def auto_detect_assets(
    user: User = Depends(get_current_user),
    service: AmmortamentiService = Depends(get_service),
) -> dict:
    """Scan invoices for immobilizzazioni and propose depreciation (US-59)."""
    if not user.tenant_id:
        raise HTTPException(status_code=400, detail="Profilo azienda non configurato")

    return await service.auto_detect(user.tenant_id)


class ConfirmAssetRequest(BaseModel):
    invoice_id: UUID
    depreciation_rate: float


@router.post("/confirm")
async def confirm_asset(
    request: ConfirmAssetRequest,
    user: User = Depends(get_current_user),
    service: AmmortamentiService = Depends(get_service),
) -> dict:
    """Confirm an invoice as a fixed asset (US-59)."""
    if not user.tenant_id:
        raise HTTPException(status_code=400, detail="Profilo azienda non configurato")

    try:
        return await service.confirm_asset(
            user.tenant_id, request.invoice_id, request.depreciation_rate,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
