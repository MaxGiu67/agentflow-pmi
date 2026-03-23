"""Pydantic schemas for payments PISP module (US-27)."""

from uuid import UUID

from pydantic import BaseModel


class PaymentExecuteRequest(BaseModel):
    """Request to execute a single payment via PISP."""
    bank_account_id: UUID
    invoice_id: UUID
    beneficiary_name: str
    beneficiary_iban: str
    amount: float
    causale: str | None = None


class PaymentBatchRequest(BaseModel):
    """Request to execute a batch payment via PISP."""
    bank_account_id: UUID
    beneficiary_name: str
    beneficiary_iban: str
    invoice_ids: list[UUID]


class PaymentResponse(BaseModel):
    """Response from payment execution."""
    id: UUID
    tenant_id: UUID
    bank_account_id: UUID
    beneficiary_name: str
    beneficiary_iban: str
    amount: float
    causale: str | None = None
    payment_type: str
    sca_status: str
    error_message: str | None = None
    reconciled: bool = False

    model_config = {"from_attributes": True}


class PaymentBatchResponse(BaseModel):
    """Response from batch payment execution."""
    payment: PaymentResponse
    invoice_count: int
    total_amount: float
    causale: str


class PaymentErrorResponse(BaseModel):
    """Error response from payment."""
    error: str
    detail: str
    saldo_disponibile: float | None = None
