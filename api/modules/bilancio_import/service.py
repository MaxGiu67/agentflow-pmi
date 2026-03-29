"""Service for bilancio/balance import — Excel/CSV, PDF, manual wizard (US-51, US-52, US-54).

Handles initial balance import for new tenants:
1. Excel/CSV: auto-detect columns, LLM-assisted account mapping
2. PDF: pdftotext + LLM extraction
3. Manual wizard: guided entry of key balances
"""

import csv as csv_mod
import io
import json
import logging
import os
import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import JournalEntry, JournalLine

logger = logging.getLogger(__name__)


class BilancioImportService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def import_csv(
        self,
        tenant_id: uuid.UUID,
        filename: str,
        content: bytes,
    ) -> dict:
        """Import bilancio from CSV/Excel-exported CSV (US-51).

        Auto-detects columns: codice conto, descrizione, saldo dare, saldo avere.
        """
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("latin-1")

        # Auto-detect separator
        first_line = text.split("\n", 1)[0]
        sep = max({";": first_line.count(";"), ",": first_line.count(","), "\t": first_line.count("\t")},
                  key=lambda k: {";": first_line.count(";"), ",": first_line.count(","), "\t": first_line.count("\t")}[k])

        reader = csv_mod.DictReader(io.StringIO(text), delimiter=sep)
        if not reader.fieldnames:
            raise ValueError("File CSV vuoto o senza intestazione")

        # Auto-detect column mapping
        mapping = _detect_bilancio_columns(reader.fieldnames)

        lines = []
        for row in reader:
            try:
                codice = row.get(mapping.get("codice", ""), "").strip()
                desc = row.get(mapping.get("descrizione", ""), "").strip()
                dare = _parse_amount(row.get(mapping.get("dare", ""), "0"))
                avere = _parse_amount(row.get(mapping.get("avere", ""), "0"))

                if dare == 0 and avere == 0:
                    continue

                lines.append({
                    "codice_conto": codice,
                    "descrizione": desc,
                    "dare": round(dare, 2),
                    "avere": round(avere, 2),
                })
            except (ValueError, KeyError):
                continue

        totale_dare = sum(l["dare"] for l in lines)
        totale_avere = sum(l["avere"] for l in lines)
        bilanciato = abs(totale_dare - totale_avere) < 0.10

        return {
            "filename": filename,
            "extraction_method": "csv",
            "lines": lines,
            "lines_count": len(lines),
            "totale_dare": round(totale_dare, 2),
            "totale_avere": round(totale_avere, 2),
            "differenza": round(abs(totale_dare - totale_avere), 2),
            "bilanciato": bilanciato,
            "columns_detected": mapping,
        }

    async def import_pdf(
        self,
        tenant_id: uuid.UUID,
        filename: str,
        pdf_content: bytes,
    ) -> dict:
        """Import bilancio from PDF via LLM extraction (US-52)."""
        from api.modules.banking.import_service import extract_text_from_pdf

        text = extract_text_from_pdf(pdf_content)
        if not text or len(text) < 100:
            raise ValueError("Impossibile estrarre testo dal PDF")

        # LLM extraction
        lines = await _extract_bilancio_llm(text)

        totale_dare = sum(l["dare"] for l in lines)
        totale_avere = sum(l["avere"] for l in lines)
        bilanciato = abs(totale_dare - totale_avere) < 1.0  # tolleranza piu ampia per LLM

        return {
            "filename": filename,
            "extraction_method": "llm",
            "lines": lines,
            "lines_count": len(lines),
            "totale_dare": round(totale_dare, 2),
            "totale_avere": round(totale_avere, 2),
            "differenza": round(abs(totale_dare - totale_avere), 2),
            "bilanciato": bilanciato,
        }

    async def confirm_import(
        self,
        tenant_id: uuid.UUID,
        lines: list[dict],
        description: str = "Saldi iniziali bilancio",
    ) -> dict:
        """Save confirmed bilancio lines as opening journal entry (US-51/52/54)."""
        totale_dare = sum(l.get("dare", 0) for l in lines)
        totale_avere = sum(l.get("avere", 0) for l in lines)

        je = JournalEntry(
            tenant_id=tenant_id,
            description=f"Scrittura di apertura — {description}",
            entry_date=date.today(),
            total_debit=round(totale_dare, 2),
            total_credit=round(totale_avere, 2),
            status="posted",
        )
        self.db.add(je)
        await self.db.flush()

        for line in lines:
            dare = line.get("dare", 0)
            avere = line.get("avere", 0)
            if dare == 0 and avere == 0:
                continue
            jl = JournalLine(
                entry_id=je.id,
                account_code=line.get("codice_conto", "")[:20],
                account_name=line.get("descrizione", "")[:255],
                description=line.get("descrizione", "")[:255],
                debit=round(dare, 2),
                credit=round(avere, 2),
            )
            self.db.add(jl)

        await self.db.flush()

        return {
            "journal_entry_id": str(je.id),
            "lines_saved": len([l for l in lines if l.get("dare", 0) != 0 or l.get("avere", 0) != 0]),
            "totale_dare": round(totale_dare, 2),
            "totale_avere": round(totale_avere, 2),
            "bilanciato": abs(totale_dare - totale_avere) < 0.10,
            "message": f"Saldi iniziali importati: {len(lines)} conti",
        }

    async def save_wizard(
        self,
        tenant_id: uuid.UUID,
        balances: dict,
    ) -> dict:
        """Save manual wizard balances (US-54).

        Expected keys: banca, crediti_clienti, debiti_fornitori, capitale_sociale,
        magazzino, immobilizzazioni (all optional).
        """
        lines = []
        accounts_map = {
            "banca": ("15150000", "Depositi bancari", "dare"),
            "cassa": ("15150010", "Cassa contanti", "dare"),
            "crediti_clienti": ("15040000", "Crediti verso clienti", "dare"),
            "debiti_fornitori": ("37030000", "Debiti verso fornitori", "avere"),
            "capitale_sociale": ("31000000", "Capitale sociale", "avere"),
            "magazzino": ("14000000", "Rimanenze", "dare"),
            "immobilizzazioni": ("13000000", "Immobilizzazioni", "dare"),
        }

        for key, (codice, desc, side) in accounts_map.items():
            value = balances.get(key)
            if value and float(value) > 0:
                lines.append({
                    "codice_conto": codice,
                    "descrizione": desc,
                    "dare": round(float(value), 2) if side == "dare" else 0,
                    "avere": round(float(value), 2) if side == "avere" else 0,
                })

        # Auto-balance with "Utili/perdite esercizi precedenti"
        totale_dare = sum(l["dare"] for l in lines)
        totale_avere = sum(l["avere"] for l in lines)
        diff = round(totale_dare - totale_avere, 2)

        if abs(diff) > 0.01:
            if diff > 0:
                lines.append({
                    "codice_conto": "31030030",
                    "descrizione": "Utili esercizi precedenti (quadratura)",
                    "dare": 0,
                    "avere": diff,
                })
            else:
                lines.append({
                    "codice_conto": "31030030",
                    "descrizione": "Perdite esercizi precedenti (quadratura)",
                    "dare": abs(diff),
                    "avere": 0,
                })

        return await self.confirm_import(tenant_id, lines, "Wizard saldi iniziali")


# ── Helpers ──

_CODICE_PATTERNS = {"codice", "cod", "conto", "codice conto", "cod.conto", "account"}
_DESC_PATTERNS = {"descrizione", "description", "nome conto", "denominazione"}
_DARE_PATTERNS = {"dare", "debit", "saldo dare", "importo dare"}
_AVERE_PATTERNS = {"avere", "credit", "saldo avere", "importo avere"}


def _detect_bilancio_columns(fieldnames: list[str]) -> dict:
    mapping = {}
    for f in fieldnames:
        norm = f.strip().lower()
        if norm in _CODICE_PATTERNS:
            mapping["codice"] = f
        elif norm in _DESC_PATTERNS:
            mapping["descrizione"] = f
        elif norm in _DARE_PATTERNS:
            mapping["dare"] = f
        elif norm in _AVERE_PATTERNS:
            mapping["avere"] = f

    if "codice" not in mapping and len(fieldnames) >= 1:
        mapping["codice"] = fieldnames[0]
    if "descrizione" not in mapping and len(fieldnames) >= 2:
        mapping["descrizione"] = fieldnames[1]
    if "dare" not in mapping and len(fieldnames) >= 3:
        mapping["dare"] = fieldnames[2]
    if "avere" not in mapping and len(fieldnames) >= 4:
        mapping["avere"] = fieldnames[3]

    return mapping


def _parse_amount(text: str) -> float:
    text = text.strip().replace(" ", "")
    if not text or text == "-":
        return 0.0
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    return abs(float(text))


LLM_BILANCIO_PROMPT = """Estrai i saldi del bilancio di verifica dal seguente testo.

Per ogni conto restituisci un oggetto JSON con:
- "codice_conto": codice del conto (es. "15150000", "100230 000")
- "descrizione": nome del conto
- "dare": saldo dare (numero positivo, 0 se assente)
- "avere": saldo avere (numero positivo, 0 se assente)

Restituisci SOLO un JSON array valido. Ignora sottotitoli, totali parziali e totali generali.
Converti importi dal formato italiano (1.234,56) al formato numerico (1234.56).

Testo bilancio:
---
{text}
---

JSON array:"""


async def _extract_bilancio_llm(text: str) -> list[dict]:
    """Extract bilancio lines from raw text using LLM."""
    from api.modules.banking.import_service import _call_anthropic, _call_openai

    prompt = LLM_BILANCIO_PROMPT.format(text=text[:20000])

    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    openai_key = os.environ.get("OPENAI_API_KEY", "")

    if anthropic_key:
        result = await _call_anthropic(anthropic_key, prompt)
        if result is not None:
            return _validate_bilancio_lines(result)

    if openai_key:
        result = await _call_openai(openai_key, prompt)
        if result is not None:
            return _validate_bilancio_lines(result)

    raise ValueError("Nessuna API LLM configurata")


def _validate_bilancio_lines(raw: list[dict]) -> list[dict]:
    validated = []
    for item in raw:
        try:
            dare = float(item.get("dare", 0) or 0)
            avere = float(item.get("avere", 0) or 0)
            if dare == 0 and avere == 0:
                continue
            validated.append({
                "codice_conto": str(item.get("codice_conto", "")).strip(),
                "descrizione": str(item.get("descrizione", "")).strip(),
                "dare": round(dare, 2),
                "avere": round(avere, 2),
            })
        except (ValueError, TypeError):
            continue
    return validated
