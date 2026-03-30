from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from api.modules.accounting.schemas import (
    PianoContiCreateRequest,
    PianoContiResponse,
)
from api.modules.accounting.batch_register import BatchRegisterService
from api.modules.accounting.service import AccountingService
from api.modules.fiscal.balance_sheet import BalanceSheetService

router = APIRouter(prefix="/accounting", tags=["accounting"])


def get_accounting_service(db: AsyncSession = Depends(get_db)) -> AccountingService:
    return AccountingService(db)


@router.get("/chart", response_model=PianoContiResponse)
async def get_piano_conti(
    user: User = Depends(get_current_user),
    service: AccountingService = Depends(get_accounting_service),
) -> PianoContiResponse:
    """Get existing chart of accounts for the tenant."""
    try:
        data = await service.get_piano_conti(user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except ConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        ) from e

    return PianoContiResponse(**data)


def get_balance_sheet_service(db: AsyncSession = Depends(get_db)) -> BalanceSheetService:
    return BalanceSheetService(db)


@router.get("/balance-sheet")
async def get_balance_sheet(
    year: int = Query(..., description="Fiscal year"),
    user: User = Depends(get_current_user),
    service: BalanceSheetService = Depends(get_balance_sheet_service),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Generate Bilancio CEE for a given year (US-23)."""
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    try:
        result = await service.generate(
            tenant_id=user.tenant_id,
            year=year,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return result


@router.post("/chart", response_model=PianoContiResponse, status_code=status.HTTP_201_CREATED)
async def create_piano_conti(
    request: PianoContiCreateRequest = PianoContiCreateRequest(),
    user: User = Depends(get_current_user),
    service: AccountingService = Depends(get_accounting_service),
) -> PianoContiResponse:
    """Create chart of accounts on Odoo for the tenant."""
    try:
        data = await service.create_piano_conti(user, force=request.force)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except ConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        ) from e

    return PianoContiResponse(**data)


# ── Batch contabilizzazione fatture ──


def get_batch_service(db: AsyncSession = Depends(get_db)) -> BatchRegisterService:
    return BatchRegisterService(db)


@router.get("/pending-registration")
async def get_pending_registration(
    user: User = Depends(get_current_user),
    service: BatchRegisterService = Depends(get_batch_service),
) -> dict:
    """Conta fatture in attesa di contabilizzazione."""
    if not user.tenant_id:
        raise HTTPException(status_code=400, detail="Profilo azienda non configurato")
    return await service.get_pending_count(user.tenant_id)


@router.post("/register-all")
async def register_all_invoices(
    user: User = Depends(get_current_user),
    service: BatchRegisterService = Depends(get_batch_service),
) -> dict:
    """Contabilizza tutte le fatture parsed non ancora registrate.

    Idempotente: non contabilizza mai la stessa fattura due volte.
    Assegna categoria default se mancante.
    """
    if not user.tenant_id:
        raise HTTPException(status_code=400, detail="Profilo azienda non configurato")
    return await service.register_all_pending(user.tenant_id)
