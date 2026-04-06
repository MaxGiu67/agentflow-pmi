"""Cross-sell signal detection service (US-217, US-218).

Analyzes deal notes/activities for keywords that indicate cross-sell opportunities
between T&M and Elevia pipelines.
"""

import logging
import uuid
from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import CrmActivity, CrmDeal, CrossSellSignal

logger = logging.getLogger(__name__)

# Default keyword rules
CROSS_SELL_RULES = {
    "tm_to_elevia": {
        "keywords": ["documentazione", "documenti", "knowledge base", "report automatici", "processi manuali", "faq", "classificazione email"],
        "suggested_product": "Elevia AI",
        "signal_type": "documentation_pain",
    },
    "elevia_to_tm": {
        "keywords": ["sviluppo custom", "integrazione", "api", "sviluppo software", "team dedicato", "consulenza", "body rental"],
        "suggested_product": "Consulenza T&M",
        "signal_type": "custom_dev_need",
    },
}


class CrossSellService:
    """Cross-sell signal detection and reporting."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── US-217: Detect signals ─────────────────────────

    async def detect_signals(self, tenant_id: uuid.UUID, deal_id: uuid.UUID) -> list[dict]:
        """Analyze deal activities/notes for cross-sell keywords."""
        # Get deal info
        deal_result = await self.db.execute(select(CrmDeal).where(CrmDeal.id == deal_id))
        deal = deal_result.scalar_one_or_none()
        if not deal:
            return []

        # Get activities with descriptions
        activities = await self.db.execute(
            select(CrmActivity).where(
                CrmActivity.deal_id == deal_id,
                CrmActivity.description.isnot(None),
            )
        )

        # Combine all text to analyze
        texts = []
        for act in activities.scalars().all():
            if act.description:
                texts.append(act.description.lower())
            if act.subject:
                texts.append(act.subject.lower())

        combined_text = " ".join(texts)
        if not combined_text:
            return []

        signals = []
        for direction, rule in CROSS_SELL_RULES.items():
            for keyword in rule["keywords"]:
                if keyword in combined_text:
                    # Check if signal already exists
                    existing = await self.db.execute(
                        select(CrossSellSignal).where(
                            CrossSellSignal.deal_source_id == deal_id,
                            CrossSellSignal.keyword_matched == keyword,
                        )
                    )
                    if existing.scalar_one_or_none():
                        continue

                    signal = CrossSellSignal(
                        tenant_id=tenant_id,
                        deal_source_id=deal_id,
                        signal_type=rule["signal_type"],
                        keyword_matched=keyword,
                        suggested_product=rule["suggested_product"],
                        priority="high" if len([k for k in rule["keywords"] if k in combined_text]) >= 2 else "medium",
                    )
                    self.db.add(signal)
                    signals.append({
                        "keyword": keyword,
                        "direction": direction,
                        "suggested_product": rule["suggested_product"],
                        "signal_type": rule["signal_type"],
                    })

        if signals:
            await self.db.flush()
            logger.info("Detected %d cross-sell signals for deal %s", len(signals), deal_id)

        return signals

    # ── US-217: List signals ───────────────────────────

    async def list_signals(
        self, tenant_id: uuid.UUID, status: str = "", limit: int = 50,
    ) -> list[dict]:
        query = select(CrossSellSignal).where(CrossSellSignal.tenant_id == tenant_id)
        if status:
            query = query.where(CrossSellSignal.status == status)
        query = query.order_by(CrossSellSignal.created_at.desc()).limit(limit)

        result = await self.db.execute(query)
        return [self._to_dict(s) for s in result.scalars().all()]

    async def update_signal_status(self, signal_id: uuid.UUID, new_status: str) -> dict | None:
        result = await self.db.execute(select(CrossSellSignal).where(CrossSellSignal.id == signal_id))
        signal = result.scalar_one_or_none()
        if not signal:
            return None
        signal.status = new_status
        await self.db.flush()
        return self._to_dict(signal)

    # ── US-218: Report ─────────────────────────────────

    async def get_report(self, tenant_id: uuid.UUID) -> dict:
        total = await self.db.scalar(
            select(func.count(CrossSellSignal.id)).where(CrossSellSignal.tenant_id == tenant_id)
        ) or 0

        converted = await self.db.scalar(
            select(func.count(CrossSellSignal.id)).where(
                CrossSellSignal.tenant_id == tenant_id,
                CrossSellSignal.status == "converted",
            )
        ) or 0

        by_type = {}
        type_result = await self.db.execute(
            select(CrossSellSignal.signal_type, func.count(CrossSellSignal.id)).where(
                CrossSellSignal.tenant_id == tenant_id,
            ).group_by(CrossSellSignal.signal_type)
        )
        for row in type_result.all():
            by_type[row[0]] = row[1]

        return {
            "total_signals": total,
            "converted": converted,
            "conversion_rate": round(converted / total * 100, 1) if total > 0 else 0,
            "by_signal_type": by_type,
        }

    def _to_dict(self, s: CrossSellSignal) -> dict:
        return {
            "id": str(s.id),
            "deal_source_id": str(s.deal_source_id),
            "signal_type": s.signal_type,
            "keyword_matched": s.keyword_matched,
            "suggested_product": s.suggested_product,
            "priority": s.priority,
            "status": s.status,
            "created_at": s.created_at.isoformat() if s.created_at else "",
        }
