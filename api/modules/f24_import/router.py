"""Router for F24 versamenti import + CRUD (US-49, US-50)."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from api.modules.f24_import.service import F24ImportService

router = APIRouter(prefix="/f24", tags=["f24-import"])


def get_service(db: AsyncSession = Depends(get_db)) -> F24ImportService:
    return F24ImportService(db)


# ── US-49: Import F24 from PDF ──

@router.post("/import-pdf")
async def import_f24_pdf(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    service: F24ImportService = Depends(get_service),
) -> dict:
    """Import F24 versamenti from PDF via LLM extraction (US-49)."""
    if not user.tenant_id:
        raise HTTPException(status_code=400, detail="Profilo azienda non configurato")

    content = await file.read()
    return await service.import_pdf(user.tenant_id, file.filename or "f24.pdf", content)


# ── US-50: CRUD manuale F24 versamenti ──

class F24VersamentoCreate(BaseModel):
    codice_tributo: str
    periodo_riferimento: str
    importo: float
    data_versamento: str  # ISO date


class F24VersamentoUpdate(BaseModel):
    codice_tributo: Optional[str] = None
    periodo_riferimento: Optional[str] = None
    importo: Optional[float] = None
    data_versamento: Optional[str] = None


@router.post("/versamenti")
async def create_versamento(
    request: F24VersamentoCreate,
    user: User = Depends(get_current_user),
    service: F24ImportService = Depends(get_service),
) -> dict:
    """Create a manual F24 versamento (US-50)."""
    if not user.tenant_id:
        raise HTTPException(status_code=400, detail="Profilo azienda non configurato")

    return await service.create_versamento(
        tenant_id=user.tenant_id,
        codice_tributo=request.codice_tributo,
        periodo_riferimento=request.periodo_riferimento,
        importo=request.importo,
        data_versamento=request.data_versamento,
    )


@router.put("/versamenti/{versamento_id}")
async def update_versamento(
    versamento_id: UUID,
    request: F24VersamentoUpdate,
    user: User = Depends(get_current_user),
    service: F24ImportService = Depends(get_service),
) -> dict:
    """Update an F24 versamento (US-50)."""
    if not user.tenant_id:
        raise HTTPException(status_code=400, detail="Profilo azienda non configurato")

    try:
        return await service.update_versamento(
            versamento_id=versamento_id,
            tenant_id=user.tenant_id,
            data=request.model_dump(exclude_none=True),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.delete("/versamenti/{versamento_id}")
async def delete_versamento(
    versamento_id: UUID,
    user: User = Depends(get_current_user),
    service: F24ImportService = Depends(get_service),
) -> dict:
    """Delete an F24 versamento (US-50)."""
    if not user.tenant_id:
        raise HTTPException(status_code=400, detail="Profilo azienda non configurato")

    try:
        return await service.delete_versamento(versamento_id, user.tenant_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
