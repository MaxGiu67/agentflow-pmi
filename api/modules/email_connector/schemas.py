"""Schemas for email connector module (US-08)."""

from uuid import UUID

from pydantic import BaseModel, EmailStr


class GmailConnectRequest(BaseModel):
    """Request to initiate Gmail OAuth connection."""
    email: EmailStr


class GmailConnectResponse(BaseModel):
    """Response with OAuth URL."""
    auth_url: str
    connection_id: UUID
    message: str


class IMAPConnectRequest(BaseModel):
    """Request to connect PEC/IMAP account."""
    email: str
    password: str
    imap_server: str
    imap_port: int = 993
    use_ssl: bool = True


class IMAPConnectResponse(BaseModel):
    """Response from IMAP connection attempt."""
    connection_id: UUID
    status: str
    message: str


class EmailStatusResponse(BaseModel):
    """Response for email connection status."""
    connections: list[dict]
    total: int
