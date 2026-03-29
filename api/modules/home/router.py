"""Router for Home conversazionale (US-68)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from api.modules.home.service import HomeService

router = APIRouter(prefix="/home", tags=["home"])


def get_service(db: AsyncSession = Depends(get_db)) -> HomeService:
    return HomeService(db)


@router.get("/summary")
async def get_home_summary(
    user: User = Depends(get_current_user),
    service: HomeService = Depends(get_service),
) -> dict:
    """Get home summary: greeting, ricavi vs target, saldo, uscite, azioni (US-68)."""
    if not user.tenant_id:
        raise HTTPException(status_code=400, detail="Profilo azienda non configurato")

    return await service.get_summary(user.tenant_id, user.name or "Utente")
