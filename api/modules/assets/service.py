"""Service layer for asset management (US-31, US-32)."""

import logging
import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import Asset, FiscalRule
from api.modules.assets.depreciation import (
    DEFAULT_CAPITALIZATION_THRESHOLD,
    calculate_annual_depreciation,
    calculate_pro_rata_depreciation,
    get_depreciation_rate,
    suggest_categories,
)

logger = logging.getLogger(__name__)


class AssetService:
    """Business logic for fixed asset management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_capitalization_threshold(self) -> float:
        """Get capitalization threshold from fiscal_rules table."""
        result = await self.db.execute(
            select(FiscalRule).where(
                FiscalRule.key == "soglia_cespite",
            )
        )
        rule = result.scalar_one_or_none()
        if rule:
            return float(rule.value)
        return DEFAULT_CAPITALIZATION_THRESHOLD

    async def create_asset(
        self,
        tenant_id: uuid.UUID,
        description: str,
        category: str,
        purchase_date: date,
        purchase_amount: float,
        is_used: bool = False,
        invoice_id: uuid.UUID | None = None,
    ) -> dict:
        """Create a fixed asset.

        AC-31.1: Auto-create if amount > threshold (516.46 EUR)
        AC-31.2: Set depreciation rate from ministerial tables
        AC-31.3: Unknown category -> suggest top 3
        AC-31.4: Used asset (no IVA) -> depreciable = gross amount
        """
        threshold = await self.get_capitalization_threshold()

        if purchase_amount < threshold:
            raise ValueError(
                f"Importo {purchase_amount:.2f} EUR inferiore alla soglia "
                f"di capitalizzazione ({threshold:.2f} EUR)"
            )

        # AC-31.2: Get depreciation rate
        rate = get_depreciation_rate(category)
        category_suggestions: list[dict] | None = None

        if rate is None:
            # AC-31.3: Category not mapped -> suggest top 3
            category_suggestions = suggest_categories(description)
            if category_suggestions:
                # Use first suggestion as default
                category = category_suggestions[0]["category"]
                rate = category_suggestions[0]["rate"]
            else:
                rate = 15.0  # fallback

        # AC-31.4: Used asset -> depreciable = gross (no IVA deduction)
        if is_used:
            depreciable_amount = purchase_amount
        else:
            # For new assets, depreciable = net of IVA (purchase_amount is the net)
            depreciable_amount = purchase_amount

        asset = Asset(
            tenant_id=tenant_id,
            invoice_id=invoice_id,
            description=description,
            category=category,
            purchase_date=purchase_date,
            purchase_amount=purchase_amount,
            depreciable_amount=depreciable_amount,
            depreciation_rate=rate,
            accumulated_depreciation=0.0,
            residual_value=depreciable_amount,
            is_used=is_used,
            status="active",
        )
        self.db.add(asset)
        await self.db.flush()

        result = self._asset_to_dict(asset)
        result["category_suggestions"] = category_suggestions
        return result

    async def list_assets(self, tenant_id: uuid.UUID) -> dict:
        """AC-32.1: Registry of assets (description, value, fund, residual, %)."""
        result = await self.db.execute(
            select(Asset)
            .where(Asset.tenant_id == tenant_id)
            .order_by(Asset.created_at.desc())
        )
        items = result.scalars().all()
        return {
            "items": [self._asset_to_dict(a) for a in items],
            "total": len(items),
        }

    async def get_asset(
        self, asset_id: uuid.UUID, tenant_id: uuid.UUID,
    ) -> dict:
        """Get single asset detail."""
        asset = await self._get_asset(asset_id, tenant_id)
        return self._asset_to_dict(asset)

    async def dispose_asset(
        self,
        asset_id: uuid.UUID,
        tenant_id: uuid.UUID,
        disposal_date: date,
        disposal_amount: float = 0.0,
    ) -> dict:
        """Dispose of an asset (sell, scrap, theft).

        AC-32.2: Sale -> calculate gain/loss, closing entries
        AC-32.3: Mid-year disposal -> pro-rata depreciation
        AC-32.4: Scrapping/theft (price=0) -> loss = residual value
        """
        asset = await self._get_asset(asset_id, tenant_id)

        if asset.status not in ("active", "fully_depreciated"):
            raise ValueError(f"Cespite in stato '{asset.status}', non dismissibile")

        # AC-32.3: Pro-rata depreciation
        pro_rata = calculate_pro_rata_depreciation(
            depreciable_amount=asset.depreciable_amount,
            rate=asset.depreciation_rate,
            disposal_date=disposal_date,
            accumulated=asset.accumulated_depreciation,
        )

        # Update accumulated depreciation with pro-rata
        new_accumulated = asset.accumulated_depreciation + pro_rata
        residual_at_disposal = round(asset.depreciable_amount - new_accumulated, 2)
        if residual_at_disposal < 0:
            residual_at_disposal = 0.0

        # Calculate gain/loss
        gain_loss = round(disposal_amount - residual_at_disposal, 2)

        if gain_loss > 0:
            gain_loss_type = "plusvalenza"
        elif gain_loss < 0:
            gain_loss_type = "minusvalenza"
        else:
            gain_loss_type = "zero"

        # Determine status
        if disposal_amount == 0:
            status = "scrapped"
        else:
            status = "disposed"

        # Update asset
        asset.status = status
        asset.disposal_date = disposal_date
        asset.disposal_amount = disposal_amount
        asset.gain_loss = gain_loss
        asset.accumulated_depreciation = new_accumulated
        asset.residual_value = 0.0

        await self.db.flush()

        # Build journal entries
        journal_entries = []

        # Pro-rata depreciation entry
        if pro_rata > 0:
            journal_entries.append({
                "description": f"Ammortamento pro-rata cespite: {asset.description}",
                "lines": [
                    {
                        "account_code": "6400",
                        "account_name": "Ammortamento",
                        "debit": pro_rata,
                        "credit": 0.0,
                    },
                    {
                        "account_code": "1050",
                        "account_name": "Fondo ammortamento",
                        "debit": 0.0,
                        "credit": pro_rata,
                    },
                ],
            })

        # Closing entry
        closing_lines = [
            {
                "account_code": "1050",
                "account_name": "Fondo ammortamento",
                "debit": new_accumulated,
                "credit": 0.0,
            },
        ]

        if disposal_amount > 0:
            closing_lines.append({
                "account_code": "1010",
                "account_name": "Banca c/c",
                "debit": disposal_amount,
                "credit": 0.0,
            })

        closing_lines.append({
            "account_code": "1040",
            "account_name": "Cespiti",
            "debit": 0.0,
            "credit": asset.depreciable_amount,
        })

        if gain_loss > 0:
            closing_lines.append({
                "account_code": "7100",
                "account_name": "Plusvalenze",
                "debit": 0.0,
                "credit": gain_loss,
            })
        elif gain_loss < 0:
            closing_lines.append({
                "account_code": "6500",
                "account_name": "Minusvalenze",
                "debit": abs(gain_loss),
                "credit": 0.0,
            })

        journal_entries.append({
            "description": f"Dismissione cespite: {asset.description}",
            "lines": closing_lines,
        })

        return {
            "id": str(asset.id),
            "description": asset.description,
            "disposal_date": disposal_date.isoformat(),
            "disposal_amount": disposal_amount,
            "residual_value_at_disposal": residual_at_disposal,
            "pro_rata_depreciation": pro_rata,
            "gain_loss": gain_loss,
            "gain_loss_type": gain_loss_type,
            "status": status,
            "journal_entries": journal_entries,
            "message": self._disposal_message(asset.description, gain_loss_type, gain_loss),
        }

    async def run_depreciation(
        self,
        tenant_id: uuid.UUID,
        fiscal_year: int,
    ) -> dict:
        """AC-31.2: Run annual depreciation for all active assets.

        DARE Ammortamento / AVERE Fondo ammortamento
        AC-32.5: Fully depreciated -> 'Ammortizzato, ancora in uso'
        """
        result = await self.db.execute(
            select(Asset).where(
                Asset.tenant_id == tenant_id,
                Asset.status == "active",
            )
        )
        assets = result.scalars().all()

        journal_entries = []
        fully_depreciated_list = []
        total_depreciation = 0.0
        processed = 0

        for asset in assets:
            depreciation = calculate_annual_depreciation(
                depreciable_amount=asset.depreciable_amount,
                rate=asset.depreciation_rate,
                purchase_date=asset.purchase_date,
                fiscal_year=fiscal_year,
                accumulated=asset.accumulated_depreciation,
            )

            if depreciation <= 0:
                continue

            # Update asset
            asset.accumulated_depreciation = round(
                asset.accumulated_depreciation + depreciation, 2,
            )
            asset.residual_value = round(
                asset.depreciable_amount - asset.accumulated_depreciation, 2,
            )
            if asset.residual_value < 0:
                asset.residual_value = 0.0

            total_depreciation += depreciation
            processed += 1

            # Journal entry
            journal_entries.append({
                "description": (
                    f"Ammortamento {fiscal_year} - {asset.description} "
                    f"({asset.category} {asset.depreciation_rate}%)"
                ),
                "lines": [
                    {
                        "account_code": "6400",
                        "account_name": "Ammortamento",
                        "debit": depreciation,
                        "credit": 0.0,
                    },
                    {
                        "account_code": "1050",
                        "account_name": "Fondo ammortamento",
                        "debit": 0.0,
                        "credit": depreciation,
                    },
                ],
            })

            # AC-32.5: Check fully depreciated
            if asset.residual_value <= 0:
                asset.status = "fully_depreciated"
                fully_depreciated_list.append({
                    "id": str(asset.id),
                    "description": asset.description,
                    "message": "Ammortizzato, ancora in uso",
                })

        await self.db.flush()

        return {
            "fiscal_year": fiscal_year,
            "assets_processed": processed,
            "total_depreciation": round(total_depreciation, 2),
            "journal_entries": journal_entries,
            "fully_depreciated": fully_depreciated_list,
            "message": (
                f"Ammortamento {fiscal_year} completato: "
                f"{processed} cespiti, totale {total_depreciation:.2f} EUR"
            ),
        }

    async def check_invoice_for_assets(
        self,
        tenant_id: uuid.UUID,
        invoice_id: uuid.UUID,
        line_description: str,
        line_amount: float,
        is_used: bool = False,
    ) -> dict:
        """AC-31.1 + AC-31.5: Check if invoice line should create asset."""
        threshold = await self.get_capitalization_threshold()

        should_create = line_amount > threshold

        result = {
            "should_create": should_create,
            "line_description": line_description,
            "line_amount": line_amount,
            "threshold": threshold,
        }

        if should_create:
            suggestions = suggest_categories(line_description)
            result["category_suggestions"] = suggestions

        return result

    async def _get_asset(
        self, asset_id: uuid.UUID, tenant_id: uuid.UUID,
    ) -> Asset:
        """Get asset by id and tenant."""
        result = await self.db.execute(
            select(Asset).where(
                Asset.id == asset_id,
                Asset.tenant_id == tenant_id,
            )
        )
        asset = result.scalar_one_or_none()
        if not asset:
            raise ValueError("Cespite non trovato")
        return asset

    @staticmethod
    def _asset_to_dict(asset: Asset) -> dict:
        """Convert asset model to dict."""
        return {
            "id": str(asset.id),
            "tenant_id": str(asset.tenant_id),
            "invoice_id": str(asset.invoice_id) if asset.invoice_id else None,
            "description": asset.description,
            "category": asset.category,
            "purchase_date": asset.purchase_date.isoformat() if asset.purchase_date else None,
            "purchase_amount": asset.purchase_amount,
            "depreciable_amount": asset.depreciable_amount,
            "depreciation_rate": asset.depreciation_rate,
            "accumulated_depreciation": asset.accumulated_depreciation,
            "residual_value": asset.residual_value,
            "is_used": asset.is_used,
            "status": asset.status,
            "disposal_date": asset.disposal_date.isoformat() if asset.disposal_date else None,
            "disposal_amount": asset.disposal_amount,
            "gain_loss": asset.gain_loss,
            "journal_entry": None,
            "category_suggestions": None,
        }

    @staticmethod
    def _disposal_message(description: str, gain_loss_type: str, gain_loss: float) -> str:
        """Build human-readable disposal message."""
        if gain_loss_type == "plusvalenza":
            return (
                f"Cespite '{description}' venduto con plusvalenza "
                f"di {gain_loss:.2f} EUR"
            )
        elif gain_loss_type == "minusvalenza":
            return (
                f"Cespite '{description}' dismisso con minusvalenza "
                f"di {abs(gain_loss):.2f} EUR"
            )
        else:
            return f"Cespite '{description}' dismisso senza plus/minusvalenza"
