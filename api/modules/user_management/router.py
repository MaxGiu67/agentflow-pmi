"""Router for user management (US-109 to US-112)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from .service import UserManagementService

router = APIRouter(prefix="/api/v1/users", tags=["user-management"])


def get_service(db: AsyncSession = Depends(get_db)) -> UserManagementService:
    return UserManagementService(db)


def _require_tenant(user: User) -> uuid.UUID:
    if not user.tenant_id:
        raise HTTPException(400, "Profilo azienda non configurato")
    return user.tenant_id


class InviteRequest(BaseModel):
    email: str
    name: str
    role: str = "commerciale"
    user_type: str = "internal"
    access_expires_at: str | None = None
    default_origin_id: str | None = None
    default_product_id: str | None = None
    crm_role_id: str | None = None


class RoleUpdateRequest(BaseModel):
    role: str


class CrmRoleUpdateRequest(BaseModel):
    crm_role_id: str | None = None


class SenderUpdateRequest(BaseModel):
    sender_email: str = ""
    sender_name: str = ""


@router.get("")
async def list_users(
    user: User = Depends(get_current_user),
    svc: UserManagementService = Depends(get_service),
):
    """AC-109.1: List team users."""
    tid = _require_tenant(user)
    return await svc.list_users(tid)


@router.post("/invite", status_code=201)
async def invite_user(
    body: InviteRequest,
    user: User = Depends(get_current_user),
    svc: UserManagementService = Depends(get_service),
):
    """AC-109.2: Invite new user."""
    tid = _require_tenant(user)
    result = await svc.invite_user(
        tid, body.email, body.name, body.role, user,
        user_type=body.user_type,
        access_expires_at=body.access_expires_at,
        default_origin_id=body.default_origin_id,
        default_product_id=body.default_product_id,
        crm_role_id=body.crm_role_id,
    )
    if "error" in result:
        raise HTTPException(403 if "permessi" in result["error"] else 400, result["error"])
    return result


@router.patch("/{user_id}/role")
async def update_role(
    user_id: uuid.UUID,
    body: RoleUpdateRequest,
    user: User = Depends(get_current_user),
    svc: UserManagementService = Depends(get_service),
):
    """AC-109.3: Change user role."""
    result = await svc.update_role(user_id, body.role, user)
    if "error" in result:
        raise HTTPException(403 if "permessi" in result["error"] else 400, result["error"])
    return result


@router.post("/{user_id}/toggle-active")
async def toggle_active(
    user_id: uuid.UUID,
    user: User = Depends(get_current_user),
    svc: UserManagementService = Depends(get_service),
):
    """AC-109.4: Activate/deactivate user."""
    result = await svc.toggle_active(user_id, user)
    if "error" in result:
        raise HTTPException(403 if "permessi" in result["error"] else 400, result["error"])
    return result


@router.patch("/{user_id}/crm-role")
async def update_crm_role(
    user_id: uuid.UUID,
    body: CrmRoleUpdateRequest,
    user: User = Depends(get_current_user),
    svc: UserManagementService = Depends(get_service),
):
    """Update user's CRM role assignment."""
    result = await svc.update_crm_role(user_id, body.crm_role_id, user)
    if "error" in result:
        raise HTTPException(403 if "permessi" in result["error"] else 400, result["error"])
    return result


@router.patch("/{user_id}/sender")
async def update_sender(
    user_id: uuid.UUID,
    body: SenderUpdateRequest,
    user: User = Depends(get_current_user),
    svc: UserManagementService = Depends(get_service),
):
    """AC-111.1: Set sender email for user."""
    return await svc.update_sender(user_id, body.sender_email, body.sender_name)


@router.get("/me/permissions")
async def my_permissions(
    user: User = Depends(get_current_user),
    svc: UserManagementService = Depends(get_service),
):
    """Get current user's permissions and visible nav sections."""
    role = user.role

    # Sections visible per role
    # owner/admin: everything
    # commerciale: only sales + chat + dashboard
    # viewer: read-only areas (no settings, no write-heavy)
    visible_sections: list[str] = []

    if role in ("owner", "admin"):
        visible_sections = [
            "principale", "operativo", "commerciale",
            "gestione", "sistema",
        ]
    elif role == "commerciale":
        visible_sections = ["principale_light", "commerciale", "sistema_light"]
    elif role == "viewer":
        visible_sections = ["principale_light", "commerciale_readonly", "sistema_light"]
    else:
        visible_sections = ["principale_light", "sistema_light"]

    return {
        "role": role,
        "user_id": str(user.id),
        "email": user.email,
        "can_manage_users": role in ("owner", "admin"),
        "can_see_all_deals": svc.can_see_all(user),
        "is_active": getattr(user, "active", True),
        "visible_sections": visible_sections,
    }
