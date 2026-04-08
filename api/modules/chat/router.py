"""Router for chat module (US-A01, US-A02, US-A05, US-A08, Sprint 46-47 Sales Chat)."""

import logging
import uuid as uuid_mod
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, WebSocket, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from api.modules.chat.schemas import (
    ChatSendRequest,
    ChatSendResponse,
    ConversationDetailResponse,
    ConversationListResponse,
    MemoryListResponse,
)
from api.modules.chat.service import ChatService
from api.modules.chat.test_suite import run_chatbot_test_suite
from api.modules.chat.websocket import chat_websocket
from api.orchestrator.memory_node import MemoryManager

logger = logging.getLogger(__name__)

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
            context=request.context,
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


# ============================================================
# US-A08: Memory endpoints
# ============================================================


@router.get("/memory", response_model=MemoryListResponse)
async def get_memory(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MemoryListResponse:
    """Get user's conversation memories.

    US-A08: Conversation memory.
    """
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    mgr = MemoryManager(db)
    memories = await mgr.get_memories(user.tenant_id, user.id)
    return MemoryListResponse(items=memories, total=len(memories))


@router.delete("/memory")
async def clear_memory(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Clear all conversation memories for the current user.

    US-A08: Conversation memory.
    """
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    mgr = MemoryManager(db)
    await mgr.clear_memories(user.tenant_id, user.id)
    return {"message": "Memorie cancellate", "status": "ok"}


# ============================================================
# Test Suite endpoint
# ============================================================


@router.get("/test-suite")
async def chatbot_test_suite(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Run 40 chatbot prompts against real data and return quality report.

    Tests: KPI, top clients, invoice search, navigation, edge cases.
    Compares results with direct DB queries for validation.
    """
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    report = await run_chatbot_test_suite(
        db=db,
        tenant_id=user.tenant_id,
        user_id=user.id,
    )
    return report


# ============================================================
# Sprint 46-47: Sales Agent v2 Chat endpoint
# ============================================================


class SalesChatRequest(BaseModel):
    """Request body for the Sales Agent v2 chat endpoint."""
    message: str = Field(..., min_length=1, max_length=5000)
    deal_id: str | None = None
    history: list[dict] | None = None


class UIActionResponse(BaseModel):
    """A UI highlight action for the frontend."""
    type: str = "highlight"
    target: str = ""
    id: str = ""
    style: str = "pulse-border"
    color: str = "#8b5cf6"
    tooltip: str = ""


class SalesChatResponse(BaseModel):
    """Response from the Sales Agent v2 chat endpoint."""
    response: str
    deal_context: dict | None = None
    risk_level: str = "low"
    needs_confirmation: bool = False
    ui_actions: list[UIActionResponse] = []


@router.post("/sales", response_model=SalesChatResponse)
async def chat_sales(
    body: SalesChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SalesChatResponse:
    """Chat with Sales Agent v2 (Sprint 46-47).

    Accepts a natural language message and optional deal_id for context.
    The agent uses 25+ tools wired to real CRM and Portal services.
    """
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    from api.agents.sales_agent_v2 import invoke_sales_agent_v2
    from api.modules.crm.service import CRMService

    # Build deal context if deal_id is provided
    deal_context: dict | None = None
    pipeline_stages: list[dict] = []

    if body.deal_id:
        try:
            svc = CRMService(db)
            deal = await svc.get_deal(uuid_mod.UUID(body.deal_id), user.tenant_id)
            if deal:
                deal_context = {
                    "deal_id": body.deal_id,
                    "company": deal.get("client_name") or deal.get("portal_customer_name", ""),
                    "product": deal.get("deal_type", ""),
                    "current_stage": deal.get("stage", ""),
                    "pipeline_type": deal.get("deal_type", ""),
                    "days_in_stage": deal.get("days_in_stage", 0),
                    "last_contact": "",
                    "missing_fields": [],
                }
                # Get pipeline stages
                pipeline_stages = await svc.get_stages(user.tenant_id)
        except Exception as e:
            logger.warning("Failed to load deal context for %s: %s", body.deal_id, e)

    # Convert history dicts to LangChain messages if provided
    lc_history = None
    if body.history:
        from langchain_core.messages import AIMessage, HumanMessage
        lc_history = []
        for msg in body.history:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user":
                lc_history.append(HumanMessage(content=content))
            elif role == "assistant":
                lc_history.append(AIMessage(content=content))

    try:
        result = await invoke_sales_agent_v2(
            message=body.message,
            tenant_id=str(user.tenant_id),
            user_name=user.name or user.email,
            deal_context=deal_context,
            pipeline_stages=pipeline_stages,
            history=lc_history,
        )
    except Exception as e:
        logger.error("Sales Agent v2 error: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore nell'agente commerciale: {e}",
        ) from e

    # Extract risk/confirmation info from state
    state = result.get("state", {})
    risk_level = "low"
    needs_confirmation = False
    if isinstance(state, dict):
        risk_level = state.get("risk_level", "low")
        needs_confirmation = state.get("needs_human_confirmation", False)

    # Sprint 46-47: Extract UI actions
    raw_ui_actions = result.get("ui_actions", [])
    ui_actions = [UIActionResponse(**a) for a in raw_ui_actions if isinstance(a, dict)]

    return SalesChatResponse(
        response=result.get("response", ""),
        deal_context=deal_context,
        risk_level=risk_level,
        needs_confirmation=needs_confirmation,
        ui_actions=ui_actions,
    )
