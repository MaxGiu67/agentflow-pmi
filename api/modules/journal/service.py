"""Service layer for journal module."""

import logging
import uuid
from datetime import date
from math import ceil

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import JournalEntry, JournalLine

logger = logging.getLogger(__name__)


class JournalService:
    """Service for journal entry operations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_entries(
        self,
        tenant_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
        date_from: date | None = None,
        date_to: date | None = None,
        status: str | None = None,
    ) -> dict:
        """Get paginated list of journal entries with filters."""
        conditions = [JournalEntry.tenant_id == tenant_id]

        if date_from:
            conditions.append(JournalEntry.entry_date >= date_from)
        if date_to:
            conditions.append(JournalEntry.entry_date <= date_to)
        if status:
            conditions.append(JournalEntry.status == status)

        # Count total
        count_query = select(func.count(JournalEntry.id)).where(and_(*conditions))
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Fetch page
        offset = (page - 1) * page_size
        query = (
            select(JournalEntry)
            .where(and_(*conditions))
            .order_by(JournalEntry.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self.db.execute(query)
        entries = result.scalars().all()

        pages = ceil(total / page_size) if page_size > 0 else 0

        if total == 0:
            message = "Nessuna scrittura contabile registrata. Verifica le fatture categorizzate per iniziare."
        else:
            message = f"{total} scritture contabili trovate"

        return {
            "items": entries,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages,
            "message": message,
        }

    async def get_entry(
        self,
        tenant_id: uuid.UUID,
        entry_id: uuid.UUID,
    ) -> dict:
        """Get a single journal entry with its lines."""
        result = await self.db.execute(
            select(JournalEntry).where(
                and_(
                    JournalEntry.id == entry_id,
                    JournalEntry.tenant_id == tenant_id,
                )
            )
        )
        entry = result.scalar_one_or_none()
        if not entry:
            raise ValueError("Scrittura contabile non trovata")

        # Fetch lines
        lines_result = await self.db.execute(
            select(JournalLine)
            .where(JournalLine.entry_id == entry_id)
            .order_by(JournalLine.created_at)
        )
        lines = lines_result.scalars().all()

        return {
            "entry": entry,
            "lines": lines,
        }
