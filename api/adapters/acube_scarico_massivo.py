"""A-Cube Scarico Massivo Cassetto Fiscale — adapter REALE.

Implementazione basata su risposta Antonio (2026-04-27) + docs A-Cube ufficiali:
- Modalità: APPOINTEE (incaricato — figura interna NexaData)
- Docs: https://docs.acubeapi.com/documentation/italy/gov-it/cassettofiscale
- Massive download: https://docs.acubeapi.com/documentation/italy/gov-it/invoices/massive-download
- Webhooks: https://docs.acubeapi.com/documentation/italy/gov-it/webhooks
- Sandbox: https://docs.acubeapi.com/documentation/italy/gov-it/sandbox/introduction

Flusso onboarding cliente (per ogni P.IVA che vogliamo monitorare):
  1. Tu (incaricato) sei già configurato lato A-Cube via support
  2. PUT /ade-appointees/{id}/credentials/fisconline → salva password+PIN incaricato
  3. POST /business-registry-configuration → crea config per P.IVA cliente
  4. Cliente conferisce incarico sul portale AdE (manuale, +PDF guida)
  5. PUT /business-registry-configurations/{id}/assign → assegna config a incaricato
  6. POST /schedule/invoice-download/{fiscal_id} → schedula scarico daily
  7. (opzionale) POST /jobs/invoice-download → backfill storico (last year)
  8. Webhook → notifica nuove fatture
  9. GET /invoices?fiscalId=... → recupera fatture scaricate
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from typing import Any

from api.adapters.acube_ob import (
    ACubeAPIError,
    ACubeAuthError,
    ACubeOpenBankingClient,
)

logger = logging.getLogger(__name__)

# Backward compat: P.IVA A-Cube come delegato proxy (modalità sconsigliata da Antonio
# 2026-04-27 ma ancora citata nella guida UI). Lasciato per la card guida AdE.
ACUBE_PROXY_FISCAL_ID = "10442360961"


@dataclass
class AppointeeCredentials:
    """Credenziali Fisconline dell'incaricato (da salvare cifrate)."""
    password: str
    pin: str


@dataclass
class BRConfig:
    """Risposta creazione business-registry-configuration."""
    id: str
    fiscal_id: str  # P.IVA cliente
    enabled: bool


class ACubeScaricoMassivoClient(ACubeOpenBankingClient):
    """Client per A-Cube Cassetto Fiscale — emissione/ricezione fatture massive download.

    Eredita JWT auth da ACubeOpenBankingClient (stesso account, stesso login).
    Usa il dominio gov-it API: https://api.acubeapi.com (sandbox: api-sandbox).
    """

    def __init__(self) -> None:
        super().__init__()
        # Override base URL: gov-it API ≠ Open Banking API
        # Uso lo stesso pattern di acube_einvoicing.py
        from api.config import settings
        self.base_url = (
            settings.acube_einvoicing_base_url_prod
            if self.env == "production"
            else settings.acube_einvoicing_base_url_sandbox
        )

    # ── 1. Appointee credentials ──────────────────────────

    async def set_appointee_credentials(
        self,
        appointee_fiscal_id: str,
        password: str,
        pin: str,
        *,
        username_or_fiscal_id: str | None = None,
    ) -> dict[str, Any]:
        """PUT /ade-appointees/{fiscal_id}/credentials/fisconline

        Salva password+PIN Fisconline dell'incaricato su A-Cube (cifrate lato loro).
        Lo stesso incaricato vale per tutti i clienti gestiti.

        username_or_fiscal_id: opzionale, omettere se username == fiscal_id.
        """
        body: dict[str, Any] = {"password": password, "pin": pin}
        if username_or_fiscal_id:
            body["username_or_fiscal_id"] = username_or_fiscal_id
        return await self._put(
            f"/ade-appointees/{appointee_fiscal_id}/credentials/fisconline",
            body,
        )

    # ── 2. BusinessRegistryConfiguration ──────────────────

    async def create_br_configuration(
        self, fiscal_id: str
    ) -> dict[str, Any]:
        """POST /business-registry-configurations

        Crea config per una P.IVA cliente. Step 1 dell'onboarding, prima
        dell'assignment all'incaricato.
        """
        return await self._post(
            "/business-registry-configurations",
            {"fiscal_id": fiscal_id},
        )

    async def get_br_configuration(self, config_id: str) -> dict[str, Any]:
        """GET /business-registry-configurations/{id}"""
        return await self._get(f"/business-registry-configurations/{config_id}")

    async def assign_to_appointee(
        self,
        appointee_fiscal_id: str,
        client_fiscal_id: str,
        *,
        proxying_fiscal_id: str | None = None,
    ) -> dict[str, Any]:
        """POST /ade-appointees/{appointee_fiscal_id}/assign

        Body camelCase come da Antonio 2026-04-28:
          fiscalId          → P.IVA cliente (obbligatorio)
          proxyingFiscalId  → CF persona fisica (opzionale, solo lavoratori autonomi
                              o ditte individuali)

        Modalità INCARICO (operatore): appointee_fiscal_id = CF persona fisica registrata
        come Incaricato sul portale AdE. proxying_fiscal_id non serve.

        Modalità DELEGA (proxy A-Cube): appointee_fiscal_id = ACUBE_PROXY_FISCAL_ID
        (10442360961). Per partite IVA standard proxying_fiscal_id non serve.
        """
        body: dict[str, Any] = {"fiscalId": client_fiscal_id}
        if proxying_fiscal_id:
            body["proxyingFiscalId"] = proxying_fiscal_id
        return await self._post(
            f"/ade-appointees/{appointee_fiscal_id}/assign",
            body,
        )

    async def assign_via_proxy_delega(
        self,
        client_fiscal_id: str,
        *,
        proxying_fiscal_id: str | None = None,
    ) -> dict[str, Any]:
        """Scorciatoia: assegna usando A-Cube SRL come delegato unificato.

        Per il caso "amministratore unico/gestore" dove il CF dell'utente è
        già Gestore della società e AdE non permette di aggiungersi anche
        come Incaricato. Antonio 2026-04-28: usa Delega Unificata ad A-Cube.

        Prerequisito utente: delega ad A-Cube SRL (P.IVA 10442360961) sul
        portale AdE → Profilo → Deleghe → Intermediari → Nuova delega.
        """
        return await self.assign_to_appointee(
            appointee_fiscal_id=ACUBE_PROXY_FISCAL_ID,
            client_fiscal_id=client_fiscal_id,
            proxying_fiscal_id=proxying_fiscal_id,
        )

    # ── 3. Massive download — schedule ────────────────────

    async def schedule_daily_download(
        self,
        fiscal_id: str,
        *,
        download_archive: bool = False,
    ) -> dict[str, Any]:
        """POST /schedule/invoice-download/{fiscal_id}

        Attiva scarico schedulato daily alle 03:00 UTC.
        - download_archive=False (default): scarica solo ultimi 3 giorni
        - download_archive=True: include archivio dal 1 gennaio dell'anno scorso

        Per backfill storico: chiamare PRIMA con download_archive=true.
        """
        return await self._post(
            f"/schedule/invoice-download/{fiscal_id}",
            {"download_archive": download_archive},
        )

    async def get_schedule_status(self, fiscal_id: str) -> dict[str, Any]:
        """GET /schedule/invoice-download/{fiscal_id}

        Ritorna {enabled, valid_until, auto_renew}.
        """
        return await self._get(f"/schedule/invoice-download/{fiscal_id}")

    async def disable_auto_renew(self, fiscal_id: str) -> dict[str, Any]:
        """PUT /schedule/invoice-download/{fiscal_id}"""
        return await self._put(
            f"/schedule/invoice-download/{fiscal_id}",
            {"auto_renew": False},
        )

    async def delete_schedule(self, fiscal_id: str) -> dict[str, Any]:
        """DELETE /schedule/invoice-download/{fiscal_id}"""
        return await self._delete(f"/schedule/invoice-download/{fiscal_id}")

    # ── 4. Single download job (one-shot, custom range) ───

    async def trigger_one_shot_download(
        self,
        fiscal_id: str,
        from_date: date,
        to_date: date,
    ) -> dict[str, Any]:
        """POST /jobs/invoice-download

        Lancia un singolo job di download su un range custom.
        Utile per backfill storico mirato.
        Tempo completamento: fino a 72h (Antonio 2026-04-27).
        """
        return await self._post(
            "/jobs/invoice-download",
            {
                "fiscal_id": fiscal_id,
                "from_date": from_date.isoformat(),
                "to_date": to_date.isoformat(),
            },
        )

    # ── 5. Retrieve downloaded invoices ───────────────────

    async def list_invoices(
        self,
        *,
        fiscal_id: str | None = None,
        direction: str | None = None,  # active|passive
        from_date: date | None = None,
        to_date: date | None = None,
        page: int = 1,
        items_per_page: int = 100,
    ) -> list[dict[str, Any]]:
        """GET /invoices

        Lista fatture scaricate. Pagina automaticamente.
        """
        params: dict[str, Any] = {
            "page": page,
            "itemsPerPage": items_per_page,
        }
        if fiscal_id:
            params["fiscalId"] = fiscal_id
        if direction:
            params["direction"] = direction
        if from_date:
            params["date[after]"] = from_date.isoformat()
        if to_date:
            params["date[before]"] = to_date.isoformat()
        return await self._paginate("/invoices", params=params)

    async def get_invoice(self, uuid: str) -> dict[str, Any]:
        """GET /invoices/{uuid}"""
        return await self._get(f"/invoices/{uuid}")

    async def get_invoice_xml(self, uuid: str) -> str:
        """GET /invoices/{uuid} con Accept: application/xml — ritorna FatturaPA raw."""
        token = await self._get_token()
        import httpx
        async with httpx.AsyncClient(timeout=30) as client:
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


__all__ = [
    "ACubeScaricoMassivoClient",
    "AppointeeCredentials",
    "BRConfig",
    "ACubeAPIError",
    "ACubeAuthError",
]
