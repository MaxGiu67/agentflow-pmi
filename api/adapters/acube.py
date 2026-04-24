"""A-Cube SDI adapter for sending active invoices (US-21).

Now backed by the real A-Cube E-Invoicing Italy REST API (api/adapters/acube_einvoicing.py).
Falls back to a deterministic mock when A-Cube credentials are not configured,
so unit tests still work without live A-Cube access.
"""

import logging
import os
import uuid as _uuid
from dataclasses import dataclass

from api.adapters.acube_einvoicing import (
    ACubeAPIError,
    ACubeAuthError,
    ACubeEInvoicingClient,
    MARKING_DELIVERED,
    MARKING_REJECTED,
    MARKING_SENT,
    MARKING_WAITING,
)

logger = logging.getLogger(__name__)


@dataclass
class ACubeSendResult:
    """Result from sending an invoice to SDI via A-Cube."""
    sdi_id: str
    status: str  # sent, error
    message: str


@dataclass
class ACubeStatusResult:
    """Result from checking SDI delivery status."""
    sdi_id: str
    status: str  # sent, delivered, rejected
    reject_reason: str | None = None


_MARKING_TO_STATUS = {
    MARKING_WAITING: "sent",
    MARKING_SENT: "sent",
    MARKING_DELIVERED: "delivered",
    "accepted": "delivered",
    MARKING_REJECTED: "rejected",
    "refused": "rejected",
    "not_delivered": "not_delivered",
    "expired": "delivered",
}


class ACubeSDIAdapter:
    """Adapter for A-Cube SDI invoice sending.

    Tries the real client first; if A-Cube is not configured (no credentials),
    returns deterministic mock responses so existing unit tests keep passing.
    """

    def __init__(self, base_url: str | None = None) -> None:
        self._client = ACubeEInvoicingClient()
        self._simulate_rejection = False
        self._reject_reason: str | None = None
        # Force mock mode for tests even if credentials are set
        self._force_mock = os.getenv("ACUBE_EINVOICING_MOCK", "").lower() in ("1", "true", "yes")

    @property
    def _use_real(self) -> bool:
        return self._client.enabled and not self._force_mock

    def set_simulate_rejection(self, reject: bool, reason: str | None = None) -> None:
        """For testing: simulate SDI rejection (only affects mock path)."""
        self._simulate_rejection = reject
        self._reject_reason = reason

    async def send_invoice(self, xml_content: str, tenant_piva: str) -> ACubeSendResult:
        """Send FatturaPA XML to SDI via A-Cube.

        Real mode: POST /invoices — A-Cube signs server-side (CAdES-BES) and forwards to SDI.
        Mock mode: returns a random SDI ID without network call.
        """
        if not xml_content:
            raise ValueError("XML fattura vuoto")

        if not self._use_real:
            # Fallback mock — keeps tests green when credentials aren't set or ACUBE_EINVOICING_MOCK=true
            sdi_id = f"SDI-MOCK-{_uuid.uuid4().hex[:8].upper()}"
            logger.warning("A-Cube mock send_invoice (piva=%s, forced=%s)", tenant_piva, self._force_mock)
            return ACubeSendResult(
                sdi_id=sdi_id,
                status="sent",
                message="[MOCK] A-Cube non configurato — nessun invio reale",
            )

        try:
            result = await self._client.send_invoice_xml(xml_content)
        except (ACubeAPIError, ACubeAuthError) as e:
            logger.error("A-Cube real send failed (piva=%s): %s", tenant_piva, e)
            return ACubeSendResult(
                sdi_id="",
                status="error",
                message=f"Errore A-Cube: {e}",
            )

        return ACubeSendResult(
            sdi_id=result.uuid,
            status="sent",
            message=f"Fattura inviata ad A-Cube (marking={result.marking})",
        )

    async def get_delivery_status(self, sdi_id: str) -> ACubeStatusResult:
        """Check delivery status of a sent invoice.

        Real mode: GET /invoices/{uuid} — returns current marking.
        Mock mode: returns 'delivered' (or 'rejected' if simulated).
        """
        if not self._use_real or sdi_id.startswith("SDI-MOCK-"):
            if self._simulate_rejection:
                return ACubeStatusResult(
                    sdi_id=sdi_id,
                    status="rejected",
                    reject_reason=self._reject_reason or "Codice destinatario non valido",
                )
            return ACubeStatusResult(sdi_id=sdi_id, status="delivered")

        try:
            status = await self._client.get_invoice(sdi_id)
        except (ACubeAPIError, ACubeAuthError) as e:
            logger.error("A-Cube real status failed (sdi_id=%s): %s", sdi_id, e)
            return ACubeStatusResult(sdi_id=sdi_id, status="sent")

        mapped = _MARKING_TO_STATUS.get(status.marking, "sent")
        return ACubeStatusResult(
            sdi_id=sdi_id,
            status=mapped,
            reject_reason=status.rejection_reason if mapped == "rejected" else None,
        )
