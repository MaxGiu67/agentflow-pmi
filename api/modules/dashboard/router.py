"""Router for dashboard module."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from api.modules.dashboard.schemas import AgentStatus, DashboardSummary, YearlyStats
from api.modules.dashboard.service import DashboardService

router = APIRouter(tags=["dashboard"])


def get_dashboard_service(db: AsyncSession = Depends(get_db)) -> DashboardService:
    return DashboardService(db)


@router.get("/dashboard/summary", response_model=DashboardSummary)
async def dashboard_summary(
    user: User = Depends(get_current_user),
    service: DashboardService = Depends(get_dashboard_service),
) -> DashboardSummary:
    """Get complete dashboard summary with counters, recent invoices, and agent status."""
    result = await service.get_summary(user)
    return DashboardSummary(**result)


@router.get("/dashboard/yearly-stats", response_model=YearlyStats)
async def get_yearly_stats(
    year: int = Query(..., ge=2000, le=2100),
    user: User = Depends(get_current_user),
    service: DashboardService = Depends(get_dashboard_service),
) -> YearlyStats:
    """Get yearly statistics: totals, monthly breakdown, top clients/suppliers."""
    result = await service.get_yearly_stats(user, year)
    return YearlyStats(**result)


@router.get("/dashboard/crm-stats")
async def get_crm_stats(
    user: User = Depends(get_current_user),
    service: DashboardService = Depends(get_dashboard_service),
):
    """CRM stats for commerciale dashboard: pipeline, deals, activities."""
    return await service.get_crm_stats(user)


@router.get("/agents/status", response_model=list[AgentStatus])
async def agents_status(
    user: User = Depends(get_current_user),
    service: DashboardService = Depends(get_dashboard_service),
) -> list[AgentStatus]:
    """Get status of all agents."""
    statuses = await service.get_agent_statuses(user)
    return [AgentStatus(**s) for s in statuses]
