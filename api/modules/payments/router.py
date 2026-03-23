"""Router for payments via PISP (US-27)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from api.modules.payments.schemas import (
    PaymentBatchRequest,
    PaymentBatchResponse,
    PaymentErrorResponse,
    PaymentExecuteRequest,
    PaymentResponse,
)
from api.modules.payments.service import PaymentService

router = APIRouter(prefix="/payments", tags=["payments"])


def get_service(db: AsyncSession = Depends(get_db)) -> PaymentService:
    return PaymentService(db)


@router.post("/execute", response_model=PaymentResponse | PaymentErrorResponse)
async def execute_payment(
    request: PaymentExecuteRequest,
    user: User = Depends(get_current_user),
    service: PaymentService = Depends(get_service),
) -> PaymentResponse | PaymentErrorResponse:
    """Execute a single supplier payment via PISP.

    AC-27.1: Pagamento con SCA, registra uscita, riconcilia.
    AC-27.2: Fondi insufficienti -> errore con saldo.
    AC-27.3: IBAN non valido -> errore validazione.
    """
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    try:
        result = await service.execute_payment(
            tenant_id=user.tenant_id,
            bank_account_id=request.bank_account_id,
            invoice_id=request.invoice_id,
            beneficiary_name=request.beneficiary_name,
            beneficiary_iban=request.beneficiary_iban,
            amount=request.amount,
            causale=request.causale,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    # Check if it's an error response (insufficient funds)
    if "error" in result:
        return PaymentErrorResponse(**result)

    return PaymentResponse(**result)


@router.post("/batch", response_model=PaymentBatchResponse | PaymentErrorResponse)
async def execute_batch_payment(
    request: PaymentBatchRequest,
    user: User = Depends(get_current_user),
    service: PaymentService = Depends(get_service),
) -> PaymentBatchResponse | PaymentErrorResponse:
    """Execute a batch payment for multiple invoices.

    AC-27.4: Bonifico cumulativo con causale che elenca numeri fattura.
    """
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    try:
        result = await service.execute_batch_payment(
            tenant_id=user.tenant_id,
            bank_account_id=request.bank_account_id,
            beneficiary_name=request.beneficiary_name,
            beneficiary_iban=request.beneficiary_iban,
            invoice_ids=request.invoice_ids,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    # Check if it's an error response
    if "error" in result:
        return PaymentErrorResponse(**result)

    return PaymentBatchResponse(**result)
