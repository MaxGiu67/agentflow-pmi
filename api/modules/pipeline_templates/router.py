"""Pipeline Templates router (US-200, US-201, US-202).

Prefix: /pipeline-templates
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from api.modules.pipeline_templates.service import PipelineTemplateService

router = APIRouter(prefix="/pipeline-templates", tags=["pipeline-templates"])


def _require_tenant(user: User) -> uuid.UUID:
    if not user.tenant_id:
        raise HTTPException(400, "Profilo azienda non configurato")
    return user.tenant_id


@router.get("")
async def list_templates(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """US-200: List pipeline templates for tenant."""
    tid = _require_tenant(user)
    svc = PipelineTemplateService(db)
    return await svc.list_templates(tid)


@router.get("/{template_id}")
async def get_template(
    template_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tid = _require_tenant(user)
    svc = PipelineTemplateService(db)
    result = await svc.get_template(template_id, tid)
    if not result:
        raise HTTPException(404, "Template non trovato")
    return result


@router.post("", status_code=201)
async def create_template(
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """US-202: Create custom pipeline template (admin only)."""
    if user.role not in ("owner", "admin"):
        raise HTTPException(403, "Solo admin puo creare pipeline template")
    tid = _require_tenant(user)
    svc = PipelineTemplateService(db)
    result = await svc.create_template(tid, body)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.patch("/{template_id}")
async def update_template(
    template_id: uuid.UUID,
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """US-202: Update pipeline template (admin only)."""
    if user.role not in ("owner", "admin"):
        raise HTTPException(403, "Solo admin puo modificare pipeline template")
    tid = _require_tenant(user)
    svc = PipelineTemplateService(db)
    result = await svc.update_template(template_id, tid, body)
    if not result:
        raise HTTPException(404, "Template non trovato")
    return result


@router.delete("/{template_id}")
async def delete_template(
    template_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete pipeline template and its stages (admin only)."""
    if user.role not in ("owner", "admin"):
        raise HTTPException(403, "Solo admin puo eliminare pipeline template")
    tid = _require_tenant(user)
    svc = PipelineTemplateService(db)
    deleted = await svc.delete_template(template_id, tid)
    if not deleted:
        raise HTTPException(404, "Template non trovato")
    return {"ok": True}


# ── Stage CRUD ─────────────────────────────────────


@router.post("/{template_id}/stages", status_code=201)
async def add_stage(
    template_id: uuid.UUID,
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a stage to a pipeline template."""
    if user.role not in ("owner", "admin"):
        raise HTTPException(403, "Solo admin")
    tid = _require_tenant(user)
    svc = PipelineTemplateService(db)
    result = await svc.add_stage(template_id, tid, body)
    if not result:
        raise HTTPException(404, "Template non trovato")
    return result


@router.patch("/stages/{stage_id}")
async def update_stage(
    stage_id: uuid.UUID,
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a template stage."""
    if user.role not in ("owner", "admin"):
        raise HTTPException(403, "Solo admin")
    _require_tenant(user)
    svc = PipelineTemplateService(db)
    result = await svc.update_stage(stage_id, body)
    if not result:
        raise HTTPException(404, "Stage non trovato")
    return result


@router.delete("/stages/{stage_id}")
async def delete_stage(
    stage_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a template stage."""
    if user.role not in ("owner", "admin"):
        raise HTTPException(403, "Solo admin")
    _require_tenant(user)
    svc = PipelineTemplateService(db)
    deleted = await svc.delete_stage(stage_id)
    if not deleted:
        raise HTTPException(404, "Stage non trovato")
    return {"ok": True}
