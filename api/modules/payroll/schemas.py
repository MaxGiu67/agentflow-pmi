"""Schemas for payroll/personnel costs module (US-44)."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, field_validator


class PayrollCostCreate(BaseModel):
    """Create a payroll cost entry."""
    mese: date  # first day of month
    dipendente_nome: str
    dipendente_cf: str | None = None
    importo_lordo: float
    importo_netto: float | None = None
    contributi_inps: float | None = None
    irpef: float | None = None
    tfr: float | None = None
    costo_totale_azienda: float
    note: str | None = None

    @field_validator("mese")
    @classmethod
    def normalize_mese(cls, v: date) -> date:
        return v.replace(day=1)

    @field_validator("importo_lordo", "costo_totale_azienda")
    @classmethod
    def validate_positive(cls, v: float) -> float:
        if v < 0:
            raise ValueError("L'importo non può essere negativo")
        return round(v, 2)


class PayrollCostResponse(BaseModel):
    """Response for a payroll cost entry."""
    id: UUID
    tenant_id: UUID
    mese: date
    dipendente_nome: str
    dipendente_cf: str | None = None
    importo_lordo: float
    importo_netto: float | None = None
    contributi_inps: float | None = None
    irpef: float | None = None
    tfr: float | None = None
    costo_totale_azienda: float
    note: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class PayrollCostListResponse(BaseModel):
    items: list[PayrollCostResponse]
    total: int


class PayrollMonthlySummary(BaseModel):
    """Monthly summary of payroll costs."""
    mese: date
    num_dipendenti: int
    totale_lordo: float
    totale_netto: float
    totale_contributi: float
    totale_costo_azienda: float


class PayrollSummaryResponse(BaseModel):
    """Yearly payroll summary."""
    year: int
    total_costo_azienda: float
    total_lordo: float
    num_dipendenti: int
    monthly: list[PayrollMonthlySummary]
