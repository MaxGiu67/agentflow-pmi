"""Router for withholding tax (ritenuta d'acconto) management (US-33)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from api.modules.withholding.schemas import (
    WithholdingTaxDetectRequest,
    WithholdingTaxDetectResponse,
    WithholdingTaxListResponse,
)
from api.modules.withholding.service import WithholdingTaxService

router = APIRouter(prefix="/withholding-taxes", tags=["withholding"])


def get_service(db: AsyncSession = Depends(get_db)) -> WithholdingTaxService:
    return WithholdingTaxService(db)


@router.post("/detect", response_model=WithholdingTaxDetectResponse)
async def detect_withholding_tax(
    request: WithholdingTaxDetectRequest,
    user: User = Depends(get_current_user),
    service: WithholdingTaxService = Depends(get_service),
) -> WithholdingTaxDetectResponse:
    """Detect withholding tax from invoice XML.

    AC-33.1: Recognize <DatiRitenuta> tag, calculate net amount.
    AC-33.2: Journal entry with withholding.
    AC-33.3: F24 deadline code 1040.
    AC-33.4: Professional supplier without tag -> warning.
    """
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    try:
        result = await service.detect_from_invoice(
            invoice_id=request.invoice_id,
            tenant_id=user.tenant_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return WithholdingTaxDetectResponse(**result)


@router.get("", response_model=WithholdingTaxListResponse)
async def list_withholding_taxes(
    user: User = Depends(get_current_user),
    service: WithholdingTaxService = Depends(get_service),
) -> WithholdingTaxListResponse:
    """List all withholding taxes for tenant."""
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    result = await service.list_withholding_taxes(user.tenant_id)
    return WithholdingTaxListResponse(**result)
