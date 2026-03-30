"""Ammortamenti auto service (US-59).

Scans invoices categorized as immobilizzazioni, proposes depreciation.
Uses ministerial rates: 20% HW, 25% auto, 12% mobili.
Threshold: EUR 516.46 -> full deduction.
"""

import logging
import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import Invoice, Asset

logger = logging.getLogger(__name__)

# Ministerial depreciation rates by category
DEPRECIATION_RATES = {
    "hardware": 20.0,
    "computer": 20.0,
    "elettronica": 20.0,
    "autoveicoli": 25.0,
    "auto": 25.0,
    "mobili": 12.0,
    "arredamento": 12.0,
    "macchinari": 15.0,
    "impianti": 12.0,
    "attrezzature": 15.0,
    "software": 20.0,
    "immobilizzazioni": 12.0,
}

# Threshold for full deduction (beni strumentali < 516.46 EUR)
FULL_DEDUCTION_THRESHOLD = 516.46


class AmmortamentiService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def auto_detect(self, tenant_id: uuid.UUID) -> dict:
        """Scan invoices for immobilizzazioni and propose depreciation (US-59)."""
        # Find invoices categorized as asset-type categories
        list(DEPRECIATION_RATES.keys())
        # Use LIKE for flexible matching
        result = await self.db.execute(
            select(Invoice).where(
                Invoice.tenant_id == tenant_id,
                Invoice.type == "passiva",
                Invoice.category.isnot(None),
            )
        )
        invoices = result.scalars().all()

        proposals = []
        for inv in invoices:
            if not inv.category:
                continue

            cat_lower = inv.category.lower()
            rate = None
            for cat_key, cat_rate in DEPRECIATION_RATES.items():
                if cat_key in cat_lower:
                    rate = cat_rate
                    break

            if rate is None:
                continue

            importo = inv.importo_netto or 0
            if importo <= 0:
                continue

            # Check if asset already exists for this invoice
            existing = await self.db.execute(
                select(Asset).where(
                    Asset.tenant_id == tenant_id,
                    Asset.invoice_id == inv.id,
                )
            )
            if existing.scalar_one_or_none():
                continue

            # Determine if full deduction applies
            full_deduction = importo <= FULL_DEDUCTION_THRESHOLD

            proposal = {
                "invoice_id": str(inv.id),
                "invoice_numero": inv.numero_fattura,
                "description": f"{inv.emittente_nome} - {inv.category}",
                "category": inv.category,
                "purchase_amount": round(importo, 2),
                "depreciation_rate": rate if not full_deduction else 100.0,
                "annual_depreciation": round(importo * rate / 100, 2) if not full_deduction else round(importo, 2),
                "full_deduction": full_deduction,
                "purchase_date": inv.data_fattura.isoformat() if inv.data_fattura else None,
            }
            proposals.append(proposal)

        return {
            "proposals": proposals,
            "total_count": len(proposals),
            "total_amount": round(sum(p["purchase_amount"] for p in proposals), 2),
            "total_annual_depreciation": round(sum(p["annual_depreciation"] for p in proposals), 2),
            "full_deduction_count": sum(1 for p in proposals if p["full_deduction"]),
            "message": f"Trovate {len(proposals)} potenziali immobilizzazioni da ammortizzare",
        }

    async def confirm_asset(
        self,
        tenant_id: uuid.UUID,
        invoice_id: uuid.UUID,
        depreciation_rate: float,
    ) -> dict:
        """Confirm an invoice as a fixed asset and create asset record."""
        result = await self.db.execute(
            select(Invoice).where(
                Invoice.id == invoice_id,
                Invoice.tenant_id == tenant_id,
            )
        )
        inv = result.scalar_one_or_none()
        if not inv:
            raise ValueError("Fattura non trovata")

        importo = inv.importo_netto or 0

        asset = Asset(
            tenant_id=tenant_id,
            invoice_id=inv.id,
            description=f"{inv.emittente_nome} - {inv.category or 'Immobilizzazione'}",
            category=inv.category or "immobilizzazioni",
            purchase_date=inv.data_fattura or date.today(),
            purchase_amount=importo,
            depreciable_amount=importo,
            depreciation_rate=depreciation_rate,
            accumulated_depreciation=0.0,
            residual_value=importo,
            status="active",
        )
        self.db.add(asset)
        await self.db.flush()

        return {
            "asset_id": str(asset.id),
            "description": asset.description,
            "purchase_amount": asset.purchase_amount,
            "depreciation_rate": asset.depreciation_rate,
            "message": "Cespite creato con successo",
        }
