"""Scarico Massivo Cassetto Fiscale — A-Cube integration for bulk invoice download.

Contract NexaData 10/04/2026: €600/year, 5 P.IVA, 5.000 invoices/year.
Each tenant can register up to 50 client P.IVA under their A-Cube account
(proxy mode: clients delegate A-Cube P.IVA 10442360961 on AdE portal).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from api.db.models.base import Base


class ScaricoMassivoConfig(Base):
    """Per-client configuration for Scarico Massivo.

    One row per (tenant, P.IVA cliente). A tenant can manage multiple client P.IVAs.
    """

    __tablename__ = "scarico_massivo_config"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    # Client data
    client_fiscal_id: Mapped[str] = mapped_column(String(20), nullable=False)  # P.IVA / CF
    client_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Onboarding modality (proxy is recommended)
    onboarding_mode: Mapped[str] = mapped_column(String(20), default="proxy")  # proxy|direct|appointee

    # A-Cube IDs (filled after creating BusinessRegistry + Configuration)
    acube_br_uuid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    acube_config_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Delega tracking (proxy mode)
    delega_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    delega_expires_at: Mapped[date | None] = mapped_column(Date, nullable=True)  # 31/12 of 4th year

    # Sync state
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|active|expired|error|disabled
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_sync_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_sync_new_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Counters for quota monitoring (contract: 5.000 fatture/anno)
    invoices_downloaded_total: Mapped[int] = mapped_column(Integer, default=0)
    invoices_downloaded_ytd: Mapped[int] = mapped_column(Integer, default=0)

    environment: Mapped[str] = mapped_column(String(20), default="sandbox")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class ScaricoFatturaLog(Base):
    """Log of each downloaded invoice — dedupe key + tracking."""

    __tablename__ = "scarico_fatture_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    config_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    client_fiscal_id: Mapped[str] = mapped_column(String(20), nullable=False)

    # Dedupe key — SDI unique document code
    codice_univoco_sdi: Mapped[str] = mapped_column(String(100), nullable=False)
    numero_fattura: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tipo_documento: Mapped[str | None] = mapped_column(String(10), nullable=True)  # TD01, TD04, TD17...
    direction: Mapped[str] = mapped_column(String(10), nullable=False)  # active|passive
    data_fattura: Mapped[date | None] = mapped_column(Date, nullable=True)
    importo_totale: Mapped[float | None] = mapped_column(Float, nullable=True)
    controparte_piva: Mapped[str | None] = mapped_column(String(20), nullable=True)
    controparte_nome: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Raw XML stored for traceability
    raw_xml: Mapped[str | None] = mapped_column(Text, nullable=True)
    acube_invoice_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Linked to accounting invoice once imported
    linked_invoice_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    imported_into_accounting: Mapped[bool] = mapped_column(Boolean, default=False)

    downloaded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
