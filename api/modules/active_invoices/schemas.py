"""Pydantic schemas for active invoices module (US-21)."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, field_validator


class ActiveInvoiceCreate(BaseModel):
    """Request to create an active invoice."""
    cliente_piva: str
    cliente_nome: str
    cliente_codice_sdi: str | None = None
    data_fattura: date
    importo_netto: float
    aliquota_iva: float = 22.0
    descrizione: str | None = None
    document_type: str = "TD01"
    # For credit notes (TD04)
    original_invoice_id: UUID | None = None
    original_invoice_numero: str | None = None
    original_invoice_date: date | None = None

    @field_validator("importo_netto")
    @classmethod
    def validate_importo(cls, v: float, info: object) -> float:
        if v <= 0:
            raise ValueError(
                "Importo deve essere positivo. Per importi negativi utilizzare una nota di credito (TD04)."
            )
        return v


class ActiveInvoiceResponse(BaseModel):
    """Response for a single active invoice."""
    id: UUID
    tenant_id: UUID
    numero_fattura: str
    document_type: str
    cliente_piva: str
    cliente_nome: str
    cliente_codice_sdi: str | None = None
    data_fattura: date
    importo_netto: float
    aliquota_iva: float
    importo_iva: float
    importo_totale: float
    descrizione: str | None = None
    sdi_status: str
    sdi_id: str | None = None
    sdi_reject_reason: str | None = None
    raw_xml: str | None = None
    original_invoice_id: UUID | None = None
    original_invoice_numero: str | None = None
    original_invoice_date: date | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class ActiveInvoiceSendResponse(BaseModel):
    """Response from sending an active invoice to SDI."""
    invoice_id: UUID
    sdi_id: str
    sdi_status: str
    message: str


class ActiveInvoiceStatusResponse(BaseModel):
    """Response for SDI delivery status check."""
    invoice_id: UUID
    sdi_id: str | None
    sdi_status: str
    sdi_reject_reason: str | None = None
    message: str


class ActiveInvoiceListResponse(BaseModel):
    """Paginated list of active invoices."""
    items: list[ActiveInvoiceResponse]
    total: int
