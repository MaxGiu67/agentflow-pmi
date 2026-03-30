"""Schemas for the onboarding module."""


from pydantic import BaseModel


class OnboardingStatusResponse(BaseModel):
    """Current onboarding state."""
    step_completed: int
    step1_profile: bool
    step2_piva: bool
    step3_spid: bool
    step4_sync: bool
    completed: bool
    current_step: int
    next_action: str
    message: str


class StepCompleteRequest(BaseModel):
    """Request to complete an onboarding step."""
    data: dict = {}


class StepCompleteResponse(BaseModel):
    """Response from completing an onboarding step."""
    step: int
    completed: bool
    step_completed: int
    message: str
    next_action: str
    piano_conti_note: str | None = None
