"""Router for loans/financing (US-57, US-58)."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from api.modules.loans.service import LoanService

router = APIRouter(prefix="/loans", tags=["loans"])


def get_service(db: AsyncSession = Depends(get_db)) -> LoanService:
    return LoanService(db)


@router.post("/import-pdf")
async def import_loans_pdf(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    service: LoanService = Depends(get_service),
) -> dict:
    """Import loans from PDF (US-57)."""
    if not user.tenant_id:
        raise HTTPException(status_code=400, detail="Profilo azienda non configurato")

    content = await file.read()
    return await service.import_pdf(user.tenant_id, file.filename or "loan.pdf", content)


class LoanCreate(BaseModel):
    description: str
    lender: Optional[str] = None
    principal: float
    interest_rate: float
    installment_amount: float
    frequency: str = "monthly"
    start_date: str
    end_date: Optional[str] = None


class LoanUpdate(BaseModel):
    description: Optional[str] = None
    lender: Optional[str] = None
    principal: Optional[float] = None
    interest_rate: Optional[float] = None
    installment_amount: Optional[float] = None
    frequency: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    remaining_principal: Optional[float] = None
    status: Optional[str] = None


@router.post("")
async def create_loan(
    request: LoanCreate,
    user: User = Depends(get_current_user),
    service: LoanService = Depends(get_service),
) -> dict:
    """Create a loan (US-58)."""
    if not user.tenant_id:
        raise HTTPException(status_code=400, detail="Profilo azienda non configurato")

    return await service.create(user.tenant_id, request.model_dump(exclude_none=True))


@router.get("")
async def list_loans(
    user: User = Depends(get_current_user),
    service: LoanService = Depends(get_service),
) -> dict:
    """List all loans."""
    if not user.tenant_id:
        raise HTTPException(status_code=400, detail="Profilo azienda non configurato")

    return await service.get_all(user.tenant_id)


@router.put("/{loan_id}")
async def update_loan(
    loan_id: UUID,
    request: LoanUpdate,
    user: User = Depends(get_current_user),
    service: LoanService = Depends(get_service),
) -> dict:
    """Update a loan (US-58)."""
    if not user.tenant_id:
        raise HTTPException(status_code=400, detail="Profilo azienda non configurato")

    try:
        return await service.update(loan_id, user.tenant_id, request.model_dump(exclude_none=True))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.delete("/{loan_id}")
async def delete_loan(
    loan_id: UUID,
    user: User = Depends(get_current_user),
    service: LoanService = Depends(get_service),
) -> dict:
    """Delete a loan (US-58)."""
    if not user.tenant_id:
        raise HTTPException(status_code=400, detail="Profilo azienda non configurato")

    try:
        return await service.delete(loan_id, user.tenant_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
