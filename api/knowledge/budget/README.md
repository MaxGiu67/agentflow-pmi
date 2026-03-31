# Knowledge Base Budget — AgentFlow PMI

Questa directory contiene la conoscenza che il Budget Agent usa per guidare
l'utente nella creazione del budget aziendale.

## File

| File | Contenuto |
|------|-----------|
| `01-tecniche-budgeting.md` | Tecniche (incremental, zero-based, activity-based) e quando usarle |
| `02-benchmark-settore.md` | Benchmark costi/margini per settore ATECO + EBITDA margins |
| `03-conto-economico-struttura.md` | Schema CE civilistico, mappatura domande → voci, calcoli automatici |
| `04-domande-per-settore.md` | Domande specifiche per 8 macro-settori (IT, ristorazione, commercio...) |
| `05-consigli-agente.md` | Regole di comportamento, frasi tipo, red/green flags, validazione |

## Come si usa

Il Budget Agent carica questi file quando l'utente chiede di creare il budget:

```python
# 1. Determina il settore dal codice ATECO del tenant
ateco = tenant.ateco_code  # es. "62.01"

# 2. Carica la tecnica giusta
tecnica = scegli_tecnica(tenant)  # da 01-tecniche-budgeting.md

# 3. Carica i benchmark del settore
benchmark = carica_benchmark(ateco)  # da 02-benchmark-settore.md

# 4. Carica le domande specifiche
domande = carica_domande(ateco)  # da 04-domande-per-settore.md

# 5. Costruisci il CE previsionale
ce = costruisci_ce(risposte)  # da 03-conto-economico-struttura.md

# 6. Valida con i consigli
validazione = valida_budget(ce, benchmark)  # da 05-consigli-agente.md
```

## Aggiornamento

Questi file vanno aggiornati quando:
- Cambiano i coefficienti di redditivita (tipicamente annuale)
- Cambiano le aliquote IRES/IRAP
- Si aggiungono nuovi settori
- Si raccolgono benchmark piu precisi dai dati reali degli utenti
