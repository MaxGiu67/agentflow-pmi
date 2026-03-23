"""Depreciation calculation engine (US-31, US-32).

Implements Italian ministerial depreciation rates and pro-rata rules.
"""

from datetime import date

# Ministerial depreciation rates by category (%)
MINISTERIAL_RATES: dict[str, float] = {
    "Attrezzature informatiche": 20.0,
    "Mobili": 12.0,
    "Automezzi": 25.0,
    "Fabbricati": 3.0,
    "Impianti": 10.0,
    "Macchinari": 15.0,
    "Attrezzature": 15.0,
    "Software": 20.0,
    "Brevetti": 20.0,
}

# Default asset capitalization threshold (from fiscal rules)
DEFAULT_CAPITALIZATION_THRESHOLD = 516.46


def get_depreciation_rate(category: str) -> float | None:
    """Get ministerial depreciation rate for a category.

    Returns rate as percentage (e.g. 20.0 for 20%) or None if not found.
    """
    return MINISTERIAL_RATES.get(category)


def suggest_categories(description: str, top_n: int = 3) -> list[dict]:
    """AC-31.3: Suggest top N categories based on description keywords.

    Returns list of {category, rate, score} dicts.
    """
    desc_lower = description.lower()

    keyword_map: dict[str, list[str]] = {
        "Attrezzature informatiche": [
            "computer", "notebook", "laptop", "server", "pc",
            "stampante", "monitor", "tablet", "informatica",
        ],
        "Mobili": [
            "scrivania", "sedia", "armadio", "scaffale",
            "mobile", "tavolo", "poltrona", "arredo",
        ],
        "Automezzi": [
            "auto", "furgone", "camion", "veicolo",
            "automobile", "moto", "scooter",
        ],
        "Fabbricati": [
            "immobile", "fabbricato", "edificio", "capannone",
            "locale", "ufficio",
        ],
        "Impianti": [
            "impianto", "climatizzazione", "elettrico",
            "idraulico", "riscaldamento",
        ],
        "Macchinari": [
            "macchinario", "macchina", "tornio", "fresa",
            "pressa",
        ],
        "Attrezzature": [
            "attrezzatura", "utensile", "strumento",
        ],
        "Software": [
            "software", "licenza", "programma", "applicazione",
        ],
        "Brevetti": [
            "brevetto", "marchio", "proprietà intellettuale",
        ],
    }

    scores: list[tuple[str, float, float]] = []
    for cat, keywords in keyword_map.items():
        score = 0.0
        for kw in keywords:
            if kw in desc_lower:
                score += 1.0
        if score > 0:
            rate = MINISTERIAL_RATES[cat]
            scores.append((cat, rate, score))

    # Sort by score descending
    scores.sort(key=lambda x: x[2], reverse=True)

    # Always return at least top_n, fill with defaults
    results = [
        {"category": cat, "rate": rate, "score": score}
        for cat, rate, score in scores[:top_n]
    ]

    if len(results) < top_n:
        used = {r["category"] for r in results}
        for cat, rate in MINISTERIAL_RATES.items():
            if cat not in used and len(results) < top_n:
                results.append({"category": cat, "rate": rate, "score": 0.0})

    return results


def calculate_annual_depreciation(
    depreciable_amount: float,
    rate: float,
    purchase_date: date,
    fiscal_year: int,
    accumulated: float = 0.0,
) -> float:
    """Calculate annual depreciation amount.

    Pro-rata first year: 50% if purchased in H2 (July-December).
    Cannot exceed residual value.
    """
    residual = depreciable_amount - accumulated
    if residual <= 0:
        return 0.0

    annual = round(depreciable_amount * (rate / 100), 2)

    # First year pro-rata: 50% if purchased in second half
    if purchase_date.year == fiscal_year and purchase_date.month >= 7:
        annual = round(annual * 0.5, 2)

    # Cannot depreciate more than residual
    if annual > residual:
        annual = round(residual, 2)

    return annual


def calculate_pro_rata_depreciation(
    depreciable_amount: float,
    rate: float,
    disposal_date: date,
    accumulated: float = 0.0,
) -> float:
    """AC-32.3: Calculate pro-rata depreciation for disposal mid-year.

    Uses days elapsed in the year / total days in year.
    """
    residual = depreciable_amount - accumulated
    if residual <= 0:
        return 0.0

    annual = round(depreciable_amount * (rate / 100), 2)

    year_start = date(disposal_date.year, 1, 1)
    year_end = date(disposal_date.year, 12, 31)
    days_total = (year_end - year_start).days + 1
    days_elapsed = (disposal_date - year_start).days + 1

    pro_rata = round(annual * (days_elapsed / days_total), 2)

    if pro_rata > residual:
        pro_rata = round(residual, 2)

    return pro_rata
