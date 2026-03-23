"""Router for invoices module."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from api.modules.invoices.schemas import (
    InvoiceListResponse,
    InvoiceResponse,
    PendingReviewResponse,
    SuggestedCategoriesResponse,
    SyncRequest,
    SyncResponse,
    SyncStatusResponse,
    VerifyRequest,
    VerifyResponse,
)
from api.modules.invoices.service import InvoiceService

router = APIRouter(tags=["invoices"])


def get_invoice_service(db: AsyncSession = Depends(get_db)) -> InvoiceService:
    return InvoiceService(db)


@router.post("/cassetto/sync", response_model=SyncResponse)
async def sync_cassetto(
    request: SyncRequest = SyncRequest(),
    user: User = Depends(get_current_user),
    service: InvoiceService = Depends(get_invoice_service),
) -> SyncResponse:
    """Force sync invoices from cassetto fiscale."""
    try:
        result = await service.sync_cassetto(
            user, force=request.force, from_date=request.from_date
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except ConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        ) from e
    return SyncResponse(**result)


@router.get("/cassetto/sync/status", response_model=SyncStatusResponse)
async def sync_status(
    user: User = Depends(get_current_user),
    service: InvoiceService = Depends(get_invoice_service),
) -> SyncStatusResponse:
    """Get sync status information."""
    result = await service.get_sync_status(user)
    return SyncStatusResponse(**result)


@router.get("/invoices", response_model=InvoiceListResponse)
async def list_invoices(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    type: str | None = Query(None),
    source: str | None = Query(None),
    status: str | None = Query(None),
    emittente: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    service: InvoiceService = Depends(get_invoice_service),
) -> InvoiceListResponse:
    """List invoices with filters and pagination."""
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    result = await service.get_invoices(
        tenant_id=user.tenant_id,
        page=page,
        page_size=page_size,
        date_from=date_from,
        date_to=date_to,
        type_filter=type,
        source=source,
        status=status,
        emittente=emittente,
    )
    return InvoiceListResponse(**result)


@router.get("/invoices/pending-review", response_model=PendingReviewResponse)
async def pending_review(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    service: InvoiceService = Depends(get_invoice_service),
) -> PendingReviewResponse:
    """List invoices that need category review (categorized but not verified)."""
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    result = await service.get_pending_review(
        tenant_id=user.tenant_id,
        page=page,
        page_size=page_size,
    )
    return PendingReviewResponse(**result)


@router.patch("/invoices/{invoice_id}/verify", response_model=VerifyResponse)
async def verify_invoice(
    invoice_id: UUID,
    request: VerifyRequest,
    user: User = Depends(get_current_user),
    service: InvoiceService = Depends(get_invoice_service),
) -> VerifyResponse:
    """Verify or correct an invoice category."""
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    try:
        result = await service.verify_invoice(
            tenant_id=user.tenant_id,
            invoice_id=invoice_id,
            category=request.category,
            confirmed=request.confirmed,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    return VerifyResponse(**result)


@router.get("/invoices/{invoice_id}/suggest-categories", response_model=SuggestedCategoriesResponse)
async def suggest_categories(
    invoice_id: UUID,
    user: User = Depends(get_current_user),
    service: InvoiceService = Depends(get_invoice_service),
) -> SuggestedCategoriesResponse:
    """Suggest similar categories when the category is not in the piano conti."""
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    try:
        invoice = await service.get_invoice(user.tenant_id, invoice_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    category = invoice.category or ""
    suggestions = service.suggest_similar_categories(category)
    return SuggestedCategoriesResponse(
        suggestions=suggestions,
        message=f"Suggerimenti per '{category}': {', '.join(suggestions)}" if suggestions else "Nessun suggerimento disponibile",
    )


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: UUID,
    user: User = Depends(get_current_user),
    service: InvoiceService = Depends(get_invoice_service),
) -> InvoiceResponse:
    """Get a single invoice by ID."""
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    try:
        invoice = await service.get_invoice(user.tenant_id, invoice_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    return InvoiceResponse.model_validate(invoice)
