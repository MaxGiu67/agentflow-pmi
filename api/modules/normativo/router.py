"""Router for normativo module (US-28)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from api.modules.normativo.schemas import (
    NormativeAlertListResponse,
    NormativeCheckResponse,
)
from api.modules.normativo.service import NormativoService

router = APIRouter(prefix="/normativo", tags=["normativo"])


def get_service(db: AsyncSession = Depends(get_db)) -> NormativoService:
    return NormativoService(db)


@router.get("/alerts", response_model=NormativeAlertListResponse)
async def list_alerts(
    user: User = Depends(get_current_user),
    service: NormativoService = Depends(get_service),
) -> NormativeAlertListResponse:
    """List all normative alerts.

    AC-28.1: Alert su circolare AdE.
    """
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    result = await service.list_alerts(user.tenant_id)
    return NormativeAlertListResponse(**result)


@router.post("/check", response_model=NormativeCheckResponse)
async def check_feed(
    user: User = Depends(get_current_user),
    service: NormativoService = Depends(get_service),
) -> NormativeCheckResponse:
    """Force check RSS feed for normative updates.

    AC-28.1: Alert su circolari.
    AC-28.2: Propone aggiornamento regole con preview impatto.
    AC-28.3: Feed non disponibile -> retry backoff.
    AC-28.4: Norma con decorrenza futura -> schedula.
    """
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    result = await service.check_feed(user.tenant_id)
    return NormativeCheckResponse(**result)
