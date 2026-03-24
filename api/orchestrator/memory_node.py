"""Memory manager — saves and retrieves user preferences across conversations (US-A08)."""

import uuid
from datetime import datetime, UTC

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import ConversationMemory


class MemoryManager:
    """Manage cross-conversation memory entries for a user."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def save_memory(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        key: str,
        value: str,
        memory_type: str = "preference",
    ) -> None:
        """Save or update a memory entry (upsert by key)."""
        existing = await self.db.execute(
            select(ConversationMemory).where(
                ConversationMemory.tenant_id == tenant_id,
                ConversationMemory.user_id == user_id,
                ConversationMemory.key == key,
            )
        )
        mem = existing.scalar_one_or_none()
        if mem:
            mem.value = value
            mem.updated_at = datetime.now(UTC).replace(tzinfo=None)
        else:
            mem = ConversationMemory(
                tenant_id=tenant_id,
                user_id=user_id,
                key=key,
                value=value,
                memory_type=memory_type,
            )
            self.db.add(mem)
        await self.db.flush()

    async def get_memories(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        limit: int = 20,
    ) -> list[dict]:
        """Get all memories for a user, most recent first."""
        result = await self.db.execute(
            select(ConversationMemory)
            .where(
                ConversationMemory.tenant_id == tenant_id,
                ConversationMemory.user_id == user_id,
            )
            .order_by(ConversationMemory.updated_at.desc())
            .limit(limit)
        )
        return [
            {"key": m.key, "value": m.value, "type": m.memory_type}
            for m in result.scalars().all()
        ]

    async def clear_memories(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """Clear all memories for a user."""
        await self.db.execute(
            delete(ConversationMemory).where(
                ConversationMemory.tenant_id == tenant_id,
                ConversationMemory.user_id == user_id,
            )
        )
        await self.db.flush()

    async def detect_and_save(
        self,
        user_message: str,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """Auto-detect preferences from user messages and save them."""
        msg = user_message.lower()
        if "mostra sempre" in msg or "preferisco" in msg or "ricorda che" in msg:
            key = f"user_pref_{hash(msg) % 10000}"
            await self.save_memory(
                tenant_id, user_id, key, user_message, "preference"
            )

    async def get_memory_context(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> str:
        """Return a text summary of user memories for injection into the orchestrator context."""
        memories = await self.get_memories(tenant_id, user_id, limit=10)
        if not memories:
            return ""
        lines = ["Preferenze utente memorizzate:"]
        for m in memories:
            lines.append(f"- [{m['type']}] {m['key']}: {m['value']}")
        return "\n".join(lines)
