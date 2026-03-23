"""Schemas for the invoices module."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class SyncRequest(BaseModel):
    """Request to sync invoices from cassetto fiscale."""
    force: bool = False
    from_date: date | None = None


class SyncResponse(BaseModel):
    """Response from sync operation."""
    downloaded: int
    new: int
    duplicates: int
    errors: int
    message: str


class SyncStatusResponse(BaseModel):
    """Sync status information."""
    connected: bool
    token_valid: bool
    last_sync_at: datetime | None = None
    invoices_count: int = 0
    message: str


class InvoiceResponse(BaseModel):
    """Single invoice response."""
    id: UUID
    tenant_id: UUID
    type: str
    document_type: str
    source: str
    numero_fattura: str
    emittente_piva: str
    emittente_nome: str | None = None
    data_fattura: date | None = None
    importo_netto: float | None = None
    importo_iva: float | None = None
    importo_totale: float | None = None
    category: str | None = None
    category_confidence: float | None = None
    verified: bool = False
    processing_status: str = "pending"
    has_ritenuta: bool = False
    has_bollo: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class InvoiceListResponse(BaseModel):
    """Paginated list of invoices."""
    items: list[InvoiceResponse]
    total: int
    page: int
    page_size: int
    pages: int


class VerifyRequest(BaseModel):
    """Request to verify or correct an invoice category."""
    category: str
    confirmed: bool = True


class VerifyResponse(BaseModel):
    """Response from verify operation."""
    invoice_id: UUID
    category: str
    verified: bool
    was_correct: bool
    message: str


class PendingReviewResponse(BaseModel):
    """Response for pending review invoices."""
    items: list[InvoiceResponse]
    total: int
    page: int
    page_size: int
    pages: int


class SuggestedCategoriesResponse(BaseModel):
    """Suggested categories for an invoice."""
    suggestions: list[str]
    message: str
