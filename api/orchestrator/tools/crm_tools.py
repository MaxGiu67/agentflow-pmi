"""CRM deal/contact/pipeline tool handlers — uses internal CRM (not Odoo).

ADR-009: CRM interno PostgreSQL. Odoo è deprecato.
"""

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from api.modules.crm.service import CRMService

logger = logging.getLogger(__name__)


async def crm_pipeline_summary_handler(
    db: AsyncSession, tenant_id: uuid.UUID, **kwargs: object,
) -> dict:
    """Riepilogo pipeline commerciale dal CRM interno."""
    svc = CRMService(db)
    try:
        summary = await svc.get_pipeline_summary(tenant_id)
        return summary
    except Exception as e:
        logger.error("CRM pipeline summary error: %s", e)
        return {"error": f"Errore CRM: {e}"}


async def crm_list_deals_handler(
    db: AsyncSession, tenant_id: uuid.UUID, **kwargs: object,
) -> dict:
    """Elenca deal dalla pipeline CRM interna."""
    svc = CRMService(db)
    stage = str(kwargs.get("stage", ""))
    deal_type = str(kwargs.get("deal_type", ""))
    try:
        result = await svc.list_deals(tenant_id, stage=stage, deal_type=deal_type)
        return result
    except Exception as e:
        logger.error("CRM list deals error: %s", e)
        return {"error": f"Errore CRM: {e}"}


async def crm_list_contacts_handler(
    db: AsyncSession, tenant_id: uuid.UUID, **kwargs: object,
) -> dict:
    """Elenca contatti dal CRM interno."""
    svc = CRMService(db)
    search = str(kwargs.get("search", ""))
    try:
        result = await svc.list_contacts(tenant_id, search=search)
        return result
    except Exception as e:
        logger.error("CRM list contacts error: %s", e)
        return {"error": f"Errore CRM: {e}"}


async def crm_won_deals_handler(
    db: AsyncSession, tenant_id: uuid.UUID, **kwargs: object,
) -> dict:
    """Deal vinti dal CRM interno."""
    svc = CRMService(db)
    try:
        result = await svc.get_won_deals(tenant_id)
        return result
    except Exception as e:
        logger.error("CRM won deals error: %s", e)
        return {"error": f"Errore CRM: {e}"}


async def crm_pending_orders_handler(
    db: AsyncSession, tenant_id: uuid.UUID, **kwargs: object,
) -> dict:
    """Ordini in attesa dal CRM interno."""
    svc = CRMService(db)
    try:
        result = await svc.get_pending_orders(tenant_id)
        return result
    except Exception as e:
        logger.error("CRM pending orders error: %s", e)
        return {"error": f"Errore CRM: {e}"}


async def crm_analytics_handler(
    db: AsyncSession, tenant_id: uuid.UUID, **kwargs: object,
) -> dict:
    """Analytics pipeline: conversion rate, won/lost, weighted value."""
    svc = CRMService(db)
    try:
        result = await svc.get_pipeline_analytics(tenant_id)
        return result
    except Exception as e:
        logger.error("CRM analytics error: %s", e)
        return {"error": f"Errore CRM: {e}"}


# ── Tool definitions for orchestrator registry ──

CRM_TOOL_DEFINITIONS = [
    {
        "name": "crm_pipeline_summary",
        "handler": crm_pipeline_summary_handler,
        "description": (
            "Riepilogo pipeline commerciale: deal per fase, valore pesato, "
            "win rate. Usa per overview vendite."
        ),
        "parameters": {},
    },
    {
        "name": "crm_list_deals",
        "handler": crm_list_deals_handler,
        "description": (
            "Elenca i deal/opportunita dalla pipeline CRM. "
            "Filtra per fase o tipo."
        ),
        "parameters": {
            "stage": {"type": "string", "description": "Filtra per fase pipeline"},
            "deal_type": {"type": "string", "description": "Filtra per tipo (T&M, fixed, spot)"},
        },
    },
    {
        "name": "crm_list_contacts",
        "handler": crm_list_contacts_handler,
        "description": (
            "Elenca i contatti/clienti dal CRM. "
            "Cerca per nome, email, azienda."
        ),
        "parameters": {
            "search": {"type": "string", "description": "Termine di ricerca"},
        },
    },
    {
        "name": "crm_won_deals",
        "handler": crm_won_deals_handler,
        "description": "Deal vinti/confermati. Per vedere le commesse attive.",
        "parameters": {},
    },
    {
        "name": "crm_pending_orders",
        "handler": crm_pending_orders_handler,
        "description": "Ordini in attesa di conferma.",
        "parameters": {},
    },
    {
        "name": "crm_analytics",
        "handler": crm_analytics_handler,
        "description": "Analytics pipeline: conversion rate, won/lost ratio, valore pesato, tempo medio per fase.",
        "parameters": {},
    },
]
