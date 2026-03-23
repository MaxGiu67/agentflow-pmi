"""Pydantic schemas for asset management (US-31, US-32)."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel


class AssetCreateRequest(BaseModel):
    """Request to create a fixed asset."""
    description: str
    category: str
    purchase_date: date
    purchase_amount: float
    is_used: bool = False
    invoice_id: UUID | None = None


class AssetResponse(BaseModel):
    """Single asset response."""
    id: str
    tenant_id: str
    invoice_id: str | None = None
    description: str
    category: str
    purchase_date: str
    purchase_amount: float
    depreciable_amount: float
    depreciation_rate: float
    accumulated_depreciation: float
    residual_value: float
    is_used: bool
    status: str
    disposal_date: str | None = None
    disposal_amount: float | None = None
    gain_loss: float | None = None
    journal_entry: dict | None = None
    category_suggestions: list[dict] | None = None


class AssetListResponse(BaseModel):
    """Response with list of assets (registro cespiti)."""
    items: list[AssetResponse]
    total: int


class AssetDisposeRequest(BaseModel):
    """Request to dispose of an asset."""
    disposal_date: date
    disposal_amount: float = 0.0  # 0 = rottamazione/furto


class AssetDisposeResponse(BaseModel):
    """Response from asset disposal."""
    id: str
    description: str
    disposal_date: str
    disposal_amount: float
    residual_value_at_disposal: float
    pro_rata_depreciation: float
    gain_loss: float
    gain_loss_type: str  # plusvalenza, minusvalenza, zero
    status: str
    journal_entries: list[dict]
    message: str


class DepreciationRunRequest(BaseModel):
    """Request to run annual depreciation."""
    fiscal_year: int


class DepreciationRunResponse(BaseModel):
    """Response from depreciation run."""
    fiscal_year: int
    assets_processed: int
    total_depreciation: float
    journal_entries: list[dict]
    fully_depreciated: list[dict]
    message: str


class AssetCheckRequest(BaseModel):
    """Request to check if invoice line should create an asset."""
    invoice_id: UUID
    line_description: str
    line_amount: float
    is_used: bool = False
