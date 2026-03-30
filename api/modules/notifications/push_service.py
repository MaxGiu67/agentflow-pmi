"""Push notification service — dual channel (US-67).

Sends push notifications to configured channels (Telegram, etc.).
"""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import NotificationConfig, NotificationLog

logger = logging.getLogger(__name__)


class PushNotificationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def send_push(
        self,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        message: str,
        message_type: str = "push",
        channel: str = "telegram",
    ) -> dict:
        """Send a push notification to configured channel (US-67)."""
        # Get notification config
        result = await self.db.execute(
            select(NotificationConfig).where(
                NotificationConfig.user_id == user_id,
                NotificationConfig.tenant_id == tenant_id,
                NotificationConfig.channel == channel,
                NotificationConfig.enabled,
            )
        )
        config = result.scalar_one_or_none()

        channels_sent = []

        if config and config.channel == "telegram" and config.chat_id:
            # Mock Telegram send (in production would use Telegram Bot API)
            success = True
            channels_sent.append({
                "channel": "telegram",
                "chat_id": config.chat_id,
                "success": success,
            })

            # Log the notification
            log = NotificationLog(
                user_id=user_id,
                tenant_id=tenant_id,
                channel="telegram",
                message_type=message_type,
                message_text=message,
                status="sent" if success else "failed",
            )
            self.db.add(log)

        # If no channel configured or all failed, fallback to email log
        if not channels_sent:
            log = NotificationLog(
                user_id=user_id,
                tenant_id=tenant_id,
                channel="email_fallback",
                message_type=message_type,
                message_text=message,
                status="fallback_email",
            )
            self.db.add(log)
            channels_sent.append({
                "channel": "email_fallback",
                "success": True,
                "note": "Nessun canale configurato, fallback email",
            })

        await self.db.flush()

        return {
            "message": message,
            "channels": channels_sent,
            "total_sent": len(channels_sent),
        }
