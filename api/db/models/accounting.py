"""Accounting models: Invoice, JournalEntry, JournalLine, ChartAccount, BankAccount, BankTransaction, etc."""

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, Integer, JSON, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from api.db.models.base import Base


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


class BankConnection(Base):
    """A-Cube Business Registry connection per tenant (ADR-012, Pivot 11 US-OB-03).

    1 BankConnection per tenant/cliente finale. Ciascuno corrisponde a un Business Registry
    sul lato A-Cube (identificato da fiscal_id = P.IVA cliente).
    """
    __tablename__ = "bank_connections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    fiscal_id: Mapped[str] = mapped_column(String(20), nullable=False)  # P.IVA / CF
    business_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    acube_br_uuid: Mapped[str | None] = mapped_column(String(64), nullable=True)  # UUID assegnato da A-Cube
    acube_email: Mapped[str | None] = mapped_column(String(255), nullable=True)  # email univoca per BR (vincolo A-Cube)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, active, expired, disabled
    acube_enabled: Mapped[bool] = mapped_column(Boolean, default=False)  # toggle lato A-Cube (impatto fee)
    consent_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reconnect_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    notice_level: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 0=20gg, 1=10gg, 2=oggi
    last_reconnect_webhook_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_connect_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    environment: Mapped[str] = mapped_column(String(20), default="sandbox")  # sandbox, production
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class BankAccount(Base):
    """Connected bank account via Open Banking (US-24, Pivot 11)."""
    __tablename__ = "bank_accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    iban: Mapped[str] = mapped_column(String(34), nullable=False)
    bank_name: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, default="cbi_globe")  # cbi_globe, acube_aisp, manual
    consent_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    consent_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    balance: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, connected, revoked, expired
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Pivot 11 — A-Cube Open Banking (ADR-012)
    acube_uuid: Mapped[str | None] = mapped_column(String(64), nullable=True)  # Account UUID su A-Cube
    acube_connection_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)  # FK logico → bank_connections.id
    acube_provider_name: Mapped[str | None] = mapped_column(String(255), nullable=True)  # es. "Intesa Sanpaolo"
    acube_nature: Mapped[str | None] = mapped_column(String(50), nullable=True)  # account, card, loan, investment
    acube_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    acube_extra: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # campi banca-specific
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class BankTransaction(Base):
    """Bank transaction from Open Banking sync or PDF import (US-24, US-44, Pivot 11)."""
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
    # Pivot 11 — A-Cube Open Banking (ADR-012)
    acube_transaction_id: Mapped[str | None] = mapped_column(String(255), nullable=True)  # id A-Cube (unique per account)
    acube_status: Mapped[str | None] = mapped_column(String(20), nullable=True)  # pending, booked, canceled
    acube_duplicated: Mapped[bool] = mapped_column(Boolean, default=False)  # flag duplicato da A-Cube
    acube_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    acube_fetched_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    acube_counterparty: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # CRO/TRN estratti dal parser extra (per riconciliazione)
    enriched_cro: Mapped[str | None] = mapped_column(String(50), nullable=True)
    enriched_invoice_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)
    acube_extra: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # payload originale A-Cube
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
