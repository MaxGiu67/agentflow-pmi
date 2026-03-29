"""Alert Agent service (US-66).

Scans for anomalies: overdue invoices 30+ days, unusual amounts 3x std dev.
"""

import logging
import math
import uuid
from datetime import date, timedelta

from sqlalchemy import select, func as sqla_func
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import Invoice, BankTransaction, BankAccount

logger = logging.getLogger(__name__)


class AlertService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def scan(self, tenant_id: uuid.UUID) -> dict:
        """Scan for anomalies and generate alerts (US-66)."""
        alerts = []

        # 1. Overdue invoices (30+ days unpaid passive)
        overdue_alerts = await self._check_overdue_invoices(tenant_id)
        alerts.extend(overdue_alerts)

        # 2. Unusual transaction amounts (3x std dev)
        unusual_alerts = await self._check_unusual_amounts(tenant_id)
        alerts.extend(unusual_alerts)

        # 3. Missing invoice payments (active invoices 60+ days)
        missing_payments = await self._check_missing_payments(tenant_id)
        alerts.extend(missing_payments)

        return {
            "alerts": alerts,
            "total": len(alerts),
            "critical_count": sum(1 for a in alerts if a["severity"] == "critical"),
            "warning_count": sum(1 for a in alerts if a["severity"] == "warning"),
            "info_count": sum(1 for a in alerts if a["severity"] == "info"),
        }

    async def _check_overdue_invoices(self, tenant_id: uuid.UUID) -> list:
        """Check for passive invoices unpaid for 30+ days."""
        cutoff = date.today() - timedelta(days=30)
        result = await self.db.execute(
            select(Invoice).where(
                Invoice.tenant_id == tenant_id,
                Invoice.type == "passiva",
                Invoice.data_fattura <= cutoff,
                Invoice.processing_status != "registered",
            ).limit(20)
        )
        invoices = result.scalars().all()

        alerts = []
        for inv in invoices:
            days_overdue = (date.today() - inv.data_fattura).days if inv.data_fattura else 0
            severity = "critical" if days_overdue > 60 else "warning"
            alerts.append({
                "type": "overdue_invoice",
                "severity": severity,
                "title": f"Fattura scaduta da {days_overdue} giorni",
                "description": f"{inv.emittente_nome} - {inv.numero_fattura} - {inv.importo_totale} EUR",
                "entity_id": str(inv.id),
                "amount": inv.importo_totale,
                "days_overdue": days_overdue,
            })

        return alerts

    async def _check_unusual_amounts(self, tenant_id: uuid.UUID) -> list:
        """Check for transactions with amounts > 3x standard deviation."""
        # Get bank accounts
        accounts_result = await self.db.execute(
            select(BankAccount.id).where(BankAccount.tenant_id == tenant_id)
        )
        account_ids = [row[0] for row in accounts_result.fetchall()]

        if not account_ids:
            return []

        # Calculate mean and stddev
        stats = await self.db.execute(
            select(
                sqla_func.avg(sqla_func.abs(BankTransaction.amount)),
                sqla_func.count(BankTransaction.id),
            ).where(BankTransaction.bank_account_id.in_(account_ids))
        )
        row = stats.fetchone()
        if not row or not row[0] or row[1] < 5:
            return []

        avg_amount = float(row[0])

        # Calculate stddev manually (SQLite doesn't have built-in stddev)
        all_amounts_result = await self.db.execute(
            select(sqla_func.abs(BankTransaction.amount)).where(
                BankTransaction.bank_account_id.in_(account_ids)
            )
        )
        amounts = [float(r[0]) for r in all_amounts_result.fetchall()]

        if len(amounts) < 5:
            return []

        variance = sum((a - avg_amount) ** 2 for a in amounts) / len(amounts)
        stddev = math.sqrt(variance) if variance > 0 else 0

        if stddev == 0:
            return []

        threshold = avg_amount + 3 * stddev

        # Find outlier transactions
        result = await self.db.execute(
            select(BankTransaction).where(
                BankTransaction.bank_account_id.in_(account_ids),
                sqla_func.abs(BankTransaction.amount) > threshold,
            ).limit(10)
        )
        outliers = result.scalars().all()

        alerts = []
        for tx in outliers:
            alerts.append({
                "type": "unusual_amount",
                "severity": "warning",
                "title": f"Importo anomalo: {abs(tx.amount)} EUR",
                "description": f"Transazione {tx.description or tx.counterpart or 'N/D'} - Media: {round(avg_amount, 2)} EUR, Soglia: {round(threshold, 2)} EUR",
                "entity_id": str(tx.id),
                "amount": abs(tx.amount),
                "threshold": round(threshold, 2),
            })

        return alerts

    async def _check_missing_payments(self, tenant_id: uuid.UUID) -> list:
        """Check for active invoices where payment hasn't arrived in 60+ days."""
        cutoff = date.today() - timedelta(days=60)
        result = await self.db.execute(
            select(Invoice).where(
                Invoice.tenant_id == tenant_id,
                Invoice.type == "attiva",
                Invoice.data_fattura <= cutoff,
            ).limit(10)
        )
        invoices = result.scalars().all()

        alerts = []
        for inv in invoices:
            days = (date.today() - inv.data_fattura).days if inv.data_fattura else 0
            alerts.append({
                "type": "missing_payment",
                "severity": "info",
                "title": f"Incasso non ricevuto da {days} giorni",
                "description": f"Fattura attiva {inv.numero_fattura} - {inv.importo_totale} EUR",
                "entity_id": str(inv.id),
                "amount": inv.importo_totale,
                "days_overdue": days,
            })

        return alerts
