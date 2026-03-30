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

        Requires active SPID session. Returns error if not connected.
        """
        if not user.tenant_id:
            raise ValueError("Profilo azienda non configurato. Completa il profilo prima.")

        # Check if user has active SPID connection
        if not user.spid_token:
            raise ValueError("Cassetto fiscale non collegato. Collega SPID dalle Impostazioni.")

        # Try real FiscoAPI sync
        from api.config import settings
        if settings.fiscoapi_secret_key:
            try:
                from api.adapters.fiscoapi_real import FiscoAPIReal
                real_api = FiscoAPIReal()

                # Extract session ID if stored
                session_id = ""
                if user.spid_token and user.spid_token.startswith("fiscoapi_session:"):
                    session_id = user.spid_token.replace("fiscoapi_session:", "")

                if not session_id:
                    raise ValueError("Sessione SPID non attiva. Ricollega SPID dalle Impostazioni.")

                # Check session status
                status = await real_api.get_session_status(session_id)
                session_data = status.get("sessione", status)
                stato = session_data.get("stato", "")

                if stato != "sessione_attiva":
                    raise ValueError(
                        f"Sessione SPID in stato '{stato}'. "
                        "Completa l'autenticazione SPID dalle Impostazioni."
                    )

                # Session active — request invoices
                piva = None
                if user.tenant_id:
                    from sqlalchemy import select as sel
                    from api.db.models import Tenant
                    result = await self.db.execute(sel(Tenant).where(Tenant.id == user.tenant_id))
                    tenant = result.scalar_one_or_none()
                    if tenant:
                        piva = tenant.piva

                if not piva:
                    raise ValueError("P.IVA non configurata nel profilo azienda.")

                invoices_data = await real_api.request_invoices(
                    utente_lavoro=piva,
                    tipo="ricevute",
                )

                # Process response
                fatture = invoices_data.get("fatture", [])
                if not fatture and invoices_data.get("stato") == "in_corso":
                    return {
                        "downloaded": 0,
                        "new": 0,
                        "duplicates": 0,
                        "errors": 0,
                        "message": "Richiesta fatture in corso. Riprova tra qualche secondo.",
                    }

                # Save invoices to DB
                new_count = 0
                dup_count = 0
                for f in fatture:
                    # Dedup check
                    existing = await self.db.execute(
                        select(Invoice).where(
                            and_(
                                Invoice.tenant_id == user.tenant_id,
                                Invoice.numero_fattura == f.get("numeroFattura", ""),
                                Invoice.emittente_piva == f.get("pivaEmittente", ""),
                            )
                        )
                    )
                    if existing.scalar_one_or_none():
                        dup_count += 1
                        continue

                    invoice = Invoice(
                        tenant_id=user.tenant_id,
                        type="passiva",
                        document_type=f.get("tipoDocumento", "TD01"),
                        source="cassetto_fiscale",
                        numero_fattura=f.get("numeroFattura", ""),
                        emittente_piva=f.get("pivaEmittente", ""),
                        emittente_nome=f.get("denominazioneEmittente", ""),
                        data_fattura=date.fromisoformat(f["dataFattura"]) if f.get("dataFattura") else None,
                        importo_netto=f.get("imponibile"),
                        importo_iva=f.get("imposta"),
                        importo_totale=(f.get("imponibile", 0) or 0) + (f.get("imposta", 0) or 0),
                        processing_status="pending",
                    )
                    self.db.add(invoice)
                    new_count += 1

                await self.db.flush()

                return {
                    "downloaded": len(fatture),
                    "new": new_count,
                    "duplicates": dup_count,
                    "errors": 0,
                    "message": f"Sync completato: {new_count} nuove fatture scaricate dal cassetto fiscale.",
                }

            except ValueError:
                raise
            except Exception as e:
                logger.error("FiscoAPI real sync failed: %s", e)
                raise ValueError(f"Errore sync cassetto fiscale: {e}") from e

        raise ValueError("FiscoAPI non configurato. Contatta il supporto.")

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
            from sqlalchemy import or_, cast, String
            search_term = f"%{emittente}%"
            conditions.append(
                or_(
                    Invoice.emittente_nome.ilike(search_term),
                    Invoice.numero_fattura.ilike(search_term),
                    cast(Invoice.structured_data["destinatario_nome"], String).ilike(search_term),
                )
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
