"""CRM tools for Sales Agent v2 — wired to real CRMService (Sprint 46-47).

All tools are async and use the async_session_factory to obtain a DB session.
The tenant_id is injected via tool context (set by the agent before invocation).
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from langchain_core.tools import tool

from api.db.session import async_session_factory
from api.modules.crm.service import CRMService

logger = logging.getLogger(__name__)

# Module-level tenant context — set by the agent before invoking tools.
# This avoids passing tenant_id through every tool call.
_tool_context: dict[str, Any] = {}


def set_tool_context(tenant_id: str, user_email: str = "", **extra: Any) -> None:
    """Set the tenant context for CRM tools. Called by the agent orchestrator."""
    _tool_context["tenant_id"] = tenant_id
    _tool_context["user_email"] = user_email
    _tool_context.update(extra)


def get_tenant_id() -> uuid.UUID:
    """Get current tenant_id from tool context."""
    tid = _tool_context.get("tenant_id", "")
    if not tid:
        raise ValueError("tenant_id not set in tool context. Call set_tool_context() first.")
    return uuid.UUID(tid) if isinstance(tid, str) else tid


# ── CRM Core Tools ────────────────────────────────────────


@tool
async def crm_get_deal(deal_id: str) -> dict:
    """Get deal details by ID. Returns company, product, stage, revenue, activities."""
    tenant_id = get_tenant_id()
    async with async_session_factory() as db:
        svc = CRMService(db)
        deal = await svc.get_deal(uuid.UUID(deal_id), tenant_id)
        if not deal:
            return {"error": f"Deal {deal_id} non trovato"}
        # Also fetch recent activities
        activities = await svc.list_activities(tenant_id, deal_id=uuid.UUID(deal_id), limit=5)
        deal["recent_activities"] = activities
        return deal


@tool
async def crm_list_deals(stage: str = "", deal_type: str = "", limit: int = 20) -> dict:
    """List deals with optional filters by stage name or deal_type. Returns list of deals."""
    tenant_id = get_tenant_id()
    async with async_session_factory() as db:
        svc = CRMService(db)
        result = await svc.list_deals(tenant_id, stage=stage, deal_type=deal_type, limit=limit)
        return result


@tool
async def crm_update_deal(deal_id: str, fields: dict) -> dict:
    """Update deal fields (name, expected_revenue, daily_rate, estimated_days, technology, probability).
    Pass a dict of field names to new values."""
    tenant_id = get_tenant_id()
    async with async_session_factory() as db:
        svc = CRMService(db)
        result = await svc.update_deal(uuid.UUID(deal_id), tenant_id, fields)
        if not result:
            return {"error": f"Deal {deal_id} non trovato o aggiornamento fallito"}
        await db.commit()
        return result


@tool
async def crm_move_stage(deal_id: str, stage_name: str) -> dict:
    """Move deal to a pipeline stage by name. HIGH RISK: changes deal status.
    Returns updated deal with new stage."""
    tenant_id = get_tenant_id()
    async with async_session_factory() as db:
        svc = CRMService(db)
        # Find stage by name
        stages = await svc.get_stages(tenant_id)
        target = None
        for s in stages:
            if s["name"].lower() == stage_name.lower():
                target = s
                break
        if not target:
            return {"error": f"Fase '{stage_name}' non trovata. Fasi disponibili: {[s['name'] for s in stages]}"}

        result = await svc.update_deal(uuid.UUID(deal_id), tenant_id, {"stage_id": target["id"]})
        if not result:
            return {"error": f"Deal {deal_id} non trovato"}
        await db.commit()
        return {"status": "moved", "deal": result, "new_stage": target["name"]}


@tool
async def crm_pipeline_summary(pipeline_type: str = "") -> dict:
    """Get pipeline summary: deals per stage, total value, weighted value.
    Returns total_deals, total_value, by_stage breakdown."""
    tenant_id = get_tenant_id()
    async with async_session_factory() as db:
        svc = CRMService(db)
        summary = await svc.get_pipeline_summary(tenant_id)
        # Also get analytics if available
        try:
            analytics = await svc.get_pipeline_analytics(tenant_id)
            summary["weighted_value"] = analytics.get("weighted_value", 0)
            summary["won_count"] = analytics.get("won_count", 0)
            summary["lost_count"] = analytics.get("lost_count", 0)
            summary["conversion_rate"] = analytics.get("conversion_rate", 0)
        except Exception:
            pass
        return summary


@tool
async def crm_list_contacts(search: str = "") -> dict:
    """Search CRM contacts by name, email, or VAT number. Returns list of contacts."""
    tenant_id = get_tenant_id()
    async with async_session_factory() as db:
        svc = CRMService(db)
        result = await svc.list_contacts(tenant_id, search=search)
        return result


@tool
async def crm_create_activity(
    deal_id: str,
    activity_type: str,
    subject: str,
    description: str = "",
) -> dict:
    """Create a CRM activity on a deal.
    activity_type: call, video_call, meeting, email, task, note.
    Returns the created activity."""
    tenant_id = get_tenant_id()
    async with async_session_factory() as db:
        svc = CRMService(db)
        data = {
            "deal_id": deal_id,
            "type": activity_type,
            "subject": subject,
            "description": description,
        }
        result = await svc.create_activity(tenant_id, data)
        await db.commit()
        return result


@tool
async def crm_get_activities(deal_id: str) -> list:
    """Get all activities for a deal, ordered by most recent first."""
    tenant_id = get_tenant_id()
    async with async_session_factory() as db:
        svc = CRMService(db)
        return await svc.list_activities(tenant_id, deal_id=uuid.UUID(deal_id))


# ── Tool Registry ─────────────────────────────────────────

CRM_TOOLS = [
    crm_get_deal,
    crm_list_deals,
    crm_update_deal,
    crm_move_stage,
    crm_pipeline_summary,
    crm_list_contacts,
    crm_create_activity,
    crm_get_activities,
]
