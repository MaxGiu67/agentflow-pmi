import uuid
from datetime import datetime

from pydantic import BaseModel


class SpidInitResponse(BaseModel):
    redirect_url: str
    message: str


class SpidCallbackResponse(BaseModel):
    message: str
    cassetto_connected: bool


class SpidStatusResponse(BaseModel):
    connected: bool
    token_valid: bool
    token_expires_at: datetime | None = None
    last_sync_at: datetime | None = None
    message: str


class SpidErrorResponse(BaseModel):
    message: str
    can_retry: bool = True
    alternatives: list[str] = []


class SpidDelegateRequest(BaseModel):
    delegante_cf: str  # Codice fiscale del delegante
