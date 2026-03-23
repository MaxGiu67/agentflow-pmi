"""Pydantic schemas for normativo module (US-28)."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class NormativeAlertItem(BaseModel):
    """A single normative alert."""
    id: UUID
    source: str
    title: str
    description: str | None = None
    url: str | None = None
    published_at: datetime | None = None
    effective_date: date | None = None
    impact_preview: str | None = None
    proposed_rule_key: str | None = None
    proposed_rule_value: str | None = None
    status: str

    model_config = {"from_attributes": True}


class NormativeAlertListResponse(BaseModel):
    """Response with list of normative alerts."""
    items: list[NormativeAlertItem]
    total: int


class NormativeCheckResponse(BaseModel):
    """Response from feed check."""
    status: str
    message: str
    alerts: list[dict]
    retry_scheduled: bool
