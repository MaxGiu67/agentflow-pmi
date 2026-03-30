"""Service layer for onboarding module."""

import logging
import uuid
from datetime import datetime, UTC

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import OnboardingState, User

logger = logging.getLogger(__name__)

STEP_DESCRIPTIONS = {
    1: "Configura il profilo aziendale",
    2: "Inserisci regime fiscale e P.IVA",
    3: "Collega SPID per accesso al cassetto fiscale",
    4: "Sincronizza le fatture dal cassetto fiscale",
}


class OnboardingService:
    """Service for onboarding wizard operations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _get_or_create_state(self, user_id: uuid.UUID) -> OnboardingState:
        """Get existing onboarding state or create a new one."""
        result = await self.db.execute(
            select(OnboardingState).where(OnboardingState.user_id == user_id)
        )
        state = result.scalar_one_or_none()
        if not state:
            state = OnboardingState(user_id=user_id)
            self.db.add(state)
            await self.db.flush()
        return state

    async def get_status(self, user: User) -> dict:
        """Get current onboarding status."""
        state = await self._get_or_create_state(user.id)

        # Determine current step (next step to complete)
        current_step = state.step_completed + 1
        if state.completed or current_step > 4:
            current_step = 4

        # Next action
        if state.completed:
            next_action = "Onboarding completato! Vai alla dashboard."
        else:
            next_action = STEP_DESCRIPTIONS.get(current_step, "Completa l'onboarding")

        # Message
        if state.completed:
            message = "Onboarding completato con successo!"
        elif state.step_completed == 0:
            message = "Benvenuto! Inizia configurando il profilo aziendale."
        else:
            message = f"Step {state.step_completed}/4 completati. Prossimo: {next_action}"

        return {
            "step_completed": state.step_completed,
            "step1_profile": state.step1_profile,
            "step2_piva": state.step2_piva,
            "step3_spid": state.step3_spid,
            "step4_sync": state.step4_sync,
            "completed": state.completed,
            "current_step": current_step,
            "next_action": next_action,
            "message": message,
        }

    async def complete_step(self, user: User, step_number: int, data: dict) -> dict:
        """Complete an onboarding step."""
        if step_number < 1 or step_number > 4:
            raise ValueError("Step non valido. Deve essere tra 1 e 4.")

        state = await self._get_or_create_state(user.id)

        # Validate prerequisites (steps must be done in order, but can be re-done)
        if step_number > 1:
            getattr(state, f"step{step_number - 1}_{'profile' if step_number == 2 else 'piva' if step_number == 3 else 'spid'}")
            # Actually check each prerequisite step
            prerequisites_met = True
            for prev in range(1, step_number):
                step_attr = {1: "step1_profile", 2: "step2_piva", 3: "step3_spid", 4: "step4_sync"}
                if not getattr(state, step_attr[prev]):
                    prerequisites_met = False
                    break

            if not prerequisites_met:
                raise ValueError(f"Completa prima lo step {step_number - 1}")

        piano_conti_note = None

        # Mark step as complete
        if step_number == 1:
            state.step1_profile = True
            message = "Profilo aziendale configurato"
            # Check for tipo "altro"
            tipo_azienda = data.get("tipo_azienda", "")
            if tipo_azienda == "altro":
                piano_conti_note = "Piano conti generico applicato. Si consiglia di consultare il proprio commercialista per personalizzarlo."
        elif step_number == 2:
            state.step2_piva = True
            message = "Regime fiscale e P.IVA configurati"
        elif step_number == 3:
            # SPID can fail — step is still marked but we note the issue
            spid_success = data.get("spid_success", True)
            if spid_success:
                state.step3_spid = True
                message = "SPID collegato con successo"
            else:
                # SPID failed — don't mark as complete
                raise ValueError(
                    "Autenticazione SPID non riuscita. Riprova oppure prosegui con i passi precedenti."
                )
        elif step_number == 4:
            state.step4_sync = True
            message = "Sincronizzazione fatture avviata"

        # Update step_completed counter
        completed_count = sum([
            state.step1_profile,
            state.step2_piva,
            state.step3_spid,
            state.step4_sync,
        ])
        state.step_completed = completed_count
        state.completed = completed_count == 4
        state.updated_at = datetime.now(UTC).replace(tzinfo=None)

        await self.db.flush()

        # Next action
        if state.completed:
            next_action = "Onboarding completato! Vai alla dashboard."
        else:
            next_step = state.step_completed + 1
            if next_step > 4:
                next_step = 4
            next_action = STEP_DESCRIPTIONS.get(next_step, "Completa l'onboarding")

        result = {
            "step": step_number,
            "completed": state.completed,
            "step_completed": state.step_completed,
            "message": message,
            "next_action": next_action,
        }

        if piano_conti_note:
            result["piano_conti_note"] = piano_conti_note

        return result
