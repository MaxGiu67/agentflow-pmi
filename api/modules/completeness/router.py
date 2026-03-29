"""Router for completeness score (US-69) and import exceptions (US-71)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from api.modules.completeness.service import CompletenessService
from api.modules.completeness.exceptions_service import ImportExceptionsService

router = APIRouter(prefix="/completeness-score", tags=["completeness"])


def get_service(db: AsyncSession = Depends(get_db)) -> CompletenessService:
    return CompletenessService(db)


def get_exceptions_service(db: AsyncSession = Depends(get_db)) -> ImportExceptionsService:
    return ImportExceptionsService(db)


@router.get("")
async def get_completeness_score(
    user: User = Depends(get_current_user),
    service: CompletenessService = Depends(get_service),
) -> dict:
    """Get completeness score for the current tenant (US-69)."""
    if not user.tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Profilo azienda non configurato")
    return await service.get_score(user.tenant_id)


# ── Import Exceptions (US-71) ──

@router.get("/exceptions")
async def get_import_exceptions(
    user: User = Depends(get_current_user),
    service: ImportExceptionsService = Depends(get_exceptions_service),
) -> dict:
    """Get pending import exceptions — max 3 visible (US-71).

    Returns the most urgent exceptions (by severity) with total count.
    If more than 3 pending, shows 'has_more: true' with remaining count.
    """
    if not user.tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Profilo azienda non configurato")
    return await service.get_pending(user.tenant_id)


@router.get("/exceptions/all")
async def get_all_import_exceptions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    service: ImportExceptionsService = Depends(get_exceptions_service),
) -> dict:
    """Get all pending import exceptions — full backlog (US-71)."""
    if not user.tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Profilo azienda non configurato")
    return await service.get_all_pending(user.tenant_id, page=page, page_size=page_size)


@router.post("/exceptions/{exception_id}/resolve")
async def resolve_exception(
    exception_id: UUID,
    user: User = Depends(get_current_user),
    service: ImportExceptionsService = Depends(get_exceptions_service),
) -> dict:
    """Mark an import exception as resolved (US-71)."""
    if not user.tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Profilo azienda non configurato")
    ok = await service.resolve(user.tenant_id, exception_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Eccezione non trovata")
    return {"resolved": True}
