"""Brevo (ex Sendinblue) email adapter — invio + tracking (ADR-009, US-92).

Documentazione API: https://developers.brevo.com/reference
"""

import logging
import os

import httpx

logger = logging.getLogger(__name__)

BREVO_API_URL = "https://api.brevo.com/v3"


class BrevoClient:
    """Async client for Brevo transactional email API."""

    def __init__(
        self,
        api_key: str | None = None,
        sender_email: str | None = None,
        sender_name: str | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("BREVO_API_KEY", "")
        self.sender_email = sender_email or os.getenv("BREVO_SENDER_EMAIL", "noreply@agentflow.it")
        self.sender_name = sender_name or os.getenv("BREVO_SENDER_NAME", "AgentFlow")
        self._client: httpx.AsyncClient | None = None

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=BREVO_API_URL,
                headers={
                    "api-key": self.api_key,
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    async def send_email(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        html_content: str,
        params: dict | None = None,
        tags: list[str] | None = None,
    ) -> str:
        """Send a transactional email. Returns Brevo messageId.

        AC-92.2: HTML body with variable substitution.
        AC-92.3: Returns brevo_message_id for tracking.
        """
        # Substitute variables in content
        content = html_content
        if params:
            for key, val in params.items():
                content = content.replace(f"{{{{{key}}}}}", str(val))
                subject = subject.replace(f"{{{{{key}}}}}", str(val))

        payload = {
            "sender": {"name": self.sender_name, "email": self.sender_email},
            "to": [{"email": to_email, "name": to_name}],
            "subject": subject,
            "htmlContent": content,
            "tags": tags or [],
        }

        client = await self._get_client()

        try:
            resp = await client.post("/smtp/email", json=payload)
            resp.raise_for_status()
            data = resp.json()
            message_id = data.get("messageId", "")
            logger.info("Email sent via Brevo to=%s, messageId=%s", to_email, message_id)
            return message_id
        except httpx.HTTPStatusError as e:
            logger.error("Brevo API error: %s — %s", e.response.status_code, e.response.text)
            raise
        except httpx.RequestError as e:
            logger.error("Brevo connection error: %s", e)
            raise

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
