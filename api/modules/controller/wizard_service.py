"""Budget Wizard service — guided budget creation from knowledge base.

Loads sector-specific questions, benchmarks and generates a CE previsionale
from user answers collected via the multi-step wizard.
"""

import logging
import uuid
from datetime import date

from sqlalchemy import select, func, extract
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import Budget, Invoice

logger = logging.getLogger(__name__)

# ── Sector definitions (from knowledge base 02 + 04) ──

SECTORS: dict[str, dict] = {
    "it": {
        "label": "IT / Software / Consulenza",
        "ateco": ["62", "63", "70"],
        "ebitda_range": "20-35%",
        "cost_structure": {
            "personale": {"pct_min": 0.45, "pct_max": 0.55, "default": 0.50, "label": "Costo personale"},
            "servizi_esterni": {"pct_min": 0.10, "pct_max": 0.15, "default": 0.12, "label": "Servizi esterni / Freelance"},
            "cloud_licenze": {"pct_min": 0.03, "pct_max": 0.05, "default": 0.04, "label": "Cloud e licenze software"},
            "affitto": {"pct_min": 0.03, "pct_max": 0.05, "default": 0.04, "label": "Affitto ufficio"},
            "utenze": {"pct_min": 0.01, "pct_max": 0.02, "default": 0.015, "label": "Utenze e telefonia"},
            "marketing": {"pct_min": 0.02, "pct_max": 0.05, "default": 0.03, "label": "Marketing"},
            "ammortamenti": {"pct_min": 0.02, "pct_max": 0.04, "default": 0.03, "label": "Ammortamenti HW/SW"},
        },
        "questions": [
            {"id": "clienti_fissi", "text": "Quanti clienti fissi hai con contratti annuali? Valore totale?", "type": "text"},
            {"id": "nuovi_progetti", "text": "Prevedi nuovi progetti o clienti? Stima valore?", "type": "text"},
            {"id": "collaboratori", "text": "Usi collaboratori esterni/freelance? Budget annuo stimato?", "type": "currency"},
            {"id": "cloud", "text": "Licenze software e servizi cloud? (AWS, Azure, licenze...)", "type": "currency"},
            {"id": "formazione", "text": "Budget formazione e certificazioni?", "type": "currency"},
        ],
    },
    "ristorazione": {
        "label": "Ristorazione / Bar / Food",
        "ateco": ["55", "56"],
        "ebitda_range": "8-15%",
        "cost_structure": {
            "materie_prime": {"pct_min": 0.28, "pct_max": 0.35, "default": 0.32, "label": "Materie prime (food cost)"},
            "personale": {"pct_min": 0.30, "pct_max": 0.35, "default": 0.32, "label": "Costo personale"},
            "affitto": {"pct_min": 0.08, "pct_max": 0.12, "default": 0.10, "label": "Affitto locale"},
            "utenze": {"pct_min": 0.03, "pct_max": 0.05, "default": 0.04, "label": "Utenze"},
            "marketing": {"pct_min": 0.01, "pct_max": 0.03, "default": 0.02, "label": "Marketing"},
            "ammortamenti": {"pct_min": 0.02, "pct_max": 0.04, "default": 0.03, "label": "Ammortamenti"},
        },
        "questions": [
            {"id": "coperti", "text": "Quanti coperti medi al giorno?", "type": "number"},
            {"id": "scontrino", "text": "Scontrino medio?", "type": "currency"},
            {"id": "food_cost", "text": "Food cost: quanto spendi in materie prime rispetto all'incasso? (tipico 28-35%)", "type": "percentage"},
            {"id": "stagionalita", "text": "Hai stagionalita? (es. mare/montagna: estate piu forte?)", "type": "text"},
        ],
    },
    "commercio": {
        "label": "Commercio al dettaglio",
        "ateco": ["46", "47"],
        "ebitda_range": "5-10%",
        "cost_structure": {
            "acquisto_merci": {"pct_min": 0.55, "pct_max": 0.65, "default": 0.60, "label": "Acquisto merci"},
            "personale": {"pct_min": 0.12, "pct_max": 0.18, "default": 0.15, "label": "Costo personale"},
            "affitto": {"pct_min": 0.08, "pct_max": 0.12, "default": 0.10, "label": "Affitto negozio"},
            "utenze": {"pct_min": 0.02, "pct_max": 0.03, "default": 0.025, "label": "Utenze"},
            "trasporto": {"pct_min": 0.02, "pct_max": 0.05, "default": 0.03, "label": "Trasporto e logistica"},
        },
        "questions": [
            {"id": "tipo_merce", "text": "Cosa vendi? (margine diverso per elettronica vs abbigliamento vs alimentari)", "type": "text"},
            {"id": "ricarico", "text": "Ricarico medio sui prodotti? (markup %)", "type": "percentage"},
            {"id": "merce_annua", "text": "Quanto compri di merce all'anno?", "type": "currency"},
            {"id": "online", "text": "Vendi anche online? Costi piattaforma/spedizioni?", "type": "text"},
        ],
    },
    "manifattura": {
        "label": "Manifattura / Produzione",
        "ateco": ["10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23", "24", "25", "26", "27", "28", "29", "30", "31", "32", "33"],
        "ebitda_range": "10-18%",
        "cost_structure": {
            "materie_prime": {"pct_min": 0.35, "pct_max": 0.50, "default": 0.42, "label": "Materie prime"},
            "personale": {"pct_min": 0.20, "pct_max": 0.30, "default": 0.25, "label": "Costo personale"},
            "energia": {"pct_min": 0.05, "pct_max": 0.08, "default": 0.06, "label": "Energia"},
            "manutenzione": {"pct_min": 0.02, "pct_max": 0.04, "default": 0.03, "label": "Manutenzione"},
            "ammortamenti": {"pct_min": 0.05, "pct_max": 0.08, "default": 0.06, "label": "Ammortamenti"},
            "trasporto": {"pct_min": 0.02, "pct_max": 0.04, "default": 0.03, "label": "Trasporto"},
        },
        "questions": [
            {"id": "prodotto", "text": "Cosa produci? Materie prime principali?", "type": "text"},
            {"id": "costo_mp", "text": "Costo materie prime rispetto al fatturato?", "type": "percentage"},
            {"id": "macchinari", "text": "Hai macchinari? Valore e eta?", "type": "text"},
            {"id": "energia", "text": "Consumi energetici mensili?", "type": "currency"},
            {"id": "terzisti", "text": "Usi terzisti/subappalti?", "type": "text"},
        ],
    },
    "edilizia": {
        "label": "Costruzioni / Edilizia",
        "ateco": ["41", "42", "43"],
        "ebitda_range": "8-15%",
        "cost_structure": {
            "materiali": {"pct_min": 0.30, "pct_max": 0.40, "default": 0.35, "label": "Materiali"},
            "subappalti": {"pct_min": 0.15, "pct_max": 0.25, "default": 0.20, "label": "Subappalti"},
            "personale": {"pct_min": 0.20, "pct_max": 0.25, "default": 0.22, "label": "Costo personale"},
            "noleggio_mezzi": {"pct_min": 0.03, "pct_max": 0.06, "default": 0.04, "label": "Noleggio mezzi"},
            "ammortamenti": {"pct_min": 0.03, "pct_max": 0.05, "default": 0.04, "label": "Ammortamenti"},
        },
        "questions": [
            {"id": "tipo_lavori", "text": "Che tipo di lavori fai? (edilizia, impianti, finiture)", "type": "text"},
            {"id": "cantieri", "text": "Quanti cantieri prevedi quest'anno?", "type": "number"},
            {"id": "valore_cantiere", "text": "Valore medio per cantiere?", "type": "currency"},
            {"id": "subappalti", "text": "Usi subappaltatori? Quanto del fatturato?", "type": "percentage"},
            {"id": "mezzi", "text": "Noleggio mezzi o di proprieta?", "type": "text"},
        ],
    },
    "professionale": {
        "label": "Servizi professionali",
        "ateco": ["69", "71", "73", "74"],
        "ebitda_range": "25-40%",
        "cost_structure": {
            "personale": {"pct_min": 0.40, "pct_max": 0.50, "default": 0.45, "label": "Personale e collaboratori"},
            "affitto": {"pct_min": 0.05, "pct_max": 0.08, "default": 0.06, "label": "Affitto studio"},
            "software": {"pct_min": 0.03, "pct_max": 0.05, "default": 0.04, "label": "Software e strumenti"},
            "formazione": {"pct_min": 0.01, "pct_max": 0.03, "default": 0.02, "label": "Formazione"},
            "marketing": {"pct_min": 0.02, "pct_max": 0.05, "default": 0.03, "label": "Marketing"},
        },
        "questions": [
            {"id": "servizi", "text": "Che servizi offri? (legale, contabile, ingegneria, marketing)", "type": "text"},
            {"id": "tariffa", "text": "Tariffa oraria o a progetto?", "type": "text"},
            {"id": "ore_fatturabili", "text": "Ore fatturabili all'anno per professionista?", "type": "number"},
            {"id": "collaboratori", "text": "Hai collaboratori/associati?", "type": "text"},
            {"id": "albo", "text": "Iscrizione albo e assicurazione professionale?", "type": "currency"},
        ],
    },
    "ecommerce": {
        "label": "E-commerce",
        "ateco": ["47.91"],
        "ebitda_range": "5-15%",
        "cost_structure": {
            "acquisto_merci": {"pct_min": 0.40, "pct_max": 0.55, "default": 0.47, "label": "Acquisto merci"},
            "marketing": {"pct_min": 0.10, "pct_max": 0.20, "default": 0.15, "label": "Marketing / ADS"},
            "spedizioni": {"pct_min": 0.05, "pct_max": 0.10, "default": 0.07, "label": "Spedizioni"},
            "piattaforma": {"pct_min": 0.03, "pct_max": 0.08, "default": 0.05, "label": "Piattaforma e commissioni"},
            "personale": {"pct_min": 0.05, "pct_max": 0.12, "default": 0.08, "label": "Personale"},
            "magazzino": {"pct_min": 0.03, "pct_max": 0.05, "default": 0.04, "label": "Magazzino"},
        },
        "questions": [
            {"id": "piattaforma", "text": "Che piattaforma usi? (Shopify, WooCommerce, Amazon)", "type": "text"},
            {"id": "commissioni", "text": "Costo piattaforma/commissioni mensili?", "type": "currency"},
            {"id": "spedizione_media", "text": "Costo spedizioni medio per ordine?", "type": "currency"},
            {"id": "ads_budget", "text": "Budget marketing/advertising? (Google Ads, Meta)", "type": "currency"},
            {"id": "resi", "text": "Gestisci resi? Tasso di reso?", "type": "percentage"},
        ],
    },
    "trasporto": {
        "label": "Trasporto / Logistica",
        "ateco": ["49"],
        "ebitda_range": "5-10%",
        "cost_structure": {
            "carburante": {"pct_min": 0.25, "pct_max": 0.35, "default": 0.30, "label": "Carburante"},
            "personale": {"pct_min": 0.25, "pct_max": 0.30, "default": 0.27, "label": "Personale (autisti)"},
            "ammortamento_mezzi": {"pct_min": 0.10, "pct_max": 0.15, "default": 0.12, "label": "Ammortamento/noleggio mezzi"},
            "assicurazioni": {"pct_min": 0.05, "pct_max": 0.08, "default": 0.06, "label": "Assicurazioni"},
            "manutenzione": {"pct_min": 0.05, "pct_max": 0.08, "default": 0.06, "label": "Manutenzione"},
        },
        "questions": [
            {"id": "mezzi", "text": "Quanti mezzi hai? Tipo (furgoni, bilici)?", "type": "text"},
            {"id": "km_annui", "text": "Km percorsi all'anno? Consumo carburante?", "type": "text"},
            {"id": "proprieta", "text": "Mezzi di proprieta o noleggio?", "type": "text"},
            {"id": "autisti", "text": "Quanti autisti?", "type": "number"},
            {"id": "pedaggi", "text": "Pedaggi autostradali annui?", "type": "currency"},
        ],
    },
}


def get_sectors_list() -> list[dict]:
    """Return list of available sectors for the wizard."""
    return [
        {"id": sid, "label": s["label"], "ebitda_range": s["ebitda_range"]}
        for sid, s in SECTORS.items()
    ]


def get_sector_questions(sector_id: str) -> dict:
    """Return questions and cost structure for a sector."""
    sector = SECTORS.get(sector_id)
    if not sector:
        return {"error": f"Settore '{sector_id}' non trovato"}
    return {
        "sector_id": sector_id,
        "label": sector["label"],
        "ebitda_range": sector["ebitda_range"],
        "questions": sector["questions"],
        "cost_structure": {
            k: {"label": v["label"], "pct_min": v["pct_min"], "pct_max": v["pct_max"], "default": v["default"]}
            for k, v in sector["cost_structure"].items()
        },
    }


def generate_ce_preview(
    sector_id: str,
    fatturato: float,
    n_dipendenti: int,
    ral_media: float,
    year: int,
    overrides: dict | None = None,
) -> dict:
    """Generate Conto Economico previsionale from wizard inputs.

    Args:
        sector_id: Sector identifier (e.g., "it", "ristorazione")
        fatturato: Expected annual revenue
        n_dipendenti: Number of employees
        ral_media: Average gross salary (RAL)
        year: Budget year
        overrides: Optional dict of cost_category -> amount (user adjustments)

    Returns:
        CE previsionale with line items, totals, EBITDA, and benchmark comparison.
    """
    sector = SECTORS.get(sector_id)
    if not sector:
        return {"error": f"Settore '{sector_id}' non trovato"}

    overrides = overrides or {}

    # ── Calculate costs from sector defaults ──
    cost_lines = []
    total_costi = 0

    for cat_id, cat_info in sector["cost_structure"].items():
        if cat_id == "personale" and n_dipendenti > 0:
            # Calculate from RAL: RAL + INPS 30% + INAIL 1% + TFR 6.91%
            costo_per_dip = ral_media * (1 + 0.30 + 0.01 + 0.0691)
            amount = round(costo_per_dip * n_dipendenti, 2)
        elif cat_id in overrides:
            amount = round(float(overrides[cat_id]), 2)
        else:
            amount = round(fatturato * cat_info["default"], 2)

        pct_on_revenue = round((amount / fatturato * 100), 1) if fatturato > 0 else 0
        benchmark_min = round(cat_info["pct_min"] * 100, 1)
        benchmark_max = round(cat_info["pct_max"] * 100, 1)

        # Flag anomalies
        severity = "ok"
        if pct_on_revenue > benchmark_max * 1.1:
            severity = "high"
        elif pct_on_revenue < benchmark_min * 0.9:
            severity = "low"

        cost_lines.append({
            "category": cat_id,
            "label": cat_info["label"],
            "amount": amount,
            "monthly": round(amount / 12, 2),
            "pct_on_revenue": pct_on_revenue,
            "benchmark_min": benchmark_min,
            "benchmark_max": benchmark_max,
            "severity": severity,
        })
        total_costi += amount

    # ── IRES + IRAP estimate ──
    ebitda = round(fatturato - total_costi, 2)
    ebitda_pct = round((ebitda / fatturato * 100), 1) if fatturato > 0 else 0

    # IRAP base: value of production (ricavi - costi + personale)
    personale_amount = next((c["amount"] for c in cost_lines if c["category"] == "personale"), 0)
    irap_base = fatturato - total_costi + personale_amount
    irap = round(max(0, irap_base) * 0.039, 2)
    ires = round(max(0, ebitda) * 0.24, 2)
    imposte = round(ires + irap, 2)

    utile_netto = round(ebitda - imposte, 2)

    # ── Benchmark comparison ──
    ebitda_range = sector["ebitda_range"]
    range_parts = ebitda_range.replace("%", "").split("-")
    ebitda_min = float(range_parts[0])
    ebitda_max = float(range_parts[1])

    if ebitda_pct < ebitda_min:
        ebitda_verdict = "below"
        ebitda_advice = f"Il tuo EBITDA ({ebitda_pct}%) e sotto la media del settore ({ebitda_range}). Valuta dove ridurre i costi."
    elif ebitda_pct > ebitda_max:
        ebitda_verdict = "above"
        ebitda_advice = f"Ottimo! Il tuo EBITDA ({ebitda_pct}%) e sopra la media del settore ({ebitda_range})."
    else:
        ebitda_verdict = "ok"
        ebitda_advice = f"Il tuo EBITDA ({ebitda_pct}%) e nella media del settore ({ebitda_range})."

    # ── Build budget lines for saving ──
    budget_lines = [
        {"category": "ricavi", "annual_proposed": fatturato, "monthly_proposed": round(fatturato / 12, 2)},
    ]
    for cl in cost_lines:
        budget_lines.append({
            "category": cl["category"],
            "annual_proposed": cl["amount"],
            "monthly_proposed": cl["monthly"],
        })

    return {
        "year": year,
        "sector_id": sector_id,
        "sector_label": sector["label"],
        "ricavi": fatturato,
        "cost_lines": cost_lines,
        "total_costi": round(total_costi, 2),
        "ebitda": ebitda,
        "ebitda_pct": ebitda_pct,
        "ebitda_benchmark": ebitda_range,
        "ebitda_verdict": ebitda_verdict,
        "ebitda_advice": ebitda_advice,
        "ires": ires,
        "irap": irap,
        "imposte": imposte,
        "utile_netto": utile_netto,
        "n_dipendenti": n_dipendenti,
        "ral_media": ral_media,
        "budget_lines": budget_lines,
    }


async def save_wizard_budget(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    year: int,
    budget_lines: list[dict],
) -> dict:
    """Save budget from wizard CE preview."""
    # Delete existing budget for this year
    from sqlalchemy import delete
    await db.execute(
        delete(Budget).where(
            Budget.tenant_id == tenant_id,
            Budget.year == year,
        )
    )

    saved = 0
    for line in budget_lines:
        category = line["category"]
        monthly = line.get("monthly_proposed", 0)
        for month in range(1, 13):
            budget = Budget(
                tenant_id=tenant_id,
                year=year,
                month=month,
                category=category,
                budget_amount=round(float(monthly), 2),
            )
            db.add(budget)
            saved += 1

    await db.flush()
    return {
        "year": year,
        "lines_saved": saved,
        "categories": len(budget_lines),
        "message": f"Budget {year} salvato: {len(budget_lines)} categorie x 12 mesi = {saved} righe",
    }


async def check_historical_data(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    year: int,
) -> dict:
    """Check if tenant has historical invoice data for budget generation."""
    prev_year = year - 1
    count = await db.scalar(
        select(func.count(Invoice.id)).where(
            Invoice.tenant_id == tenant_id,
            Invoice.data_fattura >= date(prev_year, 1, 1),
            Invoice.data_fattura < date(prev_year + 1, 1, 1),
        )
    ) or 0

    fatturato = 0.0
    if count > 0:
        result = await db.scalar(
            select(func.coalesce(func.sum(Invoice.importo_netto), 0)).where(
                Invoice.tenant_id == tenant_id,
                Invoice.type == "attiva",
                extract("year", Invoice.data_fattura) == prev_year,
            )
        )
        fatturato = float(result or 0)

    return {
        "has_history": count > 0,
        "prev_year": prev_year,
        "invoice_count": count,
        "fatturato_prev": round(fatturato, 2),
    }
