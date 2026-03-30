"""Home conversazionale service (US-68).

Returns a summary for the home screen: greeting, ricavi vs target,
saldo banca, prossime uscite, max 3 azioni pendenti.
"""

import logging
import uuid
from datetime import date, datetime, timedelta

from sqlalchemy import select, func as sqla_func, extract
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import (
    Invoice, BankAccount, FiscalDeadline, ImportException, Budget,
)

logger = logging.getLogger(__name__)


class HomeService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_summary(self, tenant_id: uuid.UUID, user_name: str) -> dict:
        """Get home summary (US-68)."""
        today = date.today()
        current_hour = datetime.now().hour

        # Greeting based on time of day
        if current_hour < 12:
            greeting = f"Buongiorno, {user_name}!"
        elif current_hour < 18:
            greeting = f"Buon pomeriggio, {user_name}!"
        else:
            greeting = f"Buonasera, {user_name}!"

        # Ricavi current month
        ricavi_mese = await self.db.scalar(
            select(sqla_func.coalesce(sqla_func.sum(Invoice.importo_netto), 0)).where(
                Invoice.tenant_id == tenant_id,
                Invoice.type == "attiva",
                extract("year", Invoice.data_fattura) == today.year,
                extract("month", Invoice.data_fattura) == today.month,
            )
        ) or 0

        # Budget target for this month
        budget_target = await self.db.scalar(
            select(sqla_func.coalesce(sqla_func.sum(Budget.budget_amount), 0)).where(
                Budget.tenant_id == tenant_id,
                Budget.year == today.year,
                Budget.month == today.month,
                Budget.category == "ricavi",
            )
        ) or 0

        # Bank balance
        saldo_banca = await self.db.scalar(
            select(sqla_func.coalesce(sqla_func.sum(BankAccount.balance), 0)).where(
                BankAccount.tenant_id == tenant_id,
                BankAccount.status == "connected",
            )
        ) or 0

        # Next outflows (upcoming deadlines, next 30 days)
        deadline_result = await self.db.execute(
            select(FiscalDeadline).where(
                FiscalDeadline.tenant_id == tenant_id,
                FiscalDeadline.due_date >= today,
                FiscalDeadline.due_date <= today + timedelta(days=30),
                FiscalDeadline.status == "pending",
            ).order_by(FiscalDeadline.due_date).limit(5)
        )
        deadlines = deadline_result.scalars().all()
        prossime_uscite = [
            {
                "description": d.description,
                "amount": d.amount,
                "due_date": d.due_date.isoformat(),
            }
            for d in deadlines
        ]

        # Pending actions (import exceptions unresolved, max 3)
        exc_result = await self.db.execute(
            select(ImportException).where(
                ImportException.tenant_id == tenant_id,
                not ImportException.resolved,
            ).order_by(ImportException.created_at.desc()).limit(3)
        )
        exceptions = exc_result.scalars().all()
        azioni_pendenti = [
            {
                "title": e.title,
                "severity": e.severity,
                "action_label": e.action_label,
                "source_type": e.source_type,
            }
            for e in exceptions
        ]

        return {
            "greeting": greeting,
            "ricavi_mese": round(float(ricavi_mese), 2),
            "budget_target": round(float(budget_target), 2),
            "ricavi_vs_target_pct": round(
                (float(ricavi_mese) / float(budget_target) * 100), 1
            ) if float(budget_target) > 0 else None,
            "saldo_banca": round(float(saldo_banca), 2),
            "prossime_uscite": prossime_uscite,
            "azioni_pendenti": azioni_pendenti,
            "azioni_pendenti_count": len(azioni_pendenti),
        }
