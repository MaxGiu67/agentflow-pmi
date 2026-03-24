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


@router.post("/auth/spid/init")
async def init_spid_auth(
    user: User = Depends(get_current_user),
    service: SpidService = Depends(get_spid_service),
) -> dict:
    """Start SPID/CIE authentication for cassetto fiscale.

    Returns session_id + QR code (for PosteID) or redirect_url (for mock).
    """
    return await service.init_spid_auth(user)


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


@router.get("/auth/spid/session/{session_id}")
async def get_spid_session(
    session_id: str,
    user: User = Depends(get_current_user),
    service: SpidService = Depends(get_spid_service),
) -> dict:
    """Check FiscoAPI session status (SPID auth progress)."""
    if not service.real_api:
        return {"stato": "mock", "message": "FiscoAPI non configurata"}
    try:
        return await service.real_api.get_session_status(session_id)
    except Exception as e:
        return {"stato": "errore", "message": str(e)}


@router.post("/auth/spid/session/{session_id}/otp")
async def send_spid_otp(
    session_id: str,
    body: dict,
    user: User = Depends(get_current_user),
    service: SpidService = Depends(get_spid_service),
) -> dict:
    """Send OTP code for SPID authentication."""
    if not service.real_api:
        return {"stato": "mock", "message": "FiscoAPI non configurata"}
    try:
        return await service.real_api.send_otp(session_id, body.get("codice_otp", ""))
    except Exception as e:
        return {"stato": "errore", "message": str(e)}


@router.post("/auth/spid/delegate", response_model=SpidInitResponse)
async def init_delegate_auth(
    request: SpidDelegateRequest,
    user: User = Depends(get_current_user),
    service: SpidService = Depends(get_spid_service),
) -> SpidInitResponse:
    """Start delegated SPID auth (commercialista accessing client's cassetto)."""
    data = await service.init_delegate_auth(user, request.delegante_cf)
    return SpidInitResponse(**data)
