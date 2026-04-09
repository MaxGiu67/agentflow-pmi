"""Other models: Expense, Asset, Budget, Resource, Elevia, Notification, Dashboard, Chat, Payroll, Loans, etc."""

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Float, Integer, JSON, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from api.db.models.base import Base


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


class Resource(Base):
    """Internal consultant/resource for T&M matching (US-204)."""
    __tablename__ = "resources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    seniority: Mapped[str] = mapped_column(String(20), nullable=False, default="mid")  # junior, mid, senior, lead
    daily_cost: Mapped[float] = mapped_column(Float, default=0.0)
    suggested_daily_rate: Mapped[float] = mapped_column(Float, default=0.0)
    available_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    current_project: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class ResourceSkill(Base):
    """Skill for a resource with level (US-204)."""
    __tablename__ = "resource_skills"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resource_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    skill_name: Mapped[str] = mapped_column(String(100), nullable=False)  # Java, Angular, DevOps, etc.
    skill_level: Mapped[int] = mapped_column(Integer, default=3)  # 1-5
    certification: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class EleviaUseCase(Base):
    """Elevia AI use case with ATECO fit scores (US-208)."""
    __tablename__ = "elevia_use_cases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)  # UC01, UC02, etc.
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AtecoUseCaseMatrix(Base):
    """ATECO sector -> use case fit score (US-209)."""
    __tablename__ = "ateco_usecase_matrix"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    use_case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    ateco_code: Mapped[str] = mapped_column(String(10), nullable=False)  # "24", "25", "46"
    fit_score: Mapped[int] = mapped_column(Integer, default=50)  # 0-100


class CrossSellSignal(Base):
    """Cross-sell signal between pipelines (US-217)."""
    __tablename__ = "cross_sell_signals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    deal_source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    signal_type: Mapped[str] = mapped_column(String(100), nullable=False)  # documentation_pain, custom_dev_need
    keyword_matched: Mapped[str | None] = mapped_column(String(255), nullable=True)
    suggested_product: Mapped[str | None] = mapped_column(String(255), nullable=True)
    priority: Mapped[str] = mapped_column(String(20), default="medium")  # low, medium, high
    status: Mapped[str] = mapped_column(String(20), default="new")  # new, reviewed, converted, dismissed
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


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
