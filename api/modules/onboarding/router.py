"""Router for onboarding module."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from api.modules.onboarding.schemas import (
    OnboardingStatusResponse,
    StepCompleteRequest,
    StepCompleteResponse,
)
from api.modules.onboarding.service import OnboardingService

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


def get_onboarding_service(db: AsyncSession = Depends(get_db)) -> OnboardingService:
    return OnboardingService(db)


@router.get("/status", response_model=OnboardingStatusResponse)
async def onboarding_status(
    user: User = Depends(get_current_user),
    service: OnboardingService = Depends(get_onboarding_service),
) -> OnboardingStatusResponse:
    """Get current onboarding status (step, what's done, what's next)."""
    result = await service.get_status(user)
    return OnboardingStatusResponse(**result)


@router.post("/step/{step_number}", response_model=StepCompleteResponse)
async def complete_step(
    step_number: int,
    request: StepCompleteRequest = StepCompleteRequest(),
    user: User = Depends(get_current_user),
    service: OnboardingService = Depends(get_onboarding_service),
) -> StepCompleteResponse:
    """Complete an onboarding step."""
    try:
        result = await service.complete_step(user, step_number, request.data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return StepCompleteResponse(**result)
