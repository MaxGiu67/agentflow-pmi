"""Pydantic schemas for reconciliation module (US-26)."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel


class ReconciliationMatchSuggestion(BaseModel):
    """A suggested match between transaction and invoice."""
    invoice_id: UUID
    numero_fattura: str
    importo_totale: float
    data_fattura: date | None = None
    emittente_nome: str | None = None
    confidence: float
    match_type: str  # exact, amount_match, fuzzy


class ReconciliationPendingItem(BaseModel):
    """A pending (unreconciled) bank transaction with suggestions."""
    transaction_id: UUID
    bank_transaction_id: str  # external ID
    date: date
    amount: float
    direction: str
    counterpart: str | None = None
    description: str | None = None
    currency: str = "EUR"
    suggestions: list[ReconciliationMatchSuggestion]
    status: str  # unmatched, suggested


class ReconciliationPendingResponse(BaseModel):
    """Response with pending reconciliation items."""
    items: list[ReconciliationPendingItem]
    total: int


class ReconciliationMatchRequest(BaseModel):
    """Request to match a transaction to an invoice."""
    invoice_id: UUID
    match_type: str = "manual"  # exact, manual, partial
    amount: float | None = None  # for partial payments
    currency: str | None = None  # for foreign currency
    exchange_rate: float | None = None  # for foreign currency


class ReconciliationMatchResponse(BaseModel):
    """Response from a reconciliation match."""
    reconciliation_id: UUID
    transaction_id: UUID
    invoice_id: UUID
    match_type: str
    confidence: float
    amount_matched: float
    amount_remaining: float
    status: str
    message: str


class ReconciliationPartialResponse(BaseModel):
    """Response for partial payment reconciliation."""
    reconciliation_id: UUID
    transaction_id: UUID
    invoice_id: UUID
    amount_matched: float
    amount_total: float
    amount_remaining: float
    status: str  # partial
    message: str
