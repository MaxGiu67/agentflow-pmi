"""Service layer for cash flow prediction (US-25)."""

import logging
import uuid
from datetime import date, datetime, timedelta

from sqlalchemy import select, func as sqla_func
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import BankAccount, Invoice, FiscalDeadline, ActiveInvoice

logger = logging.getLogger(__name__)

# Minimum invoices for reliable prediction
MIN_INVOICES = 20

# Default critical threshold
DEFAULT_SOGLIA_CRITICA = 5000.0

# Stale data threshold (days)
STALE_DAYS = 3


class CashFlowService:
    """Business logic for cash flow prediction and alerts."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def predict(
        self,
        tenant_id: uuid.UUID,
        days: int = 90,
        reference_date: date | None = None,
    ) -> dict:
        """Generate cash flow prediction for the next N days.

        AC-25.1: Chart with current balance + expected income/expenses + projected balance
        AC-25.3: Insufficient data (<20 invoices) -> show available + warning
        AC-25.4: Stale bank data (>3 days) -> banner warning
        """
        ref = reference_date or date.today()

        # Get current balance from bank accounts
        saldo_attuale = await self._get_current_balance(tenant_id)

        # Check for stale bank data (AC-25.4)
        stale_warning = await self._check_stale_data(tenant_id, ref)

        # Get invoice counts
        invoice_count = await self._count_invoices(tenant_id)

        # Determine data source quality (AC-25.3)
        if invoice_count < MIN_INVOICES:
            data_source = "insufficient"
            message = (
                f"Dati disponibili: {invoice_count} fatture. "
                f"Servono almeno {MIN_INVOICES} fatture per una previsione affidabile."
            )
        else:
            data_source = "sufficient"
            message = None

        # Get expected income (fatture attive non pagate)
        entrate_previste = await self._get_expected_income(tenant_id, ref, days)

        # Get expected expenses (fatture passive non pagate + fiscal deadlines)
        uscite_previste = await self._get_expected_expenses(tenant_id, ref, days)

        # Build projection day by day
        projection = []
        running_balance = saldo_attuale
        total_entrate = 0.0
        total_uscite = 0.0

        for i in range(days):
            current_date = ref + timedelta(days=i)
            day_entrate = sum(e["amount"] for e in entrate_previste if e["date"] == current_date)
            day_uscite = sum(e["amount"] for e in uscite_previste if e["date"] == current_date)

            saldo_iniziale = running_balance
            running_balance = running_balance + day_entrate - day_uscite
            total_entrate += day_entrate
            total_uscite += day_uscite

            projection.append({
                "date": current_date.isoformat(),
                "saldo_iniziale": round(saldo_iniziale, 2),
                "entrate": round(day_entrate, 2),
                "uscite": round(day_uscite, 2),
                "saldo_proiettato": round(running_balance, 2),
            })

        return {
            "saldo_attuale": round(saldo_attuale, 2),
            "giorni": days,
            "projection": projection,
            "total_entrate_previste": round(total_entrate, 2),
            "total_uscite_previste": round(total_uscite, 2),
            "saldo_finale_proiettato": round(running_balance, 2),
            "data_source": data_source,
            "invoice_count": invoice_count,
            "min_invoices_required": MIN_INVOICES,
            "message": message,
            "stale_warning": stale_warning,
        }

    async def get_alerts(
        self,
        tenant_id: uuid.UUID,
        soglia_critica: float | None = None,
        days: int = 90,
        reference_date: date | None = None,
    ) -> dict:
        """Get cash flow alerts.

        AC-25.2: Alert on critical threshold (default 5000, configurable)
        AC-25.5: Late payment highlighted with two scenarios
        """
        ref = reference_date or date.today()
        soglia = soglia_critica if soglia_critica is not None else DEFAULT_SOGLIA_CRITICA

        alerts: list[dict] = []

        # Get prediction
        prediction = await self.predict(tenant_id, days=days, reference_date=ref)

        # AC-25.2: Check for critical balance
        for entry in prediction["projection"]:
            if entry["saldo_proiettato"] < soglia:
                alerts.append({
                    "type": "critical_balance",
                    "message": (
                        f"Saldo previsto sotto soglia critica ({soglia:.2f} EUR) "
                        f"il {entry['date']}: {entry['saldo_proiettato']:.2f} EUR"
                    ),
                    "alert_date": entry["date"],
                    "amount": entry["saldo_proiettato"],
                    "severity": "critical",
                    "scenario_optimistic": None,
                    "scenario_pessimistic": None,
                })
                break  # Only first occurrence

        # AC-25.5: Check for late payments
        late_payments = await self._get_late_payments(tenant_id, ref)
        for lp in late_payments:
            # Optimistic: payment arrives in 7 days
            optimistic_balance = prediction["saldo_finale_proiettato"] + lp["amount"]
            # Pessimistic: payment never arrives
            pessimistic_balance = prediction["saldo_finale_proiettato"]

            alerts.append({
                "type": "late_payment",
                "message": (
                    f"Pagamento in ritardo: {lp['description']} - "
                    f"{lp['amount']:.2f} EUR (scadenza {lp['due_date']})"
                ),
                "alert_date": lp["due_date"],
                "amount": lp["amount"],
                "severity": "warning",
                "scenario_optimistic": round(optimistic_balance, 2),
                "scenario_pessimistic": round(pessimistic_balance, 2),
            })

        return {
            "alerts": alerts,
            "soglia_critica": soglia,
            "total": len(alerts),
        }

    async def _get_current_balance(self, tenant_id: uuid.UUID) -> float:
        """Get the sum of balances from all connected bank accounts."""
        result = await self.db.execute(
            select(sqla_func.coalesce(sqla_func.sum(BankAccount.balance), 0.0)).where(
                BankAccount.tenant_id == tenant_id,
                BankAccount.status == "connected",
            )
        )
        return float(result.scalar() or 0.0)

    async def _check_stale_data(self, tenant_id: uuid.UUID, ref: date) -> str | None:
        """Check if bank data is stale (>3 days since last sync). AC-25.4."""
        result = await self.db.execute(
            select(sqla_func.max(BankAccount.last_sync_at)).where(
                BankAccount.tenant_id == tenant_id,
                BankAccount.status == "connected",
            )
        )
        last_sync = result.scalar()

        if last_sync is None:
            return "Nessun conto bancario collegato. I dati di saldo potrebbero non essere aggiornati."

        last_sync_date = last_sync.date() if isinstance(last_sync, datetime) else last_sync
        days_since = (ref - last_sync_date).days

        if days_since > STALE_DAYS:
            return (
                f"Dati bancari non aggiornati da {days_since} giorni. "
                f"Ultima sincronizzazione: {last_sync_date.isoformat()}. "
                "Sincronizzare il conto per dati aggiornati."
            )
        return None

    async def _count_invoices(self, tenant_id: uuid.UUID) -> int:
        """Count total invoices for tenant."""
        result = await self.db.execute(
            select(sqla_func.count(Invoice.id)).where(
                Invoice.tenant_id == tenant_id,
            )
        )
        return int(result.scalar() or 0)

    async def _get_expected_income(
        self, tenant_id: uuid.UUID, ref: date, days: int,
    ) -> list[dict]:
        """Get expected income from unpaid active invoices."""
        end_date = ref + timedelta(days=days)

        # Fatture attive non pagate (active invoices not yet paid)
        result = await self.db.execute(
            select(ActiveInvoice).where(
                ActiveInvoice.tenant_id == tenant_id,
                ActiveInvoice.sdi_status.in_(["sent", "delivered"]),
            )
        )
        active_invoices = result.scalars().all()

        entries = []
        for inv in active_invoices:
            # Estimate payment date: 30 days from invoice date
            estimated_date = inv.data_fattura + timedelta(days=30)
            if ref <= estimated_date <= end_date:
                entries.append({
                    "date": estimated_date,
                    "amount": inv.importo_totale,
                    "description": f"Incasso fattura {inv.numero_fattura}",
                })

        # Also check passive invoices of type "attiva" from Invoice table
        result2 = await self.db.execute(
            select(Invoice).where(
                Invoice.tenant_id == tenant_id,
                Invoice.type == "attiva",
                Invoice.processing_status.in_(["parsed", "categorized", "registered"]),
            )
        )
        invoices = result2.scalars().all()

        for inv in invoices:
            if inv.data_fattura:
                estimated_date = inv.data_fattura + timedelta(days=30)
                if ref <= estimated_date <= end_date:
                    entries.append({
                        "date": estimated_date,
                        "amount": inv.importo_totale or 0.0,
                        "description": f"Incasso fattura {inv.numero_fattura}",
                    })

        return entries

    async def _get_expected_expenses(
        self, tenant_id: uuid.UUID, ref: date, days: int,
    ) -> list[dict]:
        """Get expected expenses from unpaid passive invoices + fiscal deadlines."""
        end_date = ref + timedelta(days=days)
        entries = []

        # Fatture passive non pagate
        result = await self.db.execute(
            select(Invoice).where(
                Invoice.tenant_id == tenant_id,
                Invoice.type == "passiva",
                Invoice.processing_status.in_(["parsed", "categorized", "registered"]),
            )
        )
        passive_invoices = result.scalars().all()

        for inv in passive_invoices:
            if inv.data_fattura:
                # Estimate payment date: 30 days from invoice date
                estimated_date = inv.data_fattura + timedelta(days=30)
                if ref <= estimated_date <= end_date:
                    entries.append({
                        "date": estimated_date,
                        "amount": inv.importo_totale or 0.0,
                        "description": f"Pagamento fattura {inv.numero_fattura}",
                    })

        # Fiscal deadlines (F24, bollo, ritenute)
        result2 = await self.db.execute(
            select(FiscalDeadline).where(
                FiscalDeadline.tenant_id == tenant_id,
                FiscalDeadline.status == "pending",
                FiscalDeadline.due_date >= ref,
                FiscalDeadline.due_date <= end_date,
            )
        )
        deadlines = result2.scalars().all()

        for dl in deadlines:
            entries.append({
                "date": dl.due_date,
                "amount": dl.amount,
                "description": f"Scadenza fiscale: {dl.description}",
            })

        return entries

    async def _get_late_payments(
        self, tenant_id: uuid.UUID, ref: date,
    ) -> list[dict]:
        """Get late payments (invoices past due date). AC-25.5."""
        # Active invoices where estimated payment date is past
        result = await self.db.execute(
            select(ActiveInvoice).where(
                ActiveInvoice.tenant_id == tenant_id,
                ActiveInvoice.sdi_status.in_(["sent", "delivered"]),
            )
        )
        active_invoices = result.scalars().all()

        late = []
        for inv in active_invoices:
            estimated_date = inv.data_fattura + timedelta(days=30)
            if estimated_date < ref:
                late.append({
                    "due_date": estimated_date.isoformat(),
                    "amount": inv.importo_totale,
                    "description": f"Fattura {inv.numero_fattura} - {inv.cliente_nome}",
                })

        return late
