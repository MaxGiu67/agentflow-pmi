"""Scarico Massivo Cassetto Fiscale router."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from api.modules.scarico_massivo.schemas import (
    ClientRegisterRequest,
    ConfigListResponse,
    ConfigResponse,
    DelegaGuideResponse,
    InvoiceLogListResponse,
    InvoiceLogResponse,
    SyncRequest,
    SyncResponse,
)
from api.modules.scarico_massivo.service import (
    ScaricoMassivoService,
    ScaricoMassivoServiceError,
)

router = APIRouter(prefix="/scarico-massivo", tags=["scarico-massivo"])


def get_service(db: AsyncSession = Depends(get_db)) -> ScaricoMassivoService:
    return ScaricoMassivoService(db)


def _require_tenant(user: User) -> UUID:
    if not user.tenant_id:
        raise HTTPException(status_code=400, detail="Profilo azienda non configurato")
    return user.tenant_id


@router.get("/delega-guide", response_model=DelegaGuideResponse)
async def delega_guide() -> DelegaGuideResponse:
    """Step-by-step procedure to delegate A-Cube on AdE portal (proxy mode)."""
    return DelegaGuideResponse(**ScaricoMassivoService.get_delega_guide())


@router.get("/configs", response_model=ConfigListResponse)
async def list_configs(
    user: User = Depends(get_current_user),
    service: ScaricoMassivoService = Depends(get_service),
) -> ConfigListResponse:
    tenant_id = _require_tenant(user)
    items = await service.list_configs(tenant_id)
    return ConfigListResponse(
        items=[ConfigResponse.model_validate(c) for c in items],
        total=len(items),
    )


@router.post("/configs", response_model=ConfigResponse, status_code=status.HTTP_201_CREATED)
async def register_client(
    body: ClientRegisterRequest,
    user: User = Depends(get_current_user),
    service: ScaricoMassivoService = Depends(get_service),
) -> ConfigResponse:
    tenant_id = _require_tenant(user)
    try:
        cfg = await service.register_client(
            tenant_id=tenant_id,
            client_fiscal_id=body.client_fiscal_id,
            client_name=body.client_name,
            onboarding_mode=body.onboarding_mode,
        )
    except ScaricoMassivoServiceError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return ConfigResponse.model_validate(cfg)


@router.get("/configs/{config_id}", response_model=ConfigResponse)
async def get_config(
    config_id: UUID,
    user: User = Depends(get_current_user),
    service: ScaricoMassivoService = Depends(get_service),
) -> ConfigResponse:
    tenant_id = _require_tenant(user)
    cfg = await service.get_config(config_id, tenant_id)
    if not cfg:
        raise HTTPException(status_code=404, detail="Configurazione non trovata")
    return ConfigResponse.model_validate(cfg)


@router.delete("/configs/{config_id}")
async def delete_config(
    config_id: UUID,
    user: User = Depends(get_current_user),
    service: ScaricoMassivoService = Depends(get_service),
) -> Response:
    tenant_id = _require_tenant(user)
    ok = await service.delete_config(config_id, tenant_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Configurazione non trovata")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/configs/{config_id}/sync", response_model=SyncResponse)
async def sync_now(
    config_id: UUID,
    body: SyncRequest | None = None,
    user: User = Depends(get_current_user),
    service: ScaricoMassivoService = Depends(get_service),
) -> SyncResponse:
    tenant_id = _require_tenant(user)
    body = body or SyncRequest()
    try:
        result = await service.sync_now(
            config_id=config_id,
            tenant_id=tenant_id,
            since=body.since,
            until=body.until,
            direction=body.direction,
        )
    except ScaricoMassivoServiceError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    return SyncResponse(**result)


@router.get("/configs/{config_id}/invoices", response_model=InvoiceLogListResponse)
async def list_downloaded_invoices(
    config_id: UUID,
    limit: int = Query(100, ge=1, le=500),
    user: User = Depends(get_current_user),
    service: ScaricoMassivoService = Depends(get_service),
) -> InvoiceLogListResponse:
    tenant_id = _require_tenant(user)
    items = await service.list_invoice_log(tenant_id, config_id=config_id, limit=limit)
    return InvoiceLogListResponse(
        items=[InvoiceLogResponse.model_validate(i) for i in items],
        total=len(items),
    )
