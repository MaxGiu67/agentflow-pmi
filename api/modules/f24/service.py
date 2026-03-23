"""Service layer for F24 compilazione e generazione (US-38)."""

import logging
import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import (
    F24Document,
    Invoice,
    StampDuty,
    VatSettlement,
    WithholdingTax,
)

logger = logging.getLogger(__name__)

# IVA quarterly tribute codes (6031=Q1, 6032=Q2, 6033=Q3, 6034=Q4)
IVA_TRIBUTE_CODES = {1: "6031", 2: "6032", 3: "6033", 4: "6034"}

# F24 due dates per quarter (16th of 2nd month following quarter)
IVA_DUE_DATES = {
    1: (5, 16),   # Q1 -> 16 May
    2: (8, 16),   # Q2 -> 16 Aug (actually 20 Aug but simplified)
    3: (11, 16),  # Q3 -> 16 Nov
    4: (3, 16),   # Q4 -> 16 Mar next year
}


class F24Service:
    """Business logic for F24 generation and management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def generate_f24(
        self,
        tenant_id: uuid.UUID,
        year: int,
        month: int | None = None,
        quarter: int | None = None,
        fisco_api_amount: float | None = None,
    ) -> dict:
        """Generate F24 for a given period.

        AC-38.1: F24 da liquidazione IVA -> sezione Erario, codice tributo.
        AC-38.2: F24 da ritenute -> codice 1040.
        AC-38.3: Importo FiscoAPI diverso da stima -> mostra entrambi.
        AC-38.4: Compensazione crediti IVA -> netto da versare.
        """
        sections: list[dict] = []
        total_debit = 0.0
        total_credit = 0.0
        warnings: list[str] = []

        # --- AC-38.1: IVA from VatSettlement ---
        if quarter is not None:
            iva_sections, iva_debit, iva_credit = await self._get_iva_sections(
                tenant_id, year, quarter,
            )
            sections.extend(iva_sections)
            total_debit += iva_debit
            total_credit += iva_credit

        # --- AC-38.2: Ritenute d'acconto ---
        if month is not None:
            wt_sections, wt_debit = await self._get_withholding_sections(
                tenant_id, year, month,
            )
            sections.extend(wt_sections)
            total_debit += wt_debit

        # --- Bollo (stamp duty) - aggregate if quarter present ---
        if quarter is not None:
            bollo_sections, bollo_debit = await self._get_stamp_duty_sections(
                tenant_id, year, quarter,
            )
            sections.extend(bollo_sections)
            total_debit += bollo_debit

        # AC-38.4: Net amount after compensation
        net_amount = round(total_debit - total_credit, 2)

        # AC-38.3: Compare with FiscoAPI amount if provided
        amount_difference = None
        if fisco_api_amount is not None:
            amount_difference = round(fisco_api_amount - net_amount, 2)
            if abs(amount_difference) > 0.01:
                warnings.append(
                    f"Importo FiscoAPI ({fisco_api_amount:.2f}) diverso da stima "
                    f"({net_amount:.2f}), differenza: {amount_difference:.2f}"
                )

        # Calculate due date
        due_date = self._calculate_due_date(year, month, quarter)

        # Delete existing F24 for same period
        await self._delete_existing(tenant_id, year, month, quarter)

        # Create F24 document
        f24 = F24Document(
            tenant_id=tenant_id,
            year=year,
            period_month=month,
            period_quarter=quarter,
            sections=sections,
            total_debit=round(total_debit, 2),
            total_credit=round(total_credit, 2),
            net_amount=net_amount,
            fisco_api_amount=fisco_api_amount,
            amount_difference=amount_difference,
            status="generated",
            due_date=due_date,
        )
        self.db.add(f24)
        await self.db.flush()

        return {
            "f24": {
                "id": str(f24.id),
                "tenant_id": str(f24.tenant_id),
                "year": f24.year,
                "period_month": f24.period_month,
                "period_quarter": f24.period_quarter,
                "sections": f24.sections,
                "total_debit": f24.total_debit,
                "total_credit": f24.total_credit,
                "net_amount": f24.net_amount,
                "fisco_api_amount": f24.fisco_api_amount,
                "amount_difference": f24.amount_difference,
                "status": f24.status,
                "due_date": str(f24.due_date) if f24.due_date else None,
            },
            "warnings": warnings,
        }

    async def list_f24(
        self,
        tenant_id: uuid.UUID,
        year: int | None = None,
    ) -> dict:
        """List F24 documents for a tenant."""
        query = select(F24Document).where(F24Document.tenant_id == tenant_id)
        if year:
            query = query.where(F24Document.year == year)
        query = query.order_by(F24Document.year.desc(), F24Document.due_date.desc())

        result = await self.db.execute(query)
        items = result.scalars().all()

        return {
            "items": [self._f24_to_dict(f) for f in items],
            "total": len(items),
        }

    async def get_f24(
        self,
        f24_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> dict:
        """Get F24 detail with sections."""
        result = await self.db.execute(
            select(F24Document).where(
                F24Document.id == f24_id,
                F24Document.tenant_id == tenant_id,
            )
        )
        f24 = result.scalar_one_or_none()
        if not f24:
            raise ValueError("F24 non trovato")
        return self._f24_to_dict(f24)

    async def export_f24(
        self,
        f24_id: uuid.UUID,
        tenant_id: uuid.UUID,
        format: str = "pdf",
    ) -> dict:
        """Export F24 in PDF or telematico format.

        AC-38.1: Export PDF/telematico.
        """
        result = await self.db.execute(
            select(F24Document).where(
                F24Document.id == f24_id,
                F24Document.tenant_id == tenant_id,
            )
        )
        f24 = result.scalar_one_or_none()
        if not f24:
            raise ValueError("F24 non trovato")

        if format == "pdf":
            content = self._export_pdf(f24)
            filename = f"F24_{f24.year}_{f24.period_quarter or f24.period_month}.pdf"
        else:
            content = self._export_telematico(f24)
            filename = f"F24_{f24.year}_{f24.period_quarter or f24.period_month}.txt"

        f24.status = "exported"
        await self.db.flush()

        return {
            "id": str(f24.id),
            "format": format,
            "content": content,
            "filename": filename,
        }

    async def mark_paid(
        self,
        f24_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> dict:
        """Mark F24 as paid."""
        result = await self.db.execute(
            select(F24Document).where(
                F24Document.id == f24_id,
                F24Document.tenant_id == tenant_id,
            )
        )
        f24 = result.scalar_one_or_none()
        if not f24:
            raise ValueError("F24 non trovato")

        f24.status = "paid"
        await self.db.flush()

        return {
            "id": str(f24.id),
            "status": f24.status,
            "net_amount": f24.net_amount,
        }

    # ---- Private helpers ----

    async def _get_iva_sections(
        self, tenant_id: uuid.UUID, year: int, quarter: int,
    ) -> tuple[list[dict], float, float]:
        """AC-38.1: Get IVA sections from VatSettlement."""
        sections: list[dict] = []
        total_debit = 0.0
        total_credit = 0.0

        result = await self.db.execute(
            select(VatSettlement).where(
                VatSettlement.tenant_id == tenant_id,
                VatSettlement.year == year,
                VatSettlement.quarter == quarter,
            )
        )
        settlement = result.scalar_one_or_none()

        if settlement:
            codice_tributo = IVA_TRIBUTE_CODES.get(quarter, "6031")
            periodo = f"T{quarter}"

            if settlement.saldo > 0:
                # IVA a debito
                sections.append({
                    "section_type": "erario",
                    "codice_tributo": codice_tributo,
                    "anno_riferimento": year,
                    "periodo_riferimento": periodo,
                    "importo_debito": round(settlement.saldo, 2),
                    "importo_credito": 0.0,
                    "description": f"IVA trimestrale Q{quarter} {year}",
                })
                total_debit += settlement.saldo
            else:
                # AC-38.4: IVA a credito (compensazione)
                credit_amount = abs(settlement.saldo)
                sections.append({
                    "section_type": "credito",
                    "codice_tributo": codice_tributo,
                    "anno_riferimento": year,
                    "periodo_riferimento": periodo,
                    "importo_debito": 0.0,
                    "importo_credito": round(credit_amount, 2),
                    "description": f"Credito IVA Q{quarter} {year} - compensazione",
                })
                total_credit += credit_amount

        return sections, round(total_debit, 2), round(total_credit, 2)

    async def _get_withholding_sections(
        self, tenant_id: uuid.UUID, year: int, month: int,
    ) -> tuple[list[dict], float]:
        """AC-38.2: Get withholding tax sections."""
        sections: list[dict] = []
        total_debit = 0.0

        result = await self.db.execute(
            select(WithholdingTax).where(
                WithholdingTax.tenant_id == tenant_id,
            )
        )
        all_wt = result.scalars().all()

        # Filter by month: withholding taxes whose invoice date is in the target month
        wt_for_month: list[WithholdingTax] = []
        for wt in all_wt:
            inv_result = await self.db.execute(
                select(Invoice).where(Invoice.id == wt.invoice_id)
            )
            inv = inv_result.scalar_one_or_none()
            if inv and inv.data_fattura:
                if inv.data_fattura.year == year and inv.data_fattura.month == month:
                    wt_for_month.append(wt)

        if wt_for_month:
            total_ritenute = sum(wt.importo_ritenuta for wt in wt_for_month)
            sections.append({
                "section_type": "erario",
                "codice_tributo": "1040",
                "anno_riferimento": year,
                "periodo_riferimento": f"{month:02d}",
                "importo_debito": round(total_ritenute, 2),
                "importo_credito": 0.0,
                "description": f"Ritenute d'acconto mese {month:02d}/{year}",
            })
            total_debit += total_ritenute

        return sections, round(total_debit, 2)

    async def _get_stamp_duty_sections(
        self, tenant_id: uuid.UUID, year: int, quarter: int,
    ) -> tuple[list[dict], float]:
        """Get stamp duty sections for F24."""
        sections: list[dict] = []
        total_debit = 0.0

        result = await self.db.execute(
            select(StampDuty).where(
                StampDuty.tenant_id == tenant_id,
                StampDuty.year == year,
                StampDuty.quarter == quarter,
            )
        )
        stamps = result.scalars().all()

        if stamps:
            total_bollo = sum(s.importo_bollo for s in stamps)
            sections.append({
                "section_type": "erario",
                "codice_tributo": "2501",
                "anno_riferimento": year,
                "periodo_riferimento": f"T{quarter}",
                "importo_debito": round(total_bollo, 2),
                "importo_credito": 0.0,
                "description": f"Imposta di bollo Q{quarter} {year}",
            })
            total_debit += total_bollo

        return sections, round(total_debit, 2)

    async def _delete_existing(
        self, tenant_id: uuid.UUID, year: int,
        month: int | None, quarter: int | None,
    ) -> None:
        """Delete existing F24 for same period."""
        query = select(F24Document).where(
            F24Document.tenant_id == tenant_id,
            F24Document.year == year,
        )
        if month is not None:
            query = query.where(F24Document.period_month == month)
        if quarter is not None:
            query = query.where(F24Document.period_quarter == quarter)

        result = await self.db.execute(query)
        for old_f24 in result.scalars().all():
            await self.db.delete(old_f24)
        await self.db.flush()

    def _calculate_due_date(
        self, year: int, month: int | None, quarter: int | None,
    ) -> date | None:
        """Calculate F24 due date."""
        if quarter is not None:
            m, d = IVA_DUE_DATES[quarter]
            due_year = year + 1 if quarter == 4 else year
            return date(due_year, m, d)
        if month is not None:
            # Ritenute due on 16th of following month
            next_month = month + 1
            next_year = year
            if next_month > 12:
                next_month = 1
                next_year = year + 1
            return date(next_year, next_month, 16)
        return None

    def _f24_to_dict(self, f24: F24Document) -> dict:
        """Convert F24Document to dict."""
        return {
            "id": str(f24.id),
            "tenant_id": str(f24.tenant_id),
            "year": f24.year,
            "period_month": f24.period_month,
            "period_quarter": f24.period_quarter,
            "sections": f24.sections,
            "total_debit": f24.total_debit,
            "total_credit": f24.total_credit,
            "net_amount": f24.net_amount,
            "fisco_api_amount": f24.fisco_api_amount,
            "amount_difference": f24.amount_difference,
            "status": f24.status,
            "due_date": str(f24.due_date) if f24.due_date else None,
        }

    def _export_pdf(self, f24: F24Document) -> str:
        """Export F24 as PDF-like text (mock).

        AC-38.1: Export PDF.
        """
        lines = [
            "=" * 60,
            "MODELLO F24 - DELEGA DI PAGAMENTO",
            "=" * 60,
            f"Anno: {f24.year}",
        ]
        if f24.period_quarter:
            lines.append(f"Periodo: Trimestre {f24.period_quarter}")
        if f24.period_month:
            lines.append(f"Periodo: Mese {f24.period_month:02d}")
        lines.append(f"Scadenza: {f24.due_date}")
        lines.append("")
        lines.append("SEZIONE ERARIO")
        lines.append("-" * 60)
        lines.append(f"{'Codice Tributo':<20}{'Periodo':<15}{'Debito':<15}{'Credito':<15}")

        if f24.sections:
            for s in f24.sections:
                lines.append(
                    f"{s.get('codice_tributo', ''):<20}"
                    f"{s.get('periodo_riferimento', ''):<15}"
                    f"{s.get('importo_debito', 0):<15.2f}"
                    f"{s.get('importo_credito', 0):<15.2f}"
                )

        lines.append("-" * 60)
        lines.append(f"Totale Debito: {f24.total_debit:.2f}")
        lines.append(f"Totale Credito: {f24.total_credit:.2f}")
        lines.append(f"NETTO DA VERSARE: {f24.net_amount:.2f}")
        lines.append("=" * 60)

        return "\n".join(lines)

    def _export_telematico(self, f24: F24Document) -> str:
        """Export F24 in telematico format (mock ministerial).

        AC-38.1: Export telematico.
        """
        records = [f"F24|{f24.year}|{f24.period_quarter or ''}|{f24.period_month or ''}"]

        if f24.sections:
            for s in f24.sections:
                records.append(
                    f"SEZ|{s.get('section_type', '')}|"
                    f"{s.get('codice_tributo', '')}|"
                    f"{s.get('periodo_riferimento', '')}|"
                    f"{s.get('importo_debito', 0):.2f}|"
                    f"{s.get('importo_credito', 0):.2f}"
                )

        records.append(
            f"TOT|{f24.total_debit:.2f}|{f24.total_credit:.2f}|{f24.net_amount:.2f}"
        )
        return "\n".join(records)
