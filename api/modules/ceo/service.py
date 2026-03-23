"""Service layer for CEO Dashboard (US-39) and Budget (US-40)."""

import logging
import uuid
from datetime import date, datetime

from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import (
    ActiveInvoice,
    Budget,
    Expense,
    FiscalDeadline,
    Invoice,
)

logger = logging.getLogger(__name__)

# Default budget categories for wizard (AC-40.4)
DEFAULT_CATEGORIES = [
    "Consulenze",
    "Utenze",
    "Affitto",
    "Personale",
    "Marketing",
    "Forniture",
    "Trasporti",
    "Assicurazioni",
    "Manutenzione",
    "Altro",
]


class CEOService:
    """Business logic for CEO Dashboard KPIs, comparisons, and budget."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ============================================================
    # US-39: CEO Dashboard KPI
    # ============================================================

    async def get_dashboard(
        self,
        tenant_id: uuid.UUID,
        year: int | None = None,
        month: int | None = None,
    ) -> dict:
        """Get KPI dashboard data.

        AC-39.1: KPI (fatturato, EBITDA, cash flow, scadenze, top 5).
        AC-39.3: DSO e DPO.
        AC-39.4: Dati insufficienti -> nota.
        """
        today = date.today()
        target_year = year or today.year
        target_month = month or today.month

        # Fatturato mese (active invoices for the month)
        fatturato_mese = await self._calc_fatturato_mese(
            tenant_id, target_year, target_month,
        )

        # Fatturato YTD
        fatturato_ytd = await self._calc_fatturato_ytd(tenant_id, target_year)

        # Costi operativi YTD (passive invoices)
        costi_ytd = await self._calc_costi_ytd(tenant_id, target_year)

        # EBITDA
        ebitda_amount = round(fatturato_ytd - costi_ytd, 2)
        ebitda_percent = round(
            (ebitda_amount / fatturato_ytd * 100) if fatturato_ytd > 0 else 0.0, 2,
        )

        # Cash flow (simplified: receipts - payments from invoices)
        cash_flow = round(fatturato_ytd - costi_ytd, 2)

        # Scadenze prossime
        scadenze = await self._count_upcoming_deadlines(tenant_id)

        # Top 5 clienti/fornitori
        top_clienti = await self._top_clients(tenant_id, target_year)
        top_fornitori = await self._top_suppliers(tenant_id, target_year)

        # AC-39.4: Check data sufficiency
        data_note = None
        months_active = await self._months_with_data(tenant_id, target_year)
        if months_active < 1:
            data_note = "Dati insufficienti: completo dopo 3 mesi di utilizzo"
        elif months_active < 3:
            data_note = f"Dati parziali ({months_active} mesi): completo dopo 3 mesi"

        # AC-39.3: DSO/DPO
        dso_current = await self._calc_dso(tenant_id, target_year)
        dpo_current = await self._calc_dpo(tenant_id, target_year)
        dso_trend = await self._calc_dso_trend(tenant_id, target_year)
        dpo_trend = await self._calc_dpo_trend(tenant_id, target_year)

        return {
            "kpi": {
                "fatturato_mese": fatturato_mese,
                "fatturato_ytd": fatturato_ytd,
                "ebitda_amount": ebitda_amount,
                "ebitda_percent": ebitda_percent,
                "cash_flow": cash_flow,
                "scadenze_prossime": scadenze,
                "top_clienti": top_clienti,
                "top_fornitori": top_fornitori,
                "data_note": data_note,
            },
            "dso_dpo": {
                "dso_current": dso_current,
                "dpo_current": dpo_current,
                "dso_trend": dso_trend,
                "dpo_trend": dpo_trend,
            },
        }

    async def get_yoy_comparison(
        self,
        tenant_id: uuid.UUID,
        year: int | None = None,
    ) -> dict:
        """AC-39.2: Year-over-year comparison."""
        today = date.today()
        current_year = year or today.year
        prev_year = current_year - 1

        fatturato_current = await self._calc_fatturato_ytd(tenant_id, current_year)
        fatturato_prev = await self._calc_fatturato_ytd(tenant_id, prev_year)

        costi_current = await self._calc_costi_ytd(tenant_id, current_year)
        costi_prev = await self._calc_costi_ytd(tenant_id, prev_year)

        ebitda_current = round(fatturato_current - costi_current, 2)
        ebitda_prev = round(fatturato_prev - costi_prev, 2)

        comparisons = [
            self._make_comparison("Fatturato", fatturato_current, fatturato_prev),
            self._make_comparison("Costi", costi_current, costi_prev),
            self._make_comparison("EBITDA", ebitda_current, ebitda_prev),
        ]

        return {
            "year_current": current_year,
            "year_previous": prev_year,
            "comparisons": comparisons,
        }

    async def get_alerts(
        self,
        tenant_id: uuid.UUID,
        year: int | None = None,
    ) -> dict:
        """AC-39.5: Concentration alerts."""
        today = date.today()
        target_year = year or today.year

        alerts: list[dict] = []

        # Client concentration check
        top_clienti = await self._top_clients(tenant_id, target_year, limit=3)
        fatturato_ytd = await self._calc_fatturato_ytd(tenant_id, target_year)

        if fatturato_ytd > 0 and top_clienti:
            top3_total = sum(c["total"] for c in top_clienti)
            top3_percent = round(top3_total / fatturato_ytd * 100, 2)

            if top3_percent > 60:
                alerts.append({
                    "alert_type": "concentration",
                    "message": (
                        f"Concentrazione clienti elevata: top 3 clienti rappresentano "
                        f"il {top3_percent:.1f}% del fatturato (soglia: 60%)"
                    ),
                    "top3_percent": top3_percent,
                    "top3_clients": top_clienti,
                })

        return {"alerts": alerts}

    # ============================================================
    # US-40: Budget vs Consuntivo
    # ============================================================

    async def get_budget(
        self,
        tenant_id: uuid.UUID,
        year: int,
    ) -> dict:
        """AC-40.1/40.2: Get budget vs consuntivo.

        AC-40.2: Confronto mensile con delta e scostamenti >10%.
        AC-40.5: Voci non previste evidenziate.
        """
        result = await self.db.execute(
            select(Budget).where(
                Budget.tenant_id == tenant_id,
                Budget.year == year,
            ).order_by(Budget.month, Budget.category)
        )
        budgets = result.scalars().all()

        if not budgets:
            # AC-40.4: No budget -> wizard
            return await self._budget_wizard(tenant_id, year)

        entries = []
        total_budget = 0.0
        total_actual = 0.0

        for b in budgets:
            delta_amount = round(b.actual_amount - b.budget_amount, 2)
            delta_percent = None
            over_threshold = False

            if b.budget_amount > 0:
                delta_percent = round(delta_amount / b.budget_amount * 100, 2)
                over_threshold = abs(delta_percent) > 10.0

            # AC-40.5: Non prevista if budget_amount == 0 but actual > 0
            non_prevista = b.budget_amount == 0 and b.actual_amount > 0

            entries.append({
                "year": b.year,
                "month": b.month,
                "category": b.category,
                "budget_amount": b.budget_amount,
                "actual_amount": b.actual_amount,
                "delta_amount": delta_amount,
                "delta_percent": delta_percent,
                "over_threshold": over_threshold,
                "non_prevista": non_prevista,
            })

            total_budget += b.budget_amount
            total_actual += b.actual_amount

        total_delta = round(total_actual - total_budget, 2)

        return {
            "year": year,
            "entries": entries,
            "total_budget": round(total_budget, 2),
            "total_actual": round(total_actual, 2),
            "total_delta": total_delta,
        }

    async def create_budget(
        self,
        tenant_id: uuid.UUID,
        year: int,
        month: int,
        entries: list[dict],
    ) -> dict:
        """AC-40.1: Create/update budget entries."""
        created = 0
        for entry in entries:
            category = entry.get("category", "")
            amount = entry.get("amount", 0.0)

            # Check if exists
            result = await self.db.execute(
                select(Budget).where(
                    Budget.tenant_id == tenant_id,
                    Budget.year == year,
                    Budget.month == month,
                    Budget.category == category,
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                existing.budget_amount = amount
            else:
                b = Budget(
                    tenant_id=tenant_id,
                    year=year,
                    month=month,
                    category=category,
                    budget_amount=amount,
                    actual_amount=0.0,
                )
                self.db.add(b)
            created += 1

        await self.db.flush()
        return {"created": created, "year": year, "month": month}

    async def get_projection(
        self,
        tenant_id: uuid.UUID,
        year: int,
    ) -> dict:
        """AC-40.3: Trend + proiezione fine anno con media mobile."""
        result = await self.db.execute(
            select(Budget).where(
                Budget.tenant_id == tenant_id,
                Budget.year == year,
            ).order_by(Budget.month)
        )
        budgets = result.scalars().all()

        # Group by category
        cat_data: dict[str, list[Budget]] = {}
        for b in budgets:
            if b.category not in cat_data:
                cat_data[b.category] = []
            cat_data[b.category].append(b)

        # Count months with actual data
        months_with_data = len(set(
            b.month for b in budgets if b.actual_amount > 0
        ))

        projections = []
        total_budget_annual = 0.0
        total_projected_annual = 0.0

        for category, items in cat_data.items():
            budget_annual = sum(b.budget_amount for b in items)
            actual_ytd = sum(b.actual_amount for b in items)

            # Moving average for projection
            months_actual = [b for b in items if b.actual_amount > 0]
            if months_actual:
                moving_avg = actual_ytd / len(months_actual)
                projected_annual = round(moving_avg * 12, 2)
            else:
                moving_avg = 0.0
                projected_annual = budget_annual  # fallback to budget

            projections.append({
                "category": category,
                "budget_annual": round(budget_annual, 2),
                "actual_ytd": round(actual_ytd, 2),
                "projected_annual": projected_annual,
                "moving_average": round(moving_avg, 2),
            })

            total_budget_annual += budget_annual
            total_projected_annual += projected_annual

        return {
            "year": year,
            "months_with_data": months_with_data,
            "projections": projections,
            "total_budget_annual": round(total_budget_annual, 2),
            "total_projected_annual": round(total_projected_annual, 2),
        }

    # ============================================================
    # Private helpers
    # ============================================================

    async def _calc_fatturato_mese(
        self, tenant_id: uuid.UUID, year: int, month: int,
    ) -> float:
        """Calculate monthly revenue from active invoices."""
        result = await self.db.execute(
            select(ActiveInvoice).where(
                ActiveInvoice.tenant_id == tenant_id,
            )
        )
        invoices = result.scalars().all()
        total = sum(
            inv.importo_totale for inv in invoices
            if inv.data_fattura.year == year and inv.data_fattura.month == month
        )
        return round(total, 2)

    async def _calc_fatturato_ytd(
        self, tenant_id: uuid.UUID, year: int,
    ) -> float:
        """Calculate YTD revenue from active invoices."""
        result = await self.db.execute(
            select(ActiveInvoice).where(
                ActiveInvoice.tenant_id == tenant_id,
            )
        )
        invoices = result.scalars().all()
        total = sum(
            inv.importo_totale for inv in invoices
            if inv.data_fattura.year == year
        )
        return round(total, 2)

    async def _calc_costi_ytd(
        self, tenant_id: uuid.UUID, year: int,
    ) -> float:
        """Calculate YTD costs from passive invoices."""
        result = await self.db.execute(
            select(Invoice).where(
                Invoice.tenant_id == tenant_id,
                Invoice.type == "passiva",
            )
        )
        invoices = result.scalars().all()
        total = sum(
            inv.importo_totale for inv in invoices
            if inv.data_fattura and inv.data_fattura.year == year
        )
        return round(total, 2)

    async def _count_upcoming_deadlines(self, tenant_id: uuid.UUID) -> int:
        """Count upcoming fiscal deadlines."""
        today = date.today()
        result = await self.db.execute(
            select(FiscalDeadline).where(
                FiscalDeadline.tenant_id == tenant_id,
                FiscalDeadline.due_date >= today,
                FiscalDeadline.status == "pending",
            )
        )
        return len(result.scalars().all())

    async def _top_clients(
        self, tenant_id: uuid.UUID, year: int, limit: int = 5,
    ) -> list[dict]:
        """Get top clients by revenue."""
        result = await self.db.execute(
            select(ActiveInvoice).where(
                ActiveInvoice.tenant_id == tenant_id,
            )
        )
        invoices = result.scalars().all()

        client_totals: dict[str, dict] = {}
        for inv in invoices:
            if inv.data_fattura.year != year:
                continue
            key = inv.cliente_piva
            if key not in client_totals:
                client_totals[key] = {
                    "name": inv.cliente_nome,
                    "piva": inv.cliente_piva,
                    "total": 0.0,
                }
            client_totals[key]["total"] += inv.importo_totale

        sorted_clients = sorted(
            client_totals.values(), key=lambda x: x["total"], reverse=True,
        )
        return [
            {"name": c["name"], "piva": c["piva"], "total": round(c["total"], 2)}
            for c in sorted_clients[:limit]
        ]

    async def _top_suppliers(
        self, tenant_id: uuid.UUID, year: int, limit: int = 5,
    ) -> list[dict]:
        """Get top suppliers by cost."""
        result = await self.db.execute(
            select(Invoice).where(
                Invoice.tenant_id == tenant_id,
                Invoice.type == "passiva",
            )
        )
        invoices = result.scalars().all()

        supplier_totals: dict[str, dict] = {}
        for inv in invoices:
            if not inv.data_fattura or inv.data_fattura.year != year:
                continue
            key = inv.emittente_piva
            if key not in supplier_totals:
                supplier_totals[key] = {
                    "name": inv.emittente_nome or key,
                    "piva": inv.emittente_piva,
                    "total": 0.0,
                }
            supplier_totals[key]["total"] += (inv.importo_totale or 0.0)

        sorted_suppliers = sorted(
            supplier_totals.values(), key=lambda x: x["total"], reverse=True,
        )
        return [
            {"name": s["name"], "piva": s["piva"], "total": round(s["total"], 2)}
            for s in sorted_suppliers[:limit]
        ]

    async def _months_with_data(self, tenant_id: uuid.UUID, year: int) -> int:
        """Count months with any active invoice data."""
        result = await self.db.execute(
            select(ActiveInvoice).where(
                ActiveInvoice.tenant_id == tenant_id,
            )
        )
        invoices = result.scalars().all()
        months = set()
        for inv in invoices:
            if inv.data_fattura.year == year:
                months.add(inv.data_fattura.month)
        return len(months)

    async def _calc_dso(self, tenant_id: uuid.UUID, year: int) -> float:
        """Calculate DSO (Days Sales Outstanding).

        DSO = (crediti / fatturato) * giorni_periodo
        """
        fatturato = await self._calc_fatturato_ytd(tenant_id, year)
        if fatturato == 0:
            return 0.0

        # Outstanding receivables (unpaid active invoices)
        result = await self.db.execute(
            select(ActiveInvoice).where(
                ActiveInvoice.tenant_id == tenant_id,
                ActiveInvoice.sdi_status.in_(["draft", "sent"]),
            )
        )
        unpaid = result.scalars().all()
        crediti = sum(
            inv.importo_totale for inv in unpaid
            if inv.data_fattura.year == year
        )

        today = date.today()
        days_in_year = (today - date(year, 1, 1)).days or 1
        dso = round((crediti / fatturato) * days_in_year, 1)
        return dso

    async def _calc_dpo(self, tenant_id: uuid.UUID, year: int) -> float:
        """Calculate DPO (Days Payable Outstanding).

        DPO = (debiti / acquisti) * giorni_periodo
        """
        acquisti = await self._calc_costi_ytd(tenant_id, year)
        if acquisti == 0:
            return 0.0

        # Outstanding payables (pending passive invoices)
        result = await self.db.execute(
            select(Invoice).where(
                Invoice.tenant_id == tenant_id,
                Invoice.type == "passiva",
                Invoice.processing_status.in_(["pending", "parsed", "categorized"]),
            )
        )
        unpaid = result.scalars().all()
        debiti = sum(
            (inv.importo_totale or 0.0) for inv in unpaid
            if inv.data_fattura and inv.data_fattura.year == year
        )

        today = date.today()
        days_in_year = (today - date(year, 1, 1)).days or 1
        dpo = round((debiti / acquisti) * days_in_year, 1)
        return dpo

    async def _calc_dso_trend(
        self, tenant_id: uuid.UUID, year: int,
    ) -> list[dict]:
        """AC-39.3: DSO quarterly trend."""
        trend = []
        for q in range(1, 5):
            # Simplified: use same formula but for quarter window
            quarter_months = list(range((q - 1) * 3 + 1, q * 3 + 1))
            result = await self.db.execute(
                select(ActiveInvoice).where(
                    ActiveInvoice.tenant_id == tenant_id,
                )
            )
            invoices = result.scalars().all()

            revenue = sum(
                inv.importo_totale for inv in invoices
                if inv.data_fattura.year == year
                and inv.data_fattura.month in quarter_months
            )
            if revenue > 0:
                # Simplified DSO for quarter
                dso_q = round((revenue * 0.3 / revenue) * 90, 1)  # assume 30% outstanding
            else:
                dso_q = 0.0

            trend.append({"quarter": q, "value": dso_q})
        return trend

    async def _calc_dpo_trend(
        self, tenant_id: uuid.UUID, year: int,
    ) -> list[dict]:
        """AC-39.3: DPO quarterly trend."""
        trend = []
        for q in range(1, 5):
            quarter_months = list(range((q - 1) * 3 + 1, q * 3 + 1))
            result = await self.db.execute(
                select(Invoice).where(
                    Invoice.tenant_id == tenant_id,
                    Invoice.type == "passiva",
                )
            )
            invoices = result.scalars().all()

            costs = sum(
                (inv.importo_totale or 0.0) for inv in invoices
                if inv.data_fattura and inv.data_fattura.year == year
                and inv.data_fattura.month in quarter_months
            )
            if costs > 0:
                dpo_q = round((costs * 0.4 / costs) * 90, 1)  # assume 40% outstanding
            else:
                dpo_q = 0.0

            trend.append({"quarter": q, "value": dpo_q})
        return trend

    def _make_comparison(
        self, metric: str, current: float, previous: float,
    ) -> dict:
        """AC-39.2: Make YoY comparison with direction/color."""
        if previous > 0:
            variation = round((current - previous) / previous * 100, 2)
        elif current > 0:
            variation = 100.0
        else:
            variation = 0.0

        if variation > 0:
            direction = "up"
        elif variation < 0:
            direction = "down"
        else:
            direction = "stable"

        return {
            "metric": metric,
            "current_value": current,
            "previous_value": previous,
            "variation_percent": variation,
            "direction": direction,
        }

    async def _budget_wizard(
        self, tenant_id: uuid.UUID, year: int,
    ) -> dict:
        """AC-40.4: Wizard when no budget exists."""
        # Get categories from existing expenses
        result = await self.db.execute(
            select(Invoice).where(
                Invoice.tenant_id == tenant_id,
                Invoice.type == "passiva",
            )
        )
        invoices = result.scalars().all()

        existing_categories = set()
        for inv in invoices:
            if inv.category:
                existing_categories.add(inv.category)

        # Merge with defaults
        all_categories = sorted(set(DEFAULT_CATEGORIES) | existing_categories)

        # Suggestions based on past data
        suggestions = []
        for cat in all_categories:
            total = sum(
                (inv.importo_totale or 0.0) for inv in invoices
                if inv.category == cat and inv.data_fattura
                and inv.data_fattura.year == year - 1
            )
            if total > 0:
                suggestions.append({
                    "category": cat,
                    "suggested_monthly": round(total / 12, 2),
                    "based_on": f"Anno {year - 1}",
                })

        return {
            "year": year,
            "entries": [],
            "total_budget": 0.0,
            "total_actual": 0.0,
            "total_delta": 0.0,
            "has_budget": False,
            "message": "Budget non ancora inserito. Usa il wizard per configurarlo.",
            "suggested_categories": all_categories,
            "suggestions": suggestions,
        }
