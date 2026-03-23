"""FiscoAgent: Syncs invoices from cassetto fiscale via FiscoAPI."""

import logging
import uuid
from datetime import date, datetime, timedelta, UTC

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from api.adapters.fiscoapi import FiscoAPIClient
from api.agents.base_agent import BaseAgent
from api.db.models import Invoice, User

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAYS_HOURS = [1, 2, 4]  # backoff: 1h, 2h, 4h


class FiscoAgent(BaseAgent):
    """Agent that syncs invoices from Agenzia delle Entrate cassetto fiscale."""

    agent_name = "fisco_agent"

    def __init__(self, db: AsyncSession, fiscoapi: FiscoAPIClient | None = None) -> None:
        super().__init__(db)
        self.fiscoapi = fiscoapi or FiscoAPIClient()

    async def sync_cassetto(
        self,
        user: User,
        tenant_id: uuid.UUID,
        force: bool = False,
        from_date: date | None = None,
    ) -> dict:
        """Sync invoices from cassetto fiscale.

        Args:
            user: The user initiating the sync (must have SPID token).
            tenant_id: The tenant to sync for.
            force: If True, force full resync ignoring last_sync.
            from_date: Override start date for sync.

        Returns:
            Dict with sync results: downloaded, new, duplicates, errors.
        """
        if not user.spid_token:
            raise ValueError("Cassetto fiscale non collegato. Autentica con SPID prima.")

        # Determine sync start date
        sync_from = from_date
        if not sync_from and not force:
            # Check last sync — look for the most recent invoice from cassetto
            result = await self.db.execute(
                select(Invoice.created_at)
                .where(
                    and_(
                        Invoice.tenant_id == tenant_id,
                        Invoice.source == "cassetto_fiscale",
                    )
                )
                .order_by(Invoice.created_at.desc())
                .limit(1)
            )
            last_invoice = result.scalar_one_or_none()
            if last_invoice:
                # Incremental sync from last sync date
                sync_from = last_invoice.date() if isinstance(last_invoice, datetime) else date.today() - timedelta(days=1)

        # If no previous sync and no from_date → storico 90 giorni
        if not sync_from and force:
            sync_from = None  # Will default to 90 days in FiscoAPI

        # Try sync with retry backoff
        raw_invoices = None
        last_error = None
        retry_count = 0

        for attempt in range(MAX_RETRIES):
            try:
                raw_invoices = await self.fiscoapi.sync_invoices(
                    token=user.spid_token,
                    from_date=sync_from,
                )
                break
            except ConnectionError as e:
                last_error = e
                retry_count = attempt + 1
                logger.warning(
                    "FiscoAPI sync failed (attempt %d/%d): %s",
                    attempt + 1, MAX_RETRIES, e,
                )

        if raw_invoices is None:
            # All retries failed
            await self.publish_event(
                "invoice.sync_failed",
                {
                    "reason": str(last_error),
                    "retries": retry_count,
                },
                tenant_id,
            )
            raise ConnectionError(
                f"FiscoAPI non disponibile dopo {MAX_RETRIES} tentativi. "
                f"Prossimo tentativo automatico tra {RETRY_DELAYS_HOURS[min(retry_count - 1, len(RETRY_DELAYS_HOURS) - 1)]}h."
            )

        # Handle empty cassetto
        if not raw_invoices:
            await self.publish_event(
                "invoice.sync_complete",
                {"downloaded": 0, "new": 0, "message": "Nessuna fattura trovata nel cassetto fiscale"},
                tenant_id,
            )
            return {
                "downloaded": 0,
                "new": 0,
                "duplicates": 0,
                "errors": 0,
                "message": "Nessuna fattura trovata nel cassetto fiscale per il periodo selezionato",
            }

        # Process and save invoices
        new_count = 0
        dup_count = 0
        error_count = 0

        for raw in raw_invoices:
            try:
                is_dup = await self._is_duplicate(
                    tenant_id,
                    raw["numero_fattura"],
                    raw["emittente_piva"],
                    raw.get("data_fattura"),
                )
                if is_dup:
                    dup_count += 1
                    continue

                invoice = Invoice(
                    tenant_id=tenant_id,
                    type="passiva",  # Cassetto fiscale = fatture ricevute
                    document_type=raw.get("tipo_documento", "TD01"),
                    source="cassetto_fiscale",
                    numero_fattura=raw["numero_fattura"],
                    emittente_piva=raw["emittente_piva"],
                    emittente_nome=raw.get("emittente_nome"),
                    data_fattura=date.fromisoformat(raw["data_fattura"]) if raw.get("data_fattura") else None,
                    importo_netto=raw.get("importo_netto"),
                    importo_iva=raw.get("importo_iva"),
                    importo_totale=raw.get("importo_totale"),
                    raw_xml=raw.get("raw_xml"),
                    processing_status="pending",
                )
                self.db.add(invoice)
                await self.db.flush()
                new_count += 1

                # Publish download event
                await self.publish_event(
                    "invoice.downloaded",
                    {
                        "invoice_id": str(invoice.id),
                        "numero_fattura": raw["numero_fattura"],
                        "emittente": raw.get("emittente_nome", raw["emittente_piva"]),
                    },
                    tenant_id,
                )
            except Exception as e:
                error_count += 1
                logger.error("Error processing invoice %s: %s", raw.get("numero_fattura"), e)

        # Publish sync complete event
        await self.publish_event(
            "invoice.sync_complete",
            {
                "downloaded": len(raw_invoices),
                "new": new_count,
                "duplicates": dup_count,
                "errors": error_count,
            },
            tenant_id,
        )

        return {
            "downloaded": len(raw_invoices),
            "new": new_count,
            "duplicates": dup_count,
            "errors": error_count,
            "message": f"Sync completato: {new_count} nuove fatture scaricate",
        }

    async def _is_duplicate(
        self,
        tenant_id: uuid.UUID,
        numero_fattura: str,
        emittente_piva: str,
        data_fattura: str | None,
    ) -> bool:
        """Check if invoice already exists (dedup on numero_fattura + P.IVA + data)."""
        conditions = [
            Invoice.tenant_id == tenant_id,
            Invoice.numero_fattura == numero_fattura,
            Invoice.emittente_piva == emittente_piva,
        ]
        if data_fattura:
            conditions.append(
                Invoice.data_fattura == date.fromisoformat(data_fattura)
            )

        result = await self.db.execute(
            select(Invoice.id).where(and_(*conditions)).limit(1)
        )
        return result.scalar_one_or_none() is not None
