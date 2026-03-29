"""Proactive Deadlines Agent service (US-65).

Returns upcoming deadlines with calculated amounts from invoices/payroll.
"""

import logging
import uuid
from datetime import date, timedelta

from sqlalchemy import select, func as sqla_func, extract
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import FiscalDeadline, Invoice, PayrollCost, WithholdingTax

logger = logging.getLogger(__name__)


class ProactiveDeadlineService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_proactive_deadlines(
        self,
        tenant_id: uuid.UUID,
        days_ahead: int = 60,
    ) -> dict:
        """Get upcoming deadlines with calculated amounts (US-65)."""
        today = date.today()
        end_date = today + timedelta(days=days_ahead)

        # Get fiscal deadlines
        result = await self.db.execute(
            select(FiscalDeadline).where(
                FiscalDeadline.tenant_id == tenant_id,
                FiscalDeadline.due_date >= today,
                FiscalDeadline.due_date <= end_date,
            ).order_by(FiscalDeadline.due_date)
        )
        deadlines = result.scalars().all()

        # Calculate supplementary data from invoices
        iva_estimate = await self._estimate_iva(tenant_id)
        ritenute_estimate = await self._estimate_ritenute(tenant_id)
        payroll_estimate = await self._estimate_payroll(tenant_id)

        items = []
        for d in deadlines:
            days_remaining = (d.due_date - today).days
            items.append({
                "id": str(d.id),
                "code": d.code,
                "description": d.description,
                "amount": d.amount,
                "due_date": d.due_date.isoformat(),
                "days_remaining": days_remaining,
                "status": d.status,
                "urgency": "critical" if days_remaining <= 7 else ("warning" if days_remaining <= 30 else "ok"),
            })

        # Add estimated upcoming obligations not yet in deadlines
        estimates = {
            "iva_trimestrale_stima": round(iva_estimate, 2),
            "ritenute_mensili_stima": round(ritenute_estimate, 2),
            "costo_personale_mensile": round(payroll_estimate, 2),
        }

        total_upcoming = sum(d.amount for d in deadlines)

        return {
            "deadlines": items,
            "total_count": len(items),
            "total_amount": round(total_upcoming, 2),
            "estimates": estimates,
            "period_days": days_ahead,
            "message": f"{len(items)} scadenze nei prossimi {days_ahead} giorni per un totale di {round(total_upcoming, 2)} EUR",
        }

    async def _estimate_iva(self, tenant_id: uuid.UUID) -> float:
        """Estimate quarterly IVA from recent invoices."""
        iva_vendite = await self.db.scalar(
            select(sqla_func.coalesce(sqla_func.sum(Invoice.importo_iva), 0)).where(
                Invoice.tenant_id == tenant_id,
                Invoice.type == "attiva",
            )
        ) or 0

        iva_acquisti = await self.db.scalar(
            select(sqla_func.coalesce(sqla_func.sum(Invoice.importo_iva), 0)).where(
                Invoice.tenant_id == tenant_id,
                Invoice.type == "passiva",
            )
        ) or 0

        return max(0, float(iva_vendite) - float(iva_acquisti))

    async def _estimate_ritenute(self, tenant_id: uuid.UUID) -> float:
        """Estimate monthly withholding taxes."""
        result = await self.db.scalar(
            select(sqla_func.coalesce(sqla_func.sum(WithholdingTax.importo_ritenuta), 0)).where(
                WithholdingTax.tenant_id == tenant_id,
                WithholdingTax.status == "detected",
            )
        )
        return float(result or 0)

    async def _estimate_payroll(self, tenant_id: uuid.UUID) -> float:
        """Estimate monthly payroll cost."""
        result = await self.db.scalar(
            select(sqla_func.coalesce(sqla_func.sum(PayrollCost.costo_totale_azienda), 0)).where(
                PayrollCost.tenant_id == tenant_id,
            )
        )
        total = float(result or 0)
        count_result = await self.db.scalar(
            select(sqla_func.count(sqla_func.distinct(PayrollCost.mese))).where(
                PayrollCost.tenant_id == tenant_id,
            )
        )
        months = int(count_result or 1) or 1
        return total / months
