"""Service layer for payments via PISP (US-27)."""

import logging
import re
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import BankAccount, BankTransaction, Invoice, Payment, Reconciliation

logger = logging.getLogger(__name__)

# Italian IBAN pattern: IT + 2 check digits + 1 CIN + 5 ABI + 5 CAB + 12 account
IBAN_PATTERN = re.compile(r"^IT\d{2}[A-Z]\d{22}$")


def validate_iban(iban: str) -> bool:
    """Validate Italian IBAN format."""
    iban = iban.replace(" ", "").upper()
    if not IBAN_PATTERN.match(iban):
        return False
    return True


class PaymentService:
    """Business logic for supplier payments via PISP."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def execute_payment(
        self,
        tenant_id: uuid.UUID,
        bank_account_id: uuid.UUID,
        invoice_id: uuid.UUID,
        beneficiary_name: str,
        beneficiary_iban: str,
        amount: float,
        causale: str | None = None,
    ) -> dict:
        """Execute a single payment via PISP with SCA.

        AC-27.1: Pagamento con SCA -> via A-Cube PISP, registra uscita, riconcilia.
        AC-27.2: Fondi insufficienti -> errore con saldo.
        AC-27.3: IBAN non valido -> errore validazione.
        """
        # AC-27.3: Validate IBAN
        if not validate_iban(beneficiary_iban):
            raise ValueError(
                f"IBAN non valido: {beneficiary_iban}. "
                "Formato atteso: IT + 2 cifre di controllo + CIN + ABI + CAB + conto (27 caratteri)"
            )

        # Get bank account
        account = await self._get_bank_account(bank_account_id, tenant_id)
        if not account:
            raise ValueError("Conto bancario non trovato")

        # AC-27.2: Check balance
        balance = account.balance or 0.0
        if balance < amount:
            return {
                "error": "fondi_insufficienti",
                "detail": (
                    f"Fondi insufficienti. Saldo disponibile: {balance:.2f} EUR, "
                    f"importo richiesto: {amount:.2f} EUR"
                ),
                "saldo_disponibile": balance,
            }

        # Get invoice for causale
        inv_result = await self.db.execute(
            select(Invoice).where(Invoice.id == invoice_id)
        )
        invoice = inv_result.scalar_one_or_none()
        if not invoice:
            raise ValueError("Fattura non trovata")

        if not causale:
            causale = f"Pagamento fattura {invoice.numero_fattura}"

        # AC-27.1: Mock SCA flow and execute payment
        payment = Payment(
            tenant_id=tenant_id,
            bank_account_id=bank_account_id,
            invoice_ids=[str(invoice_id)],
            beneficiary_name=beneficiary_name,
            beneficiary_iban=beneficiary_iban,
            amount=amount,
            causale=causale,
            payment_type="single",
            sca_status="completed",
            reconciled=True,
        )
        self.db.add(payment)

        # Update bank account balance
        account.balance = round(balance - amount, 2)

        # Create bank transaction for the outgoing payment
        tx = BankTransaction(
            bank_account_id=bank_account_id,
            transaction_id=f"PISP-{uuid.uuid4().hex[:8].upper()}",
            date=invoice.data_fattura or __import__("datetime").date.today(),
            amount=amount,
            direction="debit",
            counterpart=beneficiary_name,
            description=causale,
            reconciled=True,
        )
        self.db.add(tx)
        await self.db.flush()

        # Create reconciliation
        reconciliation = Reconciliation(
            tenant_id=tenant_id,
            transaction_id=tx.id,
            invoice_id=invoice_id,
            match_type="exact",
            confidence=1.0,
            amount_matched=amount,
            amount_remaining=0.0,
            status="matched",
        )
        self.db.add(reconciliation)
        await self.db.flush()

        return {
            "id": str(payment.id),
            "tenant_id": str(payment.tenant_id),
            "bank_account_id": str(payment.bank_account_id),
            "beneficiary_name": payment.beneficiary_name,
            "beneficiary_iban": payment.beneficiary_iban,
            "amount": payment.amount,
            "causale": payment.causale,
            "payment_type": payment.payment_type,
            "sca_status": payment.sca_status,
            "error_message": payment.error_message,
            "reconciled": payment.reconciled,
        }

    async def execute_batch_payment(
        self,
        tenant_id: uuid.UUID,
        bank_account_id: uuid.UUID,
        beneficiary_name: str,
        beneficiary_iban: str,
        invoice_ids: list[uuid.UUID],
    ) -> dict:
        """Execute a batch payment for multiple invoices.

        AC-27.4: Pagamento batch -> bonifico cumulativo con causale che elenca numeri fattura.
        """
        # AC-27.3: Validate IBAN
        if not validate_iban(beneficiary_iban):
            raise ValueError(
                f"IBAN non valido: {beneficiary_iban}. "
                "Formato atteso: IT + 2 cifre di controllo + CIN + ABI + CAB + conto (27 caratteri)"
            )

        # Get bank account
        account = await self._get_bank_account(bank_account_id, tenant_id)
        if not account:
            raise ValueError("Conto bancario non trovato")

        # Get all invoices
        invoices: list[Invoice] = []
        total_amount = 0.0
        numeri_fattura: list[str] = []

        for inv_id in invoice_ids:
            inv_result = await self.db.execute(
                select(Invoice).where(Invoice.id == inv_id)
            )
            inv = inv_result.scalar_one_or_none()
            if not inv:
                raise ValueError(f"Fattura {inv_id} non trovata")
            invoices.append(inv)
            total_amount += inv.importo_totale or 0.0
            numeri_fattura.append(inv.numero_fattura)

        total_amount = round(total_amount, 2)

        # AC-27.2: Check balance
        balance = account.balance or 0.0
        if balance < total_amount:
            return {
                "error": "fondi_insufficienti",
                "detail": (
                    f"Fondi insufficienti. Saldo disponibile: {balance:.2f} EUR, "
                    f"importo richiesto: {total_amount:.2f} EUR"
                ),
                "saldo_disponibile": balance,
            }

        # AC-27.4: Build causale with invoice numbers
        causale = f"Pagamento fatture: {', '.join(numeri_fattura)}"

        # Execute cumulative payment
        payment = Payment(
            tenant_id=tenant_id,
            bank_account_id=bank_account_id,
            invoice_ids=[str(iid) for iid in invoice_ids],
            beneficiary_name=beneficiary_name,
            beneficiary_iban=beneficiary_iban,
            amount=total_amount,
            causale=causale,
            payment_type="batch",
            sca_status="completed",
            reconciled=True,
        )
        self.db.add(payment)

        # Update balance
        account.balance = round(balance - total_amount, 2)

        # Create bank transaction
        tx = BankTransaction(
            bank_account_id=bank_account_id,
            transaction_id=f"PISP-BATCH-{uuid.uuid4().hex[:8].upper()}",
            date=__import__("datetime").date.today(),
            amount=total_amount,
            direction="debit",
            counterpart=beneficiary_name,
            description=causale,
            reconciled=True,
        )
        self.db.add(tx)
        await self.db.flush()

        # Create reconciliations for each invoice
        for inv in invoices:
            recon = Reconciliation(
                tenant_id=tenant_id,
                transaction_id=tx.id,
                invoice_id=inv.id,
                match_type="exact",
                confidence=1.0,
                amount_matched=inv.importo_totale or 0.0,
                amount_remaining=0.0,
                status="matched",
            )
            self.db.add(recon)

        await self.db.flush()

        return {
            "payment": {
                "id": str(payment.id),
                "tenant_id": str(payment.tenant_id),
                "bank_account_id": str(payment.bank_account_id),
                "beneficiary_name": payment.beneficiary_name,
                "beneficiary_iban": payment.beneficiary_iban,
                "amount": payment.amount,
                "causale": payment.causale,
                "payment_type": payment.payment_type,
                "sca_status": payment.sca_status,
                "error_message": payment.error_message,
                "reconciled": payment.reconciled,
            },
            "invoice_count": len(invoices),
            "total_amount": total_amount,
            "causale": causale,
        }

    async def _get_bank_account(
        self,
        account_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> BankAccount | None:
        """Get bank account by ID and tenant."""
        result = await self.db.execute(
            select(BankAccount).where(
                BankAccount.id == account_id,
                BankAccount.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()
