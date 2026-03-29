"""Router for Alert Agent (US-66)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from api.modules.alerts.service import AlertService

router = APIRouter(prefix="/alerts", tags=["alerts"])


def get_service(db: AsyncSession = Depends(get_db)) -> AlertService:
    return AlertService(db)


@router.get("/scan")
async def scan_alerts(
    user: User = Depends(get_current_user),
    service: AlertService = Depends(get_service),
) -> dict:
    """Scan for anomalies: overdue invoices, unusual amounts (US-66)."""
    if not user.tenant_id:
        raise HTTPException(status_code=400, detail="Profilo azienda non configurato")

    return await service.scan(user.tenant_id)
