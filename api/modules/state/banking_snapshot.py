"""Banking state snapshot — vista aggregata banca per agenti AI.

GET /api/v1/state/banking
Ritorna in 1 chiamata: saldi, movimenti recenti, top controparti, distribuzione
categorie, anomalie, runway stimata.
"""

from __future__ import annotations

import uuid
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import BankAccount, BankConnection, BankTransaction, User
from api.db.session import get_db
from api.middleware.auth import get_current_user

router = APIRouter(prefix="/state", tags=["state"])


class AccountSummary(BaseModel):
    iban: str
    bank_name: str | None
    balance: float | None
    currency: str = "EUR"
    last_sync_at: datetime | None
    consent_expires_at: datetime | None
    transactions_count: int
    days_since_oldest_tx: int | None


class CategoryStat(BaseModel):
    category: str
    count: int
    total_amount: float


class CounterpartyStat(BaseModel):
    name: str
    direction: str  # in|out
    total_amount: float
    transactions_count: int


class TxAnomaly(BaseModel):
    id: uuid.UUID
    date: date
    amount: float
    description: str | None
    counterparty: str | None
    reason: str  # large_amount|unusual_pattern|recurring_changed


class BankingSnapshot(BaseModel):
    tenant_piva: str | None
    snapshot_at: datetime
    # Account level
    accounts_total: int
    accounts: list[AccountSummary]
    total_balance: float
    # Transaction stats
    tx_30d_in: float
    tx_30d_out: float
    tx_30d_net: float
    tx_30d_count: int
    tx_90d_in: float
    tx_90d_out: float
    tx_90d_net: float
    tx_90d_count: int
    # Categories (last 30d)
    top_categories_30d: list[CategoryStat]
    # Counterparties (last 30d)
    top_counterparts_in_30d: list[CounterpartyStat]
    top_counterparts_out_30d: list[CounterpartyStat]
    # Health
    runway_months_estimate: float | None
    avg_monthly_burn: float | None
    avg_monthly_revenue: float | None
    # Anomalies & flags
    anomalies: list[TxAnomaly]
    flags: list[str]  # human-readable warnings


@router.get("/banking", response_model=BankingSnapshot)
async def banking_snapshot(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BankingSnapshot:
    """Snapshot aggregato dello stato bancario per agente AI / dashboard CEO.

    1 sola query → tutti i dati per Controller/Analytics agent.
    """
    if not user.tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Profilo azienda non configurato")

    tenant_id = user.tenant_id
    now = datetime.utcnow()
    today = now.date()
    d_30 = today - timedelta(days=30)
    d_90 = today - timedelta(days=90)

    # ── Accounts ──
    accounts_res = await db.execute(
        select(BankAccount).where(BankAccount.tenant_id == tenant_id)
    )
    accounts: list[BankAccount] = list(accounts_res.scalars().all())
    account_ids = [a.id for a in accounts]

    # ── Connections (per consent expiry) ──
    conns_by_id: dict[uuid.UUID, BankConnection] = {}
    if account_ids:
        conn_ids = [a.acube_connection_id for a in accounts if a.acube_connection_id]
        if conn_ids:
            conns_res = await db.execute(
                select(BankConnection).where(BankConnection.id.in_(conn_ids))
            )
            conns_by_id = {c.id: c for c in conns_res.scalars().all()}

    # ── All transactions (per account/period stats) ──
    all_txs: list[BankTransaction] = []
    if account_ids:
        tx_res = await db.execute(
            select(BankTransaction).where(BankTransaction.bank_account_id.in_(account_ids))
        )
        all_txs = list(tx_res.scalars().all())

    # ── Per-account stats ──
    account_summaries: list[AccountSummary] = []
    for acc in accounts:
        acc_txs = [t for t in all_txs if t.bank_account_id == acc.id]
        oldest = min((t.date for t in acc_txs), default=None)
        days_old = (today - oldest).days if oldest else None
        conn = conns_by_id.get(acc.acube_connection_id) if acc.acube_connection_id else None
        account_summaries.append(
            AccountSummary(
                iban=acc.iban or "",
                bank_name=acc.bank_name,
                balance=acc.balance,
                currency="EUR",
                last_sync_at=acc.last_sync_at,
                consent_expires_at=conn.consent_expires_at if conn else None,
                transactions_count=len(acc_txs),
                days_since_oldest_tx=days_old,
            )
        )

    total_balance = sum((a.balance or 0.0) for a in accounts)

    # ── 30d stats ──
    txs_30 = [t for t in all_txs if t.date >= d_30]
    in_30 = sum(t.amount for t in txs_30 if (t.amount or 0) > 0)
    out_30 = sum(t.amount for t in txs_30 if (t.amount or 0) < 0)
    net_30 = in_30 + out_30

    # ── 90d stats ──
    txs_90 = [t for t in all_txs if t.date >= d_90]
    in_90 = sum(t.amount for t in txs_90 if (t.amount or 0) > 0)
    out_90 = sum(t.amount for t in txs_90 if (t.amount or 0) < 0)
    net_90 = in_90 + out_90

    # ── Categories last 30d ──
    cat_counter: defaultdict[str, dict[str, Any]] = defaultdict(lambda: {"count": 0, "total": 0.0})
    for t in txs_30:
        cat = t.parsed_category or "other"
        cat_counter[cat]["count"] += 1
        cat_counter[cat]["total"] += abs(t.amount or 0)
    top_categories = [
        CategoryStat(category=c, count=v["count"], total_amount=round(v["total"], 2))
        for c, v in sorted(cat_counter.items(), key=lambda x: -x[1]["total"])
    ][:10]

    # ── Counterparts last 30d ──
    cp_in: defaultdict[str, dict[str, Any]] = defaultdict(lambda: {"total": 0.0, "count": 0})
    cp_out: defaultdict[str, dict[str, Any]] = defaultdict(lambda: {"total": 0.0, "count": 0})
    for t in txs_30:
        name = t.parsed_counterparty or t.counterpart
        if not name:
            continue
        target = cp_in if (t.amount or 0) > 0 else cp_out
        target[name]["total"] += abs(t.amount or 0)
        target[name]["count"] += 1
    top_in = [
        CounterpartyStat(name=k, direction="in", total_amount=round(v["total"], 2), transactions_count=v["count"])
        for k, v in sorted(cp_in.items(), key=lambda x: -x[1]["total"])
    ][:10]
    top_out = [
        CounterpartyStat(name=k, direction="out", total_amount=round(v["total"], 2), transactions_count=v["count"])
        for k, v in sorted(cp_out.items(), key=lambda x: -x[1]["total"])
    ][:10]

    # ── Runway / burn ──
    months_window = 3.0
    avg_burn = (-out_90 / months_window) if out_90 < 0 else None
    avg_rev = (in_90 / months_window) if in_90 > 0 else None
    runway = (total_balance / avg_burn) if (avg_burn and avg_burn > 0) else None

    # ── Anomalies ──
    anomalies: list[TxAnomaly] = []
    # Heuristic 1: largest single tx in last 30d > 3x median
    if len(txs_30) >= 5:
        sorted_amounts = sorted([abs(t.amount or 0) for t in txs_30])
        median = sorted_amounts[len(sorted_amounts) // 2] if sorted_amounts else 0
        threshold = max(median * 3, 10000)  # almeno €10k per essere "anomalo"
        for t in txs_30:
            if abs(t.amount or 0) >= threshold:
                anomalies.append(
                    TxAnomaly(
                        id=t.id,
                        date=t.date,
                        amount=t.amount or 0,
                        description=t.description,
                        counterparty=t.parsed_counterparty or t.counterpart,
                        reason="large_amount",
                    )
                )
    # Limit
    anomalies = anomalies[:20]

    # ── Flags ──
    flags: list[str] = []
    if not accounts:
        flags.append("no_bank_accounts_connected")
    elif total_balance < 0:
        flags.append("negative_total_balance")
    if runway is not None and runway < 2:
        flags.append("low_runway_under_2_months")
    if avg_rev and avg_burn and avg_burn > avg_rev:
        flags.append("burn_exceeds_revenue_3m")
    # Consensi in scadenza < 14gg
    for s in account_summaries:
        if s.consent_expires_at:
            days_left = (s.consent_expires_at.date() - today).days
            if 0 <= days_left <= 14:
                flags.append(f"consent_expiring_soon_{s.iban}")
    # Stale sync (> 7gg)
    for s in account_summaries:
        if s.last_sync_at and (now - s.last_sync_at).days > 7:
            flags.append(f"stale_sync_{s.iban}")

    # ── Tenant info ──
    from api.db.models import Tenant
    tenant_res = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = tenant_res.scalar_one_or_none()

    return BankingSnapshot(
        tenant_piva=tenant.piva if tenant else None,
        snapshot_at=now,
        accounts_total=len(accounts),
        accounts=account_summaries,
        total_balance=round(total_balance, 2),
        tx_30d_in=round(in_30, 2),
        tx_30d_out=round(out_30, 2),
        tx_30d_net=round(net_30, 2),
        tx_30d_count=len(txs_30),
        tx_90d_in=round(in_90, 2),
        tx_90d_out=round(out_90, 2),
        tx_90d_net=round(net_90, 2),
        tx_90d_count=len(txs_90),
        top_categories_30d=top_categories,
        top_counterparts_in_30d=top_in,
        top_counterparts_out_30d=top_out,
        runway_months_estimate=round(runway, 1) if runway else None,
        avg_monthly_burn=round(avg_burn, 2) if avg_burn else None,
        avg_monthly_revenue=round(avg_rev, 2) if avg_rev else None,
        anomalies=anomalies,
        flags=flags,
    )
