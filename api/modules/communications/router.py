"""Router for communications (US-70)."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from api.modules.communications.service import CommunicationsService

router = APIRouter(prefix="/communications", tags=["communications"])


def get_service(db: AsyncSession = Depends(get_db)) -> CommunicationsService:
    return CommunicationsService(db)


class GenerateEmailRequest(BaseModel):
    template_type: str = "bilancio_request"
    year: Optional[int] = None
    notes: str = ""


@router.post("/generate-email")
async def generate_email(
    request: GenerateEmailRequest,
    user: User = Depends(get_current_user),
    service: CommunicationsService = Depends(get_service),
) -> dict:
    """Generate pre-filled email for accountant (US-70)."""
    if not user.tenant_id:
        raise HTTPException(status_code=400, detail="Profilo azienda non configurato")

    return await service.generate_email(
        tenant_id=user.tenant_id,
        template_type=request.template_type,
        year=request.year or 0,
        notes=request.notes,
    )
