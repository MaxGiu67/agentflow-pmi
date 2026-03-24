"""Router for chat module (US-A01, US-A02, US-A05)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, WebSocket, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from api.modules.chat.schemas import (
    ChatSendRequest,
    ChatSendResponse,
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationResponse,
)
from api.modules.chat.service import ChatService
from api.modules.chat.websocket import chat_websocket

router = APIRouter(prefix="/chat", tags=["chat"])


def get_service(db: AsyncSession = Depends(get_db)) -> ChatService:
    return ChatService(db)


@router.websocket("/ws")
async def ws_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time chat (US-A05)."""
    await chat_websocket(websocket)


@router.post("/send", response_model=ChatSendResponse)
async def send_message(
    request: ChatSendRequest,
    user: User = Depends(get_current_user),
    service: ChatService = Depends(get_service),
) -> ChatSendResponse:
    """Send a message and get an AI response.

    US-A01: Chat with orchestrator.
    Creates a new conversation if conversation_id is not provided.
    """
    try:
        result = await service.send_message(
            user=user,
            conversation_id=request.conversation_id,
            message=request.message,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return ChatSendResponse(**result)


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    user: User = Depends(get_current_user),
    service: ChatService = Depends(get_service),
) -> ConversationListResponse:
    """List user's conversations.

    US-A02: Persistent conversations.
    """
    result = await service.list_conversations(user)
    return ConversationListResponse(**result)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: UUID,
    user: User = Depends(get_current_user),
    service: ChatService = Depends(get_service),
) -> ConversationDetailResponse:
    """Get conversation detail with all messages.

    US-A02: Persistent conversations.
    """
    try:
        result = await service.get_conversation(user, conversation_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return ConversationDetailResponse(**result)


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: UUID,
    user: User = Depends(get_current_user),
    service: ChatService = Depends(get_service),
) -> dict:
    """Soft delete a conversation.

    US-A02: Persistent conversations.
    """
    try:
        result = await service.delete_conversation(user, conversation_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return result


@router.post("/conversations/new", response_model=ConversationDetailResponse)
async def new_conversation(
    user: User = Depends(get_current_user),
    service: ChatService = Depends(get_service),
) -> ConversationDetailResponse:
    """Create a new empty conversation.

    US-A02: Persistent conversations.
    """
    try:
        result = await service.create_conversation(user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return ConversationDetailResponse(**result)
