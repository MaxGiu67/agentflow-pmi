"""Service for pipeline stages — pre-funnel + CRUD + reorder (US-136)."""

import logging
import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import CrmPipelineStage

logger = logging.getLogger(__name__)


class PipelineService:
    """CRUD for pipeline stages with pre-funnel support."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── US-136: Create stage ────────────────────────────

    async def create_stage(self, tenant_id: uuid.UUID, data: dict) -> dict:
        """AC-136.1: Create pipeline or pre-funnel stage."""
        name = data.get("name", "").strip()
        if not name:
            return {"error": "Nome stadio obbligatorio"}

        stage_type = data.get("stage_type", "pipeline")
        if stage_type not in ("pre_funnel", "pipeline"):
            return {"error": "stage_type deve essere: pre_funnel, pipeline"}

        sequence = data.get("sequence", 0)

        # AC-136.3: pre-funnel stages must have sequence < first pipeline stage
        if stage_type == "pre_funnel":
            first_pipeline = await self.db.execute(
                select(CrmPipelineStage).where(
                    CrmPipelineStage.tenant_id == tenant_id,
                    CrmPipelineStage.stage_type == "pipeline",
                ).order_by(CrmPipelineStage.sequence)
            )
            first = first_pipeline.scalars().first()
            if first and sequence >= first.sequence:
                return {"error": "Stadi pre-funnel devono avere sequenza prima di 'Nuovo Lead'"}

        stage = CrmPipelineStage(
            tenant_id=tenant_id,
            name=name,
            sequence=sequence,
            probability_default=data.get("probability", 0),
            color=data.get("color", "#6B7280"),
            is_won=data.get("is_won", False),
            is_lost=data.get("is_lost", False),
            stage_type=stage_type,
            is_active=data.get("is_active", True),
        )
        self.db.add(stage)
        await self.db.flush()
        return self._to_dict(stage)

    # ── US-136: Update stage ────────────────────────────

    async def update_stage(self, stage_id: uuid.UUID, data: dict) -> dict | None:
        """AC-136 H4: Update stage properties."""
        result = await self.db.execute(
            select(CrmPipelineStage).where(CrmPipelineStage.id == stage_id)
        )
        stage = result.scalar_one_or_none()
        if not stage:
            return None

        for key in ("name", "probability_default", "color", "is_active", "is_won", "is_lost"):
            if key in data and data[key] is not None:
                # map "probability" to "probability_default"
                setattr(stage, key, data[key])
        if "probability" in data and data["probability"] is not None:
            stage.probability_default = data["probability"]

        await self.db.flush()
        return self._to_dict(stage)

    # ── Reorder stages ─────────────────────────────────

    async def reorder_stages(self, stage_order: list[dict]) -> dict:
        """Reorder stages by setting new sequence values."""
        updated = 0
        for item in stage_order:
            result = await self.db.execute(
                select(CrmPipelineStage).where(
                    CrmPipelineStage.id == uuid.UUID(item["stage_id"])
                )
            )
            stage = result.scalar_one_or_none()
            if stage:
                stage.sequence = item["sequence"]
                updated += 1
        await self.db.flush()
        return {"updated": updated}

    # ── List stages ────────────────────────────────────

    async def list_stages(self, tenant_id: uuid.UUID) -> list[dict]:
        """List all stages including pre-funnel, ordered by sequence."""
        result = await self.db.execute(
            select(CrmPipelineStage).where(
                CrmPipelineStage.tenant_id == tenant_id,
            ).order_by(CrmPipelineStage.sequence)
        )
        return [self._to_dict(s) for s in result.scalars().all()]

    def _to_dict(self, s: CrmPipelineStage) -> dict:
        return {
            "id": str(s.id),
            "name": s.name,
            "sequence": s.sequence,
            "probability": s.probability_default,
            "color": s.color,
            "is_won": s.is_won,
            "is_lost": s.is_lost,
            "stage_type": getattr(s, "stage_type", "pipeline") or "pipeline",
            "is_active": getattr(s, "is_active", True),
        }
