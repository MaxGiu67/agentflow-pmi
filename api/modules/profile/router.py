from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from api.modules.profile.schemas import (
    InvoiceSettingsRequest,
    InvoiceSettingsResponse,
    ProfileChangeWarning,
    ProfileResponse,
    ProfileUpdateRequest,
)
from api.modules.profile.service import ProfileService

router = APIRouter(prefix="/profile", tags=["profile"])


def get_profile_service(db: AsyncSession = Depends(get_db)) -> ProfileService:
    return ProfileService(db)


@router.get("", response_model=ProfileResponse)
async def get_profile(
    user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> ProfileResponse:
    data = await service.get_profile(user)
    return ProfileResponse(**data)


@router.patch("", response_model=ProfileResponse)
async def update_profile(
    request: ProfileUpdateRequest,
    confirm: bool = Query(False, description="Conferma modifica piano conti"),
    user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> ProfileResponse:
    # Check if change requires confirmation (AC-02.4)
    if not confirm and (request.tipo_azienda or request.regime_fiscale):
        warning = await service.check_profile_change_impact(
            user,
            tipo_azienda=request.tipo_azienda.value if request.tipo_azienda else None,
            regime_fiscale=request.regime_fiscale.value if request.regime_fiscale else None,
        )
        if warning:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=warning,
            )

    try:
        data = await service.update_profile(
            user,
            name=request.name,
            tipo_azienda=request.tipo_azienda.value if request.tipo_azienda else None,
            regime_fiscale=request.regime_fiscale.value if request.regime_fiscale else None,
            piva=request.piva,
            codice_ateco=request.codice_ateco,
            azienda_nome=request.azienda_nome,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return ProfileResponse(**data)


# ── Impostazioni Fatturazione (US-42) ──


@router.get("/invoice-settings", response_model=InvoiceSettingsResponse)
async def get_invoice_settings(
    user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> InvoiceSettingsResponse:
    """Get invoice settings (IBAN, sede, regime fiscale SDI, pagamento)."""
    try:
        data = await service.get_invoice_settings(user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return InvoiceSettingsResponse(**data)


@router.patch("/invoice-settings", response_model=InvoiceSettingsResponse)
async def update_invoice_settings(
    request: InvoiceSettingsRequest,
    user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> InvoiceSettingsResponse:
    """Update invoice settings. Only provided fields are updated."""
    try:
        data = await service.update_invoice_settings(
            user, request.model_dump(exclude_none=True),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return InvoiceSettingsResponse(**data)
