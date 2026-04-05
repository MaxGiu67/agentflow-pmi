"""Service for products catalog + deal products (US-142→US-145)."""

import logging
import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import CrmProduct, CrmProductCategory, CrmDealProduct, CrmDeal

logger = logging.getLogger(__name__)


class ProductsService:
    """CRUD for product catalog and deal-product associations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── US-142: Create product ─────────────────────────

    async def create_product(self, tenant_id: uuid.UUID, data: dict) -> dict:
        """AC-142.1: Create product in catalog."""
        code = data.get("code", "").strip().lower()
        if not code or len(code) > 50:
            return {"error": "Codice prodotto obbligatorio, max 50 caratteri"}

        existing = await self.db.execute(
            select(CrmProduct).where(
                CrmProduct.tenant_id == tenant_id,
                CrmProduct.code == code,
            )
        )
        if existing.scalar_one_or_none():
            return {"error": "Codice prodotto gia esistente nel tenant"}

        pricing_model = data.get("pricing_model", "fixed")
        if pricing_model not in ("fixed", "hourly", "custom"):
            return {"error": "pricing_model deve essere: fixed, hourly, custom"}

        # AC-142.4: Auto-create category if needed
        category_id = None
        category_name = data.get("category_name")
        if category_name:
            cat_result = await self.db.execute(
                select(CrmProductCategory).where(
                    CrmProductCategory.tenant_id == tenant_id,
                    CrmProductCategory.name == category_name,
                )
            )
            cat = cat_result.scalar_one_or_none()
            if not cat:
                cat = CrmProductCategory(tenant_id=tenant_id, name=category_name)
                self.db.add(cat)
                await self.db.flush()
            category_id = cat.id
        elif data.get("category_id"):
            category_id = uuid.UUID(data["category_id"]) if isinstance(data["category_id"], str) else data["category_id"]

        product = CrmProduct(
            tenant_id=tenant_id,
            name=data.get("name", code),
            code=code,
            category_id=category_id,
            pricing_model=pricing_model,
            base_price=data.get("base_price"),
            hourly_rate=data.get("hourly_rate"),
            estimated_duration_days=data.get("estimated_duration_days"),
            technology_type=data.get("technology_type"),
            target_margin_percent=data.get("target_margin_percent"),
            description=data.get("description"),
            is_active=True,
        )
        self.db.add(product)
        await self.db.flush()
        return self._product_to_dict(product)

    # ── US-143: Update / Deactivate ────────────────────

    async def update_product(self, product_id: uuid.UUID, data: dict) -> dict | None:
        """AC-143.1: Update product (code immutable)."""
        result = await self.db.execute(
            select(CrmProduct).where(CrmProduct.id == product_id)
        )
        product = result.scalar_one_or_none()
        if not product:
            return None

        for key in ("name", "base_price", "hourly_rate", "estimated_duration_days",
                     "technology_type", "target_margin_percent", "description", "is_active"):
            if key in data and data[key] is not None:
                setattr(product, key, data[key])

        await self.db.flush()
        return self._product_to_dict(product)

    async def delete_product(self, product_id: uuid.UUID) -> dict:
        """AC-143.3: Hard delete not allowed."""
        result = await self.db.execute(
            select(CrmProduct).where(CrmProduct.id == product_id)
        )
        if not result.scalar_one_or_none():
            return {"error": "Prodotto non trovato", "code": 404}
        return {"error": "Eliminazione non consentita. Usa disattivazione.", "code": 409}

    # ── List products ──────────────────────────────────

    async def list_products(
        self, tenant_id: uuid.UUID, active_only: bool = False, category_id: uuid.UUID | None = None,
    ) -> list[dict]:
        query = select(CrmProduct).where(CrmProduct.tenant_id == tenant_id)
        if active_only:
            query = query.where(CrmProduct.is_active.is_(True))
        if category_id:
            query = query.where(CrmProduct.category_id == category_id)
        query = query.order_by(CrmProduct.name)
        result = await self.db.execute(query)
        return [self._product_to_dict(p) for p in result.scalars().all()]

    # ── US-144: Deal products ──────────────────────────

    async def add_deal_product(self, tenant_id: uuid.UUID, deal_id: uuid.UUID, data: dict) -> dict:
        """AC-144.1: Add product to deal."""
        product_id = data.get("product_id")
        if not product_id:
            return {"error": "product_id obbligatorio"}

        pid = uuid.UUID(product_id) if isinstance(product_id, str) else product_id

        # Verify product exists
        prod_result = await self.db.execute(
            select(CrmProduct).where(CrmProduct.id == pid, CrmProduct.is_active.is_(True))
        )
        product = prod_result.scalar_one_or_none()
        if not product:
            return {"error": "Prodotto non trovato o disattivato"}

        dp = CrmDealProduct(
            tenant_id=tenant_id,
            deal_id=deal_id,
            product_id=pid,
            quantity=data.get("quantity", 1),
            price_override=data.get("price_override"),
            notes=data.get("notes"),
        )
        self.db.add(dp)
        await self.db.flush()

        # AC-144.2: Update deal revenue
        await self._recalculate_deal_revenue(deal_id)

        return self._deal_product_to_dict(dp, product)

    async def remove_deal_product(self, deal_id: uuid.UUID, line_id: uuid.UUID) -> dict:
        """AC-144.3: Remove product from deal (min 1 product)."""
        # Count products on deal
        count = await self.db.scalar(
            select(func.count(CrmDealProduct.id)).where(CrmDealProduct.deal_id == deal_id)
        ) or 0

        if count <= 1:
            return {"error": "Un deal deve avere almeno 1 prodotto"}

        result = await self.db.execute(
            select(CrmDealProduct).where(CrmDealProduct.id == line_id, CrmDealProduct.deal_id == deal_id)
        )
        dp = result.scalar_one_or_none()
        if not dp:
            return {"error": "Linea prodotto non trovata"}

        await self.db.delete(dp)
        await self.db.flush()
        await self._recalculate_deal_revenue(deal_id)
        return {"status": "removed"}

    async def list_deal_products(self, deal_id: uuid.UUID) -> list[dict]:
        result = await self.db.execute(
            select(CrmDealProduct).where(CrmDealProduct.deal_id == deal_id)
        )
        items = []
        for dp in result.scalars().all():
            prod_result = await self.db.execute(
                select(CrmProduct).where(CrmProduct.id == dp.product_id)
            )
            product = prod_result.scalar_one_or_none()
            items.append(self._deal_product_to_dict(dp, product))
        return items

    async def _recalculate_deal_revenue(self, deal_id: uuid.UUID) -> None:
        """AC-144.2: Update deal.expected_revenue from product lines."""
        result = await self.db.execute(
            select(CrmDealProduct).where(CrmDealProduct.deal_id == deal_id)
        )
        total = 0.0
        for dp in result.scalars().all():
            prod_result = await self.db.execute(
                select(CrmProduct).where(CrmProduct.id == dp.product_id)
            )
            product = prod_result.scalar_one_or_none()
            if product:
                price = dp.price_override if dp.price_override is not None else (product.base_price or 0)
                total += price * (dp.quantity or 1)

        deal_result = await self.db.execute(
            select(CrmDeal).where(CrmDeal.id == deal_id)
        )
        deal = deal_result.scalar_one_or_none()
        if deal:
            deal.expected_revenue = total
            await self.db.flush()

    def _product_to_dict(self, p: CrmProduct) -> dict:
        return {
            "id": str(p.id),
            "name": p.name,
            "code": p.code,
            "category_id": str(p.category_id) if p.category_id else None,
            "pricing_model": p.pricing_model,
            "base_price": p.base_price,
            "hourly_rate": p.hourly_rate,
            "estimated_duration_days": p.estimated_duration_days,
            "technology_type": p.technology_type,
            "target_margin_percent": p.target_margin_percent,
            "description": p.description,
            "is_active": p.is_active,
        }

    def _deal_product_to_dict(self, dp: CrmDealProduct, product: CrmProduct | None) -> dict:
        price = dp.price_override if dp.price_override is not None else (product.base_price if product else 0)
        return {
            "id": str(dp.id),
            "deal_id": str(dp.deal_id),
            "product_id": str(dp.product_id),
            "product_name": product.name if product else "",
            "quantity": dp.quantity,
            "price_override": dp.price_override,
            "unit_price": price,
            "line_total": (price or 0) * (dp.quantity or 1),
            "notes": dp.notes,
        }
