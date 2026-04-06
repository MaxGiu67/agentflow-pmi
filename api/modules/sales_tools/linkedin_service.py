"""LinkedIn Social Selling service (US-214, US-215, US-216).

Message generation, warmth scoring, cadence tracking, CSV import.
All messages are COMPOSED by AI, never sent automatically (LinkedIn ToS).
"""

import csv
import io
import logging
import uuid
from datetime import datetime, timedelta

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import CrmActivity, CrmContact, CrmCompany

logger = logging.getLogger(__name__)

# LinkedIn activity types for cadence tracking
CADENCE_TYPES = [
    "linkedin_view", "linkedin_follow", "linkedin_like", "linkedin_comment",
    "linkedin_connection", "linkedin_dm", "linkedin_content_share",
    "linkedin_voice_note", "linkedin_call_ask",
]

# Cadence template (day → action)
CADENCE_TEMPLATE = [
    {"day": -7, "action": "linkedin_view", "label": "View profilo prospect"},
    {"day": -5, "action": "linkedin_follow", "label": "Follow pagina azienda"},
    {"day": -3, "action": "linkedin_like", "label": "Like post recente"},
    {"day": -1, "action": "linkedin_comment", "label": "Commento di valore (no pitch)"},
    {"day": 1, "action": "linkedin_connection", "label": "Connection request personalizzata"},
    {"day": 3, "action": "linkedin_dm", "label": "Conversation starter (no pitch)"},
    {"day": 7, "action": "linkedin_content_share", "label": "Share contenuto settoriale"},
    {"day": 10, "action": "linkedin_voice_note", "label": "Voice note LinkedIn"},
    {"day": 14, "action": "linkedin_call_ask", "label": "Soft ask per call (link Calendly)"},
    {"day": 18, "action": "linkedin_dm", "label": "Follow-up con insight aziendale"},
    {"day": 21, "action": "linkedin_dm", "label": "Breakup message (porta aperta)"},
]

# Warmth score points
WARMTH_POINTS = {
    "linkedin_connection": 20,  # Connection accepted
    "linkedin_dm": 30,  # Replied to DM
    "linkedin_like": 15,
    "linkedin_comment": 25,
    "linkedin_view": 10,
    "linkedin_content_share": 5,
}


class LinkedInService:
    """LinkedIn social selling tools."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── US-214: Message generation ─────────────────────

    def generate_message(
        self, message_type: str, prospect_name: str, company: str,
        ateco_sector: str = "", trigger_detail: str = "",
    ) -> dict:
        """Generate LinkedIn message for phase. NOT sent — composed for user to copy."""
        templates = {
            "connection_request": (
                f"Buongiorno {prospect_name}, ho visto {trigger_detail or 'il suo profilo'}. "
                f"Lavoriamo con PMI del settore {ateco_sector or 'manifatturiero'} su temi di innovazione AI. "
                f"Mi farebbe piacere connetterci."
            ),
            "conversation_starter": (
                f"Grazie per la connessione, {prospect_name}! Ho notato che {company} opera nel settore "
                f"{ateco_sector or 'produttivo'}. Come state gestendo la documentazione tecnica e i report?"
            ),
            "value_share": (
                f"{prospect_name}, pensando a {company} ho trovato questo caso studio su come "
                f"una PMI simile ha automatizzato i report di produzione. Potrebbe interessarti."
            ),
            "soft_ask": (
                f"{prospect_name}, dalle nostre conversazioni credo ci siano spunti interessanti "
                f"per {company}. Ha 10 minuti questa settimana per una chiacchierata veloce?"
            ),
            "breakup": (
                f"{prospect_name}, capisco che i tempi non siano giusti. Resto disponibile se in futuro "
                f"volete esplorare come l'AI puo aiutare {company}. Buon lavoro!"
            ),
        }

        text = templates.get(message_type, templates["conversation_starter"])

        # Enforce LinkedIn limits
        if message_type == "connection_request" and len(text) > 200:
            text = text[:197] + "..."
        elif len(text) > 300:
            text = text[:297] + "..."

        return {
            "message_type": message_type,
            "text": text,
            "char_count": len(text),
            "max_chars": 200 if message_type == "connection_request" else 300,
            "note": "Messaggio composto dall'AI. Copia e incolla su LinkedIn.",
        }

    # ── US-215: Warmth score ───────────────────────────

    async def calc_warmth_score(self, contact_id: uuid.UUID) -> dict:
        """Calculate warmth score from LinkedIn activities."""
        result = await self.db.execute(
            select(CrmActivity).where(
                CrmActivity.contact_id == contact_id,
                CrmActivity.type.in_(CADENCE_TYPES),
            ).order_by(CrmActivity.created_at.desc())
        )
        activities = result.scalars().all()

        score = 0
        activity_summary = []
        for act in activities:
            points = WARMTH_POINTS.get(act.type, 5)
            score += points
            activity_summary.append({"type": act.type, "points": points, "date": act.created_at.isoformat() if act.created_at else ""})

        score = min(score, 100)

        if score >= 60:
            label = "hot"
            suggestion = "Prospect caldo. Suggerisco di proporre la discovery call."
        elif score >= 30:
            label = "warm"
            suggestion = "Prospect in warming. Continua con contenuti di valore."
        else:
            label = "cold"
            suggestion = "Prospect freddo. Inizia il warm-up (view profilo, like, commento)."

        return {
            "score": score,
            "label": label,
            "suggestion": suggestion,
            "activities": activity_summary[:10],
        }

    # ── US-215: Cadence tracking ───────────────────────

    async def check_cadence(self, contact_id: uuid.UUID) -> dict:
        """Check where we are in the LinkedIn cadence for a contact."""
        # Get first linkedin activity to determine cadence start
        result = await self.db.execute(
            select(CrmActivity).where(
                CrmActivity.contact_id == contact_id,
                CrmActivity.type.in_(CADENCE_TYPES),
            ).order_by(CrmActivity.created_at.asc())
        )
        activities = list(result.scalars().all())

        if not activities:
            return {
                "cadence_day": 0,
                "cadence_started": False,
                "completed_steps": [],
                "next_action": CADENCE_TEMPLATE[0],
                "suggestion": "Cadence non iniziata. Primo step: view profilo prospect.",
            }

        first_activity_date = activities[0].created_at.date() if activities[0].created_at else None
        if not first_activity_date:
            first_activity_date = datetime.utcnow().date()

        days_since_start = (datetime.utcnow().date() - first_activity_date).days
        completed_types = {a.type for a in activities}

        # Find next uncompleted step
        next_step = None
        for step in CADENCE_TEMPLATE:
            if step["action"] not in completed_types:
                next_step = step
                break

        last_activity = activities[-1] if activities else None
        days_since_last = (datetime.utcnow().date() - last_activity.created_at.date()).days if last_activity and last_activity.created_at else 0

        return {
            "cadence_day": days_since_start,
            "cadence_started": True,
            "completed_steps": [{"type": a.type, "date": a.created_at.isoformat() if a.created_at else ""} for a in activities],
            "total_touchpoints": len(activities),
            "days_since_last_contact": days_since_last,
            "next_action": next_step,
            "suggestion": f"Giorno {days_since_start} della cadence. {next_step['label'] if next_step else 'Cadence completata.'}",
        }

    # ── US-216: CSV Import ─────────────────────────────

    async def import_csv(self, tenant_id: uuid.UUID, csv_content: str) -> dict:
        """Import LinkedIn prospect list from CSV."""
        reader = csv.DictReader(io.StringIO(csv_content))
        imported = 0
        duplicates = 0
        errors = 0

        for row in reader:
            company_name = row.get("Company", row.get("company", row.get("azienda", ""))).strip()
            first_name = row.get("First Name", row.get("first_name", row.get("nome", ""))).strip()
            last_name = row.get("Last Name", row.get("last_name", row.get("cognome", ""))).strip()
            title = row.get("Title", row.get("title", row.get("ruolo", ""))).strip()

            if not company_name or not (first_name or last_name):
                errors += 1
                continue

            full_name = f"{first_name} {last_name}".strip()

            # Check duplicate
            existing = await self.db.execute(
                select(CrmContact).where(
                    CrmContact.tenant_id == tenant_id,
                    CrmContact.contact_name == full_name,
                )
            )
            if existing.scalar_one_or_none():
                duplicates += 1
                continue

            # Create/find company
            company_result = await self.db.execute(
                select(CrmCompany).where(
                    CrmCompany.tenant_id == tenant_id,
                    CrmCompany.name == company_name,
                )
            )
            company = company_result.scalar_one_or_none()
            if not company:
                company = CrmCompany(tenant_id=tenant_id, name=company_name)
                self.db.add(company)
                await self.db.flush()

            # Create contact
            contact = CrmContact(
                tenant_id=tenant_id,
                name=company_name,
                contact_name=full_name,
                contact_role=title,
                company_id=company.id,
                source="linkedin_import",
            )
            self.db.add(contact)
            imported += 1

        await self.db.flush()

        return {
            "imported": imported,
            "duplicates": duplicates,
            "errors": errors,
            "total_processed": imported + duplicates + errors,
        }
