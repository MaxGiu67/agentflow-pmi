"""Pydantic schemas for Scarico Massivo module."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ClientRegisterRequest(BaseModel):
    client_fiscal_id: str = Field(..., min_length=11, max_length=16, description="P.IVA o CF cliente")
    client_name: str
    onboarding_mode: str = Field("proxy", description="proxy|direct|appointee")


class ConfigResponse(BaseModel):
    id: UUID
    client_fiscal_id: str
    client_name: str
    onboarding_mode: str
    acube_br_uuid: str | None = None
    acube_config_id: str | None = None
    delega_confirmed_at: datetime | None = None
    delega_expires_at: date | None = None
    status: str
    last_sync_at: datetime | None = None
    last_sync_error: str | None = None
    last_sync_new_count: int | None = None
    invoices_downloaded_total: int
    invoices_downloaded_ytd: int
    environment: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ConfigListResponse(BaseModel):
    items: list[ConfigResponse]
    total: int


class SyncRequest(BaseModel):
    since: date | None = None
    until: date | None = None
    direction: str | None = Field(None, description="active|passive|None (both)")


class SyncResponse(BaseModel):
    config_id: UUID
    client_fiscal_id: str
    new_invoices: int
    total_scanned: int
    errors: int
    message: str


class InvoiceLogResponse(BaseModel):
    id: UUID
    codice_univoco_sdi: str
    numero_fattura: str | None
    tipo_documento: str | None
    direction: str
    data_fattura: date | None
    importo_totale: float | None
    controparte_nome: str | None
    imported_into_accounting: bool
    downloaded_at: datetime

    model_config = {"from_attributes": True}


class InvoiceLogListResponse(BaseModel):
    items: list[InvoiceLogResponse]
    total: int


class AppointeeCredentialsRequest(BaseModel):
    """Credenziali Fisconline dell'incaricato — salvate cifrate lato A-Cube."""

    appointee_fiscal_id: str = Field(..., min_length=11, max_length=16)
    password: str = Field(..., min_length=8, max_length=64)
    pin: str = Field(..., min_length=10, max_length=10, pattern=r"^\d{10}$")
    username_or_fiscal_id: str | None = None


class AppointeeCredentialsResponse(BaseModel):
    appointee_fiscal_id: str
    saved: bool
    message: str


class DelegaGuideResponse(BaseModel):
    """Step-by-step guide AdE setup. Differente per modalità."""

    mode: str = "appointee"  # appointee | proxy_delega
    acube_fiscal_id: str
    portale_ade_url: str
    steps: list[str]
    services_to_delegate: list[str]


class OnboardingRequest(BaseModel):
    """Body opzionale per /me/onboarding — permette di scegliere modalità."""

    mode: str | None = Field(None, description="appointee | proxy_delega")
    proxying_fiscal_id: str | None = Field(
        None, description="CF persona fisica per ditte individuali / lavoratori autonomi"
    )
