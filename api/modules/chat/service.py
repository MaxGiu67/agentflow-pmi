"""Service layer for chat module (US-A01, US-A02)."""

import logging
import uuid

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import Conversation, Message, User
from api.orchestrator.graph import run_orchestrator

logger = logging.getLogger(__name__)


class ChatService:
    """Business logic for chat operations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def send_message(
        self,
        user: User,
        conversation_id: uuid.UUID | None,
        message: str,
        context: dict | None = None,
    ) -> dict:
        """Send a message and get an AI response.

        Creates a new conversation if conversation_id is None.
        Saves user message, runs orchestrator, saves assistant response.
        """
        tenant_id = user.tenant_id
        if not tenant_id:
            raise ValueError("Profilo azienda non configurato")

        # Get or create conversation
        if conversation_id:
            conversation = await self._get_conversation(conversation_id, user.id)
            if not conversation:
                raise ValueError("Conversazione non trovata")
        else:
            conversation = await self._create_conversation(tenant_id, user.id)

        # Save user message
        user_msg = Message(
            conversation_id=conversation.id,
            role="user",
            content=message,
        )
        self.db.add(user_msg)
        await self.db.flush()

        # Load conversation history for context
        history = await self._get_conversation_history(conversation.id)

        # Run orchestrator
        try:
            result = await run_orchestrator(
                user_message=message,
                tenant_id=tenant_id,
                user_id=user.id,
                db=self.db,
                conversation_messages=history,
                context=context,
            )
        except Exception as e:
            logger.error("Orchestrator error: %s", e)
            result = {
                "content": "Mi dispiace, si è verificato un errore. Riprova tra poco.",
                "tool_calls": None,
                "tool_results": None,
                "agent_name": "orchestrator",
                "agent_type": "orchestrator",
            }

        # Save assistant message
        assistant_msg = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=result["content"],
            agent_name=result.get("agent_name"),
            agent_type=result.get("agent_type"),
            tool_calls=result.get("tool_calls"),
            tool_results=result.get("tool_results"),
        )
        self.db.add(assistant_msg)
        await self.db.flush()

        # Update conversation title from first user message
        if not conversation.title:
            conversation.title = message[:100]

        # Generate suggestions
        suggestions = self._generate_suggestions(result.get("tool_calls", []))

        return {
            "conversation_id": conversation.id,
            "message_id": assistant_msg.id,
            "role": "assistant",
            "content": result["content"],
            "agent_name": result.get("agent_name"),
            "agent_type": result.get("agent_type"),
            "tool_calls": result.get("tool_calls"),
            "suggestions": suggestions,
            "response_meta": result.get("response_meta"),
        }

    async def list_conversations(self, user: User) -> dict:
        """List user's conversations."""
        result = await self.db.execute(
            select(Conversation)
            .where(
                and_(
                    Conversation.user_id == user.id,
                    Conversation.status != "deleted",
                )
            )
            .order_by(Conversation.updated_at.desc())
        )
        conversations = result.scalars().all()

        items = []
        for conv in conversations:
            # Get message count
            count_result = await self.db.execute(
                select(func.count(Message.id)).where(
                    Message.conversation_id == conv.id
                )
            )
            message_count = count_result.scalar() or 0

            # Get last message preview
            last_msg_result = await self.db.execute(
                select(Message.content)
                .where(Message.conversation_id == conv.id)
                .order_by(Message.created_at.desc())
                .limit(1)
            )
            last_msg = last_msg_result.scalar_one_or_none()
            preview = (last_msg[:100] + "...") if last_msg and len(last_msg) > 100 else last_msg

            items.append({
                "id": conv.id,
                "title": conv.title,
                "status": conv.status,
                "message_count": message_count,
                "last_message_preview": preview,
                "created_at": conv.created_at,
                "updated_at": conv.updated_at,
            })

        return {"items": items, "total": len(items)}

    async def get_conversation(
        self, user: User, conversation_id: uuid.UUID
    ) -> dict:
        """Get conversation with all messages."""
        conversation = await self._get_conversation(conversation_id, user.id)
        if not conversation:
            raise ValueError("Conversazione non trovata")

        msg_result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .order_by(Message.created_at)
        )
        messages = msg_result.scalars().all()

        return {
            "id": conversation.id,
            "title": conversation.title,
            "status": conversation.status,
            "messages": [
                {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "agent_name": m.agent_name,
                    "agent_type": m.agent_type,
                    "tool_calls": m.tool_calls,
                    "created_at": m.created_at,
                }
                for m in messages
            ],
            "created_at": conversation.created_at,
            "updated_at": conversation.updated_at,
        }

    async def delete_conversation(
        self, user: User, conversation_id: uuid.UUID
    ) -> dict:
        """Soft delete a conversation."""
        conversation = await self._get_conversation(conversation_id, user.id)
        if not conversation:
            raise ValueError("Conversazione non trovata")

        conversation.status = "deleted"
        await self.db.flush()

        return {"id": conversation.id, "status": "deleted"}

    async def create_conversation(self, user: User) -> dict:
        """Create a new empty conversation."""
        tenant_id = user.tenant_id
        if not tenant_id:
            raise ValueError("Profilo azienda non configurato")

        conversation = await self._create_conversation(tenant_id, user.id)
        return {
            "id": conversation.id,
            "title": conversation.title,
            "status": conversation.status,
            "messages": [],
            "created_at": conversation.created_at,
            "updated_at": conversation.updated_at,
        }

    # ============================================================
    # Private helpers
    # ============================================================

    async def _get_conversation(
        self, conversation_id: uuid.UUID, user_id: uuid.UUID
    ) -> Conversation | None:
        """Fetch a conversation by ID and user, excluding deleted."""
        result = await self.db.execute(
            select(Conversation).where(
                and_(
                    Conversation.id == conversation_id,
                    Conversation.user_id == user_id,
                    Conversation.status != "deleted",
                )
            )
        )
        return result.scalar_one_or_none()

    async def _create_conversation(
        self, tenant_id: uuid.UUID, user_id: uuid.UUID
    ) -> Conversation:
        """Create a new conversation."""
        conversation = Conversation(
            tenant_id=tenant_id,
            user_id=user_id,
            status="active",
        )
        self.db.add(conversation)
        await self.db.flush()
        return conversation

    async def _get_conversation_history(
        self, conversation_id: uuid.UUID, limit: int = 20
    ) -> list[dict]:
        """Get recent messages for context, formatted for the orchestrator."""
        result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        messages = list(reversed(result.scalars().all()))

        # Exclude the latest user message (it will be added by orchestrator)
        # Return only prior messages
        if messages and messages[-1].role == "user":
            messages = messages[:-1]

        return [
            {"role": m.role, "content": m.content or ""}
            for m in messages
        ]

    def _generate_suggestions(self, tool_calls: list | None) -> list[str]:
        """Generate follow-up suggestions based on tool calls.

        US-A10: Always include a base set of suggestions so users can discover
        available capabilities.
        """
        # Default suggestions (US-A10)
        default_suggestions = [
            "Come stanno le mie finanze?",
            "Fatture da verificare",
            "Prossime scadenze",
            "Aiuto",
        ]

        suggestions: list[str] = []
        if not tool_calls:
            return default_suggestions

        for call in tool_calls:
            tool_name = call.get("tool", "")
            if tool_name == "count_invoices":
                suggestions.extend([
                    "Mostra l'elenco delle fatture",
                    "Qual e la situazione della dashboard?",
                ])
            elif tool_name == "get_dashboard_summary":
                suggestions.extend([
                    "Ci sono scadenze in arrivo?",
                    "Mostra i KPI del CEO",
                ])
            elif tool_name == "get_deadlines":
                suggestions.extend([
                    "Ci sono scadenze in ritardo?",
                    "Mostra la dashboard",
                ])
            elif tool_name in ("crm_pipeline_summary", "crm_list_deals"):
                suggestions.extend([
                    "Quali deal sono fermi da troppo?",
                    "Deal vinti questo mese",
                    "Ordini in attesa di conferma",
                    "Mostra i contatti CRM",
                ])
            elif tool_name == "crm_won_deals":
                suggestions.extend([
                    "Com'e la pipeline?",
                    "Ordini in attesa",
                ])
            elif tool_name == "crm_pending_orders":
                suggestions.extend([
                    "Com'e la pipeline?",
                    "Deal vinti",
                ])
            elif tool_name == "direct_response":
                suggestions.extend(default_suggestions)

        # If no specific suggestions were generated, use defaults
        if not suggestions:
            suggestions = list(default_suggestions)

        # Deduplicate and limit
        seen: set[str] = set()
        unique: list[str] = []
        for s in suggestions:
            if s not in seen:
                seen.add(s)
                unique.append(s)
        return unique[:4]
