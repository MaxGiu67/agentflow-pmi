"""Pydantic schemas for active invoices module (US-21 + US-41)."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, field_validator


class InvoiceLineItem(BaseModel):
    """A single line item in the invoice."""
    descrizione: str
    quantita: float = 1.0
    unita_misura: str | None = None  # PZ, KG, NR, etc.
    prezzo_unitario: float
    aliquota_iva: float = 22.0
    natura: str | None = None  # N1-N7 (required when aliquota_iva = 0)

    @field_validator("prezzo_unitario")
    @classmethod
    def validate_prezzo(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Prezzo unitario non può essere negativo")
        return round(v, 2)


class InvoiceClientData(BaseModel):
    """Client (cessionario/committente) data."""
    piva: str | None = None
    codice_fiscale: str | None = None
    denominazione: str
    nome: str | None = None  # for persone fisiche
    cognome: str | None = None
    codice_sdi: str | None = "0000000"
    pec: str | None = None
    # Sede
    indirizzo: str | None = None
    cap: str | None = None
    comune: str | None = None
    provincia: str | None = None
    nazione: str = "IT"


class ActiveInvoiceCreate(BaseModel):
    """Request to create an active invoice with multiple line items."""
    # Client
    cliente: InvoiceClientData
    # Document
    data_fattura: date
    document_type: str = "TD01"
    causale: str | None = None
    # Line items (multi-line)
    linee: list[InvoiceLineItem]
    # Payment override (if different from tenant defaults)
    modalita_pagamento: str | None = None  # MP01-MP23
    condizioni_pagamento: str | None = None  # TP01-TP03
    giorni_pagamento: int | None = None
    iban: str | None = None
    # For credit notes (TD04)
    original_invoice_numero: str | None = None
    original_invoice_date: date | None = None

    @field_validator("linee")
    @classmethod
    def validate_linee(cls, v: list[InvoiceLineItem]) -> list[InvoiceLineItem]:
        if len(v) == 0:
            raise ValueError("La fattura deve avere almeno una riga")
        return v

    @field_validator("document_type")
    @classmethod
    def validate_doc_type(cls, v: str) -> str:
        valid = ["TD01", "TD02", "TD03", "TD04", "TD05", "TD06", "TD24", "TD25"]
        if v not in valid:
            raise ValueError(f"Tipo documento non valido: {v}. Valori: {', '.join(valid)}")
        return v


# Legacy single-line create (backwards compatible)
class ActiveInvoiceCreateLegacy(BaseModel):
    """Legacy request (single line). Converted to multi-line internally."""
    cliente_piva: str
    cliente_nome: str
    cliente_codice_sdi: str | None = None
    data_fattura: date
    importo_netto: float
    aliquota_iva: float = 22.0
    descrizione: str | None = None
    document_type: str = "TD01"
    original_invoice_id: UUID | None = None
    original_invoice_numero: str | None = None
    original_invoice_date: date | None = None

    @field_validator("importo_netto")
    @classmethod
    def validate_importo(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Importo deve essere positivo")
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
