from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.adapters.fiscoapi import FiscoAPIClient
from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from api.modules.spid.schemas import (
    SpidCallbackResponse,
    SpidDelegateRequest,
    SpidErrorResponse,
    SpidInitResponse,
    SpidStatusResponse,
)
from api.modules.spid.service import SpidService

router = APIRouter(tags=["spid"])


def get_spid_service(db: AsyncSession = Depends(get_db)) -> SpidService:
    return SpidService(db)


@router.post("/auth/spid/init", response_model=SpidInitResponse)
async def init_spid_auth(
    user: User = Depends(get_current_user),
    service: SpidService = Depends(get_spid_service),
) -> SpidInitResponse:
    """Start SPID/CIE authentication for cassetto fiscale."""
    data = await service.init_spid_auth(user)
    return SpidInitResponse(**data)


@router.get("/auth/spid/callback", response_model=SpidCallbackResponse)
async def spid_callback(
    code: str = Query(...),
    state: str = Query(""),
    user: User = Depends(get_current_user),
    service: SpidService = Depends(get_spid_service),
) -> SpidCallbackResponse:
    """Handle SPID callback after user authenticates."""
    data = await service.handle_spid_callback(code, state, user)
    return SpidCallbackResponse(**data)


@router.get("/cassetto/status", response_model=SpidStatusResponse)
async def cassetto_status(
    user: User = Depends(get_current_user),
    service: SpidService = Depends(get_spid_service),
) -> SpidStatusResponse:
    """Get cassetto fiscale connection status."""
    data = await service.get_spid_status(user)
    return SpidStatusResponse(**data)


@router.get("/cassetto/no-spid", response_model=SpidErrorResponse)
async def no_spid_info(
    service: SpidService = Depends(get_spid_service),
) -> SpidErrorResponse:
    """Info for users without SPID/CIE — how to get it + alternatives."""
    data = await service.get_no_spid_info()
    return SpidErrorResponse(**data)


@router.post("/auth/spid/delegate", response_model=SpidInitResponse)
async def init_delegate_auth(
    request: SpidDelegateRequest,
    user: User = Depends(get_current_user),
    service: SpidService = Depends(get_spid_service),
) -> SpidInitResponse:
    """Start delegated SPID auth (commercialista accessing client's cassetto)."""
    data = await service.init_delegate_auth(user, request.delegante_cf)
    return SpidInitResponse(**data)
