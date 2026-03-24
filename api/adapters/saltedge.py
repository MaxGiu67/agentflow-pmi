"""Salt Edge Open Banking adapter — AISP (account info + transactions).

Uses Salt Edge Account Information API v5.
Docs: https://docs.saltedge.com/account_information/v5/
"""

import logging
from datetime import date

import httpx

from api.config import settings

logger = logging.getLogger(__name__)


class SaltEdgeClient:
    """Client for Salt Edge Open Banking API."""

    def __init__(self) -> None:
        self.base_url = settings.saltedge_base_url
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
        """Create a Salt Edge customer (maps to our tenant).

        Args:
            identifier: unique ID (e.g. tenant UUID)
        Returns:
            { id, identifier, secret }
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

    # ── Connect Session (bank link) ──────────────────────

    async def create_connect_session(
        self,
        customer_id: str,
        country_code: str = "IT",
        return_url: str = "",
    ) -> dict:
        """Create a connect session — returns a URL where the user authenticates with their bank.

        Args:
            customer_id: Salt Edge customer ID
            country_code: ISO country code (default IT)
            return_url: URL to redirect after bank auth

        Returns:
            { expires_at, connect_url } — redirect user to connect_url
        """
        if not return_url:
            return_url = f"{settings.frontend_url}/impostazioni?bank=connected"

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/connect_sessions/create",
                headers=self._headers(),
                json={
                    "data": {
                        "customer_id": customer_id,
                        "consent": {
                            "scopes": ["account_details", "transactions_details"],
                            "from_date": str(date.today().replace(day=1)),
                        },
                        "attempt": {
                            "return_to": return_url,
                            "fetch_scopes": ["accounts", "transactions"],
                        },
                        "allowed_countries": [country_code],
                    }
                },
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()["data"]

    # ── Connections ───────────────────────────────────────

    async def list_connections(self, customer_id: str) -> list[dict]:
        """List all bank connections for a customer."""
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
        """Get a single connection."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/connections/{connection_id}",
                headers=self._headers(),
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()["data"]

    async def refresh_connection(self, connection_id: str) -> dict:
        """Refresh connection data (re-fetch accounts and transactions)."""
        async with httpx.AsyncClient() as client:
            resp = await client.put(
                f"{self.base_url}/connections/{connection_id}/refresh",
                headers=self._headers(),
                json={"data": {"fetch_scopes": ["accounts", "transactions"]}},
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()["data"]

    async def remove_connection(self, connection_id: str) -> bool:
        """Remove/revoke a bank connection."""
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
        """Get accounts (with balances) for a connection.

        Returns list of: { id, name, nature, balance, currency_code, iban, ... }
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
        from_date: str | None = None,
    ) -> list[dict]:
        """Get transactions for an account.

        Returns list of: { id, amount, currency_code, description, category, made_on, status }
        """
        params: dict = {
            "connection_id": connection_id,
            "account_id": account_id,
        }
        if from_date:
            params["from_date"] = from_date

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/transactions",
                headers=self._headers(),
                params=params,
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()["data"]

    # ── Providers (list available banks) ─────────────────

    async def list_providers(self, country_code: str = "IT") -> list[dict]:
        """List available banks/providers for a country.

        Returns list of: { code, name, country_code, status, ... }
        """
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/providers",
                headers=self._headers(),
                params={"country_code": country_code},
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()["data"]
