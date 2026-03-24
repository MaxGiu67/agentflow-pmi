"""Banking adapter for Open Banking AISP via A-Cube / CBI Globe (US-24).

Provides abstract BankingAdapter and mock implementation for testing.
Production adapter will connect to A-Cube's Open Banking endpoints.
"""

import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, UTC

logger = logging.getLogger(__name__)

# Italian banks available on CBI Globe
CBI_GLOBE_BANKS = {
    "IT": [
        "Intesa Sanpaolo",
        "UniCredit",
        "Banco BPM",
        "BPER Banca",
        "Mediobanca",
        "Monte dei Paschi di Siena",
        "Credem",
        "Banca Popolare di Sondrio",
    ]
}


@dataclass
class SCAFlowResult:
    """Result from initiating SCA (Strong Customer Authentication) flow."""
    consent_token: str
    consent_expires_at: datetime
    redirect_url: str
    bank_name: str


@dataclass
class AccountInfo:
    """Bank account information."""
    iban: str
    bank_name: str
    balance: float
    currency: str = "EUR"


@dataclass
class TransactionInfo:
    """Bank transaction data."""
    transaction_id: str
    date: date
    amount: float
    direction: str  # credit, debit
    counterpart: str | None = None
    description: str | None = None


class BankingAdapter(ABC):
    """Abstract adapter for Open Banking AISP operations."""

    @abstractmethod
    async def init_sca_flow(self, iban: str) -> SCAFlowResult:
        """Initiate SCA flow to connect a bank account."""
        ...

    @abstractmethod
    async def get_account_info(self, consent_token: str, iban: str) -> AccountInfo:
        """Get account information and balance."""
        ...

    @abstractmethod
    async def get_transactions(
        self, consent_token: str, iban: str, from_date: date | None = None,
    ) -> list[TransactionInfo]:
        """Get account transactions."""
        ...

    @abstractmethod
    async def revoke_consent(self, consent_token: str) -> bool:
        """Revoke PSD2 consent."""
        ...

    @abstractmethod
    def is_bank_supported(self, iban: str) -> bool:
        """Check if the bank for this IBAN is supported on CBI Globe."""
        ...


class MockBankingAdapter(BankingAdapter):
    """Mock implementation for testing and development."""

    def __init__(self) -> None:
        self._unsupported_ibans: set[str] = set()

    def set_unsupported(self, iban: str) -> None:
        """Mark an IBAN as unsupported (for testing)."""
        self._unsupported_ibans.add(iban)

    async def init_sca_flow(self, iban: str) -> SCAFlowResult:
        """Initiate mock SCA flow."""
        if not self.is_bank_supported(iban):
            raise ValueError(
                f"Banca non supportata su CBI Globe per IBAN {iban}. "
                "Suggerimento: utilizza l'upload manuale dei movimenti."
            )

        consent_token = f"consent-{uuid.uuid4().hex[:12]}"
        expires_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(days=90)

        logger.info("Mock SCA flow initiated for IBAN %s", iban)

        return SCAFlowResult(
            consent_token=consent_token,
            consent_expires_at=expires_at,
            redirect_url=f"https://mock-bank.example.com/sca?iban={iban}",
            bank_name=self._resolve_bank_name(iban),
        )

    async def get_account_info(self, consent_token: str, iban: str) -> AccountInfo:
        """Get mock account info."""
        return AccountInfo(
            iban=iban,
            bank_name=self._resolve_bank_name(iban),
            balance=15420.50,
        )

    async def get_transactions(
        self, consent_token: str, iban: str, from_date: date | None = None,
    ) -> list[TransactionInfo]:
        """Get mock transactions."""
        base = from_date or (date.today() - timedelta(days=90))
        transactions = []
        for i in range(5):
            tx_date = base + timedelta(days=i * 7)
            if tx_date > date.today():
                break
            transactions.append(
                TransactionInfo(
                    transaction_id=f"TX-{uuid.uuid4().hex[:8]}",
                    date=tx_date,
                    amount=round(500.0 + i * 100, 2),
                    direction="credit" if i % 2 == 0 else "debit",
                    counterpart=f"Controparte {i + 1} SRL",
                    description=f"Pagamento fattura #{1000 + i}",
                )
            )
        return transactions

    async def revoke_consent(self, consent_token: str) -> bool:
        """Revoke mock consent."""
        logger.info("Mock consent revoked: %s", consent_token)
        return True

    def is_bank_supported(self, iban: str) -> bool:
        """Check if IBAN is for a supported bank."""
        if iban in self._unsupported_ibans:
            return False
        # Italian IBANs start with IT
        if not iban.startswith("IT"):
            return False
        return True

    def _resolve_bank_name(self, iban: str) -> str:
        """Resolve bank name from IBAN (mock)."""
        if iban.startswith("IT"):
            # Use ABI code (chars 5-9) to mock bank name
            abi = iban[5:10] if len(iban) >= 10 else "00000"
            bank_idx = int(abi) % len(CBI_GLOBE_BANKS["IT"])
            return CBI_GLOBE_BANKS["IT"][bank_idx]
        return "Banca Estera"
