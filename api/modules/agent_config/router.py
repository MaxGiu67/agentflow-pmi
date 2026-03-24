"""Router for agent configuration module (US-A03) and LLM settings."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from api.modules.agent_config.schemas import (
    AgentConfigListResponse,
    AgentConfigResponse,
    AgentConfigResetResponse,
    AgentConfigUpdate,
    LLMSettingsResponse,
    LLMSettingsUpdate,
)
from api.modules.agent_config.service import AgentConfigService
from api.orchestrator.llm_adapter import LLMAdapter, LLM_PROVIDERS
from api.orchestrator.memory_node import MemoryManager

router = APIRouter(prefix="/agents", tags=["agent-config"])


def get_service(db: AsyncSession = Depends(get_db)) -> AgentConfigService:
    return AgentConfigService(db)


@router.get("/config", response_model=AgentConfigListResponse)
async def list_agent_configs(
    user: User = Depends(get_current_user),
    service: AgentConfigService = Depends(get_service),
) -> AgentConfigListResponse:
    """List all agent configurations for current tenant.

    US-A03: Agent Config.
    Creates default configurations if none exist.
    """
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    result = await service.list_configs(user.tenant_id)
    return AgentConfigListResponse(**result)


@router.patch("/config/{agent_type}", response_model=AgentConfigResponse)
async def update_agent_config(
    agent_type: str,
    update: AgentConfigUpdate,
    user: User = Depends(get_current_user),
    service: AgentConfigService = Depends(get_service),
) -> AgentConfigResponse:
    """Update a specific agent configuration.

    US-A03: Agent Config.
    """
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    try:
        update_dict = update.model_dump(exclude_unset=True)
        result = await service.update_config(user.tenant_id, agent_type, update_dict)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    return AgentConfigResponse(**result)


@router.post("/config/reset", response_model=AgentConfigResetResponse)
async def reset_agent_configs(
    user: User = Depends(get_current_user),
    service: AgentConfigService = Depends(get_service),
) -> AgentConfigResetResponse:
    """Reset all agent configurations to defaults.

    US-A03: Agent Config.
    """
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    result = await service.reset_defaults(user.tenant_id)
    return AgentConfigResetResponse(**result)


# ============================================================
# LLM Settings
# ============================================================


@router.get("/llm-settings", response_model=LLMSettingsResponse)
async def get_llm_settings(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LLMSettingsResponse:
    """Get current LLM provider/model and available options."""
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    memory_mgr = MemoryManager(db)
    memories = await memory_mgr.get_memories(user.tenant_id, user.id, limit=50)
    mem_dict = {m["key"]: m["value"] for m in memories}

    from api.config import settings as app_settings

    current_provider = mem_dict.get("llm_provider", app_settings.default_llm_provider)
    current_model = mem_dict.get("llm_model", app_settings.default_llm_model)

    available_providers = LLMAdapter.get_available_providers()

    return LLMSettingsResponse(
        current_provider=current_provider,
        current_model=current_model,
        available_providers=available_providers,
    )


@router.patch("/llm-settings", response_model=LLMSettingsResponse)
async def update_llm_settings(
    body: LLMSettingsUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LLMSettingsResponse:
    """Update LLM provider and model preference."""
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    provider = body.provider
    model = body.model

    # Validate provider
    if provider not in LLM_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Provider '{provider}' non supportato. Disponibili: {list(LLM_PROVIDERS.keys())}",
        )

    # Validate model for provider
    provider_config = LLM_PROVIDERS[provider]
    valid_model_ids = [m["id"] for m in provider_config["models"]]
    if model not in valid_model_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Modello '{model}' non disponibile per il provider '{provider}'. Disponibili: {valid_model_ids}",
        )

    memory_mgr = MemoryManager(db)
    await memory_mgr.save_memory(user.tenant_id, user.id, "llm_provider", provider, "setting")
    await memory_mgr.save_memory(user.tenant_id, user.id, "llm_model", model, "setting")

    available_providers = LLMAdapter.get_available_providers()

    return LLMSettingsResponse(
        current_provider=provider,
        current_model=model,
        available_providers=available_providers,
    )
