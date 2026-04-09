"""Pipeline template models: PipelineTemplate, PipelineTemplateStage."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, JSON, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from api.db.models.base import Base


class PipelineTemplate(Base):
    """Pipeline template — FSM definition for a product type (US-200)."""
    __tablename__ = "pipeline_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)  # tm_consulting, fixed_project, elevia_product
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    pipeline_type: Mapped[str] = mapped_column(String(50), nullable=False, default="custom")  # services, product, custom
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class PipelineTemplateStage(Base):
    """Stage within a pipeline template (US-200)."""
    __tablename__ = "pipeline_template_stages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    required_fields: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # ["budget", "timeline", ...]
    sla_days: Mapped[int] = mapped_column(Integer, default=7)
    is_won: Mapped[bool] = mapped_column(Boolean, default=False)
    is_lost: Mapped[bool] = mapped_column(Boolean, default=False)
    is_optional: Mapped[bool] = mapped_column(Boolean, default=False)
