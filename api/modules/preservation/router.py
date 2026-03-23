"""Router for digital preservation (conservazione digitale a norma) (US-37)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from api.modules.preservation.schemas import (
    PreservationBatchResponse,
    PreservationListResponse,
    PreservationStatusResponse,
)
from api.modules.preservation.service import PreservationService

router = APIRouter(prefix="/preservation", tags=["preservation"])


def get_service(db: AsyncSession = Depends(get_db)) -> PreservationService:
    return PreservationService(db)


@router.get("", response_model=PreservationListResponse)
async def list_preservation(
    user: User = Depends(get_current_user),
    service: PreservationService = Depends(get_service),
) -> PreservationListResponse:
    """List all preservation records with status summary.

    AC-37.2: Verifica stato (conservati, in attesa, errori).
    """
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    result = await service.list_preservation(user.tenant_id)
    return PreservationListResponse(**result)


@router.post("/batch", response_model=PreservationBatchResponse)
async def send_batch(
    provider: str = Query("aruba", description="Provider: aruba o infocert"),
    user: User = Depends(get_current_user),
    service: PreservationService = Depends(get_service),
) -> PreservationBatchResponse:
    """Send batch of documents to preservation provider.

    AC-37.1: Invio automatico batch giornaliero a provider.
    AC-37.3: Provider non raggiungibile -> retry backoff.
    """
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    result = await service.send_batch(user.tenant_id, provider)
    return PreservationBatchResponse(**result)


@router.post("/check-status", response_model=PreservationStatusResponse)
async def check_status(
    user: User = Depends(get_current_user),
    service: PreservationService = Depends(get_service),
) -> PreservationStatusResponse:
    """Check preservation status for all sent documents.

    AC-37.2: Verifica stato (conservati, in attesa, errori).
    AC-37.4: Pacchetto rifiutato -> conservazione rifiutata con motivo.
    """
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    result = await service.check_status(user.tenant_id)
    return PreservationStatusResponse(**result)


@router.post("/credit-note/{credit_note_id}")
async def send_credit_note(
    credit_note_id: UUID,
    provider: str = Query("aruba", description="Provider: aruba o infocert"),
    user: User = Depends(get_current_user),
    service: PreservationService = Depends(get_service),
) -> dict:
    """Send credit note linked to preserved invoice.

    AC-37.5: Nota credito post-conservazione -> invia anche NC collegata.
    """
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    try:
        result = await service.send_credit_note(
            user.tenant_id, credit_note_id, provider,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    return result
