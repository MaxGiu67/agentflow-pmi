"""Auto-match reconciliation service (US-72).

Auto-matches bank transactions to invoices by amount/date.
"""

import logging
import uuid
from datetime import timedelta

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import BankTransaction, BankAccount, Invoice, Reconciliation

logger = logging.getLogger(__name__)

# Tolerance for amount matching
AMOUNT_TOLERANCE = 0.50  # EUR
DATE_TOLERANCE_DAYS = 5


class AutoMatchService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def auto_match(self, tenant_id: uuid.UUID) -> dict:
        """Auto-match unreconciled bank transactions to invoices (US-72)."""
        # Get bank accounts for tenant
        accounts_result = await self.db.execute(
            select(BankAccount.id).where(BankAccount.tenant_id == tenant_id)
        )
        account_ids = [row[0] for row in accounts_result.fetchall()]

        if not account_ids:
            return {
                "matched": 0,
                "unmatched": 0,
                "matches": [],
                "message": "Nessun conto bancario trovato",
            }

        # Get unreconciled transactions
        tx_result = await self.db.execute(
            select(BankTransaction).where(
                BankTransaction.bank_account_id.in_(account_ids),
                BankTransaction.reconciled == False,
            )
        )
        transactions = tx_result.scalars().all()

        # Get unreconciled invoices
        inv_result = await self.db.execute(
            select(Invoice).where(
                Invoice.tenant_id == tenant_id,
            )
        )
        invoices = inv_result.scalars().all()

        matches = []
        matched_invoice_ids = set()

        for tx in transactions:
            best_match = None
            best_confidence = 0.0

            for inv in invoices:
                if inv.id in matched_invoice_ids:
                    continue

                confidence = self._calculate_match_confidence(tx, inv)
                if confidence > best_confidence and confidence >= 0.7:
                    best_confidence = confidence
                    best_match = inv

            if best_match:
                # Create reconciliation record
                rec = Reconciliation(
                    tenant_id=tenant_id,
                    transaction_id=tx.id,
                    invoice_id=best_match.id,
                    match_type="exact" if best_confidence >= 0.95 else "fuzzy",
                    confidence=best_confidence,
                    amount_matched=abs(tx.amount),
                    amount_remaining=0.0,
                    status="matched",
                )
                self.db.add(rec)

                tx.reconciled = True
                matched_invoice_ids.add(best_match.id)

                matches.append({
                    "transaction_id": str(tx.id),
                    "invoice_id": str(best_match.id),
                    "amount": abs(tx.amount),
                    "confidence": round(best_confidence, 2),
                    "match_type": rec.match_type,
                })

        await self.db.flush()

        return {
            "matched": len(matches),
            "unmatched": len(transactions) - len(matches),
            "matches": matches,
            "message": f"Auto-riconciliazione: {len(matches)} movimenti abbinati su {len(transactions)} totali",
        }

    def _calculate_match_confidence(self, tx: BankTransaction, inv: Invoice) -> float:
        """Calculate confidence score for a transaction-invoice match."""
        score = 0.0

        # Amount match (most important)
        if inv.importo_totale is not None:
            amount_diff = abs(abs(tx.amount) - inv.importo_totale)
            if amount_diff <= 0.01:
                score += 0.6
            elif amount_diff <= AMOUNT_TOLERANCE:
                score += 0.4
            elif amount_diff <= 5.0:
                score += 0.2
            else:
                return 0.0  # Too different

        # Date proximity
        if inv.data_fattura and tx.date:
            date_diff = abs((tx.date - inv.data_fattura).days)
            if date_diff <= DATE_TOLERANCE_DAYS:
                score += 0.3
            elif date_diff <= 30:
                score += 0.15
            elif date_diff <= 90:
                score += 0.05

        # Direction match
        if tx.direction == "debit" and inv.type == "passiva":
            score += 0.1
        elif tx.direction == "credit" and inv.type == "attiva":
            score += 0.1

        return min(score, 1.0)
