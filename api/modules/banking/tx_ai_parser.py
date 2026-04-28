"""AI-powered parser per movimenti bancari italiani (Sprint 50).

Pipeline a 3 livelli:
  1. RULES (regex/keyword) — gratis, ~70% delle transazioni IT
  2. LLM (Anthropic Claude Sonnet 4.6) — fallback per low confidence, ~25%
  3. MANUAL — utente corregge in UI, feedback loop, ~5%

Cache: SHA256(description) → output. Hit rate atteso 80% (boilerplate Intesa/Unicredit/etc).

Categorie (parsed_category):
  income_invoice    — bonifico ricevuto da cliente (probabile fattura attiva)
  expense_invoice   — bonifico inviato a fornitore (probabile fattura passiva)
  payroll           — stipendio dipendente / collaboratore
  tax_f24           — F24 / addebito Agenzia Entrate
  tax_iva           — versamento IVA periodico
  fee               — commissione bancaria, canone, bollo
  transfer          — giroconto tra conti propri
  loan_payment      — rata finanziamento
  interest          — interessi attivi/passivi
  atm               — prelievo bancomat
  pos               — pagamento POS / carta
  sepa_dd           — addebito SEPA Direct Debit
  refund            — rimborso
  other             — non classificato
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ParsedTx:
    counterparty: str | None = None
    counterparty_iban: str | None = None
    invoice_ref: str | None = None
    category: str = "other"
    subcategory: str | None = None
    confidence: float = 0.0
    method: str = "rules"  # rules|llm|manual
    notes: str | None = None


# ── Regex italiani comuni ───────────────────────────────────

# Mittente (per credit) o Beneficiario (per debit)
_MITT_RE = re.compile(
    r"(?:MITT(?:ENTE)?\.?|DA|ORDINANTE)[:\s]+"
    r"([A-Z0-9][A-ZÀ-Ý0-9.\-&'/ ]{2,80}?)"
    r"(?=\s+(?:BIC\.?|BENEF|IBAN|COD\.|VS|CRO|TRN|FATT|FT|N\.?\b)|\.?\s*$)",
    re.IGNORECASE,
)
_BENEF_RE = re.compile(
    r"(?:BENEF(?:ICIARIO)?\.?|A FAVORE DI|DESTINATARIO|PER)[:\s]+"
    r"([A-Z0-9][A-ZÀ-Ý0-9.\-&'/ ]{2,80}?)"
    r"(?=\s+(?:BIC\.?|MITT|IBAN|COD\.|VS|CRO|TRN|FATT|FT|N\.?\b)|\.?\s*$)",
    re.IGNORECASE,
)
_IBAN_RE = re.compile(r"\b(IT[0-9A-Z]{25})\b", re.IGNORECASE)

# Riferimenti fattura
_INVOICE_RE = re.compile(
    r"\b(?:FATT(?:URA)?|FT|FTR|N(?:UM)?(?:\.|°)?)\s*[:.\s]*"
    r"([A-Z0-9][A-Z0-9/\-]{0,30}[0-9])",
    re.IGNORECASE,
)

# Categorie via keyword
# IMPORTANT: ordine = priorità. Le commissioni bonifico vanno PRIMA del bonifico
# generico, altrimenti "COSTO BONIFICO 0,70 EUR" diventerebbe expense_invoice.
_CATEGORY_KEYWORDS: list[tuple[str, str, list[str]]] = [
    # (category, subcategory, keywords)
    # ── Commissioni bonifico (priorità alta) ──
    ("fee", "commissione_bonifico", [
        "COSTO BONIFICO", "SPESE BONIFICO", "COMMISSIONE BONIFICO",
        "COMM BONIFICO", "COMM. BONIFICO", "COSTO BON", "SPESE BON",
        "COMMISSIONE INCASSO", "SPESE OPERAZIONE",
    ]),
    ("tax_f24", "f24", ["F24", "AGENZIA ENTRATE", "ADDEBITO F24"]),
    ("tax_iva", "iva", ["LIQUIDAZIONE IVA", "VERSAMENTO IVA", "ADDEBITO IVA"]),
    # ── Stipendi e compensi ──
    ("payroll", "stipendio", [
        "STIPENDIO", "STIPENDI", "EMOLUMENTI", "BUSTA PAGA", "RETRIBUZIONE",
        "ACCREDITO STIPENDIO", "PAGAMENTO STIPENDIO", "MENSILITA",
        "PAGA MESE", "ACCONTO STIPENDIO",
    ]),
    ("payroll", "compenso", [
        "COMPENSO", "COMPENSO COLLABORATORE", "COMPENSO AMMINISTRATORE",
        "COMPENSO CO.CO.CO", "PARCELLA",
    ]),
    ("payroll", "tfr", ["TFR", "TRATTAMENTO FINE RAPPORTO"]),
    ("payroll", "contributi", ["INPS", "INAIL", "F24 INPS"]),
    # ── Finanziamenti ──
    ("loan_payment", "rata_mutuo", ["MUTUO", "RATA MUTUO"]),
    ("loan_payment", "rata_prestito", ["PRESTITO", "RATA PRESTITO", "PRESTITALIA", "FINANZIAMENTO"]),
    ("loan_payment", "leasing", ["LEASING", "RATA LEASING"]),
    ("interest", None, ["INTERESSI", "COMPETENZE"]),
    # ── Commissioni generiche e canoni ──
    ("fee", "commissione", ["COMMISSIONI", "COMMISSIONE", "SPESE TENUTA", "COSTO", "BOLLO"]),
    ("fee", "canone", ["CANONE", "CANONE MENSILE", "CANONE TRIMESTRALE"]),
    ("fee", "polizza", ["POLIZZA", "PREMIO POLIZZA", "ASSICURAZIONE"]),
    ("fee", "imposta_bollo", ["IMPOSTA DI BOLLO"]),
    # ── Operazioni cash/POS ──
    ("atm", None, ["PRELEVAMENTO ATM", "PRELIEVO ATM", "PRELIEVO BANCOMAT"]),
    ("pos", None, ["POS", "PAGAMENTO POS", "ACQUISTO"]),
    ("sepa_dd", None, ["SEPA DIRECT DEBIT", "ADDEBITO DIRETTO", "RID", "SDD"]),
    ("transfer", "giroconto", ["GIROCONTO", "TRASFERIMENTO TRA CONTI"]),
    ("refund", None, ["RIMBORSO", "STORNO", "ACCREDITO STORNO"]),
]

_BONIFICO_KEYWORDS = ["BONIFICO", "ACCR BON", "ADDEBITO BON", "BONIFICO IST"]

# Soglia importo: bonifici sotto questa cifra in uscita sono quasi sempre
# commissioni della banca (mai un pagamento reale a un fornitore).
_FEE_AMOUNT_THRESHOLD_EUR = 5.0


def _hash(s: str) -> str:
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()[:16]


def parse_with_rules(description: str | None, direction: str, amount: float) -> ParsedTx:
    """Step 1: regex + keyword. Confidence 0.5-0.95 a seconda di quanti campi estrae."""
    if not description:
        return ParsedTx(category="other", confidence=0.0, method="rules")

    desc_upper = description.upper()
    result = ParsedTx(method="rules", confidence=0.0)

    # ── Counterparty ──
    if direction == "credit":
        # noi riceviamo → mittente
        m = _MITT_RE.search(description)
        if m:
            result.counterparty = _clean_party(m.group(1))
            result.confidence += 0.4
    else:
        # noi paghiamo → beneficiario
        m = _BENEF_RE.search(description)
        if m:
            result.counterparty = _clean_party(m.group(1))
            result.confidence += 0.4

    # ── IBAN controparte ──
    iban_m = _IBAN_RE.search(description)
    if iban_m:
        result.counterparty_iban = iban_m.group(1).upper()
        result.confidence += 0.05

    # ── Invoice ref ──
    inv_m = _INVOICE_RE.search(description)
    if inv_m:
        ref = inv_m.group(1).strip()
        if len(ref) >= 2:
            result.invoice_ref = ref
            result.confidence += 0.15

    # ── Category by keywords (con word boundary per evitare false match come 'POS' in 'DISPOSTO') ──
    matched_cat = False
    for cat, subcat, keywords in _CATEGORY_KEYWORDS:
        for kw in keywords:
            # word boundary: keyword deve essere parola intera o frase intera
            pattern = r"\b" + re.escape(kw) + r"\b"
            if re.search(pattern, desc_upper):
                result.category = cat
                result.subcategory = subcat
                result.confidence += 0.3
                matched_cat = True
                break
        if matched_cat:
            break

    # Fallback: se è bonifico ma niente match
    if not matched_cat:
        is_bonifico = any(
            re.search(r"\b" + re.escape(b) + r"\b", desc_upper) for b in _BONIFICO_KEYWORDS
        )
        if is_bonifico:
            # Importi piccoli in uscita = quasi sempre commissione bancaria,
            # MAI un pagamento reale a un cliente/fornitore (Massimi feedback 2026-04-28)
            abs_amount = abs(amount or 0)
            if direction == "debit" and abs_amount < _FEE_AMOUNT_THRESHOLD_EUR:
                result.category = "fee"
                result.subcategory = "commissione_bonifico"
                result.counterparty = None  # non è una controparte reale
                result.confidence = max(result.confidence, 0.85)
            else:
                result.category = "income_invoice" if direction == "credit" else "expense_invoice"
                result.subcategory = "bonifico"
                result.confidence += 0.2
        else:
            result.category = "other"

    # Cap a 1.0
    result.confidence = min(result.confidence, 0.95)

    return result


def _clean_party(name: str) -> str:
    """Pulisce il nome controparte estratto: trimming, normalizzazione."""
    name = re.sub(r"\s+", " ", name).strip()
    # Rimuovi suffissi parassiti
    name = re.sub(r"\s+(?:BIC|IBAN|COD|VS|CRO|TRN)\.?$", "", name, flags=re.IGNORECASE)
    return name[:255]


# ── Step 2: LLM fallback ────────────────────────────────────

_LLM_PROMPT_SYSTEM = """Sei un esperto di contabilità italiana. Estrai dati strutturati da una descrizione di bonifico bancario italiana grezza.

IMPORTANTE — IDENTITÀ DEL TITOLARE:
Ti verrà comunicato il TITOLARE del conto (nome azienda + P.IVA). La "controparte"
è SEMPRE chi NON è il titolare. Se vedi MITT.:X e BENEF.:Y dove X è il titolare,
la controparte è Y. Se vedi MITT.:X dove X NON è il titolare, la controparte è X.
NON ritornare mai il titolare come counterparty.

Rispondi SOLO in JSON con questa struttura:
{
  "counterparty": "nome controparte pulito (es. 'QUBIKA SRL') — MAI il titolare del conto",
  "counterparty_iban": "IBAN controparte SOLO se è un vero IBAN (formato 'IT' + 25 char alfanumerici), altrimenti null",
  "invoice_ref": "riferimento fattura se presente (es. 'FT 2025/123'), altrimenti null",
  "category": "una di: income_invoice, expense_invoice, payroll, tax_f24, tax_iva, fee, transfer, loan_payment, interest, atm, pos, sepa_dd, refund, other",
  "subcategory": "sottocategoria opzionale (es. 'stipendio', 'mutuo', 'commissione')",
  "confidence": 0.0-1.0,
  "notes": "note libere (max 100 char)"
}

Regole categorizzazione:
- Bonifico ricevuto da CLIENTE/altra azienda → category='income_invoice'
- Bonifico inviato a FORNITORE/altra azienda → category='expense_invoice'
- Stipendio, busta paga, retribuzione, emolumenti, mensilità → category='payroll', subcategory='stipendio'
- Compenso amministratore, parcella professionista, co.co.co → category='payroll', subcategory='compenso'
- TFR, fine rapporto → category='payroll', subcategory='tfr'
- F24/Agenzia Entrate → category='tax_f24'
- Liquidazione/versamento IVA → category='tax_iva'
- Commissione/canone/imposta bollo/spese → category='fee'
- Premio polizza assicurativa → category='fee', subcategory='polizza'
- Rata mutuo/prestito/finanziamento → category='loan_payment'
- Interessi attivi/passivi → category='interest'

REGOLE CRITICHE — costi banca vs pagamenti reali:
- Bonifico USCITA con importo < 5 EUR (es. 0,70 EUR, 1,50 EUR, 2 EUR) →
  è SEMPRE una COMMISSIONE BONIFICO della banca, MAI un pagamento a un cliente/fornitore.
  Imposta category='fee', subcategory='commissione_bonifico', counterparty=null.
- "COSTO BONIFICO", "SPESE BONIFICO", "COMMISSIONE BONIFICO", "COMM BONIFICO" →
  category='fee', subcategory='commissione_bonifico', counterparty=null (è la banca, non un soggetto).
- Movimento senza controparte chiara e descrizione tipo "spese", "imposta", "bollo" →
  counterparty=null, category='fee'.

IMPORTANTE — IBAN:
- IBAN italiano valido = 'IT' + 2 cifre + 1 lettera + 22 caratteri alfanumerici (totale 27)
- Codici dispositivi tipo "0126040163715019" o "TRN: 0123..." NON sono IBAN, ritorna null
- confidence: 0.95+ se chiaro, 0.7-0.9 buono, < 0.7 ambiguo
"""


async def parse_with_llm(
    description: str,
    direction: str,
    amount: float,
    *,
    tenant_name: str | None = None,
    tenant_piva: str | None = None,
) -> ParsedTx:
    """Step 2: chiamata Anthropic Claude Sonnet 4.6 per parsing strutturato.

    Async (httpx). Default ANTHROPIC_PARSER_MODEL=claude-sonnet-4-6.
    Override possibile via env var per A/B test (es. claude-haiku-4-5 per
    minor costo, claude-opus-4-7 per max qualità).
    """
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY non configurata — LLM parser disabled")
        return ParsedTx(category="other", confidence=0.0, method="llm", notes="LLM not configured")

    model = os.getenv("ANTHROPIC_PARSER_MODEL", "claude-sonnet-4-6")

    titolare_info = ""
    if tenant_name or tenant_piva:
        titolare_info = (
            f"TITOLARE DEL CONTO: {tenant_name or ''} (P.IVA {tenant_piva or 'N/A'}). "
            "La controparte è SEMPRE diversa dal titolare.\n\n"
        )

    user_msg = (
        titolare_info
        + f"Descrizione: {description}\n"
        f"Direzione: {'ricevuto (credit)' if direction == 'credit' else 'inviato (debit)'}\n"
        f"Importo: {amount} EUR\n\n"
        "Rispondi SOLO con un oggetto JSON valido (no markdown, no testo prima/dopo)."
    )

    import httpx

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": model,
                    "max_tokens": 512,
                    "temperature": 0.0,
                    "system": _LLM_PROMPT_SYSTEM,
                    "messages": [{"role": "user", "content": user_msg}],
                },
            )
        if resp.status_code != 200:
            logger.error("Anthropic %s: %s", resp.status_code, resp.text[:200])
            return ParsedTx(category="other", confidence=0.0, method="llm", notes="LLM error")

        data = resp.json()
        # Anthropic content è un array di blocchi: prendi il primo blocco text
        text_blocks = [b for b in data.get("content", []) if b.get("type") == "text"]
        if not text_blocks:
            logger.error("Anthropic empty content: %s", data)
            return ParsedTx(category="other", confidence=0.0, method="llm", notes="LLM empty")
        content = text_blocks[0]["text"].strip()

        # Strip eventuali code fence che il modello a volte aggiunge
        if content.startswith("```"):
            content = content.split("```", 2)[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip("` \n")

        parsed = json.loads(content)

        return ParsedTx(
            counterparty=parsed.get("counterparty"),
            counterparty_iban=parsed.get("counterparty_iban"),
            invoice_ref=parsed.get("invoice_ref"),
            category=parsed.get("category") or "other",
            subcategory=parsed.get("subcategory"),
            confidence=float(parsed.get("confidence") or 0.7),
            method="llm",
            notes=(parsed.get("notes") or "")[:255],
        )
    except (httpx.HTTPError, json.JSONDecodeError, KeyError, ValueError) as e:
        logger.exception("LLM parse failed: %s", e)
        return ParsedTx(category="other", confidence=0.0, method="llm", notes=f"LLM error: {e}")


# ── Pipeline orchestratore ──────────────────────────────────

# Cache in-memory (process-local). Per multi-worker → Redis.
_PARSE_CACHE: dict[str, ParsedTx] = {}
LLM_THRESHOLD = 0.65  # Sotto questa confidence dei rules → fallback LLM


async def parse_transaction(
    description: str | None,
    direction: str,
    amount: float,
    *,
    use_llm: bool = True,
    use_cache: bool = True,
    tenant_name: str | None = None,
    tenant_piva: str | None = None,
) -> ParsedTx:
    """Pipeline completa: cache → rules → LLM se needed.

    Args:
        description: testo grezzo bonifico bancario
        direction: 'credit' (entrata) o 'debit' (uscita)
        amount: importo (signed)
        use_llm: se False salta lo step LLM
        use_cache: se False ignora cache (per re-parse)
        tenant_name: nome azienda titolare conto (per LLM context)
        tenant_piva: P.IVA titolare (per LLM context)
    """
    if not description:
        return ParsedTx(category="other", confidence=0.0, method="rules")

    # Cache key include tenant per evitare cross-contamination
    cache_key = _hash(f"{description}|{direction}|{tenant_piva or ''}")
    if use_cache and cache_key in _PARSE_CACHE:
        cached = _PARSE_CACHE[cache_key]
        return ParsedTx(**cached.__dict__)

    # Step 1: rules
    result = parse_with_rules(description, direction, amount)

    # Filtro: se rules ha estratto un counterparty che è il titolare stesso, scartiamolo
    if tenant_name and result.counterparty:
        if _normalize_name(result.counterparty) == _normalize_name(tenant_name):
            result.counterparty = None
            result.confidence = max(result.confidence - 0.4, 0.0)

    # Step 2: LLM fallback se rules incerti
    if use_llm and result.confidence < LLM_THRESHOLD:
        llm_result = await parse_with_llm(
            description, direction, amount,
            tenant_name=tenant_name, tenant_piva=tenant_piva,
        )
        # Filtro tenant: scartiamo se LLM ha messo il titolare come counterparty
        if tenant_name and llm_result.counterparty:
            if _normalize_name(llm_result.counterparty) == _normalize_name(tenant_name):
                llm_result.counterparty = None
        if llm_result.confidence > result.confidence:
            result = llm_result

    # Sanity check: counterparty_iban deve essere IBAN reale (IT + 25)
    if result.counterparty_iban and not re.match(r"^IT[0-9A-Z]{25}$", result.counterparty_iban.upper().strip()):
        result.counterparty_iban = None

    if use_cache:
        _PARSE_CACHE[cache_key] = result

    return result


def _normalize_name(name: str) -> str:
    """Normalizza nome azienda per confronto: upper, no punteggiatura, no SRL/SPA."""
    s = name.upper().strip()
    s = re.sub(r"[.,&'/-]", " ", s)
    s = re.sub(r"\b(S\.?R\.?L\.?|S\.?P\.?A\.?|SOC|SOCIETA|S\.?A\.?S\.?|S\.?N\.?C\.?)\b", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def cache_size() -> int:
    return len(_PARSE_CACHE)


def cache_clear() -> None:
    _PARSE_CACHE.clear()
