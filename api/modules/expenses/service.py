"""Service layer for expense management (US-29, US-30)."""

import logging
import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import Expense, ExpensePolicy, User

logger = logging.getLogger(__name__)

# OCR category mapping (simulated)
OCR_CATEGORY_MAP: dict[str, tuple[str, float]] = {
    "ristorante": ("Pranzo", 0.90),
    "trattoria": ("Pranzo", 0.88),
    "bar": ("Pranzo", 0.75),
    "pizzeria": ("Pranzo", 0.85),
    "hotel": ("Alloggio", 0.92),
    "albergo": ("Alloggio", 0.90),
    "taxi": ("Trasporto", 0.88),
    "uber": ("Trasporto", 0.85),
    "treno": ("Trasporto", 0.90),
    "trenitalia": ("Trasporto", 0.92),
    "italo": ("Trasporto", 0.92),
    "autostrada": ("Trasporto", 0.87),
    "benzina": ("Carburante", 0.90),
    "carburante": ("Carburante", 0.92),
    "eni": ("Carburante", 0.80),
    "parcheggio": ("Trasporto", 0.82),
    "farmacia": ("Altro", 0.70),
    "cancelleria": ("Materiale ufficio", 0.85),
}

# BCE exchange rates (simulated, frozen for deterministic tests)
BCE_EXCHANGE_RATES: dict[str, float] = {
    "USD": 1.08,
    "GBP": 0.86,
    "CHF": 0.97,
    "JPY": 163.50,
    "SEK": 11.20,
    "NOK": 11.50,
    "DKK": 7.46,
    "PLN": 4.32,
    "CZK": 25.10,
    "HUF": 395.00,
    "RON": 4.98,
    "BGN": 1.96,
    "HRK": 7.53,
    "EUR": 1.0,
}


class ExpenseService:
    """Business logic for expense management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_expense(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        description: str,
        amount: float,
        expense_date: date,
        currency: str = "EUR",
        category: str | None = None,
        receipt_file: str | None = None,
        ocr_text: str | None = None,
    ) -> dict:
        """Create an expense entry.

        AC-29.1: Upload receipt -> OCR -> propose category
        AC-29.2: Policy check (max amount per category)
        AC-29.3: Unreadable receipt -> manual entry
        AC-29.4: Foreign currency -> BCE conversion
        """
        # AC-29.1: OCR category proposal
        proposed_category = category
        category_confidence: float | None = None
        ocr_readable = True

        if ocr_text:
            cat_result = self._propose_category_from_ocr(ocr_text)
            if cat_result:
                proposed_category = cat_result[0]
                category_confidence = cat_result[1]
            else:
                # AC-29.3: Unreadable receipt
                ocr_readable = False
        elif receipt_file:
            # No OCR text provided with receipt file -> unreadable
            ocr_readable = False

        if category:
            proposed_category = category
            category_confidence = 1.0

        # AC-29.4: Foreign currency conversion
        amount_eur = amount
        exchange_rate: float | None = None
        if currency != "EUR":
            rate = BCE_EXCHANGE_RATES.get(currency)
            if rate is None:
                raise ValueError(f"Valuta {currency} non supportata per conversione BCE")
            exchange_rate = rate
            amount_eur = round(amount / rate, 2)

        # AC-29.2: Policy check
        policy_warning = await self._check_policy(
            tenant_id, proposed_category, amount_eur,
        )

        expense = Expense(
            tenant_id=tenant_id,
            user_id=user_id,
            description=description,
            amount=amount,
            currency=currency,
            amount_eur=amount_eur,
            exchange_rate=exchange_rate,
            category=proposed_category,
            category_confidence=category_confidence,
            receipt_file=receipt_file,
            ocr_text=ocr_text,
            ocr_readable=ocr_readable,
            expense_date=expense_date,
            policy_warning=policy_warning,
            status="submitted",
        )
        self.db.add(expense)
        await self.db.flush()

        return self._expense_to_dict(expense)

    async def list_expenses(self, tenant_id: uuid.UUID) -> dict:
        """List all expenses for tenant."""
        result = await self.db.execute(
            select(Expense)
            .where(Expense.tenant_id == tenant_id)
            .order_by(Expense.created_at.desc())
        )
        items = result.scalars().all()
        return {
            "items": [self._expense_to_dict(e) for e in items],
            "total": len(items),
        }

    async def approve_expense(
        self,
        expense_id: uuid.UUID,
        tenant_id: uuid.UUID,
        approver_id: uuid.UUID,
    ) -> dict:
        """Approve an expense.

        AC-30.1: DARE Trasferte / AVERE Debiti dipendenti
        AC-30.5: Auto-approval for sole owner (BR-10)
        """
        expense = await self._get_expense(expense_id, tenant_id)

        if expense.status != "submitted":
            raise ValueError(f"Spesa in stato '{expense.status}', non approvabile")

        expense.status = "approved"
        expense.approved_by = approver_id

        # AC-30.1: Journal entry
        journal_entry = {
            "description": f"Nota spese approvata: {expense.description}",
            "lines": [
                {
                    "account_code": "6300",
                    "account_name": "Spese di trasferta",
                    "debit": expense.amount_eur,
                    "credit": 0.0,
                },
                {
                    "account_code": "2040",
                    "account_name": "Debiti verso dipendenti",
                    "debit": 0.0,
                    "credit": expense.amount_eur,
                },
            ],
        }

        await self.db.flush()

        result = self._expense_to_dict(expense)
        result["journal_entry"] = journal_entry
        return result

    async def reject_expense(
        self,
        expense_id: uuid.UUID,
        tenant_id: uuid.UUID,
        reason: str,
    ) -> dict:
        """Reject an expense with motivation.

        AC-30.3: Rejection with reason -> notification to employee
        """
        expense = await self._get_expense(expense_id, tenant_id)

        if expense.status != "submitted":
            raise ValueError(f"Spesa in stato '{expense.status}', non rifiutabile")

        expense.status = "rejected"
        expense.rejection_reason = reason

        await self.db.flush()

        return self._expense_to_dict(expense)

    async def reimburse_expense(
        self,
        expense_id: uuid.UUID,
        tenant_id: uuid.UUID,
        payment_method: str = "pisp",
        simulate_failure: bool = False,
    ) -> dict:
        """Reimburse an approved expense.

        AC-30.2: DARE Debiti dipendenti / AVERE Banca
        AC-30.4: PISP failure -> status 'reimburse_failed'
        """
        expense = await self._get_expense(expense_id, tenant_id)

        if expense.status != "approved":
            raise ValueError(f"Spesa in stato '{expense.status}', non rimborsabile")

        if simulate_failure:
            # AC-30.4: PISP failure
            expense.status = "reimburse_failed"
            await self.db.flush()
            return {
                "expense_id": str(expense.id),
                "status": "reimburse_failed",
                "journal_entry": None,
                "message": "Rimborso PISP fallito. Riprovare o procedere manualmente.",
            }

        expense.status = "reimbursed"

        # AC-30.2: Journal entry
        journal_entry = {
            "description": f"Rimborso nota spese: {expense.description}",
            "lines": [
                {
                    "account_code": "2040",
                    "account_name": "Debiti verso dipendenti",
                    "debit": expense.amount_eur,
                    "credit": 0.0,
                },
                {
                    "account_code": "1010",
                    "account_name": "Banca c/c",
                    "debit": 0.0,
                    "credit": expense.amount_eur,
                },
            ],
        }

        await self.db.flush()

        return {
            "expense_id": str(expense.id),
            "status": "reimbursed",
            "journal_entry": journal_entry,
            "message": "Rimborso effettuato con successo.",
        }

    async def check_auto_approval(
        self, tenant_id: uuid.UUID, user_id: uuid.UUID,
    ) -> bool:
        """AC-30.5: Check if user is sole owner (BR-10) for auto-approval."""
        result = await self.db.execute(
            select(func.count(User.id)).where(
                User.tenant_id == tenant_id,
                User.role == "owner",
            )
        )
        owner_count = result.scalar() or 0
        return owner_count == 1

    async def _get_expense(
        self, expense_id: uuid.UUID, tenant_id: uuid.UUID,
    ) -> Expense:
        """Get expense by id and tenant."""
        result = await self.db.execute(
            select(Expense).where(
                Expense.id == expense_id,
                Expense.tenant_id == tenant_id,
            )
        )
        expense = result.scalar_one_or_none()
        if not expense:
            raise ValueError("Nota spese non trovata")
        return expense

    async def _check_policy(
        self,
        tenant_id: uuid.UUID,
        category: str | None,
        amount_eur: float,
    ) -> str | None:
        """AC-29.2: Check expense against policy rules."""
        if not category:
            return None

        result = await self.db.execute(
            select(ExpensePolicy).where(
                ExpensePolicy.tenant_id == tenant_id,
                ExpensePolicy.category == category,
                ExpensePolicy.active == True,  # noqa: E712
            )
        )
        policy = result.scalar_one_or_none()
        if not policy:
            return None

        if amount_eur > policy.max_amount:
            return (
                f"Importo {amount_eur:.2f} EUR supera il limite di "
                f"{policy.max_amount:.2f} EUR per categoria '{category}'"
            )
        return None

    def _propose_category_from_ocr(
        self, ocr_text: str,
    ) -> tuple[str, float] | None:
        """AC-29.1: Propose category from OCR text."""
        text_lower = ocr_text.lower()
        best_match: tuple[str, float] | None = None

        for keyword, (cat, conf) in OCR_CATEGORY_MAP.items():
            if keyword in text_lower:
                if best_match is None or conf > best_match[1]:
                    best_match = (cat, conf)

        return best_match

    @staticmethod
    def _expense_to_dict(expense: Expense) -> dict:
        """Convert expense model to dict."""
        return {
            "id": str(expense.id),
            "tenant_id": str(expense.tenant_id),
            "user_id": str(expense.user_id),
            "description": expense.description,
            "amount": expense.amount,
            "currency": expense.currency,
            "amount_eur": expense.amount_eur,
            "exchange_rate": expense.exchange_rate,
            "category": expense.category,
            "category_confidence": expense.category_confidence,
            "receipt_file": expense.receipt_file,
            "ocr_readable": expense.ocr_readable,
            "expense_date": expense.expense_date.isoformat() if expense.expense_date else None,
            "policy_warning": expense.policy_warning,
            "status": expense.status,
            "approved_by": str(expense.approved_by) if expense.approved_by else None,
            "rejection_reason": expense.rejection_reason,
            "journal_entry": None,
        }
