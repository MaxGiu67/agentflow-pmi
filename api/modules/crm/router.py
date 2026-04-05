"""Router CRM — endpoint REST per pipeline interna + ordini cliente.

Prefix: /crm
Tags: crm

Migrato da Odoo (ADR-008) a DB interno (ADR-009).
Flusso: Pipeline -> Offerta -> Ordine Cliente -> Conferma -> Commessa (sistema Nexa Data)
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from api.modules.crm.service import CRMService
from api.modules.crm.schemas import (
    ContactCreate,
    ContactListResponse,
    DealCreate,
    DealListResponse,
    DealUpdate,
    OrderRegister,
    PipelineSummaryResponse,
)

router = APIRouter(prefix="/crm", tags=["crm"])


def get_service(db: AsyncSession = Depends(get_db)) -> CRMService:
    return CRMService(db)


def _require_tenant(user: User) -> uuid.UUID:
    if not user.tenant_id:
        raise HTTPException(400, "Profilo azienda non configurato")
    return user.tenant_id


# ── Contatti ────────────────────────────────────────────


@router.get("/contacts", response_model=ContactListResponse)
async def list_contacts(
    search: str = Query("", description="Ricerca per nome/P.IVA/email"),
    type: str = Query("", description="Filtro tipo: lead, prospect, cliente, ex_cliente"),
    limit: int = Query(100, ge=1, le=500),
    user: User = Depends(get_current_user),
    svc: CRMService = Depends(get_service),
):
    tid = _require_tenant(user)
    # AC-110.2: commerciale sees only own contacts
    assigned = user.id if user.role == "commerciale" else None
    # US-140 AC-140.2: external user sees only contacts matching their default origin
    origin_filter = getattr(user, "default_origin_id", None) if getattr(user, "user_type", "internal") == "external" else None
    return await svc.list_contacts(tid, search=search, contact_type=type, limit=limit, assigned_to=assigned, origin_id=origin_filter)


@router.post("/contacts", status_code=201)
async def create_contact(
    body: ContactCreate,
    user: User = Depends(get_current_user),
    svc: CRMService = Depends(get_service),
):
    tid = _require_tenant(user)
    return await svc.create_contact(tid, body.model_dump())


@router.patch("/contacts/{contact_id}")
async def update_contact(
    contact_id: uuid.UUID,
    body: dict,
    user: User = Depends(get_current_user),
    svc: CRMService = Depends(get_service),
):
    _require_tenant(user)
    result = await svc.update_contact(contact_id, body)
    if not result:
        raise HTTPException(404, "Contatto non trovato")
    return result


@router.delete("/contacts/{contact_id}")
async def delete_contact(
    contact_id: uuid.UUID,
    user: User = Depends(get_current_user),
    svc: CRMService = Depends(get_service),
):
    _require_tenant(user)
    ok = await svc.delete_contact(contact_id)
    if not ok:
        raise HTTPException(404, "Contatto non trovato")
    return {"status": "deleted"}


# ── Pipeline / Deal ────────────────────────────────────


@router.get("/deals", response_model=DealListResponse)
async def list_deals(
    stage: str = Query("", description="Filtra per nome fase"),
    deal_type: str = Query("", description="T&M, fixed, spot, hardware"),
    limit: int = Query(100, ge=1, le=500),
    user: User = Depends(get_current_user),
    svc: CRMService = Depends(get_service),
):
    tid = _require_tenant(user)
    # AC-110.1: commerciale sees only own deals
    assigned = user.id if user.role == "commerciale" else None
    return await svc.list_deals(tid, stage=stage, deal_type=deal_type, limit=limit, assigned_to=assigned)


@router.get("/deals/won", response_model=DealListResponse)
async def list_won_deals(
    user: User = Depends(get_current_user),
    svc: CRMService = Depends(get_service),
):
    tid = _require_tenant(user)
    return await svc.get_won_deals(tid)


@router.get("/deals/{deal_id}")
async def get_deal(
    deal_id: uuid.UUID,
    user: User = Depends(get_current_user),
    svc: CRMService = Depends(get_service),
):
    tid = _require_tenant(user)
    deal = await svc.get_deal(deal_id, tid)
    if not deal:
        raise HTTPException(404, "Deal non trovato")
    return deal


@router.post("/deals", status_code=201)
async def create_deal(
    body: DealCreate,
    user: User = Depends(get_current_user),
    svc: CRMService = Depends(get_service),
):
    tid = _require_tenant(user)
    return await svc.create_deal(tid, body.model_dump())


@router.patch("/deals/{deal_id}")
async def update_deal(
    deal_id: uuid.UUID,
    body: DealUpdate,
    user: User = Depends(get_current_user),
    svc: CRMService = Depends(get_service),
):
    tid = _require_tenant(user)
    result = await svc.update_deal(deal_id, tid, body.model_dump(exclude_none=True))
    if not result:
        raise HTTPException(404, "Deal non trovato")
    return result


# ── Ordini Cliente ─────────────────────────────────────


@router.post("/deals/{deal_id}/order")
async def register_order(
    deal_id: uuid.UUID,
    body: OrderRegister,
    user: User = Depends(get_current_user),
    svc: CRMService = Depends(get_service),
):
    tid = _require_tenant(user)
    result = await svc.register_order(
        deal_id, tid,
        order_type=body.order_type,
        order_reference=body.order_reference,
        order_notes=body.order_notes,
    )
    if "error" in result:
        raise HTTPException(404, result["error"])
    return result


@router.get("/orders/pending", response_model=DealListResponse)
async def list_pending_orders(
    user: User = Depends(get_current_user),
    svc: CRMService = Depends(get_service),
):
    tid = _require_tenant(user)
    return await svc.get_pending_orders(tid)


@router.post("/deals/{deal_id}/order/confirm")
async def confirm_order(
    deal_id: uuid.UUID,
    user: User = Depends(get_current_user),
    svc: CRMService = Depends(get_service),
):
    tid = _require_tenant(user)
    result = await svc.confirm_order(deal_id, tid)
    if "error" in result:
        raise HTTPException(404, result["error"])
    return result


# ── Pipeline overview ──────────────────────────────────


@router.get("/pipeline/summary", response_model=PipelineSummaryResponse)
async def pipeline_summary(
    user: User = Depends(get_current_user),
    svc: CRMService = Depends(get_service),
):
    tid = _require_tenant(user)
    return await svc.get_pipeline_summary(tid)


@router.get("/pipeline/analytics")
async def pipeline_analytics(
    user: User = Depends(get_current_user),
    svc: CRMService = Depends(get_service),
):
    """US-91: Pipeline analytics — weighted value, conversion, won/lost."""
    tid = _require_tenant(user)
    return await svc.get_pipeline_analytics(tid)


@router.get("/pipeline/stages")
async def list_stages(
    user: User = Depends(get_current_user),
    svc: CRMService = Depends(get_service),
):
    tid = _require_tenant(user)
    return await svc.get_stages(tid)


# ── Activities ─────────────────────────────────────────


@router.get("/activities")
async def list_activities(
    deal_id: uuid.UUID | None = Query(None),
    contact_id: uuid.UUID | None = Query(None),
    type: str = Query(""),
    status: str = Query(""),
    user: User = Depends(get_current_user),
    svc: CRMService = Depends(get_service),
):
    tid = _require_tenant(user)
    return await svc.list_activities(
        tid, deal_id=deal_id, contact_id=contact_id,
        activity_type=type, status=status,
    )


@router.post("/activities", status_code=201)
async def create_activity(
    body: dict,
    user: User = Depends(get_current_user),
    svc: CRMService = Depends(get_service),
):
    tid = _require_tenant(user)
    return await svc.create_activity(tid, body)


@router.post("/activities/{activity_id}/complete")
async def complete_activity(
    activity_id: uuid.UUID,
    user: User = Depends(get_current_user),
    svc: CRMService = Depends(get_service),
):
    _require_tenant(user)
    result = await svc.complete_activity(activity_id)
    if not result:
        raise HTTPException(404, "Attivita non trovata")
    return result
