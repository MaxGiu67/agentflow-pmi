"""Scadenze/cashflow tool handlers and definitions."""

import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession


async def predict_cashflow_handler(
    db: AsyncSession, tenant_id: uuid.UUID, **kwargs: object
) -> dict:
    """Simplified cashflow prediction based on Invoice table (type attiva/passiva)."""
    from sqlalchemy import text as sa_text

    # Income: fatture emesse (type='attiva')
    recv_result = await db.execute(
        sa_text(
            "SELECT COALESCE(SUM(importo_totale), 0) FROM invoices "
            "WHERE tenant_id = :tid AND type = 'attiva'"
        ),
        {"tid": str(tenant_id)},
    )
    total_receivable = float(recv_result.scalar() or 0)

    # Expenses: fatture ricevute (type='passiva')
    pay_result = await db.execute(
        sa_text(
            "SELECT COALESCE(SUM(importo_totale), 0) FROM invoices "
            "WHERE tenant_id = :tid AND type = 'passiva'"
        ),
        {"tid": str(tenant_id)},
    )
    total_payable = float(pay_result.scalar() or 0)

    net_cashflow = round(total_receivable - total_payable, 2)

    return {
        "total_receivable": round(total_receivable, 2),
        "total_payable": round(total_payable, 2),
        "net_cashflow": net_cashflow,
        "message": f"Previsione: entrate \u20ac{total_receivable:,.2f}, uscite \u20ac{total_payable:,.2f}, saldo netto \u20ac{net_cashflow:,.2f}",
    }


SCADENZARIO_TOOLS: list[dict] = [
    {
        "name": "predict_cashflow",
        "description": "Prevede il cash flow basandosi su fatture attive e passive",
        "parameters": {"type": "object", "properties": {}},
        "handler": predict_cashflow_handler,
    },
]
