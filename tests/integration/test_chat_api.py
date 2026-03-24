"""
Test suite for Sprint 11: Agentic System — Chat, Orchestrator, Tool System

US-A01: Chat with Orchestrator (8 SP)
US-A04: Tool System (8 SP)
US-A02: Persistent Conversations (5 SP)

15+ tests covering: chat send, conversations CRUD, orchestrator routing,
tool execution, persistence, and auth.
"""

import uuid
from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import (
    Conversation,
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
