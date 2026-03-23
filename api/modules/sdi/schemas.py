"""Schemas for SDI webhook module (US-07)."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel


class SDIWebhookPayload(BaseModel):
    """Payload received from A-Cube SDI webhook."""
    id_sdi: str
    numero_fattura: str
    emittente_piva: str
    emittente_nome: str | None = None
    data_fattura: date
    importo_totale: float
    importo_netto: float | None = None
    importo_iva: float | None = None
    tipo_documento: str = "TD01"
    xml_content: str | None = None
    signature: str | None = None


class SDIWebhookResponse(BaseModel):
    """Response to SDI webhook."""
    status: str  # accepted, duplicate, error
    invoice_id: UUID | None = None
    message: str
