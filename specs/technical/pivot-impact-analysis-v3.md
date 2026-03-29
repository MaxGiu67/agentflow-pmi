# Impact Analysis — Pivot 5: Da Gestionale Contabile a Controller Aziendale AI

**Data:** 2026-03-28
**Documento sorgente:** `brainstorm/07-compare-llm.md`
**Scope:** Architetturale — cambia il posizionamento del prodotto e aggiunge feature strutturali

---

## Causa del Pivot

### Cosa cambia
AgentFlow passa da **gestionale contabile** (registra, categorizza, bilancia) a **controller aziendale AI** (importa silenziosamente, interpreta, consiglia). Il sistema non sostituisce il programma di contabilita — lo affianca come strumento di supporto per l'imprenditore.

### Perche
1. L'imprenditore target non vuole fare il contabile — vuole capire come va l'azienda
2. Un secondo gestionale contabile crea attrito (doppia registrazione)
3. Il valore e' nell'interpretazione dei dati, non nella loro registrazione
4. Il differenziante competitivo e' "zero data entry, massima interpretazione"

### Scope
- **Nuovo posizionamento di prodotto** → impatta Vision e PRD
- **12 flussi di importazione** (7 nuovi) → impatta Stories, Tech Spec, Schema DB, Sprint Plan
- **6 agenti di gestione** (4 nuovi/potenziati) → impatta Tech Spec, Stories, Sprint Plan
- **Budget Agent conversazionale** → nuova feature core
- **Principio CRUD manuale per ogni voce** → impatta tutti i moduli
- **Import silenzioso + max 3 azioni** → impatta UX/Wireframes

---

## Inventario file impattati

### RIFARE (rigenerare completamente)

| File | Motivo |
|------|--------|
| `specs/03-user-stories.md` | Serve un nuovo set US-41+ per: import banca (PDF/CSV/API), corrispettivi XML, F24 import, saldi bilancio (Excel/PDF/XBRL), Budget Agent conversazionale, Controller Agent, CRUD manuale per ogni voce, import silenzioso, Completeness Score, doppio canale notifiche |
| `specs/05-sprint-plan.md` | Nuovi sprint per le feature aggiunte. Sprint 11-16 stimati |
| `specs/ux/wireframes.md` | La home diventa conversazionale (non tabellare), Budget vs Consuntivo, import wizard banca/bilancio, Completeness Score, max 3 azioni |

### AGGIORNARE (modifica parziale)

| File | Cosa Cambiare |
|------|--------------|
| `specs/01-vision.md` | Aggiornare posizionamento: da "agente contabile" a "controller aziendale AI". Aggiornare value proposition. Aggiungere principio "zero data entry". Aggiornare metriche successo (engagement > accuracy) |
| `specs/02-prd.md` | Aggiungere EPIC 10 (Import Pipeline), EPIC 11 (Management Agents), EPIC 12 (Budget & Controller). Aggiornare MoSCoW. Aggiungere feature: B1-B12 import, Budget Agent, Controller Agent, CRUD manuale, doppio canale, Completeness Score |
| `specs/04-tech-spec.md` | Nuovi endpoint: import-statement (banca), import-corrispettivi, import-f24, import-bilancio, budget CRUD, controller queries. Nuovi modelli DB: budget_entries, budget_lines, corrispettivi, bank_statement_imports. Architettura LLM extraction per PDF |
| `specs/database/schema.md` | Aggiungere tabelle: corrispettivi, budget_entries, budget_lines, recurring_contracts, loans, bank_statement_imports. Aggiungere campo `source` (import/manual) su tutte le tabelle esistenti che hanno CRUD |
| `specs/testing/test-strategy.md` | Aggiungere strategia test per: LLM extraction (mock + golden files), import silenzioso, Budget Agent conversazionale, CRUD manuale |
| `specs/testing/test-map.md` | Aggiungere mapping AC per nuove stories US-41+ |

### INVARIATO

| File | Motivo |
|------|--------|
| `specs/07-implementation.md` | Documenta lo storico US-01 a US-40 gia completato — non va toccato, si aggiunge in coda |
| `specs/08-validation.md` | Report di validazione v0.1-v0.4 rimane valido. Nuova validazione sara' separata |
| `specs/technical/ADR-007-drop-odoo.md` | Decisione confermata e rafforzata dal pivot |
| `specs/technical/flusso-informazioni.md` | Flusso esistente resta valido, si estende |
| `specs/technical/analisi-gap-ceo.md` | Gap gia identificati, ora li implementiamo |
| `specs/sprint-reviews/sprint-final-review.md` | Review storica, non va toccata |

---

## Nuove User Stories previste (US-41+)

### EPIC 10 — Import Pipeline (silenzioso + CRUD)

| ID | Titolo | Priorita | SP | Note |
|----|--------|----------|-----|------|
| US-44 | Import estratto conto bancario (PDF + LLM) | MUST | 8 | 2 formati banca (UniCredit, Credit Agricole), LLM extraction, preview |
| US-45 | Import estratto conto bancario (CSV) | MUST | 3 | Auto-detect colonne, fallback |
| US-46 | CRUD manuale movimenti bancari | MUST | 5 | Aggiungi/modifica/elimina singolo movimento |
| US-47 | Import corrispettivi XML (COR10) | MUST | 5 | Parser XML namespace AdE, scrittura contabile auto |
| US-48 | CRUD manuale corrispettivi | MUST | 3 | Inserimento giornaliero manuale |
| US-49 | Import F24 versamenti (PDF + LLM) | MUST | 5 | Codici tributo, importi, periodo riferimento |
| US-50 | CRUD manuale F24 | MUST | 3 | Inserimento versamento manuale |
| US-51 | Import saldi bilancio (Excel/CSV) | MUST | 8 | Auto-detect, mapping LLM conti, preview, quadratura |
| US-52 | Import saldi bilancio (PDF + LLM) | MUST | 5 | Estrazione testo, mapping conti |
| US-53 | Import saldi bilancio (XBRL) | SHOULD | 5 | Parser tassonomia itcc-ci, mapping CEE |
| US-54 | CRUD manuale saldi bilancio | MUST | 3 | Inserimento wizard (saldi principali) |
| US-55 | Import contratti ricorrenti (PDF + LLM) | SHOULD | 5 | Affitto, leasing, utenze → importo/frequenza |
| US-56 | CRUD manuale contratti ricorrenti | SHOULD | 3 | Inserisci ricorrenza a mano |
| US-57 | Import piano ammortamento finanziamenti | SHOULD | 5 | Rate, capitale, interessi, debito residuo |
| US-58 | CRUD manuale finanziamenti | SHOULD | 3 | Inserisci rata manuale |
| US-59 | Ammortamenti auto da fatture cespiti | SHOULD | 5 | Auto-detect immobilizzazioni, aliquota ministeriale, conferma |

### EPIC 11 — Management Agents (doppio canale)

| ID | Titolo | Priorita | SP | Note |
|----|--------|----------|-----|------|
| US-60 | Budget Agent — creazione conversazionale | MUST | 8 | Proposta da storico, Q&A naturale, aggiustamenti |
| US-61 | Budget Agent — controllo consuntivo mensile | MUST | 8 | Budget vs actual, scostamenti, analisi cause |
| US-62 | Controller Agent — "Come sto andando?" | MUST | 5 | KPI sintetici, trend, confronto periodi |
| US-63 | Controller Agent — "Dove perdo soldi?" | SHOULD | 5 | Analisi costi per categoria, anomalie |
| US-64 | Cash Flow Agent potenziato (dati banca reali) | MUST | 5 | Previsione con movimenti reali, non solo fatture |
| US-65 | Adempimenti Agent proattivo | MUST | 5 | Push 10gg prima scadenza, calcolo importi |
| US-66 | Alert Agent (anomalie, scaduti, sbilanciamenti) | SHOULD | 5 | Pattern detection, P.IVA cessate |
| US-67 | Doppio canale notifiche (dashboard + WhatsApp/Telegram) | MUST | 5 | Ogni alert → push su messaging |

### EPIC 12 — UX Controller (non gestionale)

| ID | Titolo | Priorita | SP | Note |
|----|--------|----------|-----|------|
| US-68 | Home conversazionale (non tabellare) | MUST | 8 | Saluto + situazione + azioni (max 3) |
| US-69 | Completeness Score (framing positivo) | MUST | 5 | "Hai sbloccato X" + "Prossimo sblocco: Y" |
| US-70 | Email auto-generata per commercialista | SHOULD | 3 | Template per richiesta bilancio/dati |
| US-71 | Import silenzioso con eccezioni | MUST | 5 | Background import, solo anomalie segnalate |

**Totale nuove stories: 28 | SP stimati: ~148 | Sprint stimati: 6-7**

---

## Impatto Database

### Nuove tabelle

| Tabella | Campi chiave | Relazioni |
|---------|-------------|-----------|
| `corrispettivi` | tenant_id, data, dispositivo_id, piva_esercente, aliquota_iva, imponibile, imposta, totale_contanti, totale_elettronico, num_documenti, source (import/manual) | → journal_entries |
| `budget_entries` | tenant_id, year, status (draft/active/archived), created_by_agent (bool), notes | — |
| `budget_lines` | budget_entry_id, month, category, description, amount_planned, amount_actual (computed) | → budget_entries |
| `recurring_contracts` | tenant_id, description, counterpart, amount, frequency (monthly/quarterly/annual), start_date, end_date, category, source | → cash_flow predictions |
| `loans` | tenant_id, description, bank, original_amount, interest_rate, start_date, end_date, monthly_payment, remaining_balance, source | → cash_flow predictions |
| `bank_statement_imports` | tenant_id, bank_account_id, filename, period_from, period_to, status (pending/processed/error), extraction_method (llm/csv/api), raw_text | → bank_transactions |
| `completeness_scores` | tenant_id, source_type, status (connected/pending/not_configured), last_sync, unlocked_features (JSONB) | — |

### Modifiche a tabelle esistenti

| Tabella | Modifica |
|---------|----------|
| `bank_transactions` | Aggiungere `source` ENUM (import_pdf, import_csv, open_banking, manual) |
| `payroll_costs` | Aggiungere `source` ENUM (import_pdf, manual) |
| `expenses` | Aggiungere `source` ENUM (import_ocr, manual) — gia presente come draft/approved |
| `f24_documents` | Aggiungere `source` ENUM (import_pdf, calculated, manual) |
| `assets` | Aggiungere `source` ENUM (auto_from_invoice, manual), `detected_from_invoice_id` |

---

## Impatto API — Nuovi endpoint

| # | Metodo | Path | Scopo |
|---|--------|------|-------|
| 62 | POST | `/bank-accounts/{id}/import-statement` | Import PDF estratto conto (LLM extraction) |
| 63 | POST | `/bank-accounts/{id}/import-csv` | Import CSV movimenti bancari |
| 64 | POST/GET/PUT/DELETE | `/bank-transactions` | CRUD manuale movimenti |
| 65 | POST | `/corrispettivi/import-xml` | Import XML corrispettivi COR10 |
| 66 | POST/GET/PUT/DELETE | `/corrispettivi` | CRUD manuale corrispettivi |
| 67 | POST | `/f24/import-pdf` | Import PDF ricevuta F24 |
| 68 | POST | `/accounting/import-bilancio` | Import saldi (Excel/CSV/PDF/XBRL) |
| 69 | POST/GET/PUT/DELETE | `/accounting/initial-balances` | CRUD manuale saldi iniziali |
| 70 | POST/GET/PUT/DELETE | `/budget` | CRUD budget (entries + lines) |
| 71 | POST | `/budget/generate` | Budget Agent genera proposta da storico |
| 72 | GET | `/budget/vs-actual` | Confronto budget vs consuntivo |
| 73 | POST/GET/PUT/DELETE | `/recurring-contracts` | CRUD contratti ricorrenti |
| 74 | POST/GET/PUT/DELETE | `/loans` | CRUD finanziamenti/mutui |
| 75 | GET | `/completeness-score` | Stato completezza per onboarding |
| 76 | POST | `/notifications/push` | Invio notifica su canale esterno |

---

## Rischi del pivot

| Rischio | Probabilita | Impatto | Mitigazione |
|---------|-------------|---------|-------------|
| LLM extraction inaffidabile su PDF banca/F24 | Media | Alto | Golden file testing, fallback CSV manuale, preview obbligatorio |
| Scope creep (28 nuove stories) | Alta | Medio | MoSCoW rigoroso, fase 1 solo MUST (16 stories) |
| Parser corrispettivi XML imprevisti | Bassa | Basso | Formato standard AdE, 90 file esempio disponibili |
| Budget Agent conversazione incoerente | Media | Medio | Prompt engineering, guardrail su numeri, conferma utente |
| Doppio canale (WhatsApp) complessita | Media | Medio | Fase 1 solo Telegram (gia implementato), WhatsApp in fase 2 |

---

## Ordine di riesecuzione consigliato

```
1. /dev-prd        → Aggiornare PRD con EPIC 10-12, nuovo posizionamento
2. /dev-stories     → Generare US-44 a US-71 con AC
3. /dev-spec        → Aggiornare tech spec (endpoint 62-76, nuove tabelle, architettura LLM)
4. /dev-sprint      → Pianificare Sprint 11-16 (nuove stories)
5. /dev-review      → Verificare coerenza post-pivot
6. /dev-implement   → Iniziare da Sprint 11 (Import banca + corrispettivi)
```
