"""Parser `extra` + `description` transazioni A-Cube per estrarre CRO/TRN/invoice_ref.

A-Cube non normalizza il campo `extra` (varia per banca: Intesa, Unicredit, BPER, Fineco...).
Le info di riconciliazione (CRO, TRN, numero fattura) finiscono o dentro `extra`
(chiavi non standardizzate) o dentro `description` (testo libero).

Strategia:
1. Guardo chiavi note in `extra` (match per banca)
2. Regex di fallback sulla description

Usato da `acube_ob_service.sync_transactions` per popolare `enriched_cro` /
`enriched_invoice_ref` su BankTransaction, poi sfruttati dal modulo di riconciliazione.
"""

from __future__ import annotations

import re
from typing import Any

# Chiavi note nel campo `extra` per banca (best effort)
_EXTRA_CRO_KEYS = {
    "cro",
    "CRO",
    "bankOperationRef",
    "bank_operation_ref",
    "endToEndId",
    "endToEndRef",
    "operationRef",
    "referenceNumber",
}
_EXTRA_TRN_KEYS = {
    "trn",
    "TRN",
    "transactionRef",
    "transaction_reference",
    "transactionReference",
    "paymentRef",
}
_EXTRA_INVOICE_KEYS = {
    "invoiceNumber",
    "invoice_number",
    "invoiceRef",
    "fatturaNumero",
}

# Regex description — tolleranti a spazi/punteggiatura
_CRO_RE = re.compile(r"\bCRO[:\s.]*\s*([0-9A-Z]{10,16})\b", re.IGNORECASE)
_TRN_RE = re.compile(r"\bTRN[:\s.]*\s*([A-Z0-9]{16,35})\b", re.IGNORECASE)
_INVOICE_RE = re.compile(
    r"\b(?:FATT(?:URA)?|FT|FTR|INV(?:OICE)?)[.\s:]*(?:N(?:\.|RO?|UMERO)?|#)?[.\s:]*([A-Z0-9][A-Z0-9/\-]*[0-9][A-Z0-9/\-]*)\b",
    re.IGNORECASE,
)


def _first_from_keys(extra: dict | None, keys: set[str]) -> str | None:
    if not extra or not isinstance(extra, dict):
        return None
    for k in keys:
        v = extra.get(k)
        if v:
            return str(v).strip()
    return None


def _clean(s: str | None) -> str | None:
    if not s:
        return None
    s = s.strip().strip(".,;:-")
    return s or None


def parse_tx_extra(
    *, extra: Any = None, description: str | None = None
) -> dict[str, str | None]:
    """Ritorna CRO / TRN / invoice_ref normalizzati.

    Precedenza: chiavi dentro `extra` > regex su `description`.
    """
    cro = _clean(_first_from_keys(extra if isinstance(extra, dict) else None, _EXTRA_CRO_KEYS))
    trn = _clean(_first_from_keys(extra if isinstance(extra, dict) else None, _EXTRA_TRN_KEYS))
    invoice_ref = _clean(
        _first_from_keys(extra if isinstance(extra, dict) else None, _EXTRA_INVOICE_KEYS)
    )

    if description:
        if not cro:
            m = _CRO_RE.search(description)
            if m:
                cro = _clean(m.group(1))
        if not trn:
            m = _TRN_RE.search(description)
            if m:
                trn = _clean(m.group(1))
        if not invoice_ref:
            m = _INVOICE_RE.search(description)
            if m:
                invoice_ref = _clean(m.group(1))

    return {"cro": cro, "trn": trn, "invoice_ref": invoice_ref}
