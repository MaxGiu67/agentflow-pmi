"""WebSocket handler for chat streaming (US-A05)."""

import json
import logging
import uuid

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.db.session import async_session_factory
from api.modules.auth.service import AuthService
from api.modules.chat.service import ChatService

logger = logging.getLogger(__name__)


async def _authenticate_ws(token: str, db: AsyncSession) -> User | None:
    """Authenticate a WebSocket connection from query param token."""
    try:
        service = AuthService(db)
        payload = service.decode_access_token(token)
        user_id = uuid.UUID(payload["sub"])
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
    except (ValueError, KeyError) as exc:
        logger.warning("WS auth failed: %s", exc)
        return None


async def chat_websocket(websocket: WebSocket) -> None:
    """Handle a WebSocket chat connection.

    Protocol:
    - Client connects with ?token=JWT
    - Client sends JSON: {"message": "...", "conversation_id": "..." (optional)}
    - Server sends JSON: {"type": "typing"} then {"type": "message", "data": {...}}
    - On error: {"type": "error", "detail": "..."}
    """
    await websocket.accept()

    # Authenticate from query param
    token = websocket.query_params.get("token")
    if not token:
        await websocket.send_json({"type": "error", "detail": "Token mancante"})
        await websocket.close(code=4001)
        return

    async with async_session_factory() as db:
        user = await _authenticate_ws(token, db)
        if not user:
            await websocket.send_json({"type": "error", "detail": "Autenticazione fallita"})
            await websocket.close(code=4001)
            return

        chat_service = ChatService(db)

        try:
            while True:
                # Receive message from client
                raw = await websocket.receive_text()
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    await websocket.send_json({"type": "error", "detail": "JSON non valido"})
                    continue

                message = data.get("message", "").strip()
                if not message:
                    await websocket.send_json({"type": "error", "detail": "Messaggio vuoto"})
                    continue

                conversation_id = data.get("conversation_id")
                if conversation_id:
                    try:
                        conversation_id = uuid.UUID(conversation_id)
                    except ValueError:
                        await websocket.send_json({"type": "error", "detail": "conversation_id non valido"})
                        continue

                # Send typing indicator
                await websocket.send_json({"type": "typing"})

                # Process message through orchestrator
                try:
                    result = await chat_service.send_message(
                        user=user,
                        conversation_id=conversation_id,
                        message=message,
                    )
                    await db.commit()

                    await websocket.send_json({
                        "type": "message",
                        "data": {
                            "conversation_id": str(result["conversation_id"]),
                            "message_id": str(result["message_id"]),
                            "role": result["role"],
                            "content": result["content"],
                            "agent_name": result.get("agent_name"),
                            "agent_type": result.get("agent_type"),
                            "tool_calls": result.get("tool_calls"),
                            "suggestions": result.get("suggestions", []),
                        },
                    })
                except ValueError as e:
                    await websocket.send_json({"type": "error", "detail": str(e)})
                except Exception as exc:
                    logger.error("WS chat error: %s", exc)
                    await websocket.send_json({
                        "type": "error",
                        "detail": "Errore interno. Riprova.",
                    })

        except WebSocketDisconnect:
            logger.info("WS client disconnected: user=%s", user.id)
        except Exception as exc:
            logger.error("WS unexpected error: %s", exc)
            try:
                await websocket.close(code=1011)
            except Exception:
                pass
