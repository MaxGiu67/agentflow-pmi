"""Schemas for agent configuration module (US-A03)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AgentConfigResponse(BaseModel):
    """Single agent configuration."""
    id: UUID
    agent_type: str
    display_name: str | None = None
    personality: str | None = None
    icon: str | None = None
    enabled: bool = True
    visible: bool = True
    created_at: datetime
    updated_at: datetime


class AgentConfigListResponse(BaseModel):
    """List of agent configurations."""
    items: list[AgentConfigResponse]
    total: int


class AgentConfigUpdate(BaseModel):
    """Request to update an agent configuration."""
    display_name: str | None = Field(None, min_length=1, max_length=100)
    personality: str | None = None
    enabled: bool | None = None
    icon: str | None = None


class AgentConfigResetResponse(BaseModel):
    """Response after resetting agent configurations."""
    message: str
    total: int
