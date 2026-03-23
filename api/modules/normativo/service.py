"""Service layer for normativo module (US-28).

Delegates to NormativoAgent for business logic.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from api.agents.normativo_agent import NormativoAgent


class NormativoService:
    """Service wrapper for NormativoAgent."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.agent = NormativoAgent(db)

    async def check_feed(self, tenant_id: uuid.UUID) -> dict:
        """Check RSS feed for normative updates."""
        return await self.agent.check_feed(tenant_id)

    async def list_alerts(self, tenant_id: uuid.UUID) -> dict:
        """List all normative alerts."""
        return await self.agent.list_alerts(tenant_id)
