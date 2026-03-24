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


# ============================================================
# LLM Settings schemas
# ============================================================


class LLMModelInfo(BaseModel):
    """Single model info."""
    id: str
    name: str
    context: int
    max_output: int
    price_input: float
    price_output: float


class LLMProviderInfo(BaseModel):
    """Provider info with its models."""
    id: str
    name: str
    configured: bool
    default_model: str
    models: list[LLMModelInfo]


class LLMSettingsResponse(BaseModel):
    """Current LLM settings and available providers."""
    current_provider: str
    current_model: str
    available_providers: list[LLMProviderInfo]


class LLMSettingsUpdate(BaseModel):
    """Request to update LLM settings."""
    provider: str
    model: str
