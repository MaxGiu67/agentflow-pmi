"""FiscoAPI real adapter — connects to api.fiscoapi.com for cassetto fiscale.

Handles: authentication (chiave segreta → pubblica), session management (SPID),
invoice download, F24, CU, and webhook processing.
"""

import logging
import time

import httpx

from api.config import settings

logger = logging.getLogger(__name__)

# Token cache
_token_cache: dict = {"public_key": None, "refresh_token": None, "expires_at": 0}


class FiscoAPIReal:
    """Real client for FiscoAPI — cassetto fiscale, fatture, F24."""

    def __init__(self) -> None:
        self.base_url = settings.fiscoapi_base_url
        self.secret_key = settings.fiscoapi_secret_key

    # ── Auth ──────────────────────────────────────────────

    async def _get_public_key(self) -> str:
        """Get or refresh public key (valid 1h)."""
        now = time.time()

        # Use cached key if still valid (with 5min buffer)
        if _token_cache["public_key"] and _token_cache["expires_at"] > now + 300:
            return _token_cache["public_key"]

        # Try refresh first
        if _token_cache["refresh_token"]:
            try:
                return await self._refresh_key()
            except Exception:
                logger.warning("Refresh failed, creating new key")

        # Create new key
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/crea_chiave_api",
                json={"chiave_segreta": self.secret_key},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

        _token_cache["public_key"] = data["chiave_pubblica"]
        _token_cache["refresh_token"] = data["refresh_token"]
        _token_cache["expires_at"] = now + 3600  # 1h

        logger.info("FiscoAPI: new public key created")
        return _token_cache["public_key"]

    async def _refresh_key(self) -> str:
        """Refresh public key using refresh token."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/refresh_chiave_api",
                json={"refresh_token": _token_cache["refresh_token"]},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

        _token_cache["public_key"] = data["chiave_pubblica"]
        _token_cache["expires_at"] = time.time() + 3600

        logger.info("FiscoAPI: public key refreshed")
        return _token_cache["public_key"]

    async def _headers(self) -> dict:
        """Get auth headers with current public key."""
        key = await self._get_public_key()
        return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    # ── Session (SPID login) ─────────────────────────────

    async def create_session(self) -> dict:
        """Create a new SPID authentication session.

        Returns session object with state and login URL.
        """
        headers = await self._headers()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/sessione/crea",
                headers=headers,
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()

    async def get_session_status(self, session_id: str) -> dict:
        """Check session authentication state."""
        headers = await self._headers()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/sessione/{session_id}",
                headers=headers,
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()

    # ── Fatture ───────────────────────────────────────────

    async def request_invoices(
        self,
        utente_lavoro: str,
        tipo: str = "ricevute",
        inizio: int | None = None,
        fine: int | None = None,
        skip: int = 0,
        limit: int = 3000,
    ) -> dict:
        """Request invoice list from cassetto fiscale.

        Args:
            utente_lavoro: P.IVA or codice fiscale
            tipo: emesse | ricevute | emesse_transfrontaliere | ricevute_transfrontaliere
            inizio: start timestamp in ms (default: 90 days ago)
            fine: end timestamp in ms (default: now)
            skip: pagination offset
            limit: max results (default 3000)

        Returns:
            RichiestaFatture object with _id, stato, fatture array
        """
        headers = await self._headers()

        now_ms = int(time.time() * 1000)
        if not inizio:
            inizio = now_ms - (90 * 24 * 3600 * 1000)  # 90 days ago
        if not fine:
            fine = now_ms

        params = {
            "utente_lavoro": utente_lavoro,
            "tipo": tipo,
            "inizio": inizio,
            "fine": fine,
            "skip": skip,
            "limit": limit,
        }

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/iva_e_servizi/fatture",
                headers=headers,
                params=params,
                timeout=60,
            )
            resp.raise_for_status()
            return resp.json()

    async def get_invoice_xml(self, id_fattura: str, tipo: str = "dettaglio") -> dict:
        """Get single invoice XML or metadata.

        Args:
            id_fattura: format {tipoInvio}{idFattura} e.g. FPR198709123
            tipo: dettaglio | metadati
        """
        headers = await self._headers()

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/iva_e_servizi/xml_fattura",
                headers=headers,
                params={"id_fattura": id_fattura, "tipo": tipo},
                timeout=60,
            )
            resp.raise_for_status()
            return resp.json()

    async def check_request_status(self, request_id: str) -> dict:
        """Poll status of async request (fatture, CU, versamenti)."""
        headers = await self._headers()

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/richiesta/{request_id}",
                headers=headers,
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()

    # ── F24 / Versamenti ──────────────────────────────────

    async def request_payments(self, tipo: str = "F24") -> dict:
        """Request F24 or F23 payment history.

        Args:
            tipo: F24 | F23
        """
        headers = await self._headers()

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/cassetto_fiscale/versamenti",
                headers=headers,
                params={"tipo": tipo},
                timeout=60,
            )
            resp.raise_for_status()
            return resp.json()

    async def download_f24(self, id_versamento: str) -> dict:
        """Download F24 document."""
        headers = await self._headers()

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/cassetto_fiscale/download_versamento_f24/{id_versamento}",
                headers=headers,
                timeout=60,
            )
            resp.raise_for_status()
            return resp.json()

    # ── CU (Certificazione Unica) ─────────────────────────

    async def request_cu(self) -> dict:
        """Request Certificazione Unica list."""
        headers = await self._headers()

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/cassetto_fiscale/certificazioni_uniche",
                headers=headers,
                timeout=60,
            )
            resp.raise_for_status()
            return resp.json()

    # ── File download ─────────────────────────────────────

    async def download_file(self, id_file: str) -> bytes:
        """Download a file (PDF, XML, etc.) by ID."""
        headers = await self._headers()

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/files/{id_file}",
                headers=headers,
                timeout=60,
            )
            resp.raise_for_status()
            return resp.content

    # ── Webhook processing ────────────────────────────────

    @staticmethod
    def parse_webhook(payload: dict) -> dict:
        """Parse incoming FiscoAPI webhook payload.

        Webhook format:
        {
            "tipo_dato": "Sessione|RichiestaFatture|...",
            "tipo_evento": "update",
            "data_invio": timestamp,
            "dato": { ... actual data ... }
        }
        """
        return {
            "type": payload.get("tipo_dato"),
            "event": payload.get("tipo_evento"),
            "timestamp": payload.get("data_invio"),
            "data": payload.get("dato", {}),
        }
