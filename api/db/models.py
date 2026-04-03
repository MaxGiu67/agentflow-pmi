import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Float, Integer, JSON, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


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

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="viewer")  # owner, admin, viewer
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verification_token: Mapped[str | None] = mapped_column(String(255))
    password_reset_token: Mapped[str | None] = mapped_column(String(255))
    password_reset_expires: Mapped[datetime | None] = mapped_column(DateTime)
    spid_token: Mapped[str | None] = mapped_column(Text)  # encrypted AES-256
    spid_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)  # attiva, passiva
    document_type: Mapped[str] = mapped_column(String(10), nullable=False, default="TD01")  # TD01, TD04, ...
    source: Mapped[str] = mapped_column(String(30), nullable=False)  # cassetto_fiscale, sdi, email, upload
    numero_fattura: Mapped[str] = mapped_column(String(100), nullable=False)
    emittente_piva: Mapped[str] = mapped_column(String(20), nullable=False)
    emittente_nome: Mapped[str | None] = mapped_column(String(255))
    data_fattura: Mapped[date | None] = mapped_column(Date)
    importo_netto: Mapped[float | None] = mapped_column(Float)
    importo_iva: Mapped[float | None] = mapped_column(Float)
    importo_totale: Mapped[float | None] = mapped_column(Float)
    raw_xml: Mapped[str | None] = mapped_column(Text)
    structured_data: Mapped[dict | None] = mapped_column(JSON)
    category: Mapped[str | None] = mapped_column(String(100))
    category_confidence: Mapped[float | None] = mapped_column(Float)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    processing_status: Mapped[str] = mapped_column(String(30), default="pending")  # pending, parsed, categorized, registered, error
    has_ritenuta: Mapped[bool] = mapped_column(Boolean, default=False)
    has_bollo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class AgentEvent(Base):
    __tablename__ = "agent_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(30), default="published")  # published, consumed, dead_letter
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class CategorizationFeedback(Base):
    __tablename__ = "categorization_feedback"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    invoice_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    suggested_category: Mapped[str | None] = mapped_column(String(100))
    final_category: Mapped[str] = mapped_column(String(100), nullable=False)
    was_correct: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_debit: Mapped[float] = mapped_column(Float, default=0.0)
    total_credit: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft, posted, error
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    odoo_move_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class JournalLine(Base):
    __tablename__ = "journal_lines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entry_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    account_code: Mapped[str] = mapped_column(String(20), nullable=False)
    account_name: Mapped[str] = mapped_column(String(255), nullable=False)
    debit: Mapped[float] = mapped_column(Float, default=0.0)
    credit: Mapped[float] = mapped_column(Float, default=0.0)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


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


class FiscalRule(Base):
    __tablename__ = "fiscal_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[str] = mapped_column(String(255), nullable=False)
    value_type: Mapped[str] = mapped_column(String(20), nullable=False)  # decimal, integer, boolean, string
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    law_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ChartAccount(Base):
    __tablename__ = "chart_accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_type: Mapped[str] = mapped_column(String(30), nullable=False)  # asset, liability, equity, income, expense
    cee_code: Mapped[str | None] = mapped_column(String(20), nullable=True)  # bilancio CEE mapping
    cee_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class NotificationConfig(Base):
    """Notification channel configuration for a user (US-18)."""
    __tablename__ = "notification_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)  # telegram, whatsapp
    chat_id: Mapped[str | None] = mapped_column(String(100), nullable=True)  # Telegram chat ID
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)  # WhatsApp phone
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class NotificationLog(Base):
    """Log of sent notifications (US-18)."""
    __tablename__ = "notification_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    message_type: Mapped[str] = mapped_column(String(50), nullable=False)  # scadenza, digest
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="sent")  # sent, failed, retry, fallback_email
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class EmailConnection(Base):
    """Email connector state for Gmail OAuth or PEC/IMAP."""
    __tablename__ = "email_connections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    provider: Mapped[str] = mapped_column(String(20), nullable=False)  # gmail, imap
    email_address: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, connected, error
    credentials_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class ActiveInvoice(Base):
    """Active invoice (fattura attiva) for SDI sending (US-21)."""
    __tablename__ = "active_invoices"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    numero_fattura: Mapped[str] = mapped_column(String(100), nullable=False)
    document_type: Mapped[str] = mapped_column(String(10), nullable=False, default="TD01")  # TD01, TD04
    cliente_piva: Mapped[str] = mapped_column(String(20), nullable=False)
    cliente_nome: Mapped[str] = mapped_column(String(255), nullable=False)
    cliente_codice_sdi: Mapped[str | None] = mapped_column(String(7), nullable=True)
    data_fattura: Mapped[date] = mapped_column(Date, nullable=False)
    importo_netto: Mapped[float] = mapped_column(Float, nullable=False)
    aliquota_iva: Mapped[float] = mapped_column(Float, nullable=False, default=22.0)
    importo_iva: Mapped[float] = mapped_column(Float, nullable=False)
    importo_totale: Mapped[float] = mapped_column(Float, nullable=False)
    descrizione: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_xml: Mapped[str | None] = mapped_column(Text, nullable=True)
    sdi_status: Mapped[str] = mapped_column(String(30), default="draft")  # draft, sent, delivered, rejected
    sdi_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sdi_reject_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    original_invoice_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)  # for TD04 credit notes
    original_invoice_numero: Mapped[str | None] = mapped_column(String(100), nullable=True)
    original_invoice_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class BankAccount(Base):
    """Connected bank account via Open Banking (US-24)."""
    __tablename__ = "bank_accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    iban: Mapped[str] = mapped_column(String(34), nullable=False)
    bank_name: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, default="cbi_globe")  # cbi_globe, manual
    consent_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    consent_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    balance: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, connected, revoked, expired
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class BankTransaction(Base):
    """Bank transaction from Open Banking sync or PDF import (US-24, US-44)."""
    __tablename__ = "bank_transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bank_account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    transaction_id: Mapped[str] = mapped_column(String(255), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    value_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)  # credit, debit
    counterpart: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    reconciled: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="open_banking")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class BankStatementImport(Base):
    """Log of bank statement PDF/CSV imports (US-44, US-45)."""
    __tablename__ = "bank_statement_imports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    bank_account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    filename: Mapped[str | None] = mapped_column(String(500), nullable=True)
    period_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    extraction_method: Mapped[str] = mapped_column(String(20), nullable=False, default="llm")
    movements_count: Mapped[int] = mapped_column(Integer, default=0)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Corrispettivo(Base):
    """Daily receipt total from electronic cash register (US-47)."""
    __tablename__ = "corrispettivi"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    data: Mapped[date] = mapped_column(Date, nullable=False)
    dispositivo_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    piva_esercente: Mapped[str | None] = mapped_column(String(11), nullable=True)
    aliquota_iva: Mapped[float | None] = mapped_column(Float, nullable=True)
    imponibile: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    imposta: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    totale_contanti: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    totale_elettronico: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    num_documenti: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="import_xml")
    journal_entry_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    raw_xml: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class ImportPromptTemplate(Base):
    """Saved LLM prompt templates optimized per tenant/format (US-74 Self-Healing)."""
    __tablename__ = "import_prompt_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)  # banca, paghe, f24, bilancio
    format_key: Mapped[str] = mapped_column(String(255), nullable=False, default="default")  # e.g. "unicredit", "zucchetti"
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    failure_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class ImportException(Base):
    """Exception/anomaly from an import that requires user attention (US-71)."""
    __tablename__ = "import_exceptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)  # fatture, banca, corrispettivi, paghe
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="warning")  # info, warning, error
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    action_label: Mapped[str | None] = mapped_column(String(100), nullable=True)  # "Verifica", "Categorizza", "Correggi"
    action_url: Mapped[str | None] = mapped_column(String(500), nullable=True)  # deep link
    related_entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class CompletenessScore(Base):
    """Tracks which data sources are connected and what features are unlocked (US-69)."""
    __tablename__ = "completeness_scores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)  # fatture, banca, paghe, corrispettivi, bilancio, f24
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="not_configured")  # connected, pending, not_configured
    last_sync: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class VatSettlement(Base):
    """VAT settlement (liquidazione IVA) record (US-22)."""
    __tablename__ = "vat_settlements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    quarter: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-4
    iva_vendite: Mapped[float] = mapped_column(Float, default=0.0)  # IVA a debito (vendite)
    iva_acquisti: Mapped[float] = mapped_column(Float, default=0.0)  # IVA a credito (acquisti)
    iva_reverse_charge_debito: Mapped[float] = mapped_column(Float, default=0.0)
    iva_reverse_charge_credito: Mapped[float] = mapped_column(Float, default=0.0)
    credito_periodo_precedente: Mapped[float] = mapped_column(Float, default=0.0)
    interessi: Mapped[float] = mapped_column(Float, default=0.0)  # 1% trimestrale
    saldo: Mapped[float] = mapped_column(Float, default=0.0)  # positive = debito, negative = credito
    unregistered_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="computed")  # computed, confirmed
    computed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class FiscalDeadline(Base):
    """Fiscal deadline instance (e.g. F24 ritenuta, bollo trimestrale) (US-33, US-35)."""
    __tablename__ = "fiscal_deadlines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)  # 1040, 2501, etc.
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, paid, overdue
    source_invoice_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class WithholdingTax(Base):
    """Withholding tax (ritenuta d'acconto) record (US-33)."""
    __tablename__ = "withholding_taxes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    invoice_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tipo_ritenuta: Mapped[str] = mapped_column(String(10), nullable=False)  # RT01, RT02, etc.
    aliquota: Mapped[float] = mapped_column(Float, nullable=False)  # e.g. 20.0
    causale_pagamento: Mapped[str | None] = mapped_column(String(10), nullable=True)  # A, B, etc.
    importo_ritenuta: Mapped[float] = mapped_column(Float, nullable=False)
    imponibile_ritenuta: Mapped[float] = mapped_column(Float, nullable=False)
    importo_netto: Mapped[float] = mapped_column(Float, nullable=False)  # total - ritenuta
    f24_code: Mapped[str] = mapped_column(String(10), default="1040")
    f24_due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="detected")  # detected, registered, paid
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Reconciliation(Base):
    """Reconciliation between bank transaction and invoice (US-26)."""
    __tablename__ = "reconciliations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    transaction_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    match_type: Mapped[str] = mapped_column(String(20), nullable=False)  # exact, fuzzy, manual, partial
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    amount_matched: Mapped[float] = mapped_column(Float, default=0.0)
    amount_remaining: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    exchange_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    original_amount: Mapped[float | None] = mapped_column(Float, nullable=True)  # foreign currency
    original_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="matched")  # matched, partial, unmatched
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class StampDuty(Base):
    """Stamp duty (imposta di bollo) record (US-35)."""
    __tablename__ = "stamp_duties"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    invoice_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    importo_bollo: Mapped[float] = mapped_column(Float, default=2.0)
    importo_esente: Mapped[float] = mapped_column(Float, default=0.0)  # exempt amount on the invoice
    bollo_virtuale: Mapped[bool] = mapped_column(Boolean, default=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    quarter: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# ============================================================
# Sprint 8: US-29/30 — Note Spese
# ============================================================


class Expense(Base):
    """Expense report entry (US-29, US-30)."""
    __tablename__ = "expenses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    amount_eur: Mapped[float] = mapped_column(Float, nullable=False)  # converted amount
    exchange_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    category_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    receipt_file: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocr_readable: Mapped[bool] = mapped_column(Boolean, default=True)
    expense_date: Mapped[date] = mapped_column(Date, nullable=False)
    policy_warning: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="submitted")  # submitted, approved, rejected, reimbursed, reimburse_failed
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    journal_entry_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class ExpensePolicy(Base):
    """Expense policy rules (US-29)."""
    __tablename__ = "expense_policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    max_amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# ============================================================
# Sprint 8: US-31/32 — Cespiti
# ============================================================


class Asset(Base):
    """Fixed asset (cespite) record (US-31, US-32)."""
    __tablename__ = "assets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    purchase_date: Mapped[date] = mapped_column(Date, nullable=False)
    purchase_amount: Mapped[float] = mapped_column(Float, nullable=False)
    depreciable_amount: Mapped[float] = mapped_column(Float, nullable=False)  # valore ammortizzabile
    depreciation_rate: Mapped[float] = mapped_column(Float, nullable=False)  # % annuale
    accumulated_depreciation: Mapped[float] = mapped_column(Float, default=0.0)  # fondo ammortamento
    residual_value: Mapped[float] = mapped_column(Float, nullable=False)  # valore residuo
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)  # cespite usato (no IVA)
    status: Mapped[str] = mapped_column(String(30), default="active")  # active, disposed, scrapped, fully_depreciated
    disposal_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    disposal_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    gain_loss: Mapped[float | None] = mapped_column(Float, nullable=True)  # plus/minusvalenza
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


# ============================================================
# Sprint 8: US-36 — Ratei e Risconti
# ============================================================


class Accrual(Base):
    """Accrual/deferral (rateo/risconto) record (US-36)."""
    __tablename__ = "accruals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    type: Mapped[str] = mapped_column(String(20), nullable=False)  # risconto_attivo, risconto_passivo, rateo_attivo, rateo_passivo
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    total_amount: Mapped[float] = mapped_column(Float, nullable=False)
    current_year_amount: Mapped[float] = mapped_column(Float, nullable=False)
    deferred_amount: Mapped[float] = mapped_column(Float, nullable=False)  # quota rinviata
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="proposed")  # proposed, confirmed
    journal_entry_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reversal_entry_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


# ============================================================
# Sprint 9: US-34 — Certificazione Unica (CU)
# ============================================================


class CertificazioneUnica(Base):
    """Certificazione Unica (CU) record (US-34)."""
    __tablename__ = "certificazioni_uniche"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    percettore_piva: Mapped[str] = mapped_column(String(20), nullable=False)
    percettore_nome: Mapped[str] = mapped_column(String(255), nullable=False)
    compenso_lordo: Mapped[float] = mapped_column(Float, nullable=False)
    ritenute_operate: Mapped[float] = mapped_column(Float, nullable=False)
    netto_corrisposto: Mapped[float] = mapped_column(Float, nullable=False)
    contributo_inps: Mapped[float] = mapped_column(Float, default=0.0)  # 4% INPS
    ritenute_versate: Mapped[float] = mapped_column(Float, default=0.0)
    has_inps_separato: Mapped[bool] = mapped_column(Boolean, default=False)
    warning: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="generated")  # generated, exported
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# ============================================================
# Sprint 9: US-37 — Conservazione Digitale
# ============================================================


class DigitalPreservation(Base):
    """Digital preservation (conservazione digitale) record (US-37)."""
    __tablename__ = "digital_preservations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    invoice_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)  # aruba, infocert
    batch_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    package_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)  # SHA-256
    status: Mapped[str] = mapped_column(String(20), default="queued")  # queued, sent, confirmed, rejected
    reject_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


# ============================================================
# Sprint 9: US-27 — Pagamenti PISP
# ============================================================


class Payment(Base):
    """Payment (pagamento fornitore) record via PISP (US-27)."""
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    bank_account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    invoice_ids: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # list of invoice UUIDs
    beneficiary_name: Mapped[str] = mapped_column(String(255), nullable=False)
    beneficiary_iban: Mapped[str] = mapped_column(String(34), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    causale: Mapped[str | None] = mapped_column(String(500), nullable=True)
    payment_type: Mapped[str] = mapped_column(String(20), default="single")  # single, batch
    sca_status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, authorized, completed, failed
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    reconciled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


# ============================================================
# Sprint 9: US-28 — Monitor Normativo
# ============================================================


class NormativeAlert(Base):
    """Normative alert from RSS feed monitoring (US-28)."""
    __tablename__ = "normative_alerts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)  # gazzetta_ufficiale, agenzia_entrate
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)  # decorrenza
    impact_preview: Mapped[str | None] = mapped_column(Text, nullable=True)
    proposed_rule_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    proposed_rule_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="new")  # new, reviewed, applied, scheduled
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# ============================================================
# Sprint 10: US-38 — F24 Compilazione e Generazione
# ============================================================


class F24Document(Base):
    """F24 tax payment document (US-38)."""
    __tablename__ = "f24_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    period_month: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-12 for monthly
    period_quarter: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-4 for quarterly
    sections: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # {erario: [...], crediti: [...]}
    total_debit: Mapped[float] = mapped_column(Float, default=0.0)
    total_credit: Mapped[float] = mapped_column(Float, default=0.0)
    net_amount: Mapped[float] = mapped_column(Float, default=0.0)  # debit - credit
    fisco_api_amount: Mapped[float | None] = mapped_column(Float, nullable=True)  # amount from FiscoAPI
    amount_difference: Mapped[float | None] = mapped_column(Float, nullable=True)  # fisco - estimate
    status: Mapped[str] = mapped_column(String(20), default="generated")  # generated, exported, paid
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


# ============================================================
# Sprint 10: US-40 — Budget vs Consuntivo
# ============================================================


class Budget(Base):
    """Budget entry per month and category (US-40)."""
    __tablename__ = "budgets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-12
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    label: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    budget_amount: Mapped[float] = mapped_column(Float, default=0.0)
    actual_amount: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class BudgetMeta(Base):
    """Wizard metadata for budget — stores inputs for re-editing."""
    __tablename__ = "budget_meta"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    sector_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    fatturato: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    n_dipendenti: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ral_media: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    costo_personale_diretto: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    personnel_mode: Mapped[Optional[str]] = mapped_column(String(10), nullable=True, default="calc")
    overrides_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    custom_costs_json: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    extra_revenues_json: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# ============================================================
# Pivot 6: US-84 — Scadenzario Attivo/Passivo
# ============================================================


class Scadenza(Base):
    """Payment deadline from invoices, payroll, loans, contracts (US-84)."""
    __tablename__ = "scadenze"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tipo: Mapped[str] = mapped_column(String(10), nullable=False)  # attivo, passivo
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)  # fattura, stipendio, f24, mutuo, contratto
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    controparte: Mapped[str | None] = mapped_column(String(255), nullable=True)
    importo_lordo: Mapped[float] = mapped_column(Float, nullable=False)
    importo_netto: Mapped[float] = mapped_column(Float, nullable=False)
    importo_iva: Mapped[float] = mapped_column(Float, default=0.0)
    data_scadenza: Mapped[date] = mapped_column(Date, nullable=False)
    data_pagamento: Mapped[date | None] = mapped_column(Date, nullable=True)
    stato: Mapped[str] = mapped_column(String(20), default="aperto")  # aperto, pagato, insoluto, parziale
    importo_pagato: Mapped[float] = mapped_column(Float, default=0.0)
    banca_appoggio_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)  # FK BankAccount
    anticipata: Mapped[bool] = mapped_column(Boolean, default=False)
    anticipo_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)  # FK InvoiceAdvance (future)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


# ============================================================
# Pivot 6: US-85 — Fidi Bancari
# ============================================================


class BankFacility(Base):
    """Bank credit facility for invoice advances (US-85)."""
    __tablename__ = "bank_facilities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    bank_account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)  # FK BankAccount
    tipo: Mapped[str] = mapped_column(String(30), nullable=False, default="anticipo_fatture")  # anticipo_fatture, sbf, riba
    plafond: Mapped[float] = mapped_column(Float, nullable=False)
    percentuale_anticipo: Mapped[float] = mapped_column(Float, nullable=False, default=80.0)  # % of invoice
    tasso_interesse_annuo: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    commissione_presentazione_pct: Mapped[float] = mapped_column(Float, default=0.0)
    commissione_incasso: Mapped[float] = mapped_column(Float, default=0.0)  # EUR per invoice
    commissione_insoluto: Mapped[float] = mapped_column(Float, default=0.0)  # EUR per insoluto
    giorni_max: Mapped[int] = mapped_column(Integer, default=120)
    attivo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


# ============================================================
# Pivot 6: US-86 — Anticipo Fatture
# ============================================================


class InvoiceAdvance(Base):
    """Single invoice advance tracking (US-86)."""
    __tablename__ = "invoice_advances"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    facility_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)  # FK BankFacility
    invoice_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)  # FK Invoice
    importo_fattura: Mapped[float] = mapped_column(Float, nullable=False)
    importo_anticipato: Mapped[float] = mapped_column(Float, nullable=False)
    commissione: Mapped[float] = mapped_column(Float, default=0.0)
    interessi_stimati: Mapped[float] = mapped_column(Float, default=0.0)
    interessi_effettivi: Mapped[float | None] = mapped_column(Float, nullable=True)
    data_presentazione: Mapped[date] = mapped_column(Date, nullable=False)
    data_scadenza_prevista: Mapped[date] = mapped_column(Date, nullable=False)
    data_chiusura: Mapped[date | None] = mapped_column(Date, nullable=True)
    stato: Mapped[str] = mapped_column(String(20), default="attivo")  # attivo, incassato, insoluto
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


# ============================================================
# Pivot 7: US-87/88/89 — CRM Interno
# ============================================================


class CrmContact(Base):
    """CRM contact (azienda cliente/lead/prospect) — US-87."""
    __tablename__ = "crm_contacts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(20), default="lead")  # lead, prospect, cliente, ex_cliente
    piva: Mapped[str | None] = mapped_column(String(11), nullable=True)
    codice_fiscale: Mapped[str | None] = mapped_column(String(16), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    province: Mapped[str | None] = mapped_column(String(2), nullable=True)
    sector: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)  # web, referral, evento, cold
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    email_opt_in: Mapped[bool] = mapped_column(Boolean, default=True)
    last_contact_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class CrmPipelineStage(Base):
    """CRM pipeline stage — US-88."""
    __tablename__ = "crm_pipeline_stages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    probability_default: Mapped[float] = mapped_column(Float, default=0.0)
    color: Mapped[str] = mapped_column(String(7), default="#6B7280")
    is_won: Mapped[bool] = mapped_column(Boolean, default=False)
    is_lost: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class CrmDeal(Base):
    """CRM deal/opportunity — US-88."""
    __tablename__ = "crm_deals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    contact_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    stage_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    deal_type: Mapped[str | None] = mapped_column(String(20), nullable=True)  # T&M, fixed, spot, hardware
    expected_revenue: Mapped[float] = mapped_column(Float, default=0.0)
    daily_rate: Mapped[float] = mapped_column(Float, default=0.0)
    estimated_days: Mapped[float] = mapped_column(Float, default=0.0)
    technology: Mapped[str | None] = mapped_column(String(255), nullable=True)
    probability: Mapped[float] = mapped_column(Float, default=10.0)
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    expected_close_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    order_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    order_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    order_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    order_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    lost_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class CrmActivity(Base):
    """CRM activity (call, email, meeting, note) — US-89."""
    __tablename__ = "crm_activities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    deal_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    contact_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    type: Mapped[str] = mapped_column(String(20), nullable=False)  # call, email, meeting, note, task
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="planned")  # planned, completed, cancelled
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# ============================================================
# Pivot 7: US-92/93/94 — Email Marketing (Brevo)
# ============================================================


class EmailTemplate(Base):
    """Email template with variables — US-94."""
    __tablename__ = "email_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    html_body: Mapped[str] = mapped_column(Text, nullable=False)
    text_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    variables: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    category: Mapped[str] = mapped_column(String(50), default="followup")  # welcome, followup, proposal, reminder, nurture
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class EmailCampaign(Base):
    """Email campaign (single/sequence/trigger) — US-97."""
    __tablename__ = "email_campaigns"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[str] = mapped_column(String(20), default="single")  # single, sequence, trigger
    trigger_event: Mapped[str | None] = mapped_column(String(50), nullable=True)
    trigger_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft, active, paused, completed
    stats_sent: Mapped[int] = mapped_column(Integer, default=0)
    stats_opened: Mapped[int] = mapped_column(Integer, default=0)
    stats_clicked: Mapped[int] = mapped_column(Integer, default=0)
    stats_bounced: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class EmailSend(Base):
    """Single email send with tracking — US-93/95."""
    __tablename__ = "email_sends"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    contact_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    template_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    brevo_message_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    subject_sent: Mapped[str] = mapped_column(String(255), nullable=False)
    to_email: Mapped[str] = mapped_column(String(255), nullable=False)
    to_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    status: Mapped[str] = mapped_column(String(20), default="sent")  # queued, sent, delivered, opened, clicked, bounced, failed
    opened_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    clicked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    open_count: Mapped[int] = mapped_column(Integer, default=0)
    click_count: Mapped[int] = mapped_column(Integer, default=0)


class EmailEvent(Base):
    """Email tracking event from Brevo webhook — US-93."""
    __tablename__ = "email_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    send_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(20), nullable=False)  # delivered, opened, clicked, hard_bounce, soft_bounce, unsubscribed, spam
    url_clicked: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    raw_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class EmailSequenceStep(Base):
    """Step in an email sequence — US-97."""
    __tablename__ = "email_sequence_steps"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    template_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    delay_days: Mapped[int] = mapped_column(Integer, default=0)
    delay_hours: Mapped[int] = mapped_column(Integer, default=0)
    condition_type: Mapped[str] = mapped_column(String(30), default="none")  # none, if_opened, if_not_opened, if_clicked
    condition_link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    skip_if_replied: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class EmailSequenceEnrollment(Base):
    """Enrollment of a contact in a sequence — US-97/98."""
    __tablename__ = "email_sequence_enrollments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    campaign_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    contact_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    current_step: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="active")  # active, completed, paused, cancelled
    next_send_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


# ============================================================
# Sprint 11: US-A01/A02/A04 — Agentic System (Chat, Orchestrator)
# ============================================================


class DashboardLayout(Base):
    """User dashboard layout with draggable widgets."""
    __tablename__ = "dashboard_layouts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(100), default="default")
    year: Mapped[int] = mapped_column(Integer, default=2024)
    widgets: Mapped[dict | None] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class Conversation(Base):
    """Chat conversation (US-A02)."""
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")  # active, archived, deleted
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class Message(Base):
    """Chat message within a conversation (US-A02)."""
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user, assistant, system, tool
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    agent_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    agent_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tool_calls: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    tool_results: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AgentConfig(Base):
    """Agent configuration per tenant (US-A01)."""
    __tablename__ = "agent_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    agent_type: Mapped[str] = mapped_column(String(50), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    personality: Mapped[str | None] = mapped_column(Text, nullable=True)
    system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class ConversationMemory(Base):
    """Cross-conversation memory (user preferences etc.) (US-A02)."""
    __tablename__ = "conversation_memories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    memory_type: Mapped[str] = mapped_column(String(30), default="preference")  # preference, fact, context
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class PayrollCost(Base):
    """Monthly payroll/personnel costs (US-44)."""
    __tablename__ = "payroll_costs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    mese: Mapped[date] = mapped_column(Date, nullable=False)  # first day of month (2024-01-01)
    dipendente_nome: Mapped[str] = mapped_column(String(255), nullable=False)
    dipendente_cf: Mapped[str | None] = mapped_column(String(16))
    importo_lordo: Mapped[float] = mapped_column(Float, nullable=False)
    importo_netto: Mapped[float | None] = mapped_column(Float)
    contributi_inps: Mapped[float | None] = mapped_column(Float)
    irpef: Mapped[float | None] = mapped_column(Float)
    tfr: Mapped[float | None] = mapped_column(Float)
    costo_totale_azienda: Mapped[float] = mapped_column(Float, nullable=False)  # lordo + contributi azienda
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


# ============================================================
# Sprint 14-16: F24 Versamenti, Recurring Contracts, Loans
# ============================================================


class F24Versamento(Base):
    """F24 payment (versamento) record imported from PDF or manually entered (US-49, US-50)."""
    __tablename__ = "f24_versamenti"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    codice_tributo: Mapped[str] = mapped_column(String(10), nullable=False)
    periodo_riferimento: Mapped[str | None] = mapped_column(String(20), nullable=True)
    importo: Mapped[float] = mapped_column(Float, nullable=False)
    data_versamento: Mapped[date] = mapped_column(Date, nullable=False)
    source: Mapped[str] = mapped_column(String(20), default="manual")  # manual, pdf_import
    journal_entry_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class RecurringContract(Base):
    """Recurring contract (contratto ricorrente) (US-55, US-56)."""
    __tablename__ = "recurring_contracts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    counterpart: Mapped[str | None] = mapped_column(String(255), nullable=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    frequency: Mapped[str] = mapped_column(String(20), nullable=False, default="monthly")  # monthly, quarterly, annual
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    next_due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="manual")  # manual, pdf_import
    status: Mapped[str] = mapped_column(String(20), default="active")  # active, paused, expired
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class Loan(Base):
    """Loan/financing (finanziamento/mutuo) record (US-57, US-58)."""
    __tablename__ = "loans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    lender: Mapped[str | None] = mapped_column(String(255), nullable=True)
    principal: Mapped[float] = mapped_column(Float, nullable=False)
    interest_rate: Mapped[float] = mapped_column(Float, nullable=False)  # annual %
    installment_amount: Mapped[float] = mapped_column(Float, nullable=False)
    frequency: Mapped[str] = mapped_column(String(20), nullable=False, default="monthly")
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    remaining_principal: Mapped[float] = mapped_column(Float, nullable=False)
    next_payment_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="manual")  # manual, pdf_import
    status: Mapped[str] = mapped_column(String(20), default="active")  # active, closed, defaulted
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
