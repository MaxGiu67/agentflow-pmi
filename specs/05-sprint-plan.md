# Sprint Plan — AgentFlow PMI (ContaBot)

**Progetto:** AgentFlow PMI
**Data:** 2026-03-22
**Fase:** 5 — Sprint Planning
**Fonte:** specs/03-user-stories.md, specs/04-tech-spec.md

---

## Sprint Overview

- **Velocity**: 20-24 SP/sprint
- **Durata Sprint**: 2 settimane
- **Sprint Totali**: 16 (10 completati + 6 Pivot 5)
- **SP Totali Progetto**: 365 (224 completati + 141 Pivot 5)
- **v0.1-v0.4 (Sprint 1-10):** 224 SP — COMPLETATO
- **v0.5-v0.7 (Sprint 11-16):** 141 SP — Pivot 5: Controller Aziendale AI

---

## Sprint 1: Autenticazione e Contabilità Base

### Objective
Costruire le fondamenta: registrazione, login, SPID/CIE per cassetto fiscale e setup piano dei conti personalizzato. Al termine, un utente può registrarsi, autenticarsi via SPID e avere il proprio piano dei conti pronto.

### Stories

| ID | Titolo | SP | Priority | Dependencies |
|----|--------|:--:|----------|-------------|
| US-01 | Registrazione e login utente | 5 | Must | — |
| US-02 | Profilo utente e configurazione azienda | 3 | Must | US-01 |
| US-03 | Autenticazione SPID/CIE per cassetto fiscale | 8 | Must | US-01 |
| US-12 | Setup piano dei conti personalizzato | 8 | Must | US-02 |

**SP Totali Sprint**: 24 / 24

### Task Breakdown

#### US-01: Registrazione e login utente
| Task | Owner | Stima |
|------|-------|-------|
| Setup FastAPI project, Docker, PostgreSQL, Redis | Backend | 4h |
| Modelli User + Tenant (SQLAlchemy + Alembic migration) | Backend | 3h |
| Endpoint POST /auth/register con validazione Pydantic | Backend | 3h |
| Endpoint POST /auth/login + JWT (24h) + refresh token (7gg) | Backend | 4h |
| Email verifica (template + invio) | Backend | 2h |
| Brute force protection (5 tentativi + lockout 15min) | Backend | 2h |
| Unit test (5 AC × 2 test min) | Test | 3h |

#### US-02: Profilo utente e configurazione azienda
| Task | Owner | Stima |
|------|-------|-------|
| Endpoint GET/PATCH /profile con dati azienda | Backend | 2h |
| Validazione P.IVA, CF, codice ATECO | Backend | 2h |
| Setup Odoo database per tenant (via XML-RPC) | Backend | 4h |
| Test integration Odoo connection | Test | 2h |

#### US-03: Autenticazione SPID/CIE per cassetto fiscale
| Task | Owner | Stima |
|------|-------|-------|
| Integrazione FiscoAPI client (adapter) | Backend | 4h |
| Endpoint POST /auth/spid/init (redirect SPID) | Backend | 3h |
| Endpoint GET /auth/spid/callback (salva token cifrato) | Backend | 3h |
| Gestione scadenza token SPID + rinnovo | Backend | 3h |
| Test mock FiscoAPI + test errori SPID | Test | 3h |

#### US-12: Setup piano dei conti personalizzato
| Task | Owner | Stima |
|------|-------|-------|
| Template piano dei conti per tipo azienda (SRL, P.IVA, forfettario) | Backend | 4h |
| Creazione piano conti su Odoo via XML-RPC/JSON-2 | Backend | 6h |
| Endpoint GET /accounting/chart | Backend | 2h |
| Test creazione piano conti + validazione struttura | Test | 3h |

### Completion Criteria
- [ ] Un utente si registra, verifica email, fa login con JWT
- [ ] SPID/CIE autentica su FiscoAPI e token salvato cifrato
- [ ] Piano dei conti creato su Odoo per tipo azienda
- [ ] Test copertura ≥ 80% su auth, ≥ 70% su Odoo bridge
- [ ] Docker compose funzionante (API + Odoo + PostgreSQL + Redis)

### Risks
- **SPID/CIE integration complessa**: FiscoAPI gestisce il flusso, ma il testing richiede sandbox. Mitigazione: mock FiscoAPI per CI, test manuale su sandbox.
- **Odoo XML-RPC lento al primo setup**: Mitigazione: pool connessioni, timeout 30s.

---

## Sprint 2: Pipeline Fatture

### Objective
Completare il flusso fatture: sync dal cassetto fiscale, parsing XML, categorizzazione automatica e dashboard operativa. Al termine, le fatture si sincronizzano, vengono parse e categorizzate automaticamente.

### Stories

| ID | Titolo | SP | Priority | Dependencies |
|----|--------|:--:|----------|-------------|
| US-04 | Sync fatture dal cassetto fiscale AdE | 8 | Must | US-03 |
| US-05 | Parsing XML FatturaPA | 3 | Must | US-04 |
| US-10 | Categorizzazione automatica con learning | 8 | Must | US-05 |
| US-14 | Dashboard fatture e stato agenti | 5 | Must | US-05 |

**SP Totali Sprint**: 24 / 24

### Task Breakdown

#### US-04: Sync fatture dal cassetto fiscale AdE
| Task | Owner | Stima |
|------|-------|-------|
| FiscoAgent: scheduler sync giornaliero (Celery beat) | Backend | 4h |
| Download batch fatture via FiscoAPI | Backend | 4h |
| Dedup fatture (hash XML) + salvataggio PostgreSQL | Backend | 3h |
| Endpoint POST /cassetto/sync + GET /cassetto/status | Backend | 3h |
| Redis pub/sub: invoice.downloaded event | Backend | 2h |
| Test con XML fatture reali (10+ campioni) | Test | 3h |

#### US-05: Parsing XML FatturaPA
| Task | Owner | Stima |
|------|-------|-------|
| Parser Agent: lxml parsing FatturaPA 1.2.2 | Backend | 3h |
| Estrazione campi: emittente, importi, IVA, ritenuta, bollo | Backend | 3h |
| Redis event: invoice.parsed | Backend | 1h |
| Test parsing con fatture edge case (200+ righe, reverse charge) | Test | 2h |

#### US-10: Categorizzazione automatica con learning
| Task | Owner | Stima |
|------|-------|-------|
| Learning Agent: regole base (fornitore → categoria) | Backend | 4h |
| scikit-learn similarity model (TF-IDF su descrizioni) | Backend | 6h |
| Confidence score + threshold (>0.8 auto, <0.8 review) | Backend | 3h |
| Redis event: invoice.categorized | Backend | 1h |
| Test accuracy su dataset 50+ fatture | Test | 3h |

#### US-14: Dashboard fatture e stato agenti
| Task | Owner | Stima |
|------|-------|-------|
| Endpoint GET /dashboard/summary (fatture in/out, totali) | Backend | 3h |
| Endpoint GET /agents/status (stato agenti) | Backend | 2h |
| Frontend: pagina Dashboard.tsx con React + Tailwind | Frontend | 6h |
| Test API dashboard | Test | 2h |

### Completion Criteria
- [ ] Fatture scaricate dal cassetto fiscale e salvate in DB
- [ ] XML FatturaPA parsato con tutti i campi estratti
- [ ] Categorizzazione automatica con accuracy ≥ 70%
- [ ] Dashboard mostra fatture con stato e agenti attivi
- [ ] Pipeline event-driven funzionante (downloaded → parsed → categorized)

### Risks
- **FiscoAPI rate limiting**: Mitigazione: batch download con backoff, cache locale.
- **Learning accuracy bassa su pochi dati**: Mitigazione: regole base sempre attive come fallback.

---

## Sprint 3: Contabilità e Onboarding

### Objective
Chiudere il ciclo v0.1: registrazione automatica scritture in partita doppia, dashboard contabile e onboarding guidato. Al termine, il flusso end-to-end funziona: SPID → sync → parse → categorizza → registra → visualizza.

### Stories

| ID | Titolo | SP | Priority | Dependencies |
|----|--------|:--:|----------|-------------|
| US-11 | Verifica e correzione categoria | 5 | Must | US-10 |
| US-13 | Registrazione automatica scritture partita doppia | 8 | Must | US-10, US-12 |
| US-15 | Dashboard scritture contabili | 3 | Must | US-13 |
| US-16 | Onboarding guidato (SPID → cassetto → prima fattura) | 5 | Must | US-03, US-12 |

**SP Totali Sprint**: 21 / 24

### Task Breakdown

#### US-11: Verifica e correzione categoria
| Task | Owner | Stima |
|------|-------|-------|
| Endpoint PATCH /invoices/{id}/verify (conferma/correggi) | Backend | 3h |
| Salvataggio feedback in categorization_feedback | Backend | 2h |
| Retraining pipeline (batch settimanale) | Backend | 4h |
| Frontend: UI correzione categoria con suggerimenti | Frontend | 4h |
| Test feedback loop | Test | 2h |

#### US-13: Registrazione automatica scritture partita doppia
| Task | Owner | Stima |
|------|-------|-------|
| ContaAgent: listener invoice.categorized | Backend | 2h |
| Mapping categoria → conto dare/avere | Backend | 4h |
| Creazione account.move + account.move.line su Odoo | Backend | 6h |
| Gestione IVA (aliquote, reverse charge, split payment) | Backend | 4h |
| Redis event: journal.entry.created | Backend | 1h |
| Test scritture con 5 tipologie fattura | Test | 3h |

#### US-15: Dashboard scritture contabili
| Task | Owner | Stima |
|------|-------|-------|
| Endpoint GET /accounting/journal-entries (con filtri) | Backend | 3h |
| Frontend: pagina scritture con tabella e filtri | Frontend | 4h |
| Test API + paginazione | Test | 2h |

#### US-16: Onboarding guidato
| Task | Owner | Stima |
|------|-------|-------|
| Frontend: wizard step-by-step (SPID → cassetto → prima fattura) | Frontend | 6h |
| Logica di stato onboarding (completed steps) | Backend | 2h |
| Test E2E onboarding flow (Playwright) | Test | 3h |

### Completion Criteria
- [ ] Flusso end-to-end: SPID → sync → parse → categorizza → registra → dashboard
- [ ] Utente può correggere categoria e il sistema impara
- [ ] Scritture partita doppia registrate su Odoo con IVA
- [ ] Onboarding wizard funzionante
- [ ] **v0.1 MVP completo e testabile**

### Risks
- **Complessità IVA italiana**: Reverse charge, split payment, aliquote multiple. Mitigazione: iniziare con aliquote standard (4/10/22%), aggiungere casi speciali iterativamente.

---

## Sprint 4: Canali Secondari e Reporting

### Objective
Ampliare i canali di acquisizione fatture (SDI real-time, email, upload) e aggiungere scadenzario fiscale e report per il commercialista.

### Stories

| ID | Titolo | SP | Priority | Dependencies |
|----|--------|:--:|----------|-------------|
| US-06 | Upload manuale fattura | 2 | Should | — |
| US-07 | Ricezione fatture real-time A-Cube SDI | 5 | Should | US-02 |
| US-08 | Connessione email via MCP server | 5 | Should | — |
| US-17 | Scadenzario fiscale base | 5 | Should | US-02 |
| US-19 | Report export per commercialista | 5 | Should | US-13 |

**SP Totali Sprint**: 22 / 24

### Task Breakdown

#### US-06: Upload manuale fattura
| Task | Owner | Stima |
|------|-------|-------|
| Endpoint POST /invoices/upload (multipart PDF/foto) | Backend | 2h |
| Validazione file (tipo, dimensione max 10MB) | Backend | 1h |
| Frontend: drag & drop upload | Frontend | 2h |
| Test upload + integrazione pipeline parsing | Test | 2h |

#### US-07: Ricezione fatture real-time A-Cube SDI
| Task | Owner | Stima |
|------|-------|-------|
| A-Cube SDK integration (webhook receiver) | Backend | 4h |
| Webhook endpoint + signature verification | Backend | 3h |
| Dedup con fatture da cassetto fiscale | Backend | 2h |
| Test con sandbox A-Cube | Test | 2h |

#### US-08: Connessione email via MCP server
| Task | Owner | Stima |
|------|-------|-------|
| MCP server Gmail/PEC (monitoring inbox) | Backend | 6h |
| Filtro allegati fattura (PDF, XML, P7M) | Backend | 3h |
| Test mock email con allegati | Test | 2h |

#### US-17: Scadenzario fiscale base
| Task | Owner | Stima |
|------|-------|-------|
| Endpoint GET /deadlines + PATCH complete | Backend | 3h |
| Calcolo scadenze da fatture (IVA trimestrale, ritenute) | Backend | 4h |
| Frontend: pagina FiscalDeadlines.tsx | Frontend | 3h |
| Test scadenze generate correttamente | Test | 2h |

#### US-19: Report export per commercialista
| Task | Owner | Stima |
|------|-------|-------|
| Endpoint GET /reports/commercialista (PDF + CSV) | Backend | 4h |
| Template report: fatture, scritture, IVA, scadenze | Backend | 3h |
| Test export con dati realistici | Test | 2h |

### Completion Criteria
- [ ] Fatture acquisibili da 4 canali: cassetto, SDI, email, upload
- [ ] Scadenzario fiscale con date calcolate automaticamente
- [ ] Report esportabile per commercialista (PDF + CSV)
- [ ] Webhook A-Cube funzionante con dedup

### Risks
- **Gmail OAuth review lento**: Mitigazione: MCP server non bloccante, canale secondario.

---

## Sprint 5: OCR, Notifiche e Fisco Base

### Objective
Completare v0.2 con OCR e notifiche. Avviare v0.3 con bilancio CEE e alert scadenze personalizzate.

### Stories

| ID | Titolo | SP | Priority | Dependencies |
|----|--------|:--:|----------|-------------|
| US-09 | OCR su fattura PDF/immagine | 5 | Should | US-08 o US-06 |
| US-18 | Notifiche WhatsApp/Telegram | 5 | Should | US-17 |
| US-20 | Alert scadenze fiscali personalizzate | 5 | Could | US-04 |
| US-23 | Bilancio CEE via Odoo OCA | 5 | Could | US-13 |

**SP Totali Sprint**: 20 / 24

### Task Breakdown

#### US-09: OCR su fattura PDF/immagine
| Task | Owner | Stima |
|------|-------|-------|
| Google Cloud Vision adapter | Backend | 3h |
| OCR pipeline: immagine → testo → parsing strutturato | Backend | 4h |
| Fallback Tesseract per documenti semplici | Backend | 3h |
| Test OCR con 10+ scontrini/fatture reali | Test | 2h |

#### US-18: Notifiche WhatsApp/Telegram
| Task | Owner | Stima |
|------|-------|-------|
| Notification Agent: listener deadline.approaching | Backend | 3h |
| WhatsApp Business API integration | Backend | 3h |
| Telegram Bot API integration | Backend | 2h |
| Test notifiche con mock | Test | 2h |

#### US-20: Alert scadenze fiscali personalizzate
| Task | Owner | Stima |
|------|-------|-------|
| Configurazione alert per utente (anticipo, canale) | Backend | 3h |
| Endpoint GET /ceo/alerts (riuso per alert scadenze) | Backend | 2h |
| Test alert generati correttamente | Test | 2h |

#### US-23: Bilancio CEE via Odoo OCA
| Task | Owner | Stima |
|------|-------|-------|
| Integrazione modulo OCA l10n_it_financial_statements_report | Backend | 4h |
| Endpoint GET /accounting/balance-sheet | Backend | 3h |
| Test bilancio con dati di esempio | Test | 2h |

### Completion Criteria
- [ ] **v0.2 completo**: tutti i canali + OCR + notifiche + report
- [ ] OCR accuracy ≥ 85% su scontrini italiani
- [ ] Notifiche push funzionanti su WhatsApp e Telegram
- [ ] Bilancio CEE generato da Odoo OCA

### Risks
- **OCR accuracy su scontrini**: Qualità variabile. Mitigazione: fallback manuale se confidence < 0.7.

---

## Sprint 6: Open Banking e Fatturazione Attiva

### Objective
Collegare il conto corrente via Open Banking e abilitare la fatturazione attiva SDI. Chiudere la liquidazione IVA automatica.

### Stories

| ID | Titolo | SP | Priority | Dependencies |
|----|--------|:--:|----------|-------------|
| US-21 | Fatturazione attiva SDI via A-Cube | 8 | Could | US-12 |
| US-24 | Collegamento conto corrente Open Banking | 8 | Could | — |
| US-22 | Liquidazione IVA automatica | 8 | Could | US-13, US-04 |

**SP Totali Sprint**: 24 / 24

### Task Breakdown

#### US-21: Fatturazione attiva SDI via A-Cube
| Task | Owner | Stima |
|------|-------|-------|
| Generazione XML FatturaPA da dati utente | Backend | 6h |
| Invio SDI via A-Cube API | Backend | 4h |
| Tracking stato fattura (inviata, consegnata, scartata) | Backend | 3h |
| Frontend: form creazione fattura attiva | Frontend | 4h |
| Test invio su sandbox A-Cube | Test | 3h |

#### US-24: Collegamento conto corrente Open Banking
| Task | Owner | Stima |
|------|-------|-------|
| BankingAdapter astratto (A-Cube/Fabrick) | Backend | 4h |
| Flusso SCA: redirect → consent → callback | Backend | 4h |
| Sync saldi e movimenti (AISP) | Backend | 4h |
| Rinnovo consent 90gg automatico | Backend | 3h |
| Test mock AISP + sandbox | Test | 3h |

#### US-22: Liquidazione IVA automatica
| Task | Owner | Stima |
|------|-------|-------|
| Integrazione Odoo OCA vat_period_end_settlement | Backend | 5h |
| Calcolo IVA trimestrale/mensile da registri | Backend | 4h |
| Generazione scadenza F24 per IVA | Backend | 3h |
| Test liquidazione con dati realistici | Test | 3h |

### Completion Criteria
- [ ] Fattura attiva inviabile via SDI
- [ ] Conto corrente collegato con saldi e movimenti visibili
- [ ] Liquidazione IVA calcolata e scadenza generata
- [ ] BankingAdapter pronto per switch provider

### Risks
- **PSD2 consent 90gg**: Banche minori potrebbero non supportare rinnovo. Mitigazione: graceful degradation + upload manuale movimenti.

---

## Sprint 7: Riconciliazione e Gap Contabili (I)

### Objective
Riconciliare fatture con movimenti bancari. Iniziare i gap contabili: ritenute d'acconto e imposta di bollo.

### Stories

| ID | Titolo | SP | Priority | Dependencies |
|----|--------|:--:|----------|-------------|
| US-25 | Cash flow predittivo 90gg | 8 | Could | US-24, US-13 |
| US-26 | Riconciliazione fatture-movimenti bancari | 8 | Could | US-24, US-13 |
| US-33 | Ritenute d'acconto — riconoscimento e calcolo netto | 5 | Could | US-05, US-13 |
| US-35 | Imposta di bollo automatica | 3 | Could | US-21 |

**SP Totali Sprint**: 24 / 24

### Task Breakdown

#### US-25: Cash flow predittivo 90gg
| Task | Owner | Stima |
|------|-------|-------|
| CashFlowAgent: raccolta dati (fatture + movimenti + scadenze) | Backend | 4h |
| Modello previsionale (media mobile + scadenze note) | Backend | 5h |
| Endpoint API cash flow + grafico | Backend | 3h |
| Test previsione con scenario 3 mesi | Test | 2h |

#### US-26: Riconciliazione fatture-movimenti bancari
| Task | Owner | Stima |
|------|-------|-------|
| Engine riconciliazione (match per importo, data, causale) | Backend | 6h |
| Endpoint GET /reconciliation/pending + POST match | Backend | 3h |
| Frontend: UI riconciliazione con suggerimenti | Frontend | 4h |
| Test riconciliazione con 100+ movimenti | Test | 2h |

#### US-33: Ritenute d'acconto — riconoscimento e calcolo netto
| Task | Owner | Stima |
|------|-------|-------|
| Riconoscimento tag DatiRitenuta da XML | Backend | 3h |
| Calcolo netto (multi-aliquota 20/23/26/30%) | Backend | 3h |
| Creazione scadenza F24 (16 mese successivo) | Backend | 2h |
| Test con fatture con/senza ritenuta | Test | 2h |

#### US-35: Imposta di bollo automatica
| Task | Owner | Stima |
|------|-------|-------|
| Rilevamento bollo su fatture esenti > €77.16 | Backend | 2h |
| Gestione fatture miste (parte esente + imponibile) | Backend | 2h |
| Tracking trimestrale + totale per F24 | Backend | 2h |
| Test bollo con edge case (miste, passive) | Test | 2h |

### Completion Criteria
- [ ] Cash flow predittivo a 90gg funzionante
- [ ] Riconciliazione automatica con match ≥ 70%
- [ ] Ritenute riconosciute da XML e netto calcolato
- [ ] Bollo tracciato per trimestre con totale F24

### Risks
- **Riconciliazione bassa accuracy**: Movimenti bancari spesso con causali generiche. Mitigazione: suggerimenti multipli con confidence, conferma manuale.

---

## Sprint 8: Note Spese, Cespiti e Ratei

### Objective
Completare i gap contabili operativi: note spese con OCR, registro cespiti con ammortamento, ratei e risconti di fine esercizio.

### Stories

| ID | Titolo | SP | Priority | Dependencies |
|----|--------|:--:|----------|-------------|
| US-29 | Note spese — upload e categorizzazione | 5 | Could | US-02, US-09, US-10 |
| US-30 | Note spese — approvazione e rimborso | 3 | Could | US-29 |
| US-31 | Cespiti — scheda cespite e ammortamento automatico | 5 | Could | US-13 |
| US-32 | Cespiti — registro e dismissione | 3 | Could | US-31 |
| US-36 | Ratei e risconti di fine esercizio | 5 | Could | US-13 |

**SP Totali Sprint**: 21 / 24

### Task Breakdown

#### US-29: Note spese — upload e categorizzazione
| Task | Owner | Stima |
|------|-------|-------|
| Endpoint POST /expenses (upload + OCR scontrino) | Backend | 3h |
| Policy check (max importo, categoria) | Backend | 2h |
| Categorizzazione automatica (riuso Learning Agent) | Backend | 2h |
| Frontend: pagina Expenses.tsx con upload | Frontend | 3h |
| Test OCR + policy check | Test | 2h |

#### US-30: Note spese — approvazione e rimborso
| Task | Owner | Stima |
|------|-------|-------|
| Endpoint PATCH approve/reject + POST reimburse | Backend | 3h |
| Auto-approvazione titolare unico (BR-10) | Backend | 2h |
| Registrazione contabile su Odoo post-approvazione | Backend | 2h |
| Test workflow completo | Test | 2h |

#### US-31: Cespiti — scheda cespite e ammortamento automatico
| Task | Owner | Stima |
|------|-------|-------|
| Tabelle ministeriali ammortamento (D.M. 31/12/1988) | Backend | 3h |
| Endpoint POST /assets + calcolo ammortamento | Backend | 3h |
| Soglia €516.46 (BR-01) + pro-rata primo anno (BR-02) | Backend | 3h |
| Test ammortamento con 5 categorie | Test | 2h |

#### US-32: Cespiti — registro e dismissione
| Task | Owner | Stima |
|------|-------|-------|
| Endpoint GET /assets (registro) + POST dispose | Backend | 3h |
| Calcolo plus/minusvalenza dismissione | Backend | 2h |
| Frontend: pagina Assets.tsx | Frontend | 3h |
| Test dismissione (vendita, rottamazione, furto) | Test | 2h |

#### US-36: Ratei e risconti di fine esercizio
| Task | Owner | Stima |
|------|-------|-------|
| Analisi fatture pluriennali (BR-05) | Backend | 3h |
| Proposta scritture assestamento 31/12 | Backend | 3h |
| Riapertura automatica 1/1 | Backend | 2h |
| Test con assicurazione annuale e affitto | Test | 2h |

### Completion Criteria
- [ ] Note spese con OCR, policy check, approvazione e rimborso
- [ ] Cespiti con ammortamento automatico da tabelle ministeriali
- [ ] Ratei/risconti proposti e confermabili con riapertura 1/1
- [ ] Auto-approvazione per titolare unico funzionante

### Risks
- **Tabelle ministeriali ammortamento**: Serve dataset completo. Mitigazione: iniziare con 10 categorie principali, estendere dopo.

---

## Sprint 9: Adempimenti Fiscali

### Objective
Completare gli adempimenti: CU annuale, conservazione digitale, pagamenti PISP e monitor normativo.

### Stories

| ID | Titolo | SP | Priority | Dependencies |
|----|--------|:--:|----------|-------------|
| US-34 | Certificazione Unica (CU) annuale | 5 | Could | US-33 |
| US-37 | Conservazione digitale a norma | 5 | Could | US-04 |
| US-27 | Pagamenti fornitori via PISP | 8 | Could | US-24, US-26 |
| US-28 | Monitor aggiornamenti normativi | 5 | Could | — |

**SP Totali Sprint**: 23 / 24

### Task Breakdown

#### US-34: Certificazione Unica (CU) annuale
| Task | Owner | Stima |
|------|-------|-------|
| Aggregazione ritenute per percettore/anno | Backend | 3h |
| Generazione CU formato ministeriale | Backend | 4h |
| Endpoint POST /cu/generate + GET /cu/export | Backend | 3h |
| Test CU con 3+ percettori | Test | 2h |

#### US-37: Conservazione digitale a norma
| Task | Owner | Stima |
|------|-------|-------|
| Adapter provider conservazione (Aruba/InfoCert) | Backend | 4h |
| Batch giornaliero 02:00 (Celery) + retry backoff | Backend | 3h |
| Hash SHA-256 + pacchetto di versamento XML | Backend | 3h |
| Test batch + gestione errori/retry | Test | 2h |

#### US-27: Pagamenti fornitori via PISP
| Task | Owner | Stima |
|------|-------|-------|
| A-Cube PISP integration (disposizione pagamento) | Backend | 5h |
| Flusso SCA per conferma pagamento | Backend | 3h |
| Aggiornamento stato fattura post-pagamento | Backend | 2h |
| Test PISP su sandbox | Test | 2h |

#### US-28: Monitor aggiornamenti normativi
| Task | Owner | Stima |
|------|-------|-------|
| NormativoAgent: scraping GU + circolari AdE | Backend | 5h |
| Matching normativa → regole business impattate | Backend | 3h |
| Notifica utente + suggerimento aggiornamento | Backend | 2h |
| Test con normativa di esempio | Test | 2h |

### Completion Criteria
- [ ] CU generabile per tutti i percettori dell'anno
- [ ] Conservazione digitale batch funzionante con retry
- [ ] Pagamenti PISP eseguibili con conferma SCA
- [ ] Monitor normativo attivo con notifiche

### Risks
- **Provider conservazione API complessa**: Mitigazione: iniziare con un solo provider (Aruba), aggiungere InfoCert dopo.

---

## Sprint 10: F24 e Dashboard CEO

### Objective
Chiudere la roadmap v0.4: compilazione F24 multi-sezione e dashboard CEO con KPI, budget vs consuntivo e proiezioni.

### Stories

| ID | Titolo | SP | Priority | Dependencies |
|----|--------|:--:|----------|-------------|
| US-38 | F24 compilazione e generazione | 5 | Could | US-22, US-33 |
| US-39 | Dashboard CEO — cruscotto direzionale | 8 | Could | US-13, US-14, US-24 |
| US-40 | Dashboard CEO — KPI e budget vs consuntivo | 8 | Could | US-39 |

**SP Totali Sprint**: 21 / 24

### Task Breakdown

#### US-38: F24 compilazione e generazione
| Task | Owner | Stima |
|------|-------|-------|
| Aggregazione tributi: IVA + ritenute + bollo + INPS | Backend | 4h |
| Compilazione F24 multi-sezione (BR-07) + compensazione | Backend | 4h |
| Export PDF + formato telematico | Backend | 3h |
| Endpoint POST /f24/generate + GET export + PATCH mark-paid | Backend | 3h |
| Test F24 con compensazione crediti | Test | 2h |

#### US-39: Dashboard CEO — cruscotto direzionale
| Task | Owner | Stima |
|------|-------|-------|
| Calcolo KPI: DSO, DPO, EBITDA, fatturato (BR-08) | Backend | 5h |
| Alert concentrazione clienti (top 3 > 60%) | Backend | 2h |
| Confronto YoY con variazione % | Backend | 3h |
| Frontend: CeoDashboard.tsx con grafici recharts | Frontend | 5h |
| Cache Redis 5min per KPI | Backend | 2h |
| Test KPI con dati 3+ mesi | Test | 2h |

#### US-40: Dashboard CEO — KPI e budget vs consuntivo
| Task | Owner | Stima |
|------|-------|-------|
| CRUD budget mensile per categoria | Backend | 3h |
| Confronto budget vs consuntivo + scostamento (BR-09) | Backend | 3h |
| Proiezione fine anno (media mobile) | Backend | 3h |
| Frontend: sezione budget in CeoDashboard.tsx | Frontend | 4h |
| Test budget con scostamenti > 10% | Test | 2h |

### Completion Criteria
- [ ] F24 multi-sezione generato con compensazione crediti
- [ ] Dashboard CEO con KPI, alert, YoY e grafici
- [ ] Budget vs consuntivo con proiezione fine anno
- [ ] **v0.4 completo — tutte le 40 stories implementate**

### Risks
- **Dati insufficienti per KPI**: Dashboard CEO richiede almeno 1 mese. Mitigazione: empty state chiaro + dati demo per onboarding.

---

## Rischi del Piano

| Rischio | Sprint Impattati | Mitigazione |
|---------|-----------------|-------------|
| Odoo integration più complessa del previsto | Sprint 1-3 | Buffer 3 SP/sprint, team con esperienza Odoo |
| FiscoAPI sandbox non disponibile | Sprint 1-2 | Mock completo per CI, test manuale su sandbox appena disponibile |
| OCR accuracy insufficiente | Sprint 5, 8 | Fallback Tesseract + conferma manuale, OCR non bloccante |
| Open Banking consent issues | Sprint 6-7 | Graceful degradation, upload manuale movimenti |
| Scope creep da normativa fiscale | Sprint 7-10 | Regole business configurabili, NormativoAgent per aggiornamenti |
| Sprint 1 overloaded (24 SP) | Sprint 1 | Team allineato su priorità, US-12 può slittare a Sprint 2 se necessario |

---

## PIVOT 5 — Sprint 11-16: Controller Aziendale AI

**Nuove Stories:** US-44 a US-71 (28 stories, 148 SP)
**Velocity confermata:** 24 SP/sprint
**Sprint aggiuntivi:** 6 (Sprint 11-16)

---

## Sprint 11: Import Banca + Corrispettivi + Completeness Score (v0.5)

### Objective
Sbloccare i movimenti bancari e i corrispettivi — le due fonti dati piu critiche dopo le fatture. Il Completeness Score motiva l'utente a collegare nuove fonti.

### Stories

| ID | Titolo | SP | Priority | Dependencies |
|----|--------|:--:|----------|-------------|
| US-44 | Import estratto conto bancario (PDF + LLM) | 8 | Must | US-24 |
| US-45 | Import estratto conto bancario (CSV) | 3 | Must | US-24 |
| US-47 | Import corrispettivi telematici (XML COR10) | 5 | Must | US-04 |
| US-69 | Completeness Score (framing positivo) | 5 | Must | US-16 |
| US-71 | Import silenzioso con eccezioni (max 3 azioni) | 5 | Must | — |

**SP Totale:** 26 | **Focus:** Import Pipeline + UX base

### Acceptance Tests
- Upload PDF UniCredit → movimenti estratti correttamente con LLM
- Upload PDF Credit Agricole → formato diverso, stessa qualita estrazione
- Upload CSV → auto-detect colonne
- Upload XML corrispettivi → parsing COR10, scrittura contabile automatica
- Completeness Score → mostra "Hai sbloccato Fatture. Prossimo: Banca"

### Risks
- LLM extraction imprecisa su layout banca non visti → fallback CSV
- XML corrispettivi: varianti namespace → testare con i 90 file esempio

---

## Sprint 12: Saldi Bilancio + CRUD Banca/Corrispettivi (v0.5)

### Objective
Importare i saldi iniziali del bilancio (punto di partenza contabile) e completare i CRUD manuali per banca e corrispettivi.

### Stories

| ID | Titolo | SP | Priority | Dependencies |
|----|--------|:--:|----------|-------------|
| US-51 | Import saldi bilancio (Excel/CSV + mapping LLM) | 8 | Must | US-12 |
| US-52 | Import saldi bilancio (PDF + LLM) | 5 | Must | US-12 |
| US-46 | CRUD manuale movimenti bancari | 5 | Must | US-24 |
| US-48 | CRUD manuale corrispettivi | 3 | Must | US-47 |
| US-54 | CRUD manuale saldi bilancio (wizard) | 3 | Must | US-12 |

**SP Totale:** 24 | **Focus:** Saldi iniziali + CRUD

### Acceptance Tests
- Upload Excel bilancio TAAL → auto-detect, mapping LLM, preview, import
- Upload PDF bilancio TAAL 2023 → estrazione 856 righe, mapping conti
- CRUD movimenti: aggiungi/modifica/elimina con source="manual"
- Wizard saldi: inserimento guidato → scrittura apertura bilanciata

### Risks
- Mapping conti sorgente → conti AgentFlow: LLM puo suggerire mapping errato → preview obbligatorio con conferma utente

---

## Sprint 13: Budget Agent + Controller Agent (v0.6)

### Objective
Feature core del pivot: l'agente aiuta a creare il budget e confrontare con il consuntivo. Il controller risponde a "Come sto andando?".

### Stories

| ID | Titolo | SP | Priority | Dependencies |
|----|--------|:--:|----------|-------------|
| US-60 | Budget Agent — creazione conversazionale | 8 | Must | US-13 |
| US-61 | Budget Agent — controllo consuntivo mensile | 8 | Must | US-60 |
| US-62 | Controller Agent — "Come sto andando?" | 5 | Must | US-60, US-44 |

**SP Totale:** 21 | **Focus:** Budget + Controller

### Acceptance Tests
- Budget Agent: propone budget da storico, utente aggiusta via chat, salva mese per mese
- Consuntivo: confronto automatico con dati reali, scostamenti con colori
- Controller: risponde in linguaggio naturale con KPI, trend, anomalie

### Risks
- Budget Agent conversazionale: rischio allucinazioni LLM su numeri → validazione stretta Pydantic + conferma utente

---

## Sprint 14: F24 Import + Cash Flow + Adempimenti + Home (v0.6)

### Objective
Completare il ciclo fiscale (F24 import), potenziare cash flow con dati reali, attivare l'agente adempimenti proattivo e la home conversazionale.

### Stories

| ID | Titolo | SP | Priority | Dependencies |
|----|--------|:--:|----------|-------------|
| US-49 | Import F24 versamenti (PDF + LLM) | 5 | Must | US-38 |
| US-50 | CRUD manuale F24 versamenti | 3 | Must | — |
| US-64 | Cash Flow Agent potenziato | 5 | Must | US-44, US-25 |
| US-65 | Adempimenti Agent proattivo | 5 | Must | US-17, US-49 |
| US-67 | Doppio canale notifiche | 5 | Must | US-18 |
| US-72 | Riconciliazione Agent (match fatture ↔ banca) | 5 | Must | US-44, US-26 |

**SP Totale:** 28 | **Focus:** Ciclo fiscale + notifiche proattive + riconciliazione

### Acceptance Tests
- Upload PDF F24 → estrazione codici tributo + importi → scrittura contabile
- Cash Flow: previsione con saldo banca reale + scadenze + rate
- Adempimenti: notifica 10gg prima di scadenza con importo calcolato
- Doppio canale: alert su dashboard + Telegram

---

## Sprint 15: Home Conversazionale + XBRL + Doppio Canale (v0.6)

### Objective
La home diventa conversazionale. Import XBRL per bilanci depositati. Consolidamento UX.

### Stories

| ID | Titolo | SP | Priority | Dependencies |
|----|--------|:--:|----------|-------------|
| US-68 | Home conversazionale (non tabellare) | 8 | Must | US-14, US-62 |
| US-53 | Import saldi bilancio (XBRL) | 5 | Should | US-12 |
| US-59 | Ammortamenti cespiti auto da fatture | 5 | Should | US-31, US-05 |
| US-66 | Alert Agent (anomalie, scadute, sbilanciamenti) | 5 | Should | US-62 |

**SP Totale:** 23 | **Focus:** UX conversazionale + completamento import

### Acceptance Tests
- Home: mostra saluto + fatturato vs target + saldo + max 3 azioni
- XBRL: parsing tassonomia itcc-ci, mapping CEE → conti AgentFlow
- Ammortamenti: rileva fattura "Server Dell €5.000" → propone ammortamento 20%
- Alert: fattura scaduta 45gg → notifica con azione "Invia sollecito"

---

## Sprint 16: Contratti + Finanziamenti + Completamento (v0.7)

### Objective
Completare il quadro con contratti ricorrenti, finanziamenti, email commercialista e l'analisi costi.

### Stories

| ID | Titolo | SP | Priority | Dependencies |
|----|--------|:--:|----------|-------------|
| US-55 | Import contratti ricorrenti (PDF + LLM) | 5 | Should | — |
| US-56 | CRUD manuale contratti ricorrenti | 3 | Should | — |
| US-57 | Import piano ammortamento finanziamenti | 5 | Should | — |
| US-58 | CRUD manuale finanziamenti | 3 | Should | — |
| US-63 | Controller Agent — "Dove perdo soldi?" | 5 | Should | US-62 |
| US-70 | Email auto-generata per commercialista | 3 | Should | — |

**SP Totale:** 24 | **Focus:** Completamento + analisi avanzata

### Acceptance Tests
- Upload PDF contratto affitto → estrazione importo, frequenza, controparte
- Upload PDF piano mutuo → rate future nel cash flow
- Controller: analisi top 5 costi, confronto periodi, anomalie
- Email: template pre-compilato per richiesta bilancio

---

## Riepilogo Sprint 11-16

| Sprint | Stories | SP | Versione | Focus |
|--------|---------|:--:|----------|-------|
| Sprint 11 | US-44,45,47,69,71 | 26 | v0.5 | Import Banca + Corrispettivi + Completeness |
| Sprint 12 | US-51,52,46,48,54 | 24 | v0.5 | Saldi Bilancio + CRUD |
| Sprint 13 | US-60,61,62 | 21 | v0.6 | Budget Agent + Controller |
| Sprint 14 | US-49,50,64,65,67,72 | 28 | v0.6 | F24 + Cash Flow + Adempimenti + Riconciliazione |
| Sprint 15 | US-68,53,59,66 | 23 | v0.6 | Home Conversazionale + XBRL + Alert |
| Sprint 16 | US-55,56,57,58,63,70 | 24 | v0.7 | Contratti + Finanziamenti + Completamento |
| **TOTALE** | **29 stories** | **146** | **v0.5-v0.7** | — |

**Timeline stimata:** 12 settimane (6 sprint × 2 settimane)

---
_Sprint Plan aggiornato post Pivot 5 — 2026-03-29_
_Sprint Plan generato — 2026-03-22_
