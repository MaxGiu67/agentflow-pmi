"""Offer generation tools for Sales Agent v2 — wired to real services (Sprint 46-47).

Combines CRM deal data with the python-docx offer template engine
to generate Word documents and calculate margins.
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any

from langchain_core.tools import tool

from api.agents.tools.crm_tools import get_tenant_id
from api.agents.tools.offer_generator import generate_offer_document, KNOWN_PLACEHOLDERS
from api.db.session import async_session_factory
from api.modules.crm.service import CRMService

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("generated_offers")


@tool
async def generate_offer_doc(deal_id: str, offer_type: str = "tm") -> dict:
    """Generate a Word (.docx) offer document from deal data. HIGH RISK.

    offer_type: 'tm' for Time & Material, 'corpo' for fixed-price project.
    Pulls deal info from CRM and fills the template placeholders.
    Returns the file path of the generated document.
    """
    tenant_id = get_tenant_id()
    async with async_session_factory() as db:
        svc = CRMService(db)
        deal = await svc.get_deal(uuid.UUID(deal_id), tenant_id)

    if not deal:
        return {"error": f"Deal {deal_id} non trovato"}

    # Build replacements from deal data
    replacements: dict[str, str] = {}

    # Company / Contact info
    company_name = deal.get("company_name") or deal.get("portal_customer_name") or ""
    replacements["NOME_CLIENTE"] = company_name
    replacements["TITOLO_OFFERTA"] = deal.get("name", "")

    # Contact info (if available)
    contact_name = deal.get("contact_name", "")
    if contact_name:
        replacements["REFERENTE_CLIENTE"] = contact_name

    # Revenue / rate info
    revenue = deal.get("expected_revenue", 0)
    daily_rate = deal.get("daily_rate", 0)
    estimated_days = deal.get("estimated_days", 0)

    if offer_type == "tm":
        replacements["MODALITA_CONTRATTUALE"] = (
            f"Time & Material — Tariffa giornaliera: EUR {daily_rate:.0f}/gg, "
            f"Stima impegno: {estimated_days} gg, "
            f"Valore stimato: EUR {revenue:,.2f}"
        )
    else:
        replacements["MODALITA_CONTRATTUALE"] = (
            f"Progetto a corpo — Importo complessivo: EUR {revenue:,.2f}, "
            f"Stima impegno: {estimated_days} giornate"
        )

    # Technology
    tech = deal.get("technology", "")
    if tech:
        replacements["TECNOLOGIE_INTRO"] = f"Stack tecnologico: {tech}"

    # Generate filename
    protocol = replacements.get("PROTOCOLLO", f"deal_{deal_id[:8]}")
    output_filename = f"Offerta_{protocol.replace('.', '_')}_{offer_type}.docx"

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / output_filename

    result = generate_offer_document(replacements, output_path)
    result["deal_id"] = deal_id
    result["offer_type"] = offer_type
    result["risk"] = "high"
    result["requires_confirmation"] = True
    return result


@tool
async def calc_margin(revenue: float, daily_costs: list[float], days: int) -> dict:
    """Calculate deal margin for one or more resources.

    Args:
        revenue: total deal revenue (EUR)
        daily_costs: list of daily cost per resource (EUR)
        days: estimated working days

    Returns margin percentage, absolute margin, and warnings if margin < 15%.
    """
    if days <= 0:
        return {"error": "days deve essere positivo"}
    if not daily_costs:
        return {"error": "Fornire almeno un costo giornaliero"}

    total_cost = sum(daily_costs) * days
    margin_abs = revenue - total_cost
    margin_pct = round((margin_abs / revenue * 100) if revenue > 0 else 0, 1)

    avg_daily_cost = sum(daily_costs) / len(daily_costs)
    implied_daily_rate = revenue / days if days > 0 else 0

    result: dict[str, Any] = {
        "revenue": revenue,
        "total_cost": round(total_cost, 2),
        "margin_abs": round(margin_abs, 2),
        "margin_pct": margin_pct,
        "days": days,
        "num_resources": len(daily_costs),
        "avg_daily_cost": round(avg_daily_cost, 2),
        "implied_daily_rate": round(implied_daily_rate, 2),
    }

    if margin_pct < 15:
        result["warning"] = (
            f"Margine sotto soglia ({margin_pct}%). "
            f"Margine minimo consigliato: 15%. "
            f"Rivedi la tariffa o chiedi approvazione direzione."
        )
    elif margin_pct < 25:
        result["note"] = f"Margine accettabile ({margin_pct}%) ma sotto la media aziendale (25%)."

    return result


# ── Tool Registry ─────────────────────────────────────────

OFFER_TOOLS = [
    generate_offer_doc,
    calc_margin,
]
