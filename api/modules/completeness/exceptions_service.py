"""Import exceptions service (US-71).

Manages anomalies from imports that need user attention.
Max 3 visible at a time — the rest in backlog.
"""

import uuid
from datetime import datetime

from sqlalchemy import case, select, func, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import ImportException

MAX_VISIBLE = 3


class ImportExceptionsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_exception(
        self,
        tenant_id: uuid.UUID,
        source_type: str,
        title: str,
        description: str | None = None,
        severity: str = "warning",
        action_label: str | None = None,
        action_url: str | None = None,
        related_entity_id: uuid.UUID | None = None,
    ) -> ImportException:
        """Create a new import exception (anomaly)."""
        exc = ImportException(
            tenant_id=tenant_id,
            source_type=source_type,
            severity=severity,
            title=title,
            description=description,
            action_label=action_label,
            action_url=action_url,
            related_entity_id=related_entity_id,
        )
        self.db.add(exc)
        await self.db.flush()
        return exc

    async def get_pending(self, tenant_id: uuid.UUID) -> dict:
        """Get pending exceptions with max 3 visible + total count.

        Returns the first 3 by severity (error > warning > info), then created_at.
        """
        conditions = [
            ImportException.tenant_id == tenant_id,
            ImportException.resolved == False,
        ]

        # Total count
        total = await self.db.scalar(
            select(func.count(ImportException.id)).where(and_(*conditions))
        ) or 0

        # Top 3 by severity + date
        severity_order = case(
            (ImportException.severity == "error", 0),
            (ImportException.severity == "warning", 1),
            else_=2,
        )
        q = (
            select(ImportException)
            .where(and_(*conditions))
            .order_by(severity_order, ImportException.created_at.desc())
            .limit(MAX_VISIBLE)
        )
        result = await self.db.execute(q)
        visible = result.scalars().all()

        return {
            "visible": [self._to_dict(e) for e in visible],
            "visible_count": len(visible),
            "total_pending": total,
            "has_more": total > MAX_VISIBLE,
            "remaining": max(0, total - MAX_VISIBLE),
        }

    async def get_all_pending(self, tenant_id: uuid.UUID, page: int = 1, page_size: int = 20) -> dict:
        """Get all pending exceptions (backlog)."""
        conditions = [
            ImportException.tenant_id == tenant_id,
            ImportException.resolved == False,
        ]

        total = await self.db.scalar(
            select(func.count(ImportException.id)).where(and_(*conditions))
        ) or 0

        severity_order = case(
            (ImportException.severity == "error", 0),
            (ImportException.severity == "warning", 1),
            else_=2,
        )
        q = (
            select(ImportException)
            .where(and_(*conditions))
            .order_by(severity_order, ImportException.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(q)
        items = result.scalars().all()

        return {
            "items": [self._to_dict(e) for e in items],
            "total": total,
            "page": page,
        }

    async def resolve(self, tenant_id: uuid.UUID, exception_id: uuid.UUID) -> bool:
        """Mark an exception as resolved."""
        result = await self.db.execute(
            update(ImportException)
            .where(
                ImportException.id == exception_id,
                ImportException.tenant_id == tenant_id,
            )
            .values(resolved=True, resolved_at=datetime.utcnow())
        )
        return result.rowcount > 0

    def _to_dict(self, e: ImportException) -> dict:
        return {
            "id": str(e.id),
            "source_type": e.source_type,
            "severity": e.severity,
            "title": e.title,
            "description": e.description,
            "action_label": e.action_label,
            "action_url": e.action_url,
            "related_entity_id": str(e.related_entity_id) if e.related_entity_id else None,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
