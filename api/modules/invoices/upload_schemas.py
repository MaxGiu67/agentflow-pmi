"""Schemas for invoice upload (US-06)."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class UploadResponse(BaseModel):
    """Response from file upload."""
    invoice_id: UUID
    filename: str
    file_type: str
    source: str
    processing_status: str
    message: str


class UploadErrorResponse(BaseModel):
    """Error response for upload."""
    detail: str
