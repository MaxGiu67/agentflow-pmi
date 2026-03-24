"""Router for invoice upload (US-06) + folder import."""

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from api.modules.invoices.upload_schemas import UploadResponse
from api.modules.invoices.upload_service import UploadService

router = APIRouter(tags=["invoices"])


class FolderImportRequest(BaseModel):
    folder_path: str


class FolderImportResponse(BaseModel):
    total_files: int
    imported: int
    duplicates: int
    errors: int
    details: list[dict]


def get_upload_service(db: AsyncSession = Depends(get_db)) -> UploadService:
    return UploadService(db)


@router.post("/invoices/upload", response_model=UploadResponse)
async def upload_invoice(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    service: UploadService = Depends(get_upload_service),
) -> UploadResponse:
    """Upload a manual invoice file (PDF, JPG, PNG, XML)."""
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    # Read file content
    content = await file.read()

    try:
        result = await service.upload_file(
            tenant_id=user.tenant_id,
            filename=file.filename or "unknown",
            content_type=file.content_type or "",
            file_content=content,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return UploadResponse(**result)


@router.post("/invoices/import-folder", response_model=FolderImportResponse)
async def import_from_folder(
    request: FolderImportRequest,
    user: User = Depends(get_current_user),
    service: UploadService = Depends(get_upload_service),
) -> FolderImportResponse:
    """Import all XML invoices from a local folder path."""
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    try:
        result = await service.import_folder(
            tenant_id=user.tenant_id,
            folder_path=request.folder_path,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return FolderImportResponse(**result)
