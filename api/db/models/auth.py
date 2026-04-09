"""Auth-related models: Tenant, TenantUsage, TenantSetting, User, OnboardingState."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, JSON, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from api.db.models.base import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)  # srl, srls, piva, ditta_individuale
    regime_fiscale: Mapped[str] = mapped_column(String(50), nullable=False)  # forfettario, semplificato, ordinario
    codice_ateco: Mapped[str | None] = mapped_column(String(10))
    piva: Mapped[str | None] = mapped_column(String(11), unique=True)
    codice_fiscale: Mapped[str | None] = mapped_column(String(16))
    odoo_db_name: Mapped[str | None] = mapped_column(String(100))
    subscription_tier: Mapped[str] = mapped_column(String(20), default="starter")

    # Fatturazione — Sede (US-42)
    sede_indirizzo: Mapped[str | None] = mapped_column(String(255))
    sede_numero_civico: Mapped[str | None] = mapped_column(String(10))
    sede_cap: Mapped[str | None] = mapped_column(String(5))
    sede_comune: Mapped[str | None] = mapped_column(String(100))
    sede_provincia: Mapped[str | None] = mapped_column(String(2))
    sede_nazione: Mapped[str | None] = mapped_column(String(2), default="IT")

    # Fatturazione — Regime fiscale SDI (RF01-RF19)
    regime_fiscale_sdi: Mapped[str | None] = mapped_column(String(4), default="RF01")

    # Fatturazione — Pagamento (US-42)
    iban: Mapped[str | None] = mapped_column(String(34))
    banca_nome: Mapped[str | None] = mapped_column(String(100))
    bic: Mapped[str | None] = mapped_column(String(11))
    modalita_pagamento: Mapped[str | None] = mapped_column(String(4), default="MP05")  # MP01-MP23
    condizioni_pagamento: Mapped[str | None] = mapped_column(String(4), default="TP02")  # TP01-TP03
    giorni_pagamento: Mapped[int | None] = mapped_column(Integer, default=30)

    # Fatturazione — REA (opzionale, per società)
    rea_ufficio: Mapped[str | None] = mapped_column(String(2))
    rea_numero: Mapped[str | None] = mapped_column(String(20))
    rea_capitale_sociale: Mapped[float | None] = mapped_column(Float)
    rea_socio_unico: Mapped[str | None] = mapped_column(String(2))  # SU/SM
    rea_stato_liquidazione: Mapped[str | None] = mapped_column(String(2), default="LN")  # LN/LS

    # Contatti
    telefono: Mapped[str | None] = mapped_column(String(20))
    email_aziendale: Mapped[str | None] = mapped_column(String(255))
    pec: Mapped[str | None] = mapped_column(String(255))

    # Email marketing per tenant
    sender_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sender_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sender_domain: Mapped[str | None] = mapped_column(String(100), nullable=True)
    email_quota_monthly: Mapped[int] = mapped_column(Integer, default=5000)
    email_sent_month: Mapped[int] = mapped_column(Integer, default=0)
    email_month_reset: Mapped[str | None] = mapped_column(String(7), nullable=True)  # "2026-04"

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class TenantUsage(Base):
    """Monthly usage counters per tenant for metering/billing."""
    __tablename__ = "tenant_usage"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    month: Mapped[str] = mapped_column(String(7), nullable=False)  # "2026-04"
    llm_tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    llm_tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    llm_requests: Mapped[int] = mapped_column(Integer, default=0)
    pdf_pages: Mapped[int] = mapped_column(Integer, default=0)
    api_calls: Mapped[int] = mapped_column(Integer, default=0)
    email_sent: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class TenantSetting(Base):
    """Encrypted per-tenant configuration (API keys, integrations)."""
    __tablename__ = "tenant_settings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    value_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(20), default="platform")  # platform, custom
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="viewer")  # owner, admin, commerciale, viewer
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    sender_email: Mapped[str | None] = mapped_column(String(255), nullable=True)  # email for Brevo sender
    sender_name: Mapped[str | None] = mapped_column(String(255), nullable=True)  # name for Brevo sender
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verification_token: Mapped[str | None] = mapped_column(String(255))
    password_reset_token: Mapped[str | None] = mapped_column(String(255))
    password_reset_expires: Mapped[datetime | None] = mapped_column(DateTime)
    spid_token: Mapped[str | None] = mapped_column(Text)  # encrypted AES-256
    spid_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime)
    # US-138→US-140: Roles & External users
    user_type: Mapped[str] = mapped_column(String(50), default="internal")  # internal, external, admin
    access_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    crm_role_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    default_origin_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    default_product_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    # US-153: Microsoft 365 Calendar
    microsoft_token: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON: {access_token, refresh_token, expires_at}
    calendly_url: Mapped[str | None] = mapped_column(String(500), nullable=True)  # US-155
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class OnboardingState(Base):
    __tablename__ = "onboarding_states"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, nullable=False)
    step_completed: Mapped[int] = mapped_column(Integer, default=0)  # 0-4
    step1_profile: Mapped[bool] = mapped_column(Boolean, default=False)
    step2_piva: Mapped[bool] = mapped_column(Boolean, default=False)
    step3_spid: Mapped[bool] = mapped_column(Boolean, default=False)
    step4_sync: Mapped[bool] = mapped_column(Boolean, default=False)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
