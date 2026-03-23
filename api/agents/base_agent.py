"""Base agent with in-memory event bus (Redis pub/sub simulation)."""

import logging
import uuid
from datetime import datetime, UTC

from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import AgentEvent

logger = logging.getLogger(__name__)


class EventBus:
    """In-memory event bus simulating Redis pub/sub.

    In production, this would use Redis pub/sub or Redis Streams.
    For now, we use an in-memory list for simplicity and testability.
    """

    def __init__(self) -> None:
        self._events: list[dict] = []
        self._dead_letter: list[dict] = []

    def publish(self, event_type: str, agent_name: str, payload: dict) -> dict:
        """Publish an event to the bus."""
        event = {
            "id": str(uuid.uuid4()),
            "event_type": event_type,
            "agent_name": agent_name,
            "payload": payload,
            "status": "published",
            "created_at": datetime.now(UTC).isoformat(),
        }
        self._events.append(event)
        logger.info("Event published: %s by %s", event_type, agent_name)
        return event

    def get_events(self, event_type: str | None = None) -> list[dict]:
        """Get events, optionally filtered by type."""
        if event_type:
            return [e for e in self._events if e["event_type"] == event_type]
        return list(self._events)

    def to_dead_letter(self, event: dict, reason: str) -> None:
        """Move a failed event to the dead letter queue."""
        event["status"] = "dead_letter"
        event["error_reason"] = reason
        self._dead_letter.append(event)
        logger.warning("Event moved to dead letter: %s — %s", event["event_type"], reason)

    def get_dead_letter(self) -> list[dict]:
        """Get all dead letter events."""
        return list(self._dead_letter)

    def clear(self) -> None:
        """Clear all events (for testing)."""
        self._events.clear()
        self._dead_letter.clear()


# Global event bus instance (singleton)
event_bus = EventBus()


class BaseAgent:
    """Base class for all agents."""

    agent_name: str = "base"

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.bus = event_bus

    async def publish_event(self, event_type: str, payload: dict, tenant_id: uuid.UUID) -> dict:
        """Publish event and persist to DB."""
        event = self.bus.publish(event_type, self.agent_name, payload)

        # Persist event to DB
        db_event = AgentEvent(
            tenant_id=tenant_id,
            event_type=event_type,
            agent_name=self.agent_name,
            payload=payload,
            status="published",
        )
        self.db.add(db_event)
        await self.db.flush()

        return event

    async def publish_dead_letter(self, event_type: str, payload: dict, tenant_id: uuid.UUID, reason: str) -> dict:
        """Publish event directly to dead letter queue."""
        event = {
            "id": str(uuid.uuid4()),
            "event_type": event_type,
            "agent_name": self.agent_name,
            "payload": payload,
            "status": "dead_letter",
            "error_reason": reason,
        }
        self.bus.to_dead_letter(event, reason)

        # Persist to DB
        db_event = AgentEvent(
            tenant_id=tenant_id,
            event_type=event_type,
            agent_name=self.agent_name,
            payload=payload,
            status="dead_letter",
        )
        self.db.add(db_event)
        await self.db.flush()

        return event
