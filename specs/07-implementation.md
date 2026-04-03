# Implementation Log — AgentFlow PMI

**Progetto:** AgentFlow PMI (ContaBot)
**Fase:** 7 — Implementazione
**Data inizio:** 2026-03-22

---

## Sprint 1: Autenticazione e Contabilita Base

### Stories Status

| ID | Titolo | SP | Status | Date | Tests Written | Tests Passing | Bugs Found |
|----|--------|:--:|--------|------|:-------------:|:-------------:|:----------:|
| US-01 | Registrazione e login utente | 5 | Completata | 2026-03-22 | 17 | 17 | 0 |
| US-02 | Profilo utente e configurazione azienda | 3 | Completata | 2026-03-22 | 12 | 12 | 0 |
| US-03 | Autenticazione SPID/CIE per cassetto fiscale | 8 | Completata | 2026-03-22 | 9 | 9 | 0 |
| US-12 | Setup piano dei conti personalizzato | 8 | Completata | 2026-03-22 | 8 | 8 | 0 |

**Sprint 1 Totale:** 24 SP | 4/4 stories completate | 46 test | 46 PASS | 0 bugs

---

### US-01: Registrazione e login utente

**Status:** Completata
**Data completamento:** 2026-03-22

#### AC Coverage

| AC ID | Descrizione | Test Count | Status |
|-------|-------------|:----------:|--------|
| AC-01.1 | Registrazione con email e password | 5 | PASS |
| AC-01.2 | Login e logout con JWT | 3 | PASS |
| AC-01.3 | Email gia registrata | 2 | PASS |
| AC-01.4 | Password reset | 4 | PASS |
| AC-01.5 | Brute force protection | 3 | PASS |

#### Code Changes Summary

**Nuovi file creati:**
- `api/main.py` — Entry point FastAPI
- `api/config.py` — Pydantic Settings (env vars, JWT, brute force)
- `api/db/models.py` — SQLAlchemy models (Tenant, User)
- `api/db/session.py` — Async DB session factory
- `api/modules/auth/router.py` — Endpoints: register, login, token, verify-email, password-reset
- `api/modules/auth/service.py` — Auth logic: JWT, bcrypt, brute force, email verification
- `api/modules/auth/schemas.py` — Pydantic request/response models con validazione password
- `tests/conftest.py` — Fixtures globali (db_session, client, verified_user, unverified_user)
- `tests/factories/user_factory.py` — Factory per User e Tenant
- `tests/integration/test_auth_api.py` — 17 test per 5 AC
- `pyproject.toml` — Configurazione progetto e pytest

**Endpoints implementati:**
- `POST /api/v1/auth/register` — Registrazione utente
- `POST /api/v1/auth/login` — Login con JWT
- `POST /api/v1/auth/token` — Refresh token
- `POST /api/v1/auth/verify-email` — Verifica email
- `POST /api/v1/auth/password-reset` — Richiesta reset password
- `POST /api/v1/auth/password-reset/confirm` — Conferma reset password

#### Bug Table

_Nessun bug trovato._

---

### US-02: Profilo utente e configurazione azienda

**Status:** Completata
**Data completamento:** 2026-03-22

#### AC Coverage

| AC ID | Descrizione | Test Count | Status |
|-------|-------------|:----------:|--------|
| AC-02.1 | Configurazione completa | 4 | PASS |
| AC-02.2 | P.IVA formato invalido | 3 | PASS |
| AC-02.3 | Codice ATECO inesistente | 3 | PASS |
| AC-02.4 | Modifica profilo dopo setup piano conti | 2 | PASS |

#### Code Changes Summary

**Nuovi file creati:**
- `api/middleware/auth.py` — JWT validation middleware, get_current_user dependency
- `api/utils/validators.py` — Validatori P.IVA (Luhn checksum) e codice ATECO
- `api/modules/profile/router.py` — GET/PATCH /profile con check impatto piano conti
- `api/modules/profile/service.py` — ProfileService: gestione profilo e tenant
- `api/modules/profile/schemas.py` — Enums TipoAzienda/RegimeFiscale, validazione Pydantic
- `tests/integration/test_profile_api.py` — 12 test per 4 AC

**Endpoints implementati:**
- `GET /api/v1/profile` — Lettura profilo con dati tenant
- `PATCH /api/v1/profile` — Aggiornamento profilo con creazione/update tenant

#### Bug Table

_Nessun bug trovato._

---

### US-03: Autenticazione SPID/CIE per cassetto fiscale

**Status:** Completata
**Data completamento:** 2026-03-22

#### AC Coverage

| AC ID | Descrizione | Test Count | Status |
|-------|-------------|:----------:|--------|
| AC-03.1 | Autenticazione SPID riuscita | 3 | PASS |
| AC-03.2 | Autenticazione SPID annullata | 2 | PASS |
| AC-03.3 | Token SPID scaduto | 1 | PASS |
| AC-03.4 | Utente senza SPID/CIE | 2 | PASS |
| AC-03.5 | Delega a terzi (commercialista) | 1 | PASS |

#### Code Changes Summary

**Nuovi file creati:**
- `api/adapters/fiscoapi.py` — FiscoAPI client adapter (SPID init, callback, delega)
- `api/modules/spid/router.py` — Endpoints SPID/CIE e stato cassetto
- `api/modules/spid/service.py` — SpidService: auth flow, token management, status
- `api/modules/spid/schemas.py` — Response models per SPID e cassetto
- `tests/integration/test_spid_api.py` — 9 test per 5 AC

**Endpoints implementati:**
- `POST /api/v1/auth/spid/init` — Avvia autenticazione SPID
- `GET /api/v1/auth/spid/callback` — Callback SPID, salva token
- `GET /api/v1/cassetto/status` — Stato connessione cassetto fiscale
- `GET /api/v1/cassetto/no-spid` — Info per utenti senza SPID
- `POST /api/v1/auth/spid/delegate` — Autenticazione delegata (commercialista)

#### Bug Table

_Nessun bug trovato._

---

### US-12: Setup piano dei conti personalizzato

**Status:** Completata
**Data completamento:** 2026-03-22

#### AC Coverage

| AC ID | Descrizione | Test Count | Status |
|-------|-------------|:----------:|--------|
| AC-12.1 | Piano conti SRL ordinario | 2 | PASS |
| AC-12.2 | Piano conti P.IVA forfettaria | 1 | PASS |
| AC-12.3 | Connessione Odoo fallita | 1 | PASS |
| AC-12.4 | Tipo azienda non standard | 4 | PASS |

#### Code Changes Summary

**Nuovi file creati:**
- `api/adapters/odoo.py` — Odoo client adapter con templates piano conti (SRL, forfettario, generico)
- `api/modules/accounting/router.py` — GET/POST /accounting/chart
- `api/modules/accounting/service.py` — AccountingService: creazione piano conti con retry (3 tentativi)
- `api/modules/accounting/schemas.py` — Response models piano conti
- `tests/integration/test_accounting_api.py` — 8 test per 4 AC

**Endpoints implementati:**
- `GET /api/v1/accounting/chart` — Lettura piano dei conti
- `POST /api/v1/accounting/chart` — Creazione piano dei conti su Odoo (con force per ricreazione)

#### Bug Table

_Nessun bug trovato._

---

## Sprint 2: Pipeline Fatture

### Stories Status

| ID | Titolo | SP | Status | Date | Tests Written | Tests Passing | Bugs Found |
|----|--------|:--:|--------|------|:-------------:|:-------------:|:----------:|
| US-04 | Sync fatture dal cassetto fiscale AdE | 8 | Completata | 2026-03-22 | 6 | 6 | 0 |
| US-05 | Parsing XML FatturaPA | 3 | Completata | 2026-03-22 | 4 | 4 | 0 |
| US-10 | Categorizzazione automatica con learning | 8 | Completata | 2026-03-22 | 5 | 5 | 0 |
| US-14 | Dashboard fatture e stato agenti | 5 | Completata | 2026-03-22 | 6 | 6 | 0 |

**Sprint 2 Totale:** 24 SP | 4/4 stories completate | 21 test | 21 PASS | 0 bugs

---

### US-04: Sync fatture dal cassetto fiscale AdE

**Status:** Completata | **Data:** 2026-03-22

| AC ID | Descrizione | Tests | Status |
|-------|-------------|:-----:|--------|
| AC-04.1 | Primo sync storico 90gg | 2 | PASS |
| AC-04.2 | Sync giornaliero incrementale | 1 | PASS |
| AC-04.3 | FiscoAPI non disponibile (retry backoff) | 1 | PASS |
| AC-04.4 | Fattura duplicata (dedup) | 1 | PASS |
| AC-04.5 | Cassetto fiscale vuoto | 1 | PASS |

**File creati:** `api/modules/invoices/` (router, service, schemas), `api/agents/fisco_agent.py`, `api/agents/base_agent.py` (EventBus), `tests/integration/test_invoices_api.py`
**Endpoints:** POST /cassetto/sync, GET /cassetto/sync/status, GET /invoices, GET /invoices/{id}

---

### US-05: Parsing XML FatturaPA

**Status:** Completata | **Data:** 2026-03-22

| AC ID | Descrizione | Tests | Status |
|-------|-------------|:-----:|--------|
| AC-05.1 | Parsing XML completo | 1 | PASS |
| AC-05.2 | Nota di credito TD04 | 1 | PASS |
| AC-05.3 | XML malformato | 1 | PASS |
| AC-05.4 | Fattura 200+ righe | 1 | PASS |

**File creati:** `api/agents/parser_agent.py` (FatturaPA XML parser con xml.etree), `tests/integration/test_parser_api.py`

---

### US-10: Categorizzazione automatica con learning

**Status:** Completata | **Data:** 2026-03-22

| AC ID | Descrizione | Tests | Status |
|-------|-------------|:-----:|--------|
| AC-10.1 | Rules engine (P.IVA match) | 1 | PASS |
| AC-10.2 | Learning dopo 30+ verifiche | 1 | PASS |
| AC-10.3 | Nessuna regola applicabile | 1 | PASS |
| AC-10.4 | Dead letter queue | 1 | PASS |
| AC-10.5 | Fornitore cambia nome, stessa P.IVA | 1 | PASS |

**File creati:** `api/agents/learning_agent.py` (rules + similarity + feedback), `tests/integration/test_categorization_api.py`

---

### US-14: Dashboard fatture e stato agenti

**Status:** Completata | **Data:** 2026-03-22

| AC ID | Descrizione | Tests | Status |
|-------|-------------|:-----:|--------|
| AC-14.1 | Vista completa (contatori, recenti, agenti) | 2 | PASS |
| AC-14.2 | Filtri e ricerca | 1 | PASS |
| AC-14.3 | Empty state | 1 | PASS |
| AC-14.4 | 1000+ fatture (paginazione) | 2 | PASS |

**File creati:** `api/modules/dashboard/` (router, service, schemas), `tests/integration/test_dashboard_api.py`
**Endpoints:** GET /dashboard/summary, GET /agents/status

---

## Sprint 3: Contabilita e Onboarding

### Stories Status

| ID | Titolo | SP | Status | Date | Tests Written | Tests Passing | Bugs Found |
|----|--------|:--:|--------|------|:-------------:|:-------------:|:----------:|
| US-11 | Verifica e correzione categoria | 5 | Completata | 2026-03-22 | 7 | 7 | 0 |
| US-13 | Registrazione automatica scritture partita doppia | 8 | Completata | 2026-03-22 | 7 | 7 | 0 |
| US-15 | Dashboard scritture contabili | 3 | Completata | 2026-03-22 | 6 | 6 | 0 |
| US-16 | Onboarding guidato | 5 | Completata | 2026-03-22 | 5 | 5 | 0 |

**Sprint 3 Totale:** 21 SP | 4/4 stories completate | 25 test | 25 PASS | 0 bugs

---

### US-11: Verifica e correzione categoria

**Status:** Completata | **Data:** 2026-03-22

| AC ID | Descrizione | Tests | Status |
|-------|-------------|:-----:|--------|
| AC-11.1 | Conferma categoria | 1 | PASS |
| AC-11.2 | Correzione categoria | 1 | PASS |
| AC-11.3 | Categoria non in piano conti (suggerimenti) | 2 | PASS |
| AC-11.4 | Verifica batch (lista da verificare) | 2 | PASS |
| AC-11.5 | Verifica concorrente (last-write-wins) | 1 | PASS |

**File:** `api/modules/invoices/` (verify endpoint, pending-review, suggest-categories)
**Endpoints:** PATCH /invoices/{id}/verify, GET /invoices/pending-review, GET /invoices/{id}/suggest-categories

---

### US-13: Registrazione automatica scritture partita doppia

**Status:** Completata | **Data:** 2026-03-22

| AC ID | Descrizione | Tests | Status |
|-------|-------------|:-----:|--------|
| AC-13.1 | Fattura passiva (dare/avere/fornitori) | 1 | PASS |
| AC-13.2 | Reverse charge (doppia IVA) | 1 | PASS |
| AC-13.3 | Conto contabile mancante | 1 | PASS |
| AC-13.4 | Sbilanciamento dare/avere | 1 | PASS |
| AC-13.5 | Multi-aliquota IVA | 1 | PASS |
| AC-13.6 | Registrazione concorrente (idempotency) | 2 | PASS |

**File:** `api/agents/conta_agent.py` (ACCOUNT_MAPPINGS, multi-IVA, reverse charge, balance validation)
**Models:** JournalEntry, JournalLine

---

### US-15: Dashboard scritture contabili

**Status:** Completata | **Data:** 2026-03-22

| AC ID | Descrizione | Tests | Status |
|-------|-------------|:-----:|--------|
| AC-15.1 | Lista scritture dare/avere | 1 | PASS |
| AC-15.2 | Quadratura dare=avere | 1 | PASS |
| AC-15.3 | Errore Odoo visibile | 1 | PASS |
| AC-15.4 | Empty state | 1 | PASS |
| AC-15.5 | Filtro per periodo contabile | 2 | PASS |

**File:** `api/modules/journal/` (router, service, schemas)
**Endpoints:** GET /accounting/journal-entries, GET /accounting/journal-entries/{id}

---

### US-16: Onboarding guidato

**Status:** Completata | **Data:** 2026-03-22

| AC ID | Descrizione | Tests | Status |
|-------|-------------|:-----:|--------|
| AC-16.1 | Wizard completo in <5 min | 1 | PASS |
| AC-16.2 | Time-to-value (fatture in dashboard) | 1 | PASS |
| AC-16.3 | Onboarding abbandonato (riprende) | 1 | PASS |
| AC-16.4 | SPID fallisce (completa passi 1-2) | 1 | PASS |
| AC-16.5 | Tipo "Altro" (piano generico) | 1 | PASS |

**File:** `api/modules/onboarding/` (router, service, schemas)
**Models:** OnboardingState
**Endpoints:** GET /onboarding/status, POST /onboarding/step/{step_number}

---

## Sprint 17: IVA Netto + Modello Scadenza (Pivot 6)

### Stories Status

| ID | Titolo | SP | Status | Date | Tests Written | Tests Passing | Bugs Found |
|----|--------|:--:|--------|------|:-------------:|:-------------:|:----------:|
| US-70 | Dashboard mostra ricavi e costi al netto IVA | 3 | Completata | 2026-04-01 | 5 | 5 | 0 |
| US-71 | Budget consuntivo usa importi netti | 2 | Completata | 2026-04-01 | 3 | 3 | 0 |
| US-84 | Modello Scadenza (DB) | 3 | Completata | 2026-04-01 | 3 | 3 | 0 |
| US-85 | Modello BankFacility (DB) | 2 | Completata | 2026-04-01 | 1 | 1 | 0 |
| US-86 | Modello InvoiceAdvance (DB) | 2 | Completata | 2026-04-01 | 1 | 1 | 0 |

**Sprint 17 Totale:** 12 SP | 5/5 stories completate | 13 test | 13 PASS | 0 bugs

---

### US-70: Dashboard mostra ricavi e costi al netto IVA

**Status:** Completata | **Data:** 2026-04-01

| AC ID | Descrizione | Tests | Status |
|-------|-------------|:-----:|--------|
| AC-70.1 | Ricavi Totali usa importo_netto | 1 | PASS |
| AC-70.2 | Costi Totali usa importo_netto passive | 1 | PASS |
| AC-70.3 | Margine EBITDA su importi netti | 1 | PASS |
| AC-70.4 | Grafico mensile con importi netti | 1 | PASS |
| AC-70.5 | Widget IVA Netta (debito - credito) | 1 | PASS |

**File modificati:**
- `api/modules/dashboard/service.py` — ricavi/costi usano `imponibile` (netto); grafico mensile usa `importo_netto`; aggiunto `iva_netta`
- `api/modules/dashboard/schemas.py` — aggiunto `IvaNettaSummary` e campo `iva_netta` in `YearlyStats`
- `api/modules/ceo/service.py` — `_calc_fatturato_*`, `_calc_costi_*`, `_top_clients`, `_top_suppliers`, DSO/DPO: tutti usano `importo_netto`

---

### US-71: Budget consuntivo usa importi netti

**Status:** Completata | **Data:** 2026-04-01

| AC ID | Descrizione | Tests | Status |
|-------|-------------|:-----:|--------|
| AC-71.1 | Consuntivo ricavi da fatture attive usa importo_netto | 1 | PASS |
| AC-71.2 | Consuntivo costi da fatture passive usa importo_netto | 1 | PASS |
| AC-71.3 | Scostamento budget/consuntivo calcolato su netti | 1 | PASS |

**File modificati:**
- `api/modules/ceo/service.py` — `get_budget()` calcola consuntivo dinamicamente da Invoice usando `importo_netto`
- `api/modules/ceo/schemas.py` — `BudgetEntry` aggiornato a formato griglia mensile (`BudgetMonthValue`, `monthly[]`)

---

### US-84/85/86: Modelli DB Scadenzario + Fidi + Anticipi

**Status:** Completata | **Data:** 2026-04-01

**Nuovi modelli in `api/db/models.py`:**
- `Scadenza` — scadenzario attivo/passivo (tipo, source_type, source_id, controparte, importi lordo/netto/iva, date, stato, banca_appoggio, anticipata)
- `BankFacility` — fidi bancari (plafond, %, tasso, commissioni per banca)
- `InvoiceAdvance` — singolo anticipo fattura (importi, date, stato, commissioni, interessi)

**Test:** `tests/integration/test_sprint17_api.py` — 13 test

---

## Sprint 18: Scadenzario Attivo/Passivo (Pivot 6)

### Stories Status

| ID | Titolo | SP | Status | Date | Tests Written | Tests Passing | Bugs Found |
|----|--------|:--:|--------|------|:-------------:|:-------------:|:----------:|
| US-72 | Generazione automatica scadenze da fatture | 5 | Completata | 2026-04-01 | 6 | 6 | 0 |
| US-73 | Visualizzazione scadenzario attivo (crediti) | 5 | Completata | 2026-04-01 | 6 | 6 | 0 |
| US-74 | Visualizzazione scadenzario passivo (debiti) | 5 | Completata | 2026-04-01 | 7 | 7 | 0 |

**Sprint 18 Totale:** 15 SP | 3/3 stories completate | 19 test | 19 PASS | 0 bugs

---

### US-72: Generazione automatica scadenze da fatture

**Status:** Completata | **Data:** 2026-04-01

| AC ID | Descrizione | Tests | Status |
|-------|-------------|:-----:|--------|
| AC-72.1 | Fattura attiva → scadenza tipo "attivo" | 1 | PASS |
| AC-72.2 | Fattura passiva → scadenza tipo "passivo" | 1 | PASS |
| AC-72.3 | Importi lordo/netto/IVA separati | 1 | PASS |
| AC-72.4 | Banca appoggio da IBAN fattura | 1 | PASS |
| AC-72.5 | Default 30gg se giorni_pagamento assente | 1 | PASS |
| - | generate_all_missing idempotente | 1 | PASS |

### US-73: Scadenzario attivo

| AC ID | Descrizione | Tests | Status |
|-------|-------------|:-----:|--------|
| AC-73.1 | Lista ordinata per data scadenza | 1 | PASS |
| AC-73.2 | Colonne complete | 1 | PASS |
| AC-73.3 | Stati: aperto, pagato, insoluto, parziale | 1 | PASS |
| AC-73.4 | Colori: rosso/giallo/verde | 1 | PASS |
| AC-73.5 | Filtri per stato e controparte | 1 | PASS |
| AC-73.6 | Totali per stato | 1 | PASS |

### US-74: Scadenzario passivo

| AC ID | Descrizione | Tests | Status |
|-------|-------------|:-----:|--------|
| AC-74.1 | Lista scadenze passive da fatture | 1 | PASS |
| AC-74.2 | Colonne complete passivo | 1 | PASS |
| AC-74.3 | Stati passivo con filtro | 1 | PASS |
| AC-74.5 | Totali per stato passivo | 1 | PASS |
| - | API endpoint attivo | 1 | PASS |
| - | API endpoint passivo | 1 | PASS |
| - | API generate endpoint | 1 | PASS |

**Nuovi file:**
- `api/modules/scadenzario/service.py` — ScadenzarioService (generazione, list attivo/passivo, filtri, colori)
- `api/modules/scadenzario/schemas.py` — ScadenzaItem, ScadenzarioResponse, GenerateResponse
- `api/modules/scadenzario/router.py` — 3 endpoint: POST generate, GET attivo, GET passivo
- `tests/integration/test_sprint18_api.py` — 19 test

---

## Sprint 19: Chiusura Scadenze + Insoluti + Cash Flow (Pivot 6)

### Stories Status

| ID | Titolo | SP | Status | Date | Tests Written | Tests Passing | Bugs Found |
|----|--------|:--:|--------|------|:-------------:|:-------------:|:----------:|
| US-75 | Chiusura automatica scadenze da movimenti banca | 5 | Completata | 2026-04-01 | 4 | 4 | 0 |
| US-76 | Gestione insoluti | 3 | Completata | 2026-04-01 | 4 | 4 | 0 |
| US-77 | Cash flow previsionale da scadenzario | 8 | Completata | 2026-04-01 | 8 | 8 | 0 |

**Sprint 19 Totale:** 16 SP | 3/3 stories completate | 16 test | 16 PASS | 0 bugs

---

### US-75: Chiusura scadenze

| AC ID | Descrizione | Tests | Status |
|-------|-------------|:-----:|--------|
| AC-75.1 | Incasso fattura attiva → "incassato" | 1 | PASS |
| AC-75.2 | Pagamento fattura passiva → "pagato" | 1 | PASS |
| AC-75.3 | Importo parziale → "parziale" con residuo | 1 | PASS |
| AC-75.4 | Anticipata → scarico anticipo segnalato | 1 | PASS |

### US-76: Gestione insoluti

| AC ID | Descrizione | Tests | Status |
|-------|-------------|:-----:|--------|
| AC-76.1 | Segna insoluto su scadenze attive | 1 | PASS |
| AC-76.2 | Warning riaddebito se anticipata | 1 | PASS |
| AC-76.3/4 | Insoluto resta in scadenzario, badge rosso | 1 | PASS |
| - | Passivo non può essere insoluto | 1 | PASS |

### US-77: Cash flow previsionale

| AC ID | Descrizione | Tests | Status |
|-------|-------------|:-----:|--------|
| AC-77.1 | Calcolo: saldo + incassi - pagamenti | 1 | PASS |
| AC-77.2 | Vista 30/60/90 giorni | 1 | PASS |
| AC-77.3 | Breakdown settimanale con saldo progressivo | 1 | PASS |
| AC-77.4 | Alert soglia liquidità | 1 | PASS |
| - | No alert se sopra soglia | 1 | PASS |
| - | API endpoint chiudi | 1 | PASS |
| - | API endpoint insoluto | 1 | PASS |
| - | API endpoint cash-flow | 1 | PASS |

**File modificati:**
- `api/modules/scadenzario/service.py` — aggiunto `chiudi_scadenza()`, `segna_insoluto()`, `cash_flow_previsionale()`
- `api/modules/scadenzario/router.py` — 3 nuovi endpoint: POST chiudi, POST insoluto, GET cash-flow
- `tests/integration/test_sprint19_api.py` — 16 test

---

## Sprint 20: Cash Flow per Banca + Config Fidi (Pivot 6)

### Stories Status

| ID | Titolo | SP | Status | Date | Tests Written | Tests Passing | Bugs Found |
|----|--------|:--:|--------|------|:-------------:|:-------------:|:----------:|
| US-78 | Cash flow per banca | 5 | Completata | 2026-04-01 | 2 | 2 | 0 |
| US-79 | Configurazione fido anticipo per banca | 5 | Completata | 2026-04-01 | 7 | 7 | 0 |

**Sprint 20 Totale:** 10 SP | 2/2 stories | 9 test | 9 PASS | 0 bugs

**Endpoint:** GET /scadenzario/cash-flow/per-banca, GET /fidi, POST /fidi
**Test:** `tests/integration/test_sprint20_api.py`

---

## Sprint 21: Anticipo Fatture Completo (Pivot 6)

### Stories Status

| ID | Titolo | SP | Status | Date | Tests Written | Tests Passing | Bugs Found |
|----|--------|:--:|--------|------|:-------------:|:-------------:|:----------:|
| US-80 | Anticipo fattura — Presentazione | 8 | Completata | 2026-04-01 | 7 | 7 | 0 |
| US-81 | Anticipo fattura — Incasso e scarico | 5 | Completata | 2026-04-01 | 3 | 3 | 0 |
| US-82 | Anticipo fattura — Insoluto | 3 | Completata | 2026-04-01 | 4 | 4 | 0 |

**Sprint 21 Totale:** 16 SP | 3/3 stories | 14 test | 14 PASS | 0 bugs

**Endpoint:** POST /scadenzario/{id}/anticipa, POST /anticipi/{id}/incassa, POST /anticipi/{id}/insoluto
**Test:** `tests/integration/test_sprint21_api.py`

---

## Sprint 22: Confronto Costi Anticipo (Pivot 6)

### Stories Status

| ID | Titolo | SP | Status | Date | Tests Written | Tests Passing | Bugs Found |
|----|--------|:--:|--------|------|:-------------:|:-------------:|:----------:|
| US-83 | Confronto costi anticipo tra banche | 3 | Completata | 2026-04-01 | 4 | 4 | 0 |

**Sprint 22 Totale:** 3 SP | 1/1 stories | 4 test | 4 PASS | 0 bugs

**Endpoint:** GET /scadenzario/{id}/confronta-anticipi
**Test:** `tests/integration/test_sprint22_api.py`

---

## PIVOT 6 COMPLETATO

| Sprint | Stories | SP | Tests | Status |
|--------|---------|----|-------|--------|
| Sprint 17 | US-70, US-71, US-84, US-85, US-86 | 12 | 13 | PASS |
| Sprint 18 | US-72, US-73, US-74 | 15 | 19 | PASS |
| Sprint 19 | US-75, US-76, US-77 | 16 | 16 | PASS |
| Sprint 20 | US-78, US-79 | 10 | 9 | PASS |
| Sprint 21 | US-80, US-81, US-82 | 16 | 14 | PASS |
| Sprint 22 | US-83 | 3 | 4 | PASS |
| **TOTALE** | **17 stories** | **72 SP** | **75 test** | **75 PASS** |

---

## Sprint 23: CRM Interno — Modelli DB + Migrazione (Pivot 7)

### Stories Status

| ID | Titolo | SP | Status | Date | Tests Written | Tests Passing | Bugs Found |
|----|--------|:--:|--------|------|:-------------:|:-------------:|:----------:|
| US-87 | Modello contatti CRM | 3 | Completata | 2026-04-03 | 5 | 5 | 0 |
| US-88 | Modello deal + pipeline stages | 5 | Completata | 2026-04-03 | 6 | 6 | 0 |
| US-89 | Modello attivita CRM | 3 | Completata | 2026-04-03 | 5 | 5 | 0 |
| US-99 | Migrazione endpoint CRM da Odoo a DB interno | 5 | Completata | 2026-04-03 | 7 | 7 | 0 |

**Sprint 23 Totale:** 16 SP | 4/4 stories | 23 test | 23 PASS | 0 bugs

**Nuovi modelli in `api/db/models.py`:**
- `CrmContact` — contatti aziendali (name, type, piva, email, phone, sector, source, assigned_to, email_opt_in)
- `CrmPipelineStage` — stadi pipeline configurabili (name, sequence, probability_default, color, is_won, is_lost)
- `CrmDeal` — opportunita/deal (contact_id, stage_id, deal_type, revenue, daily_rate, order_*, lost_reason)
- `CrmActivity` — attivita su deal/contatto (type: call/email/meeting/note/task, status, timestamps)

**File riscritti (migrazione Odoo → DB interno):**
- `api/modules/crm/service.py` — CRMService usa DB interno, non piu Odoo adapter
- `api/modules/crm/router.py` — endpoint con auth + tenant, nuovi endpoint activities
- `api/modules/crm/schemas.py` — schema aggiornati per UUID string

**Test:** `tests/integration/test_sprint23_crm_api.py` — 23 test

---

## Sprint 24: Kanban Pipeline + Analytics (Pivot 7)

### Stories Status

| ID | Titolo | SP | Status | Date | Tests Written | Tests Passing | Bugs Found |
|----|--------|:--:|--------|------|:-------------:|:-------------:|:----------:|
| US-90 | Pipeline Kanban drag-and-drop | 8 | Completata | 2026-04-03 | 4 | 4 | 0 |
| US-91 | Pipeline analytics | 5 | Completata | 2026-04-03 | 4 | 4 | 0 |

**Sprint 24 Totale:** 13 SP | 2/2 stories | 8 test | 8 PASS | 0 bugs

**US-90 — Kanban:**
- Frontend riscritto come Kanban board con colonne per stage
- Card deal con drag-and-drop HTML5 nativo (no libreria esterna)
- Header colonna: nome, count, totale EUR
- Toggle Kanban/Tabella
- Mobile: dropdown per cambiare stage
- Filtri per tipo deal
- PATCH /crm/deals/{id} aggiorna stage + auto-probabilita

**US-91 — Analytics:**
- Endpoint GET /crm/pipeline/analytics
- Weighted pipeline value (revenue x probability)
- Won/Lost ratio
- Conversion rate per stage
- Analytics bar nella pagina Kanban

**File:**
- `frontend/src/pages/crm/CrmPipelinePage.tsx` — riscritto come Kanban
- `api/modules/crm/service.py` — aggiunto `get_pipeline_analytics()`
- `api/modules/crm/router.py` — aggiunto endpoint analytics
- `frontend/src/api/hooks.ts` — +2 hooks (analytics, updateDeal)
- `tests/integration/test_sprint24_crm_api.py` — 8 test

---

## Sprint 25: Email Marketing con Brevo (Pivot 7)

### Stories Status

| ID | Titolo | SP | Status | Date | Tests Written | Tests Passing | Bugs Found |
|----|--------|:--:|--------|------|:-------------:|:-------------:|:----------:|
| US-92 | Adapter Brevo per invio email | 3 | Completata | 2026-04-03 | 2 | 2 | 0 |
| US-93 | Webhook email tracking | 5 | Completata | 2026-04-03 | 5 | 5 | 0 |
| US-94 | Template email con variabili | 5 | Completata | 2026-04-03 | 9 | 9 | 0 |

**Sprint 25 Totale:** 13 SP | 3/3 stories | 16 test | 16 PASS | 0 bugs

**Nuovi modelli in `api/db/models.py`:**
- `EmailTemplate` — template HTML con variabili, categorie, active flag
- `EmailCampaign` — campagne (single/sequence/trigger) con stats aggregate
- `EmailSend` — singoli invii con brevo_message_id, timestamps open/click, contatori
- `EmailEvent` — eventi webhook (delivered, opened, clicked, bounce, unsub, spam)

**Nuovi file:**
- `api/adapters/brevo.py` — BrevoClient async con invio email e variable substitution
- `api/modules/email_marketing/service.py` — template CRUD, invio con tracking, webhook processing, stats
- `api/modules/email_marketing/router.py` — 8 endpoint (templates, send, webhook, sends, stats)
- 3 template default italiani pre-caricati (Benvenuto, Follow-up, Reminder)

**Endpoint:**
- GET /email/templates, POST /email/templates, GET /email/templates/{id}, PATCH /email/templates/{id}
- POST /email/templates/{id}/preview
- POST /email/send, GET /email/sends, GET /email/stats
- POST /email/webhook (no auth — riceve da Brevo)

**Test:** `tests/integration/test_sprint25_email_api.py` — 16 test

---

## Sprint 26: Invio Email + Analytics Dashboard (Pivot 7)

| ID | Titolo | SP | Status | Tests |
|----|--------|:--:|--------|:-----:|
| US-95 | Invio email singola a contatto | 5 | Completata | 4 |
| US-96 | Dashboard email analytics | 3 | Completata | 6 |

**Sprint 26 Totale:** 8 SP | 10 test | 10 PASS

**Aggiunto:** analytics avanzate (breakdown per template, top contatti, bounced contacts), endpoint GET /email/analytics

---

## Sprint 27: Sequenze Email Automatiche (Pivot 7)

| ID | Titolo | SP | Status | Tests |
|----|--------|:--:|--------|:-----:|
| US-97 | Sequenze email multi-step | 8 | Completata | 5 |
| US-98 | Trigger automatici su eventi CRM | 5 | Completata | 5 |

**Sprint 27 Totale:** 13 SP | 10 test | 10 PASS

**Nuovi modelli:** `EmailSequenceStep`, `EmailSequenceEnrollment`
**Features:** sequenze multi-step con condizioni (if_opened, if_not_opened), enrollment con dedup, trigger su deal_stage_changed e contact_created, config filter per stage

**Endpoint:** POST /email/sequences, POST /email/sequences/{id}/steps, GET /email/sequences/{id}/steps, POST /email/sequences/{id}/enroll

---

## PIVOT 7 COMPLETATO — CRM Interno + Brevo Email

| Sprint | Stories | SP | Tests | Status |
|--------|---------|----|-------|--------|
| Sprint 23 | US-87, US-88, US-89, US-99 | 16 | 23 | PASS |
| Sprint 24 | US-90, US-91 | 13 | 8 | PASS |
| Sprint 25 | US-92, US-93, US-94 | 13 | 16 | PASS |
| Sprint 26 | US-95, US-96 | 8 | 10 | PASS |
| Sprint 27 | US-97, US-98 | 13 | 10 | PASS |
| **TOTALE** | **13 stories** | **63 SP** | **67 test** | **67 PASS** |

---
