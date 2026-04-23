"""Pydantic schemas per endpoint A-Cube Open Banking (Pivot 11 US-OB-04).

Separati da `schemas.py` (Salt Edge-based) per chiarezza.
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class InitConnectionRequest(BaseModel):
    """Body per avviare una nuova connessione PSD2 via A-Cube."""

    return_url: str = Field(
        ...,
        description="URL dove rediretto l'utente dopo completamento SCA sulla banca.",
    )
    fiscal_id: str | None = Field(
        default=None,
        description="P.IVA del cliente. Se assente, prende tenant.piva dell'utente loggato.",
    )


class InitConnectionResponse(BaseModel):
    connection_id: UUID
    connect_url: str
    status: str
    fiscal_id: str
    acube_br_uuid: str | None = None


class BankConnectionResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    fiscal_id: str
    business_name: str | None = None
    status: str  # pending, active, expired, disabled
    acube_br_uuid: str | None = None
    acube_enabled: bool
    consent_expires_at: datetime | None = None
    notice_level: int | None = None
    reconnect_url: str | None = None
    last_reconnect_webhook_at: datetime | None = None
    environment: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class ReconnectResponse(BaseModel):
    connection_id: UUID
    reconnect_url: str
    source: str  # webhook_cached | on_demand
    notice_level: int | None = None
    consent_expires_at: datetime | None = None


class BankConnectionListResponse(BaseModel):
    items: list[BankConnectionResponse]
    total: int


class SyncAccountsResponse(BaseModel):
    connection_id: UUID
    accounts_created: int
    accounts_updated: int
    accounts_revoked: int
    message: str


class SyncTransactionsRequest(BaseModel):
    since: date | None = Field(
        default=None,
        description="Backfill da questa data (ISO). Default: 30 giorni fa. A-Cube di default filtra solo mese corrente.",
    )
    until: date | None = Field(default=None, description="Limite superiore (ISO).")
    status: list[str] | None = Field(
        default=None,
        description="Filtra per status A-Cube: pending | booked | canceled.",
    )


class SyncTransactionsResponse(BaseModel):
    connection_id: UUID
    accounts_processed: int
    tx_created: int
    tx_updated: int
    since: str | None = None
    until: str | None = None
    message: str


class SyncNowResponse(BaseModel):
    connection_id: UUID
    accounts_created: int
    accounts_updated: int
    accounts_revoked: int
    accounts_synced: int  # back-compat: created + updated
    tx_created: int
    tx_updated: int
    message: str
