"""Service for payroll/personnel costs (US-44)."""

import logging
import uuid
from datetime import date
from math import ceil

from sqlalchemy import select, func, and_, extract
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import PayrollCost

logger = logging.getLogger(__name__)


class PayrollService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, tenant_id: uuid.UUID, data: dict) -> dict:
        """Create a payroll cost entry."""
        entry = PayrollCost(tenant_id=tenant_id, **data)
        self.db.add(entry)
        await self.db.flush()
        return self._to_dict(entry)

    async def list_costs(
        self,
        tenant_id: uuid.UUID,
        year: int | None = None,
        month: int | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict:
        """List payroll costs with optional filters."""
        conditions = [PayrollCost.tenant_id == tenant_id]
        if year:
            conditions.append(extract("year", PayrollCost.mese) == year)
        if month:
            conditions.append(extract("month", PayrollCost.mese) == month)

        count_q = select(func.count(PayrollCost.id)).where(and_(*conditions))
        total = (await self.db.execute(count_q)).scalar() or 0

        offset = (page - 1) * page_size
        q = (
            select(PayrollCost)
            .where(and_(*conditions))
            .order_by(PayrollCost.mese.desc(), PayrollCost.dipendente_nome)
            .offset(offset)
            .limit(page_size)
        )
        result = await self.db.execute(q)
        items = [self._to_dict(r) for r in result.scalars().all()]

        return {"items": items, "total": total, "page": page, "pages": ceil(total / page_size) if page_size > 0 else 0}

    async def get_summary(self, tenant_id: uuid.UUID, year: int) -> dict:
        """Get yearly payroll summary with monthly breakdown."""
        conditions = [
            PayrollCost.tenant_id == tenant_id,
            extract("year", PayrollCost.mese) == year,
        ]

        # Monthly aggregation
        q = (
            select(
                PayrollCost.mese,
                func.count(PayrollCost.id).label("num"),
                func.coalesce(func.sum(PayrollCost.importo_lordo), 0).label("lordo"),
                func.coalesce(func.sum(PayrollCost.importo_netto), 0).label("netto"),
                func.coalesce(func.sum(PayrollCost.contributi_inps), 0).label("contributi"),
                func.coalesce(func.sum(PayrollCost.costo_totale_azienda), 0).label("costo"),
            )
            .where(and_(*conditions))
            .group_by(PayrollCost.mese)
            .order_by(PayrollCost.mese)
        )
        result = await self.db.execute(q)

        monthly = []
        total_costo = 0.0
        total_lordo = 0.0
        all_dipendenti = set()

        for row in result.fetchall():
            m = {
                "mese": row[0],
                "num_dipendenti": int(row[1]),
                "totale_lordo": round(float(row[2]), 2),
                "totale_netto": round(float(row[3]), 2),
                "totale_contributi": round(float(row[4]), 2),
                "totale_costo_azienda": round(float(row[5]), 2),
            }
            monthly.append(m)
            total_costo += m["totale_costo_azienda"]
            total_lordo += m["totale_lordo"]

        # Count unique employees
        emp_q = (
            select(func.count(func.distinct(PayrollCost.dipendente_nome)))
            .where(and_(*conditions))
        )
        num_dip = (await self.db.execute(emp_q)).scalar() or 0

        return {
            "year": year,
            "total_costo_azienda": round(total_costo, 2),
            "total_lordo": round(total_lordo, 2),
            "num_dipendenti": num_dip,
            "monthly": monthly,
        }

    async def delete(self, tenant_id: uuid.UUID, cost_id: uuid.UUID) -> dict:
        """Delete a payroll cost entry."""
        result = await self.db.execute(
            select(PayrollCost).where(PayrollCost.id == cost_id, PayrollCost.tenant_id == tenant_id)
        )
        entry = result.scalar_one_or_none()
        if not entry:
            raise ValueError("Voce costo personale non trovata")
        await self.db.delete(entry)
        await self.db.flush()
        return {"id": str(cost_id), "deleted": True}

    def _to_dict(self, entry: PayrollCost) -> dict:
        return {
            "id": entry.id,
            "tenant_id": entry.tenant_id,
            "mese": entry.mese,
            "dipendente_nome": entry.dipendente_nome,
            "dipendente_cf": entry.dipendente_cf,
            "importo_lordo": entry.importo_lordo,
            "importo_netto": entry.importo_netto,
            "contributi_inps": entry.contributi_inps,
            "irpef": entry.irpef,
            "tfr": entry.tfr,
            "costo_totale_azienda": entry.costo_totale_azienda,
            "note": entry.note,
            "created_at": entry.created_at,
        }
