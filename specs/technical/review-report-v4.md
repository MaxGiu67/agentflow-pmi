# Review Report — Fase 4 (Tech Spec)
Data: 2026-03-22

## Risultato: PASS (post-fix — tutte le contraddizioni risolte)

---

## Pass 1: Completeness Check

Checklist Fase 4 da `phase-checklists.md`:

| # | Item | Esito | Dettaglio |
|---|------|-------|-----------|
| 1 | Stack tecnologico definito con motivazione | ✅ PASS | Tabella 14 righe, ogni riga con tecnologia + motivazione |
| 2 | Diagramma architettura (ASCII) | ✅ PASS | 2 diagrammi: Fase 1-2 (singolo tenant) + Fase 3 (multi-tenant) |
| 3 | Schema Database con CREATE TABLE completo | ✅ PASS | 18 tabelle inline + file canonico `database/schema.md` + 22 indici |
| 4 | API Endpoints definiti (path, metodo, request, response, errori) | ⚠️ PARTIAL | 56 endpoint con path, metodo, auth, descrizione. **Mancano request/response JSON e error codes per endpoint** |
| 5 | Struttura file progetto | ✅ PASS | Directory tree completo: backend (12 moduli), frontend (10 pagine), tests, odoo |
| 6 | Regole di business elencate | ✅ PASS | 10 BR (BR-01→BR-10) con riferimento a US e AC specifici |
| 7 | Sezione sicurezza | ✅ PASS | Threat model (5 vettori), GDPR, security roadmap P0-P2, compliance italiana, budget |
| 8 | Performance target con numeri | ✅ PASS | 12 metriche con valori numerici (p95 200ms→2s, OCR <3s, DB <50ms) |
| 9 | Test strategy con framework e coverage | ✅ PASS | Tabella riassuntiva + file dettagliato `testing/test-strategy.md` |
| 10 | Mappatura Story → Endpoint | ⚠️ PARTIAL | 35/40 stories mappate. **5 stories mancanti** (vedi Pass 2) |
| 11 | Almeno 1 ADR documentato | ✅ PASS | 6 ADR (ADR-001→ADR-006) |

**Score: 9/11 PASS pieno + 2/11 PARTIAL = 9.5/11 (86%)**

---

## Pass 2: Adversarial Review

### Contraddizioni (CRITICAL)

**[CONTRADICTION-01] Schema inline ≠ Schema canonico**
Lo schema CREATE TABLE in `04-tech-spec.md` (righe 168-455) è **significativamente diverso** dal file canonico `database/schema.md`. Il file canonico ha campi aggiuntivi critici in quasi tutte le tabelle:

| Tabella | Campi mancanti nell'inline | Impatto |
|---------|---------------------------|---------|
| `tenants` | `piva`, `codice_ateco`, `updated_at` | P.IVA è campo critico per business logic |
| `users` | `password_hash`, `spid_token`, `spid_token_expires_at`, `failed_login_attempts`, `locked_until` | Sicurezza auth compromessa senza questi |
| `invoices` | `document_type`, `numero_fattura`, `emittente_piva`, `emittente_nome`, `data_fattura`, `importo_netto`, `importo_iva`, `importo_totale`, `raw_xml`, `has_ritenuta`, `has_bollo`, `processing_status` | 12 campi mancanti — schema inutilizzabile per US-04/US-05 |
| `fiscal_deadlines` | `codice_tributo`, `related_f24_id`, `notified_at`, `completed_at` | Link F24 mancante per US-38 |
| `expenses` | `merchant`, `ocr_data`, `approved_at`, `rejection_reason`, `reimbursement_status` | Workflow approvazione incompleto |
| `assets` | `ministerial_code`, `disposal_type`, `gain_loss`, `odoo_asset_id` | Plus/minusvalenza non calcolabile |
| `bank_transactions` | `value_date`, `match_type`, `match_confidence` | Riconciliazione degradata |

**Raccomandazione:** Eliminare lo schema inline in `04-tech-spec.md` e sostituirlo con un riferimento al file canonico `database/schema.md`, oppure sincronizzare i due file.

**[CONTRADICTION-02] Numerazione endpoint duplicata**
Nella tabella API (righe 474-536), i numeri #3-7 compaiono **due volte**:
- Prima volta: #3=`/auth/token`, #4=`/auth/spid/init`, #5=`/auth/spid/callback`, #6=`/cassetto/sync`, #7=`/cassetto/status`
- Seconda volta: #3=`/invoices` GET, #4=`/invoices/{id}`, #5=`/invoices/{id}/verify`, #6=`/invoices/upload`, #7=`/accounting/chart`

**Raccomandazione:** Rinumerare sequenzialmente da 1 a 56.

**[CONTRADICTION-03] Campo `raw_data JSONB` vs `raw_xml TEXT`**
La tabella `invoices` nell'inline usa `raw_data JSONB`, mentre `database/schema.md` usa `raw_xml TEXT` + `structured_data JSONB`. Sono semanticamente diversi — uno generico, l'altro specifico per FatturaPA XML.

**Raccomandazione:** Allineare a `raw_xml TEXT` + `structured_data JSONB` del file canonico (più appropriato per FatturaPA).

### Stories mancanti nella mappatura (HIGH)

**[FINDING-01] 5 stories non mappate in Story → Endpoint**
Le seguenti stories v0.2 non compaiono nella tabella di mappatura:

| Story | Descrizione | Endpoint atteso |
|-------|-------------|-----------------|
| US-07 | Ricezione fatture real-time A-Cube SDI | Webhook endpoint o interno |
| US-08 | Connessione email via MCP server | Interno (MCP) |
| US-09 | OCR su fattura PDF/immagine | Interno (Vision) o `POST /invoices/upload` |
| US-18 | Notifiche WhatsApp/Telegram | Interno (Notification Agent) |
| US-19 | Report export per commercialista | `GET /reports/commercialista` (endpoint #14 esiste!) |

**Nota:** US-19 ha l'endpoint nella tabella API (#14) ma manca nella mappatura. US-07/08/09 sono interni ma andrebbero documentati come "(interno: agent)" come fatto per US-05, US-10, US-25.

### Request/Response non documentati (HIGH)

**[FINDING-02] API senza schema request/response**
I 56 endpoint sono definiti con path, metodo, auth e descrizione, ma **nessun endpoint ha lo schema JSON di request o response documentato**. Il template di Fase 4 richiede esplicitamente:
- Request body con campi e validazione
- Response 200/201 con struttura
- Error responses (400, 401, 403, 404, 422)

Questo è particolarmente critico per:
- `POST /expenses` (upload + OCR, campi complessi)
- `POST /f24/generate` (parametri periodo, sezioni)
- `POST /cu/generate/{year}` (filtri, opzioni)
- `POST /ceo/budget` (struttura budget mensile)
- `POST /assets/{id}/dispose` (tipo dismissione, importi)

**Raccomandazione:** Documentare almeno i 10 endpoint POST/PATCH più complessi con schema JSON. Può essere fatto in un file separato `specs/api/endpoints-detail.md`.

### Assunzioni non documentate

**[FINDING-03] Cloud Vision data residency**
ADR usa "Cloud Vision data residency EU" come mitigazione per data leak, ma Google Cloud Vision **non** ha data residency configurabile — le immagini vengono processate nei data center Google globali. Solo l'API endpoint può essere regionale, non il processing.

**Raccomandazione:** Verificare con DPO. Alternativa: Tesseract self-hosted per dati sensibili, Cloud Vision per non-sensibili.

**[FINDING-04] Odoo XML-RPC deprecation timeline**
ADR-002 menziona "XML-RPC deprecato da v19, migrazione a JSON-2 API pianificata" ma non c'è timeline. Odoo 19 è atteso Q4 2026 — questo impatta il progetto entro 9 mesi.

### Linguaggio vago

**[FINDING-05] Range di costi troppo ampi**
- "€200-400/mese" per AWS MVP (range 100%)
- "€3.500-7.000/mese" per 100 tenant (range 100%)
- "FiscoAPI: Gratuito per 2 mesi, poi personalizzato" — costo sconosciuto

**Raccomandazione:** Definire costo target (non range) per MVP e breakeven point.

---

## Pass 3: Edge Case Hunter

### Concurrency

**[EDGE-01] Budget upsert race condition**
`POST /ceo/budget` con UNIQUE constraint su `(tenant_id, year, month, category)`. Se due richieste arrivano per stessa categoria/mese: una fallisce con 409 Conflict o silent overwrite? Nessun comportamento documentato.
**Suggerimento:** Documentare semantica UPSERT (INSERT ON CONFLICT UPDATE) nel BR-09.

**[EDGE-02] F24 generazione duplicata**
`POST /f24/generate` per lo stesso periodo: genera un secondo F24 o restituisce l'esistente? Nessuna dedup documentata.
**Suggerimento:** Aggiungere UNIQUE su `(tenant_id, year, period_month)` o `(tenant_id, year, period_quarter)` + logica "genera solo se non esiste draft".

**[EDGE-03] Approvazione spesa concorrente**
Due owner approvano la stessa spesa simultaneamente → doppia registrazione contabile? Nessun optimistic locking documentato.
**Suggerimento:** Aggiungere `version` o `updated_at` check nell'approve.

### Empty State

**[EDGE-04] Dashboard CEO con dati insufficienti**
BR-08 dice "dati disponibili dopo minimo 1 mese" ma non specifica cosa mostrare con 0 giorni, 1 settimana, 2 settimane di dati. Il wireframe W-05 mostra valori reali ma nessun empty state.
**Suggerimento:** Definire 3 stati: empty (0 fatture), partial (< 1 mese), full (≥ 1 mese).

**[EDGE-05] Budget senza voci definite**
`GET /ceo/budget` se nessun budget è stato inserito: ritorna 200 con array vuoto, 404, o suggerisce template? Non documentato.

### Limiti e Validazione

**[EDGE-06] JSONB senza schema**
Campi JSONB critici senza JSON Schema definito:
- `sections` in `f24_documents`: struttura sezioni F24
- `ocr_data` in `expenses`: output OCR
- `active_agents` in `tenants`: lista agenti
- `structured_data` in `invoices`: dati fattura estratti

Senza schema, la validazione backend è ambigua e il frontend non sa cosa aspettarsi.
**Suggerimento:** Definire Pydantic model per ogni campo JSONB.

**[EDGE-07] VARCHAR limits non verificati**
- `description TEXT` senza max length in expenses, assets, fiscal_deadlines → potenziale abuse
- `rejection_reason TEXT` senza max → DoS lento via storage
**Suggerimento:** Aggiungere CHECK constraint o validazione Pydantic (max 2000 chars).

### Permessi

**[EDGE-08] Ruolo "admin" non definito per CEO endpoints**
Gli endpoint CEO (`/ceo/*`) sono marcati "JWT (owner)" ma il sistema ha 3 ruoli: owner, admin, viewer. Un admin può vedere la dashboard CEO? Non documentato.
**Suggerimento:** Definire matrice RBAC esplicita per tutti i 56 endpoint × 3 ruoli.

**[EDGE-09] F24 mark-paid senza restrizione ruolo**
`PATCH /f24/{id}/mark-paid` ha solo "JWT" senza specifica ruolo. Un viewer potrebbe segnare un F24 come pagato?
**Suggerimento:** Almeno "admin" o "owner" richiesto.

### Network / External Failures

**[EDGE-10] Stato sync cassetto dopo errore FiscoAPI**
Se `POST /cassetto/sync` fallisce a metà (es. 30/50 fatture scaricate), qual è lo stato? Le 30 scaricate vengono salvate? La prossima sync riparte da dove? Nessun checkpoint documentato.
**Suggerimento:** Aggiungere `last_sync_cursor` e comportamento idempotente.

**[EDGE-11] OCR timeout su nota spese**
`POST /expenses` con OCR Cloud Vision < 3s target. Se timeout a 3.1s: la spesa viene creata senza OCR, l'utente viene notificato, o errore 504?
**Suggerimento:** Creare spesa come "draft" anche senza OCR, retry asincrono.

---

## Riepilogo

| Categoria | Conteggio | Dettaglio |
|-----------|-----------|-----------|
| **Completeness** | 9.5/11 (86%) | 2 item parziali (API schema, mapping) |
| **Contraddizioni** | 3 | Schema sync, numerazione, campo raw_data |
| **Finding critici** | 5 | Mapping incompleto, no req/res schema, Cloud Vision residency, Odoo timeline, costi vaghi |
| **Edge case** | 11 | Concurrency (3), empty state (2), limiti (2), permessi (2), network (2) |

**Criterio FAIL:** Almeno 1 contraddizione trovata → 3 contraddizioni identificate.

---

## Azioni Consigliate

### Da correggere subito (BLOCKING — prima di Fase 5)

1. **[CONTRADICTION-01] Sincronizzare schema inline** — Sostituire lo schema inline in `04-tech-spec.md` con riferimento a `database/schema.md` (file canonico). Rimuovere ~300 righe di SQL duplicato.

2. **[CONTRADICTION-02] Rinumerare endpoint** — Numerazione sequenziale 1-56 senza duplicati.

3. **[CONTRADICTION-03] Allineare campo invoices** — Usare `raw_xml TEXT` + `structured_data JSONB` ovunque.

4. **[FINDING-01] Completare Story → Endpoint mapping** — Aggiungere US-07, US-08, US-09, US-18, US-19 alla tabella (anche come "interno").

### Da correggere presto (NON-BLOCKING — prima di Fase 7)

5. **[FINDING-02] Request/Response schema** — Documentare JSON schema per i 10 endpoint POST/PATCH più complessi.

6. **[EDGE-08/09] Matrice RBAC** — Definire permessi per tutti i 56 endpoint × 3 ruoli.

7. **[EDGE-01/02/03] Concurrency** — Documentare comportamento upsert, dedup F24, locking spese.

### Nice-to-have (prima del lancio)

8. **[EDGE-06] JSON Schema per JSONB** — Pydantic models per tutti i campi JSONB.
9. **[FINDING-03] Cloud Vision DPA** — Verificare data processing locality.
10. **[FINDING-04] Odoo v19 timeline** — Pianificare migrazione XML-RPC → JSON-2.

---

## Fix Applicati

Data: 2026-03-22

| # | Fix | Cosa è stato fatto |
|---|-----|--------------------|
| 1 | **[CONTRADICTION-01/03] Schema inline rimosso** | Rimosso intero blocco SQL inline (~280 righe). Sostituito con tabella riepilogativa (4 categorie × 18 tabelle) + riferimento a `database/schema.md` come file canonico. Risolve anche CONTRADICTION-03 (campo `raw_data` vs `raw_xml` eliminato). |
| 2 | **[CONTRADICTION-02] Endpoint rinumerati** | Numerazione sequenziale 1-61 (era 1-7, 3-56 con duplicati). Totale effettivo: 61 endpoint (erano 56 contati, ma 5 endpoint avevano numeri duplicati). |
| 3 | **[FINDING-01] Mapping completato** | Aggiunte 5 stories mancanti: US-07 (A-Cube SDI webhook), US-08 (Email MCP), US-09 (OCR Cloud Vision), US-18 (Notification Agent), US-19 (`GET /reports/commercialista`). Mapping ora 40/40. |
| 4 | **[EDGE-08/09] Ruoli CEO e F24** | Endpoint CEO (#56-61) aggiornati a `JWT (owner/admin)` per lettura, `JWT (owner)` per scrittura budget. F24 mark-paid (#55) aggiornato a `JWT (owner/admin)`. |

**Risultato post-fix:** PASS — 3 contraddizioni risolte, mapping 40/40, completeness 10.5/11. Restano 3 finding non-blocking e 9 edge case per fasi successive.

---
_Review Fase 4 — 2026-03-22 (aggiornata post-fix)_
