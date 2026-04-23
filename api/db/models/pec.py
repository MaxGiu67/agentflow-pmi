"""PEC configuration per tenant — encrypted SMTP/IMAP credentials for invoice sending to SDI."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from api.db.models.base import Base


class TenantPecConfig(Base):
    """PEC SMTP/IMAP credentials per tenant (encrypted password)."""

    __tablename__ = "tenant_pec_config"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)  # aruba|namirial|poste|legalmail|custom
    pec_address: Mapped[str] = mapped_column(String(255), nullable=False)
    smtp_host: Mapped[str] = mapped_column(String(255), nullable=False)
    smtp_port: Mapped[int] = mapped_column(Integer, nullable=False, default=465)
    imap_host: Mapped[str] = mapped_column(String(255), nullable=False)
    imap_port: Mapped[int] = mapped_column(Integer, nullable=False, default=993)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    password_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    last_test_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_test_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class PecMessage(Base):
    """Sent/received PEC messages — tracks SDI delivery via PEC."""

    __tablename__ = "pec_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    active_invoice_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)  # sent|received
    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    message_id: Mapped[str | None] = mapped_column(String(500), nullable=True)  # SMTP Message-ID
    recipient: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sender: Mapped[str | None] = mapped_column(String(255), nullable=True)
    attachment_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    receipt_type: Mapped[str | None] = mapped_column(String(10), nullable=True)  # RC|NS|MC|NE|DT|AT|EC|SE
    raw_headers: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
