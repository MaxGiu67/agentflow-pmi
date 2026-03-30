"""Router for corrispettivi telematici (US-47, US-48)."""

from datetime import date as date_type
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from api.modules.corrispettivi.service import CorrispettiviService

router = APIRouter(prefix="/corrispettivi", tags=["corrispettivi"])


def get_service(db: AsyncSession = Depends(get_db)) -> CorrispettiviService:
    return CorrispettiviService(db)


@router.post("/import-xml")
async def import_corrispettivo_xml(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    service: CorrispettiviService = Depends(get_service),
) -> dict:
    """Import a single corrispettivo XML file (COR10) (US-47).

    Parses XML, creates corrispettivo record, and generates journal entry
    (Dare: Cassa/Banca, Avere: Ricavi + IVA).
    """
    if not user.tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Profilo azienda non configurato")

    if not file.filename or not file.filename.lower().endswith(".xml"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Solo file XML accettati")

    content = await file.read()
    try:
        xml_str = content.decode("utf-8")
    except UnicodeDecodeError:
        xml_str = content.decode("latin-1")

    try:
        result = await service.import_xml(user.tenant_id, xml_str)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Errore parsing XML corrispettivi: {e}",
        ) from e

    return result


@router.post("/import-batch")
async def import_corrispettivi_batch(
    files: list[UploadFile] = File(...),
    user: User = Depends(get_current_user),
    service: CorrispettiviService = Depends(get_service),
) -> dict:
    """Import multiple corrispettivi XML files at once (US-47)."""
    if not user.tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Profilo azienda non configurato")

    xml_files = []
    for f in files:
        if f.filename and f.filename.lower().endswith(".xml"):
            content = await f.read()
            try:
                xml_str = content.decode("utf-8")
            except UnicodeDecodeError:
                xml_str = content.decode("latin-1")
            xml_files.append((f.filename, xml_str))

    if not xml_files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nessun file XML trovato")

    return await service.import_batch(user.tenant_id, xml_files)


@router.get("")
async def list_corrispettivi(
    year: int | None = None,
    month: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    service: CorrispettiviService = Depends(get_service),
) -> dict:
    """List corrispettivi with filters (US-47, US-48)."""
    if not user.tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Profilo azienda non configurato")

    return await service.list_corrispettivi(user.tenant_id, year=year, month=month, page=page, page_size=page_size)


# ── CRUD manuale (US-48) ──


class CorrispettivoCreate(BaseModel):
    data: date_type
    imponibile: float
    imposta: float
    totale_contanti: float = 0
    totale_elettronico: float = 0
    num_documenti: int = 0
    aliquota_iva: float | None = None


class CorrispettivoUpdate(BaseModel):
    imponibile: float | None = None
    imposta: float | None = None
    totale_contanti: float | None = None
    totale_elettronico: float | None = None
    num_documenti: int | None = None


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_corrispettivo_manual(
    request: CorrispettivoCreate,
    user: User = Depends(get_current_user),
    service: CorrispettiviService = Depends(get_service),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a manual corrispettivo entry (US-48)."""
    if not user.tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Profilo azienda non configurato")

    from api.db.models import Corrispettivo
    corr = Corrispettivo(
        tenant_id=user.tenant_id,
        data=request.data,
        imponibile=request.imponibile,
        imposta=request.imposta,
        totale_contanti=request.totale_contanti,
        totale_elettronico=request.totale_elettronico,
        num_documenti=request.num_documenti,
        aliquota_iva=request.aliquota_iva,
        source="manual",
    )
    db.add(corr)
    await db.flush()
    return {"id": str(corr.id), "source": "manual", "message": "Corrispettivo creato"}


@router.put("/{corr_id}")
async def update_corrispettivo(
    corr_id: UUID,
    request: CorrispettivoUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update a corrispettivo (US-48)."""
    if not user.tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Profilo azienda non configurato")

    from sqlalchemy import select as sel
    from api.db.models import Corrispettivo
    corr = await db.scalar(sel(Corrispettivo).where(Corrispettivo.id == corr_id, Corrispettivo.tenant_id == user.tenant_id))
    if not corr:
        raise HTTPException(status_code=404, detail="Corrispettivo non trovato")

    for field in ("imponibile", "imposta", "totale_contanti", "totale_elettronico", "num_documenti"):
        val = getattr(request, field, None)
        if val is not None:
            setattr(corr, field, val)
    await db.flush()
    return {"id": str(corr.id), "updated": True}


@router.delete("/{corr_id}")
async def delete_corrispettivo(
    corr_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a corrispettivo (US-48)."""
    if not user.tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Profilo azienda non configurato")

    from sqlalchemy import select as sel
    from api.db.models import Corrispettivo
    corr = await db.scalar(sel(Corrispettivo).where(Corrispettivo.id == corr_id, Corrispettivo.tenant_id == user.tenant_id))
    if not corr:
        raise HTTPException(status_code=404, detail="Corrispettivo non trovato")

    await db.delete(corr)
    await db.flush()
    return {"id": str(corr_id), "deleted": True}
