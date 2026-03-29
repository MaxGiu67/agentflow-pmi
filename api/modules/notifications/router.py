"""Router for notifications (US-18)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from api.modules.notifications.schemas import (
    NotificationConfigCreate,
    NotificationConfigResponse,
    NotificationConfigListResponse,
    NotificationTestRequest,
    NotificationTestResponse,
)
from api.modules.notifications.service import NotificationService
from api.modules.notifications.push_service import PushNotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


def get_notification_service(db: AsyncSession = Depends(get_db)) -> NotificationService:
    return NotificationService(db)


@router.post("/config", response_model=NotificationConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_notification_config(
    request: NotificationConfigCreate,
    user: User = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
) -> NotificationConfigResponse:
    """Create or update a notification channel configuration."""
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    try:
        result = await service.create_or_update_config(
            user_id=user.id,
            tenant_id=user.tenant_id,
            channel=request.channel,
            chat_id=request.chat_id,
            phone=request.phone,
            enabled=request.enabled,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return NotificationConfigResponse(**result)


@router.get("/config", response_model=NotificationConfigListResponse)
async def get_notification_configs(
    user: User = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
) -> NotificationConfigListResponse:
    """Get all notification configurations for the current user."""
    configs = await service.get_configs(user.id)
    return NotificationConfigListResponse(
        configs=[NotificationConfigResponse(**c) for c in configs],
        count=len(configs),
    )


@router.post("/test", response_model=list[NotificationTestResponse])
async def send_test_notification(
    request: NotificationTestRequest,
    user: User = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
) -> list[NotificationTestResponse]:
    """Send a test notification to verify channel configuration."""
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    results = await service.send_test_notification(
        user_id=user.id,
        tenant_id=user.tenant_id,
        channel=request.channel,
    )

    return [
        NotificationTestResponse(
            channel=r["channel"],
            success=r["success"],
            message=r.get("error") or "Notifica di test inviata con successo",
        )
        for r in results
    ]


# ── US-67: Push notifications ──

from pydantic import BaseModel as _BaseModel


class PushNotificationRequest(_BaseModel):
    message: str
    message_type: str = "push"
    channel: str = "telegram"


def get_push_service(db: AsyncSession = Depends(get_db)) -> PushNotificationService:
    return PushNotificationService(db)


@router.post("/push")
async def send_push_notification(
    request: PushNotificationRequest,
    user: User = Depends(get_current_user),
    service: PushNotificationService = Depends(get_push_service),
) -> dict:
    """Send push notification to configured channel (US-67)."""
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    return await service.send_push(
        user_id=user.id,
        tenant_id=user.tenant_id,
        message=request.message,
        message_type=request.message_type,
        channel=request.channel,
    )
