"""Service for usage metering — LLM tokens, API calls, email, PDF pages (US-113/115)."""

import logging
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import TenantUsage, Tenant

logger = logging.getLogger(__name__)

DEFAULT_LLM_QUOTA = 100_000  # tokens/month


class MeteringService:
    """Track and check usage per tenant per month."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _get_or_create_usage(self, tenant_id: uuid.UUID) -> TenantUsage:
        """Get or create usage record for current month."""
        month = datetime.utcnow().strftime("%Y-%m")
        result = await self.db.execute(
            select(TenantUsage).where(
                TenantUsage.tenant_id == tenant_id,
                TenantUsage.month == month,
            )
        )
        usage = result.scalar_one_or_none()
        if not usage:
            usage = TenantUsage(tenant_id=tenant_id, month=month)
            self.db.add(usage)
            await self.db.flush()
        return usage

    # ── LLM tokens (US-113) ───────────────────────────────

    async def track_llm_usage(
        self, tenant_id: uuid.UUID, tokens_in: int, tokens_out: int,
    ) -> None:
        """AC-113.2: Increment LLM token counters after OpenAI call."""
        usage = await self._get_or_create_usage(tenant_id)
        usage.llm_tokens_in += tokens_in
        usage.llm_tokens_out += tokens_out
        usage.llm_requests += 1
        await self.db.flush()

    async def check_llm_quota(self, tenant_id: uuid.UUID) -> dict:
        """AC-113.3/113.4: Check if tenant has LLM quota remaining."""
        usage = await self._get_or_create_usage(tenant_id)
        total_tokens = usage.llm_tokens_in + usage.llm_tokens_out

        # Get tenant quota (from tenant_settings or default)
        from api.modules.tenant_settings.service import TenantSettingsService
        settings_svc = TenantSettingsService(self.db)
        quota_str = await settings_svc.get_setting(tenant_id, "llm_quota_monthly")
        quota = int(quota_str) if quota_str else DEFAULT_LLM_QUOTA

        return {
            "allowed": total_tokens < quota,
            "tokens_used": total_tokens,
            "tokens_in": usage.llm_tokens_in,
            "tokens_out": usage.llm_tokens_out,
            "requests": usage.llm_requests,
            "quota": quota,
            "remaining": max(0, quota - total_tokens),
        }

    # ── Other counters ────────────────────────────────────

    async def track_pdf_page(self, tenant_id: uuid.UUID, pages: int = 1) -> None:
        usage = await self._get_or_create_usage(tenant_id)
        usage.pdf_pages += pages
        await self.db.flush()

    async def track_api_call(self, tenant_id: uuid.UUID) -> None:
        usage = await self._get_or_create_usage(tenant_id)
        usage.api_calls += 1
        await self.db.flush()

    async def track_email_sent(self, tenant_id: uuid.UUID) -> None:
        usage = await self._get_or_create_usage(tenant_id)
        usage.email_sent += 1
        await self.db.flush()

    # ── Metering dashboard (US-115) ───────────────────────

    async def get_all_usage(self, month: str | None = None) -> list[dict]:
        """AC-115.1: Get usage for all tenants."""
        target_month = month or datetime.utcnow().strftime("%Y-%m")

        result = await self.db.execute(
            select(TenantUsage).where(TenantUsage.month == target_month)
        )
        usages = result.scalars().all()

        items = []
        for u in usages:
            # Get tenant name
            tenant_result = await self.db.execute(
                select(Tenant.name).where(Tenant.id == u.tenant_id)
            )
            tenant_name = tenant_result.scalar() or "Sconosciuto"

            items.append({
                "tenant_id": str(u.tenant_id),
                "tenant_name": tenant_name,
                "month": u.month,
                "llm_tokens": u.llm_tokens_in + u.llm_tokens_out,
                "llm_requests": u.llm_requests,
                "pdf_pages": u.pdf_pages,
                "api_calls": u.api_calls,
                "email_sent": u.email_sent,
            })

        return items

    async def get_tenant_usage(self, tenant_id: uuid.UUID, month: str | None = None) -> dict:
        """Get usage for a single tenant."""
        target_month = month or datetime.utcnow().strftime("%Y-%m")
        result = await self.db.execute(
            select(TenantUsage).where(
                TenantUsage.tenant_id == tenant_id,
                TenantUsage.month == target_month,
            )
        )
        usage = result.scalar_one_or_none()
        if not usage:
            return {
                "month": target_month,
                "llm_tokens": 0, "llm_requests": 0,
                "pdf_pages": 0, "api_calls": 0, "email_sent": 0,
            }
        return {
            "month": usage.month,
            "llm_tokens": usage.llm_tokens_in + usage.llm_tokens_out,
            "llm_requests": usage.llm_requests,
            "pdf_pages": usage.pdf_pages,
            "api_calls": usage.api_calls,
            "email_sent": usage.email_sent,
        }
