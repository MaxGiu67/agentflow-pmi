"""Service layer for fiscal deadlines / scadenzario (US-17, US-20)."""

import logging
import uuid
from datetime import date, timedelta

from sqlalchemy import select, func as sqla_func
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import Invoice

logger = logging.getLogger(__name__)

# Italian public holidays (fixed dates, no Easter computation for simplicity)
ITALIAN_HOLIDAYS_FIXED = {
    (1, 1),   # Capodanno
    (1, 6),   # Epifania
    (4, 25),  # Liberazione
    (5, 1),   # Festa del Lavoro
    (6, 2),   # Festa della Repubblica
    (8, 15),  # Ferragosto
    (11, 1),  # Tutti i Santi
    (12, 8),  # Immacolata
    (12, 25), # Natale
    (12, 26), # Santo Stefano
}


def is_italian_holiday(d: date) -> bool:
    """Check if date is a fixed Italian public holiday."""
    return (d.month, d.day) in ITALIAN_HOLIDAYS_FIXED


def next_business_day(d: date) -> date:
    """Shift date forward to next business day if it falls on weekend/holiday."""
    while d.weekday() >= 5 or is_italian_holiday(d):  # 5=Saturday, 6=Sunday
        d += timedelta(days=1)
    return d


def compute_countdown_color(days_remaining: int) -> str:
    """Compute color based on days remaining.

    Red: <= 7 days
    Yellow: 8-30 days
    Green: > 30 days
    """
    if days_remaining <= 7:
        return "red"
    elif days_remaining <= 30:
        return "yellow"
    else:
        return "green"


# Deadline definitions per regime
ORDINARIO_DEADLINES = [
    # IVA trimestrale
    {
        "name": "Liquidazione IVA Q1",
        "description": "Versamento IVA primo trimestre",
        "month": 5, "day": 16,
        "category": "iva",
    },
    {
        "name": "Liquidazione IVA Q2",
        "description": "Versamento IVA secondo trimestre",
        "month": 8, "day": 20,
        "category": "iva",
    },
    {
        "name": "Liquidazione IVA Q3",
        "description": "Versamento IVA terzo trimestre",
        "month": 11, "day": 16,
        "category": "iva",
    },
    {
        "name": "Acconto IVA dicembre",
        "description": "Versamento acconto IVA annuale",
        "month": 12, "day": 27,
        "category": "iva",
    },
    # F24 mensile
    {
        "name": "F24 Gennaio",
        "description": "Versamento ritenute e contributi mese precedente",
        "month": 1, "day": 16,
        "category": "f24",
    },
    {
        "name": "F24 Febbraio",
        "description": "Versamento ritenute e contributi mese precedente",
        "month": 2, "day": 16,
        "category": "f24",
    },
    {
        "name": "F24 Marzo",
        "description": "Versamento ritenute e contributi mese precedente",
        "month": 3, "day": 16,
        "category": "f24",
    },
    {
        "name": "F24 Aprile",
        "description": "Versamento ritenute e contributi mese precedente",
        "month": 4, "day": 16,
        "category": "f24",
    },
    {
        "name": "F24 Maggio",
        "description": "Versamento ritenute e contributi mese precedente",
        "month": 5, "day": 16,
        "category": "f24",
    },
    {
        "name": "F24 Giugno",
        "description": "Versamento ritenute e contributi mese precedente",
        "month": 6, "day": 16,
        "category": "f24",
    },
    {
        "name": "F24 Luglio",
        "description": "Versamento ritenute e contributi mese precedente",
        "month": 7, "day": 16,
        "category": "f24",
    },
    {
        "name": "F24 Agosto",
        "description": "Versamento ritenute e contributi mese precedente",
        "month": 8, "day": 20,
        "category": "f24",
    },
    {
        "name": "F24 Settembre",
        "description": "Versamento ritenute e contributi mese precedente",
        "month": 9, "day": 16,
        "category": "f24",
    },
    {
        "name": "F24 Ottobre",
        "description": "Versamento ritenute e contributi mese precedente",
        "month": 10, "day": 16,
        "category": "f24",
    },
    {
        "name": "F24 Novembre",
        "description": "Versamento ritenute e contributi mese precedente",
        "month": 11, "day": 16,
        "category": "f24",
    },
    {
        "name": "F24 Dicembre",
        "description": "Versamento ritenute e contributi mese precedente",
        "month": 12, "day": 16,
        "category": "f24",
    },
    # Dichiarazione annuale
    {
        "name": "Dichiarazione IVA annuale",
        "description": "Invio dichiarazione IVA annuale",
        "month": 4, "day": 30,
        "category": "dichiarazione",
    },
]

FORFETTARIO_DEADLINES = [
    # Imposta sostitutiva
    {
        "name": "Saldo imposta sostitutiva anno precedente",
        "description": "Versamento saldo imposta sostitutiva 15% (o 5%)",
        "month": 6, "day": 30,
        "category": "imposta_sostitutiva",
    },
    {
        "name": "Primo acconto imposta sostitutiva",
        "description": "Versamento primo acconto imposta sostitutiva (40%)",
        "month": 6, "day": 30,
        "category": "imposta_sostitutiva",
    },
    {
        "name": "Secondo acconto imposta sostitutiva",
        "description": "Versamento secondo acconto imposta sostitutiva (60%)",
        "month": 11, "day": 30,
        "category": "imposta_sostitutiva",
    },
    # Dichiarazione Redditi
    {
        "name": "Dichiarazione Redditi PF",
        "description": "Invio modello Redditi Persone Fisiche",
        "month": 11, "day": 30,
        "category": "dichiarazione",
    },
    # INPS
    {
        "name": "INPS contributi fissi Q1",
        "description": "Versamento contributi INPS fissi primo trimestre",
        "month": 5, "day": 16,
        "category": "f24",
    },
    {
        "name": "INPS contributi fissi Q2",
        "description": "Versamento contributi INPS fissi secondo trimestre",
        "month": 8, "day": 20,
        "category": "f24",
    },
    {
        "name": "INPS contributi fissi Q3",
        "description": "Versamento contributi INPS fissi terzo trimestre",
        "month": 11, "day": 16,
        "category": "f24",
    },
    {
        "name": "INPS contributi fissi Q4",
        "description": "Versamento contributi INPS fissi quarto trimestre",
        "month": 2, "day": 16,
        "category": "f24",
    },
]

SEMPLIFICATO_DEADLINES = [
    # IVA trimestrale (same as ordinario for quarterly)
    {
        "name": "Liquidazione IVA Q1",
        "description": "Versamento IVA primo trimestre",
        "month": 5, "day": 16,
        "category": "iva",
    },
    {
        "name": "Liquidazione IVA Q2",
        "description": "Versamento IVA secondo trimestre",
        "month": 8, "day": 20,
        "category": "iva",
    },
    {
        "name": "Liquidazione IVA Q3",
        "description": "Versamento IVA terzo trimestre",
        "month": 11, "day": 16,
        "category": "iva",
    },
    {
        "name": "Acconto IVA dicembre",
        "description": "Versamento acconto IVA annuale",
        "month": 12, "day": 27,
        "category": "iva",
    },
    # Dichiarazione
    {
        "name": "Dichiarazione IVA annuale",
        "description": "Invio dichiarazione IVA annuale",
        "month": 4, "day": 30,
        "category": "dichiarazione",
    },
]

REGIME_DEADLINES = {
    "ordinario": ORDINARIO_DEADLINES,
    "forfettario": FORFETTARIO_DEADLINES,
    "semplificato": SEMPLIFICATO_DEADLINES,
}


class DeadlineService:
    """Service for fiscal deadline computation."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def get_deadlines(
        self,
        regime: str,
        year: int,
        reference_date: date | None = None,
    ) -> dict:
        """Compute all deadlines for a given regime and year.

        Args:
            regime: Fiscal regime (ordinario, forfettario, semplificato).
            year: Calendar year.
            reference_date: Date to compute countdown from (default: today).

        Returns:
            Dict with deadlines, regime, total, year.
        """
        if regime not in REGIME_DEADLINES:
            raise ValueError(
                f"Regime fiscale '{regime}' non configurato. "
                f"Regimi supportati: {', '.join(REGIME_DEADLINES.keys())}"
            )

        ref = reference_date or date.today()
        deadline_defs = REGIME_DEADLINES[regime]
        deadlines = []

        for dl in deadline_defs:
            original = date(year, dl["month"], dl["day"])
            effective = next_business_day(original)
            days_remaining = (effective - ref).days
            color = compute_countdown_color(days_remaining)

            deadlines.append({
                "name": dl["name"],
                "description": dl["description"],
                "original_date": original.isoformat(),
                "effective_date": effective.isoformat(),
                "days_remaining": days_remaining,
                "color": color,
                "regime": regime,
                "category": dl["category"],
            })

        # Sort by effective_date
        deadlines.sort(key=lambda d: d["effective_date"])

        return {
            "deadlines": deadlines,
            "regime": regime,
            "total": len(deadlines),
            "year": year,
        }

    # ------------------------------------------------------------------
    # US-20: Personalized fiscal alerts with estimated amounts
    # ------------------------------------------------------------------

    async def get_alerts(
        self,
        tenant_id: uuid.UUID,
        regime: str,
        year: int,
        reference_date: date | None = None,
        advance_days: int = 10,
        fiscoapi_available: bool = False,
        regime_change_date: date | None = None,
        new_regime: str | None = None,
    ) -> dict:
        """Get personalized fiscal alerts with estimated amounts.

        Args:
            tenant_id: Tenant for invoice lookup.
            regime: Fiscal regime.
            year: Calendar year.
            reference_date: Date to compute from (default: today).
            advance_days: Days before deadline to generate alert.
            fiscoapi_available: If True, amounts come from FiscoAPI.
            regime_change_date: Date of regime change (if any).
            new_regime: New regime after change (if any).

        Returns:
            Dict with alerts, regime, total, year.
        """
        if regime not in REGIME_DEADLINES:
            raise ValueError(
                f"Regime fiscale '{regime}' non configurato. "
                f"Regimi supportati: {', '.join(REGIME_DEADLINES.keys())}"
            )

        ref = reference_date or date.today()

        # Handle regime change mid-year (AC-20.4)
        if regime_change_date and new_regime and new_regime in REGIME_DEADLINES:
            alerts = await self._compute_alerts_with_regime_change(
                tenant_id=tenant_id,
                old_regime=regime,
                new_regime=new_regime,
                change_date=regime_change_date,
                year=year,
                ref=ref,
                advance_days=advance_days,
                fiscoapi_available=fiscoapi_available,
            )
            return {
                "alerts": alerts,
                "regime": f"{regime} -> {new_regime}",
                "total": len(alerts),
                "year": year,
            }

        deadline_defs = REGIME_DEADLINES[regime]
        alerts = []

        for dl in deadline_defs:
            if dl["category"] not in ("iva", "imposta_sostitutiva"):
                continue  # Alerts only for IVA / imposta sostitutiva

            original = date(year, dl["month"], dl["day"])
            effective = next_business_day(original)
            days_remaining = (effective - ref).days

            # Only show alerts within advance_days window
            if days_remaining < 0 or days_remaining > advance_days + 30:
                continue

            # Estimate amount from invoices
            importo_stimato, is_provisional, pending_count = (
                await self._estimate_amount(
                    tenant_id=tenant_id,
                    category=dl["category"],
                    regime=regime,
                    year=year,
                    quarter=self._get_quarter_for_deadline(dl),
                )
            )

            importo_source = "fiscoapi" if fiscoapi_available else "stima"
            provisional_note = None
            if is_provisional and pending_count > 0:
                provisional_note = (
                    f"Stima provvisoria, {pending_count} fatture in attesa di registrazione"
                )

            alerts.append({
                "name": dl["name"],
                "description": dl["description"],
                "scadenza_date": effective.isoformat(),
                "days_remaining": days_remaining,
                "importo_stimato": importo_stimato,
                "importo_source": importo_source,
                "is_provisional": is_provisional,
                "provisional_note": provisional_note,
                "regime": regime,
                "category": dl["category"],
            })

        alerts.sort(key=lambda a: a["scadenza_date"])

        return {
            "alerts": alerts,
            "regime": regime,
            "total": len(alerts),
            "year": year,
        }

    async def _estimate_amount(
        self,
        tenant_id: uuid.UUID,
        category: str,
        regime: str,
        year: int,
        quarter: int | None,
    ) -> tuple[float, bool, int]:
        """Estimate the amount for a fiscal deadline from registered invoices.

        Returns:
            (estimated_amount, is_provisional, pending_invoice_count)
        """
        # Get all invoices for the tenant in the relevant period
        q_start, q_end = self._quarter_date_range(year, quarter or 1)

        # Count registered (categorized/parsed) invoices
        result = await self.db.execute(
            select(
                sqla_func.coalesce(sqla_func.sum(Invoice.importo_iva), 0.0),
            ).where(
                Invoice.tenant_id == tenant_id,
                Invoice.data_fattura >= q_start,
                Invoice.data_fattura <= q_end,
                Invoice.processing_status.in_(["parsed", "categorized", "registered"]),
            )
        )
        total_iva = result.scalar() or 0.0

        # Count pending invoices
        result2 = await self.db.execute(
            select(sqla_func.count(Invoice.id)).where(
                Invoice.tenant_id == tenant_id,
                Invoice.data_fattura >= q_start,
                Invoice.data_fattura <= q_end,
                Invoice.processing_status.in_(["pending", "error"]),
            )
        )
        pending_count = result2.scalar() or 0

        is_provisional = pending_count > 0

        if regime == "forfettario":
            # Imposta sostitutiva 15% (or 5% for first 5 years)
            estimated = round(total_iva * 0.15, 2) if total_iva else 0.0
        else:
            # IVA: debito - credito (simplified: use total IVA from passive invoices)
            estimated = round(total_iva, 2) if total_iva else 0.0

        return estimated, is_provisional, pending_count

    async def _compute_alerts_with_regime_change(
        self,
        tenant_id: uuid.UUID,
        old_regime: str,
        new_regime: str,
        change_date: date,
        year: int,
        ref: date,
        advance_days: int,
        fiscoapi_available: bool,
    ) -> list[dict]:
        """Compute alerts when regime changes mid-year (AC-20.4).

        Deadlines before change_date use old_regime,
        deadlines after use new_regime.
        """
        alerts: list[dict] = []

        for regime, deadlines in [
            (old_regime, REGIME_DEADLINES[old_regime]),
            (new_regime, REGIME_DEADLINES[new_regime]),
        ]:
            for dl in deadlines:
                if dl["category"] not in ("iva", "imposta_sostitutiva"):
                    continue

                original = date(year, dl["month"], dl["day"])
                effective = next_business_day(original)
                days_remaining = (effective - ref).days

                # Apply regime based on whether deadline is before/after change
                if regime == old_regime and effective >= change_date:
                    continue
                if regime == new_regime and effective < change_date:
                    continue

                if days_remaining < 0 or days_remaining > advance_days + 30:
                    continue

                importo_stimato, is_provisional, pending_count = (
                    await self._estimate_amount(
                        tenant_id=tenant_id,
                        category=dl["category"],
                        regime=regime,
                        year=year,
                        quarter=self._get_quarter_for_deadline(dl),
                    )
                )

                importo_source = "fiscoapi" if fiscoapi_available else "stima"
                provisional_note = None
                if is_provisional and pending_count > 0:
                    provisional_note = (
                        f"Stima provvisoria, {pending_count} fatture in attesa di registrazione"
                    )

                alerts.append({
                    "name": dl["name"],
                    "description": dl["description"],
                    "scadenza_date": effective.isoformat(),
                    "days_remaining": days_remaining,
                    "importo_stimato": importo_stimato,
                    "importo_source": importo_source,
                    "is_provisional": is_provisional,
                    "provisional_note": provisional_note,
                    "regime": regime,
                    "category": dl["category"],
                })

        alerts.sort(key=lambda a: a["scadenza_date"])
        return alerts

    @staticmethod
    def _get_quarter_for_deadline(dl: dict) -> int:
        """Determine which quarter a deadline relates to."""
        month = dl["month"]
        if month <= 3:
            return 4  # Q4 of previous year or Q1 current
        elif month <= 6:
            return 1
        elif month <= 9:
            return 2
        else:
            return 3

    @staticmethod
    def _quarter_date_range(year: int, quarter: int) -> tuple[date, date]:
        """Return (start, end) dates for a quarter."""
        if quarter == 1:
            return date(year, 1, 1), date(year, 3, 31)
        elif quarter == 2:
            return date(year, 4, 1), date(year, 6, 30)
        elif quarter == 3:
            return date(year, 7, 1), date(year, 9, 30)
        else:
            return date(year, 10, 1), date(year, 12, 31)
