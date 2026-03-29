"""Router for banking / Open Banking (US-24) + Import (US-44/45) + CRUD (US-46)."""

import uuid as uuid_mod
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import BankAccount, BankTransaction, User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from api.modules.banking.schemas import (
    BankAccountBalanceResponse,
    BankAccountConnectRequest,
    BankAccountConnectResponse,
    BankAccountListResponse,
    BankAccountResponse,
    BankRevokeResponse,
    BankSyncResponse,
    BankTransactionCreate,
    BankTransactionListResponse,
    BankTransactionResponse,
    BankTransactionUpdate,
    BankUnsupportedResponse,
    ConfirmImportRequest,
    ConfirmImportResponse,
    ImportStatementResponse,
)
from api.modules.banking.import_service import BankImportService
from api.modules.banking.service import BankingService

router = APIRouter(prefix="/bank-accounts", tags=["banking"])


def get_service(db: AsyncSession = Depends(get_db)) -> BankingService:
    return BankingService(db)


def get_import_service(db: AsyncSession = Depends(get_db)) -> BankImportService:
    return BankImportService(db)


@router.post("/connect-session")
async def create_connect_session(
    user: User = Depends(get_current_user),
    service: BankingService = Depends(get_service),
) -> dict:
    """Create a Salt Edge connect session — returns URL to authenticate with bank.

    User opens the URL, selects bank, completes SCA, and the account is linked.
    """
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )
    result = await service.create_connect_session(user.tenant_id)
    if "error" in result and not result.get("connect_url"):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=result["error"])
    return result


@router.post("/connect", status_code=status.HTTP_201_CREATED)
async def connect_bank_account(
    request: BankAccountConnectRequest,
    user: User = Depends(get_current_user),
    service: BankingService = Depends(get_service),
) -> BankAccountConnectResponse | BankUnsupportedResponse:
    """Connect a bank account via Open Banking SCA flow.

    If the bank is not supported on CBI Globe, returns suggestion
    for manual upload.
    """
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    try:
        result = await service.connect_account(
            tenant_id=user.tenant_id,
            iban=request.iban,
            bank_name=request.bank_name,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    # Check if unsupported
    if "supported" in result and not result["supported"]:
        return BankUnsupportedResponse(
            iban=result["iban"],
            supported=False,
            message=result["message"],
        )

    return BankAccountConnectResponse(**result)


@router.get("", response_model=BankAccountListResponse)
async def list_bank_accounts(
    user: User = Depends(get_current_user),
    service: BankingService = Depends(get_service),
) -> BankAccountListResponse:
    """List all connected bank accounts."""
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    items = await service.list_accounts(user.tenant_id)
    return BankAccountListResponse(
        items=[BankAccountResponse(**i) for i in items],
        total=len(items),
    )


@router.get("/{account_id}/balance", response_model=BankAccountBalanceResponse)
async def get_account_balance(
    account_id: UUID,
    user: User = Depends(get_current_user),
    service: BankingService = Depends(get_service),
) -> BankAccountBalanceResponse:
    """Get balance for a connected bank account."""
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    try:
        result = await service.get_balance(account_id, user.tenant_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    return BankAccountBalanceResponse(**result)


@router.get("/{account_id}/transactions", response_model=BankTransactionListResponse)
async def get_account_transactions(
    account_id: UUID,
    user: User = Depends(get_current_user),
    service: BankingService = Depends(get_service),
) -> BankTransactionListResponse:
    """Get transactions for a connected bank account."""
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    try:
        items = await service.get_transactions(account_id, user.tenant_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    return BankTransactionListResponse(
        items=[BankTransactionResponse(**i) for i in items],
        total=len(items),
    )


@router.post("/{account_id}/sync", response_model=BankSyncResponse)
async def sync_bank_account(
    account_id: UUID,
    user: User = Depends(get_current_user),
    service: BankingService = Depends(get_service),
) -> BankSyncResponse:
    """Sync transactions for a connected bank account.

    First sync: downloads 90 days of history.
    Subsequent syncs: incremental from last sync.
    """
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    try:
        result = await service.sync_transactions(account_id, user.tenant_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return BankSyncResponse(**result)


@router.post("/{account_id}/revoke", response_model=BankRevokeResponse)
async def revoke_consent(
    account_id: UUID,
    user: User = Depends(get_current_user),
    service: BankingService = Depends(get_service),
) -> BankRevokeResponse:
    """Revoke PSD2 consent for a connected bank account.

    Disconnects the account and offers option to re-connect.
    """
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    try:
        result = await service.revoke_consent(account_id, user.tenant_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    return BankRevokeResponse(**result)


# ── Statement Import (US-44) ──


@router.post("/{account_id}/import-statement", response_model=ImportStatementResponse)
async def import_bank_statement(
    account_id: UUID,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    service: BankImportService = Depends(get_import_service),
) -> ImportStatementResponse:
    """Import bank statement from PDF using LLM extraction (US-44).

    Extracts movements and returns preview for user confirmation.
    Use POST /{account_id}/confirm-import to save the movements.
    """
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo file PDF accettati",
        )

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File troppo grande (max 10MB)",
        )

    try:
        result = await service.import_pdf_statement(
            tenant_id=user.tenant_id,
            account_id=account_id,
            filename=file.filename,
            pdf_content=content,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from e

    return ImportStatementResponse(**result)


@router.post("/{account_id}/confirm-import", response_model=ConfirmImportResponse)
async def confirm_bank_import(
    account_id: UUID,
    request: ConfirmImportRequest,
    user: User = Depends(get_current_user),
    service: BankImportService = Depends(get_import_service),
) -> ConfirmImportResponse:
    """Confirm and save imported bank movements (US-44).

    Called after the user reviews the preview from import-statement.
    """
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    try:
        result = await service.confirm_import(
            tenant_id=user.tenant_id,
            account_id=account_id,
            movements=[m.model_dump() for m in request.movements],
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return ConfirmImportResponse(**result)


@router.post("/{account_id}/import-csv", response_model=ImportStatementResponse)
async def import_bank_csv(
    account_id: UUID,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    service: BankImportService = Depends(get_import_service),
) -> ImportStatementResponse:
    """Import bank statement from CSV with auto-detect columns (US-45).

    Auto-detects separator (, ; tab) and column names.
    Returns preview for user confirmation.
    """
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo file CSV accettati",
        )

    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File troppo grande (max 5MB)",
        )

    try:
        result = await service.import_csv_statement(
            tenant_id=user.tenant_id,
            account_id=account_id,
            filename=file.filename,
            csv_content=content,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from e

    return ImportStatementResponse(**result)


# ── CRUD Bank Transactions (US-46) ──


@router.post("/transactions", status_code=status.HTTP_201_CREATED)
async def create_bank_transaction(
    request: BankTransactionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a manual bank transaction (US-46)."""
    if not user.tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Profilo azienda non configurato")

    acct = await db.scalar(
        select(BankAccount).where(BankAccount.id == request.bank_account_id, BankAccount.tenant_id == user.tenant_id)
    )
    if not acct:
        raise HTTPException(status_code=404, detail="Conto bancario non trovato")

    tx = BankTransaction(
        bank_account_id=request.bank_account_id,
        transaction_id=f"MAN-{uuid_mod.uuid4().hex[:12]}",
        date=request.date,
        amount=abs(request.amount),
        direction=request.direction,
        description=request.description,
        source="manual",
    )
    db.add(tx)
    await db.flush()
    return {"id": str(tx.id), "source": "manual", "message": "Movimento creato"}


@router.put("/transactions/{tx_id}")
async def update_bank_transaction(
    tx_id: UUID,
    request: BankTransactionUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update a bank transaction (US-46)."""
    if not user.tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Profilo azienda non configurato")

    tx = await db.scalar(
        select(BankTransaction).select_from(BankTransaction).join(
            BankAccount, BankTransaction.bank_account_id == BankAccount.id
        ).where(BankTransaction.id == tx_id, BankAccount.tenant_id == user.tenant_id)
    )
    if not tx:
        raise HTTPException(status_code=404, detail="Movimento non trovato")

    if request.date is not None:
        tx.date = request.date
    if request.description is not None:
        tx.description = request.description
    if request.amount is not None:
        tx.amount = abs(request.amount)
    if request.direction is not None:
        tx.direction = request.direction
    await db.flush()
    return {"id": str(tx.id), "updated": True}


@router.delete("/transactions/{tx_id}")
async def delete_bank_transaction(
    tx_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a bank transaction (US-46)."""
    if not user.tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Profilo azienda non configurato")

    tx = await db.scalar(
        select(BankTransaction).select_from(BankTransaction).join(
            BankAccount, BankTransaction.bank_account_id == BankAccount.id
        ).where(BankTransaction.id == tx_id, BankAccount.tenant_id == user.tenant_id)
    )
    if not tx:
        raise HTTPException(status_code=404, detail="Movimento non trovato")

    await db.delete(tx)
    await db.flush()
    return {"id": str(tx_id), "deleted": True}
