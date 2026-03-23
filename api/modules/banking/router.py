"""Router for banking / Open Banking (US-24)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
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
    BankTransactionListResponse,
    BankTransactionResponse,
    BankUnsupportedResponse,
)
from api.modules.banking.service import BankingService

router = APIRouter(prefix="/bank-accounts", tags=["banking"])


def get_service(db: AsyncSession = Depends(get_db)) -> BankingService:
    return BankingService(db)


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
