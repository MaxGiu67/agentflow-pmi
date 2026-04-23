"""Pydantic schemas for PEC module."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class PecProviderPreset(BaseModel):
    code: str
    label: str
    smtp_host: str
    smtp_port: int
    imap_host: str
    imap_port: int
    docs: str | None = None


class PecProvidersResponse(BaseModel):
    providers: list[PecProviderPreset]


class PecConfigRequest(BaseModel):
    provider: str = Field(..., description="aruba|namirial|poste|legalmail|register|custom")
    pec_address: EmailStr
    username: str
    password: str = Field(..., min_length=4)
    smtp_host: str | None = None
    smtp_port: int | None = None
    imap_host: str | None = None
    imap_port: int | None = None


class PecConfigResponse(BaseModel):
    provider: str
    pec_address: str
    username: str
    smtp_host: str
    smtp_port: int
    imap_host: str
    imap_port: int
    verified: bool
    last_test_at: datetime | None = None
    last_test_error: str | None = None


class PecTestResponse(BaseModel):
    smtp_ok: bool
    imap_ok: bool
    error: str | None = None


class PecSendResponse(BaseModel):
    invoice_id: UUID
    pec_message_id: str
    recipient: str
    filename: str
    sent_at: datetime
    sdi_status: str


class PecReceiptRecord(BaseModel):
    receipt_type: str
    subject: str | None = None
    sender: str | None = None
    related_filename: str | None = None
    message_id: str | None = None
    sent_at: datetime


class PecPollResponse(BaseModel):
    new_receipts: int
    items: list[PecReceiptRecord]
