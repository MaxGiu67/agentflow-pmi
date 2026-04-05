"""Service for CRM dashboards + scorecard (US-146→US-147)."""

import logging
import uuid
from datetime import date, timedelta

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import CrmDashboardWidget, CrmDeal, CrmActivity

logger = logging.getLogger(__name__)


class DashboardService:
    """Custom dashboards and scorecard calculation."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── US-146: Dashboard CRUD ─────────────────────────

    async def create_dashboard(self, tenant_id: uuid.UUID, user_id: uuid.UUID, data: dict) -> dict:
        """AC-146.1: Create composable dashboard."""
        name = data.get("name", "").strip()
        if not name:
            return {"error": "Nome dashboard obbligatorio"}

        layout = data.get("dashboard_layout", [])
        if not layout:
            return {"error": "dashboard_layout obbligatorio"}

        # AC-146.3: Validate all widgets have period
        for widget in layout:
            if not widget.get("period"):
                return {"error": "Tutti i widget devono avere Periodo configurato"}

        dashboard = CrmDashboardWidget(
            tenant_id=tenant_id,
            name=name,
            dashboard_layout=layout,
            created_by=user_id,
            is_shared=data.get("is_shared", False),
        )
        self.db.add(dashboard)
        await self.db.flush()
        return self._to_dict(dashboard)

    async def list_dashboards(self, tenant_id: uuid.UUID) -> list[dict]:
        result = await self.db.execute(
            select(CrmDashboardWidget).where(
                CrmDashboardWidget.tenant_id == tenant_id,
            ).order_by(CrmDashboardWidget.name)
        )
        return [self._to_dict(d) for d in result.scalars().all()]

    # ── US-147: Scorecard ──────────────────────────────

    async def get_scorecard(
        self, tenant_id: uuid.UUID, user_id: uuid.UUID,
        start_date: date | None = None, end_date: date | None = None,
    ) -> dict:
        """AC-147.1/147.2: Scorecard KPI for a user."""
        if not start_date:
            start_date = date.today().replace(day=1)
        if not end_date:
            end_date = date.today()

        # Deal count
        deal_count = await self.db.scalar(
            select(func.count(CrmDeal.id)).where(
                CrmDeal.tenant_id == tenant_id,
                CrmDeal.assigned_to == user_id,
                CrmDeal.created_at >= start_date,
                CrmDeal.created_at <= end_date,
            )
        ) or 0

        # Won deals
        won_count = await self.db.scalar(
            select(func.count(CrmDeal.id)).where(
                CrmDeal.tenant_id == tenant_id,
                CrmDeal.assigned_to == user_id,
                CrmDeal.probability == 100,
                CrmDeal.updated_at >= start_date,
                CrmDeal.updated_at <= end_date,
            )
        ) or 0

        # Revenue closed
        revenue_closed = await self.db.scalar(
            select(func.coalesce(func.sum(CrmDeal.expected_revenue), 0.0)).where(
                CrmDeal.tenant_id == tenant_id,
                CrmDeal.assigned_to == user_id,
                CrmDeal.probability == 100,
                CrmDeal.updated_at >= start_date,
                CrmDeal.updated_at <= end_date,
            )
        ) or 0.0

        # Win rate
        win_rate = (won_count / deal_count * 100) if deal_count > 0 else 0.0

        # Activity count
        activity_count = await self.db.scalar(
            select(func.count(CrmActivity.id)).where(
                CrmActivity.tenant_id == tenant_id,
                CrmActivity.user_id == user_id,
                CrmActivity.created_at >= start_date,
                CrmActivity.created_at <= end_date,
            )
        ) or 0

        return {
            "user_id": str(user_id),
            "period": {"start": str(start_date), "end": str(end_date)},
            "kpis": {
                "deal_count": deal_count,
                "won_count": won_count,
                "revenue_closed": float(revenue_closed),
                "win_rate": round(win_rate, 1),
                "activity_count": activity_count,
            },
        }

    def _to_dict(self, d: CrmDashboardWidget) -> dict:
        return {
            "id": str(d.id),
            "name": d.name,
            "dashboard_layout": d.dashboard_layout,
            "created_by": str(d.created_by),
            "is_shared": d.is_shared,
        }
