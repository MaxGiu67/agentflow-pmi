"""Router A-Cube Open Banking (Pivot 11 Sprint 48 US-OB-04).

Endpoint esposti sotto `/api/v1/banking/connections`.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from api.modules.banking.acube_ob_schemas import (
    BankConnectionListResponse,
    BankConnectionResponse,
    InitConnectionRequest,
    InitConnectionResponse,
    SyncNowResponse,
)
from api.modules.banking.acube_ob_service import (
    ACubeOBServiceError,
    ACubeOpenBankingService,
)

router = APIRouter(prefix="/banking/connections", tags=["banking-openbanking"])


def get_service(db: AsyncSession = Depends(get_db)) -> ACubeOpenBankingService:
    return ACubeOpenBankingService(db)


def _require_tenant(user: User) -> UUID:
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato per l'utente corrente",
        )
    return user.tenant_id


@router.post("/init", response_model=InitConnectionResponse)
async def init_connection(
    body: InitConnectionRequest,
    user: User = Depends(get_current_user),
    service: ACubeOpenBankingService = Depends(get_service),
) -> InitConnectionResponse:
    """Avvia flusso PSD2 Connect — crea BR su A-Cube se mancante.

    ⚠️ Generate fee su A-Cube al primo call per fiscal_id nuovo.
    """
    tenant_id = _require_tenant(user)
    try:
        result = await service.init_connection(
            tenant_id=tenant_id,
            return_url=body.return_url,
            fiscal_id=body.fiscal_id,
        )
    except ACubeOBServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    return InitConnectionResponse(**result)


@router.get("", response_model=BankConnectionListResponse)
async def list_connections(
    user: User = Depends(get_current_user),
    service: ACubeOpenBankingService = Depends(get_service),
) -> BankConnectionListResponse:
    tenant_id = _require_tenant(user)
    items = await service.list_connections(tenant_id)
    return BankConnectionListResponse(
        items=[BankConnectionResponse.model_validate(c) for c in items],
        total=len(items),
    )


@router.get("/{connection_id}", response_model=BankConnectionResponse)
async def get_connection(
    connection_id: UUID,
    user: User = Depends(get_current_user),
    service: ACubeOpenBankingService = Depends(get_service),
) -> BankConnectionResponse:
    tenant_id = _require_tenant(user)
    try:
        conn = await service.get_connection(connection_id, tenant_id)
    except ACubeOBServiceError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return BankConnectionResponse.model_validate(conn)


@router.post("/{connection_id}/sync-now", response_model=SyncNowResponse)
async def sync_now(
    connection_id: UUID,
    user: User = Depends(get_current_user),
    service: ACubeOpenBankingService = Depends(get_service),
) -> SyncNowResponse:
    tenant_id = _require_tenant(user)
    try:
        result = await service.sync_now(connection_id, tenant_id)
    except ACubeOBServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return SyncNowResponse(**result)
