"""Service for F24 versamenti import (PDF + LLM) and CRUD (US-49, US-50)."""

import logging
import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import F24Versamento, JournalEntry, JournalLine

logger = logging.getLogger(__name__)


class F24ImportService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def import_pdf(
        self,
        tenant_id: uuid.UUID,
        filename: str,
        pdf_content: bytes,
    ) -> dict:
        """Import F24 versamenti from PDF via LLM extraction (US-49).

        Mock LLM extraction similar to banking import_service pattern.
        """
        # Mock LLM extraction (real implementation would call LLM)
        extracted = _mock_extract_f24_from_pdf(pdf_content)

        versamenti = []
        for item in extracted:
            v = F24Versamento(
                tenant_id=tenant_id,
                codice_tributo=item["codice_tributo"],
                periodo_riferimento=item.get("periodo_riferimento"),
                importo=item["importo"],
                data_versamento=date.fromisoformat(item["data_versamento"]),
                source="pdf_import",
            )
            self.db.add(v)
            versamenti.append(v)

        await self.db.flush()

        # Create journal entries for each versamento
        for v in versamenti:
            je = await self._create_journal_entry(tenant_id, v)
            v.journal_entry_id = je.id

        await self.db.flush()

        return {
            "filename": filename,
            "versamenti_count": len(versamenti),
            "versamenti": [
                {
                    "id": str(v.id),
                    "codice_tributo": v.codice_tributo,
                    "periodo_riferimento": v.periodo_riferimento,
                    "importo": v.importo,
                    "data_versamento": v.data_versamento.isoformat(),
                }
                for v in versamenti
            ],
            "message": f"Importati {len(versamenti)} versamenti F24 da PDF",
        }

    async def create_versamento(
        self,
        tenant_id: uuid.UUID,
        codice_tributo: str,
        periodo_riferimento: str,
        importo: float,
        data_versamento: str,
    ) -> dict:
        """Create a manual F24 versamento (US-50)."""
        v = F24Versamento(
            tenant_id=tenant_id,
            codice_tributo=codice_tributo,
            periodo_riferimento=periodo_riferimento,
            importo=importo,
            data_versamento=date.fromisoformat(data_versamento),
            source="manual",
        )
        self.db.add(v)
        await self.db.flush()

        je = await self._create_journal_entry(tenant_id, v)
        v.journal_entry_id = je.id
        await self.db.flush()

        return {
            "id": str(v.id),
            "codice_tributo": v.codice_tributo,
            "periodo_riferimento": v.periodo_riferimento,
            "importo": v.importo,
            "data_versamento": v.data_versamento.isoformat(),
            "journal_entry_id": str(je.id),
        }

    async def update_versamento(
        self,
        versamento_id: uuid.UUID,
        tenant_id: uuid.UUID,
        data: dict,
    ) -> dict:
        """Update a versamento (US-50)."""
        result = await self.db.execute(
            select(F24Versamento).where(
                F24Versamento.id == versamento_id,
                F24Versamento.tenant_id == tenant_id,
            )
        )
        v = result.scalar_one_or_none()
        if not v:
            raise ValueError("Versamento non trovato")

        for key in ("codice_tributo", "periodo_riferimento", "importo", "data_versamento"):
            if key in data:
                if key == "data_versamento":
                    setattr(v, key, date.fromisoformat(data[key]))
                else:
                    setattr(v, key, data[key])

        await self.db.flush()

        return {
            "id": str(v.id),
            "codice_tributo": v.codice_tributo,
            "periodo_riferimento": v.periodo_riferimento,
            "importo": v.importo,
            "data_versamento": v.data_versamento.isoformat(),
        }

    async def delete_versamento(
        self,
        versamento_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> dict:
        """Delete a versamento (US-50)."""
        result = await self.db.execute(
            select(F24Versamento).where(
                F24Versamento.id == versamento_id,
                F24Versamento.tenant_id == tenant_id,
            )
        )
        v = result.scalar_one_or_none()
        if not v:
            raise ValueError("Versamento non trovato")

        await self.db.delete(v)
        await self.db.flush()

        return {"deleted": True, "id": str(versamento_id)}

    async def _create_journal_entry(
        self, tenant_id: uuid.UUID, versamento: F24Versamento
    ) -> JournalEntry:
        """Create journal entry: Dare erario conti, Avere Banca."""
        je = JournalEntry(
            tenant_id=tenant_id,
            description=f"Versamento F24 - {versamento.codice_tributo} - {versamento.data_versamento.isoformat()}",
            entry_date=versamento.data_versamento,
            total_debit=versamento.importo,
            total_credit=versamento.importo,
            status="posted",
        )
        self.db.add(je)
        await self.db.flush()

        # Dare: Erario conti
        self.db.add(JournalLine(
            entry_id=je.id,
            account_code="2510",
            account_name="Erario c/tributi",
            debit=versamento.importo,
            credit=0.0,
            description=f"Versamento tributo {versamento.codice_tributo}",
        ))

        # Avere: Banca
        self.db.add(JournalLine(
            entry_id=je.id,
            account_code="1510",
            account_name="Banca c/c",
            debit=0.0,
            credit=versamento.importo,
            description=f"Pagamento F24 {versamento.codice_tributo}",
        ))

        await self.db.flush()
        return je


def _mock_extract_f24_from_pdf(pdf_content: bytes) -> list:
    """Mock LLM extraction from F24 PDF.

    In production, this would call Anthropic/OpenAI with the PDF text.
    """
    return [
        {
            "codice_tributo": "1040",
            "periodo_riferimento": "01/2026",
            "importo": 500.00,
            "data_versamento": "2026-02-16",
        },
        {
            "codice_tributo": "6031",
            "periodo_riferimento": "T1/2026",
            "importo": 1200.00,
            "data_versamento": "2026-05-16",
        },
    ]
