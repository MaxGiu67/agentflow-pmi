"""Router A-Cube Open Banking (Pivot 11 Sprint 48 US-OB-04).

Endpoint esposti sotto `/api/v1/banking/connections`.
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from api.modules.banking.acube_ob_schemas import (
    BankConnectionListResponse,
    BankConnectionResponse,
    InitConnectionRequest,
    InitConnectionResponse,
    ReconnectResponse,
    SyncAccountsResponse,
    SyncNowResponse,
    SyncTransactionsRequest,
    SyncTransactionsResponse,
)
from api.modules.banking.acube_ob_service import (
    ACubeOBServiceError,
    ACubeOpenBankingService,
)

router = APIRouter(prefix="/banking/connections", tags=["banking-openbanking"])


def get_service(db: AsyncSession = Depends(get_db)) -> ACubeOpenBankingService:
    return ACubeOpenBankingService(db)


def _require_tenant(user: User) -> UUID:
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato per l'utente corrente",
        )
    return user.tenant_id


@router.post("/init", response_model=InitConnectionResponse)
async def init_connection(
    body: InitConnectionRequest,
    user: User = Depends(get_current_user),
    service: ACubeOpenBankingService = Depends(get_service),
) -> InitConnectionResponse:
    """Avvia flusso PSD2 Connect — crea BR su A-Cube se mancante.

    ⚠️ Generate fee su A-Cube al primo call per fiscal_id nuovo.
    """
    tenant_id = _require_tenant(user)
    try:
        result = await service.init_connection(
            tenant_id=tenant_id,
            return_url=body.return_url,
            fiscal_id=body.fiscal_id,
        )
    except ACubeOBServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    return InitConnectionResponse(**result)


@router.get("", response_model=BankConnectionListResponse)
async def list_connections(
    user: User = Depends(get_current_user),
    service: ACubeOpenBankingService = Depends(get_service),
) -> BankConnectionListResponse:
    tenant_id = _require_tenant(user)
    items = await service.list_connections(tenant_id)
    return BankConnectionListResponse(
        items=[BankConnectionResponse.model_validate(c) for c in items],
        total=len(items),
    )


@router.get("/{connection_id}", response_model=BankConnectionResponse)
async def get_connection(
    connection_id: UUID,
    user: User = Depends(get_current_user),
    service: ACubeOpenBankingService = Depends(get_service),
) -> BankConnectionResponse:
    tenant_id = _require_tenant(user)
    try:
        conn = await service.get_connection(connection_id, tenant_id)
    except ACubeOBServiceError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return BankConnectionResponse.model_validate(conn)


@router.post("/{connection_id}/sync-accounts", response_model=SyncAccountsResponse)
async def sync_accounts(
    connection_id: UUID,
    user: User = Depends(get_current_user),
    service: ACubeOpenBankingService = Depends(get_service),
) -> SyncAccountsResponse:
    """US-OB-06: recupera i conti A-Cube del BR e fa upsert su `bank_accounts`."""
    tenant_id = _require_tenant(user)
    try:
        result = await service.sync_accounts(connection_id, tenant_id)
    except ACubeOBServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    return SyncAccountsResponse(**result)


@router.post("/{connection_id}/sync-transactions", response_model=SyncTransactionsResponse)
async def sync_transactions(
    connection_id: UUID,
    body: SyncTransactionsRequest | None = None,
    since: date | None = Query(None, description="Backfill da questa data (ISO). Default: 30gg fa."),
    user: User = Depends(get_current_user),
    service: ACubeOpenBankingService = Depends(get_service),
) -> SyncTransactionsResponse:
    """US-OB-07: scarica transazioni A-Cube con backfill. Idempotente per (account, acube_transaction_id)."""
    tenant_id = _require_tenant(user)
    effective_since = (body.since if body and body.since else since)
    effective_until = body.until if body else None
    effective_status = body.status if body else None
    try:
        result = await service.sync_transactions(
            connection_id,
            tenant_id,
            since=effective_since,
            until=effective_until,
            status_filter=effective_status,
        )
    except ACubeOBServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    return SyncTransactionsResponse(**result)


@router.post("/{connection_id}/reconnect", response_model=ReconnectResponse)
async def request_reconnect(
    connection_id: UUID,
    user: User = Depends(get_current_user),
    service: ACubeOpenBankingService = Depends(get_service),
) -> ReconnectResponse:
    """US-OB-11: richiedi URL SCA per rinnovare consenso PSD2.

    Ritorna l'url dal webhook Reconnect se presente, altrimenti chiama A-Cube on-demand.
    """
    tenant_id = _require_tenant(user)
    try:
        result = await service.request_reconnect(connection_id, tenant_id)
    except ACubeOBServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    return ReconnectResponse(**result)


@router.post("/{connection_id}/sync-now", response_model=SyncNowResponse)
async def sync_now(
    connection_id: UUID,
    since: date | None = Query(
        None, description="Backfill transazioni da questa data. Default: delta dall'ultimo sync (o 30gg)."
    ),
    until: date | None = Query(
        None, description="Backfill transazioni fino a questa data. Default: oggi."
    ),
    user: User = Depends(get_current_user),
    service: ACubeOpenBankingService = Depends(get_service),
) -> SyncNowResponse:
    """Sync completo: accounts + transactions in sequenza.

    Se `since` è omesso e la connection ha già fatto un sync precedente, parte
    dall'ultimo sync_at - 1gg (overlap di sicurezza). Altrimenti default 30gg.
    """
    tenant_id = _require_tenant(user)
    try:
        result = await service.sync_now(connection_id, tenant_id, since=since, until=until)
    except ACubeOBServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return SyncNowResponse(**result)


# ── Sprint 50 — AI parser endpoints ─────────────────────────


class ParseResponse(BaseModel):
    connection_id: UUID
    parsed: int
    rules_count: int
    llm_count: int
    use_llm: bool
    force: bool
    message: str


class CorrectTxRequest(BaseModel):
    counterparty: str | None = None
    category: str | None = None
    invoice_ref: str | None = None


class CorrectTxResponse(BaseModel):
    id: UUID
    parsed_counterparty: str | None
    parsed_category: str | None
    parsed_invoice_ref: str | None
    user_corrected: bool


@router.post("/{connection_id}/parse", response_model=ParseResponse)
async def parse_transactions(
    connection_id: UUID,
    use_llm: bool = Query(True, description="Use LLM fallback per low-confidence (costo ~$0.0005/tx)"),
    force: bool = Query(False, description="Re-parse anche tx già parsate (escluse user_corrected)"),
    limit: int | None = Query(None, ge=1, le=2000, description="Max tx da parsare in questa chiamata"),
    user: User = Depends(get_current_user),
    service: ACubeOpenBankingService = Depends(get_service),
) -> ParseResponse:
    """Esegui parsing AI sulle transazioni di una connection.

    Pipeline: cache → rules (gratis) → LLM se confidence < 0.65.
    Categorie: income_invoice, expense_invoice, payroll, tax_f24, tax_iva, fee,
    transfer, loan_payment, interest, atm, pos, sepa_dd, refund, other.
    """
    tenant_id = _require_tenant(user)
    try:
        result = await service.parse_transactions(
            connection_id, tenant_id, force=force, use_llm=use_llm, limit=limit,
        )
    except ACubeOBServiceError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ParseResponse(**result)


@router.patch("/transactions/{tx_id}/correct", response_model=CorrectTxResponse)
async def correct_tx_parse(
    tx_id: UUID,
    body: CorrectTxRequest,
    user: User = Depends(get_current_user),
    service: ACubeOpenBankingService = Depends(get_service),
) -> CorrectTxResponse:
    """Correzione manuale del parse di una transazione.

    Imposta user_corrected=True così non viene sovrascritta da reparse successivi.
    Salvata anche per future fine-tuning del parser (feedback loop).
    """
    tenant_id = _require_tenant(user)
    try:
        tx = await service.correct_transaction_parse(
            tx_id, tenant_id,
            counterparty=body.counterparty, category=body.category, invoice_ref=body.invoice_ref,
        )
    except ACubeOBServiceError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return CorrectTxResponse(
        id=tx.id,
        parsed_counterparty=tx.parsed_counterparty,
        parsed_category=tx.parsed_category,
        parsed_invoice_ref=tx.parsed_invoice_ref,
        user_corrected=tx.user_corrected,
    )
