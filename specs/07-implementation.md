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

## Sprint 28: Social Selling — Epic 1 Origini + Epic 2 Activity Types (Pivot 8)

| ID | Titolo | SP | Status | Tests |
|----|--------|:--:|--------|:-----:|
| US-130 | Admin definisce origine contact custom | 5 | Completata | 5 |
| US-131 | Admin modifica/disattiva origine | 3 | Completata | 4 |
| US-132 | Migrare campo source a origine FK | 5 | Completata | 3 |
| US-133 | Filtro contatti per origine | 3 | Completata | 3 |
| US-134 | Admin definisce tipi attivita custom | 5 | Completata | 7 |
| US-135 | Admin modifica/disattiva tipo attivita | 3 | Completata | 4 |
| US-136 | Pipeline stages + pre-funnel | 5 | Completata | 6 |
| US-137 | Attivita con tipo custom + last_contact | 3 | Completata | 3 |

**Sprint 28 Totale:** 32 SP | 8 stories | 35 test (18 Epic 1 + 17 Epic 2) | 35 PASS

**Nuovi modelli DB:**
- `CrmContactOrigin` — origini custom per tenant (code, label, parent_channel, icon_name, is_active)
- `CrmActivityType` — tipi attivita custom (code, label, category, icon_name, counts_as_last_contact)

**Backend:**
- `api/modules/social_selling/origins_service.py` — CRUD origini + migration + seed 4 default
- `api/modules/social_selling/activity_types_service.py` — CRUD tipi attivita + seed 8 default
- `api/modules/social_selling/pipeline_service.py` — Stage CRUD + auto-reorder per pre-funnel

**Frontend:**
- `frontend/src/pages/social/OriginsPage.tsx` — Lista origini con edit inline, toggle, delete
- `frontend/src/pages/social/ActivityTypesPage.tsx` — Lista tipi attivita con badge categorie
- `frontend/src/pages/social/PipelineSettingsPage.tsx` — Gestione stadi con supporto pre-funnel

**Test:** `test_social_selling_origins_api.py` (18), `test_social_selling_epic2_api.py` (17)

---

## Sprint 29: Social Selling — Epic 3 RBAC + Audit (Pivot 8)

| ID | Titolo | SP | Status | Tests |
|----|--------|:--:|--------|:-----:|
| US-138 | Ruoli CRM custom con matrice permessi | 8 | Completata | 7 |
| US-141 | Audit trail immutabile | 5 | Completata | 6 |

**Sprint 29 Totale:** 13 SP | 2 stories | 13 test | 13 PASS

**Nuovi modelli DB:**
- `CrmRole` — ruoli custom per tenant (name, is_system)
- `CrmRolePermission` — matrice permessi entity×permission
- `CrmAuditLog` — log immutabile (action, entity, entity_id, user_id, details, ip_address)

**Backend:**
- `api/modules/social_selling/roles_service.py` — RBAC + seed 5 ruoli default + permission matrix
- `api/modules/social_selling/audit_service.py` — Log immutabile + CSV export con SHA256

**Frontend:**
- `frontend/src/pages/social/RolesPage.tsx` — Matrice RBAC con checkbox per entity/permission
- `frontend/src/pages/social/AuditLogPage.tsx` — Tabella log con filtri, paginazione, CSV export

**Test:** `test_social_selling_epic3_api.py` (13)

---

## Sprint 30: Social Selling — Epic 4 Catalogo Prodotti (Pivot 8)

| ID | Titolo | SP | Status | Tests |
|----|--------|:--:|--------|:-----:|
| US-142 | Catalogo prodotti/servizi | 5 | Completata | 3 |
| US-143 | Modifica/disattiva prodotto | 3 | Completata | 3 |
| US-144 | Prodotti associati a deal | 5 | Completata | 5 |

**Sprint 30 Totale:** 13 SP | 3 stories | 11 test | 11 PASS

**Nuovi modelli DB:**
- `CrmProductCategory` — categorie prodotto per tenant
- `CrmProduct` — prodotti/servizi (code, name, category, pricing_model, unit_price, margin_target)
- `CrmDealProduct` — M2M deal↔prodotto (quantity, unit_price_override, total_price)

**Backend:**
- `api/modules/social_selling/products_service.py` — CRUD prodotti + deal products + revenue calc

**Frontend:**
- `frontend/src/pages/social/ProductsPage.tsx` — Card grid con edit inline, badge pricing, toggle

**Test:** `test_social_selling_epic4_api.py` (11)

---

## Sprint 31: Social Selling — Epic 5 Analytics + Compensi (Pivot 8)

| ID | Titolo | SP | Status | Tests |
|----|--------|:--:|--------|:-----:|
| US-146 | Dashboard KPI personalizzabile | 5 | Completata | 3 |
| US-147 | Scorecard performance | 3 | Completata | 2 |
| US-148 | Regole compenso configurabili | 5 | Completata | 4 |
| US-149 | Calcolo compensi mensile | 3 | Completata | 2 |
| US-150 | Conferma e pagamento compensi | 3 | Completata | 3 |

**Sprint 31 Totale:** 19 SP | 5 stories | 14 test | 14 PASS

**Nuovi modelli DB:**
- `CrmDashboardWidget` — widget configurabili per dashboard
- `CrmCompensationRule` — regole compenso (method, percentage, threshold, conditions)
- `CrmCompensationEntry` — entry mensili (draft → confirmed → paid)

**Backend:**
- `api/modules/social_selling/dashboard_service.py` — Dashboard custom + scorecard KPIs
- `api/modules/social_selling/compensation_service.py` — Regole + calcolo tiered + confirm/pay

**Frontend:**
- `frontend/src/pages/social/ScorecardPage.tsx` — KPI cards, auto-load per commerciale
- `frontend/src/pages/social/CompensationPage.tsx` — Compensi mensili con calculate/confirm/pay

**Test:** `test_social_selling_epic5_api.py` (14)

---

## Sprint 32: User Management + Role-Based UI + Company/Contact Split (Pivot 8)

| ID | Titolo | SP | Status | Tests |
|----|--------|:--:|--------|:-----:|
| US-109 | Gestione utenti con invito | 5 | Completata | 6 |
| US-110 | Row-level security per commerciale | 5 | Completata | 3 |
| US-111 | Email sender per utente | 3 | Completata | 2 |
| — | Role-based sidebar + dashboard | — | Completata | 3 |
| — | Company/Contact 1:N split | — | Completata | — |
| — | TipTap rich text editor | — | Completata | — |
| — | Service Worker network-first | — | Completata | — |
| — | ErrorBoundary auto-reload | — | Completata | — |

**Sprint 32 Totale:** 13 SP | 3 stories + 4 infra | 14 test | 14 PASS

**Nuovi modelli DB:**
- `CrmCompany` (NEW) — azienda separata da contatto (name, piva, sector, city, website, origin_id, assigned_to)
- `CrmContact.company_id` FK — referente legato ad azienda (1:N)
- `CrmDeal.company_id` FK — deal appartiene ad azienda
- `CrmPipelineStage.stage_type` — "pre_funnel" vs "pipeline"
- `User.user_type` — "internal" vs "external"
- `User.access_expires_at` — scadenza accesso utente esterno
- `User.crm_role_id`, `User.default_origin_id`, `User.default_product_id`

**Backend:**
- `api/modules/crm/service.py` — Company CRUD, list_contacts con origin_id filter, pipeline analytics con assigned_to
- `api/modules/crm/router.py` — Company endpoints, row-level filtering per commerciale/esterno
- `api/modules/user_management/service.py` — invite con user_type/expiry, update CRM role
- `api/modules/dashboard/default_widgets.py` — Widget set per ruolo (admin 13, commerciale 8)
- `api/modules/dashboard/service.py` — get_crm_stats() per dashboard commerciale
- `api/middleware/auth.py` — Check access_expires_at, auto-deactivazione

**Frontend:**
- `frontend/src/components/ui/Sidebar.tsx` — Filtro per ruolo (admin/owner vede tutto, commerciale vede solo CRM)
- `frontend/src/components/ui/BottomNav.tsx` — Stesso filtro ruolo per mobile
- `frontend/src/pages/DashboardPage.tsx` — Dashboard admin (financial KPIs) vs commerciale (sales KPIs)
- `frontend/src/pages/crm/CrmContactsPage.tsx` — Form 2 step: seleziona/crea azienda → aggiungi referente
- `frontend/src/pages/crm/CrmDealDetailPage.tsx` — Prodotti, timeline attivita, planned activities, bottone Modifica
- `frontend/src/pages/crm/CrmPipelinePage.tsx` — Dialog ibrido cambio fase: sposta diretto o con registrazione attivita
- `frontend/src/pages/crm/CrmNewDealPage.tsx` — Selettore stage + prima attivita opzionale
- `frontend/src/pages/impostazioni/UsersPage.tsx` — Interno/Esterno toggle, CRM role, expiry
- `frontend/src/pages/email/EmailTemplatesPage.tsx` — TipTap RichTextEditor per template
- `frontend/src/components/email/RichTextEditor.tsx` — TipTap con toolbar completa + variable quick-insert
- `frontend/public/sw.js` — Network-first per HTML, cache-first per assets hashed
- `frontend/src/components/ui/ErrorBoundary.tsx` — Auto-reload su stale chunk (debounce 10s)

**Test:** `test_sprint32_users_api.py` (14)

---

## Sprint 33: Integrazione Calendario Commerciali

| ID | Titolo | SP | Status | Tests |
|----|--------|:--:|--------|:-----:|
| US-151 | Vista calendario FullCalendar | 5 | Completata | 2 |
| US-152 | Export .ics client-side | 3 | Completata | — |
| US-153 | OAuth Microsoft 365 | 5 | Completata | 6 |
| US-154 | Push attivita → Outlook | 5 | Completata | 2 |
| US-155 | Link Calendly profilo | 3 | Completata | 10 |

**Sprint 33 Totale:** 21 SP | 5 stories | 20 test | 20 PASS

**Nuovi campi DB:**
- `User.microsoft_token` (Text) — JSON criptato con access_token, refresh_token, expires_at
- `User.calendly_url` (String) — URL Calendly personale
- `CrmActivity.outlook_event_id` (String) — ID evento Outlook per tracking push

**Backend:**
- `api/modules/calendar/microsoft_service.py` — OAuth2 flow (authorize URL, code exchange, token refresh) + Graph API push (create/update events)
- `api/modules/calendar/router.py` — 6 endpoint: GET/POST microsoft connect/callback/status/disconnect, GET/PATCH calendly
- `api/modules/crm/service.py` — Hook push_activity su create_activity quando status=planned e user ha Microsoft 365

**Frontend:**
- `frontend/src/pages/crm/CrmCalendarPage.tsx` — FullCalendar (daygrid+timegrid+interaction), legenda colori per tipo, popover dettaglio con .ics download
- `frontend/src/pages/ImpostazioniPage.tsx` — Sezione "Calendario e Appuntamenti": Microsoft 365 connect/disconnect + Calendly URL input
- `frontend/src/pages/crm/CrmDealDetailPage.tsx` — Bottone "Prenota appuntamento" (Calendly) nel header del deal
- `frontend/src/components/ui/Sidebar.tsx` — Voce "Calendario" nella sezione Commerciale
- `frontend/src/api/hooks.ts` — 5 nuovi hooks: useMicrosoftCalendarStatus, useMicrosoftConnect, useMicrosoftDisconnect, useCalendlyUrl, useUpdateCalendlyUrl

**Librerie aggiunte:**
- `@fullcalendar/react` + `@fullcalendar/daygrid` + `@fullcalendar/timegrid` + `@fullcalendar/interaction` (~40KB gzipped, lazy-loaded)
- `ics` (3KB) — generazione file .ics client-side

**Test:** `test_calendar_api.py` (20)

---

## Sprint 34: CRM Bug Fixes + Schema Hardening + Calendar Enhancement + Pipeline UX (2026-04-07)

### Bug Fixes

| # | Descrizione | Impatto | Fix |
|---|-------------|---------|-----|
| BF-01 | `ContactCreate` schema mancava `contact_name`, `contact_role`, `company_id`, `website` | 422 su creazione contatto | Aggiunti campi opzionali allo schema Pydantic |
| BF-02 | `ContactResponse` schema mancava `company_id`, `contact_name`, `contact_role`, `website`, `origin_id` | Frontend non riceveva dati completi | Aggiunti campi alla response |
| BF-03 | `DealResponse` schema mancava `company_id`, `pipeline_template_id`, `assigned_to_name`, `days_in_stage` | Card Kanban incomplete | Aggiunti campi calcolati alla response |
| BF-04 | `scheduled_at` tipo string invece di datetime | 500 su create_activity (fromisoformat su oggetto non-stringa) | Parse esplicito con `fromisoformat()` |
| BF-05 | Microsoft OAuth redirect URI puntava a frontend domain | OAuth callback 404 | Corretto a API domain |
| BF-06 | OAuth callback non redirigeva al frontend | Utente restava su pagina bianca dopo OAuth | Redirect a `/profilo?calendar=connected` |
| BF-07 | `user_id` non auto-assegnato su create_activity | Outlook push falliva (user_id null) | Auto-assign `current_user.id` |
| BF-08 | `useCrmActivities` hook con condizione `enabled` | Calendario non caricava attivita | Rimossa condizione `enabled` |
| BF-09 | Import `Package` rimosso da lucide-react | Build error | Sostituito con `Building2` |

### Features

| # | Descrizione | Dettaglio |
|---|-------------|-----------|
| FT-01 | Search bar in CRM Pipeline | Sostituita combo "Tutti i tipi" con campo ricerca (filtra per client, nominativo, descrizione) |
| FT-02 | Colonna "Perso" visibile in Kanban | Rimosso filtro `!s.is_lost` che nascondeva la colonna |
| FT-03 | DELETE company endpoint | Nuovo `DELETE /crm/companies/{id}` per rimozione aziende |
| FT-04 | Company deduplication frontend | Dedup per nome in CrmContactsPage e CrmNewDealPage (evita duplicati in dropdown) |
| FT-05 | Rimossa sezione Prodotti/Servizi da deal detail | Il tipo deal + pipeline template definisce il prodotto, sezione ridondante |
| FT-06 | Enhanced Calendar | FullCalendar con click-to-create, 6 tipi attivita (call, video_call, meeting, email, task, note), badge sync Outlook |
| FT-07 | Enhanced Activity Form in deal detail | Bottoni tipo visivi, supporto video call, campo data sempre visibile, nota sync Outlook |

### E2E Tests

| Suite | Test | Status |
|-------|------|--------|
| CRM E2E | 182 | 182 PASS (companies, contacts, deals, stages, activities, orders, analytics) |
| Calendar E2E | 38 | 38 PASS (MS365 status, OAuth URL, Calendly CRUD, activities, non-destructive) |
| **Totale** | **220** | **220 PASS** |

### DB Cleanup
- Eliminati 13 aziende duplicate/test dal DB produzione
- Rimane solo l'azienda reale "replay"

**Sprint 34 Totale:** 9 bug fix + 7 feature + 220 E2E test | 220 PASS

**File modificati (backend):**
- `api/modules/crm/schemas.py` — ContactCreate, ContactResponse, DealResponse ampliati
- `api/modules/crm/service.py` — `scheduled_at` parsing, `user_id` auto-assign, delete_company
- `api/modules/crm/router.py` — Nuovo endpoint DELETE /crm/companies/{id}
- `api/modules/calendar/router.py` — Redirect URI corretta, callback redirect a frontend
- `api/modules/calendar/microsoft_service.py` — OAuth redirect fix

**File modificati (frontend):**
- `frontend/src/pages/crm/CrmPipelinePage.tsx` — Search bar, colonna Perso visibile
- `frontend/src/pages/crm/CrmContactsPage.tsx` — Company dedup
- `frontend/src/pages/crm/CrmNewDealPage.tsx` — Company dedup
- `frontend/src/pages/crm/CrmDealDetailPage.tsx` — Rimossa sezione prodotti, enhanced activity form
- `frontend/src/pages/crm/CrmCalendarPage.tsx` — Click-to-create, 6 tipi, Outlook sync badge
- `frontend/src/api/hooks.ts` — Rimossa condizione `enabled` su useCrmActivities
- Sostituito import `Package` con `Building2` (lucide-react)

**Test:** `test_crm_e2e.py` (182), `test_calendar_e2e.py` (38)

---

## PIVOT 8 COMPLETATO — Social Selling + Company/Contact + Role-Based UI + Calendar

| Sprint | Stories | SP | Tests | Status |
|--------|---------|----|-------|--------|
| Sprint 28 | US-130→137 | 32 | 35 | PASS |
| Sprint 29 | US-138, US-141 | 13 | 13 | PASS |
| Sprint 30 | US-142→144 | 13 | 11 | PASS |
| Sprint 31 | US-146→150 | 19 | 14 | PASS |
| Sprint 32 | US-109→111 + infra | 13 | 14 | PASS |
| Sprint 33 | US-151→155 (Calendar) | 21 | 20 | PASS |
| Sprint 34 | Bug fix + Schema + UX | — | 220 | PASS |
| **TOTALE** | **26 stories + infra** | **111 SP** | **327 test** | **327 PASS** |

**Stories non ancora implementate (Pivot 8):**
- US-139: Utenti esterni con scadenza accesso (parziale — backend pronto, frontend form esterno pronto)
- US-140: Filtro dati per origine default utente esterno (parziale — backend pronto, da testare E2E)
- US-145: Pipeline filtro per prodotto (non implementato)

---
