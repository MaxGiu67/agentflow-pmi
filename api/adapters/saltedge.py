"""Salt Edge Open Banking adapter — AISP (account info + transactions).

Uses Salt Edge Account Information API v6.
Docs: https://docs.saltedge.com/v6/

Key v5 → v6 changes:
- Scopes: account_details → accounts, transactions_details → transactions
- Connect: connect_sessions/create → connections/connect
- Customer field: id → customer_id
- Refresh: PUT → POST
- Transactions pending/duplicate: separate endpoints → query params
"""

import logging
from datetime import date
from typing import Optional

import httpx

from api.config import settings

logger = logging.getLogger(__name__)


class SaltEdgeClient:
    """Client for Salt Edge Open Banking API v6."""

    def __init__(self) -> None:
        self.base_url = settings.saltedge_base_url.rstrip("/")
        self.app_id = settings.saltedge_app_id
        self.secret = settings.saltedge_secret

    def _headers(self) -> dict:
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "App-id": self.app_id,
            "Secret": self.secret,
        }

    # ── Customers ─────────────────────────────────────────

    async def create_customer(self, identifier: str) -> dict:
        """Crea un customer Salt Edge (mappato al nostro tenant).

        Args:
            identifier: ID univoco (es. tenant UUID)

        Returns:
            dict con customer_id, identifier, created_at
        """
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/customers",
                headers=self._headers(),
                json={"data": {"identifier": identifier}},
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()["data"]

    async def list_customers(self) -> list[dict]:
        """Lista tutti i customer."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/customers",
                headers=self._headers(),
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()["data"]

    # ── Connect (bank link) — v6: /connections/connect ────

    async def create_connect_session(
        self,
        customer_id: str,
        country_code: str = "XF",
        return_url: str = "",
    ) -> dict:
        """Crea una sessione di connessione banca — restituisce URL per autenticazione.

        Args:
            customer_id: Salt Edge customer_id
            country_code: ISO country (default XF=Fake per test, IT per produzione)
            return_url: URL di redirect dopo auth banca (opzionale in test mode)

        Returns:
            dict con connect_url, expires_at
        """
        payload: dict = {
            "customer_id": customer_id,
            "consent": {
                "scopes": ["accounts", "transactions"],
                "from_date": str(date.today().replace(month=max(1, date.today().month - 3), day=1)),
            },
            "allowed_countries": [country_code],
        }

        # return_to e' opzionale — deve essere nella whitelist della dashboard
        if return_url:
            payload["attempt"] = {"return_to": return_url}

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/connections/connect",
                headers=self._headers(),
                json={"data": payload},
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()["data"]

    async def reconnect(self, connection_id: str) -> dict:
        """Riconnetti una connessione scaduta (rinnovo consent PSD2)."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/connections/{connection_id}/reconnect",
                headers=self._headers(),
                json={"data": {"consent": {"scopes": ["accounts", "transactions"]}}},
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()["data"]

    # ── Connections ───────────────────────────────────────

    async def list_connections(self, customer_id: str) -> list[dict]:
        """Lista tutte le connessioni bancarie di un customer."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/connections",
                headers=self._headers(),
                params={"customer_id": customer_id},
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()["data"]

    async def get_connection(self, connection_id: str) -> dict:
        """Dettaglio di una singola connessione."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/connections/{connection_id}",
                headers=self._headers(),
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()["data"]

    async def refresh_connection(self, connection_id: str) -> dict:
        """Aggiorna dati connessione (ri-scarica conti e transazioni).

        v6: POST (era PUT in v5).
        """
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/connections/{connection_id}/refresh",
                headers=self._headers(),
                json={"data": {"consent": {"scopes": ["accounts", "transactions"]}}},
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()["data"]

    async def remove_connection(self, connection_id: str) -> bool:
        """Rimuovi/revoca una connessione bancaria."""
        async with httpx.AsyncClient() as client:
            resp = await client.delete(
                f"{self.base_url}/connections/{connection_id}",
                headers=self._headers(),
                timeout=30,
            )
            resp.raise_for_status()
            return True

    # ── Accounts (balances) ──────────────────────────────

    async def list_accounts(self, connection_id: str) -> list[dict]:
        """Lista conti con saldi per una connessione.

        Returns:
            list di dict con: id, name, nature, balance, currency_code, iban, ...
        """
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/accounts",
                headers=self._headers(),
                params={"connection_id": connection_id},
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()["data"]

    # ── Transactions ─────────────────────────────────────

    async def list_transactions(
        self,
        connection_id: str,
        account_id: str,
        from_date: Optional[str] = None,
        include_pending: bool = False,
    ) -> list[dict]:
        """Lista transazioni per un conto.

        Args:
            connection_id: ID connessione Salt Edge
            account_id: ID conto Salt Edge
            from_date: data inizio (YYYY-MM-DD)
            include_pending: include transazioni in sospeso (v6: query param)

        Returns:
            list di dict con: id, amount, currency_code, description, category, made_on, status
        """
        params: dict = {
            "connection_id": connection_id,
            "account_id": account_id,
        }
        if from_date:
            params["from_date"] = from_date
        if include_pending:
            params["pending"] = "true"

        all_transactions = []
        async with httpx.AsyncClient() as client:
            while True:
                resp = await client.get(
                    f"{self.base_url}/transactions",
                    headers=self._headers(),
                    params=params,
                    timeout=30,
                )
                resp.raise_for_status()
                data = resp.json()
                all_transactions.extend(data["data"])

                # Paginazione: next_id
                next_id = data.get("meta", {}).get("next_id")
                if not next_id:
                    break
                params["from_id"] = next_id

        return all_transactions

    # ── Providers (list available banks) ─────────────────

    async def list_providers(
        self,
        country_code: str = "IT",
        include_sandboxes: bool = True,
    ) -> list[dict]:
        """Lista banche/provider disponibili per un paese.

        Args:
            country_code: ISO country (IT, XF per fake)
            include_sandboxes: include sandbox provider per testing

        Returns:
            list di dict con: code, name, country_code, status, mode, ...
        """
        params: dict = {"country_code": country_code}
        if include_sandboxes:
            params["include_sandboxes"] = "true"

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/providers",
                headers=self._headers(),
                params=params,
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()["data"]
