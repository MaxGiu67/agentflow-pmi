"""Schemas for the dashboard module."""

from datetime import datetime

from pydantic import BaseModel

from api.modules.invoices.schemas import InvoiceResponse


class InvoiceCounters(BaseModel):
    """Invoice counters by status."""
    total: int = 0
    pending: int = 0
    parsed: int = 0
    categorized: int = 0
    registered: int = 0
    error: int = 0


class AgentStatus(BaseModel):
    """Status of a single agent."""
    name: str
    status: str  # active, idle, error
    last_run: datetime | None = None
    events_published: int = 0
    events_failed: int = 0


class DashboardSummary(BaseModel):
    """Complete dashboard summary."""
    counters: InvoiceCounters
    recent_invoices: list[InvoiceResponse]
    agents: list[AgentStatus]
    last_sync_at: datetime | None = None
    message: str | None = None
