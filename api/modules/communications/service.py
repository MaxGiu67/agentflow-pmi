"""Communications service — email generation for accountant (US-70).

Generates pre-filled email template for requesting bilancio/data from accountant.
"""

import logging
import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import Tenant

logger = logging.getLogger(__name__)


class CommunicationsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def generate_email(
        self,
        tenant_id: uuid.UUID,
        template_type: str = "bilancio_request",
        year: int = 0,
        notes: str = "",
    ) -> dict:
        """Generate pre-filled email for accountant (US-70)."""
        from sqlalchemy import select
        result = await self.db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()

        company_name = tenant.name if tenant else "La nostra azienda"
        target_year = year or date.today().year

        if template_type == "bilancio_request":
            subject = f"Richiesta bilancio di verifica {target_year} - {company_name}"
            body = _bilancio_request_template(company_name, target_year, notes)
        elif template_type == "document_request":
            subject = f"Richiesta documenti contabili - {company_name}"
            body = _document_request_template(company_name, target_year, notes)
        elif template_type == "f24_request":
            subject = f"Richiesta dati F24 {target_year} - {company_name}"
            body = _f24_request_template(company_name, target_year, notes)
        else:
            subject = f"Comunicazione contabile - {company_name}"
            body = _generic_template(company_name, notes)

        return {
            "template_type": template_type,
            "subject": subject,
            "body": body,
            "year": target_year,
            "company_name": company_name,
        }


def _bilancio_request_template(company: str, year: int, notes: str) -> str:
    text = f"""Gentile Commercialista,

Le scrivo per richiedere il bilancio di verifica aggiornato per l'anno {year} relativo a {company}.

In particolare, avremmo bisogno di:
- Bilancio di verifica completo con saldi dare/avere
- Situazione patrimoniale ed economica
- Eventuali rettifiche di fine periodo

Il formato preferito e CSV o Excel, per facilitare l'importazione nel nostro sistema gestionale.
"""
    if notes:
        text += f"\nNote aggiuntive: {notes}\n"
    text += "\nGrazie per la collaborazione.\nCordiali saluti"
    return text


def _document_request_template(company: str, year: int, notes: str) -> str:
    text = f"""Gentile Commercialista,

Le scrivo per richiedere la seguente documentazione contabile per {company}, anno {year}:

- Registro IVA vendite e acquisti
- Libro giornale
- Registri dei cespiti ammortizzabili
- Liquidazioni IVA periodiche
"""
    if notes:
        text += f"\nNote aggiuntive: {notes}\n"
    text += "\nGrazie per la collaborazione.\nCordiali saluti"
    return text


def _f24_request_template(company: str, year: int, notes: str) -> str:
    text = f"""Gentile Commercialista,

Le scrivo per richiedere i dati relativi ai versamenti F24 dell'anno {year} per {company}.

In particolare:
- Elenco dei versamenti effettuati con codici tributo
- Eventuali compensazioni effettuate
- Situazione crediti/debiti tributari
"""
    if notes:
        text += f"\nNote aggiuntive: {notes}\n"
    text += "\nGrazie per la collaborazione.\nCordiali saluti"
    return text


def _generic_template(company: str, notes: str) -> str:
    text = f"""Gentile Commercialista,

Le scrivo in merito alla gestione contabile di {company}.
"""
    if notes:
        text += f"\n{notes}\n"
    text += "\nGrazie per la collaborazione.\nCordiali saluti"
    return text
