"""Service for contact origins — custom acquisition channels per tenant (US-130→US-133)."""

import logging
import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import CrmContactOrigin, CrmContact

logger = logging.getLogger(__name__)

# Default origins seeded for new tenants
DEFAULT_ORIGINS = [
    {"code": "web", "label": "Sito Web", "parent_channel": "digital"},
    {"code": "linkedin", "label": "LinkedIn", "parent_channel": "social"},
    {"code": "referral", "label": "Referral", "parent_channel": "direct"},
    {"code": "evento", "label": "Evento", "parent_channel": "event"},
    {"code": "cold_call", "label": "Cold Call", "parent_channel": "direct"},
    {"code": "email_inbound", "label": "Email Inbound", "parent_channel": "digital"},
]


class OriginsService:
    """CRUD for contact origins with tenant isolation."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── US-130: Create origin ─────────────────────────────

    async def create_origin(self, tenant_id: uuid.UUID, data: dict) -> dict:
        """AC-130.1: Create a custom contact origin."""
        code = data.get("code", "").strip().lower()
        if not code or len(code) > 50:
            return {"error": "Codice obbligatorio, max 50 caratteri"}

        # AC-130.2: Check uniqueness
        existing = await self.db.execute(
            select(CrmContactOrigin).where(
                CrmContactOrigin.tenant_id == tenant_id,
                CrmContactOrigin.code == code,
            )
        )
        if existing.scalar_one_or_none():
            return {"error": "Codice origine gia esistente per questo tenant"}

        origin = CrmContactOrigin(
            tenant_id=tenant_id,
            code=code,
            label=data.get("label", code),
            parent_channel=data.get("parent_channel"),
            icon_name=data.get("icon_name"),
            is_active=data.get("is_active", True),
        )
        self.db.add(origin)
        await self.db.flush()
        return self._to_dict(origin)

    # ── US-131: Update/deactivate origin ──────────────────

    async def update_origin(self, origin_id: uuid.UUID, data: dict) -> dict | None:
        """AC-131.1: Update origin (code is immutable)."""
        result = await self.db.execute(
            select(CrmContactOrigin).where(CrmContactOrigin.id == origin_id)
        )
        origin = result.scalar_one_or_none()
        if not origin:
            return None

        # AC-131.3: Code is immutable
        for key in ("label", "parent_channel", "icon_name", "is_active"):
            if key in data and data[key] is not None:
                setattr(origin, key, data[key])

        await self.db.flush()
        return self._to_dict(origin)

    async def delete_origin(self, origin_id: uuid.UUID) -> dict:
        """AC-131.4: Cannot delete origin with contacts."""
        result = await self.db.execute(
            select(CrmContactOrigin).where(CrmContactOrigin.id == origin_id)
        )
        origin = result.scalar_one_or_none()
        if not origin:
            return {"error": "Origine non trovata"}

        # Check if contacts use this origin
        count = await self.db.scalar(
            select(func.count(CrmContact.id)).where(
                CrmContact.origin_id == origin_id,
            )
        ) or 0

        if count > 0:
            return {"error": f"Non puoi eliminare un'origine con {count} contatti associati. Disattivala invece."}

        await self.db.delete(origin)
        await self.db.flush()
        return {"status": "deleted"}

    # ── US-130: List origins ──────────────────────────────

    async def list_origins(
        self, tenant_id: uuid.UUID, active_only: bool = False,
    ) -> list[dict]:
        """List all origins for tenant."""
        await self._ensure_defaults(tenant_id)
        query = select(CrmContactOrigin).where(
            CrmContactOrigin.tenant_id == tenant_id,
        )
        if active_only:
            query = query.where(CrmContactOrigin.is_active.is_(True))
        query = query.order_by(CrmContactOrigin.label)

        result = await self.db.execute(query)
        return [self._to_dict(o) for o in result.scalars().all()]

    # ── US-132: Migration source → origin_id ──────────────

    async def migrate_sources(self, tenant_id: uuid.UUID) -> dict:
        """AC-132.1/132.2: Migrate legacy source field to origin_id FK."""
        # Find contacts with source but no origin_id
        result = await self.db.execute(
            select(CrmContact).where(
                CrmContact.tenant_id == tenant_id,
                CrmContact.source.isnot(None),
                CrmContact.origin_id.is_(None),
            )
        )
        contacts = result.scalars().all()

        migrated = 0
        for contact in contacts:
            source_code = contact.source.strip().lower().replace(" ", "_")
            # Find or create origin
            origin_result = await self.db.execute(
                select(CrmContactOrigin).where(
                    CrmContactOrigin.tenant_id == tenant_id,
                    CrmContactOrigin.code == source_code,
                )
            )
            origin = origin_result.scalar_one_or_none()
            if not origin:
                origin = CrmContactOrigin(
                    tenant_id=tenant_id,
                    code=source_code,
                    label=contact.source,
                    parent_channel="other",
                )
                self.db.add(origin)
                await self.db.flush()

            contact.origin_id = origin.id
            migrated += 1

        await self.db.flush()
        return {"migrated": migrated}

    # ── US-133: Assign origin to contact ──────────────────

    async def assign_origin(
        self, contact_id: uuid.UUID, origin_id: uuid.UUID,
    ) -> dict:
        """AC-133: Assign origin to a contact."""
        result = await self.db.execute(
            select(CrmContact).where(CrmContact.id == contact_id)
        )
        contact = result.scalar_one_or_none()
        if not contact:
            return {"error": "Contatto non trovato"}

        # Verify origin exists and is active
        origin_result = await self.db.execute(
            select(CrmContactOrigin).where(
                CrmContactOrigin.id == origin_id,
                CrmContactOrigin.is_active.is_(True),
            )
        )
        if not origin_result.scalar_one_or_none():
            return {"error": "Origine non trovata o disattivata"}

        contact.origin_id = origin_id
        await self.db.flush()
        return {"status": "assigned", "contact_id": str(contact_id), "origin_id": str(origin_id)}

    # ── Seed defaults ─────────────────────────────────────

    async def _ensure_defaults(self, tenant_id: uuid.UUID) -> None:
        count = await self.db.scalar(
            select(func.count(CrmContactOrigin.id)).where(
                CrmContactOrigin.tenant_id == tenant_id,
            )
        )
        if count and count > 0:
            return
        for d in DEFAULT_ORIGINS:
            self.db.add(CrmContactOrigin(
                tenant_id=tenant_id,
                code=d["code"],
                label=d["label"],
                parent_channel=d["parent_channel"],
            ))
        await self.db.flush()

    def _to_dict(self, o: CrmContactOrigin) -> dict:
        return {
            "id": str(o.id),
            "code": o.code,
            "label": o.label,
            "parent_channel": o.parent_channel or "",
            "icon_name": o.icon_name or "",
            "is_active": o.is_active,
        }
