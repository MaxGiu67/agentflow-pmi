"""Router for email marketing module (US-92, US-93, US-94, US-95)."""

import hashlib
import hmac
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user

from .service import EmailMarketingService

router = APIRouter(prefix="/api/v1", tags=["email-marketing"])


def get_service(db: AsyncSession = Depends(get_db)) -> EmailMarketingService:
    return EmailMarketingService(db)


def _require_tenant(user: User) -> uuid.UUID:
    if not user.tenant_id:
        raise HTTPException(400, "Profilo azienda non configurato")
    return user.tenant_id


# ── Templates (US-94) ─────────────────────────────────


@router.get("/email/templates")
async def list_templates(
    user: User = Depends(get_current_user),
    svc: EmailMarketingService = Depends(get_service),
):
    tid = _require_tenant(user)
    return await svc.list_templates(tid)


class TemplateCreate(BaseModel):
    name: str
    subject: str
    html_body: str
    text_body: str = ""
    variables: list[str] = []
    category: str = "followup"


@router.post("/email/templates", status_code=201)
async def create_template(
    body: TemplateCreate,
    user: User = Depends(get_current_user),
    svc: EmailMarketingService = Depends(get_service),
):
    tid = _require_tenant(user)
    return await svc.create_template(tid, body.model_dump())


@router.get("/email/templates/{template_id}")
async def get_template(
    template_id: uuid.UUID,
    user: User = Depends(get_current_user),
    svc: EmailMarketingService = Depends(get_service),
):
    _require_tenant(user)
    tpl = await svc.get_template(template_id)
    if not tpl:
        raise HTTPException(404, "Template non trovato")
    return tpl


@router.patch("/email/templates/{template_id}")
async def update_template(
    template_id: uuid.UUID,
    body: dict,
    user: User = Depends(get_current_user),
    svc: EmailMarketingService = Depends(get_service),
):
    _require_tenant(user)
    result = await svc.update_template(template_id, body)
    if not result:
        raise HTTPException(404, "Template non trovato")
    return result


class PreviewRequest(BaseModel):
    params: dict = {}


@router.post("/email/templates/{template_id}/preview")
async def preview_template(
    template_id: uuid.UUID,
    body: PreviewRequest,
    user: User = Depends(get_current_user),
    svc: EmailMarketingService = Depends(get_service),
):
    _require_tenant(user)
    result = await svc.preview_template(template_id, body.params)
    if not result:
        raise HTTPException(404, "Template non trovato")
    return result


# ── Send email (US-95) ────────────────────────────────


class SendEmailRequest(BaseModel):
    to_email: str
    to_name: str = ""
    subject: str
    html_body: str = ""
    template_id: str = ""
    contact_id: str = ""
    params: dict = {}


@router.post("/email/send")
async def send_email(
    body: SendEmailRequest,
    user: User = Depends(get_current_user),
    svc: EmailMarketingService = Depends(get_service),
):
    tid = _require_tenant(user)

    # If template_id provided, load template
    subject = body.subject
    html_body = body.html_body
    template_id = uuid.UUID(body.template_id) if body.template_id else None

    if template_id:
        tpl = await svc.get_template(template_id)
        if tpl:
            subject = subject or tpl["subject"]
            html_body = html_body or tpl["html_body"]

    return await svc.send_email(
        tenant_id=tid,
        to_email=body.to_email,
        to_name=body.to_name,
        subject=subject,
        html_body=html_body,
        contact_id=uuid.UUID(body.contact_id) if body.contact_id else None,
        template_id=template_id,
        params=body.params,
    )


# ── Email history ─────────────────────────────────────


@router.get("/email/sends")
async def list_sends(
    contact_id: uuid.UUID | None = Query(None),
    user: User = Depends(get_current_user),
    svc: EmailMarketingService = Depends(get_service),
):
    tid = _require_tenant(user)
    return await svc.list_sends(tid, contact_id=contact_id)


@router.get("/email/stats")
async def email_stats(
    user: User = Depends(get_current_user),
    svc: EmailMarketingService = Depends(get_service),
):
    tid = _require_tenant(user)
    return await svc.get_email_stats(tid)


@router.get("/email/analytics")
async def email_analytics(
    user: User = Depends(get_current_user),
    svc: EmailMarketingService = Depends(get_service),
):
    """US-96: Full email analytics — breakdown by template, top contacts, bounced."""
    tid = _require_tenant(user)
    return await svc.get_email_analytics(tid)


# ── Webhook (US-93) — NO auth required ───────────────


@router.post("/email/webhook")
async def email_webhook(
    request: Request,
    svc: EmailMarketingService = Depends(get_service),
):
    """Brevo webhook endpoint for email events (open, click, bounce, etc.)."""
    payload = await request.json()
    result = await svc.process_webhook_event(payload)
    return result


# ── Sequences (US-97/98) ──────────────────────────────


class SequenceCreate(BaseModel):
    name: str
    trigger_event: str = "manual"
    trigger_config: dict = {}


class SequenceStepCreate(BaseModel):
    template_id: str
    step_order: int = 1
    delay_days: int = 0
    delay_hours: int = 0
    condition_type: str = "none"
    condition_link: str = ""
    skip_if_replied: bool = False


@router.post("/email/sequences", status_code=201)
async def create_sequence(
    body: SequenceCreate,
    user: User = Depends(get_current_user),
    svc: EmailMarketingService = Depends(get_service),
):
    """US-97: Create email sequence."""
    tid = _require_tenant(user)
    return await svc.create_sequence(tid, body.model_dump())


@router.post("/email/sequences/{campaign_id}/steps", status_code=201)
async def add_sequence_step(
    campaign_id: uuid.UUID,
    body: SequenceStepCreate,
    user: User = Depends(get_current_user),
    svc: EmailMarketingService = Depends(get_service),
):
    _require_tenant(user)
    return await svc.add_sequence_step(campaign_id, body.model_dump())


@router.get("/email/sequences/{campaign_id}/steps")
async def get_sequence_steps(
    campaign_id: uuid.UUID,
    user: User = Depends(get_current_user),
    svc: EmailMarketingService = Depends(get_service),
):
    _require_tenant(user)
    return await svc.get_sequence_steps(campaign_id)


class EnrollRequest(BaseModel):
    contact_id: str


@router.post("/email/sequences/{campaign_id}/enroll")
async def enroll_contact(
    campaign_id: uuid.UUID,
    body: EnrollRequest,
    user: User = Depends(get_current_user),
    svc: EmailMarketingService = Depends(get_service),
):
    tid = _require_tenant(user)
    return await svc.enroll_contact(tid, campaign_id, uuid.UUID(body.contact_id))
