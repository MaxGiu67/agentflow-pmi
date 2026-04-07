"""Pipeline Templates service — CRUD + seed (US-200, US-201, US-202).

Manages pipeline templates (FSM definitions) that determine the sales process
for each product type. Seeds 3 default templates: T&M, Corpo, Elevia.
"""

import logging
import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import PipelineTemplate, PipelineTemplateStage

logger = logging.getLogger(__name__)

# ── Seed data ──────────────────────────────────────────

TM_STAGES = [
    {"code": "lead", "name": "Lead", "sequence": 10, "sla_days": 3, "required_fields": ["company", "contact"]},
    {"code": "qualifica", "name": "Qualifica", "sequence": 20, "sla_days": 7, "required_fields": ["budget", "timeline", "tech_stack"]},
    {"code": "match", "name": "Match risorse", "sequence": 30, "sla_days": 5, "required_fields": ["match_score"]},
    {"code": "offerta", "name": "Offerta", "sequence": 40, "sla_days": 5, "required_fields": ["revenue", "margin"]},
    {"code": "negoziazione", "name": "Negoziazione", "sequence": 50, "sla_days": 15},
    {"code": "won", "name": "Won", "sequence": 60, "is_won": True},
    {"code": "lost", "name": "Lost", "sequence": 61, "is_lost": True},
    {"code": "delivery", "name": "Delivery", "sequence": 70, "sla_days": 90},
]

CORPO_STAGES = [
    {"code": "lead", "name": "Lead", "sequence": 10, "sla_days": 3, "required_fields": ["company", "contact"]},
    {"code": "analisi", "name": "Analisi requisiti", "sequence": 20, "sla_days": 10, "required_fields": ["requirements_notes"]},
    {"code": "specifiche", "name": "Specifiche", "sequence": 30, "sla_days": 10, "required_fields": ["scope", "deliverables"]},
    {"code": "demo", "name": "Demo", "sequence": 40, "sla_days": 7, "is_optional": True},
    {"code": "offerta", "name": "Offerta", "sequence": 50, "sla_days": 5, "required_fields": ["revenue", "effort_days"]},
    {"code": "negoziazione", "name": "Negoziazione", "sequence": 60, "sla_days": 15},
    {"code": "won", "name": "Won", "sequence": 70, "is_won": True},
    {"code": "lost", "name": "Lost", "sequence": 71, "is_lost": True},
    {"code": "delivery", "name": "Delivery", "sequence": 80, "sla_days": 120},
]

ELEVIA_STAGES = [
    {"code": "prospect", "name": "Prospect", "sequence": 10, "sla_days": 2, "required_fields": ["ateco", "company_size"]},
    {"code": "connessione", "name": "Connessione LinkedIn", "sequence": 20, "sla_days": 7},
    {"code": "engagement", "name": "Engagement", "sequence": 30, "sla_days": 14},
    {"code": "discovery", "name": "Discovery Call", "sequence": 40, "sla_days": 5, "required_fields": ["pain_points", "use_cases"]},
    {"code": "demo", "name": "Demo", "sequence": 50, "sla_days": 7, "is_optional": True},
    {"code": "offerta", "name": "Offerta", "sequence": 60, "sla_days": 3, "required_fields": ["revenue", "use_case_bundle"]},
    {"code": "won", "name": "Won", "sequence": 70, "is_won": True},
    {"code": "lost", "name": "Lost", "sequence": 71, "is_lost": True},
    {"code": "onboarding", "name": "Onboarding", "sequence": 80, "sla_days": 30},
]

SEED_TEMPLATES = [
    {"code": "vendita_diretta", "name": "Vendita Diretta", "pipeline_type": "services", "description": "Pipeline per vendita diretta: consulenza, T&M, hardware, prodotti, servizi. Vendita relazionale con matching risorse/disponibilita.", "stages": TM_STAGES},
    {"code": "progetto_corpo", "name": "Progetto a Corpo", "pipeline_type": "services", "description": "Pipeline per progetti a prezzo fisso con fase analisi requisiti e specifiche", "stages": CORPO_STAGES},
    {"code": "social_selling", "name": "Social Selling", "pipeline_type": "product", "description": "Pipeline per vendita via LinkedIn/social: prospect, engagement, discovery, demo, offerta. Per Elevia e prodotti digitali.", "stages": ELEVIA_STAGES},
]


class PipelineTemplateService:
    """CRUD + seed for pipeline templates."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── US-200: Seed ───────────────────────────────────

    async def ensure_defaults(self, tenant_id: uuid.UUID) -> None:
        """Seed default templates if tenant has none."""
        count = await self.db.scalar(
            select(func.count(PipelineTemplate.id)).where(
                PipelineTemplate.tenant_id == tenant_id,
            )
        )
        if count and count > 0:
            return

        for tmpl in SEED_TEMPLATES:
            template = PipelineTemplate(
                tenant_id=tenant_id,
                code=tmpl["code"],
                name=tmpl["name"],
                pipeline_type=tmpl["pipeline_type"],
                description=tmpl["description"],
            )
            self.db.add(template)
            await self.db.flush()

            for s in tmpl["stages"]:
                stage = PipelineTemplateStage(
                    template_id=template.id,
                    code=s["code"],
                    name=s["name"],
                    sequence=s["sequence"],
                    required_fields=s.get("required_fields"),
                    sla_days=s.get("sla_days", 7),
                    is_won=s.get("is_won", False),
                    is_lost=s.get("is_lost", False),
                    is_optional=s.get("is_optional", False),
                )
                self.db.add(stage)

            await self.db.flush()

        logger.info("Seeded %d pipeline templates for tenant %s", len(SEED_TEMPLATES), tenant_id)

    # ── US-200: List ───────────────────────────────────

    async def list_templates(self, tenant_id: uuid.UUID) -> list[dict]:
        """List all pipeline templates for tenant."""
        await self.ensure_defaults(tenant_id)
        result = await self.db.execute(
            select(PipelineTemplate).where(
                PipelineTemplate.tenant_id == tenant_id,
            ).order_by(PipelineTemplate.code)
        )
        templates = []
        for t in result.scalars().all():
            stages = await self._get_stages(t.id)
            templates.append(self._to_dict(t, stages))
        return templates

    async def get_template(self, template_id: uuid.UUID, tenant_id: uuid.UUID) -> dict | None:
        """Get a single template with stages."""
        result = await self.db.execute(
            select(PipelineTemplate).where(
                PipelineTemplate.id == template_id,
                PipelineTemplate.tenant_id == tenant_id,
            )
        )
        t = result.scalar_one_or_none()
        if not t:
            return None
        stages = await self._get_stages(t.id)
        return self._to_dict(t, stages)

    async def get_template_by_code(self, tenant_id: uuid.UUID, code: str) -> dict | None:
        """Get template by code."""
        await self.ensure_defaults(tenant_id)
        result = await self.db.execute(
            select(PipelineTemplate).where(
                PipelineTemplate.tenant_id == tenant_id,
                PipelineTemplate.code == code,
            )
        )
        t = result.scalar_one_or_none()
        if not t:
            return None
        stages = await self._get_stages(t.id)
        return self._to_dict(t, stages)

    # ── US-202: CRUD ───────────────────────────────────

    async def create_template(self, tenant_id: uuid.UUID, data: dict) -> dict:
        """Create a custom pipeline template."""
        code = data.get("code", "").strip().lower()
        if not code:
            return {"error": "Codice template obbligatorio"}

        template = PipelineTemplate(
            tenant_id=tenant_id,
            code=code,
            name=data.get("name", code),
            pipeline_type=data.get("pipeline_type", "custom"),
            description=data.get("description"),
        )
        self.db.add(template)
        await self.db.flush()

        # Create stages if provided
        stages_data = data.get("stages", [])
        for s in stages_data:
            stage = PipelineTemplateStage(
                template_id=template.id,
                code=s.get("code", ""),
                name=s.get("name", ""),
                sequence=s.get("sequence", 0),
                required_fields=s.get("required_fields"),
                sla_days=s.get("sla_days", 7),
                is_won=s.get("is_won", False),
                is_lost=s.get("is_lost", False),
                is_optional=s.get("is_optional", False),
            )
            self.db.add(stage)
        await self.db.flush()

        stages = await self._get_stages(template.id)
        return self._to_dict(template, stages)

    async def update_template(self, template_id: uuid.UUID, tenant_id: uuid.UUID, data: dict) -> dict | None:
        """Update template name/description."""
        result = await self.db.execute(
            select(PipelineTemplate).where(
                PipelineTemplate.id == template_id,
                PipelineTemplate.tenant_id == tenant_id,
            )
        )
        t = result.scalar_one_or_none()
        if not t:
            return None

        for key in ("name", "description", "is_active"):
            if key in data:
                setattr(t, key, data[key])
        await self.db.flush()

        stages = await self._get_stages(t.id)
        return self._to_dict(t, stages)

    async def delete_template(self, template_id: uuid.UUID, tenant_id: uuid.UUID) -> bool:
        """Delete template and its stages."""
        from sqlalchemy import delete as sql_delete
        result = await self.db.execute(
            select(PipelineTemplate).where(
                PipelineTemplate.id == template_id,
                PipelineTemplate.tenant_id == tenant_id,
            )
        )
        t = result.scalar_one_or_none()
        if not t:
            return False
        await self.db.execute(sql_delete(PipelineTemplateStage).where(PipelineTemplateStage.template_id == template_id))
        await self.db.delete(t)
        await self.db.flush()
        return True

    # ── Stage CRUD ────────────────────────────────────

    async def add_stage(self, template_id: uuid.UUID, tenant_id: uuid.UUID, data: dict) -> dict | None:
        """Add a stage to a template."""
        result = await self.db.execute(
            select(PipelineTemplate).where(PipelineTemplate.id == template_id, PipelineTemplate.tenant_id == tenant_id)
        )
        if not result.scalar_one_or_none():
            return None
        stage = PipelineTemplateStage(
            template_id=template_id,
            code=data.get("code", "").strip().lower().replace(" ", "_"),
            name=data.get("name", ""),
            sequence=data.get("sequence", 0),
            required_fields=data.get("required_fields"),
            sla_days=data.get("sla_days", 7),
            is_won=data.get("is_won", False),
            is_lost=data.get("is_lost", False),
            is_optional=data.get("is_optional", False),
        )
        self.db.add(stage)
        await self.db.flush()
        return self._stage_to_dict(stage)

    async def update_stage(self, stage_id: uuid.UUID, data: dict) -> dict | None:
        """Update a template stage."""
        result = await self.db.execute(select(PipelineTemplateStage).where(PipelineTemplateStage.id == stage_id))
        stage = result.scalar_one_or_none()
        if not stage:
            return None
        for key in ("name", "code", "sequence", "sla_days", "is_won", "is_lost", "is_optional", "required_fields"):
            if key in data:
                setattr(stage, key, data[key])
        await self.db.flush()
        return self._stage_to_dict(stage)

    async def delete_stage(self, stage_id: uuid.UUID) -> bool:
        """Delete a template stage."""
        result = await self.db.execute(select(PipelineTemplateStage).where(PipelineTemplateStage.id == stage_id))
        stage = result.scalar_one_or_none()
        if not stage:
            return False
        await self.db.delete(stage)
        await self.db.flush()
        return True

    # ── Helpers ────────────────────────────────────────

    async def _get_stages(self, template_id: uuid.UUID) -> list[dict]:
        result = await self.db.execute(
            select(PipelineTemplateStage).where(
                PipelineTemplateStage.template_id == template_id,
            ).order_by(PipelineTemplateStage.sequence)
        )
        return [self._stage_to_dict(s) for s in result.scalars().all()]

    def _to_dict(self, t: PipelineTemplate, stages: list[dict]) -> dict:
        return {
            "id": str(t.id),
            "code": t.code,
            "name": t.name,
            "pipeline_type": t.pipeline_type,
            "description": t.description,
            "is_active": t.is_active,
            "stages": stages,
            "stage_count": len(stages),
        }

    def _stage_to_dict(self, s: PipelineTemplateStage) -> dict:
        return {
            "id": str(s.id),
            "code": s.code,
            "name": s.name,
            "sequence": s.sequence,
            "required_fields": s.required_fields or [],
            "sla_days": s.sla_days,
            "is_won": s.is_won,
            "is_lost": s.is_lost,
            "is_optional": s.is_optional,
        }
