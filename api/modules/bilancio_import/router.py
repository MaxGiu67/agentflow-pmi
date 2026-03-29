"""Router for bilancio/balance import (US-51, US-52, US-54)."""

from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from api.modules.bilancio_import.service import BilancioImportService

router = APIRouter(prefix="/accounting", tags=["bilancio-import"])


def get_service(db: AsyncSession = Depends(get_db)) -> BilancioImportService:
    return BilancioImportService(db)


@router.post("/import-bilancio")
async def import_bilancio(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    service: BilancioImportService = Depends(get_service),
) -> dict:
    """Import bilancio from CSV, Excel, or PDF (US-51, US-52).

    Auto-detects format by extension. Returns preview for user confirmation.
    """
    if not user.tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Profilo azienda non configurato")

    if not file.filename:
        raise HTTPException(status_code=400, detail="Nome file mancante")

    content = await file.read()
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""

    try:
        if ext in ("csv", "txt", "xlsx"):
            result = await service.import_csv(user.tenant_id, file.filename, content)
        elif ext == "pdf":
            result = await service.import_pdf(user.tenant_id, file.filename, content)
        else:
            raise ValueError(f"Formato non supportato: .{ext}. Formati ammessi: CSV, PDF")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e

    return result


class ConfirmBilancioRequest(BaseModel):
    lines: list[dict[str, Any]]
    description: str = "Saldi iniziali bilancio"


@router.post("/confirm-bilancio")
async def confirm_bilancio_import(
    request: ConfirmBilancioRequest,
    user: User = Depends(get_current_user),
    service: BilancioImportService = Depends(get_service),
) -> dict:
    """Confirm and save bilancio lines as opening journal entry (US-51/52)."""
    if not user.tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Profilo azienda non configurato")

    return await service.confirm_import(user.tenant_id, request.lines, request.description)


class WizardBalancesRequest(BaseModel):
    banca: float | None = None
    cassa: float | None = None
    crediti_clienti: float | None = None
    debiti_fornitori: float | None = None
    capitale_sociale: float | None = None
    magazzino: float | None = None
    immobilizzazioni: float | None = None


@router.post("/initial-balances/wizard")
async def save_wizard_balances(
    request: WizardBalancesRequest,
    user: User = Depends(get_current_user),
    service: BilancioImportService = Depends(get_service),
) -> dict:
    """Save manual wizard balances as opening entry (US-54).

    The wizard asks for key balances and auto-balances with equity.
    """
    if not user.tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Profilo azienda non configurato")

    return await service.save_wizard(user.tenant_id, request.model_dump(exclude_none=True))
