"""Preservation adapter for digital preservation providers (US-37).

Mock implementations for Aruba and InfoCert providers.
"""

import hashlib
import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PreservationSendResult:
    """Result from sending a document to preservation."""
    batch_id: str
    package_hash: str
    status: str  # sent, error
    message: str


@dataclass
class PreservationStatusResult:
    """Result from checking preservation status."""
    batch_id: str
    status: str  # sent, confirmed, rejected
    reject_reason: str | None = None


class PreservationAdapter(ABC):
    """Abstract adapter for digital preservation providers."""

    @abstractmethod
    async def send_document(
        self, document_content: str, document_id: str,
    ) -> PreservationSendResult:
        """Send a document for preservation."""
        ...

    @abstractmethod
    async def check_status(self, batch_id: str) -> PreservationStatusResult:
        """Check preservation status."""
        ...

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the provider is reachable."""
        ...


class MockArubaPreservationAdapter(PreservationAdapter):
    """Mock Aruba preservation adapter."""

    def __init__(self) -> None:
        self._available: bool = True
        self._simulate_rejection: bool = False
        self._reject_reason: str | None = None

    def set_available(self, available: bool) -> None:
        """For testing: control provider availability."""
        self._available = available

    def set_simulate_rejection(self, reject: bool, reason: str | None = None) -> None:
        """For testing: simulate rejection."""
        self._simulate_rejection = reject
        self._reject_reason = reason

    async def send_document(
        self, document_content: str, document_id: str,
    ) -> PreservationSendResult:
        """Send document to mock Aruba preservation."""
        if not self._available:
            raise ConnectionError("Provider Aruba non raggiungibile")

        batch_id = f"ARUBA-{uuid.uuid4().hex[:8].upper()}"
        package_hash = hashlib.sha256(document_content.encode()).hexdigest()

        logger.info("Mock Aruba: document %s sent (batch %s)", document_id, batch_id)

        return PreservationSendResult(
            batch_id=batch_id,
            package_hash=package_hash,
            status="sent",
            message="Documento inviato a conservazione Aruba",
        )

    async def check_status(self, batch_id: str) -> PreservationStatusResult:
        """Check mock Aruba preservation status."""
        if not self._available:
            raise ConnectionError("Provider Aruba non raggiungibile")

        if self._simulate_rejection:
            return PreservationStatusResult(
                batch_id=batch_id,
                status="rejected",
                reject_reason=self._reject_reason or "Formato non conforme",
            )

        return PreservationStatusResult(
            batch_id=batch_id,
            status="confirmed",
        )

    async def is_available(self) -> bool:
        """Check mock Aruba availability."""
        return self._available


class MockInfoCertPreservationAdapter(PreservationAdapter):
    """Mock InfoCert preservation adapter."""

    def __init__(self) -> None:
        self._available: bool = True
        self._simulate_rejection: bool = False
        self._reject_reason: str | None = None

    def set_available(self, available: bool) -> None:
        self._available = available

    def set_simulate_rejection(self, reject: bool, reason: str | None = None) -> None:
        self._simulate_rejection = reject
        self._reject_reason = reason

    async def send_document(
        self, document_content: str, document_id: str,
    ) -> PreservationSendResult:
        if not self._available:
            raise ConnectionError("Provider InfoCert non raggiungibile")

        batch_id = f"INFOCERT-{uuid.uuid4().hex[:8].upper()}"
        package_hash = hashlib.sha256(document_content.encode()).hexdigest()

        return PreservationSendResult(
            batch_id=batch_id,
            package_hash=package_hash,
            status="sent",
            message="Documento inviato a conservazione InfoCert",
        )

    async def check_status(self, batch_id: str) -> PreservationStatusResult:
        if not self._available:
            raise ConnectionError("Provider InfoCert non raggiungibile")

        if self._simulate_rejection:
            return PreservationStatusResult(
                batch_id=batch_id,
                status="rejected",
                reject_reason=self._reject_reason or "Pacchetto non valido",
            )

        return PreservationStatusResult(
            batch_id=batch_id,
            status="confirmed",
        )

    async def is_available(self) -> bool:
        return self._available
