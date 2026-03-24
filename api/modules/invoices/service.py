"""Service layer for invoices module."""

import logging
import uuid
from datetime import date, datetime, UTC
from difflib import SequenceMatcher
from math import ceil

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.adapters.fiscoapi import FiscoAPIClient
from api.adapters.odoo import PIANO_CONTI_SRL_ORDINARIO
from api.agents.fisco_agent import FiscoAgent
from api.agents.learning_agent import LearningAgent
from api.db.models import Invoice, User

logger = logging.getLogger(__name__)


class InvoiceService:
    """Service for invoice operations."""

    def __init__(self, db: AsyncSession, fiscoapi: FiscoAPIClient | None = None) -> None:
        self.db = db
        self.fiscoapi = fiscoapi or FiscoAPIClient()

    async def sync_cassetto(self, user: User, force: bool = False, from_date: date | None = None) -> dict:
        """Sync invoices from cassetto fiscale.

        Delegates to FiscoAgent for actual sync logic.
        """
        if not user.tenant_id:
            raise ValueError("Profilo azienda non configurato. Completa il profilo prima.")

        agent = FiscoAgent(self.db, fiscoapi=self.fiscoapi)
        return await agent.sync_cassetto(user, user.tenant_id, force=force, from_date=from_date)

    async def get_invoices(
        self,
        tenant_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
        date_from: date | None = None,
        date_to: date | None = None,
        type_filter: str | None = None,
        source: str | None = None,
        status: str | None = None,
        emittente: str | None = None,
    ) -> dict:
        """Get paginated list of invoices with filters."""
        conditions = [Invoice.tenant_id == tenant_id]

        if date_from:
            conditions.append(Invoice.data_fattura >= date_from)
        if date_to:
            conditions.append(Invoice.data_fattura <= date_to)
        if type_filter:
            conditions.append(Invoice.type == type_filter)
        if source:
            conditions.append(Invoice.source == source)
        if status:
            conditions.append(Invoice.processing_status == status)
        if emittente:
            conditions.append(
                Invoice.emittente_nome.ilike(f"%{emittente}%")
            )

        # Count total
        count_query = select(func.count(Invoice.id)).where(and_(*conditions))
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Fetch page
        offset = (page - 1) * page_size
        query = (
            select(Invoice)
            .where(and_(*conditions))
            .order_by(Invoice.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self.db.execute(query)
        invoices = result.scalars().all()

        pages = ceil(total / page_size) if page_size > 0 else 0

        return {
            "items": invoices,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages,
        }

    async def get_invoice(self, tenant_id: uuid.UUID, invoice_id: uuid.UUID) -> Invoice:
        """Get a single invoice by ID."""
        result = await self.db.execute(
            select(Invoice).where(
                and_(
                    Invoice.id == invoice_id,
                    Invoice.tenant_id == tenant_id,
                )
            )
        )
        invoice = result.scalar_one_or_none()
        if not invoice:
            raise ValueError("Fattura non trovata")
        return invoice

    async def verify_invoice(
        self,
        tenant_id: uuid.UUID,
        invoice_id: uuid.UUID,
        category: str,
        confirmed: bool,
    ) -> dict:
        """Verify or correct an invoice category.

        If confirmed=True, the existing category is confirmed.
        If confirmed=False (or category differs), it's a correction.
        """
        result = await self.db.execute(
            select(Invoice).where(
                and_(
                    Invoice.id == invoice_id,
                    Invoice.tenant_id == tenant_id,
                )
            )
        )
        invoice = result.scalar_one_or_none()
        if not invoice:
            raise ValueError("Fattura non trovata")

        suggested_category = invoice.category
        was_correct = confirmed and (suggested_category == category)

        # Record feedback via LearningAgent
        agent = LearningAgent(self.db)
        await agent.record_feedback(
            invoice_id=invoice_id,
            tenant_id=tenant_id,
            suggested_category=suggested_category,
            final_category=category,
        )

        # Update invoice
        invoice.category = category
        invoice.verified = True
        invoice.category_confidence = 1.0
        invoice.updated_at = datetime.now(UTC).replace(tzinfo=None)
        await self.db.flush()

        if was_correct:
            message = "Categoria confermata con successo"
        else:
            message = f"Categoria aggiornata da '{suggested_category}' a '{category}'"

        return {
            "invoice_id": invoice_id,
            "category": category,
            "verified": True,
            "was_correct": was_correct,
            "message": message,
        }

    async def get_pending_review(
        self,
        tenant_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """Get invoices that are categorized but not yet verified."""
        conditions = [
            Invoice.tenant_id == tenant_id,
            Invoice.processing_status == "categorized",
            Invoice.verified == False,  # noqa: E712
            Invoice.category.isnot(None),
        ]

        # Count total
        count_query = select(func.count(Invoice.id)).where(and_(*conditions))
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Fetch page
        offset = (page - 1) * page_size
        query = (
            select(Invoice)
            .where(and_(*conditions))
            .order_by(Invoice.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self.db.execute(query)
        invoices = result.scalars().all()

        pages = ceil(total / page_size) if page_size > 0 else 0

        return {
            "items": invoices,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages,
        }

    def suggest_similar_categories(self, category: str) -> list[str]:
        """Suggest similar categories from the piano conti when category is not found."""
        all_categories = [acc.name for acc in PIANO_CONTI_SRL_ORDINARIO if acc.account_type == "expense"]
        scored = []
        for cat in all_categories:
            ratio = SequenceMatcher(None, category.lower(), cat.lower()).ratio()
            scored.append((cat, ratio))
        scored.sort(key=lambda x: x[1], reverse=True)
        return [cat for cat, _ in scored[:3]]

    async def get_sync_status(self, user: User) -> dict:
        """Get sync status information."""
        if not user.tenant_id:
            return {
                "connected": False,
                "token_valid": False,
                "last_sync_at": None,
                "invoices_count": 0,
                "message": "Profilo azienda non configurato",
            }

        # Check SPID connection
        connected = bool(user.spid_token)
        token_valid = connected and (
            not user.spid_token_expires_at
            or user.spid_token_expires_at > datetime.now(UTC).replace(tzinfo=None)
        )

        # Count invoices
        count_result = await self.db.execute(
            select(func.count(Invoice.id)).where(
                Invoice.tenant_id == user.tenant_id
            )
        )
        invoices_count = count_result.scalar() or 0

        # Last sync timestamp
        last_sync_result = await self.db.execute(
            select(Invoice.created_at)
            .where(
                and_(
                    Invoice.tenant_id == user.tenant_id,
                    Invoice.source == "cassetto_fiscale",
                )
            )
            .order_by(Invoice.created_at.desc())
            .limit(1)
        )
        last_sync_at = last_sync_result.scalar_one_or_none()

        if not connected:
            message = "Cassetto fiscale non collegato. Autentica con SPID."
        elif not token_valid:
            message = "Sessione SPID scaduta. Riautentica."
        else:
            message = "Cassetto fiscale collegato e attivo"

        return {
            "connected": connected,
            "token_valid": token_valid,
            "last_sync_at": last_sync_at,
            "invoices_count": invoices_count,
            "message": message,
        }
