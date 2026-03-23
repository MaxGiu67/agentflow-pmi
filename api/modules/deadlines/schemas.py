"""Schemas for fiscal deadlines module (US-17)."""

from datetime import date

from pydantic import BaseModel


class DeadlineItem(BaseModel):
    """A single fiscal deadline."""
    name: str
    description: str
    original_date: date
    effective_date: date  # adjusted for weekends/holidays
    days_remaining: int
    color: str  # red, yellow, green
    regime: str
    category: str  # iva, f24, imposta_sostitutiva, dichiarazione


class DeadlinesResponse(BaseModel):
    """Response with list of fiscal deadlines."""
    deadlines: list[DeadlineItem]
    regime: str
    total: int
    year: int


# ============================================================
# US-20: Alert scadenze fiscali personalizzate
# ============================================================


class FiscalAlertItem(BaseModel):
    """A personalized fiscal alert with estimated amount."""
    name: str
    description: str
    scadenza_date: date
    days_remaining: int
    importo_stimato: float | None = None
    importo_source: str = "stima"  # stima, fiscoapi
    is_provisional: bool = False
    provisional_note: str | None = None
    regime: str
    category: str


class FiscalAlertsResponse(BaseModel):
    """Response with personalized fiscal alerts."""
    alerts: list[FiscalAlertItem]
    regime: str
    total: int
    year: int
