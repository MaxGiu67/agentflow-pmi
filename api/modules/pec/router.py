"""PEC router — config, test, invoice dispatch, receipts polling."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.adapters import pec_client
from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from api.modules.pec.schemas import (
    PecConfigRequest,
    PecConfigResponse,
    PecPollResponse,
    PecProviderPreset,
    PecProvidersResponse,
    PecReceiptRecord,
    PecSendResponse,
    PecTestResponse,
)
from api.modules.pec.service import PecService, PecServiceError

router = APIRouter(prefix="/pec", tags=["pec"])


def get_service(db: AsyncSession = Depends(get_db)) -> PecService:
    return PecService(db)


def _require_tenant(user: User) -> UUID:
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )
    return user.tenant_id


def _cfg_to_response(cfg) -> PecConfigResponse:
    return PecConfigResponse(
        provider=cfg.provider,
        pec_address=cfg.pec_address,
        username=cfg.username,
        smtp_host=cfg.smtp_host,
        smtp_port=cfg.smtp_port,
        imap_host=cfg.imap_host,
        imap_port=cfg.imap_port,
        verified=cfg.verified,
        last_test_at=cfg.last_test_at,
        last_test_error=cfg.last_test_error,
    )


@router.get("/providers", response_model=PecProvidersResponse)
async def list_providers() -> PecProvidersResponse:
    """List known PEC providers with SMTP/IMAP presets."""
    return PecProvidersResponse(
        providers=[
            PecProviderPreset(
                code=code,
                label=p["label"],
                smtp_host=p["smtp_host"],
                smtp_port=p["smtp_port"],
                imap_host=p["imap_host"],
                imap_port=p["imap_port"],
                docs=p.get("docs"),
            )
            for code, p in pec_client.PEC_PROVIDERS.items()
        ]
    )


@router.get("/config", response_model=PecConfigResponse | None)
async def get_config(
    user: User = Depends(get_current_user),
    service: PecService = Depends(get_service),
) -> PecConfigResponse | None:
    tenant_id = _require_tenant(user)
    cfg = await service.get_config(tenant_id)
    if not cfg:
        return None
    return _cfg_to_response(cfg)


@router.put("/config", response_model=PecConfigResponse)
async def upsert_config(
    body: PecConfigRequest,
    user: User = Depends(get_current_user),
    service: PecService = Depends(get_service),
) -> PecConfigResponse:
    tenant_id = _require_tenant(user)
    try:
        cfg = await service.upsert_config(
            tenant_id=tenant_id,
            provider=body.provider,
            pec_address=body.pec_address,
            username=body.username,
            password=body.password,
            smtp_host=body.smtp_host,
            smtp_port=body.smtp_port,
            imap_host=body.imap_host,
            imap_port=body.imap_port,
        )
    except PecServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return _cfg_to_response(cfg)


@router.post("/config/test", response_model=PecTestResponse)
async def test_config(
    user: User = Depends(get_current_user),
    service: PecService = Depends(get_service),
) -> PecTestResponse:
    tenant_id = _require_tenant(user)
    try:
        result = await service.test_connection(tenant_id)
    except PecServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return PecTestResponse(smtp_ok=result.smtp_ok, imap_ok=result.imap_ok, error=result.error)


@router.post("/invoices/{invoice_id}/send", response_model=PecSendResponse)
async def send_invoice_pec(
    invoice_id: UUID,
    file: UploadFile = File(..., description="Fattura firmata .xml.p7m"),
    user: User = Depends(get_current_user),
    service: PecService = Depends(get_service),
) -> PecSendResponse:
    tenant_id = _require_tenant(user)
    filename = file.filename or ""
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="File vuoto")
    if not (filename.endswith(".p7m") or filename.endswith(".xml")):
        raise HTTPException(status_code=400, detail="Il file deve essere .xml o .xml.p7m")

    try:
        msg = await service.send_signed_invoice_to_sdi(
            tenant_id=tenant_id,
            invoice_id=invoice_id,
            filename=filename,
            p7m_content=content,
        )
    except PecServiceError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e)) from e

    return PecSendResponse(
        invoice_id=invoice_id,
        pec_message_id=msg.message_id or "",
        recipient=msg.recipient or pec_client.SDI_PEC_ADDRESS,
        filename=filename,
        sent_at=msg.sent_at,
        sdi_status="sent",
    )


@router.post("/receipts/poll", response_model=PecPollResponse)
async def poll_receipts(
    user: User = Depends(get_current_user),
    service: PecService = Depends(get_service),
) -> PecPollResponse:
    tenant_id = _require_tenant(user)
    try:
        new_msgs = await service.poll_receipts(tenant_id=tenant_id)
    except PecServiceError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e)) from e
    return PecPollResponse(
        new_receipts=len(new_msgs),
        items=[
            PecReceiptRecord(
                receipt_type=m.receipt_type or "",
                subject=m.subject,
                sender=m.sender,
                related_filename=m.attachment_name,
                message_id=m.message_id,
                sent_at=m.sent_at,
            )
            for m in new_msgs
        ],
    )
