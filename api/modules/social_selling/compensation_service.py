"""Service for compensation rules + monthly calculation (US-148→US-150)."""

import logging
import uuid
from datetime import date, datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import CrmCompensationRule, CrmCompensationEntry, CrmDeal, User

logger = logging.getLogger(__name__)


class CompensationService:
    """Compensation rules CRUD + monthly calculation."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── US-148: Rules CRUD ─────────────────────────────

    async def create_rule(self, tenant_id: uuid.UUID, user_id: uuid.UUID, data: dict) -> dict:
        """AC-148.1: Create compensation rule."""
        name = data.get("name", "").strip()
        if not name:
            return {"error": "Nome regola obbligatorio"}

        method = data.get("calculation_method", "percent_revenue")
        if method not in ("percent_revenue", "fixed_amount", "tiered"):
            return {"error": "calculation_method deve essere: percent_revenue, fixed_amount, tiered"}

        base_config = data.get("base_config", {})
        if not base_config:
            return {"error": "base_config obbligatorio"}

        rule = CrmCompensationRule(
            tenant_id=tenant_id,
            name=name,
            trigger=data.get("trigger", "deal_won"),
            calculation_method=method,
            base_config=base_config,
            conditions=data.get("conditions"),
            priority=data.get("priority", 0),
            is_active=True,
            created_by=user_id,
        )
        self.db.add(rule)
        await self.db.flush()
        return self._rule_to_dict(rule)

    async def list_rules(self, tenant_id: uuid.UUID) -> list[dict]:
        result = await self.db.execute(
            select(CrmCompensationRule).where(
                CrmCompensationRule.tenant_id == tenant_id,
            ).order_by(CrmCompensationRule.priority)
        )
        return [self._rule_to_dict(r) for r in result.scalars().all()]

    # ── US-149: Calculate monthly compensation ─────────

    async def calculate_monthly(self, tenant_id: uuid.UUID, month: date) -> list[dict]:
        """AC-149.1/149.2: Calculate compensation for all users for a month."""
        # Get active rules
        rules_result = await self.db.execute(
            select(CrmCompensationRule).where(
                CrmCompensationRule.tenant_id == tenant_id,
                CrmCompensationRule.is_active.is_(True),
            ).order_by(CrmCompensationRule.priority)
        )
        rules = rules_result.scalars().all()

        if not rules:
            return []

        # Get users
        users_result = await self.db.execute(
            select(User).where(User.tenant_id == tenant_id, User.active.is_(True))
        )
        users = users_result.scalars().all()

        month_start = date(month.year, month.month, 1)
        if month.month == 12:
            month_end = date(month.year + 1, 1, 1)
        else:
            month_end = date(month.year, month.month + 1, 1)

        entries = []
        for user in users:
            # Get won deals for user in month (H5: single CTE-like query)
            deals_result = await self.db.execute(
                select(
                    func.count(CrmDeal.id),
                    func.coalesce(func.sum(CrmDeal.expected_revenue), 0.0),
                ).where(
                    CrmDeal.tenant_id == tenant_id,
                    CrmDeal.assigned_to == user.id,
                    CrmDeal.probability == 100,  # won deals
                    CrmDeal.updated_at >= month_start,
                    CrmDeal.updated_at < month_end,
                )
            )
            row = deals_result.one()
            deal_count = row[0] or 0
            total_revenue = float(row[1] or 0)

            if total_revenue == 0:
                continue

            # Apply rules
            amount = 0.0
            rules_applied = []
            for rule in rules:
                rule_amount = self._apply_rule(rule, total_revenue)
                amount += rule_amount
                rules_applied.append({
                    "rule_id": str(rule.id),
                    "rule_name": rule.name,
                    "amount": rule_amount,
                })

            # Check for existing entry
            existing = await self.db.execute(
                select(CrmCompensationEntry).where(
                    CrmCompensationEntry.tenant_id == tenant_id,
                    CrmCompensationEntry.user_id == user.id,
                    CrmCompensationEntry.month == month_start,
                )
            )
            entry = existing.scalar_one_or_none()
            if entry:
                entry.amount_gross = amount
                entry.rules_applied = rules_applied
                entry.deal_contributions = {"deal_count": deal_count, "total_revenue": total_revenue}
            else:
                entry = CrmCompensationEntry(
                    tenant_id=tenant_id,
                    user_id=user.id,
                    month=month_start,
                    amount_gross=amount,
                    rules_applied=rules_applied,
                    deal_contributions={"deal_count": deal_count, "total_revenue": total_revenue},
                    status="draft",
                )
                self.db.add(entry)

            await self.db.flush()
            entries.append(self._entry_to_dict(entry))

        return entries

    # ── US-149/150: List + Confirm + Pay ───────────────

    async def list_monthly(
        self, tenant_id: uuid.UUID, month: str = "", status: str = "", user_id: uuid.UUID | None = None,
    ) -> list[dict]:
        query = select(CrmCompensationEntry).where(CrmCompensationEntry.tenant_id == tenant_id)
        if month:
            query = query.where(CrmCompensationEntry.month == month)
        if status:
            query = query.where(CrmCompensationEntry.status == status)
        if user_id:
            query = query.where(CrmCompensationEntry.user_id == user_id)
        query = query.order_by(CrmCompensationEntry.month.desc())
        result = await self.db.execute(query)
        return [self._entry_to_dict(e) for e in result.scalars().all()]

    async def confirm_entry(self, entry_id: uuid.UUID) -> dict | None:
        """AC-150.1: Confirm compensation entry."""
        result = await self.db.execute(
            select(CrmCompensationEntry).where(CrmCompensationEntry.id == entry_id)
        )
        entry = result.scalar_one_or_none()
        if not entry:
            return None
        if entry.status != "draft":
            return {"error": f"Compenso non in stato bozza (attuale: {entry.status})"}
        entry.status = "confirmed"
        entry.confirmed_at = datetime.utcnow()
        await self.db.flush()
        return self._entry_to_dict(entry)

    async def mark_paid(self, entry_id: uuid.UUID) -> dict | None:
        """AC-150.3: Mark as paid."""
        result = await self.db.execute(
            select(CrmCompensationEntry).where(CrmCompensationEntry.id == entry_id)
        )
        entry = result.scalar_one_or_none()
        if not entry:
            return None
        if entry.status != "confirmed":
            return {"error": f"Compenso non confermato (attuale: {entry.status})"}
        entry.status = "paid"
        entry.paid_at = datetime.utcnow()
        await self.db.flush()
        return self._entry_to_dict(entry)

    # ── Calculation helpers ────────────────────────────

    def _apply_rule(self, rule: CrmCompensationRule, revenue: float) -> float:
        """Apply a single compensation rule to revenue."""
        method = rule.calculation_method
        config = rule.base_config or {}

        if method == "percent_revenue":
            rate = config.get("rate", 0) / 100
            return revenue * rate

        elif method == "fixed_amount":
            return config.get("amount", 0)

        elif method == "tiered":
            # AC-148.2: Tiered calculation
            tiers = config.get("tiers", [])
            remaining = revenue
            total = 0.0
            for tier in sorted(tiers, key=lambda t: t.get("min", 0)):
                tier_min = tier.get("min", 0)
                tier_max = tier.get("max", float("inf"))
                rate = tier.get("rate", 0) / 100
                applicable = min(remaining, tier_max - tier_min)
                if applicable > 0:
                    total += applicable * rate
                    remaining -= applicable
                if remaining <= 0:
                    break
            return total

        return 0.0

    def _rule_to_dict(self, r: CrmCompensationRule) -> dict:
        return {
            "id": str(r.id),
            "name": r.name,
            "trigger": r.trigger,
            "calculation_method": r.calculation_method,
            "base_config": r.base_config,
            "conditions": r.conditions,
            "priority": r.priority,
            "is_active": r.is_active,
        }

    def _entry_to_dict(self, e: CrmCompensationEntry) -> dict:
        return {
            "id": str(e.id),
            "user_id": str(e.user_id),
            "month": str(e.month),
            "amount_gross": e.amount_gross,
            "rules_applied": e.rules_applied,
            "deal_contributions": e.deal_contributions,
            "status": e.status,
            "error_message": e.error_message,
            "confirmed_at": e.confirmed_at.isoformat() if e.confirmed_at else None,
            "paid_at": e.paid_at.isoformat() if e.paid_at else None,
        }
