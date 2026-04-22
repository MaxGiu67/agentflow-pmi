# User Stories — Pivot 11 "Finance Cockpit" (A-Cube Open Banking + Scarico Massivo)

**Data creazione:** 2026-04-19
**ADR di riferimento:** ADR-012
**Sprint coinvolti:** 48-55 (8 sprint)
**Story points totali stimati:** ~140 SP
**Contratto vincolante:** €1.800/anno listino (AISP €1.200 + SM €600 + setup €900 una tantum)

---

## Mappa sprint

| Sprint | Focus | Stories | SP |
|---|---|---|---|
| 48 | Fondamenta OB (adapter, auth, DB, connect) | US-OB-01→05 | 22 |
| 49 | Sync conti e movimenti | US-OB-06→10 | 21 |
| 50 | Provisioning tenant + Consenso lifecycle | US-OB-11→15 + US-PROV-01→04 | 20 |
| 51 | Riconciliazione automatica movimenti↔fatture | US-OB-16→19 | 18 |
| 52 | Cash flow predittivo + chatbot tool | US-OB-20→23 | 16 |
| 53 | Usage Monitor + admin dashboard | US-MON-01→05 | 12 |
| 54 | Scarico Massivo (post call tecnica) — Sprint A | US-CF-01→05 | 18 |
| 55 | Scarico Massivo (post call tecnica) — Sprint B | US-CF-06→09 | 13 |

---

# Traccia A — Open Banking AISP

## Sprint 48 — Fondamenta OB

### US-OB-01 — Adapter A-Cube Open Banking client

**Come** sviluppatore AgentFlow,
**voglio** un client async per l'API A-Cube Open Banking,
**affinché** tutti i moduli backend possano chiamare gli endpoint PSD2 in modo consistente.

**Story points:** 5
**Priorità:** P0

**Acceptance Criteria:**
- [ ] File `api/adapters/acube_ob.py` con classe `ACubeOpenBankingClient`
- [ ] Config da env: `ACUBE_OB_BASE_URL`, `ACUBE_LOGIN_EMAIL`, `ACUBE_LOGIN_PASSWORD`, `ACUBE_ENV` (sandbox|prod)
- [ ] Metodo `_login()` → `POST /login` → restituisce JWT
- [ ] Base methods: `get()`, `post()`, `put()`, `delete()` con retry su 5xx (3x exp backoff)
- [ ] Header standard: `Authorization: Bearer <jwt>`, `Accept: application/ld+json`
- [ ] Timeout default 30s
- [ ] Logging strutturato (no JWT in log)
- [ ] Test unitari con `httpx.MockTransport`

### US-OB-02 — JWT token manager con cache Redis

**Come** sistema AgentFlow,
**voglio** riutilizzare il JWT A-Cube per 23 ore senza rifare login,
**affinché** ridurre latenza e rispettare le best practice A-Cube (1 login/24h).

**Story points:** 3
**Priorità:** P0

**AC:**
- [ ] `acube:jwt:{env}` in Redis con TTL 23h
- [ ] Metodo `_get_token()` → cache hit → return; cache miss → login + set
- [ ] Refresh proattivo 1h prima della scadenza (background task Celery)
- [ ] Su 401 → invalidate cache + retry 1 volta
- [ ] Test concorrenza (lock Redis per evitare login doppio)

### US-OB-03 — Modelli DB per Open Banking

**Come** sviluppatore,
**voglio** nuove tabelle per memorizzare connessioni, account e arricchire i movimenti,
**affinché** poter mappare dati A-Cube su strutture AgentFlow.

**Story points:** 5
**Priorità:** P0

**AC:**
- [ ] Tabella `bank_connection`: `id`, `customer_id` (AgentFlow), `fiscal_id` (P.IVA), `acube_br_uuid`, `status` (pending/active/expired), `consent_expires_at`, `last_reconnect_webhook_at`
- [ ] Tabella `bank_account` (nuova): `id`, `bank_connection_id`, `acube_uuid`, `provider_name`, `iban`, `bban`, `swift`, `name`, `nature`, `balance`, `currency_code`, `enabled`, `consent_expires_at`
- [ ] Estensione `bank_movement`: aggiungere `acube_transaction_id` (UNIQUE), `acube_duplicated_flag`, `acube_status` (pending/booked/canceled), `acube_category`, `acube_fetched_at`, `acube_counterparty`, `acube_extra` (JSONB)
- [ ] Indici: `(customer_id, fiscal_id)`, `(acube_br_uuid)`, `(acube_transaction_id)`
- [ ] Alembic migration

### US-OB-04 — Endpoint init connessione

**Come** utente AgentFlow,
**voglio** cliccare "Collega conto bancario" e ricevere l'URL verso la banca,
**affinché** completare il consenso PSD2 sulla mia banca.

**Story points:** 5
**Priorità:** P0

**AC:**
- [ ] Endpoint `POST /api/v1/banking/connections/init`
- [ ] Body: `{fiscal_id, return_url}` (fiscal_id ricavato da tenant context)
- [ ] Service:
  1. Se Business Registry non esiste → `POST /business-registry` A-Cube
  2. `POST /business-registry/{fiscal_id}/connect` con `redirectUrl` e `locale=it`
  3. Persisti `bank_connection` status=pending + `acube_connect_request_uuid`
  4. Return `{connect_url, connection_id}`
- [ ] Frontend: pulsante "Collega conto" su `/banca/connessioni`
- [ ] Redirect window.location.href verso `connect_url`

### US-OB-05 — Webhook Connect receiver

**Come** sistema,
**voglio** ricevere notifica quando il consenso PSD2 è concluso,
**affinché** poter sincronizzare subito conti e storico movimenti.

**Story points:** 4
**Priorità:** P0

**AC:**
- [ ] Endpoint `POST /api/v1/webhooks/acube/connect`
- [ ] Verifica firma HMAC (algoritmo + header da confermare con A-Cube — vedi open questions)
- [ ] Payload success: update `bank_connection.status=active`, scatena task `sync_accounts(fiscal_id)`
- [ ] Payload error: update status=failed, salva errorClass + errorMessage, notifica email admin
- [ ] Idempotency: se stesso `fiscal_id`+`updatedAccounts` già processato, ignora
- [ ] Test con payload JSON esempio da docs

---

## Sprint 49 — Sync conti e movimenti

### US-OB-06 — Service sync_accounts

**Come** sistema,
**voglio** leggere la lista account di un Business Registry e persisterli localmente,
**affinché** mostrare all'utente i conti collegati con saldo e IBAN.

**Story points:** 3
**Priorità:** P0

**AC:**
- [ ] Funzione `sync_accounts(fiscal_id)` → `GET /business-registry/{fiscal_id}/accounts?itemsPerPage=100`
- [ ] Loop paginazione via Hydra `hydra:next`
- [ ] Upsert `bank_account` per ogni UUID
- [ ] Solo account con `enabled=true` considerati attivi in AgentFlow
- [ ] Test con fixture JSON 2 conti

### US-OB-07 — Service sync_transactions con backfill

**Come** sistema,
**voglio** scaricare tutti i movimenti storici disponibili di un conto,
**affinché** popolare DB iniziale senza perdere nessun movimento.

**Story points:** 8
**Priorità:** P0

**AC:**
- [ ] Funzione `sync_transactions(account_uuid, date_from=None, date_to=None)`
- [ ] Se `date_from=None` → default 730 giorni fa (2 anni)
- [ ] Query params: `account.uuid`, `madeOn[strictly_after]`, `itemsPerPage=100`
- [ ] Loop paginazione completa (può essere 50+ pagine)
- [ ] Dedup: skip se `acube_transaction_id` già in DB
- [ ] ⚠️ **Pending transactions**: `DELETE FROM bank_movement WHERE acube_status='pending' AND account_id=?` → poi re-insert da A-Cube
- [ ] Skip transazioni con `duplicated=true` (ma log)
- [ ] Mapping campi: A-Cube → AgentFlow (`amount`, `description`, `madeOn`→`value_date`, `category`, `counterparty`, `extra`→JSONB)
- [ ] Rate limiting: max 10 req/s verso A-Cube
- [ ] Test con fixture 250 movimenti (3 pagine)

### US-OB-08 — Celery beat sync orario

**Come** sistema,
**voglio** sincronizzare automaticamente i movimenti ogni ora,
**affinché** l'utente veda dati aggiornati senza intervento manuale.

**Story points:** 3
**Priorità:** P1

**AC:**
- [ ] Task Celery `sync_all_active_banks` eseguito ogni ora
- [ ] Per ogni `bank_connection` status=active:
  - `sync_accounts(fiscal_id)`
  - Per ogni account → `sync_transactions(uuid, date_from=now-7days)`
- [ ] Scheduler beat in `celery_beat_schedule`
- [ ] Log metrics: N connessioni sync, N movimenti nuovi, tempo esecuzione
- [ ] Error handling: skip account che falliscono (non blocca gli altri)

### US-OB-09 — Parser normalizzazione extra

**Come** sistema,
**voglio** estrarre CRO, TRN e riferimenti pagamento dal campo `extra` variabile per banca,
**affinché** poter riconciliare automaticamente con fatture.

**Story points:** 5
**Priorità:** P1

**AC:**
- [ ] Modulo `api/modules/banking/extra_parser.py`
- [ ] Parser dedicato per Intesa Sanpaolo, Unicredit, Fineco, BPM (le più diffuse)
- [ ] Fallback generico regex su `description` per pattern CRO (`CRO \d{11}` / `TRN [A-Z0-9]+`)
- [ ] Estrazione: `cro`, `trn`, `iban_counterparty`, `invoice_ref` (es. "FT 2024/45", "FATTURA N. 123")
- [ ] Output come colonne enriched su `bank_movement.enriched_cro`, `enriched_invoice_ref`
- [ ] Test unitari su 20+ esempi di movimenti reali per banca

### US-OB-10 — Endpoint sync manuale

**Come** utente,
**voglio** cliccare "Sincronizza ora" sul mio conto,
**affinché** forzare un refresh senza aspettare il job orario.

**Story points:** 2
**Priorità:** P2

**AC:**
- [ ] Endpoint `POST /api/v1/banking/connections/{id}/sync-now`
- [ ] Trigger task `sync_accounts` + `sync_transactions` immediato
- [ ] Rate limit utente: 1 sync ogni 5 minuti
- [ ] Response: `{status: "started", task_id}`
- [ ] Frontend: bottone "Aggiorna ora" con spinner

---

## Sprint 50 — Consenso lifecycle + Provisioning

### US-OB-11 — Webhook Reconnect receiver

**AC:**
- [ ] Endpoint `POST /api/v1/webhooks/acube/reconnect`
- [ ] Persist `bank_connection.reconnect_url`, `notice_level`, `consent_expires_at`
- [ ] Trigger notifiche (vedi US-OB-12)
- [ ] **SP: 3 | P0**

### US-OB-12 — Notifica cliente scadenza consenso

**AC:**
- [ ] Email Brevo `consent_expiring` (template con `{{provider_name}}`, `{{days_left}}`, `{{reconnect_url}}`)
- [ ] Trigger su noticeLevel 0/1/2 con escalation (1 mail giorno 0, 1 mail giorno 10, 2 mail giorno 20)
- [ ] In-app notification (banner giallo `/banca`)
- [ ] **SP: 3 | P0**

### US-OB-13 — UI rinnovo consenso

**AC:**
- [ ] Pagina `/banca/connessioni` lista conti con badge scadenza
- [ ] Badge: verde (>20gg), giallo (<20gg), rosso (<10gg), bloccante (scaduto)
- [ ] Bottone "Rinnova consenso" → apre `reconnect_url` in new tab
- [ ] **SP: 3 | P0**

### US-OB-14 — Job giornaliero check scadenze

**AC:**
- [ ] Task Celery `check_expiring_consents` daily 9:00
- [ ] Query `bank_connection` dove `consent_expires_at < now()+5days`
- [ ] Alert admin via Slack/email se non rinnovato 2gg prima scadenza
- [ ] **SP: 2 | P1**

### US-OB-15 — Webhook Payment receiver

**AC:**
- [ ] Endpoint `POST /api/v1/webhooks/acube/payment`
- [ ] Placeholder per future outbound payments (PISP)
- [ ] Log evento + no-op per ora (feature attivata con contratto PISP)
- [ ] **SP: 1 | P2**

### US-PROV-01 — Provisioning BR su onboarding cliente

**Come** sistema,
**voglio** creare automaticamente un Business Registry A-Cube quando un nuovo cliente AgentFlow si registra,
**affinché** pre-configurare l'integrazione bancaria prima che l'utente lo richieda.

**Story points:** 4
**Priorità:** P0

**AC:**
- [ ] Hook post-onboarding: quando customer.status diventa `active` →
  1. Generare email univoca (es. `br-{customer_id}@agentflow.taal.it`)
  2. `POST /business-registry` con `{fiscalId, email, businessName, enabled: false}`
  3. Persist `customer.acube_br_uuid`, `customer.acube_br_email`
- [ ] Modalità `enabled: false` iniziale → attivata solo su primo connect (evita fee)
- [ ] Gestione errore "entity already exists" con retry email alternativa
- [ ] Test mock + integration sandbox

### US-PROV-02 — Controllo soglia 50 clienti

**AC:**
- [ ] Check pre-creazione: se `COUNT(bank_connection) >= 50` → blocco con alert admin
- [ ] Banner admin dashboard "Fascia 1-50 piena — upgrade contrattuale necessario"
- [ ] Endpoint `GET /api/v1/admin/acube/tier-status` per monitoraggio
- [ ] **SP: 2 | P1**

### US-PROV-03 — Pause/resume BR (disable/enable)

**AC:**
- [ ] Endpoint `POST /api/v1/banking/connections/{id}/pause` → `POST /business-registry/{fid}/disable` A-Cube
- [ ] Endpoint `POST /api/v1/banking/connections/{id}/resume` → `POST /business-registry/{fid}/enable`
- [ ] ⚠️ Warning UX: "Il resume fattura un canone prorata"
- [ ] **SP: 2 | P2**

### US-PROV-04 — DELETE BR quando customer churn

**AC:**
- [ ] Su customer status=churned → `DELETE /business-registry/{fiscal_id}` dopo 30gg di grace period
- [ ] Backup transazioni pre-delete in S3/R2 per compliance
- [ ] **SP: 2 | P1**

---

## Sprint 51 — Riconciliazione automatica

### US-OB-16 — Matching engine movimenti↔scadenze

**Come** cliente AgentFlow,
**voglio** che i miei bonifici incassati chiudano automaticamente le scadenze attive corrispondenti,
**affinché** non perdere tempo a marcare fatture come pagate.

**Story points:** 8
**Priorità:** P0

**AC:**
- [ ] Modulo `api/modules/reconciliation/matcher.py` con funzione `match_movement(movement)`
- [ ] Scoring multi-criterio 0-100:
  - Importo match exact: +50 punti
  - Importo match ±0.02€: +40 punti
  - CRO/TRN match: +30 punti
  - Numero fattura estratto in description: +20 punti
  - IBAN controparte match: +15 punti
  - Data valuta vicina scadenza (±7gg): +10 punti
- [ ] Score ≥85 → auto-match + chiusura scadenza
- [ ] Score 60-84 → suggerimento (richiede conferma user)
- [ ] Score <60 → no match
- [ ] Test con 100 casi reali

### US-OB-17 — Dashboard riconciliazione

**AC:**
- [ ] Pagina `/banca/riconciliazione`
- [ ] 3 tab: Auto-matched, Suggeriti (score 60-84), Non matched
- [ ] Per ogni suggerimento: mostra movimento + scadenza candidata + score + motivazione
- [ ] Bottoni Conferma/Rifiuta
- [ ] **SP: 4 | P0**

### US-OB-18 — Feedback loop per ML futuro

**AC:**
- [ ] Tabella `reconciliation_feedback`: `movement_id`, `scadenza_id`, `score_proposto`, `user_action` (confirmed/rejected/ignored), `timestamp`
- [ ] API per registrare feedback
- [ ] Dataset utile per training modello ML futuro
- [ ] **SP: 2 | P2**

### US-OB-19 — Task notturno auto-match

**AC:**
- [ ] Celery task `auto_reconcile_movements` daily 22:00
- [ ] Processa movimenti non ancora matched degli ultimi 30gg
- [ ] Auto-match se score ≥85
- [ ] Log report giornaliero (N matched, N suggested, N unmatched)
- [ ] **SP: 4 | P0**

---

## Sprint 52 — Cash Flow predittivo + chatbot

### US-OB-20 — Cash flow forecast con dati reali

**AC:**
- [ ] Funzione `forecast_cashflow(days=30|60|90)` in `cashflow/forecast.py`
- [ ] Input: saldi attuali A-Cube + scadenze confermate + movimenti ricorrenti
- [ ] Output: time series daily balance projection
- [ ] **SP: 5 | P0**

### US-OB-21 — Alert soglia cassa

**AC:**
- [ ] Config `cash_flow_alert_threshold` per customer (default €5.000)
- [ ] Se forecast < soglia entro N giorni → notifica email + in-app
- [ ] **SP: 3 | P1**

### US-OB-22 — Widget dashboard "Previsione cassa"

**AC:**
- [ ] Widget puzzle dashboard con grafico line 90gg
- [ ] Marker verticale "oggi", shaded area "below threshold"
- [ ] Toggle 30/60/90gg
- [ ] **SP: 4 | P0**

### US-OB-23 — Tool chatbot get_cash_flow_forecast

**AC:**
- [ ] Aggiunta tool al Controller Agent
- [ ] Input: `{days: 30|60|90}`
- [ ] Output: narrativo "Tra X giorni il tuo saldo previsto è Y €..."
- [ ] **SP: 4 | P1**

---

# Traccia C — Usage Monitor

## Sprint 53 — Dashboard consumi A-Cube

### US-MON-01 — Tabella acube_usage

**AC:**
- [ ] Tabella `acube_usage`: `date`, `active_customers_count`, `invoices_downloaded_ytd`, `tier_current`, `estimated_cost_eur`
- [ ] Snapshot giornaliero automatico
- [ ] **SP: 2 | P0**

### US-MON-02 — Dashboard admin /admin/acube-usage

**AC:**
- [ ] Pagina solo-admin con:
  - Counter "Clienti attivi": X/50 (progress bar)
  - Counter "Fatture scaricate YTD": X/5.000 (progress bar)
  - Grafico trend mensile
  - Stima costo annuo (proiezione)
- [ ] **SP: 4 | P0**

### US-MON-03 — Alert soglia 80%

**AC:**
- [ ] Alert email a owner quando:
  - Clienti attivi ≥ 40 (80% di 50)
  - Fatture YTD ≥ 4.000 (80% di 5.000)
- [ ] Alert rosso bloccante quando 100%
- [ ] **SP: 2 | P0**

### US-MON-04 — Report annuale

**AC:**
- [ ] Report PDF/CSV scaricabile (esercizio passato)
- [ ] Proiezione anno successivo (simula upgrade tier)
- [ ] Utile per rinnovo contrattuale
- [ ] **SP: 2 | P1**

### US-MON-05 — Integrazione endpoint A-Cube (se disponibile)

**AC:**
- [ ] Se A-Cube espone endpoint consumi (open question) → chiamata daily per cross-check
- [ ] Altrimenti: calcolo interno su nostra DB
- [ ] **SP: 2 | P2**

---

# Traccia B — Scarico Massivo Fatture (post call tecnica)

## Sprint 54 — Fondamenta Cassetto Fiscale

### US-CF-01 — Adapter A-Cube Cassetto client

**AC:**
- [ ] Classe `ACubeCassettoClient` in `api/adapters/acube_cassetto.py`
- [ ] Riusa token manager US-OB-02
- [ ] Endpoint (da confermare call tecnica): `/business-registry-configurations/*`, `/ade-appointees/*`
- [ ] **SP: 5 | P0**

### US-CF-02 — Onboarding wizard 3 modalità delega

**AC:**
- [ ] UI wizard 3 step: scegli modalità (proxy A-Cube / credenziali dirette / incaricato)
- [ ] Per proxy: mostra guida con screenshot AdE + P.IVA 10442360961
- [ ] Per dirette: form CF + password + PIN Fisconline (criptati AES)
- [ ] Per incaricato: form incaricato + credenziali
- [ ] **SP: 5 | P0**

### US-CF-03 — Tabella delega_agenzia_entrate

**AC:**
- [ ] Tabella `ade_delegation`: `id`, `customer_id`, `mode`, `status` (pending/active/expired), `expires_at`, `acube_config_id`
- [ ] Durata 4 anni (come normativa AdE)
- [ ] **SP: 3 | P0**

### US-CF-04 — Job scarico fatture notturno

**AC:**
- [ ] Task Celery `download_invoices_all_active_customers` daily 02:00
- [ ] Per ogni ade_delegation active:
  - Call endpoint A-Cube per nuove fatture (ultimi 3 giorni + backfill primo run)
  - Download XML → parsing FatturaPA (riusa `api/modules/invoices/parsing.py`)
  - Dedup su progressivo univoco SDI
  - Upsert tabella `invoices`
- [ ] Log metrics
- [ ] **SP: 5 | P0**

### US-CF-05 — Gestione rotazione password Fisconline

**AC:**
- [ ] Per modalità "credenziali dirette" e "incaricato":
  - Notifica pre-scadenza (21/14/7/2 giorni come fa A-Cube)
  - Form "Aggiorna password Fisconline"
  - Call `PUT /.../credentials/fisconline`
- [ ] **SP: 3 | P1**

---

## Sprint 55 — Scarico Massivo UX + observability

### US-CF-06 — UI lista fatture scaricate

**AC:**
- [ ] Pagina `/fatture/passive-automatiche` filtrata per source=acube_cassetto
- [ ] Badge "Scaricata automaticamente" vs "Caricata manualmente"
- [ ] **SP: 3 | P1**

### US-CF-07 — Monitor conteggio fatture YTD

**AC:**
- [ ] Counter su admin dashboard
- [ ] Integrato in US-MON-02
- [ ] **SP: 2 | P0**

### US-CF-08 — Gestione errori delega scaduta/credenziali invalide

**AC:**
- [ ] Se A-Cube restituisce errore delega → `ade_delegation.status=expired`
- [ ] Notifica cliente + UI "Riconfigura delega"
- [ ] **SP: 3 | P0**

### US-CF-09 — Import corrispettivi 2026 (when available)

**AC:**
- [ ] Feature flag `CORRISPETTIVI_2026_ENABLED`
- [ ] Placeholder per quando AdE rilascerà canale
- [ ] **SP: 5 | P2**

---

## Dipendenze esterne

| Blocco | Dipendenza | Mitigazione |
|---|---|---|
| Sprint 48+ | Credenziali sandbox A-Cube | Email kick-off inviata |
| Sprint 48 US-OB-05 | Firma HMAC webhook (algoritmo) | Email kick-off — in attesa risposta |
| Sprint 54+ | Call tecnica Scarico Massivo | Da prenotare (email kick-off) |
| Sprint 48 US-OB-09 | Normalizzazione `extra` per banca | Email kick-off — in attesa |

## Criteri Definition of Done (tutte le stories)

- [ ] Codice review approvato
- [ ] Test unitari ≥ 1 per AC
- [ ] Test integrazione sandbox A-Cube per task chiave
- [ ] Logging strutturato
- [ ] Zero dati sensibili in log (JWT, password, credenziali AdE)
- [ ] Documentazione inline + aggiornamento `api/README.md` se endpoint pubblici
- [ ] Migration Alembic testata up+down
- [ ] Performance: response API < 500ms p95 (esclusi sync batch)
