"""Router for Social Selling module (US-130→US-150)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from fastapi.responses import StreamingResponse

from .origins_service import OriginsService
from .activity_types_service import ActivityTypesService
from .pipeline_service import PipelineService
from .roles_service import RolesService
from .audit_service import AuditService
from .products_service import ProductsService
from .dashboard_service import DashboardService
from .compensation_service import CompensationService

router = APIRouter(prefix="/api/v1/social", tags=["social-selling"])


def _require_admin(user: User) -> uuid.UUID:
    if not user.tenant_id:
        raise HTTPException(400, "Profilo azienda non configurato")
    if user.role not in ("owner", "admin"):
        raise HTTPException(403, "Solo owner/admin possono gestire le origini")
    return user.tenant_id


def _require_tenant(user: User) -> uuid.UUID:
    if not user.tenant_id:
        raise HTTPException(400, "Profilo azienda non configurato")
    return user.tenant_id


# ── Origins (US-130→US-133) ───────────────────────────


class OriginCreate(BaseModel):
    code: str
    label: str
    parent_channel: str = ""
    icon_name: str = ""
    is_active: bool = True


class OriginUpdate(BaseModel):
    label: str | None = None
    parent_channel: str | None = None
    icon_name: str | None = None
    is_active: bool | None = None


@router.get("/origins")
async def list_origins(
    active_only: bool = Query(False),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """US-130: List contact origins for tenant."""
    tid = _require_tenant(user)
    svc = OriginsService(db)
    return await svc.list_origins(tid, active_only=active_only)


@router.post("/origins", status_code=201)
async def create_origin(
    body: OriginCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """US-130: Create custom contact origin."""
    tid = _require_admin(user)
    svc = OriginsService(db)
    result = await svc.create_origin(tid, body.model_dump())
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.patch("/origins/{origin_id}")
async def update_origin(
    origin_id: uuid.UUID,
    body: OriginUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """US-131: Update origin (code immutable)."""
    _require_admin(user)
    svc = OriginsService(db)
    result = await svc.update_origin(origin_id, body.model_dump(exclude_none=True))
    if not result:
        raise HTTPException(404, "Origine non trovata")
    return result


@router.delete("/origins/{origin_id}")
async def delete_origin(
    origin_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """US-131: Delete origin (blocked if contacts assigned)."""
    _require_admin(user)
    svc = OriginsService(db)
    result = await svc.delete_origin(origin_id)
    if "error" in result:
        raise HTTPException(400 if "contatti" in result["error"] else 404, result["error"])
    return result


@router.post("/origins/migrate")
async def migrate_sources(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """US-132: Migrate legacy source field to origin_id."""
    tid = _require_admin(user)
    svc = OriginsService(db)
    return await svc.migrate_sources(tid)


@router.post("/contacts/{contact_id}/origin")
async def assign_origin(
    contact_id: uuid.UUID,
    origin_id: uuid.UUID = Query(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """US-133: Assign origin to contact."""
    _require_tenant(user)
    svc = OriginsService(db)
    result = await svc.assign_origin(contact_id, origin_id)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


# ── Activity Types (US-134→US-135) ────────────────────


class ActivityTypeCreate(BaseModel):
    code: str
    label: str
    category: str = "sales"
    counts_as_last_contact: bool = False


class ActivityTypeUpdate(BaseModel):
    label: str | None = None
    category: str | None = None
    counts_as_last_contact: bool | None = None
    is_active: bool | None = None


@router.get("/activity-types")
async def list_activity_types(
    active_only: bool = Query(False),
    category: str = Query(""),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """US-134: List activity types for tenant."""
    tid = _require_tenant(user)
    svc = ActivityTypesService(db)
    return await svc.list_types(tid, active_only=active_only, category=category)


@router.post("/activity-types", status_code=201)
async def create_activity_type(
    body: ActivityTypeCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """US-134: Create custom activity type."""
    tid = _require_admin(user)
    svc = ActivityTypesService(db)
    result = await svc.create_type(tid, body.model_dump())
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.patch("/activity-types/{type_id}")
async def update_activity_type(
    type_id: uuid.UUID,
    body: ActivityTypeUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """US-135: Update activity type (code immutable)."""
    _require_admin(user)
    svc = ActivityTypesService(db)
    result = await svc.update_type(type_id, body.model_dump(exclude_none=True))
    if not result:
        raise HTTPException(404, "Tipo attivita non trovato")
    return result


@router.delete("/activity-types/{type_id}")
async def delete_activity_type(
    type_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """US-135.3: Hard delete not allowed — return 409."""
    _require_admin(user)
    svc = ActivityTypesService(db)
    result = await svc.delete_type(type_id)
    code = result.get("code", 400)
    raise HTTPException(code, result["error"])


# ── Pipeline Stages (US-136) ─────────────────────────


class StageCreate(BaseModel):
    name: str
    sequence: int = 0
    probability: float = 0
    color: str = "#6B7280"
    stage_type: str = "pipeline"
    is_active: bool = True
    is_won: bool = False
    is_lost: bool = False


class StageUpdate(BaseModel):
    name: str | None = None
    probability: float | None = None
    color: str | None = None
    is_active: bool | None = None
    is_won: bool | None = None
    is_lost: bool | None = None


class StageReorderItem(BaseModel):
    stage_id: str
    sequence: int


class StageReorder(BaseModel):
    stage_order: list[StageReorderItem]


@router.get("/pipeline/stages")
async def list_pipeline_stages(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """US-136: List all pipeline stages (pre-funnel + pipeline)."""
    tid = _require_tenant(user)
    svc = PipelineService(db)
    return await svc.list_stages(tid)


@router.post("/pipeline/stages", status_code=201)
async def create_pipeline_stage(
    body: StageCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """US-136: Create pipeline or pre-funnel stage."""
    tid = _require_admin(user)
    svc = PipelineService(db)
    result = await svc.create_stage(tid, body.model_dump())
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.patch("/pipeline/stages/{stage_id}")
async def update_pipeline_stage(
    stage_id: uuid.UUID,
    body: StageUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """US-136/H4: Update pipeline stage."""
    _require_admin(user)
    svc = PipelineService(db)
    result = await svc.update_stage(stage_id, body.model_dump(exclude_none=True))
    if not result:
        raise HTTPException(404, "Stadio non trovato")
    return result


@router.put("/pipeline/stages/reorder")
async def reorder_pipeline_stages(
    body: StageReorder,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """US-136: Reorder stages (drag-and-drop)."""
    _require_admin(user)
    svc = PipelineService(db)
    return await svc.reorder_stages([s.model_dump() for s in body.stage_order])


# ── Roles (US-138) ───────────────────────────────────


class RoleCreate(BaseModel):
    name: str
    description: str = ""
    permissions: dict = {}


@router.get("/roles")
async def list_roles(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """US-138: List RBAC roles."""
    tid = _require_admin(user)
    svc = RolesService(db)
    return await svc.list_roles(tid)


@router.post("/roles", status_code=201)
async def create_role(
    body: RoleCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """US-138: Create custom role."""
    tid = _require_admin(user)
    svc = RolesService(db)
    result = await svc.create_role(tid, body.model_dump())
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.delete("/roles/{role_id}")
async def delete_role(
    role_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """US-138/L4: Delete custom role."""
    _require_admin(user)
    svc = RolesService(db)
    result = await svc.delete_role(role_id)
    if "error" in result:
        raise HTTPException(result.get("code", 400), result["error"])
    return result


# ── Audit Log (US-141) ───────────────────────────────


@router.get("/audit-log")
async def list_audit_log(
    user_id: uuid.UUID | None = Query(None),
    action: str = Query(""),
    entity_type: str = Query(""),
    start_date: str = Query(""),
    end_date: str = Query(""),
    limit: int = Query(50),
    offset: int = Query(0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """US-141: List audit trail."""
    tid = _require_admin(user)
    svc = AuditService(db)
    return await svc.list_logs(
        tid,
        user_id=user_id,
        action=action or None,
        entity_type=entity_type or None,
        start_date=start_date or None,
        end_date=end_date or None,
        limit=limit,
        offset=offset,
    )


@router.get("/audit-log/export")
async def export_audit_log(
    user_id: uuid.UUID | None = Query(None),
    action: str = Query(""),
    entity_type: str = Query(""),
    start_date: str = Query(""),
    end_date: str = Query(""),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """US-141.4: Export audit log as CSV with SHA256 hash."""
    tid = _require_admin(user)
    svc = AuditService(db)
    csv_content, sha256 = await svc.export_csv(
        tid,
        user_id=user_id,
        action=action or None,
        entity_type=entity_type or None,
        start_date=start_date or None,
        end_date=end_date or None,
    )
    import io
    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=audit_log.csv",
            "X-Signature-SHA256": sha256,
        },
    )


# ── Products (US-142→US-145) ─────────────────────────


class ProductCreate(BaseModel):
    name: str
    code: str
    pricing_model: str = "fixed"
    base_price: float | None = None
    hourly_rate: float | None = None
    estimated_duration_days: int | None = None
    technology_type: str | None = None
    target_margin_percent: float | None = None
    description: str | None = None
    category_name: str | None = None
    category_id: str | None = None
    pipeline_template_id: str | None = None


class ProductUpdate(BaseModel):
    name: str | None = None
    base_price: float | None = None
    hourly_rate: float | None = None
    estimated_duration_days: int | None = None
    technology_type: str | None = None
    target_margin_percent: float | None = None
    description: str | None = None
    pipeline_template_id: str | None = None
    is_active: bool | None = None


class DealProductAdd(BaseModel):
    product_id: str
    quantity: float = 1
    price_override: float | None = None
    notes: str | None = None


@router.get("/products")
async def list_products(
    active_only: bool = Query(False),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """US-142: List product catalog."""
    tid = _require_tenant(user)
    svc = ProductsService(db)
    return await svc.list_products(tid, active_only=active_only)


@router.post("/products", status_code=201)
async def create_product(
    body: ProductCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """US-142: Create product."""
    tid = _require_admin(user)
    svc = ProductsService(db)
    result = await svc.create_product(tid, body.model_dump())
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.patch("/products/{product_id}")
async def update_product(
    product_id: uuid.UUID,
    body: ProductUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """US-143: Update product (code immutable)."""
    _require_admin(user)
    svc = ProductsService(db)
    result = await svc.update_product(product_id, body.model_dump(exclude_none=True))
    if not result:
        raise HTTPException(404, "Prodotto non trovato")
    return result


@router.delete("/products/{product_id}")
async def delete_product(
    product_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """US-143.3: Hard delete not allowed."""
    _require_admin(user)
    svc = ProductsService(db)
    result = await svc.delete_product(product_id)
    raise HTTPException(result.get("code", 400), result["error"])


@router.post("/deals/{deal_id}/products", status_code=201)
async def add_deal_product(
    deal_id: uuid.UUID,
    body: DealProductAdd,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """US-144: Add product to deal."""
    tid = _require_tenant(user)
    svc = ProductsService(db)
    result = await svc.add_deal_product(tid, deal_id, body.model_dump())
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.delete("/deals/{deal_id}/products/{line_id}")
async def remove_deal_product(
    deal_id: uuid.UUID,
    line_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """US-144.3: Remove product from deal."""
    _require_tenant(user)
    svc = ProductsService(db)
    result = await svc.remove_deal_product(deal_id, line_id)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.get("/deals/{deal_id}/products")
async def list_deal_products(
    deal_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """US-144: List products on deal."""
    _require_tenant(user)
    svc = ProductsService(db)
    return await svc.list_deal_products(deal_id)


# ── Dashboards (US-146) ──────────────────────────────


class DashboardCreate(BaseModel):
    name: str
    dashboard_layout: list
    is_shared: bool = False


@router.get("/dashboards")
async def list_dashboards(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """US-146: List dashboards."""
    tid = _require_tenant(user)
    svc = DashboardService(db)
    return await svc.list_dashboards(tid)


@router.post("/dashboards", status_code=201)
async def create_dashboard(
    body: DashboardCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """US-146: Create composable dashboard."""
    tid = _require_tenant(user)
    svc = DashboardService(db)
    result = await svc.create_dashboard(tid, user.id, body.model_dump())
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


# ── Scorecard (US-147) ───────────────────────────────


@router.get("/scorecard/{target_user_id}")
async def get_scorecard(
    target_user_id: uuid.UUID,
    start_date: str = Query(""),
    end_date: str = Query(""),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """US-147: Scorecard for a collaborator."""
    tid = _require_tenant(user)
    svc = DashboardService(db)
    from datetime import date as d
    sd = d.fromisoformat(start_date) if start_date else None
    ed = d.fromisoformat(end_date) if end_date else None
    return await svc.get_scorecard(tid, target_user_id, start_date=sd, end_date=ed)


# ── Compensation (US-148→US-150) ─────────────────────


class CompensationRuleCreate(BaseModel):
    name: str
    trigger: str = "deal_won"
    calculation_method: str = "percent_revenue"
    base_config: dict
    conditions: dict | None = None
    priority: int = 0


@router.get("/compensation-rules")
async def list_compensation_rules(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """US-148: List compensation rules."""
    tid = _require_admin(user)
    svc = CompensationService(db)
    return await svc.list_rules(tid)


@router.post("/compensation-rules", status_code=201)
async def create_compensation_rule(
    body: CompensationRuleCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """US-148: Create compensation rule."""
    tid = _require_admin(user)
    svc = CompensationService(db)
    result = await svc.create_rule(tid, user.id, body.model_dump())
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.get("/compensation/monthly")
async def list_monthly_compensation(
    month: str = Query(""),
    status: str = Query(""),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """US-149: List monthly compensation entries."""
    tid = _require_admin(user)
    svc = CompensationService(db)
    return await svc.list_monthly(tid, month=month or "", status=status or "")


@router.post("/compensation/calculate")
async def calculate_compensation(
    month: str = Query(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """US-149.2: Calculate monthly compensation."""
    tid = _require_admin(user)
    svc = CompensationService(db)
    from datetime import date as d
    m = d.fromisoformat(month)
    return await svc.calculate_monthly(tid, m)


@router.patch("/compensation/monthly/{entry_id}/confirm")
async def confirm_compensation(
    entry_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """US-150.1: Confirm compensation entry."""
    _require_admin(user)
    svc = CompensationService(db)
    result = await svc.confirm_entry(entry_id)
    if not result:
        raise HTTPException(404, "Compenso non trovato")
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.patch("/compensation/monthly/{entry_id}/paid")
async def mark_paid_compensation(
    entry_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """US-150.3: Mark compensation as paid."""
    _require_admin(user)
    svc = CompensationService(db)
    result = await svc.mark_paid(entry_id)
    if not result:
        raise HTTPException(404, "Compenso non trovato")
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result
