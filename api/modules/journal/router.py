"""Router for journal entries module."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from api.modules.journal.schemas import (
    JournalEntryResponse,
    JournalLineResponse,
    JournalListResponse,
)
from api.modules.journal.service import JournalService

router = APIRouter(prefix="/accounting", tags=["journal"])


def get_journal_service(db: AsyncSession = Depends(get_db)) -> JournalService:
    return JournalService(db)


@router.get("/journal-entries", response_model=JournalListResponse)
async def list_journal_entries(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    service: JournalService = Depends(get_journal_service),
) -> JournalListResponse:
    """List journal entries with filters and pagination."""
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    result = await service.get_entries(
        tenant_id=user.tenant_id,
        page=page,
        page_size=page_size,
        date_from=date_from,
        date_to=date_to,
        status=status,
    )
    return JournalListResponse(**result)


@router.get("/journal-entries/{entry_id}", response_model=JournalEntryResponse)
async def get_journal_entry(
    entry_id: UUID,
    user: User = Depends(get_current_user),
    service: JournalService = Depends(get_journal_service),
) -> JournalEntryResponse:
    """Get a single journal entry with its lines."""
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    try:
        data = await service.get_entry(user.tenant_id, entry_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    entry = data["entry"]
    lines = data["lines"]

    return JournalEntryResponse(
        id=entry.id,
        tenant_id=entry.tenant_id,
        invoice_id=entry.invoice_id,
        description=entry.description,
        entry_date=entry.entry_date,
        total_debit=entry.total_debit,
        total_credit=entry.total_credit,
        status=entry.status,
        error_message=entry.error_message,
        odoo_move_id=entry.odoo_move_id,
        created_at=entry.created_at,
        lines=[JournalLineResponse.model_validate(line) for line in lines],
    )
