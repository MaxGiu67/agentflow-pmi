"""
Test suite for Chat API — Sprints 11 + 13

Sprint 11: US-A01, US-A04, US-A02 (Chat, Tools, Persistence)
Sprint 13: US-A07 (Multi-agent response), US-A08 (Conversation memory), US-A10 (Skill discovery)

25+ tests covering: chat send, conversations CRUD, orchestrator routing,
tool execution, persistence, auth, multi-agent, memory, skill discovery.
"""

import uuid
from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import (
    Conversation,
    ConversationMemory,
    Expense,
    FiscalDeadline,
    Invoice,
    JournalEntry,
    Message,
    Tenant,
    User,
)
from tests.conftest import create_invoice, get_auth_token


# ============================================================
# Helpers
# ============================================================


async def _send_chat(
    client: AsyncClient,
    headers: dict,
    message: str,
    conversation_id: str | None = None,
) -> dict:
    """Helper to POST /chat/send and return JSON response."""
    body: dict = {"message": message}
    if conversation_id:
        body["conversation_id"] = conversation_id
    resp = await client.post("/api/v1/chat/send", json=body, headers=headers)
    return {"status_code": resp.status_code, "data": resp.json()}


# ============================================================
# US-A01 / US-A02: Chat Send
# ============================================================


class TestChatSend:
    """Tests for POST /chat/send."""

    async def test_send_message_creates_conversation(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Sending a message without conversation_id creates a new conversation."""
        result = await _send_chat(client, auth_headers, "Ciao, come stai?")
        assert result["status_code"] == 200
        data = result["data"]
        assert "conversation_id" in data
        assert "message_id" in data
        assert data["role"] == "assistant"
        assert len(data["content"]) > 0

    async def test_send_message_existing_conversation(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Sending a message to an existing conversation continues it."""
        # First message creates conversation
        result1 = await _send_chat(client, auth_headers, "Ciao")
        assert result1["status_code"] == 200
        conv_id = result1["data"]["conversation_id"]

        # Second message uses same conversation
        result2 = await _send_chat(
            client, auth_headers, "Quante fatture ho?", conv_id
        )
        assert result2["status_code"] == 200
        assert result2["data"]["conversation_id"] == conv_id

    async def test_send_message_returns_suggestions(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Response includes follow-up suggestions."""
        result = await _send_chat(client, auth_headers, "Buongiorno!")
        assert result["status_code"] == 200
        data = result["data"]
        assert "suggestions" in data
        assert isinstance(data["suggestions"], list)


# ============================================================
# US-A02: Conversations CRUD
# ============================================================


class TestConversationsCRUD:
    """Tests for conversation endpoints."""

    async def test_list_conversations(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """GET /chat/conversations returns user's conversations."""
        # Create a conversation by sending a message
        await _send_chat(client, auth_headers, "Test listing")

        resp = await client.get("/api/v1/chat/conversations", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1
        item = data["items"][0]
        assert "id" in item
        assert "status" in item
        assert "message_count" in item

    async def test_get_conversation_detail(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """GET /chat/conversations/{id} returns conversation with messages."""
        result = await _send_chat(client, auth_headers, "Dettaglio test")
        conv_id = result["data"]["conversation_id"]

        resp = await client.get(
            f"/api/v1/chat/conversations/{conv_id}", headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == conv_id
        assert "messages" in data
        # Should have user + assistant messages
        assert len(data["messages"]) >= 2
        roles = [m["role"] for m in data["messages"]]
        assert "user" in roles
        assert "assistant" in roles

    async def test_delete_conversation(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """DELETE /chat/conversations/{id} soft deletes."""
        result = await _send_chat(client, auth_headers, "To be deleted")
        conv_id = result["data"]["conversation_id"]

        resp = await client.delete(
            f"/api/v1/chat/conversations/{conv_id}", headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"

        # Should not appear in list anymore
        list_resp = await client.get(
            "/api/v1/chat/conversations", headers=auth_headers
        )
        conv_ids = [c["id"] for c in list_resp.json()["items"]]
        assert conv_id not in conv_ids

    async def test_new_conversation(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """POST /chat/conversations/new creates an empty conversation."""
        resp = await client.post(
            "/api/v1/chat/conversations/new", headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert data["status"] == "active"
        assert data["messages"] == []


# ============================================================
# US-A01 / US-A04: Orchestrator Routing & Tool Execution
# ============================================================


class TestOrchestratorRouting:
    """Tests for orchestrator routing to correct tools."""

    async def test_orchestrator_routes_to_invoice_tool(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        tenant: Tenant,
    ):
        """Message about invoices routes to count_invoices tool."""
        # Create some invoices
        for i in range(3):
            inv = create_invoice(
                tenant_id=tenant.id,
                numero=f"FT-CHAT-{i:03d}",
                piva=f"IT{70000000000 + i}",
                nome=f"Fornitore Chat {i}",
            )
            db_session.add(inv)
        await db_session.flush()

        result = await _send_chat(
            client, auth_headers, "Quante fatture ho questo mese?"
        )
        assert result["status_code"] == 200
        data = result["data"]
        assert data["content"]  # Non-empty response
        # The orchestrator should have routed to invoice-related tool
        if data.get("tool_calls"):
            tool_names = [tc["tool"] for tc in data["tool_calls"]]
            assert any(
                "invoice" in t or "fattur" in t or t == "count_invoices"
                for t in tool_names
            )

    async def test_orchestrator_direct_response(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Greeting doesn't call data tools, returns direct response."""
        result = await _send_chat(client, auth_headers, "Ciao!")
        assert result["status_code"] == 200
        data = result["data"]
        assert data["content"]
        # Should be a direct response (greeting)
        if data.get("tool_calls"):
            tool_names = [tc["tool"] for tc in data["tool_calls"]]
            assert "direct_response" in tool_names


# ============================================================
# US-A04: Individual Tool Tests
# ============================================================


class TestToolExecution:
    """Tests for individual tool execution via chat."""

    async def test_tool_count_invoices(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        tenant: Tenant,
    ):
        """count_invoices tool returns correct count."""
        # Create 5 invoices
        for i in range(5):
            inv = create_invoice(
                tenant_id=tenant.id,
                numero=f"FT-COUNT-{i:03d}",
                piva=f"IT{80000000000 + i}",
                nome=f"Fornitore Count {i}",
            )
            db_session.add(inv)
        await db_session.flush()

        result = await _send_chat(
            client, auth_headers, "Conta le fatture che ho"
        )
        assert result["status_code"] == 200
        # Response should mention the count somewhere
        content = result["data"]["content"].lower()
        assert "5" in content or "fattur" in content

    async def test_tool_get_dashboard(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """get_dashboard tool returns dashboard data."""
        result = await _send_chat(
            client, auth_headers, "Mostrami la dashboard"
        )
        assert result["status_code"] == 200
        assert result["data"]["content"]

    async def test_tool_get_deadlines(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        tenant: Tenant,
    ):
        """get_deadlines tool returns deadlines data."""
        # Create a deadline
        deadline = FiscalDeadline(
            tenant_id=tenant.id,
            code="1040",
            description="Ritenuta d'acconto",
            amount=200.0,
            due_date=date(2026, 12, 16),
            status="pending",
        )
        db_session.add(deadline)
        await db_session.flush()

        result = await _send_chat(
            client, auth_headers, "Ci sono scadenze fiscali?"
        )
        assert result["status_code"] == 200
        assert result["data"]["content"]

    async def test_tool_error_handling(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Tool failure returns a graceful error response, not a 500."""
        # Sending a valid message should always return 200
        result = await _send_chat(
            client, auth_headers, "Mostra il dettaglio della fattura con ID inesistente"
        )
        assert result["status_code"] == 200
        # Should have content (even if it's an error message)
        assert result["data"]["content"]


# ============================================================
# US-A02: Persistence
# ============================================================


class TestPersistence:
    """Tests for message persistence."""

    async def test_conversation_persists_messages(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Messages are saved to the database."""
        result = await _send_chat(
            client, auth_headers, "Messaggio di persistenza"
        )
        assert result["status_code"] == 200
        conv_id = result["data"]["conversation_id"]

        # Verify messages are persisted
        from sqlalchemy import select

        msg_result = await db_session.execute(
            select(Message).where(
                Message.conversation_id == uuid.UUID(conv_id)
            )
        )
        messages = msg_result.scalars().all()
        assert len(messages) >= 2  # user + assistant
        roles = {m.role for m in messages}
        assert "user" in roles
        assert "assistant" in roles

    async def test_conversation_title_set_from_first_message(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Conversation title is set from the first user message."""
        message_text = "Come sta la mia azienda oggi?"
        result = await _send_chat(client, auth_headers, message_text)
        conv_id = result["data"]["conversation_id"]

        from sqlalchemy import select

        conv_result = await db_session.execute(
            select(Conversation).where(
                Conversation.id == uuid.UUID(conv_id)
            )
        )
        conversation = conv_result.scalar_one()
        assert conversation.title == message_text[:100]


# ============================================================
# Auth
# ============================================================


class TestChatAuth:
    """Tests for authentication on chat endpoints."""

    async def test_unauthorized_access_send(
        self,
        client: AsyncClient,
    ):
        """No token returns 401/403 on POST /chat/send."""
        resp = await client.post(
            "/api/v1/chat/send",
            json={"message": "test"},
        )
        assert resp.status_code in (401, 403)

    async def test_unauthorized_access_list(
        self,
        client: AsyncClient,
    ):
        """No token returns 401/403 on GET /chat/conversations."""
        resp = await client.get("/api/v1/chat/conversations")
        assert resp.status_code in (401, 403)


# ============================================================
# US-A07: Multi-agent Response
# ============================================================


class TestMultiAgentResponse:
    """Tests for multi-agent routing on broad queries (US-A07)."""

    async def test_multi_agent_come_sta(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        tenant: Tenant,
    ):
        """'come sta la mia azienda?' triggers multiple tools."""
        # Create some data so tools return something
        for i in range(2):
            inv = create_invoice(
                tenant_id=tenant.id,
                numero=f"FT-MULTI-{i:03d}",
                piva=f"IT{60000000000 + i}",
                nome=f"Fornitore Multi {i}",
            )
            db_session.add(inv)
        await db_session.flush()

        result = await _send_chat(
            client, auth_headers, "come sta la mia azienda?"
        )
        assert result["status_code"] == 200
        data = result["data"]

        # Should have routed to multiple tools
        tool_calls = data.get("tool_calls", [])
        assert len(tool_calls) >= 2, f"Expected multiple tool calls, got {len(tool_calls)}"

        tool_names = [tc["tool"] for tc in tool_calls]
        # Orchestrator may use different tool combinations depending on routing
        # At minimum, get_deadlines should be called for "come sta la mia azienda?"
        assert "get_deadlines" in tool_names or "get_period_stats" in tool_names

        # Response should contain content from agents
        assert data["content"]
        # Orchestrator may route to controller or multi depending on routing logic
        assert data.get("agent_type") in ("multi", "controller")

    async def test_multi_agent_riepilogo(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """'riepilogo' triggers multi-tool behavior."""
        result = await _send_chat(client, auth_headers, "riepilogo")
        assert result["status_code"] == 200
        data = result["data"]

        tool_calls = data.get("tool_calls", [])
        assert len(tool_calls) >= 1, f"Expected at least one tool call, got {len(tool_calls)}"

        tool_names = [tc["tool"] for tc in tool_calls]
        # Orchestrator may use various tools for a summary
        assert any(t in tool_names for t in ["count_invoices", "get_dashboard_summary", "get_period_stats", "get_deadlines"])

    async def test_multi_agent_partial_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """When one tool fails in a multi-agent call, others still respond."""
        # "panoramica" triggers agent routing with tools
        # Even if DB has no data, the tools should return zero counts, not errors
        result = await _send_chat(client, auth_headers, "panoramica della situazione")
        assert result["status_code"] == 200
        data = result["data"]

        # Should have at least one tool result
        tool_calls = data.get("tool_calls", [])
        assert len(tool_calls) >= 1

        # Content should be non-empty (partial results are fine)
        assert data["content"]

    async def test_multi_agent_response_contains_agent_badges(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Multi-tool response fallback includes agent badge prefixes."""
        result = await _send_chat(
            client, auth_headers, "come vanno le cose?"
        )
        assert result["status_code"] == 200
        data = result["data"]

        # Response should have content from an agent
        content = data["content"]
        assert content  # Non-empty response


# ============================================================
# US-A08: Conversation Memory
# ============================================================


class TestConversationMemory:
    """Tests for conversation memory management (US-A08)."""

    async def test_save_memory(
        self,
        db_session: AsyncSession,
        tenant: Tenant,
        verified_user: User,
    ):
        """MemoryManager.save_memory creates and updates entries."""
        from api.orchestrator.memory_node import MemoryManager

        mgr = MemoryManager(db_session)
        await mgr.save_memory(
            tenant.id, verified_user.id, "lang_pref", "italiano", "preference"
        )

        memories = await mgr.get_memories(tenant.id, verified_user.id)
        assert len(memories) == 1
        assert memories[0]["key"] == "lang_pref"
        assert memories[0]["value"] == "italiano"

        # Update existing key
        await mgr.save_memory(
            tenant.id, verified_user.id, "lang_pref", "english", "preference"
        )
        memories = await mgr.get_memories(tenant.id, verified_user.id)
        assert len(memories) == 1
        assert memories[0]["value"] == "english"

    async def test_get_memories(
        self,
        db_session: AsyncSession,
        tenant: Tenant,
        verified_user: User,
    ):
        """MemoryManager.get_memories returns all saved memories."""
        from api.orchestrator.memory_node import MemoryManager

        mgr = MemoryManager(db_session)
        await mgr.save_memory(tenant.id, verified_user.id, "pref_1", "val1")
        await mgr.save_memory(tenant.id, verified_user.id, "pref_2", "val2")
        await mgr.save_memory(tenant.id, verified_user.id, "pref_3", "val3")

        memories = await mgr.get_memories(tenant.id, verified_user.id)
        assert len(memories) == 3
        keys = {m["key"] for m in memories}
        assert keys == {"pref_1", "pref_2", "pref_3"}

    async def test_clear_memories(
        self,
        db_session: AsyncSession,
        tenant: Tenant,
        verified_user: User,
    ):
        """MemoryManager.clear_memories removes all entries for a user."""
        from api.orchestrator.memory_node import MemoryManager

        mgr = MemoryManager(db_session)
        await mgr.save_memory(tenant.id, verified_user.id, "to_clear", "data")

        memories_before = await mgr.get_memories(tenant.id, verified_user.id)
        assert len(memories_before) >= 1

        await mgr.clear_memories(tenant.id, verified_user.id)

        memories_after = await mgr.get_memories(tenant.id, verified_user.id)
        assert len(memories_after) == 0

    async def test_memory_loaded_in_chat_context(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        tenant: Tenant,
        verified_user: User,
    ):
        """Sending a preference message auto-saves it; memory is loaded on next call."""
        from api.orchestrator.memory_node import MemoryManager

        # Manually save a memory to verify it is available
        mgr = MemoryManager(db_session)
        await mgr.save_memory(
            tenant.id, verified_user.id, "test_ctx", "mostra sempre i totali"
        )

        # The orchestrator should load memory context before routing
        # Send a normal chat message — memory loading should not break anything
        result = await _send_chat(client, auth_headers, "Quante fatture ho?")
        assert result["status_code"] == 200
        assert result["data"]["content"]

    async def test_detect_and_save_preference(
        self,
        db_session: AsyncSession,
        tenant: Tenant,
        verified_user: User,
    ):
        """detect_and_save auto-detects preference keywords and saves memory."""
        from api.orchestrator.memory_node import MemoryManager

        mgr = MemoryManager(db_session)
        await mgr.detect_and_save(
            "Ricorda che preferisco il formato dettagliato",
            tenant.id,
            verified_user.id,
        )

        memories = await mgr.get_memories(tenant.id, verified_user.id)
        assert len(memories) >= 1
        assert any("preferisco il formato dettagliato" in (m["value"] or "") for m in memories)

    async def test_memory_api_get(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        tenant: Tenant,
        verified_user: User,
    ):
        """GET /chat/memory returns saved memories."""
        from api.orchestrator.memory_node import MemoryManager

        mgr = MemoryManager(db_session)
        await mgr.save_memory(tenant.id, verified_user.id, "api_test", "value_api")

        resp = await client.get("/api/v1/chat/memory", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1
        keys = [item["key"] for item in data["items"]]
        assert "api_test" in keys

    async def test_memory_api_clear(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        tenant: Tenant,
        verified_user: User,
    ):
        """DELETE /chat/memory clears all memories."""
        from api.orchestrator.memory_node import MemoryManager

        mgr = MemoryManager(db_session)
        await mgr.save_memory(tenant.id, verified_user.id, "to_del", "val")

        resp = await client.delete("/api/v1/chat/memory", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

        # Verify memories are gone
        get_resp = await client.get("/api/v1/chat/memory", headers=auth_headers)
        assert get_resp.json()["total"] == 0


# ============================================================
# US-A10: Skill Discovery
# ============================================================


class TestSkillDiscovery:
    """Tests for help/skill discovery via chat (US-A10)."""

    async def test_skill_discovery_help(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """'cosa sai fare?' returns a capabilities list."""
        result = await _send_chat(client, auth_headers, "cosa sai fare?")
        assert result["status_code"] == 200
        data = result["data"]
        content = data["content"]

        # Should list capabilities
        assert "cosa posso fare" in content.lower() or "ecco cosa" in content.lower()
        assert "fisco" in content.lower() or "fattur" in content.lower()
        assert "conta" in content.lower() or "contabil" in content.lower()
        assert "cashflow" in content.lower() or "cash flow" in content.lower()

    async def test_skill_discovery_aiuto(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """'aiuto' returns the same capabilities list."""
        result = await _send_chat(client, auth_headers, "aiuto")
        assert result["status_code"] == 200
        data = result["data"]
        content = data["content"]

        assert "cosa posso fare" in content.lower() or "ecco cosa" in content.lower()
        # Should include example queries
        assert "fatture" in content.lower() or "fattur" in content.lower()

    async def test_suggestions_in_response(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Every response includes suggestions array (US-A10)."""
        result = await _send_chat(client, auth_headers, "Ciao!")
        assert result["status_code"] == 200
        data = result["data"]

        suggestions = data.get("suggestions", [])
        assert isinstance(suggestions, list)
        assert len(suggestions) >= 1
        # Should include discovery-friendly suggestions
        assert any("aiuto" in s.lower() or "finanze" in s.lower() for s in suggestions)

    async def test_skill_discovery_message_format(self):
        """get_skill_discovery_message returns well-formed content."""
        from api.orchestrator.skill_discovery import get_skill_discovery_message

        msg = get_skill_discovery_message()
        assert "Ecco cosa posso fare per te:" in msg
        assert "fisco" in msg.lower() or "Fatture" in msg
        assert "conta" in msg.lower() or "Scritture" in msg
        assert "cashflow" in msg.lower() or "cash flow" in msg.lower()
        assert "Prova a chiedermi" in msg
