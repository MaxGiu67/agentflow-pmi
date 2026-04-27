"""Sales state snapshot — vista aggregata pipeline commerciale per agenti AI.

GET /api/v1/state/sales
Aggrega: pipeline value, deal per stage, win rate, deal stagnanti,
top contatti, attivita pianificate.
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

from api.db.models import (
    CrmActivity,
    CrmDeal,
    CrmPipelineStage,
    User,
)
from api.db.session import get_db
from api.middleware.auth import get_current_user

router = APIRouter(prefix="/state", tags=["state"])


class StageStat(BaseModel):
    stage_id: uuid.UUID
    stage_name: str
    deals_count: int
    weighted_value: float  # sum(value * probability)
    raw_value: float
    avg_value: float | None


class DealHotspot(BaseModel):
    id: uuid.UUID
    name: str
    stage: str | None
    value: float
    last_activity_at: datetime | None
    days_since_activity: int | None
    reason: str  # stagnant|high_value_no_followup|nearing_close


class TopContact(BaseModel):
    contact_id: uuid.UUID
    name: str
    company: str | None
    deals_count: int
    deals_total_value: float


class ActivityNext(BaseModel):
    id: uuid.UUID
    type: str
    deal_name: str | None
    contact_name: str | None
    scheduled_at: datetime | None
    days_until: int | None
    description: str | None


class SalesSnapshot(BaseModel):
    tenant_piva: str | None
    snapshot_at: datetime

    # Pipeline aggregate
    open_deals_count: int
    open_pipeline_value: float
    weighted_pipeline_value: float

    # Per stage
    stages: list[StageStat]

    # Performance YTD
    won_ytd_count: int
    won_ytd_value: float
    lost_ytd_count: int
    lost_ytd_value: float
    win_rate_ytd: float | None  # 0..1

    # Performance MTD
    won_mtd_count: int
    won_mtd_value: float
    new_deals_mtd: int

    # Hotspots — deal che richiedono attenzione
    stagnant_deals: list[DealHotspot]  # no activity > 14gg
    high_value_no_activity: list[DealHotspot]  # value > soglia, no activity 7gg

    # Top contacts
    top_contacts: list[TopContact]

    # Activity board
    activities_overdue: int  # planned scheduled_at < now & status != completed
    activities_today: int
    activities_this_week: int
    next_activities: list[ActivityNext]

    flags: list[str]


@router.get("/sales", response_model=SalesSnapshot)
async def sales_snapshot(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SalesSnapshot:
    if not user.tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Profilo azienda non configurato")

    tenant_id = user.tenant_id
    now = datetime.utcnow()
    today = now.date()
    ytd_start = date(today.year, 1, 1)
    mtd_start = date(today.year, today.month, 1)

    # ── Stages map ──
    stages_res = await db.execute(
        select(CrmPipelineStage).where(CrmPipelineStage.tenant_id == tenant_id)
    )
    stages: list[CrmPipelineStage] = list(stages_res.scalars().all())
    stages_by_id = {s.id: s for s in stages}

    # ── All deals (for tenant) ──
    deals_res = await db.execute(
        select(CrmDeal).where(CrmDeal.tenant_id == tenant_id)
    )
    deals: list[CrmDeal] = list(deals_res.scalars().all())

    # ── Open deals (non won/lost) ──
    open_deals: list[CrmDeal] = []
    won_ytd: list[CrmDeal] = []
    lost_ytd: list[CrmDeal] = []
    won_mtd: list[CrmDeal] = []
    deals_mtd_new: list[CrmDeal] = []

    for d in deals:
        stage = stages_by_id.get(d.stage_id) if d.stage_id else None
        is_won = stage.is_won if stage else False
        is_lost = stage.is_lost if stage else False
        if not is_won and not is_lost:
            open_deals.append(d)
        # YTD won/lost — usa created_at o updated_at come proxy della chiusura
        ref_date = (d.updated_at or d.created_at).date() if (d.updated_at or d.created_at) else None
        if is_won and ref_date and ref_date >= ytd_start:
            won_ytd.append(d)
            if ref_date >= mtd_start:
                won_mtd.append(d)
        elif is_lost and ref_date and ref_date >= ytd_start:
            lost_ytd.append(d)
        # New deals MTD
        if d.created_at and d.created_at.date() >= mtd_start:
            deals_mtd_new.append(d)

    # ── Pipeline value ──
    open_value = sum((d.revenue or 0) for d in open_deals)
    weighted_value = sum(
        (d.revenue or 0) * (stages_by_id[d.stage_id].probability or 0) / 100.0
        for d in open_deals
        if d.stage_id and d.stage_id in stages_by_id and stages_by_id[d.stage_id].probability
    )

    # ── Per stage stats ──
    stage_buckets: defaultdict[uuid.UUID, list[CrmDeal]] = defaultdict(list)
    for d in open_deals:
        if d.stage_id:
            stage_buckets[d.stage_id].append(d)
    stage_stats: list[StageStat] = []
    for s in stages:
        if s.is_won or s.is_lost:
            continue  # solo open stages
        bucket = stage_buckets.get(s.id, [])
        raw = sum((d.revenue or 0) for d in bucket)
        weighted = raw * (s.probability or 0) / 100.0
        stage_stats.append(
            StageStat(
                stage_id=s.id,
                stage_name=s.name,
                deals_count=len(bucket),
                weighted_value=round(weighted, 2),
                raw_value=round(raw, 2),
                avg_value=round(raw / len(bucket), 2) if bucket else None,
            )
        )
    stage_stats.sort(key=lambda x: -x.raw_value)

    # ── Win rate ──
    closed_ytd = len(won_ytd) + len(lost_ytd)
    win_rate = len(won_ytd) / closed_ytd if closed_ytd > 0 else None

    # ── Activities ──
    deal_ids = [d.id for d in deals]
    activities: list[CrmActivity] = []
    if deal_ids:
        act_res = await db.execute(
            select(CrmActivity).where(CrmActivity.deal_id.in_(deal_ids))
        )
        activities = list(act_res.scalars().all())

    # Last activity per deal
    last_act_by_deal: dict[uuid.UUID, datetime] = {}
    for a in activities:
        ref = a.completed_at or a.scheduled_at or a.created_at
        if not ref:
            continue
        if a.deal_id and (a.deal_id not in last_act_by_deal or ref > last_act_by_deal[a.deal_id]):
            last_act_by_deal[a.deal_id] = ref

    # ── Hotspots: stagnant ──
    stagnant: list[DealHotspot] = []
    high_no_act: list[DealHotspot] = []
    HIGH_VALUE_THRESHOLD = 10000.0
    for d in open_deals:
        last_act = last_act_by_deal.get(d.id)
        days_since = (now - last_act).days if last_act else (now - d.created_at).days if d.created_at else None
        stage = stages_by_id.get(d.stage_id) if d.stage_id else None
        stage_name = stage.name if stage else None
        if days_since is not None and days_since > 14:
            stagnant.append(
                DealHotspot(
                    id=d.id, name=d.name or "?", stage=stage_name,
                    value=d.revenue or 0, last_activity_at=last_act,
                    days_since_activity=days_since, reason="stagnant",
                )
            )
        if (d.revenue or 0) >= HIGH_VALUE_THRESHOLD and days_since is not None and days_since > 7:
            high_no_act.append(
                DealHotspot(
                    id=d.id, name=d.name or "?", stage=stage_name,
                    value=d.revenue or 0, last_activity_at=last_act,
                    days_since_activity=days_since, reason="high_value_no_followup",
                )
            )
    stagnant.sort(key=lambda x: -(x.days_since_activity or 0))
    high_no_act.sort(key=lambda x: -x.value)
    stagnant = stagnant[:10]
    high_no_act = high_no_act[:10]

    # ── Top contacts (by deal value) ──
    contact_buckets: defaultdict[uuid.UUID, dict[str, Any]] = defaultdict(
        lambda: {"name": "", "company": None, "deals": [], "total": 0.0}
    )
    for d in deals:
        if not d.contact_id:
            continue
        contact_buckets[d.contact_id]["deals"].append(d.id)
        contact_buckets[d.contact_id]["total"] += d.revenue or 0
    # Carica nomi contatti
    if contact_buckets:
        from api.db.models import CrmContact
        cont_res = await db.execute(
            select(CrmContact).where(CrmContact.id.in_(list(contact_buckets.keys())))
        )
        for c in cont_res.scalars().all():
            contact_buckets[c.id]["name"] = c.contact_name or ""
            contact_buckets[c.id]["company"] = None  # company_id -> nome richiede join, omesso per ora
    top_contacts = [
        TopContact(
            contact_id=cid,
            name=v["name"] or "?",
            company=v["company"],
            deals_count=len(v["deals"]),
            deals_total_value=round(v["total"], 2),
        )
        for cid, v in sorted(contact_buckets.items(), key=lambda x: -x[1]["total"])
    ][:10]

    # ── Activity board ──
    overdue_count = 0
    today_count = 0
    week_count = 0
    next_acts: list[ActivityNext] = []
    week_end = today + timedelta(days=7)
    for a in activities:
        sch = a.scheduled_at
        if not sch or a.status == "completed":
            continue
        sch_date = sch.date()
        if sch < now:
            overdue_count += 1
        elif sch_date == today:
            today_count += 1
        elif sch_date <= week_end:
            week_count += 1
        # Build next list
        if sch >= now and sch_date <= week_end:
            days_until = (sch_date - today).days
            deal_name = next((d.name for d in deals if d.id == a.deal_id), None)
            next_acts.append(
                ActivityNext(
                    id=a.id,
                    type=a.type or "task",
                    deal_name=deal_name,
                    contact_name=None,
                    scheduled_at=sch,
                    days_until=days_until,
                    description=a.description,
                )
            )
    next_acts.sort(key=lambda x: x.scheduled_at or datetime.max)
    next_acts = next_acts[:20]

    # ── Flags ──
    flags: list[str] = []
    if not deals:
        flags.append("no_deals")
    if open_deals and len(stagnant) > len(open_deals) / 2:
        flags.append("majority_deals_stagnant")
    if win_rate is not None and win_rate < 0.2:
        flags.append("win_rate_below_20pct")
    if overdue_count > 5:
        flags.append(f"activities_overdue_{overdue_count}")
    if not deals_mtd_new:
        flags.append("no_new_deals_this_month")

    from api.db.models import Tenant
    tenant_res = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = tenant_res.scalar_one_or_none()

    return SalesSnapshot(
        tenant_piva=tenant.piva if tenant else None,
        snapshot_at=now,
        open_deals_count=len(open_deals),
        open_pipeline_value=round(open_value, 2),
        weighted_pipeline_value=round(weighted_value, 2),
        stages=stage_stats,
        won_ytd_count=len(won_ytd),
        won_ytd_value=round(sum(d.revenue or 0 for d in won_ytd), 2),
        lost_ytd_count=len(lost_ytd),
        lost_ytd_value=round(sum(d.revenue or 0 for d in lost_ytd), 2),
        win_rate_ytd=round(win_rate, 3) if win_rate is not None else None,
        won_mtd_count=len(won_mtd),
        won_mtd_value=round(sum(d.revenue or 0 for d in won_mtd), 2),
        new_deals_mtd=len(deals_mtd_new),
        stagnant_deals=stagnant,
        high_value_no_activity=high_no_act,
        top_contacts=top_contacts,
        activities_overdue=overdue_count,
        activities_today=today_count,
        activities_this_week=week_count,
        next_activities=next_acts,
        flags=flags,
    )
