# AI Parser Movimenti Bancari (Sprint 50)

Pipeline a 3 livelli per interpretare automaticamente le descrizioni grezze
dei bonifici bancari italiani e estrarre dati strutturati.

## Problema

A-Cube via PSD2 ritorna le descrizioni dei movimenti come testi grezzi della
banca, esempio reale Intesa Sanpaolo:

```
ACCR BON ISTANT COD. DISP.: 0126040163715019 CASH PhLoSu3O010420262004071
Acconto pagamento fattura Bonifico a Vostro favore disposto da:
MITT.: QUBIKA S.R.L. BENEF.: TAAL SRL BIC. ORD.: CCRTIT2TN00
```

Vogliamo invece estrarre:
- `counterparty` = "QUBIKA S.R.L."
- `category` = "income_invoice"
- `invoice_ref` = "FT 2025/123" se presente
- `confidence` = 0.85

## Architettura — pipeline 3 step

```
┌─────────────────────────────────────────────────────┐
│  Sync transactions A-Cube → bank_transactions       │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
        ┌─────────────────────────────┐
        │ STEP 1 — RULES (regex/kw)   │  ← gratis, ~70%
        │ tx_ai_parser.py             │
        │ confidence 0.0-0.95         │
        └─────┬───────────────────────┘
              │
       confidence < 0.65?
              │ sì
              ▼
        ┌─────────────────────────────┐
        │ STEP 2 — LLM fallback       │  ← $0.0005/tx, ~25%
        │ OpenAI GPT-4o-mini          │
        └─────┬───────────────────────┘
              │
              ▼
        ┌─────────────────────────────┐
        │ Cache (SHA256 hash)         │  ← hit rate 80%+
        └─────┬───────────────────────┘
              │
              ▼
        ┌─────────────────────────────┐
        │ STEP 3 — UI inline edit     │  ← user_corrected=true
        │ correzioni salvate          │
        └─────────────────────────────┘
```

## Categorie supportate

| `parsed_category` | Descrizione |
|---|---|
| `income_invoice` | Bonifico ricevuto da cliente |
| `expense_invoice` | Bonifico inviato a fornitore |
| `payroll` | Stipendio / TFR / contributi |
| `tax_f24` | F24 / Agenzia Entrate |
| `tax_iva` | Versamento IVA periodico |
| `fee` | Commissioni / canoni / polizze / bolli |
| `transfer` | Giroconto tra conti propri |
| `loan_payment` | Rata mutuo / prestito / leasing |
| `interest` | Interessi attivi/passivi |
| `atm` | Prelievo bancomat |
| `pos` | Pagamento POS |
| `sepa_dd` | Addebito SEPA Direct Debit |
| `refund` | Rimborso / storno |
| `other` | Non classificato |

## API endpoint

### POST `/api/v1/banking/connections/{id}/parse`

Ri-parsa tutte le transazioni della connection.

```bash
POST /banking/connections/abc-123/parse?use_llm=true&force=false&limit=500
```

Query params:
- `use_llm` (bool, default `true`): se `false` salta lo step LLM
- `force` (bool, default `false`): re-parsa anche tx già parsate (escluse `user_corrected`)
- `limit` (int, optional): max tx in questa chiamata

Response:
```json
{
  "connection_id": "abc-123",
  "parsed": 35,
  "rules_count": 28,
  "llm_count": 7,
  "use_llm": true,
  "force": false,
  "message": "Parsed 35 transazioni (28 rules, 7 LLM)"
}
```

### PATCH `/api/v1/banking/connections/transactions/{tx_id}/correct`

Correzione manuale del parse (alza `user_corrected=true`).

```json
{
  "counterparty": "QUBIKA S.R.L.",
  "category": "income_invoice",
  "invoice_ref": "FT 2025/123"
}
```

## Performance e costi

### Volumi attesi
- 1 cliente PMI media: 50-200 movimenti/mese
- 50 clienti (commitment A-Cube AISP): 2.500-10.000 movimenti/mese

### Costi LLM
- **GPT-4o-mini**: $0.0005 per transazione (input ~200 token, output ~150 token)
- Pipeline ottimizzata (rules first):
  - 70% rules-only → $0
  - 25% rules+LLM → $0.0005
  - 5% manual → $0
- Costo medio: $0.000125 per transazione
- 10.000 tx/mese → $1.25/mese
- 1M tx/mese → $125/mese

### Cache
SHA256 di `description|direction` → output. Cache in-memory process-local.
Hit rate atteso: 80%+ dopo il primo mese (boilerplate banche italiane si ripetono).

## Auto-parse

Durante `sync_transactions` le nuove tx vengono auto-parsate con **rules-only**
(no LLM, gratis e veloce). L'upgrade LLM è on-demand via endpoint `/parse`.

## Feedback loop

Quando l'utente corregge un parse via UI:
1. `parsed_counterparty/category/invoice_ref` aggiornati
2. `user_corrected = true` → la tx non viene sovrascritta da reparse
3. `parsed_method = "manual"` → `parsed_confidence = 1.0`

Future enhancement: aggregare correzioni in `categorization_feedback` per
fine-tuning automatico delle regole / system prompt LLM.

## File interessati

- `api/modules/banking/tx_ai_parser.py` — pipeline parser (rules + LLM + cache)
- `api/modules/banking/acube_ob_service.py` — `parse_transactions()` + `correct_transaction_parse()`
- `api/modules/banking/acube_ob_router.py` — endpoint `/parse` e `/correct`
- `api/db/models/accounting.py` — campi `parsed_*` su `BankTransaction`
- `frontend/src/pages/banca/MovimentiPage.tsx` — UI con badges + expand + bottone "Classifica con AI"
- `tests/test_tx_ai_parser.py` — 11 unit test su pattern italiani comuni
