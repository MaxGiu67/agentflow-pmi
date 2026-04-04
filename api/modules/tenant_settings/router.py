"""Router for tenant settings (integrations, API keys, email config)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from .service import TenantSettingsService

router = APIRouter(prefix="/api/v1/settings", tags=["tenant-settings"])


def get_service(db: AsyncSession = Depends(get_db)) -> TenantSettingsService:
    return TenantSettingsService(db)


def _require_admin(user: User) -> uuid.UUID:
    if not user.tenant_id:
        raise HTTPException(400, "Profilo azienda non configurato")
    if user.role not in ("owner", "admin"):
        raise HTTPException(403, "Solo owner/admin possono gestire le impostazioni")
    return user.tenant_id


@router.get("/integrations")
async def list_settings(
    user: User = Depends(get_current_user),
    svc: TenantSettingsService = Depends(get_service),
):
    """List all integration settings (masked values)."""
    tid = _require_admin(user)
    return await svc.list_settings(tid)


class SettingUpdate(BaseModel):
    key: str
    value: str


@router.post("/integrations")
async def set_setting(
    body: SettingUpdate,
    user: User = Depends(get_current_user),
    svc: TenantSettingsService = Depends(get_service),
):
    """Set a custom integration setting (encrypted)."""
    tid = _require_admin(user)
    return await svc.set_setting(tid, body.key, body.value, source="custom")


@router.delete("/integrations/{key}")
async def delete_setting(
    key: str,
    user: User = Depends(get_current_user),
    svc: TenantSettingsService = Depends(get_service),
):
    """Delete custom setting (falls back to platform default)."""
    tid = _require_admin(user)
    ok = await svc.delete_setting(tid, key)
    if not ok:
        raise HTTPException(404, "Setting non trovato")
    return {"status": "deleted", "key": key}


@router.get("/email-quota")
async def email_quota(
    user: User = Depends(get_current_user),
    svc: TenantSettingsService = Depends(get_service),
):
    """Check email quota for current tenant."""
    if not user.tenant_id:
        raise HTTPException(400, "Profilo azienda non configurato")
    return await svc.check_email_quota(user.tenant_id)


@router.get("/sender")
async def get_sender(
    user: User = Depends(get_current_user),
    svc: TenantSettingsService = Depends(get_service),
):
    """Get email sender config for current tenant."""
    if not user.tenant_id:
        raise HTTPException(400, "Profilo azienda non configurato")
    email, name = await svc.get_sender_for_tenant(user.tenant_id)
    return {"sender_email": email, "sender_name": name}
