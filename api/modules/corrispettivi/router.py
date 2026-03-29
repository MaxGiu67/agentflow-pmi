"""Router for corrispettivi telematici (US-47, US-48)."""

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
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
