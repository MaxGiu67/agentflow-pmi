"""Router for metering/usage (US-113, US-115)."""


from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from .service import MeteringService

router = APIRouter(prefix="/api/v1", tags=["metering"])


def get_service(db: AsyncSession = Depends(get_db)) -> MeteringService:
    return MeteringService(db)


@router.get("/metering/my-usage")
async def my_usage(
    month: str | None = Query(None, description="YYYY-MM"),
    user: User = Depends(get_current_user),
    svc: MeteringService = Depends(get_service),
):
    """Get usage for current tenant."""
    if not user.tenant_id:
        raise HTTPException(400, "Profilo azienda non configurato")
    return await svc.get_tenant_usage(user.tenant_id, month)


@router.get("/metering/llm-quota")
async def llm_quota(
    user: User = Depends(get_current_user),
    svc: MeteringService = Depends(get_service),
):
    """Check LLM quota for current tenant."""
    if not user.tenant_id:
        raise HTTPException(400, "Profilo azienda non configurato")
    return await svc.check_llm_quota(user.tenant_id)


@router.get("/admin/metering")
async def admin_metering(
    month: str | None = Query(None, description="YYYY-MM"),
    user: User = Depends(get_current_user),
    svc: MeteringService = Depends(get_service),
):
    """AC-115.3: Super-admin only — usage for all tenants."""
    if user.role != "owner":
        raise HTTPException(403, "Solo owner puo vedere il metering globale")
    return await svc.get_all_usage(month)
