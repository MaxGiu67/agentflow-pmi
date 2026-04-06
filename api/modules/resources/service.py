"""Resource service — CRUD + matching + margin (US-204, US-205, US-206, US-207).

Manages internal consultants/resources for T&M pipeline.
Matching algorithm: tech stack fit (60%) + seniority match (25%) + availability (15%).
"""

import logging
import uuid
from datetime import date

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import Resource, ResourceSkill

logger = logging.getLogger(__name__)

SENIORITY_ORDER = {"junior": 1, "mid": 2, "senior": 3, "lead": 4}


class ResourceService:
    """CRUD + matching for internal resources."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── US-204: CRUD ───────────────────────────────────

    async def create_resource(self, tenant_id: uuid.UUID, data: dict) -> dict:
        name = data.get("name", "").strip()
        if not name:
            return {"error": "Nome risorsa obbligatorio"}

        resource = Resource(
            tenant_id=tenant_id,
            name=name,
            seniority=data.get("seniority", "mid"),
            daily_cost=data.get("daily_cost", 0),
            suggested_daily_rate=data.get("suggested_daily_rate", 0),
            available_from=data.get("available_from"),
            current_project=data.get("current_project"),
            notes=data.get("notes"),
        )
        self.db.add(resource)
        await self.db.flush()
        return await self._resource_to_dict(resource)

    async def list_resources(
        self, tenant_id: uuid.UUID,
        seniority: str = "", skill: str = "", available_only: bool = False,
    ) -> list[dict]:
        query = select(Resource).where(
            Resource.tenant_id == tenant_id, Resource.is_active.is_(True),
        )
        if seniority:
            query = query.where(Resource.seniority == seniority)
        if available_only:
            query = query.where(
                (Resource.available_from.is_(None)) | (Resource.available_from <= date.today())
            )
        query = query.order_by(Resource.name)
        result = await self.db.execute(query)
        resources = []
        for r in result.scalars().all():
            d = await self._resource_to_dict(r)
            if skill:
                if not any(s["skill_name"].lower() == skill.lower() for s in d["skills"]):
                    continue
            resources.append(d)
        return resources

    async def get_resource(self, resource_id: uuid.UUID) -> dict | None:
        result = await self.db.execute(select(Resource).where(Resource.id == resource_id))
        r = result.scalar_one_or_none()
        if not r:
            return None
        return await self._resource_to_dict(r)

    async def update_resource(self, resource_id: uuid.UUID, data: dict) -> dict | None:
        result = await self.db.execute(select(Resource).where(Resource.id == resource_id))
        r = result.scalar_one_or_none()
        if not r:
            return None
        for key in ("name", "seniority", "daily_cost", "suggested_daily_rate", "available_from", "current_project", "notes", "is_active"):
            if key in data and data[key] is not None:
                setattr(r, key, data[key])
        await self.db.flush()
        return await self._resource_to_dict(r)

    # ── Skills ─────────────────────────────────────────

    async def add_skill(self, resource_id: uuid.UUID, data: dict) -> dict:
        skill = ResourceSkill(
            resource_id=resource_id,
            skill_name=data.get("skill_name", ""),
            skill_level=data.get("skill_level", 3),
            certification=data.get("certification"),
        )
        self.db.add(skill)
        await self.db.flush()
        return {"id": str(skill.id), "skill_name": skill.skill_name, "skill_level": skill.skill_level}

    async def remove_skill(self, skill_id: uuid.UUID) -> bool:
        result = await self.db.execute(select(ResourceSkill).where(ResourceSkill.id == skill_id))
        skill = result.scalar_one_or_none()
        if not skill:
            return False
        await self.db.delete(skill)
        await self.db.flush()
        return True

    # ── US-205: Matching ───────────────────────────────

    async def match_resources(
        self, tenant_id: uuid.UUID,
        tech_stack: list[str], seniority: str = "",
        min_availability: date | None = None, limit: int = 5,
    ) -> list[dict]:
        """Match client request with available internal resources.

        Score: tech match (60%) + seniority match (25%) + availability (15%)
        """
        resources = await self.list_resources(tenant_id, available_only=True)
        if not resources:
            return []

        scored = []
        for r in resources:
            skill_names = {s["skill_name"].lower() for s in r["skills"]}
            requested = {t.lower() for t in tech_stack}

            # Tech match (60%)
            if not requested:
                tech_score = 50
            else:
                matched = requested & skill_names
                tech_score = (len(matched) / len(requested)) * 100

            # Seniority match (25%)
            if not seniority:
                sen_score = 50
            else:
                req_level = SENIORITY_ORDER.get(seniority, 2)
                res_level = SENIORITY_ORDER.get(r["seniority"], 2)
                if res_level >= req_level:
                    sen_score = 100
                elif res_level == req_level - 1:
                    sen_score = 60
                else:
                    sen_score = 20

            # Availability (15%)
            if r["available_from"] is None:
                avail_score = 100  # Available now
            elif min_availability:
                avail_date = date.fromisoformat(r["available_from"]) if isinstance(r["available_from"], str) else r["available_from"]
                if avail_date <= min_availability:
                    avail_score = 100
                else:
                    days_gap = (avail_date - min_availability).days
                    avail_score = max(0, 100 - days_gap * 3)
            else:
                avail_score = 80

            total_score = round(tech_score * 0.6 + sen_score * 0.25 + avail_score * 0.15)
            r["match_score"] = total_score
            scored.append(r)

        scored.sort(key=lambda x: x["match_score"], reverse=True)
        return scored[:limit]

    # ── US-206: Margin ─────────────────────────────────

    def calc_margin(self, daily_rate: float, daily_cost: float) -> dict:
        """Calculate margin for a T&M offer."""
        if daily_rate <= 0:
            return {"error": "Tariffa deve essere > 0"}
        margin_euro = daily_rate - daily_cost
        margin_pct = (margin_euro / daily_rate) * 100
        below_threshold = margin_pct < 15
        return {
            "daily_rate": daily_rate,
            "daily_cost": daily_cost,
            "margin_euro": round(margin_euro, 2),
            "margin_pct": round(margin_pct, 1),
            "below_threshold": below_threshold,
            "threshold": 15,
            "status": "needs_approval" if below_threshold else "ok",
        }

    # ── US-207: Bench ──────────────────────────────────

    async def get_bench(self, tenant_id: uuid.UUID, days_ahead: int = 30) -> list[dict]:
        """Resources becoming available within N days."""
        from datetime import timedelta
        target = date.today() + timedelta(days=days_ahead)
        query = select(Resource).where(
            Resource.tenant_id == tenant_id,
            Resource.is_active.is_(True),
            Resource.available_from.isnot(None),
            Resource.available_from <= target,
        ).order_by(Resource.available_from)
        result = await self.db.execute(query)
        return [await self._resource_to_dict(r) for r in result.scalars().all()]

    # ── Helpers ────────────────────────────────────────

    async def _resource_to_dict(self, r: Resource) -> dict:
        skills_result = await self.db.execute(
            select(ResourceSkill).where(ResourceSkill.resource_id == r.id).order_by(ResourceSkill.skill_name)
        )
        skills = [
            {"id": str(s.id), "skill_name": s.skill_name, "skill_level": s.skill_level, "certification": s.certification}
            for s in skills_result.scalars().all()
        ]
        return {
            "id": str(r.id),
            "name": r.name,
            "seniority": r.seniority,
            "daily_cost": r.daily_cost,
            "suggested_daily_rate": r.suggested_daily_rate,
            "available_from": r.available_from.isoformat() if r.available_from else None,
            "current_project": r.current_project,
            "notes": r.notes,
            "is_active": r.is_active,
            "skills": skills,
        }
