"""Accounting/journal/fatture tool handlers and definitions."""

import uuid
from datetime import date

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import Invoice, JournalEntry


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


# ============================================================
# Tool definitions
# ============================================================


ACCOUNTING_TOOLS: list[dict] = [
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
        "name": "get_pending_review",
        "description": "Mostra le fatture categorizzate in attesa di verifica umana",
        "parameters": {"type": "object", "properties": {}},
        "handler": get_pending_review_handler,
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
]
