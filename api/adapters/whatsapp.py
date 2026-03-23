"""Mock WhatsApp Business API adapter.

In production this calls the WhatsApp Business API (Meta Cloud API).
For testing, simulates message delivery with configurable failure modes.
"""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class WhatsAppSendResult:
    """Result of sending a WhatsApp message."""
    success: bool
    message_id: str | None = None
    error: str | None = None


class WhatsAppAdapter:
    """Mock adapter for WhatsApp Business API."""

    def __init__(self, api_token: str = "mock-wa-token") -> None:
        self.api_token = api_token
        self._fail_mode: bool = False
        self._sent_messages: list[dict] = []

    def set_fail_mode(self, fail: bool) -> None:
        """Enable/disable failure simulation."""
        self._fail_mode = fail

    def get_sent_messages(self) -> list[dict]:
        """Return all sent messages (for testing)."""
        return list(self._sent_messages)

    def clear_sent(self) -> None:
        """Clear sent messages (for testing)."""
        self._sent_messages.clear()

    async def send_message(
        self,
        phone: str,
        text: str,
    ) -> WhatsAppSendResult:
        """Send a message via WhatsApp.

        Args:
            phone: Phone number in international format.
            text: Message text.

        Returns:
            WhatsAppSendResult with delivery status.
        """
        if self._fail_mode:
            logger.warning("WhatsApp send failed (mock failure mode)")
            return WhatsAppSendResult(
                success=False,
                error="WhatsApp API error: numero non raggiungibile",
            )

        import uuid
        msg_id = f"wamid.{uuid.uuid4().hex[:20]}"
        self._sent_messages.append({
            "phone": phone,
            "text": text,
            "message_id": msg_id,
        })
        logger.info("WhatsApp message sent to %s (mock)", phone)
        return WhatsAppSendResult(success=True, message_id=msg_id)
