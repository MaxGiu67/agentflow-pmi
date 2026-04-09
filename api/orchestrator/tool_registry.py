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
    Budget,
    DashboardLayout,
    Expense,
    FiscalDeadline,
    Invoice,
    JournalEntry,
)
from api.modules.dashboard.default_widgets import DEFAULT_WIDGETS
from api.adapters.odoo_crm import OdooCRMClient

logger = logging.getLogger(__name__)


# ============================================================
# Handler implementations
# ============================================================


async def count_invoices_handler(
    db: AsyncSession, tenant_id: uuid.UUID, **kwargs: object
) -> dict:
    """Count invoices by optional month, type, year, and search query filters."""
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

    # Year filter (from context or explicit parameter)
    year_val = kwargs.get("year")
    if year_val is not None:
        try:
            y = int(year_val)
            conditions.append(Invoice.data_fattura >= date(y, 1, 1))
            conditions.append(Invoice.data_fattura < date(y + 1, 1, 1))
        except (ValueError, TypeError):
            pass

    # Search query — search in emittente_nome, numero_fattura, and destinatario_nome
    query = kwargs.get("query")
    if query and isinstance(query, str):
        like_pattern = f"%{query}%"
        from sqlalchemy import or_, cast, String as SAString
        conditions.append(
            or_(
                Invoice.emittente_nome.ilike(like_pattern),
                Invoice.numero_fattura.ilike(like_pattern),
                cast(Invoice.structured_data["destinatario_nome"], SAString).ilike(like_pattern),
            )
        )

    result = await db.execute(
        select(func.count(Invoice.id)).where(and_(*conditions))
    )
    count = result.scalar() or 0

    content_blocks = [{
        "type": "stat_row",
        "items": [{"label": "Fatture trovate", "value": count, "format": "number"}],
    }]
    return {"count": count, "message": f"{count} fatture trovate", "content_blocks": content_blocks}


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

    # Year filter (from context or explicit parameter)
    year_val = kwargs.get("year")
    if year_val is not None:
        try:
            y = int(year_val)
            conditions.append(Invoice.data_fattura >= date(y, 1, 1))
            conditions.append(Invoice.data_fattura < date(y + 1, 1, 1))
        except (ValueError, TypeError):
            pass

    # Month filter (YYYY-MM format)
    month_val = kwargs.get("month")
    if month_val and isinstance(month_val, str) and "-" in month_val:
        try:
            parts = month_val.split("-")
            y, m = int(parts[0]), int(parts[1])
            conditions.append(Invoice.data_fattura >= date(y, m, 1))
            next_m = m + 1 if m < 12 else 1
            next_y = y if m < 12 else y + 1
            conditions.append(Invoice.data_fattura < date(next_y, next_m, 1))
        except (ValueError, TypeError, IndexError):
            pass

    # Search query — search in emittente_nome, numero_fattura, and destinatario_nome
    query = kwargs.get("query")
    if query and isinstance(query, str):
        like_pattern = f"%{query}%"
        from sqlalchemy import or_, cast, String as SAString
        conditions.append(
            or_(
                Invoice.emittente_nome.ilike(like_pattern),
                Invoice.numero_fattura.ilike(like_pattern),
                cast(Invoice.structured_data["destinatario_nome"], SAString).ilike(like_pattern),
            )
        )

    limit = int(kwargs.get("limit", 20))

    result = await db.execute(
        select(Invoice)
        .where(and_(*conditions))
        .order_by(Invoice.data_fattura.desc().nulls_last())
        .limit(limit)
    )
    invoices = result.scalars().all()
    items = [
        {
            "id": str(inv.id),
            "numero": inv.numero_fattura,
            "emittente": inv.emittente_nome,
            "destinatario": (inv.structured_data or {}).get("destinatario_nome") if inv.structured_data else None,
            "data": str(inv.data_fattura) if inv.data_fattura else None,
            "importo_totale": inv.importo_totale,
            "type": inv.type,
            "status": inv.processing_status,
        }
        for inv in invoices
    ]

    # Content blocks for rich rendering
    content_blocks = []
    if items:
        content_blocks.append({
            "type": "table",
            "title": f"Fatture ({len(items)} risultati)",
            "columns": ["Data", "Numero", "Controparte", "Tipo", "Importo"],
            "rows": [
                [
                    it.get("data", "-") or "-",
                    it.get("numero", "-") or "-",
                    it.get("destinatario") or it.get("emittente") or "-",
                    "Emessa" if it.get("type") == "attiva" else "Ricevuta",
                    f"\u20ac{(it.get('importo_totale') or 0):,.2f}",
                ]
                for it in items[:20]
            ],
        })

    return {"items": items, "count": len(items), "content_blocks": content_blocks}


def _format_invoice(inv: object) -> dict:
    """Format an Invoice model instance into a response dict."""
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


async def get_invoice_detail_handler(
    db: AsyncSession, tenant_id: uuid.UUID, **kwargs: object
) -> dict:
    """Get a single invoice detail by ID or numero_fattura."""
    invoice_id = kwargs.get("invoice_id", "")
    if not invoice_id:
        return {"error": "invoice_id richiesto"}

    # Try by UUID first
    try:
        uid = uuid.UUID(str(invoice_id))
        result = await db.execute(
            select(Invoice).where(
                and_(Invoice.id == uid, Invoice.tenant_id == tenant_id)
            )
        )
        inv = result.scalar_one_or_none()
        if inv:
            return _format_invoice(inv)
    except (ValueError, AttributeError):
        pass

    # Try by numero_fattura (exact match)
    result = await db.execute(
        select(Invoice).where(
            and_(
                Invoice.numero_fattura == str(invoice_id),
                Invoice.tenant_id == tenant_id,
            )
        )
    )
    inv = result.scalar_one_or_none()
    if inv:
        return _format_invoice(inv)

    # Try partial match
    result = await db.execute(
        select(Invoice).where(
            and_(
                Invoice.numero_fattura.ilike(f"%{invoice_id}%"),
                Invoice.tenant_id == tenant_id,
            )
        ).limit(1)
    )
    inv = result.scalar_one_or_none()
    if inv:
        return _format_invoice(inv)

    return {"error": f"Fattura '{invoice_id}' non trovata"}


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
    """Get CEO KPI summary using Invoice table (not ActiveInvoice)."""
    from sqlalchemy import text as sa_text

    today = date.today()
    year = int(kwargs.get("year", today.year))

    # Fatturato YTD — fatture emesse (type='attiva') filtrate per anno con SQL
    fatturato_result = await db.execute(
        sa_text(
            "SELECT COALESCE(SUM(importo_totale), 0) FROM invoices "
            "WHERE tenant_id = :tid AND type = 'attiva' "
            "AND EXTRACT(YEAR FROM data_fattura) = :yr"
        ),
        {"tid": str(tenant_id), "yr": year},
    )
    fatturato_ytd = float(fatturato_result.scalar() or 0)

    # Costi YTD — fatture ricevute (type='passiva') filtrate per anno con SQL
    costi_result = await db.execute(
        sa_text(
            "SELECT COALESCE(SUM(importo_totale), 0) FROM invoices "
            "WHERE tenant_id = :tid AND type = 'passiva' "
            "AND EXTRACT(YEAR FROM data_fattura) = :yr"
        ),
        {"tid": str(tenant_id), "yr": year},
    )
    costi_ytd = float(costi_result.scalar() or 0)

    # Conteggi fatture
    count_attive_result = await db.execute(
        sa_text(
            "SELECT COUNT(*) FROM invoices "
            "WHERE tenant_id = :tid AND type = 'attiva' "
            "AND EXTRACT(YEAR FROM data_fattura) = :yr"
        ),
        {"tid": str(tenant_id), "yr": year},
    )
    count_attive = int(count_attive_result.scalar() or 0)

    count_passive_result = await db.execute(
        sa_text(
            "SELECT COUNT(*) FROM invoices "
            "WHERE tenant_id = :tid AND type = 'passiva' "
            "AND EXTRACT(YEAR FROM data_fattura) = :yr"
        ),
        {"tid": str(tenant_id), "yr": year},
    )
    count_passive = int(count_passive_result.scalar() or 0)

    ebitda = round(fatturato_ytd - costi_ytd, 2)

    # Content blocks for dashboard rendering
    content_blocks = [
        {
            "type": "stat_row",
            "items": [
                {"label": "Fatturato", "value": round(fatturato_ytd, 2), "format": "currency", "sub": f"{count_attive} fatture"},
                {"label": "Costi", "value": round(costi_ytd, 2), "format": "currency", "sub": f"{count_passive} fatture"},
                {"label": "EBITDA", "value": ebitda, "format": "currency"},
            ],
        },
    ]

    # Monthly breakdown for bar chart
    try:
        monthly_result = await db.execute(
            sa_text(
                "SELECT EXTRACT(MONTH FROM data_fattura)::int AS m, type, "
                "COALESCE(SUM(importo_totale), 0) AS tot "
                "FROM invoices WHERE tenant_id = :tid AND EXTRACT(YEAR FROM data_fattura) = :yr "
                "GROUP BY m, type ORDER BY m"
            ),
            {"tid": str(tenant_id), "yr": year},
        )
        month_labels = ["", "Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]
        month_data: dict[int, dict] = {}
        for row in monthly_result.fetchall():
            m = int(row[0])
            if m not in month_data:
                month_data[m] = {"label": month_labels[m], "Emesse": 0, "Ricevute": 0}
            if row[1] == "attiva":
                month_data[m]["Emesse"] = round(float(row[2]), 2)
            elif row[1] == "passiva":
                month_data[m]["Ricevute"] = round(float(row[2]), 2)
    except Exception as e:
        logger.error("Monthly breakdown query failed: %s", e)
        month_data = {}

    if month_data:
        content_blocks.append({
            "type": "bar_chart",
            "title": f"Fatturato Mensile {year}",
            "data": [month_data[m] for m in sorted(month_data.keys())],
            "keys": ["Emesse", "Ricevute"],
            "colors": ["#22c55e", "#f97316"],
        })

    return {
        "fatturato_ytd": round(fatturato_ytd, 2),
        "costi_ytd": round(costi_ytd, 2),
        "ebitda": ebitda,
        "year": year,
        "fatture_emesse": count_attive,
        "fatture_ricevute": count_passive,
        "content_blocks": content_blocks,
    }


async def modify_dashboard_handler(
    db: AsyncSession, tenant_id: uuid.UUID, **kwargs: object
) -> dict:
    """Add, remove, or update a widget in the user's dashboard."""
    action = kwargs.get("action", "add")
    user_id = kwargs.get("user_id")

    if not user_id:
        return {"error": "user_id richiesto"}

    try:
        uid = uuid.UUID(str(user_id))
    except ValueError:
        return {"error": "user_id non valido"}

    result = await db.execute(
        select(DashboardLayout).where(
            DashboardLayout.user_id == uid,
            DashboardLayout.tenant_id == tenant_id,
        )
    )
    layout = result.scalar_one_or_none()
    if layout is None:
        layout = DashboardLayout(
            tenant_id=tenant_id,
            user_id=uid,
            name="default",
            year=datetime.now().year,
            widgets=list(DEFAULT_WIDGETS),
        )
        db.add(layout)
        await db.flush()

    widgets: list[dict] = list(layout.widgets or [])

    if action == "add":
        title = kwargs.get("title", "Nuovo Widget")
        widget_type = kwargs.get("widget_type", "stat_card")
        config = kwargs.get("config", {})
        if not isinstance(config, dict):
            config = {}
        data_source = kwargs.get("data_source", "yearly_stats")
        data_path = kwargs.get("data_path", "")

        max_y = max((w.get("layout", {}).get("y", 0) + w.get("layout", {}).get("h", 2) for w in widgets), default=0)
        new_widget = {
            "id": f"w_custom_{uuid.uuid4().hex[:8]}",
            "type": widget_type,
            "title": title,
            "data_source": data_source,
            "data_path": data_path,
            "config": config,
            "layout": {"x": 0, "y": max_y, "w": 6, "h": 3},
        }
        widgets.append(new_widget)
        layout.widgets = widgets
        await db.flush()
        return {"message": f"Widget '{title}' aggiunto alla dashboard", "widget": new_widget}

    elif action == "remove":
        title = kwargs.get("title", "")
        original_len = len(widgets)
        widgets = [w for w in widgets if w.get("title", "").lower() != str(title).lower()]
        layout.widgets = widgets
        await db.flush()
        removed = original_len - len(widgets)
        if removed > 0:
            return {"message": f"Widget '{title}' rimosso dalla dashboard"}
        return {"message": f"Widget '{title}' non trovato nella dashboard"}

    elif action == "update":
        title = kwargs.get("title", "")
        config = kwargs.get("config", {})
        if not isinstance(config, dict):
            config = {}
        found = False
        for w in widgets:
            if w.get("title", "").lower() == str(title).lower():
                w["config"] = {**w.get("config", {}), **config}
                found = True
                break
        layout.widgets = widgets
        await db.flush()
        if found:
            return {"message": f"Widget '{title}' aggiornato"}
        return {"message": f"Widget '{title}' non trovato nella dashboard"}

    return {"error": f"Azione '{action}' non supportata. Usa: add, remove, update"}


async def get_top_clients_handler(
    db: AsyncSession, tenant_id: uuid.UUID, **kwargs: object
) -> dict:
    """Get top clients/suppliers by invoice volume and amount."""
    from sqlalchemy import text as sa_text

    year = int(kwargs.get("year", date.today().year))
    inv_type = kwargs.get("type", "attiva")  # attiva=clienti, passiva=fornitori
    limit = int(kwargs.get("limit", 10))

    label = "Clienti" if inv_type == "attiva" else "Fornitori"

    # For attiva (emesse): group by destinatario_nome from structured_data
    # For passiva (ricevute): group by emittente_nome
    if inv_type == "attiva":
        query = sa_text(
            "SELECT structured_data->>'destinatario_nome' AS nome, "
            "COUNT(*) AS num_fatture, COALESCE(SUM(importo_totale), 0) AS totale "
            "FROM invoices "
            "WHERE tenant_id = :tid AND type = 'attiva' "
            "AND EXTRACT(YEAR FROM data_fattura) = :yr "
            "AND structured_data->>'destinatario_nome' IS NOT NULL "
            "GROUP BY structured_data->>'destinatario_nome' "
            "ORDER BY totale DESC LIMIT :lim"
        )
    else:
        query = sa_text(
            "SELECT emittente_nome AS nome, "
            "COUNT(*) AS num_fatture, COALESCE(SUM(importo_totale), 0) AS totale "
            "FROM invoices "
            "WHERE tenant_id = :tid AND type = 'passiva' "
            "AND EXTRACT(YEAR FROM data_fattura) = :yr "
            "AND emittente_nome IS NOT NULL AND emittente_nome != '' "
            "GROUP BY emittente_nome "
            "ORDER BY totale DESC LIMIT :lim"
        )

    result = await db.execute(query, {"tid": str(tenant_id), "yr": year, "lim": limit})
    rows = result.fetchall()

    items = [
        {"nome": row[0], "fatture": int(row[1]), "totale": round(float(row[2]), 2)}
        for row in rows
    ]

    # Content blocks
    content_blocks = []
    if items:
        content_blocks.append({
            "type": "table",
            "title": f"Top {len(items)} {label} {year}",
            "columns": [label[:-1], "Fatture", "Totale"],
            "rows": [
                [it["nome"], str(it["fatture"]), f"\u20ac{it['totale']:,.2f}"]
                for it in items
            ],
        })
        # Bar chart for top entries
        content_blocks.append({
            "type": "bar_chart",
            "title": f"Top {min(len(items), 10)} {label} per fatturato {year}",
            "data": [
                {"label": (it["nome"] or "")[:20], "Totale": it["totale"]}
                for it in items[:10]
            ],
            "keys": ["Totale"],
            "colors": ["#3b82f6"] if inv_type == "attiva" else ["#f97316"],
        })

    return {
        "items": items,
        "count": len(items),
        "label": label,
        "year": year,
        "content_blocks": content_blocks,
        "message": f"Top {len(items)} {label.lower()} {year}: {items[0]['nome']} ({items[0]['fatture']} fatture, \u20ac{items[0]['totale']:,.2f})" if items else f"Nessun {label.lower()} trovato per {year}",
    }


MONTH_LABELS = [
    "", "Gen", "Feb", "Mar", "Apr", "Mag", "Giu",
    "Lug", "Ago", "Set", "Ott", "Nov", "Dic",
]


async def get_period_stats_handler(
    db: AsyncSession, tenant_id: uuid.UUID, **kwargs: object
) -> dict:
    """Get KPI stats for a period (month, quarter, year) with content blocks for rich rendering."""
    from sqlalchemy import text as sa_text

    year = int(kwargs.get("year", date.today().year))
    month_start = kwargs.get("month_start")
    month_end = kwargs.get("month_end")

    # Default: full year
    if month_start is None:
        month_start = 1
        month_end = 12
    month_start = int(month_start)
    month_end = int(month_end)

    # Period label
    if month_start == month_end:
        period_label = f"{MONTH_LABELS[month_start]} {year}"
    elif month_end - month_start == 2:
        q_num = (month_start - 1) // 3 + 1
        period_label = f"Q{q_num} {year}"
    else:
        period_label = str(year)

    # Monthly breakdown
    monthly_data = []
    for m in range(month_start, month_end + 1):
        # Emesse
        r_att = await db.execute(
            sa_text(
                "SELECT COALESCE(SUM(importo_totale), 0), COUNT(*) FROM invoices "
                "WHERE tenant_id = :tid AND type = 'attiva' "
                "AND EXTRACT(YEAR FROM data_fattura) = :yr "
                "AND EXTRACT(MONTH FROM data_fattura) = :m"
            ),
            {"tid": str(tenant_id), "yr": year, "m": m},
        )
        row_att = r_att.fetchone()
        emesse_tot = float(row_att[0]) if row_att else 0
        emesse_cnt = int(row_att[1]) if row_att else 0

        # Ricevute
        r_pas = await db.execute(
            sa_text(
                "SELECT COALESCE(SUM(importo_totale), 0), COUNT(*) FROM invoices "
                "WHERE tenant_id = :tid AND type = 'passiva' "
                "AND EXTRACT(YEAR FROM data_fattura) = :yr "
                "AND EXTRACT(MONTH FROM data_fattura) = :m"
            ),
            {"tid": str(tenant_id), "yr": year, "m": m},
        )
        row_pas = r_pas.fetchone()
        ricevute_tot = float(row_pas[0]) if row_pas else 0
        ricevute_cnt = int(row_pas[1]) if row_pas else 0

        monthly_data.append({
            "label": MONTH_LABELS[m],
            "emesse": round(emesse_tot, 2),
            "ricevute": round(ricevute_tot, 2),
            "emesse_count": emesse_cnt,
            "ricevute_count": ricevute_cnt,
        })

    # Totals
    tot_emesse = sum(m["emesse"] for m in monthly_data)
    tot_ricevute = sum(m["ricevute"] for m in monthly_data)
    tot_emesse_cnt = sum(m["emesse_count"] for m in monthly_data)
    tot_ricevute_cnt = sum(m["ricevute_count"] for m in monthly_data)
    ebitda = round(tot_emesse - tot_ricevute, 2)

    # Build content blocks for rich rendering
    content_blocks = [
        {
            "type": "stat_row",
            "items": [
                {"label": "Fatturato", "value": round(tot_emesse, 2), "format": "currency", "sub": f"{tot_emesse_cnt} fatture"},
                {"label": "Costi", "value": round(tot_ricevute, 2), "format": "currency", "sub": f"{tot_ricevute_cnt} fatture"},
                {"label": "EBITDA", "value": ebitda, "format": "currency"},
            ],
        },
    ]

    # Bar chart if multiple months
    if month_end - month_start >= 1:
        content_blocks.append({
            "type": "bar_chart",
            "title": f"Fatturato Mensile {period_label}",
            "data": [
                {"label": m["label"], "Emesse": m["emesse"], "Ricevute": m["ricevute"]}
                for m in monthly_data
            ],
            "keys": ["Emesse", "Ricevute"],
            "colors": ["#22c55e", "#f97316"],
        })

    # Table with monthly detail
    if month_end - month_start >= 1:
        content_blocks.append({
            "type": "table",
            "title": f"Dettaglio {period_label}",
            "columns": ["Mese", "Emesse", "Ricevute", "Margine"],
            "rows": [
                [
                    m["label"],
                    f"€{m['emesse']:,.2f}",
                    f"€{m['ricevute']:,.2f}",
                    f"€{m['emesse'] - m['ricevute']:,.2f}",
                ]
                for m in monthly_data
            ],
        })

    return {
        "period": period_label,
        "fatturato": round(tot_emesse, 2),
        "costi": round(tot_ricevute, 2),
        "ebitda": ebitda,
        "fatture_emesse": tot_emesse_cnt,
        "fatture_ricevute": tot_ricevute_cnt,
        "monthly_data": monthly_data,
        "content_blocks": content_blocks,
        "message": f"{period_label}: fatturato €{tot_emesse:,.2f}, costi €{tot_ricevute:,.2f}, EBITDA €{ebitda:,.2f}",
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


async def apertura_conti_handler(
    db: AsyncSession, tenant_id: uuid.UUID, **kwargs: object
) -> dict:
    """Guide user through balance sheet initialization (saldi bilancio)."""
    # Check current status — bilancio imported = journal entries with "apertura"
    bilancio_count = await db.scalar(
        select(func.count(JournalEntry.id)).where(
            JournalEntry.tenant_id == tenant_id,
            JournalEntry.description.ilike("%apertura%"),
        )
    ) or 0

    step = str(kwargs.get("step", "check"))
    formato = kwargs.get("formato")

    if bilancio_count > 0 and step == "check":
        # Already imported — show summary
        result = await db.execute(
            select(JournalEntry).where(
                JournalEntry.tenant_id == tenant_id,
                JournalEntry.description.ilike("%apertura%"),
            )
        )
        je_list = result.scalars().all()
        total_dare = sum(e.total_debit for e in je_list)
        total_avere = sum(e.total_credit for e in je_list)
        bilanciato = abs(total_dare - total_avere) < 0.10
        return {
            "status": "completed",
            "message": (
                f"I saldi del bilancio sono gia stati importati. "
                f"Totale dare: \u20ac{total_dare:,.2f}, totale avere: \u20ac{total_avere:,.2f}. "
                f"{'Bilancio bilanciato.' if bilanciato else 'Attenzione: differenza dare/avere.'}"
            ),
            "entries_count": len(je_list),
            "total_dare": round(total_dare, 2),
            "total_avere": round(total_avere, 2),
            "bilanciato": bilanciato,
            "content_blocks": [{
                "type": "stat_row",
                "items": [
                    {"label": "Dare", "value": round(total_dare, 2), "format": "currency"},
                    {"label": "Avere", "value": round(total_avere, 2), "format": "currency"},
                    {"label": "Registrazioni", "value": len(je_list), "format": "number"},
                ],
            }],
        }

    # Not imported — guide the user step by step
    if not formato:
        return {
            "status": "needs_input",
            "step": "choose_format",
            "message": (
                "Per importare i saldi iniziali del bilancio, ho bisogno di sapere "
                "in che formato hai i dati. Hai uno di questi?\n\n"
                "1. **PDF** del bilancio dal commercialista\n"
                "2. **File CSV o Excel** con i saldi dei conti\n"
                "3. **Nessun file** \u2014 inserisco i saldi principali a mano\n\n"
                "Dimmi quale opzione preferisci e ti guido passo passo."
            ),
            "suggested_actions": [
                {"type": "send_message", "label": "Ho un PDF", "value": "Importa bilancio da PDF"},
                {"type": "send_message", "label": "Ho un CSV/Excel", "value": "Importa bilancio da CSV"},
                {"type": "send_message", "label": "Inserisco a mano", "value": "Inserisco i saldi a mano"},
            ],
        }

    formato = str(formato).lower()
    if formato == "pdf":
        return {
            "status": "guide",
            "step": "upload_pdf",
            "message": (
                "Perfetto! Ecco come fare:\n\n"
                "1. Ti porto alla pagina **Import Bilancio**\n"
                "2. Carica il PDF del bilancio\n"
                "3. Il sistema estrae automaticamente i saldi con AI\n"
                "4. Controlla la preview e conferma\n\n"
                "L'elaborazione del PDF puo richiedere qualche secondo."
            ),
        }

    if formato == "csv":
        return {
            "status": "guide",
            "step": "upload_csv",
            "message": (
                "Perfetto! Ecco come fare:\n\n"
                "1. Ti porto alla pagina **Import Bilancio**\n"
                "2. Carica il file CSV (colonne: codice conto, descrizione, dare, avere)\n"
                "3. Il sistema rileva automaticamente le colonne\n"
                "4. Controlla la preview e conferma"
            ),
        }

    if formato in ("manuale", "wizard", "mano"):
        return {
            "status": "guide",
            "step": "manual_entry",
            "message": (
                "OK, inseriamo i saldi principali. Mi servono questi dati:\n\n"
                "1. **Saldo banca** \u2014 quanto c'e sul conto corrente\n"
                "2. **Crediti verso clienti** \u2014 fatture emesse non ancora incassate\n"
                "3. **Debiti verso fornitori** \u2014 fatture ricevute non ancora pagate\n"
                "4. **Capitale sociale**\n"
                "5. **Utile/perdita esercizio precedente**\n\n"
                "Dimmi i numeri che hai. Se non li conosci tutti, iniziamo da quelli che sai."
            ),
        }

    return {
        "status": "needs_input",
        "step": "choose_format",
        "message": "Non ho capito il formato. Scegli tra: PDF, CSV/Excel, o inserimento manuale.",
    }


async def crea_budget_handler(
    db: AsyncSession, tenant_id: uuid.UUID, **kwargs: object
) -> dict:
    """Guide user through budget creation with sector benchmarks."""
    year = int(kwargs.get("year", date.today().year))
    step = str(kwargs.get("step", "check"))

    # Check if budget exists for this year
    budget_count = await db.scalar(
        select(func.count(Budget.id)).where(
            Budget.tenant_id == tenant_id,
            Budget.year == year,
        )
    ) or 0

    if budget_count > 0 and step == "check":
        # Budget exists — show summary
        result = await db.execute(
            select(Budget).where(
                Budget.tenant_id == tenant_id,
                Budget.year == year,
            )
        )
        budget_lines = result.scalars().all()
        total = sum(b.budget_amount for b in budget_lines)
        categories = sorted(set(b.category for b in budget_lines))
        ricavi = sum(b.budget_amount for b in budget_lines if b.category == "ricavi")
        costi = total - ricavi
        ebitda = round(ricavi - costi, 2)
        return {
            "status": "completed",
            "message": (
                f"Il budget {year} e gia stato creato con {len(categories)} categorie.\n"
                f"Ricavi: \u20ac{ricavi:,.2f} | Costi: \u20ac{costi:,.2f} | EBITDA: \u20ac{ebitda:,.2f}\n\n"
                "Vuoi modificarlo o rigenerarlo?"
            ),
            "year": year,
            "categories": categories,
            "total": round(total, 2),
            "content_blocks": [{
                "type": "stat_row",
                "items": [
                    {"label": "Ricavi", "value": round(ricavi, 2), "format": "currency"},
                    {"label": "Costi", "value": round(costi, 2), "format": "currency"},
                    {"label": "EBITDA", "value": ebitda, "format": "currency"},
                ],
            }],
        }

    # No budget — check for historical data to generate proposal
    prev_year = year - 1
    prev_count = await db.scalar(
        select(func.count(Invoice.id)).where(
            Invoice.tenant_id == tenant_id,
            Invoice.data_fattura >= date(prev_year, 1, 1),
            Invoice.data_fattura < date(prev_year + 1, 1, 1),
        )
    ) or 0

    if prev_count > 0:
        # Has history — generate proposal
        from api.modules.controller.service import ControllerService
        controller = ControllerService(db)
        proposal = await controller.generate_budget_proposal(tenant_id, year)

        return {
            "status": "proposal",
            "step": "review_proposal",
            "message": (
                f"Ho analizzato i dati del {prev_year} ({prev_count} fatture) "
                f"e ho preparato una proposta di budget per il {year}.\n\n"
                f"**Ricavi previsti:** \u20ac{proposal['totale_ricavi']:,.2f}\n"
                f"**Costi previsti:** \u20ac{proposal['totale_costi']:,.2f}\n"
                f"**Margine previsto (EBITDA):** \u20ac{proposal['margine_previsto']:,.2f}\n\n"
                "Vuoi che ti faccia alcune domande per personalizzare il budget "
                "in base al tuo settore? Oppure confermi questa proposta?"
            ),
            "proposal": proposal,
            "content_blocks": [{
                "type": "stat_row",
                "items": [
                    {"label": "Ricavi", "value": proposal["totale_ricavi"], "format": "currency"},
                    {"label": "Costi", "value": proposal["totale_costi"], "format": "currency"},
                    {"label": "EBITDA", "value": proposal["margine_previsto"], "format": "currency"},
                ],
            }],
            "suggested_actions": [
                {"type": "send_message", "label": "Personalizza", "value": "Personalizza il budget con domande"},
                {"type": "send_message", "label": "Conferma", "value": "Conferma il budget proposto"},
            ],
        }

    # No history — start from scratch with guided questions
    return {
        "status": "needs_input",
        "step": "start_budget",
        "message": (
            f"Costruiamo insieme il piano economico {year}. "
            "Ti faccio alcune domande \u2014 se non sai un numero esatto, "
            "dammi una stima e la aggiustiamo.\n\n"
            "Per iniziare ho bisogno di sapere:\n\n"
            "1. **Qual e il tuo settore?** (IT, Commercio, Ristorazione, Edilizia...)\n"
            f"2. **Qual e il fatturato previsto per il {year}?** (anche una stima)\n"
            "3. **Quanti dipendenti hai?**\n\n"
            "Con queste informazioni posso proporti un budget "
            "basato sui benchmark del tuo settore."
        ),
        "suggested_actions": [
            {"type": "send_message", "label": "IT / Software", "value": "Settore IT, fatturato da stimare"},
            {"type": "send_message", "label": "Commercio", "value": "Settore commercio, fatturato da stimare"},
            {"type": "send_message", "label": "Ristorazione", "value": "Settore ristorazione, fatturato da stimare"},
            {"type": "send_message", "label": "Altro", "value": "Altro settore"},
        ],
    }


# ============================================================
# Tool definitions registry
# ── CRM handlers (Odoo pipeline) ─────────────────────────


async def crm_pipeline_summary_handler(
    db: AsyncSession, tenant_id: uuid.UUID, **kwargs: object,
) -> dict:
    """Riepilogo pipeline commerciale da Odoo CRM."""
    client = OdooCRMClient()
    if not client.is_configured():
        return {
            "error": "CRM Odoo non configurato. Imposta ODOO_URL/DB/USER/API_KEY nel .env"
        }
    try:
        summary = await client.get_pipeline_summary()
        items = []
        for stage_name, data in summary.get("by_stage", {}).items():
            items.append({
                "fase": stage_name,
                "deal": data["count"],
                "valore": f"{data['value']:,.0f} EUR",
            })
        return {
            "message": (
                f"Pipeline CRM: {summary['total_deals']} deal totali, "
                f"valore {summary['total_value']:,.0f} EUR"
            ),
            "items": items,
            "content_blocks": [{
                "type": "table",
                "title": "Pipeline CRM",
                "headers": ["Fase", "Deal", "Valore"],
                "rows": [[i["fase"], str(i["deal"]), i["valore"]] for i in items],
            }],
        }
    except Exception as e:
        logger.error("CRM pipeline error: %s", e)
        return {"error": f"Errore connessione Odoo CRM: {e}"}


async def crm_list_deals_handler(
    db: AsyncSession, tenant_id: uuid.UUID, **kwargs: object,
) -> dict:
    """Elenca deal dalla pipeline Odoo."""
    client = OdooCRMClient()
    if not client.is_configured():
        return {"error": "CRM Odoo non configurato."}
    try:
        stage = kwargs.get("stage", "") or ""
        deal_type = kwargs.get("deal_type", "") or ""
        limit = int(kwargs.get("limit", 20) or 20)

        domain: list = [["type", "=", "opportunity"]]
        if stage:
            domain.append(["stage_id.name", "ilike", stage])
        if deal_type:
            domain.append(["x_deal_type", "=", deal_type])

        deals = await client.get_deals(domain=domain, limit=limit)
        items = []
        for d in deals:
            items.append({
                "nome": d.name,
                "cliente": d.client_name,
                "fase": d.stage,
                "tipo": d.deal_type or "N/D",
                "valore": f"{d.expected_revenue:,.0f} EUR",
                "tecnologia": d.technology or "",
            })
        return {
            "count": len(items),
            "items": items,
            "content_blocks": [{
                "type": "table",
                "title": f"Deal CRM ({len(items)})",
                "headers": ["Nome", "Cliente", "Fase", "Tipo", "Valore", "Tech"],
                "rows": [[i["nome"], i["cliente"], i["fase"],
                          i["tipo"], i["valore"], i["tecnologia"]] for i in items],
            }],
        }
    except Exception as e:
        logger.error("CRM list deals error: %s", e)
        return {"error": f"Errore: {e}"}


async def crm_list_contacts_handler(
    db: AsyncSession, tenant_id: uuid.UUID, **kwargs: object,
) -> dict:
    """Elenca contatti dal CRM Odoo."""
    client = OdooCRMClient()
    if not client.is_configured():
        return {"error": "CRM Odoo non configurato."}
    try:
        search = kwargs.get("search", "") or ""
        limit = int(kwargs.get("limit", 50) or 50)
        domain: list = [["is_company", "=", True]]
        if search:
            domain.append(["name", "ilike", f"%{search}%"])
        contacts = await client.get_contacts(domain=domain, limit=limit)
        items = []
        for c in contacts:
            items.append({
                "nome": c.name,
                "email": c.email,
                "telefono": c.phone,
                "piva": c.vat or "",
                "citta": c.city,
            })
        return {
            "count": len(items),
            "items": items,
            "content_blocks": [{
                "type": "table",
                "title": f"Contatti CRM ({len(items)})",
                "headers": ["Nome", "Email", "Telefono", "P.IVA", "Citta"],
                "rows": [[i["nome"], i["email"], i["telefono"],
                          i["piva"], i["citta"]] for i in items],
            }],
        }
    except Exception as e:
        logger.error("CRM list contacts error: %s", e)
        return {"error": f"Errore: {e}"}


async def crm_won_deals_handler(
    db: AsyncSession, tenant_id: uuid.UUID, **kwargs: object,
) -> dict:
    """Deal vinti dal CRM Odoo."""
    client = OdooCRMClient()
    if not client.is_configured():
        return {"error": "CRM Odoo non configurato."}
    try:
        since = kwargs.get("since", "") or ""
        deals = await client.get_won_deals(since_date=since)
        items = []
        total_value = 0.0
        for d in deals:
            items.append({
                "nome": d.name,
                "cliente": d.client_name,
                "tipo": d.deal_type or "N/D",
                "valore": f"{d.expected_revenue:,.0f} EUR",
            })
            total_value += d.expected_revenue
        return {
            "message": f"{len(items)} deal vinti, totale {total_value:,.0f} EUR",
            "count": len(items),
            "items": items,
            "content_blocks": [{
                "type": "table",
                "title": f"Deal Vinti ({len(items)})",
                "headers": ["Nome", "Cliente", "Tipo", "Valore"],
                "rows": [[i["nome"], i["cliente"], i["tipo"], i["valore"]] for i in items],
            }],
        }
    except Exception as e:
        logger.error("CRM won deals error: %s", e)
        return {"error": f"Errore: {e}"}


async def crm_pending_orders_handler(
    db: AsyncSession, tenant_id: uuid.UUID, **kwargs: object,
) -> dict:
    """Ordini cliente ricevuti in attesa di conferma."""
    client = OdooCRMClient()
    if not client.is_configured():
        return {"error": "CRM Odoo non configurato."}
    try:
        deals = await client.get_pending_orders()
        items = []
        for d in deals:
            items.append({
                "nome": d.name,
                "cliente": d.client_name,
                "tipo_ordine": d.order_type or "N/D",
                "riferimento": d.order_reference or "",
                "data": d.order_date or "",
                "valore": f"{d.expected_revenue:,.0f} EUR",
            })
        return {
            "message": f"{len(items)} ordini in attesa di conferma",
            "count": len(items),
            "items": items,
            "content_blocks": [{
                "type": "table",
                "title": f"Ordini da Confermare ({len(items)})",
                "headers": ["Deal", "Cliente", "Tipo Ordine", "Rif.", "Data", "Valore"],
                "rows": [[i["nome"], i["cliente"], i["tipo_ordine"],
                          i["riferimento"], i["data"], i["valore"]] for i in items],
            }],
        }
    except Exception as e:
        logger.error("CRM pending orders error: %s", e)
        return {"error": f"Errore: {e}"}


# ============================================================


TOOLS: list[dict] = [
    {
        "name": "count_invoices",
        "description": "Conta il numero di fatture per periodo, tipo (emesse/ricevute) e nome cliente/fornitore",
        "parameters": {
            "type": "object",
            "properties": {
                "month": {"type": "string", "description": "Mese in formato YYYY-MM"},
                "type": {"type": "string", "enum": ["passiva", "attiva"], "description": "Tipo fattura"},
                "year": {"type": "integer", "description": "Anno di riferimento"},
                "query": {"type": "string", "description": "Ricerca per nome emittente, destinatario o numero fattura"},
            },
        },
        "handler": count_invoices_handler,
    },
    {
        "name": "list_invoices",
        "description": "Elenca le fatture con filtri opzionali per tipo, stato e nome cliente/fornitore",
        "parameters": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["passiva", "attiva"]},
                "status": {"type": "string", "enum": ["pending", "parsed", "categorized", "registered", "error"]},
                "limit": {"type": "integer", "description": "Numero massimo di risultati"},
                "year": {"type": "integer", "description": "Anno di riferimento"},
                "query": {"type": "string", "description": "Ricerca per nome emittente, destinatario o numero fattura"},
            },
        },
        "handler": list_invoices_handler,
    },
    {
        "name": "get_invoice_detail",
        "description": "Mostra i dettagli di una fattura specifica. Accetta ID fattura o numero fattura (es. '1/7', 'AQ01809969').",
        "parameters": {
            "type": "object",
            "properties": {
                "invoice_id": {"type": "string", "description": "UUID o numero fattura (es. '1/7', 'AQ01809969')"},
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
        "name": "get_top_clients",
        "description": "Mostra la classifica top clienti o fornitori per fatturato e numero fatture",
        "parameters": {
            "type": "object",
            "properties": {
                "year": {"type": "integer", "description": "Anno di riferimento"},
                "type": {"type": "string", "enum": ["attiva", "passiva"], "description": "attiva=clienti, passiva=fornitori"},
                "limit": {"type": "integer", "description": "Numero di risultati (default 10)"},
            },
        },
        "handler": get_top_clients_handler,
    },
    {
        "name": "get_period_stats",
        "description": "KPI per periodo (mese, trimestre, anno): fatturato, costi, EBITDA con dettaglio mensile e grafici",
        "parameters": {
            "type": "object",
            "properties": {
                "year": {"type": "integer", "description": "Anno di riferimento"},
                "month_start": {"type": "integer", "description": "Mese inizio (1-12)"},
                "month_end": {"type": "integer", "description": "Mese fine (1-12)"},
            },
        },
        "handler": get_period_stats_handler,
    },
    {
        "name": "sync_cassetto",
        "description": "Controlla lo stato di sincronizzazione del cassetto fiscale",
        "parameters": {"type": "object", "properties": {}},
        "handler": sync_cassetto_handler,
    },
    {
        "name": "modify_dashboard",
        "description": "Aggiunge, rimuove o modifica un widget nella dashboard dell'utente. Azioni: add (aggiungi widget), remove (rimuovi per titolo), update (modifica).",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["add", "remove", "update"],
                    "description": "Azione da eseguire: add, remove, update",
                },
                "title": {
                    "type": "string",
                    "description": "Titolo del widget da aggiungere/rimuovere/aggiornare",
                },
                "widget_type": {
                    "type": "string",
                    "enum": ["stat_card", "bar_chart", "pie_chart", "table", "alert"],
                    "description": "Tipo di widget (solo per add)",
                },
                "data_source": {
                    "type": "string",
                    "description": "Fonte dati (es. yearly_stats)",
                },
                "data_path": {
                    "type": "string",
                    "description": "Percorso dati (es. fatture_attive.totale)",
                },
                "config": {
                    "type": "object",
                    "description": "Configurazione widget (formato, colori, colonne...)",
                },
                "user_id": {
                    "type": "string",
                    "description": "UUID dell'utente",
                },
            },
            "required": ["action", "user_id"],
        },
        "handler": modify_dashboard_handler,
    },
    {
        "name": "apertura_conti",
        "description": (
            "Guida l'utente nell'importazione dei saldi iniziali del bilancio. "
            "Usa questo tool quando l'utente chiede aiuto per: importare il bilancio, "
            "inserire i saldi iniziali, apertura conti, saldi di apertura, "
            "o quando il pezzo 'Bilancio' del puzzle non e configurato. "
            "Il tool verifica lo stato attuale e guida con domande (non consigli generici)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "step": {
                    "type": "string",
                    "enum": ["check", "choose_format", "upload"],
                    "description": "Fase corrente del flusso guidato (default: check)",
                },
                "formato": {
                    "type": "string",
                    "enum": ["pdf", "csv", "manuale"],
                    "description": "Formato scelto dall'utente per l'import",
                },
            },
        },
        "handler": apertura_conti_handler,
    },
    {
        "name": "crea_budget",
        "description": (
            "Guida l'utente nella creazione del budget/piano economico annuale. "
            "Usa questo tool quando l'utente chiede aiuto per: creare il budget, "
            "piano economico, previsione costi/ricavi, EBITDA previsionale, "
            "o quando il pezzo 'Budget' del puzzle non e configurato. "
            "Se ci sono dati storici, propone un budget basato sull'anno precedente. "
            "Altrimenti fa domande guidate per settore."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "year": {
                    "type": "integer",
                    "description": "Anno per il budget (default: anno corrente)",
                },
                "step": {
                    "type": "string",
                    "enum": ["check", "review_proposal", "customize"],
                    "description": "Fase corrente del flusso guidato (default: check)",
                },
            },
        },
        "handler": crea_budget_handler,
    },
    # ── CRM (Odoo pipeline) ──────────────────────────────
    {
        "name": "crm_pipeline_summary",
        "description": (
            "Mostra il riepilogo della pipeline commerciale CRM: "
            "deal per fase, valore totale, deal vinti. "
            "Usa quando l'utente chiede della pipeline, dei deal, "
            "delle opportunita commerciali, dei clienti prospect."
        ),
        "parameters": {"type": "object", "properties": {}},
        "handler": crm_pipeline_summary_handler,
    },
    {
        "name": "crm_list_deals",
        "description": (
            "Elenca i deal/opportunita dalla pipeline CRM Odoo. "
            "Filtra per fase (es. Qualificazione, Proposta, Vinto) "
            "o tipo (T&M, fixed, spot, hardware)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "stage": {"type": "string", "description": "Nome fase pipeline"},
                "deal_type": {"type": "string", "description": "Tipo deal: T&M, fixed, spot, hardware"},
                "limit": {"type": "integer", "description": "Numero massimo risultati"},
            },
        },
        "handler": crm_list_deals_handler,
    },
    {
        "name": "crm_list_contacts",
        "description": (
            "Elenca i contatti/clienti aziendali dal CRM Odoo. "
            "Cerca per nome."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "search": {"type": "string", "description": "Ricerca per nome cliente"},
                "limit": {"type": "integer", "description": "Numero massimo risultati"},
            },
        },
        "handler": crm_list_contacts_handler,
    },
    {
        "name": "crm_won_deals",
        "description": "Mostra i deal chiusi come vinti, con filtro data opzionale.",
        "parameters": {
            "type": "object",
            "properties": {
                "since": {"type": "string", "description": "Data YYYY-MM-DD da cui filtrare"},
            },
        },
        "handler": crm_won_deals_handler,
    },
    {
        "name": "crm_pending_orders",
        "description": (
            "Mostra gli ordini cliente ricevuti in attesa di conferma. "
            "Ordini PO, email, firma Word o portale da confermare."
        ),
        "parameters": {"type": "object", "properties": {}},
        "handler": crm_pending_orders_handler,
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
