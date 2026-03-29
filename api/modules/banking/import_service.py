"""Service for bank statement import via PDF (LLM extraction) and CSV (US-44, US-45).

ADR-008: Uses LLM (Claude Haiku) for universal PDF extraction instead of
per-bank regex parsers. Cost: ~€0.01 per document.
"""

import json
import logging
import os
import subprocess
import tempfile
import uuid
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import BankAccount, BankStatementImport, BankTransaction

logger = logging.getLogger(__name__)

LLM_EXTRACTION_PROMPT = """Estrai i movimenti bancari dal seguente testo di estratto conto.

Per ogni movimento restituisci un oggetto JSON con:
- "data_operazione": data in formato YYYY-MM-DD
- "data_valuta": data valuta in formato YYYY-MM-DD (se presente, altrimenti null)
- "descrizione": descrizione completa dell'operazione
- "dare": importo in uscita (numero positivo, 0 se non presente)
- "avere": importo in entrata (numero positivo, 0 se non presente)

Restituisci SOLO un JSON array valido, senza commenti o testo aggiuntivo.
Ignora le righe di intestazione, i totali e i saldi (iniziale/finale).
Converti gli importi dal formato italiano (1.234,56) al formato numerico (1234.56).

Testo estratto conto:
---
{text}
---

JSON array:"""


async def extract_movements_llm(text: str) -> list[dict]:
    """Extract bank movements from raw text using LLM.

    Returns list of dicts with keys: data_operazione, data_valuta, descrizione, dare, avere.
    """
    import httpx

    prompt = LLM_EXTRACTION_PROMPT.format(text=text[:15000])  # limit context

    # Try Anthropic (Claude Haiku) first, then OpenAI as fallback
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    openai_key = os.environ.get("OPENAI_API_KEY", "")

    if anthropic_key:
        movements = await _call_anthropic(anthropic_key, prompt)
        if movements is not None:
            return movements

    if openai_key:
        movements = await _call_openai(openai_key, prompt)
        if movements is not None:
            return movements

    raise ValueError("Nessuna API LLM configurata (ANTHROPIC_API_KEY o OPENAI_API_KEY)")


async def _call_anthropic(api_key: str, prompt: str) -> list[dict] | None:
    """Call Anthropic Claude API for extraction."""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=60) as client:
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
            data = resp.json()
            content = data["content"][0]["text"]
            return _parse_json_response(content)
    except Exception as e:
        logger.warning("Anthropic API error: %s", e)
        return None


async def _call_openai(api_key: str, prompt: str) -> list[dict] | None:
    """Call OpenAI API as fallback."""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_completion_tokens": 4096,
                    "temperature": 0,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return _parse_json_response(content)
    except Exception as e:
        logger.warning("OpenAI API error: %s", e)
        return None


def _parse_json_response(content: str) -> list[dict]:
    """Parse JSON array from LLM response, handling markdown code blocks."""
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1] if "\n" in content else content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

    movements = json.loads(content)
    if not isinstance(movements, list):
        raise ValueError("LLM response is not a JSON array")
    return movements


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text from PDF using pdftotext (poppler)."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(pdf_bytes)
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            ["pdftotext", "-layout", tmp_path, "-"],
            capture_output=True, text=True, timeout=30,
        )
        return result.stdout
    finally:
        os.unlink(tmp_path)


class BankImportService:
    """Service for importing bank statements from PDF or CSV."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _verify_account(self, account_id: uuid.UUID, tenant_id: uuid.UUID) -> BankAccount:
        """Verify bank account exists and belongs to tenant."""
        result = await self.db.execute(
            select(BankAccount).where(
                BankAccount.id == account_id,
                BankAccount.tenant_id == tenant_id,
            )
        )
        account = result.scalar_one_or_none()
        if not account:
            raise ValueError("Conto bancario non trovato")
        return account

    async def import_pdf_statement(
        self,
        tenant_id: uuid.UUID,
        account_id: uuid.UUID,
        filename: str,
        pdf_content: bytes,
    ) -> dict:
        """Import bank statement from PDF using LLM extraction (ADR-008).

        Flow: PDF → pdftotext → LLM extraction → structured movements → preview data
        The caller should present preview to user for confirmation before saving.
        """
        account = await self._verify_account(account_id, tenant_id)

        # Extract text
        text = extract_text_from_pdf(pdf_content)
        if not text or len(text) < 50:
            raise ValueError("Impossibile estrarre testo dal PDF. Verificare il formato.")

        # Create import log
        import_log = BankStatementImport(
            tenant_id=tenant_id,
            bank_account_id=account_id,
            filename=filename,
            status="pending",
            extraction_method="llm",
            raw_text=text[:50000],
        )
        self.db.add(import_log)
        await self.db.flush()

        # LLM extraction
        try:
            movements = await extract_movements_llm(text)
        except Exception as e:
            import_log.status = "error"
            import_log.error_message = str(e)
            await self.db.flush()
            raise ValueError(
                f"Errore nell'estrazione dei movimenti: {e}. "
                "Provare con il formato CSV."
            ) from e

        # Validate and normalize movements
        validated = []
        for m in movements:
            try:
                data_op = date.fromisoformat(m["data_operazione"])
                data_val = date.fromisoformat(m["data_valuta"]) if m.get("data_valuta") else None
                dare = float(m.get("dare", 0) or 0)
                avere = float(m.get("avere", 0) or 0)
                desc = str(m.get("descrizione", "")).strip()

                if dare == 0 and avere == 0:
                    continue

                validated.append({
                    "data_operazione": data_op.isoformat(),
                    "data_valuta": data_val.isoformat() if data_val else None,
                    "descrizione": desc,
                    "dare": round(dare, 2),
                    "avere": round(avere, 2),
                    "importo": round(avere - dare, 2),
                    "direzione": "credit" if avere > dare else "debit",
                })
            except (KeyError, ValueError) as e:
                logger.warning("Skipping invalid movement: %s — %s", m, e)
                continue

        # Update log
        import_log.movements_count = len(validated)
        if validated:
            dates = [date.fromisoformat(m["data_operazione"]) for m in validated]
            import_log.period_from = min(dates)
            import_log.period_to = max(dates)
            import_log.status = "processed"
        else:
            import_log.status = "error"
            import_log.error_message = "Nessun movimento valido estratto"

        await self.db.flush()

        return {
            "import_id": str(import_log.id),
            "bank_account_id": str(account_id),
            "filename": filename,
            "extraction_method": "llm",
            "movements_count": len(validated),
            "period_from": import_log.period_from.isoformat() if import_log.period_from else None,
            "period_to": import_log.period_to.isoformat() if import_log.period_to else None,
            "movements": validated,
            "status": import_log.status,
        }

    async def confirm_import(
        self,
        tenant_id: uuid.UUID,
        account_id: uuid.UUID,
        movements: list[dict],
        source: str = "import_pdf",
    ) -> dict:
        """Confirm and save imported movements to bank_transactions."""
        await self._verify_account(account_id, tenant_id)

        saved = 0
        for m in movements:
            kwargs = {
                "bank_account_id": account_id,
                "transaction_id": f"IMP-{uuid.uuid4().hex[:12]}",
                "date": date.fromisoformat(m["data_operazione"]),
                "amount": abs(m.get("importo", 0)),
                "direction": m.get("direzione", "debit"),
                "counterpart": None,
                "description": m.get("descrizione", ""),
            }
            # value_date and source may not exist in DB yet (pre-migration)
            try:
                kwargs["value_date"] = date.fromisoformat(m["data_valuta"]) if m.get("data_valuta") else None
                kwargs["source"] = source
            except Exception:
                pass
            tx = BankTransaction(**kwargs)
            self.db.add(tx)
            saved += 1

        await self.db.flush()

        return {
            "saved": saved,
            "bank_account_id": str(account_id),
            "source": source,
            "message": f"{saved} movimenti importati con successo",
        }

    async def import_csv_statement(
        self,
        tenant_id: uuid.UUID,
        account_id: uuid.UUID,
        filename: str,
        csv_content: bytes,
    ) -> dict:
        """Import bank statement from CSV with auto-detect (US-45).

        Auto-detects separator (, ; \\t) and maps columns by header names.
        """
        import csv as csv_mod
        import io

        await self._verify_account(account_id, tenant_id)

        # Decode text
        try:
            text = csv_content.decode("utf-8")
        except UnicodeDecodeError:
            text = csv_content.decode("latin-1")

        # Auto-detect separator
        first_line = text.split("\n", 1)[0]
        separator = _detect_separator(first_line)

        # Parse CSV
        reader = csv_mod.DictReader(io.StringIO(text), delimiter=separator)
        if not reader.fieldnames:
            raise ValueError("File CSV vuoto o senza intestazione")

        # Auto-detect column mapping
        mapping = _detect_columns(reader.fieldnames)

        # Create import log
        import_log = BankStatementImport(
            tenant_id=tenant_id,
            bank_account_id=account_id,
            filename=filename,
            status="pending",
            extraction_method="csv",
        )
        self.db.add(import_log)
        await self.db.flush()

        # Extract movements
        movements = []
        for row in reader:
            try:
                m = _parse_csv_row(row, mapping)
                if m:
                    movements.append(m)
            except (KeyError, ValueError) as e:
                logger.warning("Skipping CSV row: %s — %s", row, e)

        import_log.movements_count = len(movements)
        if movements:
            dates = [date.fromisoformat(m["data_operazione"]) for m in movements]
            import_log.period_from = min(dates)
            import_log.period_to = max(dates)
            import_log.status = "processed"
        else:
            import_log.status = "error"
            import_log.error_message = "Nessun movimento valido trovato nel CSV"

        await self.db.flush()

        return {
            "import_id": str(import_log.id),
            "bank_account_id": str(account_id),
            "filename": filename,
            "extraction_method": "csv",
            "movements_count": len(movements),
            "period_from": import_log.period_from.isoformat() if import_log.period_from else None,
            "period_to": import_log.period_to.isoformat() if import_log.period_to else None,
            "movements": movements,
            "columns_detected": mapping,
            "separator_detected": separator,
            "status": import_log.status,
        }


# ── CSV helpers ──

def _detect_separator(header_line: str) -> str:
    """Auto-detect CSV separator from header line."""
    counts = {
        ";": header_line.count(";"),
        ",": header_line.count(","),
        "\t": header_line.count("\t"),
    }
    return max(counts, key=counts.get) if max(counts.values()) > 0 else ","


# Common column name patterns for Italian bank exports
_DATE_PATTERNS = {"data", "data_operazione", "data operazione", "date", "data op", "data op."}
_VALUTA_PATTERNS = {"valuta", "data_valuta", "data valuta", "value_date"}
_DESC_PATTERNS = {"descrizione", "description", "causale", "descrizione operazioni", "movimenti"}
_DARE_PATTERNS = {"dare", "uscite", "addebiti", "movimenti dare", "debit", "importo dare"}
_AVERE_PATTERNS = {"avere", "entrate", "accrediti", "movimenti avere", "credit", "importo avere"}
_IMPORTO_PATTERNS = {"importo", "amount", "ammontare"}
_SALDO_PATTERNS = {"saldo", "balance", "saldo finale", "saldo progressivo"}


def _detect_columns(fieldnames: list[str]) -> dict:
    """Map CSV column names to our standard fields."""
    mapping = {}
    normalized = {f: f.strip().lower() for f in fieldnames}

    for orig, norm in normalized.items():
        if norm in _DATE_PATTERNS:
            mapping["data_operazione"] = orig
        elif norm in _VALUTA_PATTERNS:
            mapping["data_valuta"] = orig
        elif norm in _DESC_PATTERNS:
            mapping["descrizione"] = orig
        elif norm in _DARE_PATTERNS:
            mapping["dare"] = orig
        elif norm in _AVERE_PATTERNS:
            mapping["avere"] = orig
        elif norm in _IMPORTO_PATTERNS:
            mapping["importo"] = orig
        elif norm in _SALDO_PATTERNS:
            mapping["saldo"] = orig

    if "data_operazione" not in mapping:
        # Fallback: use first column as date
        mapping["data_operazione"] = fieldnames[0]

    return mapping


def _parse_amount_it(text: str) -> float:
    """Parse amount in Italian (1.234,56) or international (1234.56) format."""
    text = text.strip().replace(" ", "")
    if not text or text == "-":
        return 0.0

    # If contains comma → Italian format: dots are thousands, comma is decimal
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    # else: international format, dots are decimals — leave as is

    return float(text)


def _parse_date_flexible(text: str) -> date:
    """Parse date in multiple formats."""
    text = text.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d.%m.%Y", "%d-%m-%Y", "%d/%m/%y", "%d.%m.%y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Formato data non riconosciuto: {text}")


def _parse_csv_row(row: dict, mapping: dict) -> dict | None:
    """Parse a single CSV row into a movement dict."""
    date_col = mapping.get("data_operazione")
    if not date_col or not row.get(date_col, "").strip():
        return None

    data_op = _parse_date_flexible(row[date_col])
    data_val = None
    if "data_valuta" in mapping and row.get(mapping["data_valuta"], "").strip():
        try:
            data_val = _parse_date_flexible(row[mapping["data_valuta"]])
        except ValueError:
            pass

    desc = row.get(mapping.get("descrizione", ""), "").strip()

    # Determine dare/avere
    dare = 0.0
    avere = 0.0

    if "dare" in mapping and "avere" in mapping:
        dare = _parse_amount_it(row.get(mapping["dare"], "0"))
        avere = _parse_amount_it(row.get(mapping["avere"], "0"))
    elif "importo" in mapping:
        importo = _parse_amount_it(row.get(mapping["importo"], "0"))
        if importo >= 0:
            avere = importo
        else:
            dare = abs(importo)

    if dare == 0 and avere == 0:
        return None

    return {
        "data_operazione": data_op.isoformat(),
        "data_valuta": data_val.isoformat() if data_val else None,
        "descrizione": desc,
        "dare": round(dare, 2),
        "avere": round(avere, 2),
        "importo": round(avere - dare, 2),
        "direzione": "credit" if avere > dare else "debit",
    }
