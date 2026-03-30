"""Loans/financing service (US-57, US-58).

Import from PDF via LLM + full CRUD.
"""

import logging
import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import Loan

logger = logging.getLogger(__name__)


class LoanService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def import_pdf(
        self,
        tenant_id: uuid.UUID,
        filename: str,
        pdf_content: bytes,
    ) -> dict:
        """Import loans from PDF via LLM (US-57)."""
        extracted = _mock_extract_loans(pdf_content)

        loans = []
        for item in extracted:
            loan = Loan(
                tenant_id=tenant_id,
                description=item["description"],
                lender=item.get("lender"),
                principal=item["principal"],
                interest_rate=item["interest_rate"],
                installment_amount=item["installment_amount"],
                frequency=item.get("frequency", "monthly"),
                start_date=date.fromisoformat(item["start_date"]),
                end_date=date.fromisoformat(item["end_date"]) if item.get("end_date") else None,
                remaining_principal=item["principal"],
                next_payment_date=date.fromisoformat(item["start_date"]),
                source="pdf_import",
                status="active",
            )
            self.db.add(loan)
            loans.append(loan)

        await self.db.flush()

        return {
            "filename": filename,
            "loans_count": len(loans),
            "loans": [self._to_dict(ln) for ln in loans],
            "message": f"Importati {len(loans)} finanziamenti da PDF",
        }

    async def create(self, tenant_id: uuid.UUID, data: dict) -> dict:
        """Create a loan (US-58)."""
        loan = Loan(
            tenant_id=tenant_id,
            description=data["description"],
            lender=data.get("lender"),
            principal=data["principal"],
            interest_rate=data["interest_rate"],
            installment_amount=data["installment_amount"],
            frequency=data.get("frequency", "monthly"),
            start_date=date.fromisoformat(data["start_date"]),
            end_date=date.fromisoformat(data["end_date"]) if data.get("end_date") else None,
            remaining_principal=data["principal"],
            next_payment_date=date.fromisoformat(data["start_date"]),
            source="manual",
            status="active",
        )
        self.db.add(loan)
        await self.db.flush()
        return self._to_dict(loan)

    async def get_all(self, tenant_id: uuid.UUID) -> dict:
        """Get all loans."""
        result = await self.db.execute(
            select(Loan).where(Loan.tenant_id == tenant_id)
        )
        loans = result.scalars().all()
        return {
            "loans": [self._to_dict(ln) for ln in loans],
            "total": len(loans),
        }

    async def update(self, loan_id: uuid.UUID, tenant_id: uuid.UUID, data: dict) -> dict:
        """Update a loan (US-58)."""
        result = await self.db.execute(
            select(Loan).where(
                Loan.id == loan_id,
                Loan.tenant_id == tenant_id,
            )
        )
        loan = result.scalar_one_or_none()
        if not loan:
            raise ValueError("Finanziamento non trovato")

        for key in ("description", "lender", "principal", "interest_rate",
                     "installment_amount", "frequency", "remaining_principal", "status"):
            if key in data:
                setattr(loan, key, data[key])
        for date_key in ("start_date", "end_date", "next_payment_date"):
            if date_key in data:
                setattr(loan, date_key, date.fromisoformat(data[date_key]) if data[date_key] else None)

        await self.db.flush()
        return self._to_dict(loan)

    async def delete(self, loan_id: uuid.UUID, tenant_id: uuid.UUID) -> dict:
        """Delete a loan (US-58)."""
        result = await self.db.execute(
            select(Loan).where(
                Loan.id == loan_id,
                Loan.tenant_id == tenant_id,
            )
        )
        loan = result.scalar_one_or_none()
        if not loan:
            raise ValueError("Finanziamento non trovato")

        await self.db.delete(loan)
        await self.db.flush()
        return {"deleted": True, "id": str(loan_id)}

    def _to_dict(self, ln: Loan) -> dict:
        return {
            "id": str(ln.id),
            "description": ln.description,
            "lender": ln.lender,
            "principal": ln.principal,
            "interest_rate": ln.interest_rate,
            "installment_amount": ln.installment_amount,
            "frequency": ln.frequency,
            "start_date": ln.start_date.isoformat(),
            "end_date": ln.end_date.isoformat() if ln.end_date else None,
            "remaining_principal": ln.remaining_principal,
            "next_payment_date": ln.next_payment_date.isoformat() if ln.next_payment_date else None,
            "status": ln.status,
        }


def _mock_extract_loans(pdf_content: bytes) -> list:
    """Mock LLM extraction of loans from PDF."""
    return [
        {
            "description": "Mutuo sede operativa",
            "lender": "Banca Intesa",
            "principal": 100000.00,
            "interest_rate": 3.5,
            "installment_amount": 1500.00,
            "frequency": "monthly",
            "start_date": "2024-01-01",
            "end_date": "2034-01-01",
        },
    ]
