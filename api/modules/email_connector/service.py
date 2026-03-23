"""Service layer for email connector (US-08)."""

import logging
import uuid
from datetime import datetime, UTC

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import EmailConnection, Invoice

logger = logging.getLogger(__name__)


class EmailConnectorService:
    """Service for email-based invoice ingestion (Gmail OAuth, PEC/IMAP)."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def connect_gmail(self, tenant_id: uuid.UUID, email: str) -> dict:
        """Initiate Gmail OAuth flow.

        Returns an auth_url the frontend will redirect to.
        """
        # Check for existing connection with same email
        existing = await self._find_connection(tenant_id, email)
        if existing and existing.status == "connected":
            return {
                "auth_url": "",
                "connection_id": existing.id,
                "message": f"Gmail {email} gia collegato",
            }

        connection = EmailConnection(
            tenant_id=tenant_id,
            provider="gmail",
            email_address=email,
            status="pending",
        )
        self.db.add(connection)
        await self.db.flush()

        # In production: initiate real OAuth flow with Google
        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?client_id=contabot&redirect_uri=callback&scope=gmail.readonly&state={connection.id}"

        return {
            "auth_url": auth_url,
            "connection_id": connection.id,
            "message": "Redirect utente a Google per autorizzazione",
        }

    async def connect_imap(
        self,
        tenant_id: uuid.UUID,
        email: str,
        password: str,
        imap_server: str,
        imap_port: int = 993,
        use_ssl: bool = True,
    ) -> dict:
        """Connect PEC/IMAP account.

        Validates credentials by attempting a mock connection.
        """
        # Check for existing connection
        existing = await self._find_connection(tenant_id, email)
        if existing and existing.status == "connected":
            return {
                "connection_id": existing.id,
                "status": "connected",
                "message": f"Account {email} gia collegato",
            }

        # Validate credentials (mock for now)
        if not password or len(password) < 4:
            raise ValueError("Credenziali IMAP non valide. Verifica email e password.")

        # In production: attempt real IMAP connection
        # For now: simulate success for valid-looking credentials
        connection = EmailConnection(
            tenant_id=tenant_id,
            provider="imap",
            email_address=email,
            status="connected",
            credentials_encrypted=f"encrypted:{imap_server}:{imap_port}",  # In production: AES-256
        )
        self.db.add(connection)
        await self.db.flush()

        logger.info("IMAP connection established for %s", email)

        return {
            "connection_id": connection.id,
            "status": "connected",
            "message": f"Account PEC {email} collegato con successo",
        }

    async def get_status(self, tenant_id: uuid.UUID) -> dict:
        """Get all email connection statuses for a tenant."""
        result = await self.db.execute(
            select(EmailConnection).where(
                EmailConnection.tenant_id == tenant_id
            )
        )
        connections = result.scalars().all()

        return {
            "connections": [
                {
                    "id": str(conn.id),
                    "provider": conn.provider,
                    "email": conn.email_address,
                    "status": conn.status,
                    "last_sync_at": conn.last_sync_at.isoformat() if conn.last_sync_at else None,
                    "error": conn.error_message,
                }
                for conn in connections
            ],
            "total": len(connections),
        }

    async def check_email_invoice_duplicate(
        self,
        tenant_id: uuid.UUID,
        numero_fattura: str,
        emittente_piva: str,
    ) -> Invoice | None:
        """Dedup email invoice against cassetto fiscale."""
        result = await self.db.execute(
            select(Invoice).where(
                and_(
                    Invoice.tenant_id == tenant_id,
                    Invoice.numero_fattura == numero_fattura,
                    Invoice.emittente_piva == emittente_piva,
                )
            )
        )
        return result.scalar_one_or_none()

    async def _find_connection(
        self, tenant_id: uuid.UUID, email: str
    ) -> EmailConnection | None:
        """Find existing connection for tenant + email."""
        result = await self.db.execute(
            select(EmailConnection).where(
                and_(
                    EmailConnection.tenant_id == tenant_id,
                    EmailConnection.email_address == email,
                )
            )
        )
        return result.scalar_one_or_none()
