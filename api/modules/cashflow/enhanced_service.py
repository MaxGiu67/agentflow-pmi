"""Enhanced Cash Flow Agent service (US-64).

Uses real bank balance + invoices + payroll + deadlines for comprehensive cash flow.
"""

import logging
import uuid
from datetime import date, timedelta

from sqlalchemy import select, func as sqla_func
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import (
    BankAccount, Invoice, PayrollCost, FiscalDeadline, RecurringContract, Loan,
)

logger = logging.getLogger(__name__)


class EnhancedCashFlowService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_enhanced_cashflow(
        self,
        tenant_id: uuid.UUID,
        days: int = 90,
    ) -> dict:
        """Enhanced cash flow using all data sources (US-64)."""
        today = date.today()
        end_date = today + timedelta(days=days)

        # 1. Bank balance
        bank_balance = await self._get_bank_balance(tenant_id)

        # 2. Expected income (unpaid active invoices)
        expected_income = await self._get_expected_income(tenant_id, today, end_date)

        # 3. Expected expenses from passive invoices
        expected_expenses = await self._get_expected_expenses(tenant_id, today, end_date)

        # 4. Payroll costs (projected from latest month)
        payroll_monthly = await self._get_monthly_payroll(tenant_id)

        # 5. Fiscal deadlines
        deadlines = await self._get_upcoming_deadlines(tenant_id, today, end_date)

        # 6. Recurring contracts
        recurring = await self._get_recurring_costs(tenant_id, today, end_date)

        # 7. Loan installments
        loan_payments = await self._get_loan_payments(tenant_id, today, end_date)

        # Calculate totals
        months_in_period = max(1, days // 30)
        total_payroll = payroll_monthly * months_in_period
        total_deadlines = sum(d["amount"] for d in deadlines)
        total_recurring = sum(r["amount"] for r in recurring)
        total_loans = sum(ln["amount"] for ln in loan_payments)

        total_income = expected_income
        total_outflow = expected_expenses + total_payroll + total_deadlines + total_recurring + total_loans

        projected_balance = bank_balance + total_income - total_outflow

        return {
            "bank_balance": round(bank_balance, 2),
            "period_days": days,
            "expected_income": round(expected_income, 2),
            "expected_expenses": round(expected_expenses, 2),
            "payroll_monthly": round(payroll_monthly, 2),
            "payroll_total": round(total_payroll, 2),
            "deadlines_total": round(total_deadlines, 2),
            "deadlines": deadlines,
            "recurring_total": round(total_recurring, 2),
            "recurring": recurring,
            "loan_payments_total": round(total_loans, 2),
            "loan_payments": loan_payments,
            "total_income": round(total_income, 2),
            "total_outflow": round(total_outflow, 2),
            "projected_balance": round(projected_balance, 2),
            "risk_level": "critical" if projected_balance < 0 else ("warning" if projected_balance < 5000 else "ok"),
            "message": f"Cash flow potenziato: saldo proiettato a {days} giorni = {round(projected_balance, 2)} EUR",
        }

    async def _get_bank_balance(self, tenant_id: uuid.UUID) -> float:
        result = await self.db.scalar(
            select(sqla_func.coalesce(sqla_func.sum(BankAccount.balance), 0)).where(
                BankAccount.tenant_id == tenant_id,
                BankAccount.status == "connected",
            )
        )
        return float(result or 0)

    async def _get_expected_income(self, tenant_id: uuid.UUID, start: date, end: date) -> float:
        result = await self.db.scalar(
            select(sqla_func.coalesce(sqla_func.sum(Invoice.importo_totale), 0)).where(
                Invoice.tenant_id == tenant_id,
                Invoice.type == "attiva",
                Invoice.data_fattura >= start,
                Invoice.data_fattura <= end,
            )
        )
        return float(result or 0)

    async def _get_expected_expenses(self, tenant_id: uuid.UUID, start: date, end: date) -> float:
        result = await self.db.scalar(
            select(sqla_func.coalesce(sqla_func.sum(Invoice.importo_totale), 0)).where(
                Invoice.tenant_id == tenant_id,
                Invoice.type == "passiva",
                Invoice.data_fattura >= start,
                Invoice.data_fattura <= end,
            )
        )
        return float(result or 0)

    async def _get_monthly_payroll(self, tenant_id: uuid.UUID) -> float:
        result = await self.db.scalar(
            select(sqla_func.coalesce(sqla_func.sum(PayrollCost.costo_totale_azienda), 0)).where(
                PayrollCost.tenant_id == tenant_id,
            )
        )
        total = float(result or 0)
        # Get count of distinct months
        count_result = await self.db.scalar(
            select(sqla_func.count(sqla_func.distinct(PayrollCost.mese))).where(
                PayrollCost.tenant_id == tenant_id,
            )
        )
        months = int(count_result or 1) or 1
        return total / months

    async def _get_upcoming_deadlines(self, tenant_id: uuid.UUID, start: date, end: date) -> list:
        result = await self.db.execute(
            select(FiscalDeadline).where(
                FiscalDeadline.tenant_id == tenant_id,
                FiscalDeadline.due_date >= start,
                FiscalDeadline.due_date <= end,
                FiscalDeadline.status == "pending",
            )
        )
        deadlines = result.scalars().all()
        return [
            {"code": d.code, "description": d.description, "amount": d.amount, "due_date": d.due_date.isoformat()}
            for d in deadlines
        ]

    async def _get_recurring_costs(self, tenant_id: uuid.UUID, start: date, end: date) -> list:
        result = await self.db.execute(
            select(RecurringContract).where(
                RecurringContract.tenant_id == tenant_id,
                RecurringContract.status == "active",
            )
        )
        contracts = result.scalars().all()
        items = []
        for c in contracts:
            if c.next_due_date and start <= c.next_due_date <= end:
                items.append({
                    "description": c.description,
                    "amount": c.amount,
                    "next_due_date": c.next_due_date.isoformat(),
                })
        return items

    async def _get_loan_payments(self, tenant_id: uuid.UUID, start: date, end: date) -> list:
        result = await self.db.execute(
            select(Loan).where(
                Loan.tenant_id == tenant_id,
                Loan.status == "active",
            )
        )
        loans = result.scalars().all()
        items = []
        for loan in loans:
            if loan.next_payment_date and start <= loan.next_payment_date <= end:
                items.append({
                    "description": loan.description,
                    "amount": loan.installment_amount,
                    "next_payment_date": loan.next_payment_date.isoformat(),
                })
        return items
