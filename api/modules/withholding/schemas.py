"""Pydantic schemas for withholding tax module (US-33)."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel


class WithholdingTaxDetectRequest(BaseModel):
    """Request to detect withholding tax from invoice XML."""
    invoice_id: UUID


class WithholdingTaxDetectResponse(BaseModel):
    """Response from withholding tax detection."""
    detected: bool
    invoice_id: UUID
    tipo_ritenuta: str | None = None
    aliquota: float | None = None
    causale_pagamento: str | None = None
    importo_ritenuta: float | None = None
    imponibile_ritenuta: float | None = None
    importo_netto: float | None = None
    f24_code: str | None = None
    f24_due_date: date | None = None
    warning: str | None = None
    journal_entry: dict | None = None


class WithholdingTaxItem(BaseModel):
    """A single withholding tax record."""
    id: UUID
    tenant_id: UUID
    invoice_id: UUID
    tipo_ritenuta: str
    aliquota: float
    causale_pagamento: str | None = None
    importo_ritenuta: float
    imponibile_ritenuta: float
    importo_netto: float
    f24_code: str
    f24_due_date: date | None = None
    status: str

    model_config = {"from_attributes": True}


class WithholdingTaxListResponse(BaseModel):
    """Response with list of withholding taxes."""
    items: list[WithholdingTaxItem]
    total: int
