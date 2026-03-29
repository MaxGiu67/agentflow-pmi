"""Router for recurring contracts (US-55, US-56)."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from api.modules.recurring.service import RecurringContractService

router = APIRouter(prefix="/recurring-contracts", tags=["recurring-contracts"])


def get_service(db: AsyncSession = Depends(get_db)) -> RecurringContractService:
    return RecurringContractService(db)


@router.post("/import-pdf")
async def import_contracts_pdf(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    service: RecurringContractService = Depends(get_service),
) -> dict:
    """Import recurring contracts from PDF (US-55)."""
    if not user.tenant_id:
        raise HTTPException(status_code=400, detail="Profilo azienda non configurato")

    content = await file.read()
    return await service.import_pdf(user.tenant_id, file.filename or "contract.pdf", content)


class ContractCreate(BaseModel):
    description: str
    counterpart: Optional[str] = None
    amount: float
    frequency: str = "monthly"
    start_date: str
    end_date: Optional[str] = None
    category: Optional[str] = None


class ContractUpdate(BaseModel):
    description: Optional[str] = None
    counterpart: Optional[str] = None
    amount: Optional[float] = None
    frequency: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None


@router.post("")
async def create_contract(
    request: ContractCreate,
    user: User = Depends(get_current_user),
    service: RecurringContractService = Depends(get_service),
) -> dict:
    """Create a recurring contract (US-56)."""
    if not user.tenant_id:
        raise HTTPException(status_code=400, detail="Profilo azienda non configurato")

    return await service.create(user.tenant_id, request.model_dump(exclude_none=True))


@router.get("")
async def list_contracts(
    user: User = Depends(get_current_user),
    service: RecurringContractService = Depends(get_service),
) -> dict:
    """List all recurring contracts."""
    if not user.tenant_id:
        raise HTTPException(status_code=400, detail="Profilo azienda non configurato")

    return await service.get_all(user.tenant_id)


@router.put("/{contract_id}")
async def update_contract(
    contract_id: UUID,
    request: ContractUpdate,
    user: User = Depends(get_current_user),
    service: RecurringContractService = Depends(get_service),
) -> dict:
    """Update a recurring contract (US-56)."""
    if not user.tenant_id:
        raise HTTPException(status_code=400, detail="Profilo azienda non configurato")

    try:
        return await service.update(contract_id, user.tenant_id, request.model_dump(exclude_none=True))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.delete("/{contract_id}")
async def delete_contract(
    contract_id: UUID,
    user: User = Depends(get_current_user),
    service: RecurringContractService = Depends(get_service),
) -> dict:
    """Delete a recurring contract (US-56)."""
    if not user.tenant_id:
        raise HTTPException(status_code=400, detail="Profilo azienda non configurato")

    try:
        return await service.delete(contract_id, user.tenant_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
