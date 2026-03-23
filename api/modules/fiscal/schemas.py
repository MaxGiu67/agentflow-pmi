"""Pydantic schemas for the fiscal module."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel, field_validator


class FiscalRuleResponse(BaseModel):
    id: str
    key: str
    value: str
    value_type: str
    valid_from: str
    valid_to: str | None = None
    law_reference: str | None = None
    description: str | None = None


class FiscalRulesListResponse(BaseModel):
    rules: list[FiscalRuleResponse]
    count: int


class VatSettlementComputeRequest(BaseModel):
    """Request to compute quarterly VAT settlement."""
    year: int
    quarter: int

    @field_validator("quarter")
    @classmethod
    def validate_quarter(cls, v: int) -> int:
        if v not in (1, 2, 3, 4):
            raise ValueError("Trimestre deve essere tra 1 e 4")
        return v


class VatSettlementResponse(BaseModel):
    """Response for a VAT settlement computation."""
    id: str
    tenant_id: str
    year: int
    quarter: int
    period: str
    iva_vendite: float
    iva_acquisti: float
    iva_reverse_charge_debito: float
    iva_reverse_charge_credito: float
    iva_debito_totale: float
    iva_credito_totale: float
    credito_periodo_precedente: float
    interessi: float
    saldo: float
    saldo_tipo: str  # debito, credito, zero
    unregistered_count: int
    warnings: list[str] = []
    status: str


# ============================================================
# US-35: Stamp Duty (Imposta di Bollo)
# ============================================================


class StampDutyCheckRequest(BaseModel):
    """Request to check stamp duty for an invoice."""
    invoice_id: UUID


class StampDutyCheckResponse(BaseModel):
    """Response from stamp duty check."""
    invoice_id: str
    bollo_required: bool
    importo_esente: float
    importo_totale: float
    soglia: float
    importo_bollo: float
    bollo_virtuale: bool
    message: str
    warning: str | None = None


class StampDutyQuarterlyResponse(BaseModel):
    """Response for quarterly stamp duty summary."""
    year: int
    quarter: int
    period: str
    invoice_count: int
    importo_unitario: float
    importo_totale: float
    f24_code: str
    due_date: date
    message: str


# ============================================================
# US-36: Ratei e Risconti (Accruals & Deferrals)
# ============================================================


class AccrualProposeRequest(BaseModel):
    """Request to propose an accrual/deferral."""
    invoice_id: UUID | None = None
    description: str | None = None
    total_amount: float | None = None
    period_start: date | None = None
    period_end: date | None = None
    accrual_type: str | None = None  # risconto_attivo, risconto_passivo, rateo_attivo, rateo_passivo
    fiscal_year: int | None = None


class AccrualResponse(BaseModel):
    """Response for a single accrual."""
    id: str
    tenant_id: str
    invoice_id: str | None = None
    type: str
    description: str
    total_amount: float
    current_year_amount: float
    deferred_amount: float
    period_start: str
    period_end: str
    fiscal_year: int
    status: str
    adjustment_entry: dict | None = None
    reversal_entry: dict | None = None


class AccrualNeedsPeriodResponse(BaseModel):
    """Response when period is needed."""
    status: str
    message: str
    description: str
    total_amount: float


class AccrualListResponse(BaseModel):
    """Response with list of accruals."""
    items: list[AccrualResponse]
    total: int
