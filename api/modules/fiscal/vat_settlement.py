"""VAT settlement (liquidazione IVA) service (US-22).

Implements quarterly VAT computation:
  IVA debito (vendite) - IVA credito (acquisti) - credito precedente + interessi (1% trim)

Handles reverse charge (both debit and credit), unregistered invoices warning,
and prior period credit carry-forward.
"""

import logging
import uuid
from datetime import date, datetime, UTC

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import (
    ActiveInvoice,
    Invoice,
    JournalEntry,
    JournalLine,
    VatSettlement,
)

logger = logging.getLogger(__name__)

# Quarter date ranges
QUARTER_RANGES = {
    1: (1, 1, 3, 31),
    2: (4, 1, 6, 30),
    3: (7, 1, 9, 30),
    4: (10, 1, 12, 31),
}


class VatSettlementService:
    """Service for computing and managing quarterly VAT settlements."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def compute(
        self,
        tenant_id: uuid.UUID,
        year: int,
        quarter: int,
    ) -> dict:
        """Compute quarterly VAT settlement (liquidazione IVA).

        Formula:
          saldo = iva_debito_vendite + iva_reverse_charge_debito
                  - iva_credito_acquisti - iva_reverse_charge_credito
                  - credito_periodo_precedente
                  + interessi (1% se debito e non primo trimestre)

        Returns:
            Dict with full VAT settlement breakdown.
        """
        if quarter not in (1, 2, 3, 4):
            raise ValueError("Trimestre deve essere tra 1 e 4")

        start_month, start_day, end_month, end_day = QUARTER_RANGES[quarter]
        period_start = date(year, start_month, start_day)
        period_end = date(year, end_month, end_day)

        # 1. IVA vendite (fatture attive emesse = IVA a debito)
        iva_vendite = await self._compute_iva_vendite(tenant_id, period_start, period_end)

        # 2. IVA acquisti (fatture passive ricevute = IVA a credito)
        iva_acquisti = await self._compute_iva_acquisti(tenant_id, period_start, period_end)

        # 3. Reverse charge (both debit and credit)
        iva_rc_debito, iva_rc_credito = await self._compute_reverse_charge(
            tenant_id, period_start, period_end,
        )

        # 4. Credito periodo precedente (carry-forward)
        credito_precedente = await self._get_previous_credit(tenant_id, year, quarter)

        # 5. Unregistered invoices warning
        unregistered_count = await self._count_unregistered(tenant_id, period_start, period_end)

        # 6. Compute saldo
        iva_debito_totale = iva_vendite + iva_rc_debito
        iva_credito_totale = iva_acquisti + iva_rc_credito

        saldo_pre_interessi = iva_debito_totale - iva_credito_totale - credito_precedente

        # 7. Interessi (1% trimestrale se saldo > 0)
        interessi = 0.0
        if saldo_pre_interessi > 0:
            interessi = round(saldo_pre_interessi * 0.01, 2)

        saldo = round(saldo_pre_interessi + interessi, 2)

        # 8. Save or update settlement record
        settlement = await self._save_settlement(
            tenant_id=tenant_id,
            year=year,
            quarter=quarter,
            iva_vendite=iva_vendite,
            iva_acquisti=iva_acquisti,
            iva_rc_debito=iva_rc_debito,
            iva_rc_credito=iva_rc_credito,
            credito_precedente=credito_precedente,
            interessi=interessi,
            saldo=saldo,
            unregistered_count=unregistered_count,
        )

        # Build warnings
        warnings: list[str] = []
        if unregistered_count > 0:
            warnings.append(
                f"{unregistered_count} fatture non registrate non incluse nel calcolo"
            )

        return {
            "id": str(settlement.id),
            "tenant_id": str(tenant_id),
            "year": year,
            "quarter": quarter,
            "period": f"Q{quarter} {year}",
            "iva_vendite": iva_vendite,
            "iva_acquisti": iva_acquisti,
            "iva_reverse_charge_debito": iva_rc_debito,
            "iva_reverse_charge_credito": iva_rc_credito,
            "iva_debito_totale": iva_debito_totale,
            "iva_credito_totale": iva_credito_totale,
            "credito_periodo_precedente": credito_precedente,
            "interessi": interessi,
            "saldo": saldo,
            "saldo_tipo": "debito" if saldo > 0 else ("credito" if saldo < 0 else "zero"),
            "unregistered_count": unregistered_count,
            "warnings": warnings,
            "status": settlement.status,
        }

    async def get_settlement(
        self,
        tenant_id: uuid.UUID,
        year: int,
        quarter: int,
    ) -> dict | None:
        """Get existing VAT settlement for a period."""
        result = await self.db.execute(
            select(VatSettlement).where(
                VatSettlement.tenant_id == tenant_id,
                VatSettlement.year == year,
                VatSettlement.quarter == quarter,
            )
        )
        settlement = result.scalar_one_or_none()
        if not settlement:
            return None

        iva_debito_totale = settlement.iva_vendite + settlement.iva_reverse_charge_debito
        iva_credito_totale = settlement.iva_acquisti + settlement.iva_reverse_charge_credito

        warnings: list[str] = []
        if settlement.unregistered_count > 0:
            warnings.append(
                f"{settlement.unregistered_count} fatture non registrate non incluse nel calcolo"
            )

        return {
            "id": str(settlement.id),
            "tenant_id": str(tenant_id),
            "year": settlement.year,
            "quarter": settlement.quarter,
            "period": f"Q{settlement.quarter} {settlement.year}",
            "iva_vendite": settlement.iva_vendite,
            "iva_acquisti": settlement.iva_acquisti,
            "iva_reverse_charge_debito": settlement.iva_reverse_charge_debito,
            "iva_reverse_charge_credito": settlement.iva_reverse_charge_credito,
            "iva_debito_totale": iva_debito_totale,
            "iva_credito_totale": iva_credito_totale,
            "credito_periodo_precedente": settlement.credito_periodo_precedente,
            "interessi": settlement.interessi,
            "saldo": settlement.saldo,
            "saldo_tipo": "debito" if settlement.saldo > 0 else ("credito" if settlement.saldo < 0 else "zero"),
            "unregistered_count": settlement.unregistered_count,
            "warnings": warnings,
            "status": settlement.status,
        }

    async def _compute_iva_vendite(
        self, tenant_id: uuid.UUID, start: date, end: date,
    ) -> float:
        """Compute IVA from active invoices (vendite) in the period."""
        result = await self.db.execute(
            select(func.coalesce(func.sum(ActiveInvoice.importo_iva), 0.0)).where(
                ActiveInvoice.tenant_id == tenant_id,
                ActiveInvoice.data_fattura >= start,
                ActiveInvoice.data_fattura <= end,
                ActiveInvoice.document_type == "TD01",
                ActiveInvoice.sdi_status.in_(["sent", "delivered"]),
            )
        )
        iva = result.scalar() or 0.0

        # Subtract credit notes (TD04 reduce IVA debito)
        result_nc = await self.db.execute(
            select(func.coalesce(func.sum(ActiveInvoice.importo_iva), 0.0)).where(
                ActiveInvoice.tenant_id == tenant_id,
                ActiveInvoice.data_fattura >= start,
                ActiveInvoice.data_fattura <= end,
                ActiveInvoice.document_type == "TD04",
                ActiveInvoice.sdi_status.in_(["sent", "delivered"]),
            )
        )
        iva_nc = result_nc.scalar() or 0.0

        return round(float(iva) - float(iva_nc), 2)

    async def _compute_iva_acquisti(
        self, tenant_id: uuid.UUID, start: date, end: date,
    ) -> float:
        """Compute IVA from passive invoices (acquisti) in the period."""
        result = await self.db.execute(
            select(func.coalesce(func.sum(Invoice.importo_iva), 0.0)).where(
                Invoice.tenant_id == tenant_id,
                Invoice.data_fattura >= start,
                Invoice.data_fattura <= end,
                Invoice.type == "passiva",
                Invoice.document_type == "TD01",
                Invoice.processing_status.in_(["categorized", "registered", "parsed"]),
            )
        )
        return round(float(result.scalar() or 0.0), 2)

    async def _compute_reverse_charge(
        self, tenant_id: uuid.UUID, start: date, end: date,
    ) -> tuple[float, float]:
        """Compute reverse charge IVA (both debit and credit).

        Reverse charge invoices (e.g. TD17/TD18/TD19) have IVA computed
        both as debito and credito, so they cancel out for the settlement
        but must be shown in the prospetto.

        For MVP, detect via document_type or has_ritenuta flag on passive invoices.
        """
        # Look for reverse charge passive invoices (document types TD17, TD18, TD19)
        # Or invoices with structured_data containing reverse_charge
        result = await self.db.execute(
            select(func.coalesce(func.sum(Invoice.importo_iva), 0.0)).where(
                Invoice.tenant_id == tenant_id,
                Invoice.data_fattura >= start,
                Invoice.data_fattura <= end,
                Invoice.type == "passiva",
                Invoice.document_type.in_(["TD17", "TD18", "TD19"]),
            )
        )
        rc_iva = round(float(result.scalar() or 0.0), 2)

        # Reverse charge: same amount goes to both debit and credit
        return rc_iva, rc_iva

    async def _get_previous_credit(
        self, tenant_id: uuid.UUID, year: int, quarter: int,
    ) -> float:
        """Get credit carry-forward from previous quarter."""
        # Determine previous quarter
        if quarter == 1:
            prev_year = year - 1
            prev_quarter = 4
        else:
            prev_year = year
            prev_quarter = quarter - 1

        result = await self.db.execute(
            select(VatSettlement).where(
                VatSettlement.tenant_id == tenant_id,
                VatSettlement.year == prev_year,
                VatSettlement.quarter == prev_quarter,
            )
        )
        prev_settlement = result.scalar_one_or_none()
        if not prev_settlement:
            return 0.0

        # If previous saldo was negative (credit), carry forward the absolute value
        if prev_settlement.saldo < 0:
            return round(abs(prev_settlement.saldo), 2)

        return 0.0

    async def _count_unregistered(
        self, tenant_id: uuid.UUID, start: date, end: date,
    ) -> int:
        """Count invoices in the period that are not yet registered (pending/error)."""
        result = await self.db.execute(
            select(func.count()).select_from(Invoice).where(
                Invoice.tenant_id == tenant_id,
                Invoice.data_fattura >= start,
                Invoice.data_fattura <= end,
                Invoice.processing_status.in_(["pending", "error"]),
            )
        )
        return result.scalar() or 0

    async def _save_settlement(
        self,
        tenant_id: uuid.UUID,
        year: int,
        quarter: int,
        iva_vendite: float,
        iva_acquisti: float,
        iva_rc_debito: float,
        iva_rc_credito: float,
        credito_precedente: float,
        interessi: float,
        saldo: float,
        unregistered_count: int,
    ) -> VatSettlement:
        """Save or update VAT settlement record."""
        result = await self.db.execute(
            select(VatSettlement).where(
                VatSettlement.tenant_id == tenant_id,
                VatSettlement.year == year,
                VatSettlement.quarter == quarter,
            )
        )
        settlement = result.scalar_one_or_none()

        if settlement:
            # Update existing
            settlement.iva_vendite = iva_vendite
            settlement.iva_acquisti = iva_acquisti
            settlement.iva_reverse_charge_debito = iva_rc_debito
            settlement.iva_reverse_charge_credito = iva_rc_credito
            settlement.credito_periodo_precedente = credito_precedente
            settlement.interessi = interessi
            settlement.saldo = saldo
            settlement.unregistered_count = unregistered_count
            settlement.computed_at = datetime.now(UTC).replace(tzinfo=None)
        else:
            settlement = VatSettlement(
                tenant_id=tenant_id,
                year=year,
                quarter=quarter,
                iva_vendite=iva_vendite,
                iva_acquisti=iva_acquisti,
                iva_reverse_charge_debito=iva_rc_debito,
                iva_reverse_charge_credito=iva_rc_credito,
                credito_periodo_precedente=credito_precedente,
                interessi=interessi,
                saldo=saldo,
                unregistered_count=unregistered_count,
            )
            self.db.add(settlement)

        await self.db.flush()
        return settlement
