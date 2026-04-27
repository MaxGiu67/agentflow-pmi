"""Invoicing state snapshot — vista aggregata fatturazione per agenti AI.

GET /api/v1/state/invoicing
Aggrega: fatture attive (emesse), fatture passive (ricevute), scadenze,
insoluti, IVA del periodo, top clienti/fornitori.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import ActiveInvoice, Invoice, User
from api.db.session import get_db
from api.middleware.auth import get_current_user

router = APIRouter(prefix="/state", tags=["state"])


class InvoiceCounter(BaseModel):
    count: int
    total: float
    avg: float | None


class TopParty(BaseModel):
    name: str
    piva: str | None
    total: float
    count: int


class UpcomingDue(BaseModel):
    invoice_id: uuid.UUID
    direction: str  # active|passive
    counterpart: str
    numero: str | None
    date: date
    due_date: date | None
    amount: float
    days_to_due: int


class InvoicingSnapshot(BaseModel):
    tenant_piva: str | None
    snapshot_at: datetime

    # Active (emesse)
    active_ytd: InvoiceCounter
    active_30d: InvoiceCounter
    active_pending_sdi: int  # marking != delivered/rejected
    active_rejected: int

    # Passive (ricevute)
    passive_ytd: InvoiceCounter
    passive_30d: InvoiceCounter
    passive_uncategorized: int

    # IVA stimata trimestre corrente
    iva_a_debito_q: float  # IVA su attive
    iva_a_credito_q: float  # IVA su passive
    iva_saldo_q: float

    # Scadenze prossime 30gg
    due_30d: list[UpcomingDue]
    due_30d_total: float

    # Insoluti (passate non incassate)
    overdue: list[UpcomingDue]
    overdue_total: float

    # Top counterparts YTD
    top_clients_ytd: list[TopParty]
    top_suppliers_ytd: list[TopParty]

    flags: list[str]


def _q_start(today: date) -> date:
    """Inizio trimestre corrente."""
    q_first_month = ((today.month - 1) // 3) * 3 + 1
    return date(today.year, q_first_month, 1)


@router.get("/invoicing", response_model=InvoicingSnapshot)
async def invoicing_snapshot(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InvoicingSnapshot:
    if not user.tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Profilo azienda non configurato")

    tenant_id = user.tenant_id
    now = datetime.utcnow()
    today = now.date()
    ytd_start = date(today.year, 1, 1)
    d_30 = today - timedelta(days=30)
    d_30_future = today + timedelta(days=30)
    q_first = _q_start(today)

    # ── ACTIVE (emesse) ──
    active_res = await db.execute(
        select(ActiveInvoice).where(
            and_(
                ActiveInvoice.tenant_id == tenant_id,
                ActiveInvoice.data_fattura >= ytd_start,
            )
        )
    )
    actives_ytd: list[ActiveInvoice] = list(active_res.scalars().all())
    actives_30 = [a for a in actives_ytd if a.data_fattura >= d_30]

    def _counter(items: list[Any], amount_attr: str) -> InvoiceCounter:
        total = sum(getattr(i, amount_attr) or 0 for i in items)
        return InvoiceCounter(
            count=len(items),
            total=round(total, 2),
            avg=round(total / len(items), 2) if items else None,
        )

    active_ytd = _counter(actives_ytd, "importo_totale")
    active_30 = _counter(actives_30, "importo_totale")
    active_pending = sum(
        1 for a in actives_ytd if a.sdi_status not in ("delivered", "rejected", "draft")
    )
    active_rejected = sum(1 for a in actives_ytd if a.sdi_status == "rejected")

    # ── PASSIVE (ricevute) ──
    passive_res = await db.execute(
        select(Invoice).where(
            and_(
                Invoice.tenant_id == tenant_id,
                Invoice.type == "passiva",
                Invoice.data_fattura >= ytd_start,
            )
        )
    )
    passives_ytd: list[Invoice] = list(passive_res.scalars().all())
    passives_30 = [p for p in passives_ytd if p.data_fattura and p.data_fattura >= d_30]

    passive_ytd = _counter(passives_ytd, "importo_totale")
    passive_30 = _counter(passives_30, "importo_totale")
    passive_uncat = sum(1 for p in passives_ytd if not p.category or p.category == "")

    # ── IVA TRIMESTRE ──
    actives_q = [a for a in actives_ytd if a.data_fattura >= q_first]
    passives_q = [p for p in passives_ytd if p.data_fattura and p.data_fattura >= q_first]
    iva_debito = sum(a.importo_iva or 0 for a in actives_q)
    iva_credito = sum(p.importo_iva or 0 for p in passives_q)

    # ── SCADENZE 30gg + OVERDUE ──
    due_30: list[UpcomingDue] = []
    overdue: list[UpcomingDue] = []
    # ActiveInvoice non ha due_date diretto; assumiamo +30gg standard
    for a in actives_ytd:
        if a.data_fattura is None:
            continue
        # Per ActiveInvoice si presume pagamento a 30gg dalla data fattura
        due = a.data_fattura + timedelta(days=30)
        days_to = (due - today).days
        if 0 <= days_to <= 30 and a.sdi_status not in ("rejected",):
            due_30.append(
                UpcomingDue(
                    invoice_id=a.id,
                    direction="active",
                    counterpart=a.cliente_nome or "?",
                    numero=a.numero_fattura,
                    date=a.data_fattura,
                    due_date=due,
                    amount=a.importo_totale or 0,
                    days_to_due=days_to,
                )
            )
        elif days_to < 0 and a.sdi_status == "delivered":
            # Overdue: solo per emesse consegnate (passive non sappiamo se pagate)
            overdue.append(
                UpcomingDue(
                    invoice_id=a.id,
                    direction="active",
                    counterpart=a.cliente_nome or "?",
                    numero=a.numero_fattura,
                    date=a.data_fattura,
                    due_date=due,
                    amount=a.importo_totale or 0,
                    days_to_due=days_to,
                )
            )

    due_30.sort(key=lambda x: x.days_to_due)
    overdue.sort(key=lambda x: x.days_to_due)
    due_30 = due_30[:50]
    overdue = overdue[:50]

    due_30_total = sum(d.amount for d in due_30)
    overdue_total = sum(d.amount for d in overdue)

    # ── Top clients/suppliers ──
    clients: defaultdict[str, dict[str, Any]] = defaultdict(lambda: {"name": "", "piva": "", "total": 0.0, "count": 0})
    for a in actives_ytd:
        key = a.cliente_piva or a.cliente_nome or "?"
        clients[key]["name"] = a.cliente_nome or "?"
        clients[key]["piva"] = a.cliente_piva
        clients[key]["total"] += a.importo_totale or 0
        clients[key]["count"] += 1
    top_clients = [
        TopParty(name=v["name"], piva=v["piva"], total=round(v["total"], 2), count=v["count"])
        for v in sorted(clients.values(), key=lambda x: -x["total"])
    ][:10]

    suppliers: defaultdict[str, dict[str, Any]] = defaultdict(lambda: {"name": "", "piva": "", "total": 0.0, "count": 0})
    for p in passives_ytd:
        key = p.emittente_piva or p.emittente_nome or "?"
        suppliers[key]["name"] = p.emittente_nome or "?"
        suppliers[key]["piva"] = p.emittente_piva
        suppliers[key]["total"] += p.importo_totale or 0
        suppliers[key]["count"] += 1
    top_suppliers = [
        TopParty(name=v["name"], piva=v["piva"], total=round(v["total"], 2), count=v["count"])
        for v in sorted(suppliers.values(), key=lambda x: -x["total"])
    ][:10]

    # ── Flags ──
    flags: list[str] = []
    if active_rejected > 0:
        flags.append(f"sdi_rejected_{active_rejected}_invoices")
    if active_pending > 5:
        flags.append(f"sdi_pending_{active_pending}_invoices")
    if passive_uncat > 0:
        flags.append(f"passive_uncategorized_{passive_uncat}")
    if overdue_total > 0:
        flags.append(f"overdue_active_{round(overdue_total, 2)}_eur")
    if iva_debito - iva_credito > 5000:
        flags.append("high_iva_debit_q")

    from api.db.models import Tenant
    tenant_res = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = tenant_res.scalar_one_or_none()

    return InvoicingSnapshot(
        tenant_piva=tenant.piva if tenant else None,
        snapshot_at=now,
        active_ytd=active_ytd,
        active_30d=active_30,
        active_pending_sdi=active_pending,
        active_rejected=active_rejected,
        passive_ytd=passive_ytd,
        passive_30d=passive_30,
        passive_uncategorized=passive_uncat,
        iva_a_debito_q=round(iva_debito, 2),
        iva_a_credito_q=round(iva_credito, 2),
        iva_saldo_q=round(iva_debito - iva_credito, 2),
        due_30d=due_30,
        due_30d_total=round(due_30_total, 2),
        overdue=overdue,
        overdue_total=round(overdue_total, 2),
        top_clients_ytd=top_clients,
        top_suppliers_ytd=top_suppliers,
        flags=flags,
    )
