"""Router for commercialista reports (US-19)."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from api.modules.reports.schemas import ReportData
from api.modules.reports.service import ReportService

router = APIRouter(tags=["reports"])


def get_report_service(db: AsyncSession = Depends(get_db)) -> ReportService:
    return ReportService(db)


@router.get("/reports/commercialista", response_model=ReportData)
async def commercialista_report(
    period: str = Query(..., description="Period (Q1-2026, H1-2026, FY-2026)"),
    format: str = Query("pdf", description="Output format (pdf, csv)"),
    user: User = Depends(get_current_user),
    service: ReportService = Depends(get_report_service),
) -> ReportData:
    """Generate commercialista report for the given period."""
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    try:
        result = await service.generate_report(
            tenant_id=user.tenant_id,
            period=period,
            format=format,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return ReportData(**result)
