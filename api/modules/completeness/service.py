"""Completeness Score service (US-69).

Detects which data sources are connected and what features they unlock.
Uses positive framing: "Hai sbloccato X", not "Ti manca il 55%".
"""

import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import (
    BankAccount,
    BankTransaction,
    Corrispettivo,
    Invoice,
    PayrollCost,
)

# Source definitions with unlocked features and next-unlock benefits
SOURCE_DEFINITIONS = [
    {
        "source_type": "fatture",
        "label": "Fatture",
        "description": "Fatture attive e passive dal cassetto fiscale",
        "unlocks": ["Fatturato in tempo reale", "Categorizzazione automatica", "Scritture contabili"],
        "next_benefit": "Vedi fatturato e costi da fatture in tempo reale",
    },
    {
        "source_type": "banca",
        "label": "Conto bancario",
        "description": "Movimenti bancari da PDF, CSV o Open Banking",
        "unlocks": ["Cash Flow predittivo", "Riconciliazione automatica", "Saldo in tempo reale"],
        "next_benefit": "Attivi il Cash Flow predittivo e la riconciliazione automatica",
    },
    {
        "source_type": "paghe",
        "label": "Costo del personale",
        "description": "Riepilogo paghe dal consulente del lavoro",
        "unlocks": ["Costo personale nel margine", "Previsione uscite stipendi"],
        "next_benefit": "Vedi il costo reale del personale e il margine operativo",
    },
    {
        "source_type": "corrispettivi",
        "label": "Corrispettivi",
        "description": "Incassi da registratore di cassa",
        "unlocks": ["Fatturato completo (retail)", "IVA completa"],
        "next_benefit": "Completi il fatturato con le vendite al dettaglio e l'IVA",
    },
    {
        "source_type": "bilancio",
        "label": "Saldi bilancio",
        "description": "Saldi iniziali dal commercialista",
        "unlocks": ["Bilancio corretto", "Stato patrimoniale", "Situazione contabile completa"],
        "next_benefit": "Hai il bilancio completo e lo stato patrimoniale",
    },
    {
        "source_type": "f24",
        "label": "Versamenti F24",
        "description": "Ricevute F24 per IRPEF, INPS, IVA",
        "unlocks": ["Quadratura fiscale", "Verifica versamenti", "Scadenze calcolate"],
        "next_benefit": "Verifichi che tutti i versamenti fiscali siano corretti",
    },
]


class CompletenessService:
    """Servizio Completeness Score: rileva sorgenti collegate e funzionalita sbloccate (US-69)."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_score(self, tenant_id: uuid.UUID) -> dict:
        """Calculate completeness score for a tenant.

        Auto-detects connected sources by checking actual data in the DB.
        Returns positive-framed response with unlocked features and next suggestion.
        """
        sources = []
        all_unlocked_features = []

        for src_def in SOURCE_DEFINITIONS:
            status = await self._detect_source_status(tenant_id, src_def["source_type"])

            entry = {
                "source_type": src_def["source_type"],
                "label": src_def["label"],
                "description": src_def["description"],
                "status": status,
                "unlocks": src_def["unlocks"],
                "next_benefit": src_def["next_benefit"],
            }

            if status == "connected":
                all_unlocked_features.extend(src_def["unlocks"])

            sources.append(entry)

        connected = [s for s in sources if s["status"] == "connected"]
        not_connected = [s for s in sources if s["status"] != "connected"]
        next_suggestion = not_connected[0] if not_connected else None

        return {
            "sources": sources,
            "connected_count": len(connected),
            "total_sources": len(sources),
            "unlocked_features": all_unlocked_features,
            "next_suggestion": {
                "source_type": next_suggestion["source_type"],
                "label": next_suggestion["label"],
                "benefit": next_suggestion["next_benefit"],
            } if next_suggestion else None,
            "message": self._build_message(connected, next_suggestion),
        }

    async def _detect_source_status(self, tenant_id: uuid.UUID, source_type: str) -> str:
        """Auto-detect if a source has data in the DB."""
        if source_type == "fatture":
            count = await self._count(Invoice, tenant_id)
            return "connected" if count > 0 else "not_configured"

        elif source_type == "banca":
            # Check for bank accounts with transactions
            acct_count = await self._count(BankAccount, tenant_id)
            if acct_count == 0:
                return "not_configured"
            tx_count = await self.db.scalar(
                select(func.count(BankTransaction.id)).join(
                    BankAccount, BankTransaction.bank_account_id == BankAccount.id
                ).where(BankAccount.tenant_id == tenant_id)
            ) or 0
            return "connected" if tx_count > 0 else "pending"

        elif source_type == "paghe":
            count = await self._count(PayrollCost, tenant_id)
            return "connected" if count > 0 else "not_configured"

        elif source_type == "corrispettivi":
            count = await self._count(Corrispettivo, tenant_id)
            return "connected" if count > 0 else "not_configured"

        elif source_type == "bilancio":
            # Check for journal entries with "apertura" in description
            from api.db.models import JournalEntry
            result = await self.db.scalar(
                select(func.count(JournalEntry.id)).where(
                    JournalEntry.tenant_id == tenant_id,
                    JournalEntry.description.ilike("%apertura%"),
                )
            ) or 0
            return "connected" if result > 0 else "not_configured"

        elif source_type == "f24":
            from api.db.models import F24Document
            count = await self._count(F24Document, tenant_id)
            return "connected" if count > 0 else "not_configured"

        return "not_configured"

    async def _count(self, model, tenant_id: uuid.UUID) -> int:
        return await self.db.scalar(
            select(func.count(model.id)).where(model.tenant_id == tenant_id)
        ) or 0

    def _build_message(self, connected: list, next_suggestion: dict | None) -> str:
        if not connected:
            return "Inizia collegando il cassetto fiscale per importare le fatture"

        labels = [s["label"] for s in connected]
        msg = f"Hai sbloccato: {', '.join(labels)}"

        if next_suggestion:
            msg += f". Prossimo passo: collega {next_suggestion['label']} per {next_suggestion['next_benefit'].lower()}"

        return msg
