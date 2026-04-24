"""A-Cube Scarico Massivo Cassetto Fiscale — adapter.

STATO: SCAFFOLDING — in attesa risposta Ticket 02 A-Cube (inviato 2026-04-24).

Le firme dei metodi sono stabili, le implementazioni HTTP esatte
(endpoint path, payload shape) saranno completate quando A-Cube risponde con:
- Specifica OpenAPI
- Modalità onboarding consigliata (proxy/direct/appointee)
- Frequenza polling / webhook disponibilità
- Formato response (array URL XML / base64 / link firmati)

Il client estende ACubeOpenBankingClient per riusare auth JWT già implementato
(lo stesso account A-Cube copre AISP + Scarico Massivo sullo stesso token).

Docs pubbliche: https://docs.acubeapi.com/documentation/italy/gov-it/cassettofiscale
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

ACUBE_PROXY_FISCAL_ID = "10442360961"  # A-Cube P.IVA to delegate on AdE portal (proxy mode)


@dataclass
class InvoiceSummary:
    codice_univoco_sdi: str
    numero_fattura: str | None
    data_fattura: date | None
    direction: str  # active|passive
    tipo_documento: str | None
    importo_totale: float | None
    controparte_piva: str | None
    controparte_nome: str | None
    acube_id: str | None


@dataclass
class InvoiceDetail:
    summary: InvoiceSummary
    raw_xml: str | None


class ACubeScaricoMassivoClient(ACubeOpenBankingClient):
    """Client for A-Cube Cassetto Fiscale bulk invoice download.

    Inherits auth flow from ACubeOpenBankingClient (same credentials).
    """

    # ── BusinessRegistry Configuration ─────────────────────

    async def create_configuration(
        self,
        fiscal_id: str,
        mode: str = "proxy",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Create BusinessRegistryConfiguration for the client P.IVA.

        TODO: confirm exact path — probable candidates:
          POST /business-registry-configurations
          body: {"fiscalId": fiscal_id, "mode": "proxy"}
        """
        raise NotImplementedError("Waiting Ticket 02 A-Cube response")

    async def get_configuration(self, config_id: str) -> dict[str, Any]:
        """TODO: GET /business-registry-configurations/{id}"""
        raise NotImplementedError("Waiting Ticket 02 A-Cube response")

    async def set_fisconline_credentials(
        self,
        config_id: str,
        cf: str,
        password: str,
        pin: str,
    ) -> dict[str, Any]:
        """Direct mode only — store Fisconline credentials.

        TODO: PUT /business-registry-configurations/{id}/credentials/fisconline
        """
        raise NotImplementedError("Waiting Ticket 02 A-Cube response")

    # ── Invoices list / download ───────────────────────────

    async def list_invoices(
        self,
        fiscal_id: str,
        *,
        since: date | None = None,
        until: date | None = None,
        direction: str | None = None,  # active|passive|None (both)
    ) -> list[dict[str, Any]]:
        """List invoices available in the cassetto fiscale.

        TODO: confirm exact path — probable candidates:
          GET /business-registry/{fiscalId}/invoices?from=&to=&direction=
        Returns: list of invoice summaries (Hydra format expected).
        """
        raise NotImplementedError("Waiting Ticket 02 A-Cube response")

    async def get_invoice_xml(self, fiscal_id: str, invoice_id: str) -> str:
        """Download raw FatturaPA XML for a specific invoice.

        TODO: confirm if API returns:
          - direct XML string
          - signed URL that we fetch separately
          - base64-encoded content inside JSON
        """
        raise NotImplementedError("Waiting Ticket 02 A-Cube response")

    # ── Quota monitoring ───────────────────────────────────

    async def get_usage(self) -> dict[str, Any]:
        """Current consumption — useful to alert at 80% of 5.000 fatture/anno threshold.

        TODO: check if A-Cube exposes this endpoint or we track locally.
        """
        raise NotImplementedError("Waiting Ticket 02 A-Cube response")


__all__ = [
    "ACUBE_PROXY_FISCAL_ID",
    "ACubeScaricoMassivoClient",
    "ACubeAPIError",
    "ACubeAuthError",
    "InvoiceSummary",
    "InvoiceDetail",
]
