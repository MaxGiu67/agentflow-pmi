"""Pydantic schemas per endpoint A-Cube Open Banking (Pivot 11 US-OB-04).

Separati da `schemas.py` (Salt Edge-based) per chiarezza.
"""

from __future__ import annotations

from datetime import datetime
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
    environment: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class BankConnectionListResponse(BaseModel):
    items: list[BankConnectionResponse]
    total: int


class SyncNowResponse(BaseModel):
    connection_id: UUID
    accounts_synced: int
    message: str
