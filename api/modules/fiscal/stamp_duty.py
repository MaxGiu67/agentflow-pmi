"""Stamp duty (imposta di bollo) service (US-35)."""

import logging
import uuid
import xml.etree.ElementTree as ET
from datetime import date

from sqlalchemy import select, func as sqla_func
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import Invoice, StampDuty

logger = logging.getLogger(__name__)

# Stamp duty thresholds
BOLLO_SOGLIA = 77.47  # EUR - minimum for stamp duty
BOLLO_IMPORTO = 2.00  # EUR - stamp duty amount

# IVA exempt nature codes (Natura in FatturaPA)
EXEMPT_NATURE_CODES = {"N1", "N2", "N2.1", "N2.2", "N3", "N4", "N5"}

# Quarter due dates (day 16 of month after quarter end)
QUARTER_DUE_DATES = {
    1: (5, 31),   # Q1: 31 maggio
    2: (9, 30),   # Q2: 30 settembre
    3: (11, 30),  # Q3: 30 novembre
    4: (2, 28),   # Q4: 28 febbraio anno successivo
}


class StampDutyService:
    """Business logic for stamp duty (imposta di bollo) management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def check_invoice(
        self,
        invoice_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> dict:
        """Check if an invoice requires stamp duty.

        AC-35.1: Detect obligation on exempt invoices > 77.47 EUR -> <BolloVirtuale>
        AC-35.3: Under threshold -> NO stamp duty
        AC-35.4: Mixed invoice -> stamp duty only if exempt portion > 77.47
        AC-35.5: Passive invoice received without stamp duty -> warning
        """
        result = await self.db.execute(
            select(Invoice).where(
                Invoice.id == invoice_id,
                Invoice.tenant_id == tenant_id,
            )
        )
        invoice = result.scalar_one_or_none()
        if not invoice:
            raise ValueError("Fattura non trovata")

        # Analyze invoice for exempt amounts
        exempt_amount = self._calculate_exempt_amount(invoice)
        total_amount = invoice.importo_totale or 0.0

        # AC-35.3: Under threshold
        if exempt_amount <= BOLLO_SOGLIA:
            return {
                "invoice_id": str(invoice_id),
                "bollo_required": False,
                "importo_esente": round(exempt_amount, 2),
                "importo_totale": round(total_amount, 2),
                "soglia": BOLLO_SOGLIA,
                "importo_bollo": 0.0,
                "bollo_virtuale": False,
                "message": (
                    f"Importo esente ({exempt_amount:.2f} EUR) sotto soglia "
                    f"({BOLLO_SOGLIA:.2f} EUR). Bollo non dovuto."
                ),
                "warning": None,
            }

        # AC-35.1 / AC-35.4: Stamp duty required
        # Determine quarter
        inv_date = invoice.data_fattura or date.today()
        quarter = (inv_date.month - 1) // 3 + 1

        # Create stamp duty record
        existing = await self.db.execute(
            select(StampDuty).where(
                StampDuty.invoice_id == invoice_id,
                StampDuty.tenant_id == tenant_id,
            )
        )
        if existing.scalar_one_or_none() is None:
            sd = StampDuty(
                tenant_id=tenant_id,
                invoice_id=invoice_id,
                importo_bollo=BOLLO_IMPORTO,
                importo_esente=exempt_amount,
                bollo_virtuale=True,
                year=inv_date.year,
                quarter=quarter,
            )
            self.db.add(sd)

            # Update invoice
            invoice.has_bollo = True
            await self.db.flush()

        # AC-35.5: Check if passive invoice without bollo tag
        warning = None
        if invoice.type == "passiva":
            has_bollo_tag = self._check_bollo_tag(invoice.raw_xml)
            if not has_bollo_tag:
                warning = (
                    f"Fattura passiva {invoice.numero_fattura} con importo esente "
                    f"({exempt_amount:.2f} EUR) > soglia ({BOLLO_SOGLIA:.2f} EUR) "
                    "ricevuta senza indicazione del bollo. "
                    "Verificare con il fornitore."
                )

        return {
            "invoice_id": str(invoice_id),
            "bollo_required": True,
            "importo_esente": round(exempt_amount, 2),
            "importo_totale": round(total_amount, 2),
            "soglia": BOLLO_SOGLIA,
            "importo_bollo": BOLLO_IMPORTO,
            "bollo_virtuale": True,
            "message": (
                f"Bollo virtuale dovuto: {BOLLO_IMPORTO:.2f} EUR. "
                f"Importo esente: {exempt_amount:.2f} EUR."
            ),
            "warning": warning,
        }

    async def get_quarterly_summary(
        self,
        tenant_id: uuid.UUID,
        year: int,
        quarter: int,
    ) -> dict:
        """Get quarterly stamp duty summary.

        AC-35.2: Count quarterly (N invoices x 2 EUR, deadline, code 2501)
        """
        if quarter not in (1, 2, 3, 4):
            raise ValueError("Trimestre deve essere tra 1 e 4")

        # Count stamp duties for the quarter
        result = await self.db.execute(
            select(
                sqla_func.count(StampDuty.id),
                sqla_func.coalesce(sqla_func.sum(StampDuty.importo_bollo), 0.0),
            ).where(
                StampDuty.tenant_id == tenant_id,
                StampDuty.year == year,
                StampDuty.quarter == quarter,
            )
        )
        row = result.one()
        count = int(row[0])
        total_bollo = float(row[1])

        # Due date
        due_month, due_day = QUARTER_DUE_DATES[quarter]
        due_year = year + 1 if quarter == 4 else year
        due_date = date(due_year, due_month, due_day)

        return {
            "year": year,
            "quarter": quarter,
            "period": f"Q{quarter} {year}",
            "invoice_count": count,
            "importo_unitario": BOLLO_IMPORTO,
            "importo_totale": round(total_bollo, 2),
            "f24_code": "2501",
            "due_date": due_date.isoformat(),
            "message": (
                f"Imposta di bollo Q{quarter} {year}: "
                f"{count} fatture x {BOLLO_IMPORTO:.2f} EUR = {total_bollo:.2f} EUR. "
                f"Scadenza versamento: {due_date.isoformat()}. Codice tributo: 2501."
            ),
        }

    def _calculate_exempt_amount(self, invoice: Invoice) -> float:
        """Calculate exempt amount from invoice structured data.

        AC-35.4: For mixed invoices, only the exempt portion counts.
        """
        structured = invoice.structured_data or {}
        riepilogo = structured.get("riepilogo", [])

        exempt_total = 0.0

        for riep in riepilogo:
            aliquota = riep.get("aliquota_iva", 0.0) or 0.0
            imponibile = riep.get("imponibile", 0.0) or 0.0

            if aliquota == 0.0:
                # This is an exempt line
                exempt_total += imponibile
            else:
                pass

        # If no structured data, check if entire invoice is exempt
        if not riepilogo:
            iva = invoice.importo_iva or 0.0
            if iva == 0.0:
                # Entire invoice is exempt
                exempt_total = invoice.importo_totale or 0.0

        return exempt_total

    def _check_bollo_tag(self, raw_xml: str | None) -> bool:
        """Check if XML contains <BolloVirtuale> or <DatiBollo> tag."""
        if not raw_xml:
            return False

        try:
            root = ET.fromstring(raw_xml)
        except ET.ParseError:
            return False

        # Check for DatiBollo or BolloVirtuale
        for tag in ("DatiBollo", "BolloVirtuale"):
            for ns_uri in ["http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2"]:
                if root.find(f".//{{{ns_uri}}}{tag}") is not None:
                    return True
            if root.find(f".//{tag}") is not None:
                return True

        return False
