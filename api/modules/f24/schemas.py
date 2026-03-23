"""Pydantic schemas for F24 module (US-38)."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel


class F24Section(BaseModel):
    """A single section entry in F24."""
    section_type: str  # erario, credito
    codice_tributo: str  # e.g. 6031, 6032, 1040, 2501
    rateazione: str | None = None
    anno_riferimento: int | None = None
    periodo_riferimento: str | None = None  # e.g. "01" for January, "T1" for Q1
    importo_debito: float = 0.0
    importo_credito: float = 0.0
    description: str | None = None


class F24GenerateRequest(BaseModel):
    """Request to generate F24 for a period."""
    year: int
    month: int | None = None  # 1-12 for monthly (ritenute)
    quarter: int | None = None  # 1-4 for quarterly (IVA)
    fisco_api_amount: float | None = None  # amount from FiscoAPI if available


class F24Item(BaseModel):
    """A single F24 document."""
    id: UUID
    tenant_id: UUID
    year: int
    period_month: int | None = None
    period_quarter: int | None = None
    sections: list[F24Section] | None = None
    total_debit: float
    total_credit: float
    net_amount: float
    fisco_api_amount: float | None = None
    amount_difference: float | None = None
    status: str
    due_date: date | None = None

    model_config = {"from_attributes": True}


class F24GenerateResponse(BaseModel):
    """Response from F24 generation."""
    f24: F24Item
    warnings: list[str] = []


class F24ListResponse(BaseModel):
    """Response with list of F24 documents."""
    items: list[F24Item]
    total: int


class F24ExportResponse(BaseModel):
    """Response with exported F24 data."""
    id: UUID
    format: str  # pdf, telematico
    content: str
    filename: str


class F24MarkPaidResponse(BaseModel):
    """Response from marking F24 as paid."""
    id: UUID
    status: str
    net_amount: float
