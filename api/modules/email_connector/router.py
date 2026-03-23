"""Router for email connector (US-08)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from api.modules.email_connector.schemas import (
    GmailConnectRequest,
    GmailConnectResponse,
    IMAPConnectRequest,
    IMAPConnectResponse,
    EmailStatusResponse,
)
from api.modules.email_connector.service import EmailConnectorService

router = APIRouter(tags=["email"])


def get_email_service(db: AsyncSession = Depends(get_db)) -> EmailConnectorService:
    return EmailConnectorService(db)


@router.post("/email/connect/gmail", response_model=GmailConnectResponse)
async def connect_gmail(
    request: GmailConnectRequest,
    user: User = Depends(get_current_user),
    service: EmailConnectorService = Depends(get_email_service),
) -> GmailConnectResponse:
    """Initiate Gmail OAuth connection flow."""
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    result = await service.connect_gmail(
        tenant_id=user.tenant_id,
        email=request.email,
    )
    return GmailConnectResponse(**result)


@router.post("/email/connect/imap", response_model=IMAPConnectResponse)
async def connect_imap(
    request: IMAPConnectRequest,
    user: User = Depends(get_current_user),
    service: EmailConnectorService = Depends(get_email_service),
) -> IMAPConnectResponse:
    """Connect PEC/IMAP email account."""
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    try:
        result = await service.connect_imap(
            tenant_id=user.tenant_id,
            email=request.email,
            password=request.password,
            imap_server=request.imap_server,
            imap_port=request.imap_port,
            use_ssl=request.use_ssl,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return IMAPConnectResponse(**result)


@router.get("/email/status", response_model=EmailStatusResponse)
async def email_status(
    user: User = Depends(get_current_user),
    service: EmailConnectorService = Depends(get_email_service),
) -> EmailStatusResponse:
    """Get email connection status."""
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    result = await service.get_status(user.tenant_id)
    return EmailStatusResponse(**result)
