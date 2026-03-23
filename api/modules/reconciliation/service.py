"""Service layer for invoice-transaction reconciliation (US-26)."""

import logging
import uuid
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import BankAccount, BankTransaction, Invoice, Reconciliation

logger = logging.getLogger(__name__)

# Confidence levels
CONFIDENCE_EXACT = 0.95
CONFIDENCE_AMOUNT_MATCH = 0.7
CONFIDENCE_FUZZY = 0.4

# Tolerance for amount matching
AMOUNT_TOLERANCE = 0.01  # 1 cent

# Date tolerance for matching (days)
DATE_TOLERANCE = 5

# BCE exchange rates (mock for non-EUR currencies)
BCE_EXCHANGE_RATES = {
    "USD": 1.08,
    "GBP": 0.86,
    "CHF": 0.95,
    "JPY": 162.50,
    "SEK": 11.20,
    "NOK": 11.50,
    "DKK": 7.46,
    "PLN": 4.32,
    "CZK": 25.10,
}


class ReconciliationService:
    """Business logic for invoice-transaction reconciliation."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_pending(self, tenant_id: uuid.UUID) -> dict:
        """Get unreconciled transactions with match suggestions.

        AC-26.1: Automatic match by amount + date + description -> "reconciled"
        AC-26.2: Suggestions with confidence (top 3 possible matches)
        AC-26.3: No match -> "unmatched" with options
        """
        # Get all bank accounts for tenant
        acct_result = await self.db.execute(
            select(BankAccount.id).where(BankAccount.tenant_id == tenant_id)
        )
        account_ids = [row[0] for row in acct_result.fetchall()]

        if not account_ids:
            return {"items": [], "total": 0}

        # Get unreconciled transactions
        tx_result = await self.db.execute(
            select(BankTransaction).where(
                BankTransaction.bank_account_id.in_(account_ids),
                BankTransaction.reconciled == False,
            ).order_by(BankTransaction.date.desc())
        )
        transactions = tx_result.scalars().all()

        # Check for already reconciled via Reconciliation table (dedup)
        reconciled_tx_ids: set[uuid.UUID] = set()
        recon_result = await self.db.execute(
            select(Reconciliation.transaction_id).where(
                Reconciliation.tenant_id == tenant_id,
            )
        )
        for row in recon_result.fetchall():
            reconciled_tx_ids.add(row[0])

        # Get all invoices for matching
        inv_result = await self.db.execute(
            select(Invoice).where(
                Invoice.tenant_id == tenant_id,
                Invoice.processing_status.in_(["parsed", "categorized", "registered"]),
            )
        )
        invoices = inv_result.scalars().all()

        items = []
        for tx in transactions:
            if tx.id in reconciled_tx_ids:
                continue

            suggestions = self._find_matches(tx, invoices)

            status = "suggested" if suggestions else "unmatched"

            items.append({
                "transaction_id": str(tx.id),
                "bank_transaction_id": tx.transaction_id,
                "date": tx.date.isoformat(),
                "amount": tx.amount,
                "direction": tx.direction,
                "counterpart": tx.counterpart,
                "description": tx.description,
                "currency": "EUR",
                "suggestions": suggestions[:3],  # Top 3 (AC-26.2)
                "status": status,
            })

        return {"items": items, "total": len(items)}

    async def match_transaction(
        self,
        tx_id: uuid.UUID,
        tenant_id: uuid.UUID,
        invoice_id: uuid.UUID,
        match_type: str = "manual",
        amount: float | None = None,
        currency: str | None = None,
        exchange_rate: float | None = None,
    ) -> dict:
        """Match a transaction to an invoice.

        AC-26.1: Exact match -> "riconciliati"
        AC-26.4: Foreign currency -> BCE conversion
        AC-26.5: Partial payment -> "parzialmente pagata (X/Y)"
        AC-26.6: Concurrent sync -> dedup on transaction_id
        """
        # AC-26.6: Check for duplicate reconciliation
        existing = await self.db.execute(
            select(Reconciliation).where(
                Reconciliation.transaction_id == tx_id,
                Reconciliation.tenant_id == tenant_id,
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise ValueError("Transazione gia riconciliata (dedup su transaction_id)")

        # Get the transaction
        tx = await self._get_transaction(tx_id, tenant_id)
        if not tx:
            raise ValueError("Transazione non trovata")

        # Get the invoice
        inv_result = await self.db.execute(
            select(Invoice).where(
                Invoice.id == invoice_id,
                Invoice.tenant_id == tenant_id,
            )
        )
        invoice = inv_result.scalar_one_or_none()
        if not invoice:
            raise ValueError("Fattura non trovata")

        # AC-26.4: Handle foreign currency conversion
        amount_eur = tx.amount
        original_amount = None
        original_currency = None
        rate = None

        if currency and currency != "EUR":
            if currency not in BCE_EXCHANGE_RATES:
                raise ValueError(f"Valuta {currency} non supportata")
            rate = exchange_rate or BCE_EXCHANGE_RATES[currency]
            original_amount = tx.amount
            original_currency = currency
            amount_eur = round(tx.amount / rate, 2)

        # AC-26.5: Partial payment handling
        invoice_total = invoice.importo_totale or 0.0
        matched_amount = amount if amount is not None else amount_eur
        remaining = round(invoice_total - matched_amount, 2)

        if remaining < -AMOUNT_TOLERANCE:
            raise ValueError(
                f"Importo ({matched_amount:.2f}) superiore al totale fattura ({invoice_total:.2f})"
            )

        if remaining > AMOUNT_TOLERANCE:
            recon_status = "partial"
            recon_match_type = "partial"
            confidence = CONFIDENCE_AMOUNT_MATCH
            message = (
                f"Parzialmente pagata ({matched_amount:.2f}/{invoice_total:.2f} EUR). "
                f"Rimanente: {remaining:.2f} EUR"
            )
        else:
            remaining = 0.0
            recon_status = "matched"
            recon_match_type = match_type
            confidence = CONFIDENCE_EXACT if match_type == "exact" else CONFIDENCE_AMOUNT_MATCH
            message = f"Fattura {invoice.numero_fattura} riconciliata con successo"

        # Create reconciliation record
        recon = Reconciliation(
            tenant_id=tenant_id,
            transaction_id=tx_id,
            invoice_id=invoice_id,
            match_type=recon_match_type,
            confidence=confidence,
            amount_matched=matched_amount,
            amount_remaining=remaining,
            currency="EUR",
            exchange_rate=rate,
            original_amount=original_amount,
            original_currency=original_currency,
            status=recon_status,
        )
        self.db.add(recon)

        # Mark transaction as reconciled
        tx.reconciled = True
        await self.db.flush()

        return {
            "reconciliation_id": str(recon.id),
            "transaction_id": str(tx_id),
            "invoice_id": str(invoice_id),
            "match_type": recon_match_type,
            "confidence": confidence,
            "amount_matched": matched_amount,
            "amount_remaining": remaining,
            "status": recon_status,
            "message": message,
        }

    def _find_matches(
        self, tx: BankTransaction, invoices: list[Invoice],
    ) -> list[dict]:
        """Find matching invoices for a transaction. Returns sorted by confidence."""
        matches = []

        for inv in invoices:
            confidence = 0.0
            match_type = "fuzzy"
            inv_total = inv.importo_totale or 0.0

            # Exact match: amount + date within tolerance + description/counterpart
            amount_match = abs(tx.amount - inv_total) < AMOUNT_TOLERANCE
            date_match = (
                inv.data_fattura is not None
                and abs((tx.date - inv.data_fattura).days) <= DATE_TOLERANCE
            )

            # Check description/causale match
            desc_match = False
            if tx.description and inv.numero_fattura:
                desc_match = inv.numero_fattura.lower() in tx.description.lower()
            if tx.counterpart and inv.emittente_nome:
                desc_match = desc_match or (
                    inv.emittente_nome.lower() in tx.counterpart.lower()
                )

            if amount_match and date_match and desc_match:
                confidence = CONFIDENCE_EXACT
                match_type = "exact"
            elif amount_match and (date_match or desc_match):
                confidence = CONFIDENCE_AMOUNT_MATCH
                match_type = "amount_match"
            elif amount_match or desc_match:
                confidence = CONFIDENCE_FUZZY
                match_type = "fuzzy"
            else:
                continue  # No match at all

            matches.append({
                "invoice_id": str(inv.id),
                "numero_fattura": inv.numero_fattura,
                "importo_totale": inv_total,
                "data_fattura": inv.data_fattura.isoformat() if inv.data_fattura else None,
                "emittente_nome": inv.emittente_nome,
                "confidence": confidence,
                "match_type": match_type,
            })

        # Sort by confidence descending
        matches.sort(key=lambda m: m["confidence"], reverse=True)
        return matches

    async def _get_transaction(
        self, tx_id: uuid.UUID, tenant_id: uuid.UUID,
    ) -> BankTransaction | None:
        """Get bank transaction by ID, verifying tenant ownership."""
        # Get account IDs for tenant
        acct_result = await self.db.execute(
            select(BankAccount.id).where(BankAccount.tenant_id == tenant_id)
        )
        account_ids = [row[0] for row in acct_result.fetchall()]

        if not account_ids:
            return None

        result = await self.db.execute(
            select(BankTransaction).where(
                BankTransaction.id == tx_id,
                BankTransaction.bank_account_id.in_(account_ids),
            )
        )
        return result.scalar_one_or_none()
