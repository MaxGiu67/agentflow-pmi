"""Router for agent configuration module (US-A03)."""

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
)
from api.modules.agent_config.service import AgentConfigService

router = APIRouter(prefix="/agents/config", tags=["agent-config"])


def get_service(db: AsyncSession = Depends(get_db)) -> AgentConfigService:
    return AgentConfigService(db)


@router.get("", response_model=AgentConfigListResponse)
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


@router.patch("/{agent_type}", response_model=AgentConfigResponse)
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


@router.post("/reset", response_model=AgentConfigResetResponse)
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
