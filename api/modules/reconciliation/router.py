"""Router for invoice-transaction reconciliation (US-26)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from api.modules.reconciliation.schemas import (
    ReconciliationMatchRequest,
    ReconciliationMatchResponse,
    ReconciliationPendingResponse,
)
from api.modules.reconciliation.service import ReconciliationService
from api.modules.reconciliation.auto_match_service import AutoMatchService

router = APIRouter(prefix="/reconciliation", tags=["reconciliation"])


def get_service(db: AsyncSession = Depends(get_db)) -> ReconciliationService:
    return ReconciliationService(db)


@router.get("/pending", response_model=ReconciliationPendingResponse)
async def get_pending_reconciliations(
    user: User = Depends(get_current_user),
    service: ReconciliationService = Depends(get_service),
) -> ReconciliationPendingResponse:
    """Get unreconciled bank transactions with match suggestions.

    AC-26.1: Automatic match by amount+date+description
    AC-26.2: Top 3 suggestions with confidence
    AC-26.3: Unmatched transactions with options
    """
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    result = await service.get_pending(user.tenant_id)
    return ReconciliationPendingResponse(**result)


@router.post("/{tx_id}/match", response_model=ReconciliationMatchResponse)
async def match_transaction(
    tx_id: UUID,
    request: ReconciliationMatchRequest,
    user: User = Depends(get_current_user),
    service: ReconciliationService = Depends(get_service),
) -> ReconciliationMatchResponse:
    """Match a bank transaction to an invoice.

    AC-26.1: Exact match -> reconciled
    AC-26.4: Foreign currency -> BCE conversion
    AC-26.5: Partial payment -> partially paid
    AC-26.6: Concurrent sync -> dedup on transaction_id
    """
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    try:
        result = await service.match_transaction(
            tx_id=tx_id,
            tenant_id=user.tenant_id,
            invoice_id=request.invoice_id,
            match_type=request.match_type,
            amount=request.amount,
            currency=request.currency,
            exchange_rate=request.exchange_rate,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return ReconciliationMatchResponse(**result)


# ── US-72: Auto-match ──

def get_auto_match_service(db: AsyncSession = Depends(get_db)) -> AutoMatchService:
    return AutoMatchService(db)


@router.post("/auto-match")
async def auto_match_transactions(
    user: User = Depends(get_current_user),
    service: AutoMatchService = Depends(get_auto_match_service),
) -> dict:
    """Auto-match bank transactions to invoices by amount/date (US-72)."""
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    return await service.auto_match(user.tenant_id)
