"""Recurring contracts service (US-55, US-56).

Import from PDF via LLM + full CRUD.
"""

import logging
import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import RecurringContract

logger = logging.getLogger(__name__)


class RecurringContractService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def import_pdf(
        self,
        tenant_id: uuid.UUID,
        filename: str,
        pdf_content: bytes,
    ) -> dict:
        """Import recurring contracts from PDF via LLM (US-55)."""
        # Mock LLM extraction
        extracted = _mock_extract_contracts(pdf_content)

        contracts = []
        for item in extracted:
            c = RecurringContract(
                tenant_id=tenant_id,
                description=item["description"],
                counterpart=item.get("counterpart"),
                amount=item["amount"],
                frequency=item.get("frequency", "monthly"),
                start_date=date.fromisoformat(item["start_date"]),
                end_date=date.fromisoformat(item["end_date"]) if item.get("end_date") else None,
                next_due_date=date.fromisoformat(item["start_date"]),
                category=item.get("category"),
                source="pdf_import",
                status="active",
            )
            self.db.add(c)
            contracts.append(c)

        await self.db.flush()

        return {
            "filename": filename,
            "contracts_count": len(contracts),
            "contracts": [
                {
                    "id": str(c.id),
                    "description": c.description,
                    "amount": c.amount,
                    "frequency": c.frequency,
                    "start_date": c.start_date.isoformat(),
                }
                for c in contracts
            ],
            "message": f"Importati {len(contracts)} contratti ricorrenti da PDF",
        }

    async def create(self, tenant_id: uuid.UUID, data: dict) -> dict:
        """Create a recurring contract (US-56)."""
        c = RecurringContract(
            tenant_id=tenant_id,
            description=data["description"],
            counterpart=data.get("counterpart"),
            amount=data["amount"],
            frequency=data.get("frequency", "monthly"),
            start_date=date.fromisoformat(data["start_date"]),
            end_date=date.fromisoformat(data["end_date"]) if data.get("end_date") else None,
            next_due_date=date.fromisoformat(data["start_date"]),
            category=data.get("category"),
            source="manual",
            status="active",
        )
        self.db.add(c)
        await self.db.flush()
        return self._to_dict(c)

    async def get_all(self, tenant_id: uuid.UUID) -> dict:
        """Get all recurring contracts."""
        result = await self.db.execute(
            select(RecurringContract).where(RecurringContract.tenant_id == tenant_id)
        )
        contracts = result.scalars().all()
        return {
            "contracts": [self._to_dict(c) for c in contracts],
            "total": len(contracts),
        }

    async def update(self, contract_id: uuid.UUID, tenant_id: uuid.UUID, data: dict) -> dict:
        """Update a recurring contract (US-56)."""
        result = await self.db.execute(
            select(RecurringContract).where(
                RecurringContract.id == contract_id,
                RecurringContract.tenant_id == tenant_id,
            )
        )
        c = result.scalar_one_or_none()
        if not c:
            raise ValueError("Contratto non trovato")

        for key in ("description", "counterpart", "amount", "frequency", "category", "status"):
            if key in data:
                setattr(c, key, data[key])
        for date_key in ("start_date", "end_date", "next_due_date"):
            if date_key in data:
                setattr(c, date_key, date.fromisoformat(data[date_key]) if data[date_key] else None)

        await self.db.flush()
        return self._to_dict(c)

    async def delete(self, contract_id: uuid.UUID, tenant_id: uuid.UUID) -> dict:
        """Delete a recurring contract (US-56)."""
        result = await self.db.execute(
            select(RecurringContract).where(
                RecurringContract.id == contract_id,
                RecurringContract.tenant_id == tenant_id,
            )
        )
        c = result.scalar_one_or_none()
        if not c:
            raise ValueError("Contratto non trovato")

        await self.db.delete(c)
        await self.db.flush()
        return {"deleted": True, "id": str(contract_id)}

    def _to_dict(self, c: RecurringContract) -> dict:
        return {
            "id": str(c.id),
            "description": c.description,
            "counterpart": c.counterpart,
            "amount": c.amount,
            "frequency": c.frequency,
            "start_date": c.start_date.isoformat(),
            "end_date": c.end_date.isoformat() if c.end_date else None,
            "next_due_date": c.next_due_date.isoformat() if c.next_due_date else None,
            "category": c.category,
            "status": c.status,
        }


def _mock_extract_contracts(pdf_content: bytes) -> list:
    """Mock LLM extraction of contracts from PDF."""
    return [
        {
            "description": "Canone hosting server",
            "counterpart": "CloudProvider SRL",
            "amount": 150.00,
            "frequency": "monthly",
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "category": "hosting",
        },
        {
            "description": "Licenza software gestionale",
            "counterpart": "SoftCo SpA",
            "amount": 1200.00,
            "frequency": "annual",
            "start_date": "2026-01-01",
            "category": "software",
        },
    ]
