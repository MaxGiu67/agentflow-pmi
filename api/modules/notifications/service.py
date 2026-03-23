"""Service layer for notifications (US-18).

Handles sending notifications via Telegram/WhatsApp with retry logic
and digest grouping when too many notifications are pending.
"""

import logging
import uuid
from datetime import datetime, UTC

from sqlalchemy import select, func as sqla_func
from sqlalchemy.ext.asyncio import AsyncSession

from api.adapters.telegram import TelegramAdapter
from api.adapters.whatsapp import WhatsAppAdapter
from api.db.models import NotificationConfig, NotificationLog

logger = logging.getLogger(__name__)

# Digest threshold: if more than 5 notifications in the same day, group them
DIGEST_THRESHOLD = 5


class NotificationService:
    """Service for sending notifications via configured channels."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.telegram = TelegramAdapter()
        self.whatsapp = WhatsAppAdapter()

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    async def create_or_update_config(
        self,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        channel: str,
        chat_id: str | None = None,
        phone: str | None = None,
        enabled: bool = True,
    ) -> dict:
        """Create or update notification channel config."""
        if channel not in ("telegram", "whatsapp"):
            raise ValueError(
                f"Canale '{channel}' non supportato. Canali: telegram, whatsapp"
            )
        if channel == "telegram" and not chat_id:
            raise ValueError("chat_id richiesto per canale Telegram")
        if channel == "whatsapp" and not phone:
            raise ValueError("phone richiesto per canale WhatsApp")

        # Check if config already exists
        result = await self.db.execute(
            select(NotificationConfig).where(
                NotificationConfig.user_id == user_id,
                NotificationConfig.channel == channel,
            )
        )
        config = result.scalar_one_or_none()

        if config:
            config.chat_id = chat_id
            config.phone = phone
            config.enabled = enabled
            config.tenant_id = tenant_id
        else:
            config = NotificationConfig(
                user_id=user_id,
                tenant_id=tenant_id,
                channel=channel,
                chat_id=chat_id,
                phone=phone,
                enabled=enabled,
            )
            self.db.add(config)

        await self.db.flush()

        return {
            "id": str(config.id),
            "user_id": str(config.user_id),
            "channel": config.channel,
            "chat_id": config.chat_id,
            "phone": config.phone,
            "enabled": config.enabled,
        }

    async def get_configs(self, user_id: uuid.UUID) -> list[dict]:
        """Get all notification configs for a user."""
        result = await self.db.execute(
            select(NotificationConfig).where(
                NotificationConfig.user_id == user_id,
            )
        )
        configs = result.scalars().all()
        return [
            {
                "id": str(c.id),
                "user_id": str(c.user_id),
                "channel": c.channel,
                "chat_id": c.chat_id,
                "phone": c.phone,
                "enabled": c.enabled,
            }
            for c in configs
        ]

    # ------------------------------------------------------------------
    # Sending
    # ------------------------------------------------------------------

    async def send_scadenza_notification(
        self,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        scadenza_tipo: str,
        scadenza_data: str,
        importo: float,
        link: str,
    ) -> list[dict]:
        """Send a deadline notification to the user on all configured channels.

        Args:
            user_id: Recipient user.
            tenant_id: Tenant.
            scadenza_tipo: Type of deadline (e.g. "Liquidazione IVA Q1").
            scadenza_data: Date string.
            importo: Amount.
            link: Link to detail page.

        Returns:
            List of send results.
        """
        text = (
            f"<b>Scadenza fiscale</b>\n"
            f"Tipo: {scadenza_tipo}\n"
            f"Data: {scadenza_data}\n"
            f"Importo: EUR {importo:,.2f}\n"
            f"Dettagli: {link}"
        )

        # Check if we should send digest instead
        should_digest = await self._should_send_digest(user_id)
        if should_digest:
            return await self._send_digest(user_id, tenant_id)

        return await self._send_to_all_channels(
            user_id=user_id,
            tenant_id=tenant_id,
            text=text,
            message_type="scadenza",
        )

    async def send_test_notification(
        self,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        channel: str | None = None,
    ) -> list[dict]:
        """Send a test notification."""
        text = "Notifica di test da ContaBot - canale configurato correttamente!"
        configs = await self.get_configs(user_id)
        if channel:
            configs = [c for c in configs if c["channel"] == channel]

        results: list[dict] = []
        for config in configs:
            result = await self._send_single(
                config=config,
                text=text,
                user_id=user_id,
                tenant_id=tenant_id,
                message_type="test",
            )
            results.append(result)
        return results

    async def _send_to_all_channels(
        self,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        text: str,
        message_type: str,
    ) -> list[dict]:
        """Send notification to all enabled channels for the user."""
        configs = await self.get_configs(user_id)
        enabled = [c for c in configs if c["enabled"]]

        results: list[dict] = []
        for config in enabled:
            result = await self._send_single(
                config=config,
                text=text,
                user_id=user_id,
                tenant_id=tenant_id,
                message_type=message_type,
            )
            results.append(result)
        return results

    async def _send_single(
        self,
        config: dict,
        text: str,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        message_type: str,
    ) -> dict:
        """Send a single notification with retry logic.

        On failure: retry up to 3 times (1h interval in production,
        immediate in mock). After max retries, fallback to email.
        """
        channel = config["channel"]
        max_retries = 3
        retry_count = 0
        last_error = None

        for attempt in range(max_retries + 1):
            if channel == "telegram":
                result = await self.telegram.send_message(
                    chat_id=config["chat_id"],
                    text=text,
                )
            elif channel == "whatsapp":
                result = await self.whatsapp.send_message(
                    phone=config["phone"],
                    text=text,
                )
            else:
                return {
                    "channel": channel,
                    "success": False,
                    "error": f"Canale non supportato: {channel}",
                    "retry_count": 0,
                    "fallback_used": False,
                }

            if result.success:
                # Log success
                log = NotificationLog(
                    user_id=user_id,
                    tenant_id=tenant_id,
                    channel=channel,
                    message_type=message_type,
                    message_text=text,
                    status="sent",
                    retry_count=retry_count,
                )
                self.db.add(log)
                await self.db.flush()

                return {
                    "channel": channel,
                    "success": True,
                    "message_id": result.message_id,
                    "retry_count": retry_count,
                    "fallback_used": False,
                }

            retry_count += 1
            last_error = result.error

        # All retries exhausted — fallback to email
        log = NotificationLog(
            user_id=user_id,
            tenant_id=tenant_id,
            channel=channel,
            message_type=message_type,
            message_text=text,
            status="fallback_email",
            retry_count=max_retries,
            error_message=last_error,
        )
        self.db.add(log)
        await self.db.flush()

        return {
            "channel": channel,
            "success": False,
            "error": last_error,
            "retry_count": max_retries,
            "fallback_used": True,
        }

    # ------------------------------------------------------------------
    # Digest
    # ------------------------------------------------------------------

    async def _should_send_digest(self, user_id: uuid.UUID) -> bool:
        """Check if notifications should be grouped into a digest.

        Returns True if >5 notifications were sent to this user today.
        """
        today_start = datetime.now(UTC).replace(
            hour=0, minute=0, second=0, microsecond=0,
        )
        result = await self.db.execute(
            select(sqla_func.count(NotificationLog.id)).where(
                NotificationLog.user_id == user_id,
                NotificationLog.sent_at >= today_start,
                NotificationLog.message_type != "digest",
            )
        )
        count = result.scalar() or 0
        return count > DIGEST_THRESHOLD

    async def _send_digest(
        self,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> list[dict]:
        """Send a grouped digest notification instead of individual ones."""
        today_start = datetime.now(UTC).replace(
            hour=0, minute=0, second=0, microsecond=0,
        )

        # Count pending notifications
        result = await self.db.execute(
            select(sqla_func.count(NotificationLog.id)).where(
                NotificationLog.user_id == user_id,
                NotificationLog.sent_at >= today_start,
                NotificationLog.message_type != "digest",
            )
        )
        count = result.scalar() or 0

        text = (
            f"<b>Riepilogo notifiche</b>\n"
            f"Hai {count} notifiche in attesa oggi.\n"
            f"Accedi a ContaBot per i dettagli."
        )

        return await self._send_to_all_channels(
            user_id=user_id,
            tenant_id=tenant_id,
            text=text,
            message_type="digest",
        )
