"""Schemas for the journal module."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class JournalLineResponse(BaseModel):
    """Single journal line response."""
    id: UUID
    entry_id: UUID
    account_code: str
    account_name: str
    debit: float = 0.0
    credit: float = 0.0
    description: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class JournalEntryResponse(BaseModel):
    """Single journal entry response."""
    id: UUID
    tenant_id: UUID
    invoice_id: UUID | None = None
    description: str
    entry_date: date
    total_debit: float = 0.0
    total_credit: float = 0.0
    status: str = "draft"
    error_message: str | None = None
    odoo_move_id: int | None = None
    created_at: datetime | None = None
    lines: list[JournalLineResponse] = []

    model_config = {"from_attributes": True}


class JournalEntryListItem(BaseModel):
    """Journal entry item for list (without lines for performance)."""
    id: UUID
    tenant_id: UUID
    invoice_id: UUID | None = None
    description: str
    entry_date: date
    total_debit: float = 0.0
    total_credit: float = 0.0
    status: str = "draft"
    error_message: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class JournalListResponse(BaseModel):
    """Paginated list of journal entries."""
    items: list[JournalEntryListItem]
    total: int
    page: int
    page_size: int
    pages: int
    message: str | None = None
