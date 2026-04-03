"""Pydantic schemas for Scadenzario module (US-72, US-73, US-74)."""

from pydantic import BaseModel


class ScadenzaItem(BaseModel):
    """Single scadenza entry for list view."""
    id: str
    controparte: str | None = None
    source_type: str
    source_id: str | None = None
    importo_lordo: float
    importo_netto: float
    importo_iva: float = 0.0
    data_scadenza: str
    data_pagamento: str | None = None
    giorni_residui: int = 0
    stato: str
    importo_pagato: float = 0.0
    anticipata: bool = False
    colore: str = "green"


class ScadenzarioResponse(BaseModel):
    """List of scadenze with totals."""
    tipo: str
    count: int = 0
    items: list[ScadenzaItem] = []
    totals: dict[str, float] = {}


class GenerateResponse(BaseModel):
    """Response from scadenze generation."""
    generated: int
    message: str
