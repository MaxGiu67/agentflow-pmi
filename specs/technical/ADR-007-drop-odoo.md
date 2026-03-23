# ADR-007: Drop Odoo — AccountingEngine interno

**Data:** 2026-03-23
**Stato:** Approvata
**Revoca:** ADR-002 (Odoo headless come engine contabile)
**Autore:** Decisione emersa da sessione brainstorming (@Davide, @Nicola, @Matteo)

---

## Contesto

ADR-002 scelse Odoo CE 18 + OCA l10n-italy come engine contabile headless, motivando:
- "Partita doppia da zero = 6+ mesi"
- "80+ moduli IT gia testati"

Dopo l'implementazione di Sprint 1-3 (12 stories, 92 test PASS), la realta e diversa:

1. **Il 70% della contabilita e gia nel nostro codice** — JournalEntry, JournalLine, ContaAgent, piano dei conti, multi-IVA, reverse charge, quadratura dare/avere
2. **L'OdooClient e un mock** — il sistema funziona perfettamente senza Odoo reale
3. **Odoo non e mai entrato nel flusso** — ogni lettura (dashboard, scritture, fatture) avviene dal DB FastAPI
4. **Il costo del doppio DB supera il beneficio** — consistenza, latenza XML-RPC, multi-tenancy esplosiva, debugging cross-system

## Decisione

**Eliminare Odoo. Sostituire OdooClient con AccountingEngine interno.**

Approccio: clean room implementation basata sulla **conoscenza fiscale** estratta dai moduli OCA (non copia di codice — i moduli OCA usano l'ORM Odoo, non ricopiabile).

## Analisi dei moduli OCA — Cosa replicare

Dall'analisi del codice sorgente OCA l10n-italy (branch 18.0):

### 1. Registri IVA (`l10n_it_vat_registries` v18.0.1.2.0)

**Riferimento normativo:** DPR 26/10/1972 n. 633

**Logica OCA:**
- 3 tipi registro: vendite (customer), acquisti (supplier), corrispettivi
- Filtra solo tasse con `_l10n_it_filter_kind("vat")`, esclude tasse con `exclude_from_registries = True`
- Reverse charge: le autofatture appaiono in ENTRAMBI i registri (acquisti + vendite), con logica di segno per evitare doppio conteggio (skip IVA debito su acquisti, skip IVA credito su vendite)
- Split payment: per group tax con figli split payment, importo tassa e debito vengono dal figlio ma detraibile no
- Classificazione documento: "NC" (nota credito) o "FA" (fattura)
- Totali per codice tassa: tupla a 9 elementi (nome, base, saldo, detraibile, indetraibile, debito, credito, saldo cliente, saldo fornitore)
- Numerazione progressiva pagine per anno solare

**Nostro AccountingEngine:**
```python
class VatRegistryService:
    # Query su journal_lines raggruppate per aliquota IVA
    # Separazione IVA detraibile vs indetraibile (basata su tipo conto)
    # Reverse charge: stessa fattura in entrambi i registri con segni opposti
    # Numerazione progressiva: ROW_NUMBER() PARTITION BY anno
    # Output: PDF/XLSX con totali per aliquota
```
**Stima:** 2-3 giorni

---

### 2. Liquidazione IVA (`l10n_it_account_vat_period_end_settlement` v18.0.1.0.5)

**Il modulo piu complesso.** Formula OCA:
```
dovuto = IVA_debito (vendite)
       - IVA_credito (acquisti, solo detraibile)
       - crediti_generici
       - credito_periodo_precedente
       + debito_periodo_precedente
       - crediti_imposta
       + interessi (1% se trimestrale, solo se dovuto > 0)
       - acconto_IVA
```

**Edge case gestiti da OCA:**
- Carry-forward credito cross-anno (flaggato separatamente)
- Interessi solo su trimestrale e solo se dovuto > 0
- Acconto IVA dicembre: 4 metodi (storico, previsionale, analitico, soggetti particolari)
- Soglia minima versamento: se dovuto < €25.82, non si versa (accumula)
- Scrittura contabile di liquidazione con split pagamento
- Tracking residuo: quando residuo = 0, stato → "paid"

**Codici tributo F24:**
- Mensile: 6001-6012
- Trimestrale: 6031 (Q1), 6032 (Q2), 6033 (Q3), 6034 (Q4/saldo annuale)
- Acconto: 6013 (mensile) o 6035 (trimestrale)

**Scadenze:**
- Mensile: 16 del mese successivo
- Trimestrale: Q1→16/05, Q2→20/08, Q3→16/11, Q4→16/03 anno dopo
- Acconto: 27 dicembre

**Nostro AccountingEngine:**
```python
class VatSettlementService:
    # Fase 1 (MVP): formula base senza acconto
    # Fase 2: acconto con metodo storico
    # Fase 3: tutti e 4 i metodi acconto
    # Tabella fiscal_rules per soglie/percentuali configurabili
```
**Stima:** 3-4 giorni (fase 1: 2 giorni, fasi 2-3: +2 giorni)

---

### 3. Piano dei conti CEE (`l10n_it_account` + `l10n_it_financial_statements_report`)

**Mapping tipo conto → sezione CEE (da OCA):**

| Tipo conto Odoo | Sezione CEE | Segno |
|----------------|-------------|-------|
| receivable, cash, current_assets, non_current_assets, fixed_assets, prepayments | **Attivo** | +1 |
| payable, credit_card, current_liabilities, non_current_liabilities | **Passivo** | -1 |
| equity | **Passivo (Patrimonio netto)** | -1 |
| income, other_income | **Ricavi** | -1 |
| expense, cost_of_revenue, depreciation, direct_costs | **Costi** | +1 |

**Struttura bilancio CEE (art. 2424-2425 c.c.):**
```
STATO PATRIMONIALE
  ATTIVO                          PASSIVO
  A) Crediti vs soci              A) Patrimonio netto
  B) Immobilizzazioni             B) Fondi rischi
     I. Immateriali               C) TFR
     II. Materiali                D) Debiti
     III. Finanziarie             E) Ratei e risconti
  C) Attivo circolante
  D) Ratei e risconti

CONTO ECONOMICO
  A) Valore della produzione
  B) Costi della produzione
  Differenza A-B
  C) Proventi e oneri finanziari
  D) Rettifiche di valore
  Risultato prima delle imposte
  22) Imposte
  23) Utile (perdita) d'esercizio
```

**Gia fatto al 90%.** Manca: mapping `account_code → voce CEE` completo e report formattato.

**Stima:** 1-2 giorni

---

### 4. Ritenute d'acconto (`l10n_it_withholding_tax` — disponibile solo in 16.0)

**Formula OCA:**
```
base = round(importo_fattura * coefficiente_base, 2)
ritenuta = round(base * aliquota / 100, 2)
netto_da_pagare = totale_fattura - ritenuta
```

**Ciclo di vita a 3 stati:** dovuta → applicata (al pagamento) → versata (F24)

**5 tipi:** ritenuta, enasarco, inps, enpam, altro

**Edge case:**
- Aliquote variabili nel tempo (date_start/date_stop con validazione overlap)
- Calcolo proporzionale su pagamento parziale
- Storno su nota credito (inversione segno)
- Pagamento automatico secondario per la quota ritenuta

**Scadenza F24:** 16 del mese successivo al PAGAMENTO (non alla fattura)

**Nostro AccountingEngine:**
```python
class WithholdingTaxService:
    # Fase 1 (MVP): ritenuta standard 20% su professionisti
    # Fase 2: multi-aliquota, ENASARCO, INPS
    # Integrazione con parser XML: tag <DatiRitenuta>
```
**Stima:** 2 giorni (fase 1: 1 giorno)

---

### 5. Imposta di bollo (`l10n_it_account_stamp`)

**Logica OCA:**
- Bollo €2.00 se somma importi righe esenti IVA > soglia (€77.47 configurabile)
- Natura IVA esenti: N1, N2.1, N2.2, N3, N4 (codici FatturaPA)
- Due modalita: automatica (al posting) o manuale (toggle utente)
- Sync con tag `<DatiBollo>` nel XML FatturaPA
- Versamento trimestrale F24 codice 2501

**Stima:** 0.5 giorni (logica gia nella US-35)

---

### 6. Libro Giornale (`l10n_it_central_journal_reportlab`)

Non nella lista prioritaria originale ma **importante per il commercialista:**
- Libro giornale = tutte le scritture in ordine cronologico con numerazione progressiva
- Obbligo di legge: art. 2216 c.c.
- Formato: data, numero, descrizione, dare, avere, saldi progressivi

**Stima:** 1 giorno (query su journal_entries ordinata per data)

---

## Piano di implementazione

| Fase | Cosa | Giorni | Sprint | Validazione commercialista |
|------|------|:------:|--------|---------------------------|
| 0 | ADR-007 approvata, rimuovi OdooClient mock | 0.5 | Ora | No |
| 1 | Tabella `fiscal_rules` (regole configurabili) | 1 | 4 | No |
| 2 | Registro IVA acquisti/vendite | 2-3 | 4 | Si (€200) |
| 3 | Liquidazione IVA base (senza acconto) | 2 | 5-6 | Si (incluso) |
| 4 | Mapping CEE completo | 1 | 5-6 | Si (incluso) |
| 5 | Ritenute d'acconto base (20%) | 1 | 7 | No |
| 6 | Bollo automatico | 0.5 | 7 | No |
| 7 | Bilancio CEE report | 2 | 8+ | Si (€200) |
| 8 | Liquidazione IVA avanzata (acconto) | 2 | 8+ | Si (incluso) |
| **Totale** | | **12-14 gg** | | **€400-600** |

## Architettura target

```
docker-compose.yml:
  api:        FastAPI + AccountingEngine interno
  postgres:   Un solo PostgreSQL (tutte le tabelle)
  redis:      Event bus + cache

Niente Odoo. Niente secondo database. Niente XML-RPC.
```

### Nuova struttura moduli

```
api/
  modules/
    fiscal/                          # NUOVO — sostituisce adapters/odoo.py
      accounting_engine.py           # Registrazione scritture (ex ContaAgent logic)
      vat_registry.py                # Registro IVA (da OCA l10n_it_vat_registries)
      vat_settlement.py              # Liquidazione IVA (da OCA l10n_it_account_vat_period_end_settlement)
      withholding_tax.py             # Ritenute d'acconto (da OCA l10n_it_withholding_tax)
      stamp_duty.py                  # Bollo (da OCA l10n_it_account_stamp)
      balance_sheet.py               # Bilancio CEE (da OCA l10n_it_financial_statements_report)
      fiscal_rules.py                # Tabella regole configurabili
      cee_mapping.py                 # Mapping codice conto → voce CEE
```

### Nuova tabella fiscal_rules

```sql
CREATE TABLE fiscal_rules (
    id UUID PRIMARY KEY,
    key VARCHAR(100) NOT NULL,          -- es. "iva_ordinaria", "soglia_bollo"
    value VARCHAR(255) NOT NULL,        -- es. "0.22", "77.47"
    value_type VARCHAR(20) NOT NULL,    -- decimal, integer, boolean, string
    valid_from DATE NOT NULL,
    valid_to DATE,                      -- NULL = ancora in vigore
    law_reference VARCHAR(255),         -- es. "DPR 633/72 art. 16"
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Rischi e mitigazioni

| Rischio | Probabilita | Mitigazione |
|---------|-------------|-------------|
| Errore contabile non rilevato | Media | Validazione commercialista + test con 50+ fatture reali |
| Cambio normativa non gestito | Bassa | NormativoAgent (US-28) + fiscal_rules configurabili |
| Commercialista non accetta output | Bassa | Export CSV/PDF standard + revisione output pre-rilascio |
| Casi fiscali complessi (IVA per cassa, pro-rata) | N/A | Esplicitamente NON supportati in v0.1, disclaimer chiaro |

## Scope esplicito v0.1 — cosa NON supportiamo

```
NON SUPPORTATO (disclaimer all'utente):
  - IVA per cassa (art. 32-bis D.L. 83/2012)
  - Ventilazione corrispettivi
  - Pro-rata di detraibilita IVA
  - Split payment PA
  - Regime OSS/IOSS
  - Intrastat
  - Ri.Ba. (ricevute bancarie)
  → "Per questi casi, consulta il tuo commercialista"
```

## Conseguenze

### Positive
- **Un solo database** — consistenza transazionale garantita
- **Zero latenza** — niente XML-RPC, tutto in-process
- **Deploy semplice** — 3 container (api + postgres + redis)
- **Multi-tenancy scalabile** — tenant_id su ogni tabella, un solo DB
- **Full control** — adattiamo il codice senza aspettare community OCA
- **Nessuna dipendenza esterna** per la contabilita
- **Costo infrastruttura ridotto** — ~€30/mese vs ~€80/mese con Odoo

### Negative
- **12-14 giorni** di sviluppo aggiuntivo per moduli fiscali
- **€400-600** di consulenza commercialista
- **Responsabilita** della correttezza contabile interamente nostra
- **Scope limitato** — casi complessi non supportati in v0.1

## Riferimenti normativi (estratti da OCA)

- **DPR 26/10/1972 n. 633** — Legge IVA fondamentale, registri, liquidazione
- **Art. 2424-2425 c.c.** — Schema bilancio CEE
- **Art. 2216 c.c.** — Libro giornale
- **DPR 642/72, Tariffa art. 13.1** — Imposta di bollo
- **D.L. 83/2012 art. 32-bis** — IVA per cassa (non supportato v0.1)

---
_ADR-007 — Proposta 2026-03-23_
