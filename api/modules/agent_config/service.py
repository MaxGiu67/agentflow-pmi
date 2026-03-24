"""Service layer for agent configuration module (US-A03)."""

import logging
import uuid

from sqlalchemy import select, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import AgentConfig
from api.modules.agent_config.defaults import DEFAULT_AGENTS

logger = logging.getLogger(__name__)


class AgentConfigService:
    """Business logic for agent configuration operations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_configs(self, tenant_id: uuid.UUID) -> dict:
        """List all agent configs for a tenant, creating defaults if missing."""
        await self._ensure_defaults(tenant_id)

        result = await self.db.execute(
            select(AgentConfig)
            .where(AgentConfig.tenant_id == tenant_id)
            .order_by(AgentConfig.agent_type)
        )
        configs = result.scalars().all()

        # Build visible flag from defaults
        defaults_map = {d["agent_type"]: d for d in DEFAULT_AGENTS}

        items = []
        for cfg in configs:
            default = defaults_map.get(cfg.agent_type, {})
            items.append({
                "id": cfg.id,
                "agent_type": cfg.agent_type,
                "display_name": cfg.display_name,
                "personality": cfg.personality,
                "icon": cfg.icon,
                "enabled": cfg.enabled,
                "visible": default.get("visible", True),
                "created_at": cfg.created_at,
                "updated_at": cfg.updated_at,
            })

        return {"items": items, "total": len(items)}

    async def update_config(
        self,
        tenant_id: uuid.UUID,
        agent_type: str,
        update_data: dict,
    ) -> dict:
        """Update a specific agent configuration."""
        await self._ensure_defaults(tenant_id)

        result = await self.db.execute(
            select(AgentConfig).where(
                and_(
                    AgentConfig.tenant_id == tenant_id,
                    AgentConfig.agent_type == agent_type,
                )
            )
        )
        config = result.scalar_one_or_none()
        if not config:
            raise ValueError(f"Configurazione agente '{agent_type}' non trovata")

        # Apply updates
        for key, value in update_data.items():
            if value is not None and hasattr(config, key):
                setattr(config, key, value)

        await self.db.flush()
        await self.db.refresh(config)

        defaults_map = {d["agent_type"]: d for d in DEFAULT_AGENTS}
        default = defaults_map.get(config.agent_type, {})

        return {
            "id": config.id,
            "agent_type": config.agent_type,
            "display_name": config.display_name,
            "personality": config.personality,
            "icon": config.icon,
            "enabled": config.enabled,
            "visible": default.get("visible", True),
            "created_at": config.created_at,
            "updated_at": config.updated_at,
        }

    async def reset_defaults(self, tenant_id: uuid.UUID) -> dict:
        """Reset all agent configs to defaults for a tenant."""
        # Delete existing configs
        await self.db.execute(
            delete(AgentConfig).where(AgentConfig.tenant_id == tenant_id)
        )
        await self.db.flush()

        # Re-create from defaults
        await self._create_defaults(tenant_id)

        return {"message": "Configurazioni agenti ripristinate", "total": len(DEFAULT_AGENTS)}

    async def _ensure_defaults(self, tenant_id: uuid.UUID) -> None:
        """Create default agent configs if none exist for this tenant."""
        result = await self.db.execute(
            select(AgentConfig).where(AgentConfig.tenant_id == tenant_id).limit(1)
        )
        if result.scalar_one_or_none() is None:
            await self._create_defaults(tenant_id)

    async def _create_defaults(self, tenant_id: uuid.UUID) -> None:
        """Create all default agent configs for a tenant."""
        for agent_data in DEFAULT_AGENTS:
            config = AgentConfig(
                tenant_id=tenant_id,
                agent_type=agent_data["agent_type"],
                display_name=agent_data["display_name"],
                icon=agent_data.get("icon"),
                enabled=agent_data.get("enabled", True),
                personality=agent_data.get("personality"),
            )
            self.db.add(config)
        await self.db.flush()
