"""Parser for Riepilogo Paghe e Contributi PDF (US-44).

Extracts payroll line items (Dare/Avere) from the standard payroll summary PDF.
Handles the columnar layout: Description | Importo D/A | DARE | AVERE
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import date

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
        summary.totale_dare = sum(l.importo for l in summary.linee if l.dare_avere == "D")
        summary.totale_avere = sum(l.importo for l in summary.linee if l.dare_avere == "A")

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
