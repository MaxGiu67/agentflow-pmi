"""Tool registry — wraps existing services as callable tools (US-A04).

Each tool is a dict with: name, description, parameters (JSON Schema), handler (async callable).
Handlers accept db (AsyncSession), tenant_id (UUID), and tool-specific keyword arguments.
"""

import logging
import uuid
from datetime import date, datetime

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import (
    Asset,
    Expense,
    FiscalDeadline,
    Invoice,
    JournalEntry,
    JournalLine,
    ChartAccount,
)

logger = logging.getLogger(__name__)


# ============================================================
# Handler implementations
# ============================================================


async def count_invoices_handler(
    db: AsyncSession, tenant_id: uuid.UUID, **kwargs: object
) -> dict:
    """Count invoices by optional month and type filters."""
    conditions = [Invoice.tenant_id == tenant_id]

    month_str = kwargs.get("month")
    if month_str and isinstance(month_str, str) and "-" in month_str:
        try:
            parts = month_str.split("-")
            year = int(parts[0])
            month = int(parts[1])
            start_date = date(year, month, 1)
            if month == 12:
                end_date = date(year + 1, 1, 1)
            else:
                end_date = date(year, month + 1, 1)
            conditions.append(Invoice.data_fattura >= start_date)
            conditions.append(Invoice.data_fattura < end_date)
        except (ValueError, IndexError):
            pass

    inv_type = kwargs.get("type")
    if inv_type:
        conditions.append(Invoice.type == inv_type)

    result = await db.execute(
        select(func.count(Invoice.id)).where(and_(*conditions))
    )
    count = result.scalar() or 0
    return {"count": count, "message": f"{count} fatture trovate"}


async def list_invoices_handler(
    db: AsyncSession, tenant_id: uuid.UUID, **kwargs: object
) -> dict:
    """List invoices with optional filters, limit 20."""
    conditions = [Invoice.tenant_id == tenant_id]

    inv_type = kwargs.get("type")
    if inv_type:
        conditions.append(Invoice.type == inv_type)

    status = kwargs.get("status")
    if status:
        conditions.append(Invoice.processing_status == status)

    limit = int(kwargs.get("limit", 20))

    result = await db.execute(
        select(Invoice)
        .where(and_(*conditions))
        .order_by(Invoice.created_at.desc())
        .limit(limit)
    )
    invoices = result.scalars().all()
    items = [
        {
            "id": str(inv.id),
            "numero": inv.numero_fattura,
            "emittente": inv.emittente_nome,
            "data": str(inv.data_fattura) if inv.data_fattura else None,
            "importo_totale": inv.importo_totale,
            "type": inv.type,
            "status": inv.processing_status,
        }
        for inv in invoices
    ]
    return {"items": items, "count": len(items)}


async def get_invoice_detail_handler(
    db: AsyncSession, tenant_id: uuid.UUID, **kwargs: object
) -> dict:
    """Get a single invoice detail by ID."""
    invoice_id = kwargs.get("invoice_id")
    if not invoice_id:
        return {"error": "invoice_id richiesto"}

    try:
        uid = uuid.UUID(str(invoice_id))
    except ValueError:
        return {"error": "invoice_id non valido"}

    result = await db.execute(
        select(Invoice).where(
            and_(Invoice.id == uid, Invoice.tenant_id == tenant_id)
        )
    )
    inv = result.scalar_one_or_none()
    if not inv:
        return {"error": "Fattura non trovata"}

    return {
        "id": str(inv.id),
        "numero": inv.numero_fattura,
        "emittente": inv.emittente_nome,
        "emittente_piva": inv.emittente_piva,
        "data": str(inv.data_fattura) if inv.data_fattura else None,
        "importo_netto": inv.importo_netto,
        "importo_iva": inv.importo_iva,
        "importo_totale": inv.importo_totale,
        "type": inv.type,
        "category": inv.category,
        "status": inv.processing_status,
    }


async def get_dashboard_summary_handler(
    db: AsyncSession, tenant_id: uuid.UUID, **kwargs: object
) -> dict:
    """Get a summary of dashboard data."""
    # Count invoices by status
    statuses = ["pending", "parsed", "categorized", "registered", "error"]
    counters: dict[str, int] = {"total": 0}

    for s in statuses:
        result = await db.execute(
            select(func.count(Invoice.id)).where(
                and_(
                    Invoice.tenant_id == tenant_id,
                    Invoice.processing_status == s,
                )
            )
        )
        count = result.scalar() or 0
        counters[s] = count
        counters["total"] += count

    return {
        "counters": counters,
        "message": f"{counters['total']} fatture totali, {counters['pending']} in attesa",
    }


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


async def get_journal_entries_handler(
    db: AsyncSession, tenant_id: uuid.UUID, **kwargs: object
) -> dict:
    """Get recent journal entries."""
    limit = int(kwargs.get("limit", 10))
    result = await db.execute(
        select(JournalEntry)
        .where(JournalEntry.tenant_id == tenant_id)
        .order_by(JournalEntry.created_at.desc())
        .limit(limit)
    )
    entries = result.scalars().all()
    items = [
        {
            "id": str(e.id),
            "description": e.description,
            "entry_date": str(e.entry_date),
            "total_debit": e.total_debit,
            "total_credit": e.total_credit,
            "status": e.status,
        }
        for e in entries
    ]
    return {"items": items, "count": len(items)}


async def get_balance_sheet_summary_handler(
    db: AsyncSession, tenant_id: uuid.UUID, **kwargs: object
) -> dict:
    """Get balance sheet summary from journal entries."""
    result = await db.execute(
        select(JournalEntry).where(
            and_(
                JournalEntry.tenant_id == tenant_id,
                JournalEntry.status == "posted",
            )
        )
    )
    entries = result.scalars().all()

    total_debit = sum(e.total_debit for e in entries)
    total_credit = sum(e.total_credit for e in entries)

    return {
        "total_debit": round(total_debit, 2),
        "total_credit": round(total_credit, 2),
        "entries_count": len(entries),
        "balanced": abs(total_debit - total_credit) < 0.01,
    }


async def predict_cashflow_handler(
    db: AsyncSession, tenant_id: uuid.UUID, **kwargs: object
) -> dict:
    """Simplified cashflow prediction based on invoices."""
    # Income: active invoices
    from api.db.models import ActiveInvoice

    active_result = await db.execute(
        select(ActiveInvoice).where(ActiveInvoice.tenant_id == tenant_id)
    )
    active_invoices = active_result.scalars().all()
    total_receivable = sum(inv.importo_totale for inv in active_invoices)

    # Expenses: passive invoices pending
    passive_result = await db.execute(
        select(Invoice).where(
            and_(
                Invoice.tenant_id == tenant_id,
                Invoice.type == "passiva",
            )
        )
    )
    passive_invoices = passive_result.scalars().all()
    total_payable = sum((inv.importo_totale or 0.0) for inv in passive_invoices)

    net_cashflow = round(total_receivable - total_payable, 2)

    return {
        "total_receivable": round(total_receivable, 2),
        "total_payable": round(total_payable, 2),
        "net_cashflow": net_cashflow,
        "message": f"Previsione: entrate €{total_receivable:,.2f}, uscite €{total_payable:,.2f}, saldo netto €{net_cashflow:,.2f}",
    }


async def get_pending_review_handler(
    db: AsyncSession, tenant_id: uuid.UUID, **kwargs: object
) -> dict:
    """Get invoices pending review (categorized but not verified)."""
    result = await db.execute(
        select(Invoice)
        .where(
            and_(
                Invoice.tenant_id == tenant_id,
                Invoice.processing_status == "categorized",
                Invoice.verified == False,  # noqa: E712
            )
        )
        .order_by(Invoice.created_at.desc())
        .limit(20)
    )
    invoices = result.scalars().all()
    items = [
        {
            "id": str(inv.id),
            "numero": inv.numero_fattura,
            "emittente": inv.emittente_nome,
            "importo_totale": inv.importo_totale,
            "category": inv.category,
        }
        for inv in invoices
    ]
    return {"items": items, "count": len(items)}


async def list_expenses_handler(
    db: AsyncSession, tenant_id: uuid.UUID, **kwargs: object
) -> dict:
    """List expenses for the tenant."""
    status = kwargs.get("status")
    conditions = [Expense.tenant_id == tenant_id]
    if status:
        conditions.append(Expense.status == status)

    result = await db.execute(
        select(Expense)
        .where(and_(*conditions))
        .order_by(Expense.created_at.desc())
        .limit(20)
    )
    expenses = result.scalars().all()
    items = [
        {
            "id": str(e.id),
            "description": e.description,
            "amount": e.amount_eur,
            "category": e.category,
            "expense_date": str(e.expense_date),
            "status": e.status,
        }
        for e in expenses
    ]
    return {"items": items, "count": len(items)}


async def list_assets_handler(
    db: AsyncSession, tenant_id: uuid.UUID, **kwargs: object
) -> dict:
    """List fixed assets."""
    result = await db.execute(
        select(Asset)
        .where(Asset.tenant_id == tenant_id)
        .order_by(Asset.created_at.desc())
        .limit(20)
    )
    assets = result.scalars().all()
    items = [
        {
            "id": str(a.id),
            "description": a.description,
            "category": a.category,
            "purchase_amount": a.purchase_amount,
            "residual_value": a.residual_value,
            "status": a.status,
        }
        for a in assets
    ]
    return {"items": items, "count": len(items)}


async def get_ceo_kpi_handler(
    db: AsyncSession, tenant_id: uuid.UUID, **kwargs: object
) -> dict:
    """Get CEO KPI summary."""
    from api.db.models import ActiveInvoice

    today = date.today()
    year = int(kwargs.get("year", today.year))

    # Fatturato YTD
    active_result = await db.execute(
        select(ActiveInvoice).where(ActiveInvoice.tenant_id == tenant_id)
    )
    active_invoices = active_result.scalars().all()
    fatturato_ytd = sum(
        inv.importo_totale for inv in active_invoices
        if inv.data_fattura.year == year
    )

    # Costi YTD
    passive_result = await db.execute(
        select(Invoice).where(
            and_(Invoice.tenant_id == tenant_id, Invoice.type == "passiva")
        )
    )
    passive_invoices = passive_result.scalars().all()
    costi_ytd = sum(
        (inv.importo_totale or 0.0) for inv in passive_invoices
        if inv.data_fattura and inv.data_fattura.year == year
    )

    ebitda = round(fatturato_ytd - costi_ytd, 2)

    return {
        "fatturato_ytd": round(fatturato_ytd, 2),
        "costi_ytd": round(costi_ytd, 2),
        "ebitda": ebitda,
        "year": year,
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


# ============================================================
# Tool definitions registry
# ============================================================


TOOLS: list[dict] = [
    {
        "name": "count_invoices",
        "description": "Conta il numero di fatture per periodo e tipo (emesse/ricevute)",
        "parameters": {
            "type": "object",
            "properties": {
                "month": {"type": "string", "description": "Mese in formato YYYY-MM"},
                "type": {"type": "string", "enum": ["passiva", "attiva"], "description": "Tipo fattura"},
            },
        },
        "handler": count_invoices_handler,
    },
    {
        "name": "list_invoices",
        "description": "Elenca le fatture con filtri opzionali per tipo e stato",
        "parameters": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["passiva", "attiva"]},
                "status": {"type": "string", "enum": ["pending", "parsed", "categorized", "registered", "error"]},
                "limit": {"type": "integer", "description": "Numero massimo di risultati"},
            },
        },
        "handler": list_invoices_handler,
    },
    {
        "name": "get_invoice_detail",
        "description": "Ottieni i dettagli di una fattura specifica dato il suo ID",
        "parameters": {
            "type": "object",
            "properties": {
                "invoice_id": {"type": "string", "description": "UUID della fattura"},
            },
            "required": ["invoice_id"],
        },
        "handler": get_invoice_detail_handler,
    },
    {
        "name": "get_dashboard_summary",
        "description": "Mostra un riepilogo della dashboard con contatori fatture per stato",
        "parameters": {"type": "object", "properties": {}},
        "handler": get_dashboard_summary_handler,
    },
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
        "name": "get_journal_entries",
        "description": "Elenca le ultime registrazioni contabili in prima nota",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Numero massimo di risultati"},
            },
        },
        "handler": get_journal_entries_handler,
    },
    {
        "name": "get_balance_sheet_summary",
        "description": "Mostra un riepilogo dello stato patrimoniale (totali dare/avere)",
        "parameters": {"type": "object", "properties": {}},
        "handler": get_balance_sheet_summary_handler,
    },
    {
        "name": "predict_cashflow",
        "description": "Prevede il cash flow basandosi su fatture attive e passive",
        "parameters": {"type": "object", "properties": {}},
        "handler": predict_cashflow_handler,
    },
    {
        "name": "get_pending_review",
        "description": "Mostra le fatture categorizzate in attesa di verifica umana",
        "parameters": {"type": "object", "properties": {}},
        "handler": get_pending_review_handler,
    },
    {
        "name": "list_expenses",
        "description": "Elenca le note spese del tenant, con filtro opzionale per stato",
        "parameters": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["submitted", "approved", "rejected", "reimbursed"]},
            },
        },
        "handler": list_expenses_handler,
    },
    {
        "name": "list_assets",
        "description": "Elenca i cespiti (beni strumentali) del tenant",
        "parameters": {"type": "object", "properties": {}},
        "handler": list_assets_handler,
    },
    {
        "name": "get_ceo_kpi",
        "description": "Mostra i KPI per il CEO: fatturato YTD, costi, EBITDA",
        "parameters": {
            "type": "object",
            "properties": {
                "year": {"type": "integer", "description": "Anno di riferimento"},
            },
        },
        "handler": get_ceo_kpi_handler,
    },
    {
        "name": "sync_cassetto",
        "description": "Controlla lo stato di sincronizzazione del cassetto fiscale",
        "parameters": {"type": "object", "properties": {}},
        "handler": sync_cassetto_handler,
    },
]


def get_tools_by_name() -> dict:
    """Return a dict mapping tool name -> tool definition."""
    return {tool["name"]: tool for tool in TOOLS}


def get_tools_description() -> str:
    """Return a formatted description of all tools for the system prompt."""
    lines = []
    for tool in TOOLS:
        params = tool["parameters"].get("properties", {})
        param_str = ", ".join(
            f"{k}: {v.get('type', 'string')}"
            for k, v in params.items()
        )
        lines.append(f"- {tool['name']}({param_str}): {tool['description']}")
    return "\n".join(lines)
