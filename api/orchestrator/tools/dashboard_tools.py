"""Dashboard/KPI/CEO tool handlers and definitions."""

import logging
import uuid
from datetime import date, datetime

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import Budget, DashboardLayout, Expense, Asset, Invoice
from api.modules.dashboard.default_widgets import DEFAULT_WIDGETS

logger = logging.getLogger(__name__)

MONTH_LABELS = [
    "", "Gen", "Feb", "Mar", "Apr", "Mag", "Giu",
    "Lug", "Ago", "Set", "Ott", "Nov", "Dic",
]


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
        month_data: dict[int, dict] = {}
        for row in monthly_result.fetchall():
            m = int(row[0])
            if m not in month_data:
                month_data[m] = {"label": MONTH_LABELS[m], "Emesse": 0, "Ricevute": 0}
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
                    f"\u20ac{m['emesse']:,.2f}",
                    f"\u20ac{m['ricevute']:,.2f}",
                    f"\u20ac{m['emesse'] - m['ricevute']:,.2f}",
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
        "message": f"{period_label}: fatturato \u20ac{tot_emesse:,.2f}, costi \u20ac{tot_ricevute:,.2f}, EBITDA \u20ac{ebitda:,.2f}",
    }


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


DASHBOARD_TOOLS: list[dict] = [
    {
        "name": "get_dashboard_summary",
        "description": "Mostra un riepilogo della dashboard con contatori fatture per stato",
        "parameters": {"type": "object", "properties": {}},
        "handler": get_dashboard_summary_handler,
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
]
