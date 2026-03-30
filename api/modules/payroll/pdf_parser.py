"""Parser for Riepilogo Paghe e Contributi PDF (US-44).

Extracts payroll line items (Dare/Avere) from the standard payroll summary PDF.
Handles the columnar layout: Description | Importo D/A | DARE | AVERE
"""

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

MONTH_MAP = {
    "gennaio": 1, "febbraio": 2, "marzo": 3, "aprile": 4,
    "maggio": 5, "giugno": 6, "luglio": 7, "agosto": 8,
    "settembre": 9, "ottobre": 10, "novembre": 11, "dicembre": 12,
}


@dataclass
class PayrollLine:
    descrizione: str
    importo: float
    dare_avere: str  # "D" or "A"
    sezione: str
    conto_suggerito: str = ""


@dataclass
class PayrollSummary:
    azienda: str = ""
    mese: int = 0
    anno: int = 0
    linee: list[PayrollLine] = field(default_factory=list)
    totale_dare: float = 0.0
    totale_avere: float = 0.0
    netto_in_busta: float = 0.0
    salari_stipendi: float = 0.0
    contributi_inps_azienda: float = 0.0
    saldo_dm10: float = 0.0
    irpef: float = 0.0
    tfr: float = 0.0
    inail: float = 0.0


# Voci → Conti contabili mapping
CONTO_MAP = {
    "salari": "costi_personale_salari",
    "stipendi": "costi_personale_stipendi",
    "salari & stipendi": "costi_personale_stipendi",
    "trasferte": "costi_personale_trasferte",
    "rimborsi chilometrici": "costi_personale_rimborsi",
    "rimborso spese": "costi_personale_rimborsi",
    "buoni pasto": "costi_personale_buoni_pasto",
    "fondo tfr": "tfr_accantonamento",
    "tfr dell'anno": "tfr_accantonamento",
    "permessi legge 104": "costi_personale_altri",
    "erogazioni c/inps": "crediti_vs_inps",
    "contributi inps c/ditta": "contributi_inps_azienda",
    "contributi inps c/dipendente": "debiti_vs_inps",
    "contributo aspi": "contributi_inps_azienda",
    "irpef": "debiti_vs_erario_irpef",
    "addizionale irpef": "debiti_vs_erario_irpef",
    "irpef su tfr": "debiti_vs_erario_irpef",
    "irpef co.co.co": "debiti_vs_erario_irpef",
    "contributi inail": "debiti_vs_inail",
    "contributo inail": "debiti_vs_inail",
    "previdenza complementare": "debiti_vs_fondi_pensione",
    "c/dipe fondo prev": "debiti_vs_fondi_pensione",
    "c/azie fondo prev": "costi_personale_prev_compl",
    "quota tfr x fondo": "debiti_vs_fondi_pensione",
    "sanimpresa": "debiti_vs_enti_bilaterali",
    "est pagamento": "debiti_vs_enti_bilaterali",
    "trattamento integrativo": "crediti_trattamento_integrativo",
    "arrotondamento": "arrotondamenti_personale",
    "contributi c/azie": "contributi_cococo_azienda",
    "contributi c/collaboratori": "debiti_vs_inps_cococo",
    "imposta sostit": "debiti_vs_erario_imposta_sost",
    "netto in busta": "debiti_vs_dipendenti",
}


def _parse_amount(text: str) -> float:
    text = text.strip().replace(".", "").replace(",", ".")
    try:
        return abs(float(text))
    except ValueError:
        return 0.0


def _match_conto(descrizione: str) -> str:
    desc_lower = descrizione.lower().strip()
    for key, conto in CONTO_MAP.items():
        if key in desc_lower:
            return conto
    return "costi_personale_altri"


def parse_payroll_text(text: str) -> PayrollSummary:
    """Parse the pdftotext -layout output of a Riepilogo Paghe PDF."""
    summary = PayrollSummary()

    # Extract month/year
    header_match = re.search(r"mese\s+di\s+(\w+)\s+(\d{4})", text, re.IGNORECASE)
    if header_match:
        summary.mese = MONTH_MAP.get(header_match.group(1).lower(), 0)
        summary.anno = int(header_match.group(2))

    # Extract azienda
    az_match = re.search(r"Azienda/Fil\.\s+\d+\s+(.+?)(?:\n|$)", text)
    if az_match:
        summary.azienda = az_match.group(1).strip()

    current_section = "retribuzioni"
    section_markers = {
        "RETRIBUZIONI E ALTRE COMPETENZE": "retribuzioni",
        "CONTRIBUTI INPS": "contributi_inps",
        "TRATTENUTE Co.Co.Co": "cococo",
        "ALTRI VERSAMENTI": "altri_versamenti",
        "TRATTENUTE FISCALI": "irpef_versamento",
        "CREDITI E BONUS FISCALI": "crediti_bonus",
        "CREDITI IRPEF": "crediti_irpef",
    }

    lines = text.split("\n")
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("Cod.Conto"):
            continue

        # Section change
        for marker, section in section_markers.items():
            if marker in stripped.upper():
                current_section = section
                break

        # Pattern 1: "Description    1.234,56   D" — single entry with D/A flag
        m1 = re.search(r"^[_\s]*(.+?)\s{2,}([\d.]+,\d{2})\s+([DA])\s*$", line)
        if m1:
            desc = m1.group(1).strip()
            importo = _parse_amount(m1.group(2))
            da = m1.group(3)
            if importo > 0:
                summary.linee.append(PayrollLine(
                    descrizione=desc, importo=importo, dare_avere=da,
                    sezione=current_section, conto_suggerito=_match_conto(desc),
                ))
            continue

        # Pattern 2: "Description         123.456,78" — value in DARE column (right-aligned ~col 80-95)
        # Pattern 3: "Description                                    123.456,78" — value in AVERE column (~col 95+)
        # Detect by position: DARE column is around position 70-90, AVERE is 90+
        m2 = re.search(r"^[_\s]*(.+?)\s{3,}([\d.]+,\d{2})\s*$", line)
        if m2:
            desc = m2.group(1).strip()
            val = _parse_amount(m2.group(2))
            if val <= 0 or len(desc) < 3:
                continue

            # Determine DARE vs AVERE by column position
            val_start = line.rfind(m2.group(2))
            is_avere = val_start > 85  # AVERE column is further right

            desc_lower = desc.lower()

            # Known summary lines — extract key totals
            if "netto in busta" in desc_lower:
                summary.netto_in_busta = val
                summary.linee.append(PayrollLine(
                    descrizione=desc, importo=val, dare_avere="A",
                    sezione="retribuzioni", conto_suggerito="debiti_vs_dipendenti",
                ))
                continue
            if "salari" in desc_lower and "stipendi" in desc_lower:
                summary.salari_stipendi = val
                summary.linee.append(PayrollLine(
                    descrizione=desc, importo=val, dare_avere="D",
                    sezione="retribuzioni", conto_suggerito="costi_personale_stipendi",
                ))
                continue
            if "saldo" in desc_lower and "dm10" in desc_lower:
                summary.saldo_dm10 = val
                continue
            if "totale irpef" in desc_lower:
                summary.irpef = val
                continue
            if "totale generale" in desc_lower:
                # This line has both dare and avere
                continue

            # Generic summary line — determine D/A by section context
            da = "A" if is_avere else "D"

            # Specific patterns
            if any(k in desc_lower for k in ["ritenute previdenziali", "trattenute fiscali", "altre trattenute", "totale trattenute"]):
                da = "A"
            elif any(k in desc_lower for k in ["contributi", "fondo tfr", "tfr dell", "trasferte", "rimborso", "buoni"]):
                if current_section == "retribuzioni":
                    da = "D"  # costs are in DARE
                elif current_section in ("contributi_inps", "cococo", "altri_versamenti"):
                    da = "D"

            summary.linee.append(PayrollLine(
                descrizione=desc, importo=val, dare_avere=da,
                sezione=current_section, conto_suggerito=_match_conto(desc),
            ))

    # Match TOTALE GENERALE line (two amounts on same line)
    tg_match = re.search(r"TOTALE GENERALE\s+([\d.]+,\d{2})\s+([\d.]+,\d{2})", text)
    if tg_match:
        summary.totale_dare = _parse_amount(tg_match.group(1))
        summary.totale_avere = _parse_amount(tg_match.group(2))
    else:
        # Calculate from lines
        summary.totale_dare = sum(ln.importo for ln in summary.linee if ln.dare_avere == "D")
        summary.totale_avere = sum(ln.importo for ln in summary.linee if ln.dare_avere == "A")

    return summary


def payroll_to_journal_lines(summary: PayrollSummary) -> list[dict]:
    """Convert parsed payroll into journal entry lines (partita doppia)."""
    account_totals: dict[str, dict] = {}

    for line in summary.linee:
        conto = line.conto_suggerito
        if conto not in account_totals:
            account_totals[conto] = {"debit": 0.0, "credit": 0.0, "descriptions": []}

        if line.dare_avere == "D":
            account_totals[conto]["debit"] += line.importo
        else:
            account_totals[conto]["credit"] += line.importo
        if line.descrizione not in account_totals[conto]["descriptions"]:
            account_totals[conto]["descriptions"].append(line.descrizione)

    journal_lines = []
    for conto, totals in account_totals.items():
        desc_text = ", ".join(totals["descriptions"])[:100]
        if totals["debit"] > 0.01:
            journal_lines.append({
                "account": conto,
                "description": f"Paghe {summary.mese:02d}/{summary.anno} — {desc_text}",
                "debit": round(totals["debit"], 2),
                "credit": 0.0,
            })
        if totals["credit"] > 0.01:
            journal_lines.append({
                "account": conto,
                "description": f"Paghe {summary.mese:02d}/{summary.anno} — {desc_text}",
                "debit": 0.0,
                "credit": round(totals["credit"], 2),
            })

    return journal_lines


# ═══════════════════════════════════════════════
# LLM-based parser (ADR-008) — replaces regex parser
# ═══════════════════════════════════════════════

LLM_PAYROLL_PROMPT = """Analizza questo Riepilogo Paghe e Contributi ed estrai i dati strutturati.

Restituisci un JSON con questa struttura:
{
  "azienda": "nome azienda",
  "mese": 1,
  "anno": 2025,
  "salari_stipendi": 5000.00,
  "netto_in_busta": 3800.00,
  "contributi_inps_azienda": 1200.00,
  "saldo_dm10": 1500.00,
  "irpef": 800.00,
  "tfr": 350.00,
  "inail": 50.00,
  "totale_dare": 8500.00,
  "totale_avere": 8500.00,
  "linee": [
    {"descrizione": "Salari & stipendi", "importo": 5000.00, "dare_avere": "D", "sezione": "retribuzioni"},
    {"descrizione": "Contributi inps c/ditta", "importo": 1200.00, "dare_avere": "D", "sezione": "contributi_inps"},
    {"descrizione": "NETTO IN BUSTA", "importo": 3800.00, "dare_avere": "A", "sezione": "retribuzioni"},
    {"descrizione": "Irpef", "importo": 800.00, "dare_avere": "A", "sezione": "irpef_versamento"}
  ]
}

REGOLE:
- dare_avere: "D" per costi/spese aziendali (costi personale, contributi c/ditta, TFR, trasferte), "A" per debiti da pagare (netto busta, ritenute IRPEF, contributi c/dipendente, enti bilaterali)
- Il TOTALE DARE deve essere uguale al TOTALE AVERE (partita doppia bilanciata)
- Se trovi "TOTALE GENERALE" con due importi, usali come totale_dare e totale_avere
- Importi in formato numerico (1234.56), non italiano (1.234,56)
- Mese come numero (1-12), anno come 4 cifre
- Includi TUTTE le voci con importo > 0, non solo i subtotali

Testo estratto dal PDF:
---
{text}
---

JSON:"""


async def parse_payroll_llm(text: str) -> PayrollSummary:
    """Parse payroll text using LLM extraction (ADR-008).

    More accurate than regex for varying PDF layouts.
    Cost: ~€0.01 per document with Claude Haiku.
    """
    import os

    prompt = LLM_PAYROLL_PROMPT.replace("{text}", text[:15000])

    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    openai_key = os.environ.get("OPENAI_API_KEY", "")


    # Call LLM directly (not via _call_anthropic which expects array)
    data = None
    if anthropic_key:
        data = await _call_anthropic_payroll(anthropic_key, prompt)
    if data is None and openai_key:
        data = await _call_openai_payroll(openai_key, prompt)

    if data is None:
        logger.warning("LLM non disponibile, fallback a parser regex")
        return parse_payroll_text(text)

    return _llm_response_to_summary(data)


async def _call_anthropic_payroll(api_key: str, prompt: str) -> dict | None:
    """Call Anthropic for payroll — expects JSON object (not array)."""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 4096,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            resp.raise_for_status()
            content = resp.json()["content"][0]["text"]
            return _parse_json_object(content)
    except Exception as e:
        logger.warning("Anthropic payroll error: %s", e)
        return None


async def _call_openai_payroll(api_key: str, prompt: str) -> dict | None:
    """Call OpenAI for payroll — expects JSON object."""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_completion_tokens": 4096,
                    "temperature": 0,
                },
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            return _parse_json_object(content)
    except Exception as e:
        logger.warning("OpenAI payroll error: %s", e)
        return None


def _parse_json_object(content: str) -> dict:
    """Parse JSON object from LLM response, handling markdown code blocks."""
    import json
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1] if "\n" in content else content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
    result = json.loads(content)
    if isinstance(result, list) and len(result) == 1:
        return result[0]
    if isinstance(result, dict):
        return result
    raise ValueError(f"Expected JSON object, got {type(result)}")


def _llm_response_to_summary(data: dict) -> PayrollSummary:
    """Convert LLM JSON response to PayrollSummary."""
    summary = PayrollSummary()
    summary.azienda = str(data.get("azienda", ""))
    summary.mese = int(data.get("mese", 0))
    summary.anno = int(data.get("anno", 0))
    summary.salari_stipendi = float(data.get("salari_stipendi", 0))
    summary.netto_in_busta = float(data.get("netto_in_busta", 0))
    summary.contributi_inps_azienda = float(data.get("contributi_inps_azienda", 0))
    summary.saldo_dm10 = float(data.get("saldo_dm10", 0))
    summary.irpef = float(data.get("irpef", 0))
    summary.tfr = float(data.get("tfr", 0))
    summary.inail = float(data.get("inail", 0))
    summary.totale_dare = float(data.get("totale_dare", 0))
    summary.totale_avere = float(data.get("totale_avere", 0))

    for line_data in data.get("linee", []):
        desc = str(line_data.get("descrizione", ""))
        importo = float(line_data.get("importo", 0))
        da = str(line_data.get("dare_avere", "D"))
        sezione = str(line_data.get("sezione", "altro"))

        if importo > 0:
            summary.linee.append(PayrollLine(
                descrizione=desc,
                importo=importo,
                dare_avere=da,
                sezione=sezione,
                conto_suggerito=_match_conto(desc),
            ))

    return summary
