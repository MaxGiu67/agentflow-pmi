"""Router for SDI webhook (US-07)."""

import uuid
from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import Tenant
from api.db.session import get_db
from api.modules.sdi.schemas import SDIWebhookPayload, SDIWebhookResponse
from api.modules.sdi.service import SDIService

router = APIRouter(tags=["sdi"])


def get_sdi_service(db: AsyncSession = Depends(get_db)) -> SDIService:
    return SDIService(db)


@router.post("/webhooks/sdi", response_model=SDIWebhookResponse)
async def sdi_webhook(
    payload: SDIWebhookPayload,
    x_tenant_id: str = Header(..., alias="X-Tenant-Id"),
    service: SDIService = Depends(get_sdi_service),
    db: AsyncSession = Depends(get_db),
) -> SDIWebhookResponse:
    """Receive invoice from A-Cube SDI webhook.

    No auth required - webhook from external service.
    Tenant is identified via X-Tenant-Id header (configured in A-Cube).
    """
    # Validate tenant exists
    try:
        tenant_id = uuid.UUID(x_tenant_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Tenant-Id non valido",
        )

    from sqlalchemy import select
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant non trovato",
        )

    try:
        data = await service.process_webhook(
            tenant_id=tenant_id,
            payload=payload.model_dump(),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from e

    return SDIWebhookResponse(**data)
