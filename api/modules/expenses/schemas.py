"""Pydantic schemas for expense management (US-29, US-30)."""

from datetime import date

from pydantic import BaseModel


class ExpenseCreateRequest(BaseModel):
    """Request to create an expense entry."""
    description: str
    amount: float
    currency: str = "EUR"
    category: str | None = None
    expense_date: date
    receipt_file: str | None = None
    ocr_text: str | None = None


class ExpenseResponse(BaseModel):
    """Single expense response."""
    id: str
    tenant_id: str
    user_id: str
    description: str
    amount: float
    currency: str
    amount_eur: float
    exchange_rate: float | None = None
    category: str | None = None
    category_confidence: float | None = None
    receipt_file: str | None = None
    ocr_readable: bool
    expense_date: str
    policy_warning: str | None = None
    status: str
    approved_by: str | None = None
    rejection_reason: str | None = None
    journal_entry: dict | None = None


class ExpenseListResponse(BaseModel):
    """Response with list of expenses."""
    items: list[ExpenseResponse]
    total: int


class ExpenseApproveRequest(BaseModel):
    """Request to approve an expense (empty body, auth determines approver)."""
    pass


class ExpenseRejectRequest(BaseModel):
    """Request to reject an expense with motivation."""
    reason: str


class ExpenseReimburseRequest(BaseModel):
    """Request to reimburse an approved expense."""
    payment_method: str = "pisp"  # pisp, manual


class ExpenseReimburseResponse(BaseModel):
    """Response from reimbursement attempt."""
    expense_id: str
    status: str
    journal_entry: dict | None = None
    message: str
