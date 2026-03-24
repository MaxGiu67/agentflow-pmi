"""Schemas for chat module (US-A01, US-A02)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ChatSendRequest(BaseModel):
    """Request to send a message in a conversation."""
    conversation_id: UUID | None = None
    message: str = Field(..., min_length=1, max_length=5000)


class ChatSendResponse(BaseModel):
    """Response after sending a message."""
    conversation_id: UUID
    message_id: UUID
    role: str
    content: str
    agent_name: str | None = None
    agent_type: str | None = None
    tool_calls: list | None = None
    suggestions: list[str] = []


class MessageResponse(BaseModel):
    """A single message in a conversation."""
    id: UUID
    role: str
    content: str | None = None
    agent_name: str | None = None
    agent_type: str | None = None
    tool_calls: list | None = None
    created_at: datetime


class ConversationResponse(BaseModel):
    """Summary of a conversation for listing."""
    id: UUID
    title: str | None = None
    status: str
    message_count: int
    last_message_preview: str | None = None
    created_at: datetime
    updated_at: datetime


class ConversationListResponse(BaseModel):
    """List of conversations."""
    items: list[ConversationResponse]
    total: int


class ConversationDetailResponse(BaseModel):
    """Conversation with all messages."""
    id: UUID
    title: str | None = None
    status: str
    messages: list[MessageResponse]
    created_at: datetime
    updated_at: datetime
