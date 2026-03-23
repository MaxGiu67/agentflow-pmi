"""Schemas for notifications module (US-18)."""

from pydantic import BaseModel


class NotificationConfigCreate(BaseModel):
    """Create/update notification channel configuration."""
    channel: str  # telegram, whatsapp
    chat_id: str | None = None  # Required for Telegram
    phone: str | None = None  # Required for WhatsApp
    enabled: bool = True


class NotificationConfigResponse(BaseModel):
    """Response for notification configuration."""
    id: str
    user_id: str
    channel: str
    chat_id: str | None = None
    phone: str | None = None
    enabled: bool


class NotificationConfigListResponse(BaseModel):
    """Response listing all notification configs."""
    configs: list[NotificationConfigResponse]
    count: int


class NotificationTestRequest(BaseModel):
    """Request to send a test notification."""
    channel: str | None = None  # If None, send to all configured channels


class NotificationTestResponse(BaseModel):
    """Response from test notification."""
    channel: str
    success: bool
    message: str


class NotificationSendResult(BaseModel):
    """Result of sending a notification."""
    channel: str
    success: bool
    message_id: str | None = None
    error: str | None = None
    retry_count: int = 0
    fallback_used: bool = False
