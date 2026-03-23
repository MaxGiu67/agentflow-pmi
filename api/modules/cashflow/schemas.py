"""Pydantic schemas for cash flow prediction module (US-25)."""

from __future__ import annotations

from datetime import date as date_type

from pydantic import BaseModel


class CashFlowDayEntry(BaseModel):
    """Single day entry in the cash flow projection."""
    date: date_type
    saldo_iniziale: float
    entrate: float
    uscite: float
    saldo_proiettato: float


class CashFlowPredictionResponse(BaseModel):
    """Response for cash flow prediction."""
    saldo_attuale: float
    giorni: int
    projection: list[CashFlowDayEntry]
    total_entrate_previste: float
    total_uscite_previste: float
    saldo_finale_proiettato: float
    data_source: str  # sufficient, insufficient
    invoice_count: int
    min_invoices_required: int
    message: str | None = None
    stale_warning: str | None = None


class CashFlowAlertItem(BaseModel):
    """A single cash flow alert."""
    type: str  # critical_balance, late_payment
    message: str
    alert_date: date_type | None = None
    amount: float | None = None
    severity: str  # warning, critical
    scenario_optimistic: float | None = None
    scenario_pessimistic: float | None = None


class CashFlowAlertsResponse(BaseModel):
    """Response for cash flow alerts."""
    alerts: list[CashFlowAlertItem]
    soglia_critica: float
    total: int
