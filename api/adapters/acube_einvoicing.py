"""A-Cube E-Invoicing Italy — SDI send/receive + Cassetto Fiscale bulk download.

Shared JWT auth with AISP: same login endpoint (common(-sandbox).api.acubeapi.com),
different base URL for the domain API.

Reference:
- OpenAPI: https://docs.acubeapi.com/openapi/gov-it-api.json
- Docs: https://docs.acubeapi.com/documentation/italy/gov-it/invoices/
- Production: https://api.acubeapi.com
- Sandbox: https://api-sandbox.acubeapi.com

Unlike the manual PEC flow, A-Cube signs server-side (CAdES-BES) and
delivers to SDI on our behalf. We just POST the raw FatturaPA XML.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import date
from typing import Any

import httpx

from api.adapters.acube_ob import (
    ACubeAPIError,
    ACubeAuthError,
    ACubeOpenBankingClient,
    DEFAULT_TIMEOUT_SECONDS,
)
from api.config import settings

logger = logging.getLogger(__name__)


# Invoice "marking" values returned by A-Cube
MARKING_WAITING = "waiting"        # queued for SDI
MARKING_SENT = "sent"              # delivered to SDI, waiting response
MARKING_DELIVERED = "delivered"    # SDI delivered to recipient (RC)
MARKING_REJECTED = "rejected"      # SDI rejected (NS)
MARKING_NOT_DELIVERED = "not_delivered"  # MC — recipient unreachable
MARKING_ACCEPTED = "accepted"      # NE — recipient accepted (PA only)
MARKING_REFUSED = "refused"        # NE — recipient refused (PA only)
MARKING_EXPIRED = "expired"        # DT — 15 days elapsed (PA only)


@dataclass
class SendInvoiceResult:
    uuid: str
    marking: str = MARKING_WAITING


@dataclass
class InvoiceStatus:
    uuid: str
    marking: str
    number: str | None = None
    date: str | None = None
    total: float | None = None
    recipient_fiscal_id: str | None = None
    rejection_reason: str | None = None
    raw: dict[str, Any] | None = None


class ACubeEInvoicingClient(ACubeOpenBankingClient):
    """Client for A-Cube E-Invoicing Italy REST API.

    Reuses auth flow from ACubeOpenBankingClient (same JWT covers all A-Cube services).
    Overrides `base_url` to point at the e-invoicing domain instead of Open Banking.
    """

    def __init__(self) -> None:
        super().__init__()
        # Override env for e-invoicing if configured separately
        # (AISP can run in production while e-invoicing stays in sandbox)
        einv_env_override = (settings.acube_einvoicing_env or "").lower()
        if einv_env_override in ("sandbox", "production"):
            self.env = einv_env_override
            # If overriding to a different env, use prod credentials when needed
            if einv_env_override == "production" and settings.acube_prod_login_email:
                self.email = settings.acube_prod_login_email
                self.password = settings.acube_prod_login_password
                self.login_url = settings.acube_ob_login_url_prod
                self.enabled = bool(self.email and self.password)
                # Reset cached token since credentials changed
                self._token = None
                self._token_expires_at = 0
            elif einv_env_override == "sandbox":
                self.login_url = settings.acube_ob_login_url_sandbox

        # Set base URL for the e-invoicing domain (separate from OB)
        self.base_url = (
            settings.acube_einvoicing_base_url_prod
            if self.env == "production"
            else settings.acube_einvoicing_base_url_sandbox
        )

    # ── Send invoice to SDI ────────────────────────────────

    async def send_invoice_xml(self, xml_content: str) -> SendInvoiceResult:
        """POST /invoices with the FatturaPA XML.

        A-Cube signs (CAdES-BES) and forwards to SDI. Returns UUID immediately;
        actual SDI delivery is async (typically ~60 seconds).
        """
        if not self.enabled:
            raise ACubeAuthError("ACube client non configurato")

        token = await self._get_token()
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SECONDS) as client:
            resp = await client.post(
                f"{self.base_url}/invoices",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/xml",
                    "Accept": "application/json",
                },
                content=xml_content.encode("utf-8"),
            )

        if resp.status_code not in (200, 201, 202):
            logger.error("A-Cube send_invoice_xml failed HTTP %s: %s", resp.status_code, resp.text[:500])
            raise ACubeAPIError(resp.status_code, resp.text)

        data = resp.json()
        uuid = data.get("uuid") or data.get("@id", "").split("/")[-1]
        if not uuid:
            raise ACubeAPIError(resp.status_code, f"Response missing uuid: {resp.text[:200]}")
        return SendInvoiceResult(uuid=uuid, marking=data.get("marking", MARKING_WAITING))

    async def send_invoice_json(self, payload: dict[str, Any]) -> SendInvoiceResult:
        """POST /invoices with JSON (A-Cube FatturaPA JSON format, snake_case)."""
        if not self.enabled:
            raise ACubeAuthError("ACube client non configurato")

        token = await self._get_token()
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SECONDS) as client:
            resp = await client.post(
                f"{self.base_url}/invoices",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json=payload,
            )

        if resp.status_code not in (200, 201, 202):
            logger.error("A-Cube send_invoice_json failed HTTP %s: %s", resp.status_code, resp.text[:500])
            raise ACubeAPIError(resp.status_code, resp.text)

        data = resp.json()
        uuid = data.get("uuid") or data.get("@id", "").split("/")[-1]
        return SendInvoiceResult(uuid=uuid, marking=data.get("marking", MARKING_WAITING))

    # ── Status / notifications ─────────────────────────────

    async def get_invoice(self, uuid: str) -> InvoiceStatus:
        """GET /invoices/{uuid} — current marking + metadata."""
        data = await self._get(f"/invoices/{uuid}", params=None)
        return InvoiceStatus(
            uuid=uuid,
            marking=(data.get("marking") or MARKING_WAITING).lower(),
            number=data.get("number"),
            date=data.get("date"),
            total=data.get("total"),
            recipient_fiscal_id=(data.get("recipient") or {}).get("fiscalId")
                if isinstance(data.get("recipient"), dict)
                else data.get("recipientFiscalId"),
            rejection_reason=data.get("rejectionReason") or data.get("errorMessage"),
            raw=data,
        )

    async def get_notifications(self, uuid: str) -> list[dict[str, Any]]:
        """GET /invoices/{uuid}/notifications — list of SDI receipts (RC/NS/MC/NE/DT)."""
        data = await self._get(f"/invoices/{uuid}/notifications", params=None)
        if isinstance(data, dict):
            return data.get("hydra:member") or data.get("member") or []
        return data or []

    # ── List / search ──────────────────────────────────────

    async def list_invoices(
        self,
        *,
        direction: str | None = None,  # active|passive
        fiscal_id: str | None = None,
        since: date | None = None,
        until: date | None = None,
        marking: str | None = None,
        page: int = 1,
        items_per_page: int = 100,
    ) -> list[dict[str, Any]]:
        """GET /invoices with filters — supports pagination via Hydra."""
        params: dict[str, Any] = {
            "page": page,
            "itemsPerPage": items_per_page,
        }
        if direction:
            params["direction"] = direction
        if fiscal_id:
            params["fiscalId"] = fiscal_id
        if since:
            params["date[after]"] = since.isoformat()
        if until:
            params["date[before]"] = until.isoformat()
        if marking:
            params["marking"] = marking

        return await self._paginate("/invoices", params=params)

    async def get_invoice_xml(self, uuid: str) -> str:
        """Fetch the raw FatturaPA XML for an invoice.

        Invoices endpoint returns JSON with either a direct XML field or a reference.
        TODO: confirm exact shape on first real call — A-Cube docs mention that
        the XML is available through a dedicated accept header or subresource.
        """
        token = await self._get_token()
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SECONDS) as client:
            resp = await client.get(
                f"{self.base_url}/invoices/{uuid}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/xml",
                },
            )
        if resp.status_code != 200:
            raise ACubeAPIError(resp.status_code, resp.text)
        return resp.text

    # ── Actions ────────────────────────────────────────────

    async def resend_invoice(self, uuid: str) -> dict[str, Any]:
        """PUT /invoices/{uuid}/resend — retry after SDI rejection (NS)."""
        return await self._put(f"/invoices/{uuid}/resend", {})

    async def validate_invoice_xml(self, xml_content: str) -> dict[str, Any]:
        """POST /invoices/validate — dry-run, no charge."""
        if not self.enabled:
            raise ACubeAuthError("ACube client non configurato")
        token = await self._get_token()
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SECONDS) as client:
            resp = await client.post(
                f"{self.base_url}/invoices/validate",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/xml",
                    "Accept": "application/json",
                },
                content=xml_content.encode("utf-8"),
            )
        if resp.status_code not in (200, 202):
            raise ACubeAPIError(resp.status_code, resp.text)
        return resp.json() if resp.content else {}

    # ── Bulk download from Cassetto Fiscale ────────────────

    async def trigger_bulk_download(
        self,
        *,
        fiscal_id: str,
        since: date | None = None,
        until: date | None = None,
        direction: str | None = None,  # active|passive
    ) -> dict[str, Any]:
        """POST /jobs/invoice-download — trigger async bulk download job."""
        body: dict[str, Any] = {"fiscalId": fiscal_id}
        if since:
            body["dateFrom"] = since.isoformat()
        if until:
            body["dateTo"] = until.isoformat()
        if direction:
            body["direction"] = direction
        return await self._post("/jobs/invoice-download", body)

    async def get_yearly_stats(self, year: int) -> dict[str, Any]:
        """GET /invoices/stats/{year} — quota monitoring."""
        return await self._get(f"/invoices/stats/{year}", params=None)


__all__ = [
    "ACubeEInvoicingClient",
    "SendInvoiceResult",
    "InvoiceStatus",
    "MARKING_WAITING",
    "MARKING_SENT",
    "MARKING_DELIVERED",
    "MARKING_REJECTED",
    "MARKING_NOT_DELIVERED",
    "MARKING_ACCEPTED",
    "MARKING_REFUSED",
    "MARKING_EXPIRED",
    "ACubeAPIError",
    "ACubeAuthError",
]
