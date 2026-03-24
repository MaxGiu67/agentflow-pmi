"""Router for conto economico onboarding (personalized income statement)."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.agents.conto_economico_agent import ContoEconomicoAgent
from api.db.models import Tenant, User
from api.db.session import get_db
from api.middleware.auth import get_current_user

router = APIRouter(
    prefix="/onboarding/conto-economico",
    tags=["onboarding", "conto-economico"],
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class QuestionOut(BaseModel):
    id: int
    question: str
    type: str


class QuestionsResponse(BaseModel):
    template_name: str
    questions: list[QuestionOut]
    ricavi_suggeriti: list[str]
    costi_suggeriti: list[str]
    invoice_analysis: dict


class AnswerIn(BaseModel):
    question: str
    answer: str


class AnswersRequest(BaseModel):
    answers: list[AnswerIn]


class PersonalizedPlanResponse(BaseModel):
    ricavi: list[str]
    costi: list[str]
    note: str
    has_dipendenti: bool
    has_affitto: bool
    regime_suggerito: str


class ConfirmRequest(BaseModel):
    personalized: dict


class ConfirmResponse(BaseModel):
    accounts: list[dict]
    total: int
    ricavi_count: int
    costi_count: int
    note: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_tenant(user: User, db: AsyncSession) -> Tenant:
    """Resolve the tenant for the current user, raising 400 if missing."""
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Utente non associato a un tenant. Completa prima l'onboarding.",
        )
    result = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant non trovato.",
        )
    return tenant


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/questions", response_model=QuestionsResponse)
async def get_questions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QuestionsResponse:
    """Return questions based on the tenant's ATECO code.

    The questions come from a deterministic template selected by the first
    two digits of the codice ATECO stored on the tenant.
    """
    tenant = await _get_tenant(user, db)
    agent = ContoEconomicoAgent(db)
    data = await agent.generate_questions(tenant.codice_ateco or "", tenant.id)
    return QuestionsResponse(**data)


@router.post("/answers", response_model=PersonalizedPlanResponse)
async def process_answers(
    body: AnswersRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PersonalizedPlanResponse:
    """Process user answers and return a personalized conto economico plan.

    If ANTHROPIC_API_KEY is set the agent calls Claude to interpret the
    free-text answers; otherwise a solid rule-based fallback is used.
    """
    tenant = await _get_tenant(user, db)
    agent = ContoEconomicoAgent(db)
    answers = [a.model_dump() for a in body.answers]
    personalized = await agent.process_answers(
        tenant.codice_ateco or "", answers, tenant.id,
    )
    return PersonalizedPlanResponse(**personalized)


@router.post("/confirm", response_model=ConfirmResponse)
async def confirm_plan(
    body: ConfirmRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConfirmResponse:
    """Save the confirmed personalized conto economico plan.

    This creates ChartAccount entries for the tenant, replacing any
    existing ones.
    """
    tenant = await _get_tenant(user, db)
    agent = ContoEconomicoAgent(db)
    result = await agent.create_personalized_chart(tenant.id, body.personalized)
    return ConfirmResponse(**result)
