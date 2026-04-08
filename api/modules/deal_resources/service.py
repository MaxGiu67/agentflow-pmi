"""Service for managing deal resources — persons from Portal assigned to deals.

Handles T&M and project staffing: add/remove/update persons on a deal,
auto-fetch person info from Portal to cache locally.
"""

import logging
import uuid
from datetime import date, datetime

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import CrmDealResource, CrmDealProduct, CrmProduct
from api.adapters.portal_client import portal_client

logger = logging.getLogger(__name__)


class DealResourceService:
    """Business logic for deal resource management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_resources(self, deal_id: uuid.UUID, tenant_id: uuid.UUID) -> list[dict]:
        """List all resources assigned to a deal."""
        result = await self.db.execute(
            select(CrmDealResource).where(
                CrmDealResource.deal_id == deal_id,
                CrmDealResource.tenant_id == tenant_id,
            ).order_by(CrmDealResource.created_at)
        )
        return [self._resource_to_dict(r) for r in result.scalars().all()]

    async def add_resource(self, deal_id: uuid.UUID, tenant_id: uuid.UUID, data: dict) -> dict:
        """Add a resource to a deal. Auto-fetches person info from Portal."""
        portal_person_id = data.get("portal_person_id")
        if not portal_person_id:
            return {"error": "portal_person_id is required"}

        # Fetch person data from Portal to cache locally
        person_name = data.get("person_name", "")
        person_email = data.get("person_email", "")
        seniority = data.get("seniority", "")
        daily_cost = data.get("daily_cost")

        try:
            person_data = await portal_client.get_person(portal_person_id)
            if person_data and not person_data.get("error"):
                first = person_data.get("firstName") or person_data.get("first_name") or ""
                last = person_data.get("lastName") or person_data.get("last_name") or ""
                fetched_name = f"{first} {last}".strip()
                if fetched_name:
                    person_name = person_name or fetched_name
                fetched_email = person_data.get("privateEmail") or person_data.get("private_email") or ""
                if fetched_email:
                    person_email = person_email or fetched_email
                fetched_seniority = person_data.get("Seniority") or person_data.get("seniority") or ""
                if isinstance(fetched_seniority, dict):
                    fetched_seniority = fetched_seniority.get("description", "")
                if fetched_seniority:
                    seniority = seniority or fetched_seniority
                # Extract daily cost from active contract
                contracts = person_data.get("EmploymentContracts") or person_data.get("employmentContracts") or []
                for c in contracts:
                    end = c.get("end_date") or c.get("endDate") or c.get("effectiveEndDate")
                    if not end:  # Active contract
                        cost = c.get("dailyCost") or c.get("daily_cost") or 0
                        if cost and daily_cost is None:
                            daily_cost = float(cost)
                        break
        except Exception as e:
            logger.warning("Failed to fetch person %s from Portal: %s", portal_person_id, e)

        # Parse dates
        start_date = None
        end_date = None
        if data.get("start_date"):
            if isinstance(data["start_date"], str):
                start_date = date.fromisoformat(data["start_date"])
            else:
                start_date = data["start_date"]
        if data.get("end_date"):
            if isinstance(data["end_date"], str):
                end_date = date.fromisoformat(data["end_date"])
            else:
                end_date = data["end_date"]

        resource = CrmDealResource(
            tenant_id=tenant_id,
            deal_id=deal_id,
            portal_person_id=portal_person_id,
            person_name=person_name,
            person_email=person_email,
            seniority=seniority,
            daily_cost=daily_cost,
            role=data.get("role"),
            start_date=start_date,
            end_date=end_date,
            status=data.get("status", "assigned"),
            notes=data.get("notes"),
            portal_activity_id=data.get("portal_activity_id"),
        )
        self.db.add(resource)
        await self.db.flush()
        return self._resource_to_dict(resource)

    async def update_resource(self, resource_id: uuid.UUID, data: dict) -> dict | None:
        """Update an existing resource."""
        result = await self.db.execute(
            select(CrmDealResource).where(CrmDealResource.id == resource_id)
        )
        resource = result.scalar_one_or_none()
        if not resource:
            return None

        allowed_fields = {
            "role", "start_date", "end_date", "status", "notes",
            "daily_cost", "seniority", "portal_activity_id",
            "person_name", "person_email",
        }
        for key, val in data.items():
            if key in allowed_fields and val is not None:
                if key in ("start_date", "end_date") and isinstance(val, str):
                    val = date.fromisoformat(val)
                setattr(resource, key, val)

        await self.db.flush()
        # Re-fetch to get server-generated values (updated_at) without lazy-load issues
        result2 = await self.db.execute(
            select(CrmDealResource).where(CrmDealResource.id == resource_id)
        )
        resource = result2.scalar_one()
        return self._resource_to_dict(resource)

    async def remove_resource(self, resource_id: uuid.UUID) -> bool:
        """Remove a resource from a deal."""
        result = await self.db.execute(
            select(CrmDealResource).where(CrmDealResource.id == resource_id)
        )
        resource = result.scalar_one_or_none()
        if not resource:
            return False
        await self.db.delete(resource)
        await self.db.flush()
        return True

    async def check_requires_resources(self, deal_id: uuid.UUID, tenant_id: uuid.UUID) -> bool:
        """Check if any product on this deal requires resources (T&M/project staffing)."""
        result = await self.db.execute(
            select(CrmProduct.requires_resources).select_from(CrmDealProduct).join(
                CrmProduct, CrmDealProduct.product_id == CrmProduct.id,
            ).where(
                CrmDealProduct.deal_id == deal_id,
                CrmDealProduct.tenant_id == tenant_id,
                CrmProduct.requires_resources.is_(True),
            ).limit(1)
        )
        return result.scalar_one_or_none() is not None

    def _resource_to_dict(self, r: CrmDealResource) -> dict:
        """Convert a CrmDealResource to dict."""
        # Use getattr to avoid lazy-load issues with onupdate columns in async context
        created_at = getattr(r, "created_at", None)
        try:
            updated_at = getattr(r, "updated_at", None)
        except Exception:
            updated_at = None

        return {
            "id": str(r.id),
            "tenant_id": str(r.tenant_id),
            "deal_id": str(r.deal_id),
            "portal_person_id": r.portal_person_id,
            "person_name": r.person_name or "",
            "person_email": r.person_email or "",
            "seniority": r.seniority or "",
            "daily_cost": r.daily_cost,
            "role": r.role or "",
            "start_date": r.start_date.isoformat() if r.start_date else None,
            "end_date": r.end_date.isoformat() if r.end_date else None,
            "status": r.status or "assigned",
            "notes": r.notes or "",
            "portal_activity_id": r.portal_activity_id,
            "created_at": created_at.isoformat() if created_at else None,
            "updated_at": updated_at.isoformat() if updated_at else None,
        }
