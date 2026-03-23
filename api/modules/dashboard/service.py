"""Service layer for dashboard module."""

import logging
import uuid
from datetime import datetime, UTC

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import AgentEvent, Invoice, User

logger = logging.getLogger(__name__)


class DashboardService:
    """Service for dashboard operations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_summary(self, user: User) -> dict:
        """Get complete dashboard summary."""
        if not user.tenant_id:
            return {
                "counters": {
                    "total": 0,
                    "pending": 0,
                    "parsed": 0,
                    "categorized": 0,
                    "registered": 0,
                    "error": 0,
                },
                "recent_invoices": [],
                "agents": await self._get_agent_statuses(None),
                "last_sync_at": None,
                "message": "Nessuna fattura presente. Collega il cassetto fiscale per iniziare.",
            }

        tenant_id = user.tenant_id

        # Counters by status
        counters = await self._get_counters(tenant_id)

        # Recent 10 invoices
        recent_result = await self.db.execute(
            select(Invoice)
            .where(Invoice.tenant_id == tenant_id)
            .order_by(Invoice.created_at.desc())
            .limit(10)
        )
        recent_invoices = recent_result.scalars().all()

        # Last sync
        last_sync_result = await self.db.execute(
            select(Invoice.created_at)
            .where(
                and_(
                    Invoice.tenant_id == tenant_id,
                    Invoice.source == "cassetto_fiscale",
                )
            )
            .order_by(Invoice.created_at.desc())
            .limit(1)
        )
        last_sync_at = last_sync_result.scalar_one_or_none()

        # Agent statuses
        agents = await self._get_agent_statuses(tenant_id)

        # Message
        if counters["total"] == 0:
            message = "Nessuna fattura presente. Collega il cassetto fiscale per iniziare."
        else:
            message = f"{counters['total']} fatture totali, {counters['pending']} in attesa di elaborazione"

        return {
            "counters": counters,
            "recent_invoices": recent_invoices,
            "agents": agents,
            "last_sync_at": last_sync_at,
            "message": message,
        }

    async def _get_counters(self, tenant_id: uuid.UUID) -> dict:
        """Get invoice counters by processing status."""
        statuses = ["pending", "parsed", "categorized", "registered", "error"]
        counters = {"total": 0}

        for s in statuses:
            result = await self.db.execute(
                select(func.count(Invoice.id)).where(
                    and_(
                        Invoice.tenant_id == tenant_id,
                        Invoice.processing_status == s,
                    )
                )
            )
            count = result.scalar() or 0
            counters[s] = count
            counters["total"] += count

        return counters

    async def _get_agent_statuses(self, tenant_id: uuid.UUID | None) -> list[dict]:
        """Get agent statuses from recent events."""
        agent_names = ["fisco_agent", "parser_agent", "learning_agent"]
        statuses = []

        for agent_name in agent_names:
            if tenant_id is None:
                statuses.append({
                    "name": agent_name,
                    "status": "idle",
                    "last_run": None,
                    "events_published": 0,
                    "events_failed": 0,
                })
                continue

            # Last event
            last_event_result = await self.db.execute(
                select(AgentEvent.created_at)
                .where(
                    and_(
                        AgentEvent.tenant_id == tenant_id,
                        AgentEvent.agent_name == agent_name,
                    )
                )
                .order_by(AgentEvent.created_at.desc())
                .limit(1)
            )
            last_run = last_event_result.scalar_one_or_none()

            # Published events count
            published_result = await self.db.execute(
                select(func.count(AgentEvent.id)).where(
                    and_(
                        AgentEvent.tenant_id == tenant_id,
                        AgentEvent.agent_name == agent_name,
                        AgentEvent.status == "published",
                    )
                )
            )
            events_published = published_result.scalar() or 0

            # Failed events count
            failed_result = await self.db.execute(
                select(func.count(AgentEvent.id)).where(
                    and_(
                        AgentEvent.tenant_id == tenant_id,
                        AgentEvent.agent_name == agent_name,
                        AgentEvent.status == "dead_letter",
                    )
                )
            )
            events_failed = failed_result.scalar() or 0

            agent_status = "idle"
            if last_run:
                agent_status = "active"

            statuses.append({
                "name": agent_name,
                "status": agent_status,
                "last_run": last_run,
                "events_published": events_published,
                "events_failed": events_failed,
            })

        return statuses

    async def get_agent_statuses(self, user: User) -> list[dict]:
        """Get agent statuses for the user's tenant."""
        return await self._get_agent_statuses(user.tenant_id)
