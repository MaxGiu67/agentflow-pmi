"""Pydantic schemas for digital preservation module (US-37)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class PreservationItem(BaseModel):
    """A single preservation record."""
    id: UUID
    tenant_id: UUID
    invoice_id: UUID
    provider: str
    batch_id: str | None = None
    package_hash: str | None = None
    status: str
    reject_reason: str | None = None
    retry_count: int = 0
    last_attempt_at: datetime | None = None
    confirmed_at: datetime | None = None

    model_config = {"from_attributes": True}


class PreservationListResponse(BaseModel):
    """Response with list of preservation records."""
    items: list[PreservationItem]
    total: int
    summary: dict  # counts by status


class PreservationBatchResponse(BaseModel):
    """Response from batch preservation send."""
    sent: int
    errors: int
    details: list[dict]


class PreservationStatusResponse(BaseModel):
    """Response with preservation status check."""
    checked: int
    confirmed: int
    rejected: int
    details: list[dict]
