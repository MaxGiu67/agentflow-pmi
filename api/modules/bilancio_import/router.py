"""Router for bilancio/balance import (US-51, US-52, US-54)."""

import logging
import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from api.modules.bilancio_import.service import BilancioImportService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/accounting", tags=["bilancio-import"])

# In-memory job store (per Railway single-instance)
_import_jobs: dict[str, dict] = {}


def get_service(db: AsyncSession = Depends(get_db)) -> BilancioImportService:
    return BilancioImportService(db)


@router.post("/import-bilancio")
async def import_bilancio(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    user: User = Depends(get_current_user),
    service: BilancioImportService = Depends(get_service),
) -> dict:
    """Import bilancio from CSV, Excel, PDF or XBRL (US-51, US-52).

    CSV/XBRL: processed synchronously (fast).
    PDF: processed asynchronously in background (LLM extraction takes time).
    Returns job_id for PDF — poll GET /accounting/import-bilancio/status/{job_id}.
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
            return result
        elif ext in ("xbrl", "xml"):
            result = await service.import_xbrl(user.tenant_id, file.filename, content)
            return result
        elif ext == "pdf":
            # PDF → async background processing
            job_id = str(uuid.uuid4())
            _import_jobs[job_id] = {
                "status": "processing",
                "message": "Estrazione dati dal PDF in corso...",
                "filename": file.filename,
            }
            background_tasks.add_task(
                _process_pdf_background, job_id, user.tenant_id, file.filename, content, service
            )
            return {
                "job_id": job_id,
                "status": "processing",
                "message": "PDF in elaborazione. Controlla lo stato con GET /accounting/import-bilancio/status/" + job_id,
            }
        else:
            raise ValueError(f"Formato non supportato: .{ext}. Formati ammessi: CSV, PDF, XBRL")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e


async def _process_pdf_background(
    job_id: str, tenant_id: uuid.UUID, filename: str, content: bytes, service: BilancioImportService
) -> None:
    """Process PDF import in background."""
    try:
        result = await service.import_pdf(tenant_id, filename, content)
        _import_jobs[job_id] = {**result, "status": "completed"}
    except Exception as e:
        logger.error("Background PDF import failed: %s", e)
        _import_jobs[job_id] = {
            "status": "error",
            "message": f"Errore nell'elaborazione del PDF: {e}",
            "filename": filename,
        }


@router.get("/import-bilancio/status/{job_id}")
async def get_import_status(
    job_id: str,
    user: User = Depends(get_current_user),
) -> dict:
    """Check status of an async PDF bilancio import."""
    if job_id not in _import_jobs:
        raise HTTPException(status_code=404, detail="Job non trovato")
    return _import_jobs[job_id]


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
