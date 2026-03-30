"""Batch contabilizzazione fatture (register journal entries for parsed invoices).

Scorre tutte le fatture in status 'parsed' o 'categorized' che NON hanno
ancora una scrittura contabile, e le registra tramite ContaAgent.

Idempotenza garantita: il ContaAgent verifica che non esista gia una scrittura
per la stessa fattura (check su JournalEntry.invoice_id).
"""

import logging
import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.agents.conta_agent import ContaAgent, ACCOUNT_MAPPINGS
from api.db.models import Invoice, JournalEntry

logger = logging.getLogger(__name__)

# Default account for uncategorized invoices
DEFAULT_EXPENSE_CODE = "5060"
DEFAULT_EXPENSE_NAME = "Oneri diversi di gestione"
DEFAULT_REVENUE_CODE = "4010"
DEFAULT_REVENUE_NAME = "Ricavi vendite e prestazioni"


class BatchRegisterService:
    """Servizio per contabilizzazione batch delle fatture importate."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def register_all_pending(self, tenant_id: uuid.UUID) -> dict:
        """Contabilizza tutte le fatture parsed/categorized non ancora registrate.

        Per ogni fattura:
        1. Verifica che non abbia gia una scrittura (idempotenza)
        2. Se non ha categoria, assegna un default
        3. Chiama ContaAgent.register_entry()

        Returns:
            dict con contatori: registered, already_done, errors, skipped
        """
        # Find invoices that don't have a journal entry yet
        # Subquery: invoice_ids that already have journal entries
        registered_ids = (
            select(JournalEntry.invoice_id)
            .where(
                JournalEntry.tenant_id == tenant_id,
                JournalEntry.invoice_id.isnot(None),
                JournalEntry.status.in_(["draft", "posted"]),
            )
        )

        # Invoices parsed/categorized without journal entry
        result = await self.db.execute(
            select(Invoice).where(
                Invoice.tenant_id == tenant_id,
                Invoice.processing_status.in_(["parsed", "categorized", "verified"]),
                Invoice.id.not_in(registered_ids),
            ).order_by(Invoice.data_fattura.desc())
        )
        invoices = result.scalars().all()

        if not invoices:
            return {
                "registered": 0,
                "already_done": 0,
                "errors": 0,
                "skipped": 0,
                "total_invoices": 0,
                "message": "Nessuna fattura da contabilizzare",
            }

        agent = ContaAgent(self.db)
        registered = 0
        already_done = 0
        errors = 0
        skipped = 0
        error_details = []

        for invoice in invoices:
            # Assign default category if missing
            if not invoice.category:
                if invoice.type == "attiva":
                    invoice.category = "Ricavi vendite"
                else:
                    invoice.category = "Oneri diversi di gestione"
                await self.db.flush()

            # Ensure the category has an account mapping
            if invoice.category not in ACCOUNT_MAPPINGS:
                # Add it temporarily
                if invoice.type == "attiva":
                    ACCOUNT_MAPPINGS[invoice.category] = (DEFAULT_REVENUE_CODE, DEFAULT_REVENUE_NAME)
                else:
                    ACCOUNT_MAPPINGS[invoice.category] = (DEFAULT_EXPENSE_CODE, DEFAULT_EXPENSE_NAME)

            try:
                result = await agent.register_entry(invoice.id, tenant_id)
                status = result.get("status", "")

                if status == "posted":
                    registered += 1
                    invoice.processing_status = "registered"
                elif status == "already_registered":
                    already_done += 1
                elif status == "error":
                    errors += 1
                    error_details.append({
                        "invoice_id": str(invoice.id),
                        "numero": invoice.numero_fattura,
                        "error": result.get("message", "Unknown error"),
                    })
                else:
                    skipped += 1
            except Exception as e:
                errors += 1
                error_details.append({
                    "invoice_id": str(invoice.id),
                    "numero": invoice.numero_fattura,
                    "error": str(e),
                })
                logger.error("Errore contabilizzazione fattura %s: %s", invoice.numero_fattura, e)

        await self.db.flush()

        return {
            "registered": registered,
            "already_done": already_done,
            "errors": errors,
            "skipped": skipped,
            "total_invoices": len(invoices),
            "error_details": error_details[:10],
            "message": f"Contabilizzate {registered} fatture su {len(invoices)} ({errors} errori)",
        }

    async def get_pending_count(self, tenant_id: uuid.UUID) -> dict:
        """Conta quante fatture sono in attesa di contabilizzazione."""
        registered_ids = (
            select(JournalEntry.invoice_id)
            .where(
                JournalEntry.tenant_id == tenant_id,
                JournalEntry.invoice_id.isnot(None),
                JournalEntry.status.in_(["draft", "posted"]),
            )
        )

        total = await self.db.scalar(
            select(func.count(Invoice.id)).where(
                Invoice.tenant_id == tenant_id,
                Invoice.processing_status.in_(["parsed", "categorized", "verified"]),
                Invoice.id.not_in(registered_ids),
            )
        ) or 0

        return {
            "pending": total,
            "message": f"{total} fatture in attesa di contabilizzazione" if total > 0 else "Tutte le fatture sono contabilizzate",
        }
