"""A-Cube SDI adapter for sending active invoices (US-21).

In production this calls the real A-Cube REST API.
For testing, the adapter returns mock responses.
"""

import logging
import uuid
from dataclasses import dataclass

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


class ACubeSDIAdapter:
    """Adapter for A-Cube SDI invoice sending.

    Mock implementation for MVP; production will call
    A-Cube REST API (OpenAPI 3.0).
    """

    def __init__(self, base_url: str = "https://api.acube.it") -> None:
        self.base_url = base_url
        self._simulate_rejection = False
        self._reject_reason: str | None = None

    def set_simulate_rejection(self, reject: bool, reason: str | None = None) -> None:
        """For testing: simulate SDI rejection."""
        self._simulate_rejection = reject
        self._reject_reason = reason

    async def send_invoice(self, xml_content: str, tenant_piva: str) -> ACubeSendResult:
        """Send FatturaPA XML to SDI via A-Cube.

        Args:
            xml_content: FatturaPA XML string.
            tenant_piva: Sender's P.IVA.

        Returns:
            ACubeSendResult with sdi_id and status.
        """
        if not xml_content:
            raise ValueError("XML fattura vuoto")

        sdi_id = f"SDI-{uuid.uuid4().hex[:8].upper()}"

        logger.info("Sending invoice to SDI via A-Cube (tenant P.IVA: %s)", tenant_piva)

        return ACubeSendResult(
            sdi_id=sdi_id,
            status="sent",
            message="Fattura inviata a SDI con successo",
        )

    async def get_delivery_status(self, sdi_id: str) -> ACubeStatusResult:
        """Check delivery status of a sent invoice.

        Args:
            sdi_id: SDI identifier returned from send_invoice.

        Returns:
            ACubeStatusResult with current status.
        """
        if self._simulate_rejection:
            return ACubeStatusResult(
                sdi_id=sdi_id,
                status="rejected",
                reject_reason=self._reject_reason or "Codice destinatario non valido",
            )

        return ACubeStatusResult(
            sdi_id=sdi_id,
            status="delivered",
        )
