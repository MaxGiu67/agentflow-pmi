"""Fiscal models: FiscalRule, FiscalDeadline, VatSettlement, WithholdingTax, StampDuty, F24, CU, etc."""

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, Integer, JSON, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from api.db.models.base import Base


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
