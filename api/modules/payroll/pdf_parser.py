"""Parser for Riepilogo Paghe e Contributi PDF (US-44).

Uses pdfplumber for structured table extraction from PDF.
Falls back to pdftotext + regex if pdfplumber fails.
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
    "acconto": "costi_personale_altri",
    "solidarieta": "contributi_inps_azienda",
}


def _parse_it_number(text: str | None) -> float:
    """Parse Italian number: 1.234,56 → 1234.56"""
    if not text:
        return 0.0
    text = str(text).strip().replace(".", "").replace(",", ".")
    try:
        return abs(float(text))
    except ValueError:
        return 0.0


def _match_conto(desc: str) -> str:
    dl = desc.lower().strip()
    for key, conto in CONTO_MAP.items():
        if key in dl:
            return conto
    return "costi_personale_altri"


def parse_payroll_pdf_bytes(pdf_bytes: bytes) -> PayrollSummary:
    """Parse payroll PDF using pdfplumber for structured table extraction."""
    try:
        import pdfplumber
        return _parse_with_pdfplumber(pdf_bytes)
    except ImportError:
        logger.warning("pdfplumber not installed, falling back to text parser")
        return _parse_with_text_fallback(pdf_bytes)
    except Exception as e:
        logger.error("pdfplumber failed: %s, falling back to text", e)
        return _parse_with_text_fallback(pdf_bytes)


def _parse_with_pdfplumber(pdf_bytes: bytes) -> PayrollSummary:
    """Extract data using pdfplumber table extraction."""
    import io
    import pdfplumber

    summary = PayrollSummary()

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        full_text = ""
        all_rows: list[list[str]] = []

        for page in pdf.pages:
            text = page.extract_text() or ""
            full_text += text + "\n"

            # Extract tables
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if row:
                        all_rows.append([str(c or "").strip() for c in row])

        # Extract month/year from full text
        hdr = re.search(r"mese\s+di\s+(\w+)\s+(\d{4})", full_text, re.IGNORECASE)
        if hdr:
            summary.mese = MONTH_MAP.get(hdr.group(1).lower(), 0)
            summary.anno = int(hdr.group(2))

        az = re.search(r"(?:Azienda|Fil)\.\s+\d+\s+(.+?)(?:\n|$)", full_text)
        if az:
            summary.azienda = az.group(1).strip()

        # Process extracted table rows
        current_section = "retribuzioni"
        section_markers = {
            "RETRIBUZIONI": "retribuzioni",
            "CONTRIBUTI INPS": "contributi_inps",
            "TRATTENUTE CO": "cococo",
            "ALTRI VERSAMENTI": "altri_versamenti",
            "TRATTENUTE FISCALI": "irpef_versamento",
            "CREDITI E BONUS": "crediti_bonus",
            "CREDITI IRPEF": "crediti_irpef",
        }

        for row in all_rows:
            # Join row to detect sections
            row_text = " ".join(row).upper()
            for marker, section in section_markers.items():
                if marker in row_text:
                    current_section = section
                    break

            # Try to find: Cod.Conto | Descrizione | Importo | D/A | DARE | AVERE
            # The table typically has 4-6 columns
            if len(row) < 3:
                continue

            # Find the description (longest non-numeric cell)
            desc = ""
            importo = 0.0
            da_flag = ""
            dare_val = 0.0
            avere_val = 0.0

            for i, cell in enumerate(row):
                cell = cell.strip()
                if not cell or cell == "_" * len(cell):
                    continue

                # Check if it's a D/A flag
                if cell in ("D", "A"):
                    da_flag = cell
                    continue

                # Check if it's a number
                num = _parse_it_number(cell)
                if num > 0 and re.match(r"^[\d.,]+$", cell.replace(" ", "")):
                    if da_flag:
                        importo = num
                    elif i >= len(row) - 2:
                        # Last columns are DARE/AVERE
                        if i == len(row) - 2:
                            dare_val = num
                        else:
                            avere_val = num
                    else:
                        importo = num
                    continue

                # It's a description
                if len(cell) > 2 and not cell.startswith("Cod"):
                    desc = cell

            # Create line if we have data
            if desc and (importo > 0 or dare_val > 0 or avere_val > 0):
                dl = desc.lower()

                # Determine D/A
                if da_flag:
                    pass  # already set
                elif dare_val > 0 and avere_val == 0:
                    da_flag = "D"
                    importo = dare_val
                elif avere_val > 0 and dare_val == 0:
                    da_flag = "A"
                    importo = avere_val
                elif dare_val > 0:
                    da_flag = "D"
                    importo = dare_val
                else:
                    da_flag = "D"  # default

                if importo <= 0:
                    importo = dare_val or avere_val

                if importo > 0:
                    conto = _match_conto(desc)
                    summary.linee.append(PayrollLine(
                        descrizione=desc, importo=round(importo, 2),
                        dare_avere=da_flag, sezione=current_section,
                        conto_suggerito=conto,
                    ))

                    # Track key totals
                    if "netto in busta" in dl:
                        summary.netto_in_busta = importo
                    elif "salari" in dl and "stipendi" in dl:
                        summary.salari_stipendi = importo
                    elif "saldo" in dl and "dm10" in dl:
                        summary.saldo_dm10 = importo

        # Extract TOTALE GENERALE
        tg = re.search(r"TOTALE\s+GENERALE\s+([\d.,]+)\s+([\d.,]+)", full_text)
        if tg:
            summary.totale_dare = _parse_it_number(tg.group(1))
            summary.totale_avere = _parse_it_number(tg.group(2))
        else:
            summary.totale_dare = sum(l.importo for l in summary.linee if l.dare_avere == "D")
            summary.totale_avere = sum(l.importo for l in summary.linee if l.dare_avere == "A")

        # Extract IRPEF total
        irpef_m = re.search(r"(?:Trattenute fiscali|TOTALE irpef)[^\d]+([\d.,]+)", full_text)
        if irpef_m:
            summary.irpef = _parse_it_number(irpef_m.group(1))

    return summary


def _parse_with_text_fallback(pdf_bytes: bytes) -> PayrollSummary:
    """Fallback: use pdftotext for extraction."""
    import subprocess
    import tempfile
    import os

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(pdf_bytes)
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            ["pdftotext", "-layout", tmp_path, "-"],
            capture_output=True, text=True, timeout=30,
        )
        return parse_payroll_text(result.stdout)
    finally:
        os.unlink(tmp_path)


def parse_payroll_text(text: str) -> PayrollSummary:
    """Parse pdftotext output (legacy fallback)."""
    summary = PayrollSummary()

    hdr = re.search(r"mese\s+di\s+(\w+)\s+(\d{4})", text, re.IGNORECASE)
    if hdr:
        summary.mese = MONTH_MAP.get(hdr.group(1).lower(), 0)
        summary.anno = int(hdr.group(2))

    az = re.search(r"Azienda/Fil\.\s+\d+\s+(.+?)(?:\n|$)", text)
    if az:
        summary.azienda = az.group(1).strip()

    current_section = "retribuzioni"
    section_markers = {
        "RETRIBUZIONI E ALTRE COMPETENZE": "retribuzioni",
        "CONTRIBUTI INPS": "contributi_inps",
        "TRATTENUTE Co.Co.Co": "cococo",
        "ALTRI VERSAMENTI": "altri_versamenti",
        "TRATTENUTE FISCALI": "irpef_versamento",
        "CREDITI E BONUS FISCALI": "crediti_bonus",
    }

    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue

        for marker, section in section_markers.items():
            if marker in stripped.upper():
                current_section = section
                break

        # Pattern: "desc    1.234,56   D"
        m1 = re.search(r"^[_\s]*(.+?)\s{2,}([\d.]+,\d{2})\s+([DA])\s*$", line)
        if m1:
            desc, importo, da = m1.group(1).strip(), _parse_it_number(m1.group(2)), m1.group(3)
            if importo > 0:
                summary.linee.append(PayrollLine(desc, importo, da, current_section, _match_conto(desc)))
            continue

        # Pattern: "desc         123.456,78"
        m2 = re.search(r"^[_\s]*(.+?)\s{3,}([\d.]+,\d{2})\s*$", line)
        if m2:
            desc, val = m2.group(1).strip(), _parse_it_number(m2.group(2))
            if val <= 0 or len(desc) < 3:
                continue
            dl = desc.lower()
            if "netto in busta" in dl:
                summary.netto_in_busta = val
                summary.linee.append(PayrollLine(desc, val, "A", "retribuzioni", "debiti_vs_dipendenti"))
            elif "salari" in dl and "stipendi" in dl:
                summary.salari_stipendi = val
                summary.linee.append(PayrollLine(desc, val, "D", "retribuzioni", "costi_personale_stipendi"))
            elif "saldo" in dl and "dm10" in dl:
                summary.saldo_dm10 = val
            elif "totale irpef" in dl:
                summary.irpef = val
            else:
                val_start = line.rfind(m2.group(2))
                da = "A" if val_start > 85 else "D"
                summary.linee.append(PayrollLine(desc, val, da, current_section, _match_conto(desc)))

    tg = re.search(r"TOTALE GENERALE\s+([\d.]+,\d{2})\s+([\d.]+,\d{2})", text)
    if tg:
        summary.totale_dare = _parse_it_number(tg.group(1))
        summary.totale_avere = _parse_it_number(tg.group(2))
    else:
        summary.totale_dare = sum(l.importo for l in summary.linee if l.dare_avere == "D")
        summary.totale_avere = sum(l.importo for l in summary.linee if l.dare_avere == "A")

    return summary


def payroll_to_journal_lines(summary: PayrollSummary) -> list[dict]:
    """Convert parsed payroll into journal entry lines."""
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
