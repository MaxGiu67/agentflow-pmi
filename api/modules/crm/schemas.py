"""Pydantic schemas per il modulo CRM interno (ADR-009)."""

from pydantic import BaseModel, Field


# ── Request ─────────────────────────────────────────────


class ContactCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    company_id: str | None = None
    contact_name: str = ""
    contact_role: str = ""
    type: str = "lead"
    email: str = ""
    phone: str = ""
    vat: str = ""
    city: str = ""
    province: str = ""
    sector: str = ""
    source: str = ""
    website: str = ""
    email_opt_in: bool = True


class DealCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=300)
    contact_id: str = ""
    deal_type: str = ""
    expected_revenue: float = 0
    daily_rate: float = 0
    estimated_days: float = 0
    technology: str = ""


class DealUpdate(BaseModel):
    name: str | None = None
    contact_id: str | None = None
    stage_id: str | None = None
    deal_type: str | None = None
    expected_revenue: float | None = None
    daily_rate: float | None = None
    estimated_days: float | None = None
    technology: str | None = None
    probability: float | None = None
    assigned_to: str | None = None
    portal_offer_id: int | None = None
    portal_project_id: int | None = None
    portal_customer_id: int | None = None
    portal_customer_name: str | None = None


class OrderRegister(BaseModel):
    order_type: str = Field(
        ..., description="Tipo accettazione: po, email, firma_word, portale",
    )
    order_reference: str = ""
    order_notes: str = ""


# ── Response ────────────────────────────────────────────


class ContactResponse(BaseModel):
    id: str
    company_id: str | None = None
    name: str
    contact_name: str = ""
    contact_role: str = ""
    type: str = "lead"
    email: str = ""
    phone: str = ""
    vat: str = ""
    city: str = ""
    province: str = ""
    sector: str = ""
    source: str = ""
    website: str = ""
    email_opt_in: bool = True
    assigned_to: str | None = None
    origin_id: str | None = None


class DealResponse(BaseModel):
    id: str
    name: str
    client_name: str = ""
    client_id: str = ""
    company_id: str = ""
    stage: str = ""
    stage_id: str = ""
    pipeline_template_id: str = ""
    expected_revenue: float = 0
    probability: float = 0
    deal_type: str = ""
    daily_rate: float = 0
    estimated_days: float = 0
    technology: str = ""
    assigned_to: str = ""
    assigned_to_name: str = ""
    days_in_stage: int = 0
    order_type: str = ""
    order_reference: str = ""
    order_date: str = ""
    order_notes: str = ""
    portal_customer_id: int | None = None
    portal_customer_name: str = ""
    portal_project_id: int | None = None
    portal_offer_id: int | None = None
    requires_resources: bool = False


class StageResponse(BaseModel):
    id: str
    name: str
    sequence: int = 0
    probability_default: float = 0
    color: str = "#6B7280"
    is_won: bool = False
    is_lost: bool = False


class PipelineSummaryResponse(BaseModel):
    total_deals: int = 0
    total_value: float = 0
    by_stage: dict[str, dict] = {}


class ContactListResponse(BaseModel):
    contacts: list[ContactResponse]
    total: int


class DealListResponse(BaseModel):
    deals: list[DealResponse]
    total: int
