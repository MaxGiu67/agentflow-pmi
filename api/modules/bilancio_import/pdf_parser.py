"""Parser deterministico per bilancio contabile PDF formato italiano.

Estrae saldi dalla Situazione Patrimoniale senza LLM.
Il PDF ha 2 colonne affiancate: Attivo (sinistra) e Passivo (destra).
Ogni riga puo contenere un conto attivo E un conto passivo.

Pattern riga tipica:
  "13005000 - Costi impianto  364.242,57 13005005 - F.do amm. costi  276.970,43"
  |--- ATTIVO (dare) ---|              |--- PASSIVO (avere) ---|
"""

import logging
import re

logger = logging.getLogger(__name__)


def _parse_amount(text: str) -> float:
    """Parse 1.234.567,89 → 1234567.89"""
    return float(text.replace('.', '').replace(',', '.'))


def parse_bilancio_pdf_text(text: str) -> dict:
    """Parse bilancio PDF text, sezione Patrimoniale only."""
    lines_out = []
    totale_attivo = 0.0
    totale_passivo = 0.0
    utile = 0.0

    all_lines = text.split('\n')

    # Extract only Situazione Patrimoniale
    in_patrimoniale = False
    patri_lines = []

    for line in all_lines:
        s = line.strip()

        if 'SITUAZIONE PATRIMONIALE' in s:
            in_patrimoniale = True
            continue
        if 'CONTO ECONOMICO' in s or 'ELENCO CLIENTI' in s:
            in_patrimoniale = False
            continue

        if in_patrimoniale and s:
            patri_lines.append(line)

        # Totals
        if 'TOTALE ATTIVITA' in s:
            amounts = re.findall(r'[\d.]+,\d{2}', s)
            if amounts:
                totale_attivo = _parse_amount(amounts[0])
                if len(amounts) >= 2:
                    totale_passivo = _parse_amount(amounts[1])

        if 'UTILE D' in s:
            amounts = re.findall(r'[\d.]+,\d{2}', s)
            if amounts:
                utile = _parse_amount(amounts[-1])

    # Parse each line: find ALL 8-digit codes with amounts
    # Pattern: codice 8 cifre + " - " + descrizione + spazi + importo
    CONTO_AMOUNT = re.compile(r'(\d{8})\s*-\s*(.+?)\s{2,}([\d.]+,\d{2})')

    for line in patri_lines:
        if '___' in line or not line.strip():
            continue

        # Find all matches on this line (could be 1 or 2 — left and right column)
        matches = CONTO_AMOUNT.finditer(line)
        found_positions = []

        for m in matches:
            codice = m.group(1)
            desc = m.group(2).strip()
            importo = _parse_amount(m.group(3))
            col_start = m.start()
            found_positions.append((codice, desc, importo, col_start))

        # Assign dare/avere based on position:
        # First match (left column) = Attivo = Dare
        # Second match (right column) = Passivo = Avere
        for i, (codice, desc, importo, col_start) in enumerate(found_positions):
            if importo == 0:
                continue

            if i == 0 and len(found_positions) >= 2:
                # First of two = Attivo
                lines_out.append({
                    'codice_conto': codice,
                    'descrizione': desc,
                    'dare': round(importo, 2),
                    'avere': 0.0,
                })
            elif i == 1 or (i == 0 and len(found_positions) == 1):
                # Second of two = Passivo, OR single match — determine by code range
                # Codes 1xxxx = Attivo, 2xxxx-3xxxx = Passivo
                first_digit = codice[0]
                if first_digit in ('1',):
                    lines_out.append({
                        'codice_conto': codice,
                        'descrizione': desc,
                        'dare': round(importo, 2),
                        'avere': 0.0,
                    })
                else:
                    lines_out.append({
                        'codice_conto': codice,
                        'descrizione': desc,
                        'dare': 0.0,
                        'avere': round(importo, 2),
                    })
            else:
                # Additional matches (rare) — use code prefix
                first_digit = codice[0]
                if first_digit in ('1',):
                    lines_out.append({
                        'codice_conto': codice,
                        'descrizione': desc,
                        'dare': round(importo, 2),
                        'avere': 0.0,
                    })
                else:
                    lines_out.append({
                        'codice_conto': codice,
                        'descrizione': desc,
                        'dare': 0.0,
                        'avere': round(importo, 2),
                    })

    # Deduplicate
    seen = set()
    unique = []
    for ln in lines_out:
        key = (ln['codice_conto'], ln['dare'], ln['avere'])
        if key not in seen:
            seen.add(key)
            unique.append(ln)

    calc_dare = sum(ln['dare'] for ln in unique)
    calc_avere = sum(ln['avere'] for ln in unique)

    # If we have PDF totals, add balancing entry for utile
    if totale_attivo > 0 and utile > 0 and abs((calc_avere + utile) - calc_dare) < calc_dare * 0.1:
        unique.append({
            'codice_conto': '32000000',
            'descrizione': "Utile d'esercizio",
            'dare': 0.0,
            'avere': round(utile, 2),
        })
        calc_avere += utile

    return {
        'lines': unique,
        'lines_count': len(unique),
        'totale_dare': round(calc_dare, 2),
        'totale_avere': round(calc_avere, 2),
        'differenza': round(abs(calc_dare - calc_avere), 2),
        'bilanciato': abs(calc_dare - calc_avere) < max(1.0, calc_dare * 0.001),
        'totale_attivo_pdf': round(totale_attivo, 2),
        'totale_passivo_pdf': round(totale_passivo, 2),
        'utile_pdf': round(utile, 2),
        'section': 'patrimoniale',
        'extraction_method': 'regex',
    }
