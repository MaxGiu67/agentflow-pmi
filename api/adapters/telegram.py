"""Mock Telegram Bot API adapter.

In production this calls the Telegram Bot API.
For testing, simulates message delivery with configurable failure modes.
"""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TelegramSendResult:
    """Result of sending a Telegram message."""
    success: bool
    message_id: str | None = None
    error: str | None = None


class TelegramAdapter:
    """Mock adapter for Telegram Bot API."""

    def __init__(self, bot_token: str = "mock-bot-token") -> None:
        self.bot_token = bot_token
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
        chat_id: str,
        text: str,
        parse_mode: str = "HTML",
    ) -> TelegramSendResult:
        """Send a message to a Telegram chat.

        Args:
            chat_id: Telegram chat ID.
            text: Message text (HTML formatted).
            parse_mode: Parse mode (HTML or Markdown).

        Returns:
            TelegramSendResult with delivery status.
        """
        if self._fail_mode:
            logger.warning("Telegram send failed (mock failure mode)")
            return TelegramSendResult(
                success=False,
                error="Telegram API error: chat not found or bot blocked",
            )

        import uuid
        msg_id = str(uuid.uuid4().int)[:10]
        self._sent_messages.append({
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "message_id": msg_id,
        })
        logger.info("Telegram message sent to chat %s (mock)", chat_id)
        return TelegramSendResult(success=True, message_id=msg_id)
