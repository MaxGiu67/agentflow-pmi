"""Controller Agent service (US-60, US-61, US-62).

Budget conversazionale + Consuntivo mensile + "Come sto andando?"
"""

import logging
import uuid
from datetime import date, datetime
from math import ceil

from sqlalchemy import select, func, and_, extract
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import Budget, Invoice, JournalEntry, PayrollCost

logger = logging.getLogger(__name__)

# Default budget categories
DEFAULT_CATEGORIES = ["ricavi", "personale", "fornitori", "utenze", "affitto", "tasse", "altro"]


class ControllerService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── US-60: Budget Agent — generate from historical data ──

    async def generate_budget_proposal(
        self,
        tenant_id: uuid.UUID,
        year: int,
        growth_rate: float = 0.05,
    ) -> dict:
        """Generate a budget proposal based on previous year data (US-60).

        The agent proposes budget lines based on actual data from year-1,
        adjusted by growth_rate. User can modify via conversational flow.
        """
        prev_year = year - 1
        actuals = await self._get_yearly_actuals(tenant_id, prev_year)

        proposal = []
        for category in DEFAULT_CATEGORIES:
            prev_amount = actuals.get(category, 0)
            if category == "ricavi":
                proposed = round(prev_amount * (1 + growth_rate), 2)
            elif prev_amount > 0:
                proposed = round(prev_amount * (1 + growth_rate * 0.5), 2)  # costs grow slower
            else:
                proposed = 0

            # Split evenly across 12 months
            monthly = round(proposed / 12, 2)

            proposal.append({
                "category": category,
                "annual_previous": round(prev_amount, 2),
                "annual_proposed": proposed,
                "monthly_proposed": monthly,
            })

        total_ricavi = sum(p["annual_proposed"] for p in proposal if p["category"] == "ricavi")
        total_costi = sum(p["annual_proposed"] for p in proposal if p["category"] != "ricavi")

        return {
            "year": year,
            "based_on_year": prev_year,
            "growth_rate": growth_rate,
            "has_historical_data": any(p["annual_previous"] > 0 for p in proposal),
            "proposal": proposal,
            "totale_ricavi": round(total_ricavi, 2),
            "totale_costi": round(total_costi, 2),
            "margine_previsto": round(total_ricavi - total_costi, 2),
            "message": f"Budget {year} proposto basato su dati {prev_year} (+{int(growth_rate*100)}% crescita)",
        }

    async def save_budget(
        self,
        tenant_id: uuid.UUID,
        year: int,
        lines: list[dict],
    ) -> dict:
        """Save budget lines from proposal or manual entry (US-60)."""
        saved = 0
        for line in lines:
            category = line["category"]
            for month in range(1, 13):
                monthly_key = f"month_{month}"
                amount = line.get(monthly_key, line.get("monthly_proposed", 0))

                budget = Budget(
                    tenant_id=tenant_id,
                    year=year,
                    month=month,
                    category=category,
                    budget_amount=round(float(amount), 2),
                )
                self.db.add(budget)
                saved += 1

        await self.db.flush()
        return {
            "year": year,
            "lines_saved": saved,
            "categories": len(lines),
            "message": f"Budget {year} salvato: {len(lines)} categorie × 12 mesi",
        }

    # ── US-61: Budget vs Consuntivo mensile ──

    async def get_budget_vs_actual(
        self,
        tenant_id: uuid.UUID,
        year: int,
        month: int,
    ) -> dict:
        """Compare budget vs actual for a given month (US-61)."""
        # Get budget for this month
        budget_result = await self.db.execute(
            select(Budget.category, Budget.budget_amount).where(
                Budget.tenant_id == tenant_id,
                Budget.year == year,
                Budget.month == month,
            )
        )
        budget_by_cat = {row[0]: row[1] for row in budget_result.fetchall()}

        # Get actuals from invoices and payroll
        actuals = await self._get_monthly_actuals(tenant_id, year, month)

        # Build comparison
        comparisons = []
        all_categories = set(list(budget_by_cat.keys()) + list(actuals.keys()))

        for cat in sorted(all_categories):
            budget_val = budget_by_cat.get(cat, 0)
            actual_val = actuals.get(cat, 0)
            diff = actual_val - budget_val
            pct = round((diff / budget_val * 100), 1) if budget_val != 0 else 0

            if budget_val == 0 and actual_val == 0:
                severity = "ok"
            elif abs(pct) <= 10:
                severity = "ok"
            elif abs(pct) <= 20:
                severity = "warning"
            else:
                severity = "critical"

            comparisons.append({
                "category": cat,
                "budget": round(budget_val, 2),
                "actual": round(actual_val, 2),
                "scostamento": round(diff, 2),
                "scostamento_pct": pct,
                "severity": severity,
            })

        total_budget = sum(c["budget"] for c in comparisons)
        total_actual = sum(c["actual"] for c in comparisons)

        anomalies = [c for c in comparisons if c["severity"] == "critical"]

        return {
            "year": year,
            "month": month,
            "comparisons": comparisons,
            "total_budget": round(total_budget, 2),
            "total_actual": round(total_actual, 2),
            "total_scostamento": round(total_actual - total_budget, 2),
            "anomalies_count": len(anomalies),
            "anomalies": anomalies,
            "has_budget": bool(budget_by_cat),
        }

    # ── US-62: Controller "Come sto andando?" ──

    async def get_summary(self, tenant_id: uuid.UUID, year: int, month: int) -> dict:
        """Get executive summary — "Come sto andando?" (US-62)."""
        actuals = await self._get_monthly_actuals(tenant_id, year, month)

        # Previous month for comparison
        prev_month = month - 1 if month > 1 else 12
        prev_year = year if month > 1 else year - 1
        prev_actuals = await self._get_monthly_actuals(tenant_id, prev_year, prev_month)

        ricavi = actuals.get("ricavi", 0)
        costi = sum(v for k, v in actuals.items() if k != "ricavi")
        margine = ricavi - costi
        margine_pct = round((margine / ricavi * 100), 1) if ricavi > 0 else 0

        prev_ricavi = prev_actuals.get("ricavi", 0)
        trend_ricavi = round(((ricavi - prev_ricavi) / prev_ricavi * 100), 1) if prev_ricavi > 0 else 0

        # Budget comparison
        budget_data = await self.get_budget_vs_actual(tenant_id, year, month)

        # Top costs
        cost_items = [(k, v) for k, v in actuals.items() if k != "ricavi" and v > 0]
        cost_items.sort(key=lambda x: x[1], reverse=True)
        top_costs = [{"category": k, "amount": round(v, 2)} for k, v in cost_items[:5]]

        return {
            "year": year,
            "month": month,
            "ricavi": round(ricavi, 2),
            "costi": round(costi, 2),
            "margine": round(margine, 2),
            "margine_pct": margine_pct,
            "trend_ricavi_pct": trend_ricavi,
            "top_costs": top_costs,
            "budget_target": budget_data.get("total_budget", 0),
            "budget_scostamento_pct": round(
                ((ricavi - budget_data.get("total_budget", 0)) / budget_data.get("total_budget", 1)) * 100, 1
            ) if budget_data.get("has_budget") else None,
            "anomalies": budget_data.get("anomalies", []),
        }

    # ── Helpers ──

    async def _get_yearly_actuals(self, tenant_id: uuid.UUID, year: int) -> dict:
        """Aggregate actual amounts by category for a full year."""
        result = {}

        # Ricavi from active invoices
        ricavi = await self.db.scalar(
            select(func.coalesce(func.sum(Invoice.importo_netto), 0)).where(
                Invoice.tenant_id == tenant_id,
                Invoice.type == "attiva",
                extract("year", Invoice.data_fattura) == year,
            )
        ) or 0
        result["ricavi"] = float(ricavi)

        # Fornitori from passive invoices
        fornitori = await self.db.scalar(
            select(func.coalesce(func.sum(Invoice.importo_netto), 0)).where(
                Invoice.tenant_id == tenant_id,
                Invoice.type == "passiva",
                extract("year", Invoice.data_fattura) == year,
            )
        ) or 0
        result["fornitori"] = float(fornitori)

        # Personale from payroll
        personale = await self.db.scalar(
            select(func.coalesce(func.sum(PayrollCost.costo_totale_azienda), 0)).where(
                PayrollCost.tenant_id == tenant_id,
                extract("year", PayrollCost.mese) == year,
            )
        ) or 0
        result["personale"] = float(personale)

        return result

    async def _get_monthly_actuals(self, tenant_id: uuid.UUID, year: int, month: int) -> dict:
        """Aggregate actual amounts by category for a specific month."""
        result = {}

        ricavi = await self.db.scalar(
            select(func.coalesce(func.sum(Invoice.importo_netto), 0)).where(
                Invoice.tenant_id == tenant_id,
                Invoice.type == "attiva",
                extract("year", Invoice.data_fattura) == year,
                extract("month", Invoice.data_fattura) == month,
            )
        ) or 0
        result["ricavi"] = float(ricavi)

        fornitori = await self.db.scalar(
            select(func.coalesce(func.sum(Invoice.importo_netto), 0)).where(
                Invoice.tenant_id == tenant_id,
                Invoice.type == "passiva",
                extract("year", Invoice.data_fattura) == year,
                extract("month", Invoice.data_fattura) == month,
            )
        ) or 0
        result["fornitori"] = float(fornitori)

        personale = await self.db.scalar(
            select(func.coalesce(func.sum(PayrollCost.costo_totale_azienda), 0)).where(
                PayrollCost.tenant_id == tenant_id,
                extract("year", PayrollCost.mese) == year,
                extract("month", PayrollCost.mese) == month,
            )
        ) or 0
        result["personale"] = float(personale)

        return result

    # ── US-63: Cost Analysis — "Dove perdo soldi?" ──

    async def cost_analysis(
        self, tenant_id: uuid.UUID, year: int, month: int,
    ) -> dict:
        """Cost analysis: top 5 categories, prev period comparison, anomalies (US-63)."""
        actuals = await self._get_monthly_actuals(tenant_id, year, month)

        # Previous month
        prev_month = month - 1 if month > 1 else 12
        prev_year = year if month > 1 else year - 1
        prev_actuals = await self._get_monthly_actuals(tenant_id, prev_year, prev_month)

        # Cost items only (exclude ricavi)
        cost_items = [(k, v) for k, v in actuals.items() if k != "ricavi" and v > 0]
        cost_items.sort(key=lambda x: x[1], reverse=True)
        top_costs = cost_items[:5]

        # Comparison with previous period
        comparisons = []
        for category, amount in top_costs:
            prev_amount = prev_actuals.get(category, 0)
            change_pct = round(((amount - prev_amount) / prev_amount * 100), 1) if prev_amount > 0 else 0
            comparisons.append({
                "category": category,
                "current": round(amount, 2),
                "previous": round(prev_amount, 2),
                "change_pct": change_pct,
                "direction": "up" if change_pct > 0 else ("down" if change_pct < 0 else "stable"),
            })

        # Anomalies: categories that grew > 20%
        anomalies = [c for c in comparisons if c["change_pct"] > 20]

        total_costs = sum(v for k, v in actuals.items() if k != "ricavi")
        ricavi = actuals.get("ricavi", 0)
        incidenza_costi = round((total_costs / ricavi * 100), 1) if ricavi > 0 else 0

        return {
            "year": year,
            "month": month,
            "top_costs": comparisons,
            "total_costs": round(total_costs, 2),
            "ricavi": round(ricavi, 2),
            "incidenza_costi_pct": incidenza_costi,
            "anomalies": anomalies,
            "anomalies_count": len(anomalies),
            "message": f"Analisi costi {month}/{year}: totale {round(total_costs, 2)} EUR, incidenza {incidenza_costi}% sui ricavi",
        }
