"""Normativo Agent for monitoring regulatory updates (US-28).

Monitors RSS feeds from Gazzetta Ufficiale and Agenzia delle Entrate
for fiscal/regulatory changes affecting PMI.
"""

import logging
import uuid
from datetime import date, datetime, UTC

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.agents.base_agent import BaseAgent
from api.db.models import FiscalRule, NormativeAlert

logger = logging.getLogger(__name__)

# Mock RSS feed items for testing
MOCK_RSS_ITEMS = [
    {
        "source": "agenzia_entrate",
        "title": "Circolare n. 15/E - Aggiornamento aliquota IVA ridotta",
        "description": "Modifica aliquota IVA ridotta dal 10% al 11% per specifiche categorie merceologiche.",
        "url": "https://www.agenziaentrate.gov.it/circolari/15e-2026",
        "published_at": "2026-03-01T10:00:00",
        "effective_date": "2026-07-01",
        "proposed_rule_key": "iva_ridotta",
        "proposed_rule_value": "11.0",
    },
    {
        "source": "gazzetta_ufficiale",
        "title": "DL 45/2026 - Nuova soglia ritenuta d'acconto",
        "description": "Innalzamento soglia minima per applicazione ritenuta d'acconto a 500 EUR.",
        "url": "https://www.gazzettaufficiale.it/dl-45-2026",
        "published_at": "2026-02-15T08:00:00",
        "effective_date": "2026-04-01",
        "proposed_rule_key": "soglia_ritenuta",
        "proposed_rule_value": "500.0",
    },
]


class NormativoAgent(BaseAgent):
    """Agent for monitoring regulatory changes."""

    agent_name: str = "normativo"

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)
        self._feed_available: bool = True
        self._mock_items: list[dict] = list(MOCK_RSS_ITEMS)

    def set_feed_available(self, available: bool) -> None:
        """For testing: control feed availability."""
        self._feed_available = available

    def set_mock_items(self, items: list[dict]) -> None:
        """For testing: set mock feed items."""
        self._mock_items = items

    async def check_feed(
        self,
        tenant_id: uuid.UUID,
    ) -> dict:
        """Check RSS feed for new normative updates.

        AC-28.1: Alert su circolare AdE (feed RSS GU mock).
        AC-28.3: Feed non disponibile -> retry backoff.
        AC-28.4: Norma con decorrenza futura -> schedula, non modifica regole correnti.
        """
        # AC-28.3: Check feed availability
        if not self._feed_available:
            # Publish retry event
            await self.publish_event(
                event_type="normativo.feed.unavailable",
                payload={"message": "Feed RSS non disponibile, retry programmato"},
                tenant_id=tenant_id,
            )
            return {
                "status": "feed_unavailable",
                "message": "Feed RSS non disponibile. Retry con backoff programmato.",
                "alerts": [],
                "retry_scheduled": True,
            }

        # Fetch mock RSS items
        new_alerts: list[dict] = []
        today = date.today()

        for item in self._mock_items:
            # Check if alert already exists
            existing = await self.db.execute(
                select(NormativeAlert).where(
                    NormativeAlert.tenant_id == tenant_id,
                    NormativeAlert.title == item["title"],
                )
            )
            if existing.scalar_one_or_none():
                continue

            # Parse effective date
            effective_date = None
            if item.get("effective_date"):
                effective_date = date.fromisoformat(item["effective_date"])

            # AC-28.4: Determine status based on effective date
            alert_status = "new"
            if effective_date and effective_date > today:
                alert_status = "scheduled"

            alert = NormativeAlert(
                tenant_id=tenant_id,
                source=item["source"],
                title=item["title"],
                description=item.get("description"),
                url=item.get("url"),
                published_at=datetime.fromisoformat(item["published_at"]) if item.get("published_at") else None,
                effective_date=effective_date,
                impact_preview=self._generate_impact_preview(item),
                proposed_rule_key=item.get("proposed_rule_key"),
                proposed_rule_value=item.get("proposed_rule_value"),
                status=alert_status,
            )
            self.db.add(alert)
            await self.db.flush()

            # If effective_date is today or past, apply rule update
            if effective_date and effective_date <= today and item.get("proposed_rule_key"):
                await self._apply_rule_update(
                    tenant_id=tenant_id,
                    key=item["proposed_rule_key"],
                    value=item["proposed_rule_value"],
                    effective_date=effective_date,
                    law_reference=item["title"],
                )
                alert.status = "applied"
                await self.db.flush()
            elif effective_date and effective_date > today and item.get("proposed_rule_key"):
                # AC-28.4: Schedule for future, don't modify current rules
                await self._schedule_rule_update(
                    key=item["proposed_rule_key"],
                    value=item["proposed_rule_value"],
                    effective_date=effective_date,
                    law_reference=item["title"],
                )

            new_alerts.append({
                "id": str(alert.id),
                "source": alert.source,
                "title": alert.title,
                "description": alert.description,
                "url": alert.url,
                "effective_date": alert.effective_date.isoformat() if alert.effective_date else None,
                "impact_preview": alert.impact_preview,
                "proposed_rule_key": alert.proposed_rule_key,
                "proposed_rule_value": alert.proposed_rule_value,
                "status": alert.status,
            })

        # Publish event
        if new_alerts:
            await self.publish_event(
                event_type="normativo.alerts.new",
                payload={"count": len(new_alerts)},
                tenant_id=tenant_id,
            )

        return {
            "status": "ok",
            "message": f"Trovati {len(new_alerts)} nuovi aggiornamenti normativi",
            "alerts": new_alerts,
            "retry_scheduled": False,
        }

    async def list_alerts(
        self,
        tenant_id: uuid.UUID,
    ) -> dict:
        """List all normative alerts.

        AC-28.1: Alert su circolari.
        """
        result = await self.db.execute(
            select(NormativeAlert).where(
                NormativeAlert.tenant_id == tenant_id,
            ).order_by(NormativeAlert.created_at.desc())
        )
        items = result.scalars().all()

        return {
            "items": [
                {
                    "id": str(a.id),
                    "source": a.source,
                    "title": a.title,
                    "description": a.description,
                    "url": a.url,
                    "published_at": a.published_at.isoformat() if a.published_at else None,
                    "effective_date": a.effective_date.isoformat() if a.effective_date else None,
                    "impact_preview": a.impact_preview,
                    "proposed_rule_key": a.proposed_rule_key,
                    "proposed_rule_value": a.proposed_rule_value,
                    "status": a.status,
                }
                for a in items
            ],
            "total": len(items),
        }

    def _generate_impact_preview(self, item: dict) -> str:
        """AC-28.2: Generate impact preview for a normative change."""
        key = item.get("proposed_rule_key", "")
        value = item.get("proposed_rule_value", "")
        description = item.get("description", "")

        preview = f"Impatto: {description}"
        if key and value:
            preview += f"\nRegola interessata: {key} -> nuovo valore: {value}"
        if item.get("effective_date"):
            preview += f"\nDecorrenza: {item['effective_date']}"

        return preview

    async def _apply_rule_update(
        self,
        tenant_id: uuid.UUID,
        key: str,
        value: str,
        effective_date: date,
        law_reference: str,
    ) -> None:
        """Apply a rule update immediately (effective date is today or past)."""
        rule = FiscalRule(
            key=key,
            value=value,
            value_type="decimal",
            valid_from=effective_date,
            law_reference=law_reference,
            description=f"Aggiornamento automatico da {law_reference}",
        )
        self.db.add(rule)
        await self.db.flush()

    async def _schedule_rule_update(
        self,
        key: str,
        value: str,
        effective_date: date,
        law_reference: str,
    ) -> None:
        """AC-28.4: Schedule a rule update for a future date.

        Creates a FiscalRule with valid_from in the future.
        Current rules remain unchanged.
        """
        # Check if already scheduled
        existing = await self.db.execute(
            select(FiscalRule).where(
                FiscalRule.key == key,
                FiscalRule.valid_from == effective_date,
            )
        )
        if existing.scalar_one_or_none():
            return

        rule = FiscalRule(
            key=key,
            value=value,
            value_type="decimal",
            valid_from=effective_date,
            law_reference=law_reference,
            description=f"Aggiornamento programmato da {law_reference} (decorrenza {effective_date})",
        )
        self.db.add(rule)
        await self.db.flush()

        logger.info(
            "Scheduled rule update: %s = %s effective %s",
            key, value, effective_date,
        )
