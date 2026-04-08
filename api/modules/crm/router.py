"""Router CRM — endpoint REST per pipeline interna + ordini cliente.

Prefix: /crm
Tags: crm

Migrato da Odoo (ADR-008) a DB interno (ADR-009).
Flusso: Pipeline -> Offerta -> Ordine Cliente -> Conferma -> Commessa (sistema Nexa Data)
"""

import base64
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
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
from api.modules.deal_resources.service import DealResourceService

router = APIRouter(prefix="/crm", tags=["crm"])


def get_service(db: AsyncSession = Depends(get_db)) -> CRMService:
    return CRMService(db)


def _require_tenant(user: User) -> uuid.UUID:
    if not user.tenant_id:
        raise HTTPException(400, "Profilo azienda non configurato")
    return user.tenant_id


# ── Aziende (Company) ──────────────────────────────────


@router.get("/companies")
async def list_companies(
    search: str = Query(""),
    limit: int = Query(100, ge=1, le=500),
    user: User = Depends(get_current_user),
    svc: CRMService = Depends(get_service),
):
    tid = _require_tenant(user)
    return await svc.list_companies(tid, search=search, limit=limit)


@router.post("/companies", status_code=201)
async def create_company(
    body: dict,
    user: User = Depends(get_current_user),
    svc: CRMService = Depends(get_service),
):
    tid = _require_tenant(user)
    return await svc.create_company(tid, body, user.id)


@router.get("/companies/{company_id}")
async def get_company(
    company_id: uuid.UUID,
    user: User = Depends(get_current_user),
    svc: CRMService = Depends(get_service),
):
    tid = _require_tenant(user)
    result = await svc.get_company(company_id, tid)
    if not result:
        raise HTTPException(404, "Azienda non trovata")
    return result


@router.patch("/companies/{company_id}")
async def update_company(
    company_id: uuid.UUID,
    body: dict,
    user: User = Depends(get_current_user),
    svc: CRMService = Depends(get_service),
):
    tid = _require_tenant(user)
    result = await svc.update_company(company_id, tid, body)
    if not result:
        raise HTTPException(404, "Azienda non trovata")
    return result


@router.delete("/companies/{company_id}")
async def delete_company(
    company_id: uuid.UUID,
    user: User = Depends(get_current_user),
    svc: CRMService = Depends(get_service),
):
    tid = _require_tenant(user)
    ok = await svc.delete_company(company_id, tid)
    if not ok:
        raise HTTPException(404, "Azienda non trovata")
    return {"status": "deleted"}


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
    body: dict,
    user: User = Depends(get_current_user),
    svc: CRMService = Depends(get_service),
):
    tid = _require_tenant(user)
    # Auto-assign to current user if commerciale
    if user.role == "commerciale" and "assigned_to" not in body:
        body["assigned_to"] = str(user.id)
    return await svc.create_deal(tid, body)


@router.delete("/deals/{deal_id}")
async def delete_deal(
    deal_id: uuid.UUID,
    user: User = Depends(get_current_user),
    svc: CRMService = Depends(get_service),
):
    tid = _require_tenant(user)
    ok = await svc.delete_deal(deal_id, tid)
    if not ok:
        raise HTTPException(404, "Deal non trovato")
    return {"status": "deleted"}


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
    assigned = user.id if user.role == "commerciale" else None
    return await svc.get_pipeline_summary(tid, assigned_to=assigned)


@router.get("/pipeline/analytics")
async def pipeline_analytics(
    user: User = Depends(get_current_user),
    svc: CRMService = Depends(get_service),
):
    """US-91: Pipeline analytics — weighted value, conversion, won/lost."""
    tid = _require_tenant(user)
    assigned = user.id if user.role == "commerciale" else None
    return await svc.get_pipeline_analytics(tid, assigned_to=assigned)


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
    # Auto-assign current user so Outlook push works
    if "user_id" not in body or not body["user_id"]:
        body["user_id"] = str(user.id)
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


@router.patch("/activities/{activity_id}")
async def update_activity(
    activity_id: uuid.UUID,
    body: dict,
    user: User = Depends(get_current_user),
    svc: CRMService = Depends(get_service),
):
    _require_tenant(user)
    result = await svc.update_activity(activity_id, body)
    if not result:
        raise HTTPException(404, "Attivita non trovata")
    return result


# ── Documents ─────────────────────────────────────────


@router.get("/deals/{deal_id}/documents")
async def list_deal_documents(
    deal_id: uuid.UUID,
    user: User = Depends(get_current_user),
    svc: CRMService = Depends(get_service),
):
    _require_tenant(user)
    return await svc.list_deal_documents(deal_id)


@router.post("/deals/{deal_id}/documents", status_code=201)
async def add_deal_document(
    deal_id: uuid.UUID,
    body: dict,
    user: User = Depends(get_current_user),
    svc: CRMService = Depends(get_service),
):
    tid = _require_tenant(user)
    return await svc.add_deal_document(tid, deal_id, body, user.id)


@router.delete("/documents/{doc_id}")
async def delete_deal_document(
    doc_id: uuid.UUID,
    user: User = Depends(get_current_user),
    svc: CRMService = Depends(get_service),
):
    _require_tenant(user)
    ok = await svc.delete_deal_document(doc_id)
    if not ok:
        raise HTTPException(404, "Documento non trovato")
    return {"status": "deleted"}


@router.post("/deals/{deal_id}/documents/upload", status_code=201)
async def upload_deal_document(
    deal_id: uuid.UUID,
    file: UploadFile = File(...),
    doc_type: str = Form("altro"),
    name: str = Form(""),
    notes: str = Form(""),
    user: User = Depends(get_current_user),
    svc: CRMService = Depends(get_service),
):
    """Upload a file as deal document. Stores as base64 data URL or uploads to R2 if configured."""
    import os

    tid = _require_tenant(user)
    file_content = await file.read()
    content_type = file.content_type or "application/octet-stream"
    file_name = name.strip() or file.filename or "documento"

    # Try Cloudflare R2 if configured
    r2_account = os.getenv("R2_ACCOUNT_ID")
    r2_access_key = os.getenv("R2_ACCESS_KEY_ID")
    r2_secret_key = os.getenv("R2_SECRET_ACCESS_KEY")
    r2_bucket = os.getenv("R2_BUCKET_NAME")
    r2_public_url = os.getenv("R2_PUBLIC_URL")

    if r2_account and r2_access_key and r2_secret_key and r2_bucket:
        try:
            import boto3
            s3 = boto3.client(
                "s3",
                endpoint_url=f"https://{r2_account}.r2.cloudflarestorage.com",
                aws_access_key_id=r2_access_key,
                aws_secret_access_key=r2_secret_key,
                region_name="auto",
            )
            object_key = f"deals/{deal_id}/{uuid.uuid4()}_{file.filename}"
            s3.put_object(
                Bucket=r2_bucket,
                Key=object_key,
                Body=file_content,
                ContentType=content_type,
            )
            if r2_public_url:
                file_url = f"{r2_public_url.rstrip('/')}/{object_key}"
            else:
                file_url = f"https://{r2_bucket}.r2.cloudflarestorage.com/{object_key}"
        except Exception as e:
            raise HTTPException(500, f"Errore upload R2: {e}")
    else:
        # Fallback: store as base64 data URL
        b64 = base64.b64encode(file_content).decode("utf-8")
        file_url = f"data:{content_type};base64,{b64}"

    doc_data = {
        "doc_type": doc_type,
        "name": file_name,
        "url": file_url,
        "notes": notes,
    }
    return await svc.add_deal_document(tid, deal_id, doc_data, user.id)


# ── Deal Resources ─────────────────────────────────


@router.get("/deals/{deal_id}/resources")
async def list_deal_resources(
    deal_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tid = _require_tenant(user)
    svc = DealResourceService(db)
    return await svc.list_resources(deal_id, tid)


@router.post("/deals/{deal_id}/resources", status_code=201)
async def add_deal_resource(
    deal_id: uuid.UUID,
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tid = _require_tenant(user)
    svc = DealResourceService(db)
    result = await svc.add_resource(deal_id, tid, body)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.patch("/deals/{deal_id}/resources/{resource_id}")
async def update_deal_resource(
    deal_id: uuid.UUID,
    resource_id: uuid.UUID,
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_tenant(user)
    svc = DealResourceService(db)
    result = await svc.update_resource(resource_id, body)
    if not result:
        raise HTTPException(404, "Resource not found")
    return result


@router.delete("/deals/{deal_id}/resources/{resource_id}")
async def remove_deal_resource(
    deal_id: uuid.UUID,
    resource_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_tenant(user)
    svc = DealResourceService(db)
    ok = await svc.remove_resource(resource_id)
    if not ok:
        raise HTTPException(404, "Resource not found")
    return {"ok": True}


@router.get("/deals/{deal_id}/resources/requires")
async def check_requires_resources(
    deal_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tid = _require_tenant(user)
    svc = DealResourceService(db)
    requires = await svc.check_requires_resources(deal_id, tid)
    return {"requires_resources": requires}
