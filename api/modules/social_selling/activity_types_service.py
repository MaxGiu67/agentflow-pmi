"""Service for activity types — custom activity types per tenant (US-134→US-135)."""

import logging
import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import CrmActivityType

logger = logging.getLogger(__name__)

DEFAULT_ACTIVITY_TYPES = [
    {"code": "call", "label": "Chiamata", "category": "sales", "counts_as_last_contact": True},
    {"code": "email", "label": "Email", "category": "sales", "counts_as_last_contact": True},
    {"code": "meeting", "label": "Incontro", "category": "sales", "counts_as_last_contact": True},
    {"code": "note", "label": "Nota", "category": "sales", "counts_as_last_contact": False},
    {"code": "task", "label": "Task/Reminder", "category": "sales", "counts_as_last_contact": False},
    {"code": "linkedin_inmail", "label": "Inmail LinkedIn", "category": "sales", "counts_as_last_contact": True},
    {"code": "linkedin_comment", "label": "Commento LinkedIn", "category": "marketing", "counts_as_last_contact": True},
    {"code": "linkedin_engagement", "label": "Engagement LinkedIn", "category": "marketing", "counts_as_last_contact": True},
]


class ActivityTypesService:
    """CRUD for custom activity types."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── US-134: Create ─────────────────────────────────

    async def create_type(self, tenant_id: uuid.UUID, data: dict) -> dict:
        """AC-134.1: Create a custom activity type."""
        code = data.get("code", "").strip().lower()
        if not code or len(code) > 50:
            return {"error": "Codice obbligatorio, max 50 caratteri"}

        existing = await self.db.execute(
            select(CrmActivityType).where(
                CrmActivityType.tenant_id == tenant_id,
                CrmActivityType.code == code,
            )
        )
        if existing.scalar_one_or_none():
            return {"error": "Codice tipo attivita gia esistente"}

        category = data.get("category", "sales")
        if category not in ("sales", "marketing", "support"):
            return {"error": "Categoria deve essere: sales, marketing, support"}

        at = CrmActivityType(
            tenant_id=tenant_id,
            code=code,
            label=data.get("label", code),
            category=category,
            counts_as_last_contact=data.get("counts_as_last_contact", False),
            is_active=True,
        )
        self.db.add(at)
        await self.db.flush()
        return self._to_dict(at)

    # ── US-135: Update / Deactivate ────────────────────

    async def update_type(self, type_id: uuid.UUID, data: dict) -> dict | None:
        """AC-135.1: Update type (code immutable)."""
        result = await self.db.execute(
            select(CrmActivityType).where(CrmActivityType.id == type_id)
        )
        at = result.scalar_one_or_none()
        if not at:
            return None

        for key in ("label", "category", "counts_as_last_contact", "is_active"):
            if key in data and data[key] is not None:
                setattr(at, key, data[key])

        await self.db.flush()
        return self._to_dict(at)

    async def delete_type(self, type_id: uuid.UUID) -> dict:
        """AC-135.3: Hard delete not allowed — return 409."""
        result = await self.db.execute(
            select(CrmActivityType).where(CrmActivityType.id == type_id)
        )
        at = result.scalar_one_or_none()
        if not at:
            return {"error": "Tipo attivita non trovato", "code": 404}
        return {"error": "Eliminazione non consentita. Usa disattivazione.", "code": 409}

    # ── List ────────────────────────────────────────────

    async def list_types(
        self, tenant_id: uuid.UUID, active_only: bool = False, category: str = "",
    ) -> list[dict]:
        await self._ensure_defaults(tenant_id)
        query = select(CrmActivityType).where(
            CrmActivityType.tenant_id == tenant_id,
        )
        if active_only:
            query = query.where(CrmActivityType.is_active.is_(True))
        if category:
            query = query.where(CrmActivityType.category == category)
        query = query.order_by(CrmActivityType.label)

        result = await self.db.execute(query)
        return [self._to_dict(t) for t in result.scalars().all()]

    # ── Seed defaults ──────────────────────────────────

    async def _ensure_defaults(self, tenant_id: uuid.UUID) -> None:
        count = await self.db.scalar(
            select(func.count(CrmActivityType.id)).where(
                CrmActivityType.tenant_id == tenant_id,
            )
        )
        if count and count > 0:
            return
        for d in DEFAULT_ACTIVITY_TYPES:
            self.db.add(CrmActivityType(
                tenant_id=tenant_id,
                code=d["code"],
                label=d["label"],
                category=d["category"],
                counts_as_last_contact=d["counts_as_last_contact"],
            ))
        await self.db.flush()

    def _to_dict(self, at: CrmActivityType) -> dict:
        return {
            "id": str(at.id),
            "code": at.code,
            "label": at.label,
            "category": at.category,
            "counts_as_last_contact": at.counts_as_last_contact,
            "is_active": at.is_active,
        }
