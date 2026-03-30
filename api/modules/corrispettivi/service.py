"""Service for corrispettivi telematici (US-47, US-48)."""

import logging
import uuid
from datetime import date
from math import ceil

from sqlalchemy import select, func, and_, extract
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import Corrispettivo, JournalEntry, JournalLine
from api.modules.corrispettivi.parser import parse_corrispettivo_xml

logger = logging.getLogger(__name__)


class CorrispettiviService:
    """Servizio per import e gestione corrispettivi telematici (XML COR10)."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def import_xml(self, tenant_id: uuid.UUID, xml_content: str) -> dict:
        """Import a single corrispettivo XML file (COR10).

        Parses XML, creates Corrispettivo record, and generates journal entry.
        """
        parsed = parse_corrispettivo_xml(xml_content)

        if parsed.totale_incasso == 0 and parsed.totale_imponibile == 0:
            return {
                "status": "skipped",
                "message": "Corrispettivo vuoto (incasso zero)",
                "data": (parsed.data_rilevazione or parsed.data_trasmissione or date.today()).isoformat(),
            }

        data_corrispettivo = parsed.data_rilevazione or parsed.data_trasmissione or date.today()

        # Check for duplicate (same date + same device)
        existing = await self.db.execute(
            select(Corrispettivo).where(
                Corrispettivo.tenant_id == tenant_id,
                Corrispettivo.data == data_corrispettivo,
                Corrispettivo.dispositivo_id == parsed.dispositivo_id,
            )
        )
        if existing.scalar_one_or_none():
            return {
                "status": "duplicate",
                "message": f"Corrispettivo {data_corrispettivo} da {parsed.dispositivo_id} gia presente",
                "data": data_corrispettivo.isoformat(),
            }

        # Create corrispettivo record
        corr = Corrispettivo(
            tenant_id=tenant_id,
            data=data_corrispettivo,
            dispositivo_id=parsed.dispositivo_id,
            piva_esercente=parsed.piva_esercente,
            imponibile=round(parsed.totale_imponibile, 2),
            imposta=round(parsed.totale_imposta, 2),
            totale_contanti=round(parsed.totale_contanti, 2),
            totale_elettronico=round(parsed.totale_elettronico, 2),
            num_documenti=parsed.num_documenti,
            source="import_xml",
            raw_xml=xml_content[:50000],
        )
        self.db.add(corr)
        await self.db.flush()

        # Create journal entry (Dare: Cassa/Banca, Avere: Ricavi + IVA)
        totale_incasso = round(parsed.totale_incasso, 2)
        totale_imponibile = round(parsed.totale_imponibile, 2)
        totale_imposta = round(parsed.totale_imposta, 2)

        je = JournalEntry(
            tenant_id=tenant_id,
            description=f"Corrispettivi {data_corrispettivo} — {parsed.num_documenti} scontrini",
            entry_date=data_corrispettivo,
            total_debit=totale_incasso,
            total_credit=totale_incasso,
            status="posted",
        )
        self.db.add(je)
        await self.db.flush()

        # Dare: Cassa (contanti) + Banca (elettronico)
        if parsed.totale_contanti > 0:
            self.db.add(JournalLine(
                entry_id=je.id,
                account_code="cassa",
                account_name="Cassa contanti",
                description=f"Incasso contanti {data_corrispettivo}",
                debit=round(parsed.totale_contanti, 2),
                credit=0,
            ))
        if parsed.totale_elettronico > 0:
            self.db.add(JournalLine(
                entry_id=je.id,
                account_code="banca_pos",
                account_name="Banca c/POS",
                description=f"Incasso POS {data_corrispettivo}",
                debit=round(parsed.totale_elettronico, 2),
                credit=0,
            ))

        # Avere: Ricavi per ogni aliquota + IVA
        for riep in parsed.riepiloghi:
            if riep.imponibile > 0:
                self.db.add(JournalLine(
                    entry_id=je.id,
                    account_code=f"ricavi_corr_{int(riep.aliquota)}",
                    account_name=f"Ricavi corrispettivi IVA {riep.aliquota}%",
                    description=f"Vendite {data_corrispettivo} al {riep.aliquota}%",
                    debit=0,
                    credit=round(riep.imponibile, 2),
                ))
            if riep.imposta > 0:
                self.db.add(JournalLine(
                    entry_id=je.id,
                    account_code="iva_debito",
                    account_name="IVA c/vendite",
                    description=f"IVA {riep.aliquota}% su corrispettivi {data_corrispettivo}",
                    debit=0,
                    credit=round(riep.imposta, 2),
                ))

        corr.journal_entry_id = je.id
        await self.db.flush()

        return {
            "status": "imported",
            "corrispettivo_id": str(corr.id),
            "journal_entry_id": str(je.id),
            "data": data_corrispettivo.isoformat(),
            "num_documenti": parsed.num_documenti,
            "totale_incasso": totale_incasso,
            "totale_imponibile": totale_imponibile,
            "totale_imposta": totale_imposta,
            "contanti": round(parsed.totale_contanti, 2),
            "elettronico": round(parsed.totale_elettronico, 2),
            "message": f"Corrispettivi {data_corrispettivo}: €{totale_incasso:,.2f} ({parsed.num_documenti} scontrini)",
        }

    async def import_batch(self, tenant_id: uuid.UUID, xml_files: list[tuple[str, str]]) -> dict:
        """Import multiple corrispettivi XML files (batch)."""
        imported = 0
        skipped = 0
        duplicates = 0
        errors = 0
        details = []

        for filename, xml_content in xml_files:
            try:
                result = await self.import_xml(tenant_id, xml_content)
                if result["status"] == "imported":
                    imported += 1
                elif result["status"] == "duplicate":
                    duplicates += 1
                elif result["status"] == "skipped":
                    skipped += 1
                details.append({"file": filename, **result})
            except Exception as e:
                errors += 1
                details.append({"file": filename, "status": "error", "message": str(e)})
                logger.error("Errore import corrispettivo %s: %s", filename, e)

        return {
            "total_files": len(xml_files),
            "imported": imported,
            "duplicates": duplicates,
            "skipped": skipped,
            "errors": errors,
            "details": details,
        }

    async def list_corrispettivi(
        self,
        tenant_id: uuid.UUID,
        year: int | None = None,
        month: int | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict:
        """List corrispettivi with filters."""
        conditions = [Corrispettivo.tenant_id == tenant_id]
        if year:
            conditions.append(extract("year", Corrispettivo.data) == year)
        if month:
            conditions.append(extract("month", Corrispettivo.data) == month)

        count_q = select(func.count(Corrispettivo.id)).where(and_(*conditions))
        total = (await self.db.execute(count_q)).scalar() or 0

        q = (
            select(Corrispettivo)
            .where(and_(*conditions))
            .order_by(Corrispettivo.data.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(q)
        items = result.scalars().all()

        return {
            "items": [self._to_dict(c) for c in items],
            "total": total,
            "page": page,
            "pages": ceil(total / page_size) if page_size > 0 else 0,
        }

    def _to_dict(self, c: Corrispettivo) -> dict:
        return {
            "id": c.id,
            "tenant_id": c.tenant_id,
            "data": c.data,
            "dispositivo_id": c.dispositivo_id,
            "piva_esercente": c.piva_esercente,
            "imponibile": c.imponibile,
            "imposta": c.imposta,
            "totale_contanti": c.totale_contanti,
            "totale_elettronico": c.totale_elettronico,
            "num_documenti": c.num_documenti,
            "source": c.source,
            "journal_entry_id": c.journal_entry_id,
            "created_at": c.created_at,
        }
