"""Router for active invoices / fatturazione attiva SDI (US-21)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from api.modules.active_invoices.schemas import (
    ActiveInvoiceCreate,
    ActiveInvoiceListResponse,
    ActiveInvoiceResponse,
    ActiveInvoiceSendResponse,
    ActiveInvoiceStatusResponse,
)
from api.modules.active_invoices.service import ActiveInvoiceService

router = APIRouter(prefix="/invoices/active", tags=["active_invoices"])


def get_service(db: AsyncSession = Depends(get_db)) -> ActiveInvoiceService:
    return ActiveInvoiceService(db)


@router.post("", response_model=ActiveInvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_active_invoice(
    request: ActiveInvoiceCreate,
    user: User = Depends(get_current_user),
    service: ActiveInvoiceService = Depends(get_service),
) -> ActiveInvoiceResponse:
    """Create a new active invoice (fattura attiva).

    Generates XML FatturaPA and assigns progressive numero_fattura.
    """
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    try:
        result = await service.create_invoice(
            tenant_id=user.tenant_id,
            data=request.model_dump(),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return ActiveInvoiceResponse(**result)


@router.post("/{invoice_id}/send", response_model=ActiveInvoiceSendResponse)
async def send_to_sdi(
    invoice_id: UUID,
    user: User = Depends(get_current_user),
    service: ActiveInvoiceService = Depends(get_service),
) -> ActiveInvoiceSendResponse:
    """Send an active invoice to SDI via A-Cube."""
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    try:
        result = await service.send_to_sdi(invoice_id, user.tenant_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return ActiveInvoiceSendResponse(**result)


@router.get("/{invoice_id}/status", response_model=ActiveInvoiceStatusResponse)
async def get_sdi_status(
    invoice_id: UUID,
    user: User = Depends(get_current_user),
    service: ActiveInvoiceService = Depends(get_service),
) -> ActiveInvoiceStatusResponse:
    """Get SDI delivery status for an active invoice."""
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    try:
        result = await service.get_sdi_status(invoice_id, user.tenant_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    return ActiveInvoiceStatusResponse(**result)


@router.get("", response_model=ActiveInvoiceListResponse)
async def list_active_invoices(
    user: User = Depends(get_current_user),
    service: ActiveInvoiceService = Depends(get_service),
) -> ActiveInvoiceListResponse:
    """List all active invoices for the tenant."""
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    items = await service.list_invoices(user.tenant_id)
    return ActiveInvoiceListResponse(
        items=[ActiveInvoiceResponse(**i) for i in items],
        total=len(items),
    )
