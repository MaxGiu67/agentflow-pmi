"""A-Cube Open Banking (AISP) async client — ADR-012.

Pivot 11 "Finance Cockpit" — Sprint 48 US-OB-01 + US-OB-02.

Autenticazione: solo JWT via POST /login (email + password), token 24h.
Nessun refresh endpoint (confermato da A-Cube 2026-04-20) → ri-login.

Documentazione:
- Auth: https://docs.acubeapi.com/documentation/common/authentication
- OB API: https://docs.acubeapi.com/documentation/open-banking/
- OpenAPI: https://docs.acubeapi.com/openapi/open-banking-api.json
- KB interna: Docs/acube-openbanking-kb/
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

from api.config import settings

logger = logging.getLogger(__name__)

TOKEN_REFRESH_MARGIN_SECONDS = 60 * 60  # rinnova 1h prima scadenza (24h → 23h cache)
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_ITEMS_PER_PAGE = 100  # max consentito da A-Cube


class ACubeAuthError(Exception):
    """Errore autenticazione A-Cube (login fallito o JWT invalido)."""


class ACubeAPIError(Exception):
    """Errore generico chiamata API A-Cube (4xx/5xx inattesi)."""

    def __init__(self, status_code: int, body: str) -> None:
        self.status_code = status_code
        self.body = body
        super().__init__(f"A-Cube API error HTTP {status_code}: {body[:200]}")


class ACubeOpenBankingClient:
    """Client async per A-Cube Open Banking API (AISP).

    Pattern: in-memory cache JWT + lock asincrono per evitare login concorrenti.
    Gracefully disabled se config assente (ritorna strutture vuote).
    """

    def __init__(self) -> None:
        self.env = (settings.acube_ob_env or "sandbox").lower()
        # In production, prefer dedicated prod credentials if set (sandbox + prod
        # accounts can be different on A-Cube)
        if self.env == "production" and settings.acube_prod_login_email:
            self.email = settings.acube_prod_login_email
            self.password = settings.acube_prod_login_password
        else:
            self.email = settings.acube_ob_login_email
            self.password = settings.acube_ob_login_password
        self.login_url = (
            settings.acube_ob_login_url_prod
            if self.env == "production"
            else settings.acube_ob_login_url_sandbox
        )
        self.base_url = (
            settings.acube_ob_base_url_prod
            if self.env == "production"
            else settings.acube_ob_base_url_sandbox
        )
        self.enabled = bool(self.email and self.password)

        self._token: str | None = None
        self._token_expires_at: float = 0
        self._login_lock = asyncio.Lock()

        if not self.enabled:
            logger.warning(
                "ACubeOpenBankingClient disabled — acube_ob_login_email/password not set"
            )

    # ── Authentication ─────────────────────────────────────

    async def _login(self) -> str:
        """Chiama POST /login e restituisce JWT fresco.

        Non fa caching: il caller deve usare `_get_token()`.
        """
        if not self.enabled:
            raise ACubeAuthError("ACubeOpenBankingClient non configurato")

        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SECONDS) as client:
            resp = await client.post(
                self.login_url,
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                json={"email": self.email, "password": self.password},
            )

        if resp.status_code != 200:
            logger.error("A-Cube login failed: HTTP %s", resp.status_code)
            raise ACubeAuthError(f"Login fallito HTTP {resp.status_code}")

        data = resp.json()
        token = data.get("token")
        if not token:
            raise ACubeAuthError("Login response senza campo 'token'")
        return token

    async def _get_token(self) -> str:
        """Ritorna JWT cache-hit o genera nuovo via /login.

        Thread-safe asincrono via asyncio.Lock → evita login concorrenti.
        Cache TTL: 23h (token vive 24h, margine 1h).
        """
        now = time.time()
        if self._token and now < self._token_expires_at:
            return self._token

        async with self._login_lock:
            # double-check dopo l'acquisizione del lock
            now = time.time()
            if self._token and now < self._token_expires_at:
                return self._token

            token = await self._login()
            self._token = token
            self._token_expires_at = now + (24 * 3600 - TOKEN_REFRESH_MARGIN_SECONDS)
            logger.info("A-Cube JWT refreshed (env=%s)", self.env)
            return token

    async def _headers(self, hydra: bool = True) -> dict[str, str]:
        token = await self._get_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/ld+json" if hydra else "application/json",
        }

    def invalidate_token(self) -> None:
        """Forza refresh al prossimo `_get_token()` — usare su 401."""
        self._token = None
        self._token_expires_at = 0

    # ── HTTP helpers ───────────────────────────────────────

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        hydra: bool = True,
        _retry_on_401: bool = True,
    ) -> Any:
        """Chiamata HTTP con retry automatico su 401 (refresh + 1 retry).

        Returns:
            dict | list: response JSON.

        Raises:
            ACubeAuthError: login fallito dopo retry.
            ACubeAPIError: risposta 4xx/5xx diversa da 401.
        """
        if not self.enabled:
            logger.warning("ACubeOpenBankingClient disabled — request skipped: %s %s", method, path)
            return {}

        url = f"{self.base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SECONDS) as client:
                resp = await client.request(
                    method,
                    url,
                    params=params,
                    json=json,
                    headers=await self._headers(hydra=hydra),
                )

            if resp.status_code == 401 and _retry_on_401:
                logger.warning("A-Cube 401 on %s %s — refreshing token and retrying", method, path)
                self.invalidate_token()
                return await self._request(
                    method, path,
                    params=params, json=json, hydra=hydra,
                    _retry_on_401=False,
                )

            if 200 <= resp.status_code < 300:
                if resp.status_code == 204 or not resp.content:
                    return {}
                return resp.json()

            logger.error("A-Cube %s %s → HTTP %s: %s", method, path, resp.status_code, resp.text[:300])
            raise ACubeAPIError(resp.status_code, resp.text)

        except httpx.HTTPError as exc:
            logger.error("A-Cube %s %s transport error: %s", method, path, exc)
            raise ACubeAPIError(0, str(exc)) from exc

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return await self._request("GET", path, params=params)

    async def _post(self, path: str, body: dict[str, Any]) -> Any:
        return await self._request("POST", path, json=body)

    async def _put(self, path: str, body: dict[str, Any]) -> Any:
        return await self._request("PUT", path, json=body)

    async def _delete(self, path: str) -> Any:
        return await self._request("DELETE", path)

    # ── Pagination helper ──────────────────────────────────

    async def _paginate(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        *,
        max_pages: int = 1000,
    ) -> list[dict[str, Any]]:
        """Itera tutte le pagine Hydra finché `hydra:view.hydra:next` esiste.

        A-Cube max `itemsPerPage=100`.
        """
        results: list[dict[str, Any]] = []
        page = 1
        p = dict(params or {})
        p.setdefault("itemsPerPage", DEFAULT_ITEMS_PER_PAGE)

        while page <= max_pages:
            p["page"] = page
            data = await self._get(path, params=p)
            members = data.get("hydra:member") or data.get("member") or []
            results.extend(members)

            view = data.get("hydra:view") or {}
            if not view.get("hydra:next") and not view.get("next"):
                break
            page += 1

        return results

    # ── Business Registry ──────────────────────────────────

    async def list_business_registries(self) -> list[dict[str, Any]]:
        """GET /business-registry (paginato). Readonly — no fee."""
        return await self._paginate("/business-registry")

    async def get_business_registry(self, fiscal_id: str) -> dict[str, Any]:
        """GET /business-registry/{fiscalId}. Readonly — no fee."""
        return await self._get(f"/business-registry/{fiscal_id}")

    async def create_business_registry(
        self, fiscal_id: str, email: str, business_name: str, enabled: bool = False
    ) -> dict[str, Any]:
        """POST /business-registry. ⚠️ GENERA FEE — usare con cautela."""
        return await self._post(
            "/business-registry",
            {
                "fiscalId": fiscal_id,
                "email": email,
                "businessName": business_name,
                "enabled": enabled,
            },
        )

    async def update_business_registry(
        self,
        fiscal_id: str,
        *,
        enabled: bool | None = None,
        email: str | None = None,
        business_name: str | None = None,
    ) -> dict[str, Any]:
        """PUT /business-registry/{fiscalId} — update fields. Used to flip enabled flag."""
        body: dict[str, Any] = {"fiscalId": fiscal_id}
        if enabled is not None:
            body["enabled"] = enabled
        if email is not None:
            body["email"] = email
        if business_name is not None:
            body["businessName"] = business_name
        return await self._put(f"/business-registry/{fiscal_id}", body)

    # ── Connect PSD2 ───────────────────────────────────────

    async def start_connect(
        self, fiscal_id: str, redirect_url: str, locale: str = "it"
    ) -> dict[str, Any]:
        """POST /business-registry/{fiscalId}/connect → restituisce URL SCA.

        Note: questo endpoint NON supporta application/ld+json (risponde 406).
        Usiamo application/json puro.
        """
        return await self._request(
            "POST",
            f"/business-registry/{fiscal_id}/connect",
            json={"redirectUrl": redirect_url, "locale": locale},
            hydra=False,
        )

    # ── Accounts ───────────────────────────────────────────

    async def list_accounts(self, fiscal_id: str, enabled: bool | None = None) -> list[dict[str, Any]]:
        """GET /business-registry/{fiscalId}/accounts (paginato)."""
        params: dict[str, Any] = {}
        if enabled is not None:
            params["enabled"] = "true" if enabled else "false"
        return await self._paginate(
            f"/business-registry/{fiscal_id}/accounts", params=params
        )

    async def get_account(self, account_uuid: str) -> dict[str, Any]:
        return await self._get(f"/accounts/{account_uuid}")

    async def reconnect_account(self, account_uuid: str) -> dict[str, Any]:
        """GET /accounts/{uuid}/reconnect → redirectUrl per rinnovo SCA."""
        return await self._get(f"/accounts/{account_uuid}/reconnect")

    # ── Transactions ───────────────────────────────────────

    async def list_transactions(
        self,
        fiscal_id: str,
        *,
        account_uuid: str | None = None,
        made_on_after: str | None = None,
        made_on_before: str | None = None,
        status: str | list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """GET /business-registry/{fiscalId}/transactions (paginato).

        ⚠️ Default A-Cube: se `madeOn` non specificato → solo mese corrente.
        Per backfill storico SEMPRE passare `made_on_after`.
        """
        params: dict[str, Any] = {}
        if account_uuid:
            params["account.uuid"] = account_uuid
        if made_on_after:
            params["madeOn[strictly_after]"] = made_on_after
        if made_on_before:
            params["madeOn[before]"] = made_on_before
        if status:
            if isinstance(status, list):
                for s in status:
                    params.setdefault("status[]", []).append(s)
            else:
                params["status"] = status
        return await self._paginate(
            f"/business-registry/{fiscal_id}/transactions", params=params
        )

    # ── Categories ─────────────────────────────────────────

    async def list_categories(self) -> list[dict[str, Any]]:
        return await self._paginate("/categories")


# Singleton di comodo (stesso pattern degli altri adapter)
acube_ob_client = ACubeOpenBankingClient()
