"""CRM core models: CrmCompany, CrmContact, CrmDeal, CrmPipelineStage, CrmActivity, CrmDealDocument, CrmDealProduct, CrmDealResource."""

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from api.db.models.base import Base


class CrmCompany(Base):
    """Company/account — the organization that buys."""
    __tablename__ = "crm_companies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(20), default="lead")  # lead, prospect, cliente, ex_cliente
    piva: Mapped[str | None] = mapped_column(String(11), nullable=True)
    codice_fiscale: Mapped[str | None] = mapped_column(String(16), nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    province: Mapped[str | None] = mapped_column(String(2), nullable=True)
    sector: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    origin_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class CrmContact(Base):
    """Contact person (referente) — linked to a company."""
    __tablename__ = "crm_contacts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    company_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)  # FK CrmCompany
    name: Mapped[str] = mapped_column(String(255), nullable=False)  # person full name
    contact_name: Mapped[str | None] = mapped_column(String(255), nullable=True)  # legacy compat
    contact_role: Mapped[str | None] = mapped_column(String(100), nullable=True)  # CEO, CTO, Buyer
    type: Mapped[str] = mapped_column(String(20), default="lead")  # lead, prospect, cliente, ex_cliente
    piva: Mapped[str | None] = mapped_column(String(11), nullable=True)  # legacy — now on company
    codice_fiscale: Mapped[str | None] = mapped_column(String(16), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    province: Mapped[str | None] = mapped_column(String(2), nullable=True)
    sector: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    origin_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
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
    stage_type: Mapped[str] = mapped_column(String(50), default="pipeline")  # pre_funnel, pipeline (US-136)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)  # US-136
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class CrmDeal(Base):
    """CRM deal/opportunity — US-88."""
    __tablename__ = "crm_deals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    company_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)  # FK CrmCompany — LEGACY (Pivot 10: use portal_customer_id)
    portal_customer_id: Mapped[int | None] = mapped_column(Integer, nullable=True)  # FK Portal Customer.id (Pivot 10)
    portal_customer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)  # Cached name from Portal
    portal_project_id: Mapped[int | None] = mapped_column(Integer, nullable=True)  # FK Portal Project.id (commessa created from Won deal)
    portal_offer_id: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Portal Offer.id
    contact_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)  # FK CrmContact — main referente
    stage_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    pipeline_template_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)  # US-201: which pipeline template
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
    activity_type_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)  # FK CrmActivityType (US-137)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="planned")  # planned, completed, cancelled
    outlook_event_id: Mapped[str | None] = mapped_column(String(255), nullable=True)  # US-154: Microsoft Graph event ID
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class CrmDealDocument(Base):
    """Document attached to a deal — offer, order, contract, etc."""
    __tablename__ = "crm_deal_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    deal_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    doc_type: Mapped[str] = mapped_column(String(30), nullable=False)  # offerta, ordine, contratto, altro
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)  # external link (Drive, SharePoint, etc.)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class CrmDealProduct(Base):
    """Pivot: product lines on a deal (US-144)."""
    __tablename__ = "crm_deal_products"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    deal_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, default=1)
    price_override: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class CrmDealResource(Base):
    """Person assigned to a deal from Portal (T&M/Project staffing)."""
    __tablename__ = "crm_deal_resources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    deal_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    portal_person_id: Mapped[int] = mapped_column(Integer, nullable=False)
    person_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    person_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    seniority: Mapped[str | None] = mapped_column(String(50), nullable=True)
    daily_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    role: Mapped[str | None] = mapped_column(String(100), nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="assigned")  # assigned, active, released
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    portal_activity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
