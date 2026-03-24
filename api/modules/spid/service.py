import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.adapters.fiscoapi import FiscoAPIClient
from api.config import settings
from api.db.models import User

logger = logging.getLogger(__name__)


def _get_real_fiscoapi():
    """Get real FiscoAPI client if configured, else mock."""
    if settings.fiscoapi_secret_key:
        from api.adapters.fiscoapi_real import FiscoAPIReal
        return FiscoAPIReal()
    return None


class SpidService:
    def __init__(self, db: AsyncSession, fiscoapi: FiscoAPIClient | None = None) -> None:
        self.db = db
        self.fiscoapi = fiscoapi or FiscoAPIClient()
        self.real_api = _get_real_fiscoapi()

    async def init_spid_auth(self, user: User) -> dict:
        """Start SPID authentication flow.

        If FiscoAPI real key is configured, creates a real session.
        Otherwise falls back to mock.
        """
        # If FiscoAPI link code is configured, redirect to FiscoAPI portal
        if settings.fiscoapi_link_code:
            redirect_url = f"https://app.fiscoapi.com/link?codice={settings.fiscoapi_link_code}"
            logger.info("SPID redirect to FiscoAPI link for user %s: %s", user.email, redirect_url)
            return {
                "redirect_url": redirect_url,
                "message": "Redirect al portale FiscoAPI per autenticazione SPID",
            }

        if self.real_api:
            try:
                session = await self.real_api.create_session(tipo_login="poste")
                session_id = session.get("_id", "")
                stato = session.get("stato", "")
                logger.info("FiscoAPI session created for %s: id=%s stato=%s", user.email, session_id, stato)

                user.spid_token = f"fiscoapi_session:{session_id}"
                await self.db.flush()

                return {
                    "redirect_url": "",
                    "session_id": session_id,
                    "stato": stato,
                    "session_data": session,
                    "message": "Sessione FiscoAPI creata. Completa l'autenticazione SPID.",
                }
            except Exception as e:
                logger.error("FiscoAPI real session failed: %s, falling back to mock", e)

        callback_url = f"{settings.app_url}/api/v1/auth/spid/callback"
        result = await self.fiscoapi.init_spid_auth(callback_url)

        logger.info("SPID auth initiated for user %s (mock)", user.email)
        return {
            "redirect_url": result.redirect_url,
            "message": "Redirect al provider SPID per l'autenticazione",
        }

    async def handle_spid_callback(self, code: str, state: str, user: User) -> dict:
        """Handle SPID callback after user authenticates."""
        try:
            result = await self.fiscoapi.handle_spid_callback(code, state)
        except ValueError:
            logger.warning("SPID auth cancelled/failed for user %s", user.email)
            return {
                "message": "Autenticazione annullata — serve SPID o CIE per accedere al cassetto fiscale",
                "cassetto_connected": False,
            }

        # Save encrypted token
        user.spid_token = result.access_token  # In production: encrypt with AES-256
        user.spid_token_expires_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(
            seconds=result.token_expires_in
        )
        await self.db.flush()

        logger.info("SPID auth successful for user %s, token expires at %s",
                     user.email, user.spid_token_expires_at)
        return {
            "message": "Cassetto fiscale collegato con successo",
            "cassetto_connected": True,
        }

    async def get_spid_status(self, user: User) -> dict:
        """Get SPID connection status."""
        if not user.spid_token:
            return {
                "connected": False,
                "token_valid": False,
                "token_expires_at": None,
                "last_sync_at": None,
                "message": "Cassetto fiscale non collegato. Autentica con SPID o CIE.",
            }

        token_valid = await self.fiscoapi.check_token_validity(user.spid_token)

        # Check expiration
        if user.spid_token_expires_at and user.spid_token_expires_at < datetime.now(UTC).replace(tzinfo=None):
            token_valid = False

        if not token_valid:
            return {
                "connected": True,
                "token_valid": False,
                "token_expires_at": user.spid_token_expires_at,
                "last_sync_at": None,
                "message": "Sessione cassetto fiscale scaduta — riautentica con SPID",
            }

        return {
            "connected": True,
            "token_valid": True,
            "token_expires_at": user.spid_token_expires_at,
            "last_sync_at": None,
            "message": "Cassetto fiscale collegato e attivo",
        }

    async def get_no_spid_info(self) -> dict:
        """Return info for users without SPID/CIE."""
        return {
            "message": (
                "Per accedere al cassetto fiscale serve SPID o CIE. "
                "Puoi ottenere SPID da: Poste Italiane, Aruba, InfoCert, Namirial, "
                "TIM, Lepida, Register.it, Sielte."
            ),
            "can_retry": False,
            "alternatives": [
                "Upload manuale delle fatture in formato XML o PDF",
                "Richiedi SPID su https://www.spid.gov.it/ottieni-spid",
            ],
        }

    async def init_delegate_auth(self, user: User, delegante_cf: str) -> dict:
        """Start delegated SPID auth for commercialista."""
        callback_url = f"{settings.app_url}/api/v1/auth/spid/callback"
        result = await self.fiscoapi.init_delegate_auth(callback_url, delegante_cf)

        logger.info("Delegate SPID auth initiated by %s for CF %s",
                     user.email, delegante_cf)
        return {
            "redirect_url": result.redirect_url,
            "message": f"Redirect per autenticazione delegata (CF: {delegante_cf})",
        }
