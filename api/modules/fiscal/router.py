"""Fiscal rules, VAT settlement, stamp duty, and accruals API router."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from api.modules.fiscal.accounting_engine import AccountingEngine
from api.modules.fiscal.accruals import AccrualsService
from api.modules.fiscal.schemas import (
    AccrualListResponse,
    AccrualProposeRequest,
    AccrualResponse,
    FiscalRulesListResponse,
    StampDutyCheckRequest,
    StampDutyCheckResponse,
    StampDutyQuarterlyResponse,
    VatSettlementComputeRequest,
    VatSettlementResponse,
)
from api.modules.fiscal.stamp_duty import StampDutyService
from api.modules.fiscal.vat_settlement import VatSettlementService

router = APIRouter(prefix="/fiscal", tags=["fiscal"])


@router.get("/rules", response_model=FiscalRulesListResponse)
async def list_fiscal_rules(
    key: str | None = Query(None, description="Filter rules by key pattern"),
    _user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FiscalRulesListResponse:
    """List all fiscal rules, optionally filtered by key pattern."""
    engine = AccountingEngine(db)
    rules = await engine.list_fiscal_rules(key_pattern=key)
    return FiscalRulesListResponse(rules=rules, count=len(rules))


@router.get("/vat-settlement", response_model=VatSettlementResponse)
async def get_vat_settlement(
    year: int = Query(..., description="Fiscal year"),
    quarter: int = Query(..., ge=1, le=4, description="Quarter (1-4)"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VatSettlementResponse:
    """Get existing VAT settlement for a given quarter."""
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    service = VatSettlementService(db)
    result = await service.get_settlement(user.tenant_id, year, quarter)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Liquidazione IVA Q{quarter} {year} non ancora calcolata",
        )

    return VatSettlementResponse(**result)


@router.post("/vat-settlement/compute", response_model=VatSettlementResponse)
async def compute_vat_settlement(
    request: VatSettlementComputeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VatSettlementResponse:
    """Compute (or recompute) quarterly VAT settlement.

    Formula: IVA debito (vendite) - IVA credito (acquisti)
             - credito precedente + interessi (1% trim)
    """
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    service = VatSettlementService(db)
    try:
        result = await service.compute(user.tenant_id, request.year, request.quarter)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return VatSettlementResponse(**result)


# ============================================================
# US-35: Stamp Duty (Imposta di Bollo)
# ============================================================


@router.post("/stamp-duties/check", response_model=StampDutyCheckResponse)
async def check_stamp_duty(
    request: StampDutyCheckRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StampDutyCheckResponse:
    """Check if an invoice requires stamp duty.

    AC-35.1: Detect obligation on exempt invoices > 77.47 EUR
    AC-35.3: Under threshold -> no stamp duty
    AC-35.4: Mixed invoice -> stamp duty only if exempt portion > 77.47
    AC-35.5: Passive invoice without bollo -> warning
    """
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    service = StampDutyService(db)
    try:
        result = await service.check_invoice(
            invoice_id=request.invoice_id,
            tenant_id=user.tenant_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return StampDutyCheckResponse(**result)


@router.get("/stamp-duties", response_model=StampDutyQuarterlyResponse)
async def get_stamp_duties(
    year: int = Query(..., description="Year"),
    quarter: int = Query(..., ge=1, le=4, description="Quarter (1-4)"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StampDutyQuarterlyResponse:
    """Get quarterly stamp duty summary.

    AC-35.2: Count quarterly (N invoices x 2 EUR, deadline, code 2501)
    """
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    service = StampDutyService(db)
    try:
        result = await service.get_quarterly_summary(
            tenant_id=user.tenant_id,
            year=year,
            quarter=quarter,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return StampDutyQuarterlyResponse(**result)


# ============================================================
# US-36: Ratei e Risconti (Accruals & Deferrals)
# ============================================================


@router.post("/accruals/propose")
async def propose_accrual(
    request: AccrualProposeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Propose an accrual/deferral.

    AC-36.1: Identify multi-year costs -> propose deferral
    AC-36.3: Non-apportionable -> request competence period
    AC-36.4: Passive accrual (cost incurred, not invoiced)
    """
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    service = AccrualsService(db)
    try:
        result = await service.propose_accrual(
            tenant_id=user.tenant_id,
            invoice_id=request.invoice_id,
            description=request.description,
            total_amount=request.total_amount,
            period_start=request.period_start,
            period_end=request.period_end,
            accrual_type=request.accrual_type,
            fiscal_year=request.fiscal_year,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return result


@router.get("/accruals", response_model=AccrualListResponse)
async def list_accruals(
    fiscal_year: int | None = Query(None, description="Filter by fiscal year"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AccrualListResponse:
    """List accruals for tenant."""
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    service = AccrualsService(db)
    result = await service.list_accruals(user.tenant_id, fiscal_year)
    return AccrualListResponse(**result)


@router.patch("/accruals/{accrual_id}/confirm", response_model=AccrualResponse)
async def confirm_accrual(
    accrual_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AccrualResponse:
    """AC-36.2: Confirm accrual -> generate adjustment and reversal entries."""
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    service = AccrualsService(db)
    try:
        result = await service.confirm_accrual(accrual_id, user.tenant_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return AccrualResponse(**result)
