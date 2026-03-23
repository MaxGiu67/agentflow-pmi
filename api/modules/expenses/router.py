"""Router for expense management (US-29, US-30)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from api.modules.expenses.schemas import (
    ExpenseCreateRequest,
    ExpenseListResponse,
    ExpenseReimburseRequest,
    ExpenseReimburseResponse,
    ExpenseRejectRequest,
    ExpenseResponse,
)
from api.modules.expenses.service import ExpenseService

router = APIRouter(prefix="/expenses", tags=["expenses"])


def get_service(db: AsyncSession = Depends(get_db)) -> ExpenseService:
    return ExpenseService(db)


@router.post("", response_model=ExpenseResponse)
async def create_expense(
    request: ExpenseCreateRequest,
    user: User = Depends(get_current_user),
    service: ExpenseService = Depends(get_service),
) -> ExpenseResponse:
    """Create an expense entry.

    AC-29.1: Upload receipt -> OCR -> propose category
    AC-29.2: Policy check (max amount per category) -> warning
    AC-29.3: Unreadable receipt -> manual entry
    AC-29.4: Foreign currency -> BCE conversion
    """
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    try:
        result = await service.create_expense(
            tenant_id=user.tenant_id,
            user_id=user.id,
            description=request.description,
            amount=request.amount,
            expense_date=request.expense_date,
            currency=request.currency,
            category=request.category,
            receipt_file=request.receipt_file,
            ocr_text=request.ocr_text,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return ExpenseResponse(**result)


@router.get("", response_model=ExpenseListResponse)
async def list_expenses(
    user: User = Depends(get_current_user),
    service: ExpenseService = Depends(get_service),
) -> ExpenseListResponse:
    """List all expenses for tenant."""
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    result = await service.list_expenses(user.tenant_id)
    return ExpenseListResponse(**result)


@router.patch("/{expense_id}/approve", response_model=ExpenseResponse)
async def approve_expense(
    expense_id: UUID,
    user: User = Depends(get_current_user),
    service: ExpenseService = Depends(get_service),
) -> ExpenseResponse:
    """Approve an expense.

    AC-30.1: DARE Trasferte / AVERE Debiti dipendenti
    AC-30.5: Auto-approval for sole owner (BR-10)
    """
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    try:
        result = await service.approve_expense(
            expense_id=expense_id,
            tenant_id=user.tenant_id,
            approver_id=user.id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return ExpenseResponse(**result)


@router.patch("/{expense_id}/reject", response_model=ExpenseResponse)
async def reject_expense(
    expense_id: UUID,
    request: ExpenseRejectRequest,
    user: User = Depends(get_current_user),
    service: ExpenseService = Depends(get_service),
) -> ExpenseResponse:
    """Reject an expense with motivation.

    AC-30.3: Rejection with reason -> notification to employee
    """
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    try:
        result = await service.reject_expense(
            expense_id=expense_id,
            tenant_id=user.tenant_id,
            reason=request.reason,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return ExpenseResponse(**result)


@router.post("/{expense_id}/reimburse", response_model=ExpenseReimburseResponse)
async def reimburse_expense(
    expense_id: UUID,
    request: ExpenseReimburseRequest | None = None,
    user: User = Depends(get_current_user),
    service: ExpenseService = Depends(get_service),
) -> ExpenseReimburseResponse:
    """Reimburse an approved expense.

    AC-30.2: DARE Debiti dipendenti / AVERE Banca
    AC-30.4: PISP failure -> status 'reimburse_failed'
    """
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    try:
        result = await service.reimburse_expense(
            expense_id=expense_id,
            tenant_id=user.tenant_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return ExpenseReimburseResponse(**result)
