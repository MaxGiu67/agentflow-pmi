"""Pydantic schemas for Certificazione Unica (CU) module (US-34)."""

from uuid import UUID

from pydantic import BaseModel


class CUItem(BaseModel):
    """A single CU record."""
    id: UUID
    tenant_id: UUID
    year: int
    percettore_piva: str
    percettore_nome: str
    compenso_lordo: float
    ritenute_operate: float
    netto_corrisposto: float
    contributo_inps: float
    ritenute_versate: float
    has_inps_separato: bool
    warning: str | None = None
    status: str

    model_config = {"from_attributes": True}


class CUListResponse(BaseModel):
    """Response with list of CU records."""
    items: list[CUItem]
    total: int
    year: int


class CUGenerateResponse(BaseModel):
    """Response from CU generation."""
    generated: int
    year: int
    warnings: list[str]
    items: list[CUItem]


class CUExportResponse(BaseModel):
    """Response with exported CU data."""
    id: UUID
    year: int
    percettore_nome: str
    format: str  # csv, telematico
    content: str
    filename: str
