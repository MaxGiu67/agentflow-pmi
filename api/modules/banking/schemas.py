"""Pydantic schemas for banking / Open Banking module (US-24)."""

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, field_validator


class BankAccountConnectRequest(BaseModel):
    """Request to connect a bank account via Open Banking SCA."""
    iban: str
    bank_name: str | None = None

    @field_validator("iban")
    @classmethod
    def validate_iban(cls, v: str) -> str:
        v = v.strip().upper().replace(" ", "")
        if len(v) < 15 or len(v) > 34:
            raise ValueError("IBAN non valido: lunghezza non corretta")
        return v


class BankAccountResponse(BaseModel):
    """Response for a connected bank account."""
    id: UUID
    tenant_id: UUID
    iban: str
    bank_name: str
    provider: str
    balance: float | None = None
    status: str
    consent_expires_at: datetime | None = None
    last_sync_at: datetime | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class BankAccountListResponse(BaseModel):
    """List of connected bank accounts."""
    items: list[BankAccountResponse]
    total: int


class BankAccountConnectResponse(BaseModel):
    """Response from bank account connection initiation."""
    account_id: UUID
    iban: str
    bank_name: str
    status: str
    balance: float | None = None
    consent_expires_at: datetime
    redirect_url: str
    message: str


class BankAccountBalanceResponse(BaseModel):
    """Response with bank account balance."""
    account_id: UUID
    iban: str
    balance: float
    currency: str = "EUR"
    last_sync_at: datetime | None = None


class BankTransactionResponse(BaseModel):
    """Response for a single bank transaction."""
    id: UUID
    bank_account_id: UUID
    transaction_id: str
    date: date
    amount: float
    direction: str
    counterpart: str | None = None
    description: str | None = None
    reconciled: bool = False
    # Sprint 50 — AI parser
    parsed_counterparty: str | None = None
    parsed_counterparty_iban: str | None = None
    parsed_invoice_ref: str | None = None
    parsed_category: str | None = None
    parsed_subcategory: str | None = None
    parsed_confidence: float | None = None
    parsed_method: str | None = None
    parsed_notes: str | None = None
    user_corrected: bool = False
    enriched_cro: str | None = None
    linked_invoice_id: UUID | None = None

    model_config = {"from_attributes": True}


class BankTransactionListResponse(BaseModel):
    """List of bank transactions."""
    items: list[BankTransactionResponse]
    total: int


class BankSyncResponse(BaseModel):
    """Response from bank account sync."""
    account_id: UUID
    new_transactions: int
    total_transactions: int
    message: str


class BankRevokeResponse(BaseModel):
    """Response from consent revocation."""
    account_id: UUID
    status: str
    message: str


# ── CRUD Bank Transactions (US-46) ──

class BankTransactionCreate(BaseModel):
    """Create a manual bank transaction."""
    bank_account_id: UUID
    date: date
    value_date: Optional[date] = None
    description: str
    amount: float
    direction: str  # credit, debit


class BankTransactionUpdate(BaseModel):
    """Update a bank transaction."""
    date: Optional[date] = None
    value_date: Optional[date] = None
    description: Optional[str] = None
    amount: Optional[float] = None
    direction: Optional[str] = None


# ── Import Statement (US-44, US-45) ──

class ImportMovementPreview(BaseModel):
    """Single movement extracted from PDF/CSV for preview."""
    data_operazione: str
    data_valuta: str | None = None
    descrizione: str
    dare: float = 0
    avere: float = 0
    importo: float = 0
    direzione: str = "debit"


class ImportStatementResponse(BaseModel):
    """Response from bank statement import (preview before confirm)."""
    import_id: str
    bank_account_id: str
    filename: str
    extraction_method: str
    movements_count: int
    period_from: str | None = None
    period_to: str | None = None
    movements: list[ImportMovementPreview]
    status: str


class ConfirmImportRequest(BaseModel):
    """Request to confirm imported movements."""
    movements: list[ImportMovementPreview]


class ConfirmImportResponse(BaseModel):
    """Response from confirmed import."""
    saved: int
    bank_account_id: str
    source: str
    message: str


class BankUnsupportedResponse(BaseModel):
    """Response when bank is not supported."""
    iban: str
    supported: bool
    message: str
