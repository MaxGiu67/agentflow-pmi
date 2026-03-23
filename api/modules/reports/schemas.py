"""Schemas for reports module (US-19)."""

from datetime import date

from pydantic import BaseModel


class InvoiceSummaryItem(BaseModel):
    """Summary of an invoice for the report."""
    numero_fattura: str
    emittente_nome: str | None = None
    data_fattura: date | None = None
    importo_netto: float | None = None
    importo_iva: float | None = None
    importo_totale: float | None = None
    category: str | None = None
    verified: bool = False


class ReportData(BaseModel):
    """Data for the commercialista report."""
    period: str
    period_start: date
    period_end: date
    format: str  # pdf, csv
    tenant_name: str
    tenant_piva: str | None = None
    regime_fiscale: str

    # Summary
    total_fatture_attive: int = 0
    total_fatture_passive: int = 0
    totale_ricavi: float = 0.0
    totale_costi: float = 0.0
    totale_iva_credito: float = 0.0
    totale_iva_debito: float = 0.0
    saldo_iva: float = 0.0

    # Category breakdown
    costi_per_categoria: dict[str, float] = {}
    ricavi_per_categoria: dict[str, float] = {}

    # Invoice lists
    fatture_attive: list[InvoiceSummaryItem] = []
    fatture_passive: list[InvoiceSummaryItem] = []

    # Uncategorized invoices
    fatture_non_categorizzate: list[InvoiceSummaryItem] = []
    has_uncategorized: bool = False

    message: str = ""


class ReportErrorResponse(BaseModel):
    """Error response for report generation."""
    detail: str
