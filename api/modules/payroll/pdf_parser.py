"""Parser for Riepilogo Paghe e Contributi PDF (US-44).

Extracts payroll line items (Dare/Avere) from the standard payroll summary PDF
produced by Italian payroll software. Creates journal entries in partita doppia.
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
    """A single line from the payroll summary."""
    descrizione: str
    importo: float
    dare_avere: str  # "D" or "A"
    sezione: str  # "retribuzioni", "contributi_inps", "trattenute_fiscali", etc.
    conto_suggerito: str = ""  # suggested account code


@dataclass
class PayrollSummary:
    """Parsed payroll summary for a month."""
    azienda: str = ""
    mese: int = 0
    anno: int = 0
    linee: list[PayrollLine] = field(default_factory=list)
    totale_dare: float = 0.0
    totale_avere: float = 0.0
    netto_in_busta: float = 0.0
    salari_stipendi: float = 0.0
    contributi_inps_azienda: float = 0.0
    contributi_inps_dipendente: float = 0.0
    irpef: float = 0.0
    tfr: float = 0.0
    inail: float = 0.0
    saldo_dm10: float = 0.0


# ── Voci → Conti contabili mapping ──
CONTO_MAP = {
    # Retribuzioni (Dare = Costo)
    "salari": "costi_personale_salari",
    "stipendi": "costi_personale_stipendi",
    "salari & stipendi": "costi_personale_stipendi",
    "trasferte": "costi_personale_trasferte",
    "rimborsi chilometrici": "costi_personale_rimborsi",
    "rimborso spese documentate": "costi_personale_rimborsi",
    "buoni pasto": "costi_personale_buoni_pasto",
    "fondo tfr": "tfr_accantonamento",
    "tfr dell'anno": "tfr_accantonamento",
    "permessi legge 104": "costi_personale_altri",
    # Contributi INPS (Dare = Costo azienda)
    "contributi inps c/ditta": "contributi_inps_azienda",
    "contributi inps c/dipendente": "debiti_vs_inps",
    "contributo aspi": "contributi_inps_azienda",
    # IRPEF (Avere = debito vs erario)
    "irpef": "debiti_vs_erario_irpef",
    "addizionale irpef regionale": "debiti_vs_erario_irpef",
    "addizionale irpef comunale": "debiti_vs_erario_irpef",
    "irpef su tfr": "debiti_vs_erario_irpef",
    "irpef co.co.co": "debiti_vs_erario_irpef",
    # INAIL
    "contributi inail": "debiti_vs_inail",
    "contributo inail": "debiti_vs_inail",
    # Previdenza complementare
    "contributi previdenza complementare": "debiti_vs_fondi_pensione",
    "contributo c/dipe fondo prev": "debiti_vs_fondi_pensione",
    "contributo c/azie fondo prev": "costi_personale_prev_compl",
    "quota tfr x fondo prev": "debiti_vs_fondi_pensione",
    # Enti
    "sanimpresa": "debiti_vs_enti_bilaterali",
    "est pagamento": "debiti_vs_enti_bilaterali",
    # Netto
    "netto in busta": "debiti_vs_dipendenti",
}


def _parse_amount(text: str) -> float:
    """Parse Italian number format: 1.234,56 → 1234.56"""
    text = text.strip().replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return 0.0


def _match_conto(descrizione: str) -> str:
    """Match a description to an account code."""
    desc_lower = descrizione.lower().strip()
    for key, conto in CONTO_MAP.items():
        if key in desc_lower:
            return conto
    return "costi_personale_altri"


def parse_payroll_text(text: str) -> PayrollSummary:
    """Parse extracted text from a Riepilogo Paghe PDF.

    Expected format: standard Italian payroll summary with
    Cod.Conto | Descrizione operazione | Importo | D/A | DARE | AVERE
    """
    summary = PayrollSummary()

    # Extract month and year from header
    header_match = re.search(r"mese\s+di\s+(\w+)\s+(\d{4})", text, re.IGNORECASE)
    if header_match:
        mese_name = header_match.group(1).lower()
        summary.mese = MONTH_MAP.get(mese_name, 0)
        summary.anno = int(header_match.group(2))

    # Extract azienda
    azienda_match = re.search(r"Azienda/Fil\.\s+\d+\s+(.+?)(?:\n|$)", text)
    if azienda_match:
        summary.azienda = azienda_match.group(1).strip()

    # Current section tracker
    current_section = "retribuzioni"

    # Section markers
    section_markers = {
        "RETRIBUZIONI E ALTRE COMPETENZE": "retribuzioni",
        "CONTRIBUTI INPS": "contributi_inps",
        "TRATTENUTE Co.Co.Co": "cococo",
        "ALTRI VERSAMENTI": "altri_versamenti",
        "TRATTENUTE FISCALI (IRPEF)": "irpef_versamento",
        "CREDITI E BONUS FISCALI": "crediti_bonus",
    }

    # Parse lines
    lines = text.split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Check section change
        for marker, section in section_markers.items():
            if marker in line.upper():
                current_section = section
                break

        # Match amount lines: "Description    1.234,56  D" or summary lines with DARE/AVERE
        # Pattern: description followed by amount and D/A indicator
        amount_match = re.search(
            r"^(.+?)\s+([\d.]+,\d{2})\s+([DA])\s*$", line
        )
        if amount_match:
            desc = amount_match.group(1).strip()
            importo = _parse_amount(amount_match.group(2))
            da = amount_match.group(3)
            conto = _match_conto(desc)

            pl = PayrollLine(
                descrizione=desc,
                importo=importo,
                dare_avere=da,
                sezione=current_section,
                conto_suggerito=conto,
            )
            summary.linee.append(pl)

            if da == "D":
                summary.totale_dare += importo
            else:
                summary.totale_avere += importo

        # Match summary lines: "Salari & stipendi   127.975,88"
        summary_match = re.search(
            r"^(.+?)\s+([\d.]+,\d{2})\s*$", line
        )
        if summary_match and not amount_match:
            desc = summary_match.group(1).strip()
            val = _parse_amount(summary_match.group(2))
            desc_lower = desc.lower()

            if "netto in busta" in desc_lower:
                summary.netto_in_busta = val
            elif "salari" in desc_lower and "stipendi" in desc_lower:
                summary.salari_stipendi = val
            elif "saldo a versare su dm10" in desc_lower:
                summary.saldo_dm10 = val
            elif "totale irpef" in desc_lower:
                summary.irpef = val

        # Match TOTALE GENERALE
        totale_match = re.search(
            r"TOTALE GENERALE\s+([\d.]+,\d{2})\s+([\d.]+,\d{2})", line
        )
        if totale_match:
            summary.totale_dare = _parse_amount(totale_match.group(1))
            summary.totale_avere = _parse_amount(totale_match.group(2))

    return summary


def payroll_to_journal_lines(summary: PayrollSummary) -> list[dict]:
    """Convert parsed payroll summary into journal entry lines (partita doppia).

    Returns list of dicts with: account, description, debit, credit
    """
    journal_lines = []

    # Aggregate by account
    account_totals: dict[str, dict] = {}

    for line in summary.linee:
        conto = line.conto_suggerito
        if conto not in account_totals:
            account_totals[conto] = {"debit": 0.0, "credit": 0.0, "descriptions": []}

        if line.dare_avere == "D":
            account_totals[conto]["debit"] += line.importo
        else:
            account_totals[conto]["credit"] += line.importo
        account_totals[conto]["descriptions"].append(line.descrizione)

    # Generate journal lines
    for conto, totals in account_totals.items():
        if totals["debit"] > 0:
            journal_lines.append({
                "account": conto,
                "description": f"Paghe {summary.mese:02d}/{summary.anno} — {', '.join(set(totals['descriptions']))[:100]}",
                "debit": round(totals["debit"], 2),
                "credit": 0.0,
            })
        if totals["credit"] > 0:
            journal_lines.append({
                "account": conto,
                "description": f"Paghe {summary.mese:02d}/{summary.anno} — {', '.join(set(totals['descriptions']))[:100]}",
                "debit": 0.0,
                "credit": round(totals["credit"], 2),
            })

    return journal_lines
