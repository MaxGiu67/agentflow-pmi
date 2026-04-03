"""Service CRM — logica di business per pipeline interna + ordini cliente.

Migrato da Odoo (ADR-008) a DB interno PostgreSQL (ADR-009).
NON gestisce: commesse, timesheet, billing (restano sul sistema NExadata).
"""

import logging
import uuid
from datetime import datetime, date

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import CrmContact, CrmDeal, CrmPipelineStage, CrmActivity

logger = logging.getLogger(__name__)

# Default pipeline stages (created on first access)
DEFAULT_STAGES = [
    {"name": "Nuovo Lead", "sequence": 1, "probability_default": 10.0, "color": "#6B7280"},
    {"name": "Qualificato", "sequence": 2, "probability_default": 30.0, "color": "#3B82F6"},
    {"name": "Proposta Inviata", "sequence": 3, "probability_default": 50.0, "color": "#F59E0B"},
    {"name": "Ordine Ricevuto", "sequence": 4, "probability_default": 80.0, "color": "#F97316"},
    {"name": "Confermato", "sequence": 5, "probability_default": 100.0, "color": "#10B981", "is_won": True},
    {"name": "Perso", "sequence": 6, "probability_default": 0.0, "color": "#EF4444", "is_lost": True},
]


class CRMService:
    """Business logic for internal CRM module."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Contacts ──────────────────────────────────────────

    async def list_contacts(
        self, tenant_id: uuid.UUID,
        search: str = "", contact_type: str = "", limit: int = 100,
    ) -> dict:
        query = select(CrmContact).where(CrmContact.tenant_id == tenant_id)
        if search:
            query = query.where(or_(
                CrmContact.name.ilike(f"%{search}%"),
                CrmContact.piva.ilike(f"%{search}%"),
                CrmContact.email.ilike(f"%{search}%"),
            ))
        if contact_type:
            query = query.where(CrmContact.type == contact_type)
        query = query.order_by(CrmContact.name).limit(limit)

        result = await self.db.execute(query)
        contacts = result.scalars().all()
        return {
            "contacts": [self._contact_to_dict(c) for c in contacts],
            "total": len(contacts),
        }

    async def create_contact(self, tenant_id: uuid.UUID, data: dict) -> dict:
        contact = CrmContact(
            tenant_id=tenant_id,
            name=data["name"],
            type=data.get("type", "lead"),
            piva=data.get("vat") or data.get("piva"),
            codice_fiscale=data.get("codice_fiscale"),
            email=data.get("email"),
            phone=data.get("phone"),
            website=data.get("website"),
            address=data.get("address"),
            city=data.get("city"),
            province=data.get("province"),
            sector=data.get("sector"),
            source=data.get("source"),
            assigned_to=uuid.UUID(data["assigned_to"]) if data.get("assigned_to") else None,
            notes=data.get("notes"),
            email_opt_in=data.get("email_opt_in", True),
        )
        self.db.add(contact)
        await self.db.flush()
        return self._contact_to_dict(contact)

    async def update_contact(self, contact_id: uuid.UUID, data: dict) -> dict | None:
        result = await self.db.execute(
            select(CrmContact).where(CrmContact.id == contact_id)
        )
        contact = result.scalar_one_or_none()
        if not contact:
            return None
        for key, val in data.items():
            if val is not None and hasattr(contact, key):
                setattr(contact, key, val)
        await self.db.flush()
        return self._contact_to_dict(contact)

    async def delete_contact(self, contact_id: uuid.UUID) -> bool:
        result = await self.db.execute(
            select(CrmContact).where(CrmContact.id == contact_id)
        )
        contact = result.scalar_one_or_none()
        if not contact:
            return False
        await self.db.delete(contact)
        await self.db.flush()
        return True

    # ── Pipeline Stages ───────────────────────────────────

    async def get_stages(self, tenant_id: uuid.UUID) -> list[dict]:
        await self._ensure_default_stages(tenant_id)
        result = await self.db.execute(
            select(CrmPipelineStage).where(
                CrmPipelineStage.tenant_id == tenant_id,
            ).order_by(CrmPipelineStage.sequence)
        )
        return [self._stage_to_dict(s) for s in result.scalars().all()]

    async def _ensure_default_stages(self, tenant_id: uuid.UUID) -> None:
        count = await self.db.scalar(
            select(func.count(CrmPipelineStage.id)).where(
                CrmPipelineStage.tenant_id == tenant_id,
            )
        )
        if count and count > 0:
            return
        for stage_data in DEFAULT_STAGES:
            self.db.add(CrmPipelineStage(
                tenant_id=tenant_id,
                name=stage_data["name"],
                sequence=stage_data["sequence"],
                probability_default=stage_data["probability_default"],
                color=stage_data["color"],
                is_won=stage_data.get("is_won", False),
                is_lost=stage_data.get("is_lost", False),
            ))
        await self.db.flush()

    # ── Deals ─────────────────────────────────────────────

    async def list_deals(
        self, tenant_id: uuid.UUID,
        stage: str = "", deal_type: str = "", limit: int = 100,
    ) -> dict:
        await self._ensure_default_stages(tenant_id)
        query = select(CrmDeal).where(CrmDeal.tenant_id == tenant_id)
        if deal_type:
            query = query.where(CrmDeal.deal_type == deal_type)
        # Stage filter by name requires subquery
        if stage:
            stage_ids = select(CrmPipelineStage.id).where(
                CrmPipelineStage.tenant_id == tenant_id,
                CrmPipelineStage.name.ilike(f"%{stage}%"),
            )
            query = query.where(CrmDeal.stage_id.in_(stage_ids))
        query = query.order_by(CrmDeal.created_at.desc()).limit(limit)

        result = await self.db.execute(query)
        deals = result.scalars().all()

        deal_dicts = []
        for d in deals:
            dd = await self._deal_to_dict(d, tenant_id)
            deal_dicts.append(dd)

        return {"deals": deal_dicts, "total": len(deal_dicts)}

    async def get_deal(self, deal_id: uuid.UUID, tenant_id: uuid.UUID) -> dict | None:
        result = await self.db.execute(
            select(CrmDeal).where(CrmDeal.id == deal_id, CrmDeal.tenant_id == tenant_id)
        )
        deal = result.scalar_one_or_none()
        if not deal:
            return None
        return await self._deal_to_dict(deal, tenant_id)

    async def create_deal(self, tenant_id: uuid.UUID, data: dict) -> dict:
        await self._ensure_default_stages(tenant_id)
        # Get first stage if not specified
        stage_id = None
        if data.get("stage_id"):
            stage_id = uuid.UUID(data["stage_id"])
        else:
            first = await self.db.execute(
                select(CrmPipelineStage.id).where(
                    CrmPipelineStage.tenant_id == tenant_id,
                ).order_by(CrmPipelineStage.sequence).limit(1)
            )
            stage_id = first.scalar()

        deal = CrmDeal(
            tenant_id=tenant_id,
            contact_id=uuid.UUID(data["contact_id"]) if data.get("contact_id") else None,
            stage_id=stage_id,
            name=data["name"],
            deal_type=data.get("deal_type"),
            expected_revenue=data.get("expected_revenue", 0),
            daily_rate=data.get("daily_rate", 0),
            estimated_days=data.get("estimated_days", 0),
            technology=data.get("technology"),
            probability=data.get("probability", 10.0),
            assigned_to=uuid.UUID(data["assigned_to"]) if data.get("assigned_to") else None,
        )
        self.db.add(deal)
        await self.db.flush()
        return await self._deal_to_dict(deal, tenant_id)

    async def update_deal(self, deal_id: uuid.UUID, tenant_id: uuid.UUID, data: dict) -> dict | None:
        result = await self.db.execute(
            select(CrmDeal).where(CrmDeal.id == deal_id, CrmDeal.tenant_id == tenant_id)
        )
        deal = result.scalar_one_or_none()
        if not deal:
            return None

        old_stage_id = deal.stage_id

        for key, val in data.items():
            if val is not None and hasattr(deal, key):
                if key in ("contact_id", "stage_id", "assigned_to") and isinstance(val, str):
                    setattr(deal, key, uuid.UUID(val))
                else:
                    setattr(deal, key, val)

        # AC-88.3: Auto-update probability when stage changes
        if deal.stage_id != old_stage_id and deal.stage_id:
            stage_result = await self.db.execute(
                select(CrmPipelineStage).where(CrmPipelineStage.id == deal.stage_id)
            )
            stage = stage_result.scalar_one_or_none()
            if stage:
                deal.probability = stage.probability_default

        await self.db.flush()
        return await self._deal_to_dict(deal, tenant_id)

    async def get_won_deals(self, tenant_id: uuid.UUID) -> dict:
        won_stages = select(CrmPipelineStage.id).where(
            CrmPipelineStage.tenant_id == tenant_id,
            CrmPipelineStage.is_won.is_(True),
        )
        result = await self.db.execute(
            select(CrmDeal).where(
                CrmDeal.tenant_id == tenant_id,
                CrmDeal.stage_id.in_(won_stages),
            ).order_by(CrmDeal.updated_at.desc())
        )
        deals = result.scalars().all()
        return {
            "deals": [await self._deal_to_dict(d, tenant_id) for d in deals],
            "total": len(deals),
        }

    # ── Orders ────────────────────────────────────────────

    async def register_order(
        self, deal_id: uuid.UUID, tenant_id: uuid.UUID,
        order_type: str, order_reference: str = "", order_notes: str = "",
    ) -> dict:
        result = await self.db.execute(
            select(CrmDeal).where(CrmDeal.id == deal_id, CrmDeal.tenant_id == tenant_id)
        )
        deal = result.scalar_one_or_none()
        if not deal:
            return {"error": "Deal non trovato"}

        deal.order_type = order_type
        deal.order_reference = order_reference
        deal.order_date = date.today()
        deal.order_notes = order_notes

        # Move to "Ordine Ricevuto" stage
        stage_result = await self.db.execute(
            select(CrmPipelineStage).where(
                CrmPipelineStage.tenant_id == tenant_id,
                CrmPipelineStage.name == "Ordine Ricevuto",
            )
        )
        stage = stage_result.scalar_one_or_none()
        if stage:
            deal.stage_id = stage.id
            deal.probability = stage.probability_default

        await self.db.flush()
        return {"status": "registered", "deal_id": str(deal.id), "order_type": order_type}

    async def get_pending_orders(self, tenant_id: uuid.UUID) -> dict:
        stage_result = await self.db.execute(
            select(CrmPipelineStage.id).where(
                CrmPipelineStage.tenant_id == tenant_id,
                CrmPipelineStage.name == "Ordine Ricevuto",
            )
        )
        stage_id = stage_result.scalar()
        if not stage_id:
            return {"deals": [], "total": 0}

        result = await self.db.execute(
            select(CrmDeal).where(
                CrmDeal.tenant_id == tenant_id,
                CrmDeal.stage_id == stage_id,
                CrmDeal.order_type.isnot(None),
            )
        )
        deals = result.scalars().all()
        return {
            "deals": [await self._deal_to_dict(d, tenant_id) for d in deals],
            "total": len(deals),
        }

    async def confirm_order(self, deal_id: uuid.UUID, tenant_id: uuid.UUID) -> dict:
        result = await self.db.execute(
            select(CrmDeal).where(CrmDeal.id == deal_id, CrmDeal.tenant_id == tenant_id)
        )
        deal = result.scalar_one_or_none()
        if not deal:
            return {"error": "Deal non trovato"}

        # Move to "Confermato"
        stage_result = await self.db.execute(
            select(CrmPipelineStage).where(
                CrmPipelineStage.tenant_id == tenant_id,
                CrmPipelineStage.is_won.is_(True),
            )
        )
        won_stage = stage_result.scalar_one_or_none()
        if won_stage:
            deal.stage_id = won_stage.id
            deal.probability = 100.0

        await self.db.flush()
        return {
            "status": "confirmed",
            "deal_id": str(deal.id),
            "next_step": "Creare la commessa nel sistema NExadata",
        }

    # ── Pipeline Summary ──────────────────────────────────

    async def get_pipeline_summary(self, tenant_id: uuid.UUID) -> dict:
        await self._ensure_default_stages(tenant_id)
        stages = await self.get_stages(tenant_id)

        by_stage = {}
        total_deals = 0
        total_value = 0.0

        for stage in stages:
            result = await self.db.execute(
                select(
                    func.count(CrmDeal.id).label("count"),
                    func.coalesce(func.sum(CrmDeal.expected_revenue), 0.0).label("value"),
                ).where(
                    CrmDeal.tenant_id == tenant_id,
                    CrmDeal.stage_id == uuid.UUID(stage["id"]),
                )
            )
            row = result.one()
            count = row.count or 0
            value = round(float(row.value), 2)
            by_stage[stage["name"]] = {"count": count, "value": value}
            total_deals += count
            total_value += value

        return {
            "total_deals": total_deals,
            "total_value": round(total_value, 2),
            "by_stage": by_stage,
        }

    # ── Activities ────────────────────────────────────────

    async def list_activities(
        self, tenant_id: uuid.UUID,
        deal_id: uuid.UUID | None = None,
        contact_id: uuid.UUID | None = None,
        activity_type: str = "",
        status: str = "",
        limit: int = 50,
    ) -> list[dict]:
        query = select(CrmActivity).where(CrmActivity.tenant_id == tenant_id)
        if deal_id:
            query = query.where(CrmActivity.deal_id == deal_id)
        if contact_id:
            query = query.where(CrmActivity.contact_id == contact_id)
        if activity_type:
            query = query.where(CrmActivity.type == activity_type)
        if status:
            query = query.where(CrmActivity.status == status)
        query = query.order_by(CrmActivity.created_at.desc()).limit(limit)

        result = await self.db.execute(query)
        return [self._activity_to_dict(a) for a in result.scalars().all()]

    async def create_activity(self, tenant_id: uuid.UUID, data: dict) -> dict:
        activity = CrmActivity(
            tenant_id=tenant_id,
            deal_id=uuid.UUID(data["deal_id"]) if data.get("deal_id") else None,
            contact_id=uuid.UUID(data["contact_id"]) if data.get("contact_id") else None,
            user_id=uuid.UUID(data["user_id"]) if data.get("user_id") else None,
            type=data["type"],
            subject=data["subject"],
            description=data.get("description"),
            scheduled_at=data.get("scheduled_at"),
            status=data.get("status", "planned"),
        )
        self.db.add(activity)
        await self.db.flush()
        return self._activity_to_dict(activity)

    async def complete_activity(self, activity_id: uuid.UUID) -> dict | None:
        result = await self.db.execute(
            select(CrmActivity).where(CrmActivity.id == activity_id)
        )
        activity = result.scalar_one_or_none()
        if not activity:
            return None
        activity.status = "completed"
        activity.completed_at = datetime.utcnow()

        # AC-89.5: Update last_contact_at on contact
        if activity.contact_id:
            contact_result = await self.db.execute(
                select(CrmContact).where(CrmContact.id == activity.contact_id)
            )
            contact = contact_result.scalar_one_or_none()
            if contact:
                contact.last_contact_at = datetime.utcnow()

        await self.db.flush()
        return self._activity_to_dict(activity)

    # ── Analytics (US-91) ────────────────────────────────

    async def get_pipeline_analytics(self, tenant_id: uuid.UUID) -> dict:
        """AC-91.1 to AC-91.5: Pipeline analytics."""
        await self._ensure_default_stages(tenant_id)
        stages = await self.get_stages(tenant_id)

        # AC-91.2: Weighted pipeline value
        weighted_result = await self.db.execute(
            select(
                func.coalesce(func.sum(CrmDeal.expected_revenue * CrmDeal.probability / 100), 0.0)
            ).where(CrmDeal.tenant_id == tenant_id)
        )
        weighted_value = round(float(weighted_result.scalar() or 0), 2)

        # AC-91.5: Won/Lost counts
        won_stages = [s for s in stages if s["is_won"]]
        lost_stages = [s for s in stages if s["is_lost"]]

        won_count = 0
        if won_stages:
            r = await self.db.execute(
                select(func.count(CrmDeal.id)).where(
                    CrmDeal.tenant_id == tenant_id,
                    CrmDeal.stage_id == uuid.UUID(won_stages[0]["id"]),
                )
            )
            won_count = r.scalar() or 0

        lost_count = 0
        if lost_stages:
            r = await self.db.execute(
                select(func.count(CrmDeal.id)).where(
                    CrmDeal.tenant_id == tenant_id,
                    CrmDeal.stage_id == uuid.UUID(lost_stages[0]["id"]),
                )
            )
            lost_count = r.scalar() or 0

        total_closed = won_count + lost_count
        won_lost_ratio = round(won_count / total_closed * 100, 1) if total_closed > 0 else 0.0

        # AC-91.3: Conversion rate (deals per stage / total deals)
        total_deals = await self.db.scalar(
            select(func.count(CrmDeal.id)).where(CrmDeal.tenant_id == tenant_id)
        ) or 0

        conversion_by_stage = []
        for stage in stages:
            stage_count = await self.db.scalar(
                select(func.count(CrmDeal.id)).where(
                    CrmDeal.tenant_id == tenant_id,
                    CrmDeal.stage_id == uuid.UUID(stage["id"]),
                )
            ) or 0
            rate = round(stage_count / total_deals * 100, 1) if total_deals > 0 else 0.0
            conversion_by_stage.append({
                "stage": stage["name"],
                "count": stage_count,
                "rate": rate,
            })

        return {
            "weighted_pipeline_value": weighted_value,
            "won_count": won_count,
            "lost_count": lost_count,
            "won_lost_ratio": won_lost_ratio,
            "total_deals": total_deals,
            "conversion_by_stage": conversion_by_stage,
        }

    # ── Serializers ───────────────────────────────────────

    def _contact_to_dict(self, c: CrmContact) -> dict:
        return {
            "id": str(c.id),
            "name": c.name,
            "type": c.type,
            "email": c.email or "",
            "phone": c.phone or "",
            "vat": c.piva or "",
            "city": c.city or "",
            "province": c.province or "",
            "sector": c.sector or "",
            "source": c.source or "",
            "email_opt_in": c.email_opt_in,
            "assigned_to": str(c.assigned_to) if c.assigned_to else None,
        }

    def _stage_to_dict(self, s: CrmPipelineStage) -> dict:
        return {
            "id": str(s.id),
            "name": s.name,
            "sequence": s.sequence,
            "probability_default": s.probability_default,
            "color": s.color,
            "is_won": s.is_won,
            "is_lost": s.is_lost,
        }

    async def _deal_to_dict(self, d: CrmDeal, tenant_id: uuid.UUID) -> dict:
        # Get stage name
        stage_name = ""
        if d.stage_id:
            stage_result = await self.db.execute(
                select(CrmPipelineStage.name).where(CrmPipelineStage.id == d.stage_id)
            )
            stage_name = stage_result.scalar() or ""

        # Get contact name
        client_name = ""
        if d.contact_id:
            contact_result = await self.db.execute(
                select(CrmContact.name).where(CrmContact.id == d.contact_id)
            )
            client_name = contact_result.scalar() or ""

        return {
            "id": str(d.id),
            "name": d.name,
            "client_name": client_name,
            "client_id": str(d.contact_id) if d.contact_id else "",
            "stage": stage_name,
            "stage_id": str(d.stage_id) if d.stage_id else "",
            "expected_revenue": d.expected_revenue,
            "probability": d.probability,
            "deal_type": d.deal_type or "",
            "daily_rate": d.daily_rate,
            "estimated_days": d.estimated_days,
            "technology": d.technology or "",
            "assigned_to": str(d.assigned_to) if d.assigned_to else "",
            "order_type": d.order_type or "",
            "order_reference": d.order_reference or "",
            "order_date": d.order_date.isoformat() if d.order_date else "",
            "order_notes": d.order_notes or "",
        }

    def _activity_to_dict(self, a: CrmActivity) -> dict:
        return {
            "id": str(a.id),
            "deal_id": str(a.deal_id) if a.deal_id else None,
            "contact_id": str(a.contact_id) if a.contact_id else None,
            "user_id": str(a.user_id) if a.user_id else None,
            "type": a.type,
            "subject": a.subject,
            "description": a.description,
            "scheduled_at": a.scheduled_at.isoformat() if a.scheduled_at else None,
            "completed_at": a.completed_at.isoformat() if a.completed_at else None,
            "status": a.status,
        }
