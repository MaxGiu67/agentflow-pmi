"""Fisco/F24/IVA tool handlers and definitions."""

import uuid
from datetime import date

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import FiscalDeadline, Invoice


async def get_deadlines_handler(
    db: AsyncSession, tenant_id: uuid.UUID, **kwargs: object
) -> dict:
    """Get upcoming fiscal deadlines."""
    today = date.today()
    result = await db.execute(
        select(FiscalDeadline)
        .where(
            and_(
                FiscalDeadline.tenant_id == tenant_id,
                FiscalDeadline.due_date >= today,
                FiscalDeadline.status == "pending",
            )
        )
        .order_by(FiscalDeadline.due_date)
        .limit(10)
    )
    deadlines = result.scalars().all()
    items = [
        {
            "id": str(d.id),
            "code": d.code,
            "description": d.description,
            "amount": d.amount,
            "due_date": str(d.due_date),
            "status": d.status,
        }
        for d in deadlines
    ]
    return {"items": items, "count": len(items)}


async def get_fiscal_alerts_handler(
    db: AsyncSession, tenant_id: uuid.UUID, **kwargs: object
) -> dict:
    """Get overdue fiscal deadlines (alerts)."""
    today = date.today()
    result = await db.execute(
        select(FiscalDeadline)
        .where(
            and_(
                FiscalDeadline.tenant_id == tenant_id,
                FiscalDeadline.due_date < today,
                FiscalDeadline.status == "pending",
            )
        )
        .order_by(FiscalDeadline.due_date)
    )
    overdue = result.scalars().all()
    items = [
        {
            "id": str(d.id),
            "code": d.code,
            "description": d.description,
            "amount": d.amount,
            "due_date": str(d.due_date),
        }
        for d in overdue
    ]
    return {
        "items": items,
        "count": len(items),
        "message": f"{len(items)} scadenze fiscali in ritardo" if items else "Nessuna scadenza in ritardo",
    }


async def sync_cassetto_handler(
    db: AsyncSession, tenant_id: uuid.UUID, **kwargs: object
) -> dict:
    """Simplified cassetto fiscale sync status check."""
    result = await db.execute(
        select(func.count(Invoice.id)).where(
            and_(
                Invoice.tenant_id == tenant_id,
                Invoice.source == "cassetto_fiscale",
            )
        )
    )
    count = result.scalar() or 0
    return {
        "synced_invoices": count,
        "message": f"{count} fatture sincronizzate dal cassetto fiscale",
    }


FISCAL_TOOLS: list[dict] = [
    {
        "name": "get_deadlines",
        "description": "Mostra le prossime scadenze fiscali in scadenza",
        "parameters": {"type": "object", "properties": {}},
        "handler": get_deadlines_handler,
    },
    {
        "name": "get_fiscal_alerts",
        "description": "Mostra le scadenze fiscali in ritardo (alert)",
        "parameters": {"type": "object", "properties": {}},
        "handler": get_fiscal_alerts_handler,
    },
    {
        "name": "sync_cassetto",
        "description": "Controlla lo stato di sincronizzazione del cassetto fiscale",
        "parameters": {"type": "object", "properties": {}},
        "handler": sync_cassetto_handler,
    },
]
