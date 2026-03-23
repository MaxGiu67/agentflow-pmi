"""Accruals and deferrals service (Ratei e Risconti) (US-36)."""

import logging
import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import Accrual, Invoice

logger = logging.getLogger(__name__)


class AccrualsService:
    """Business logic for accruals and deferrals (ratei e risconti)."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def propose_accrual(
        self,
        tenant_id: uuid.UUID,
        invoice_id: uuid.UUID | None = None,
        description: str | None = None,
        total_amount: float | None = None,
        period_start: date | None = None,
        period_end: date | None = None,
        accrual_type: str | None = None,
        fiscal_year: int | None = None,
    ) -> dict:
        """AC-36.1: Identify multi-year costs -> propose deferral.
        AC-36.3: Non-apportionable amount -> request competence period.
        AC-36.4: Passive accrual (cost incurred, not invoiced).

        Returns proposed accrual with amounts calculated.
        """
        # If linked to invoice, load from DB
        if invoice_id:
            result = await self.db.execute(
                select(Invoice).where(
                    Invoice.id == invoice_id,
                    Invoice.tenant_id == tenant_id,
                )
            )
            invoice = result.scalar_one_or_none()
            if not invoice:
                raise ValueError("Fattura non trovata")

            if not total_amount:
                total_amount = invoice.importo_netto or 0.0
            if not description:
                description = f"Risconto fattura {invoice.numero_fattura}"

        if not total_amount or not description:
            raise ValueError("Importo e descrizione obbligatori")

        # AC-36.3: Check if period is provided
        if not period_start or not period_end:
            return {
                "status": "needs_period",
                "message": (
                    "Importo non ripartibile automaticamente. "
                    "Indicare il periodo di competenza (data inizio e fine)."
                ),
                "description": description,
                "total_amount": total_amount,
            }

        if not fiscal_year:
            fiscal_year = period_start.year

        # Determine accrual type
        if not accrual_type:
            accrual_type = self._determine_type(period_start, period_end, fiscal_year)

        # Calculate amounts
        year_end = date(fiscal_year, 12, 31)
        year_start = date(fiscal_year, 1, 1)

        total_days = (period_end - period_start).days + 1
        if total_days <= 0:
            raise ValueError("Periodo non valido: data fine deve essere dopo data inizio")

        if accrual_type in ("risconto_attivo", "risconto_passivo"):
            # Risconto: cost paid, part belongs to next year
            # Current year portion: from period_start (or year_start) to year_end
            current_start = max(period_start, year_start)
            current_end = min(period_end, year_end)
            current_days = (current_end - current_start).days + 1
            if current_days < 0:
                current_days = 0

            current_year_amount = round(total_amount * (current_days / total_days), 2)
            deferred_amount = round(total_amount - current_year_amount, 2)

        elif accrual_type in ("rateo_attivo", "rateo_passivo"):
            # Rateo: cost incurred but not yet invoiced
            # Current year portion: from period_start to year_end
            current_start = max(period_start, year_start)
            current_end = min(period_end, year_end)
            current_days = (current_end - current_start).days + 1
            if current_days < 0:
                current_days = 0

            current_year_amount = round(total_amount * (current_days / total_days), 2)
            deferred_amount = round(total_amount - current_year_amount, 2)
        else:
            raise ValueError(f"Tipo rateo/risconto '{accrual_type}' non valido")

        # Create accrual record
        accrual = Accrual(
            tenant_id=tenant_id,
            invoice_id=invoice_id,
            type=accrual_type,
            description=description,
            total_amount=total_amount,
            current_year_amount=current_year_amount,
            deferred_amount=deferred_amount,
            period_start=period_start,
            period_end=period_end,
            fiscal_year=fiscal_year,
            status="proposed",
        )
        self.db.add(accrual)
        await self.db.flush()

        return self._accrual_to_dict(accrual)

    async def list_accruals(
        self,
        tenant_id: uuid.UUID,
        fiscal_year: int | None = None,
    ) -> dict:
        """List accruals for a tenant, optionally filtered by fiscal year."""
        query = select(Accrual).where(Accrual.tenant_id == tenant_id)
        if fiscal_year:
            query = query.where(Accrual.fiscal_year == fiscal_year)
        query = query.order_by(Accrual.created_at.desc())

        result = await self.db.execute(query)
        items = result.scalars().all()
        return {
            "items": [self._accrual_to_dict(a) for a in items],
            "total": len(items),
        }

    async def confirm_accrual(
        self,
        accrual_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> dict:
        """AC-36.2: Confirm accrual -> generate adjustment entries.

        Creates:
        - 31/12 adjustment entry (scrittura di assestamento)
        - 01/01 reversal entry (riapertura)
        """
        result = await self.db.execute(
            select(Accrual).where(
                Accrual.id == accrual_id,
                Accrual.tenant_id == tenant_id,
            )
        )
        accrual = result.scalar_one_or_none()
        if not accrual:
            raise ValueError("Rateo/risconto non trovato")

        if accrual.status == "confirmed":
            raise ValueError("Rateo/risconto gia' confermato")

        accrual.status = "confirmed"

        # AC-36.2: Build adjustment entries
        adjustment_entry = self._build_adjustment_entry(accrual)
        reversal_entry = self._build_reversal_entry(accrual)

        await self.db.flush()

        result_dict = self._accrual_to_dict(accrual)
        result_dict["adjustment_entry"] = adjustment_entry
        result_dict["reversal_entry"] = reversal_entry
        return result_dict

    def _determine_type(
        self, period_start: date, period_end: date, fiscal_year: int,
    ) -> str:
        """Determine accrual type based on dates."""
        year_end = date(fiscal_year, 12, 31)

        if period_end > year_end and period_start <= year_end:
            # Cost spans beyond year end, paid this year
            return "risconto_attivo"
        elif period_start <= year_end and period_end <= year_end:
            # Cost entirely within current year but invoiced later
            return "rateo_passivo"
        else:
            return "risconto_attivo"

    def _build_adjustment_entry(self, accrual: Accrual) -> dict:
        """AC-36.2: Build 31/12 adjustment entry."""
        year_end = date(accrual.fiscal_year, 12, 31)

        if accrual.type == "risconto_attivo":
            return {
                "description": f"Risconto attivo 31/12/{accrual.fiscal_year}: {accrual.description}",
                "entry_date": year_end.isoformat(),
                "lines": [
                    {
                        "account_code": "1060",
                        "account_name": "Risconti attivi",
                        "debit": accrual.deferred_amount,
                        "credit": 0.0,
                    },
                    {
                        "account_code": "6100",
                        "account_name": "Costi per servizi",
                        "debit": 0.0,
                        "credit": accrual.deferred_amount,
                    },
                ],
            }
        elif accrual.type == "rateo_passivo":
            return {
                "description": f"Rateo passivo 31/12/{accrual.fiscal_year}: {accrual.description}",
                "entry_date": year_end.isoformat(),
                "lines": [
                    {
                        "account_code": "6100",
                        "account_name": "Costi per servizi",
                        "debit": accrual.current_year_amount,
                        "credit": 0.0,
                    },
                    {
                        "account_code": "2060",
                        "account_name": "Ratei passivi",
                        "debit": 0.0,
                        "credit": accrual.current_year_amount,
                    },
                ],
            }
        else:
            return {
                "description": f"Assestamento 31/12/{accrual.fiscal_year}: {accrual.description}",
                "entry_date": year_end.isoformat(),
                "lines": [],
            }

    def _build_reversal_entry(self, accrual: Accrual) -> dict:
        """AC-36.2: Build 01/01 reversal entry."""
        next_year_start = date(accrual.fiscal_year + 1, 1, 1)

        if accrual.type == "risconto_attivo":
            return {
                "description": (
                    f"Riapertura risconto attivo 01/01/{accrual.fiscal_year + 1}: "
                    f"{accrual.description}"
                ),
                "entry_date": next_year_start.isoformat(),
                "lines": [
                    {
                        "account_code": "6100",
                        "account_name": "Costi per servizi",
                        "debit": accrual.deferred_amount,
                        "credit": 0.0,
                    },
                    {
                        "account_code": "1060",
                        "account_name": "Risconti attivi",
                        "debit": 0.0,
                        "credit": accrual.deferred_amount,
                    },
                ],
            }
        elif accrual.type == "rateo_passivo":
            return {
                "description": (
                    f"Riapertura rateo passivo 01/01/{accrual.fiscal_year + 1}: "
                    f"{accrual.description}"
                ),
                "entry_date": next_year_start.isoformat(),
                "lines": [
                    {
                        "account_code": "2060",
                        "account_name": "Ratei passivi",
                        "debit": accrual.current_year_amount,
                        "credit": 0.0,
                    },
                    {
                        "account_code": "6100",
                        "account_name": "Costi per servizi",
                        "debit": 0.0,
                        "credit": accrual.current_year_amount,
                    },
                ],
            }
        else:
            return {
                "description": (
                    f"Riapertura 01/01/{accrual.fiscal_year + 1}: {accrual.description}"
                ),
                "entry_date": next_year_start.isoformat(),
                "lines": [],
            }

    @staticmethod
    def _accrual_to_dict(accrual: Accrual) -> dict:
        """Convert accrual model to dict."""
        return {
            "id": str(accrual.id),
            "tenant_id": str(accrual.tenant_id),
            "invoice_id": str(accrual.invoice_id) if accrual.invoice_id else None,
            "type": accrual.type,
            "description": accrual.description,
            "total_amount": accrual.total_amount,
            "current_year_amount": accrual.current_year_amount,
            "deferred_amount": accrual.deferred_amount,
            "period_start": accrual.period_start.isoformat(),
            "period_end": accrual.period_end.isoformat(),
            "fiscal_year": accrual.fiscal_year,
            "status": accrual.status,
        }
