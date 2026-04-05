# Sprint Plan — AgentFlow PMI (ContaBot)

**Progetto:** AgentFlow PMI
**Data:** 2026-03-22
**Fase:** 5 — Sprint Planning
**Fonte:** specs/03-user-stories.md, specs/04-tech-spec.md

---

## Sprint Overview

- **Velocity**: 13-16 SP/sprint
- **Durata Sprint**: 2 settimane
- **Sprint Totali**: 27 completati
- **SP Totali Progetto**: ~500 (224 base + 141 Pivot 5 + 72 Pivot 6 + 63 Pivot 7)
- **v0.1-v0.4 (Sprint 1-10):** 224 SP — COMPLETATO
- **v0.5-v0.7 (Sprint 11-16):** 141 SP — Pivot 5: Controller Aziendale AI
- **v0.8 (Sprint 17-22):** 72 SP — Pivot 6: Scadenzario + Finanza Operativa — COMPLETATO
- **v0.9 (Sprint 23-27):** 63 SP — Pivot 7: CRM Sales + Email Marketing — COMPLETATO

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

## Pivot 6: Scadenzario + Finanza Operativa (Sprint 17-22) — COMPLETATO

**Stories source:** `specs/03-user-stories-pivot6.md` (US-70 → US-86)

| Sprint | Stories | SP | Focus |
|--------|---------|-----|-------|
| Sprint 17 | US-70, US-71, US-84, US-85, US-86 | 12 | IVA netto + modelli DB (Scadenza, BankFacility, InvoiceAdvance) |
| Sprint 18 | US-72, US-73, US-74 | 15 | Scadenzario attivo/passivo + generazione auto |
| Sprint 19 | US-75, US-76, US-77 | 16 | Chiusura scadenze + insoluti + cash flow 30/60/90 |
| Sprint 20 | US-78, US-79 | 10 | Cash flow per banca + config fidi |
| Sprint 21 | US-80, US-81, US-82 | 16 | Anticipo fatture completo |
| Sprint 22 | US-83 | 3 | Confronto costi anticipo tra banche |
| **TOTALE** | **17 stories** | **72** | **75 test PASS** |

---

## Pivot 7: CRM Sales + Email Marketing (Sprint 23-27) — COMPLETATO

**Stories source:** `specs/03-user-stories-pivot7-crm.md` (US-87 → US-99)

| Sprint | Stories | SP | Focus |
|--------|---------|-----|-------|
| Sprint 23 | US-87, US-88, US-89, US-99 | 16 | CRM modelli DB + migrazione Odoo→interno |
| Sprint 24 | US-90, US-91 | 13 | Kanban drag-and-drop + pipeline analytics |
| Sprint 25 | US-92, US-93, US-94 | 13 | Adapter Brevo + webhook + template email |
| Sprint 26 | US-95, US-96 | 8 | Invio email singola + dashboard analytics |
| Sprint 27 | US-97, US-98 | 13 | Sequenze automatiche + trigger CRM |
| **TOTALE** | **13 stories** | **63** | **67 test PASS** |

---

## Frontend PWA (non sprint-based) — COMPLETATO

| Fase | Cosa | Impatto |
|------|------|---------|
| PWA Foundation | manifest, SW, icons, install prompt | App installabile |
| Responsive | Bottom nav, safe areas, touch targets | Mobile-first |
| React 19 | Lazy loading, Suspense, useOptimistic | Bundle -66% |
| Design System | DM Sans, CSS variables, dark mode prep | Identita visiva |

---

---

## Pivot 8: Social Selling Configurabile (Sprint 100-106) — v1.2

**Stories source:** `specs/03-user-stories-pivot8-social.md` (US-100 → US-120)
**Tech spec:** `specs/04-tech-spec-pivot8.md` (ADR-011, 32+ endpoint, 11 tabelle, 21 BR)
**Schema DB:** `specs/database/schema-pivot8.md`
**Wireframes:** `specs/ux/wireframes-pivot8.md` (11 wireframe)
**Review:** `specs/review-pivot8-phase4.md` (16 fix applicati, 8/10 overall)

**Architettura:** Core Engine + Configuration Layer (config-driven, multi-tenant)
**Velocity target:** 20 SP/sprint | **Durata sprint:** 2 settimane
**SP Totali Pivot 8:** 140 SP | **Sprint stimati:** 7 (6 feature + 1 buffer)

---

### Sprint 100: Fondamenta — Origini + Tipi Attività + Migration DB

**Objective:** Creare le tabelle fondamentali (origini, activity types), migrare il campo `source` a FK, e configurare il seed automatico per nuovi tenant. Al termine, ogni contatto ha un'origine FK e ogni attività un tipo custom.

| ID | Titolo | SP | Priority | Dependencies |
|----|--------|:--:|----------|-------------|
| US-100 | Admin definisce origine contact custom | 5 | Must | — |
| US-101 | Admin modifica/disattiva origine | 3 | Must | US-100 |
| US-102 | Migrare campo source → origin_id FK | 8 | Must | US-100, US-101 |
| US-104 | Admin definisce tipo attività custom | 5 | Must | — |

**SP Totale:** 21

#### Task Breakdown

**US-100: Admin definisce origine contact custom**
| Task | Owner | Stima |
|------|-------|-------|
| Modello SQLAlchemy `CrmContactOrigin` + Alembic migration | Backend | 3h |
| Trigger `fn_seed_tenant_config()` per seed origini su nuovo tenant | Backend | 2h |
| Endpoint GET/POST `/api/v1/crm/origins` + Pydantic schemas | Backend | 3h |
| Pagina Settings > Origini (lista + form creazione) | Frontend | 4h |
| Unit test: CRUD origini, unicità code per tenant, seed | Test | 2h |

**US-101: Admin modifica/disattiva origine**
| Task | Owner | Stima |
|------|-------|-------|
| Endpoint PATCH `/api/v1/crm/origins/{id}` (codice read-only) | Backend | 2h |
| Soft delete logic (is_active=false, contatti rimangono) | Backend | 1h |
| UI: form modifica + badge disattivata + conteggio contatti | Frontend | 2h |
| Test: codice immutabile, soft delete, 409 su hard delete con contatti | Test | 1h |

**US-102: Migrare campo source → origin_id FK**
| Task | Owner | Stima |
|------|-------|-------|
| Alembic migration Step 1: ADD COLUMN origin_id nullable | Backend | 1h |
| Script backfill: source string → crm_contact_origins + FK mapping | Backend | 4h |
| Backfill contatti con source=NULL → origine "da_classificare" | Backend | 1h |
| Alembic migration Step 2: ADD CONSTRAINT NOT NULL (post-backfill) | Backend | 1h |
| Test: migration up/down, data preservation, null handling, rollback | Test | 3h |

**US-104: Admin definisce tipo attività custom**
| Task | Owner | Stima |
|------|-------|-------|
| Modello SQLAlchemy `CrmActivityType` + migration | Backend | 2h |
| Seed activity types in `fn_seed_tenant_config()` | Backend | 1h |
| Endpoint GET/POST `/api/v1/crm/activity-types` | Backend | 2h |
| Pagina Settings > Tipi Attività (lista + form + flag "conta ultimo contatto") | Frontend | 3h |
| Test: CRUD, unicità, flag counts_as_last_contact logic | Test | 2h |

#### Completion Criteria
- [ ] Tabelle `crm_contact_origins` e `crm_activity_types` create con indici e constraint
- [ ] Migration source→origin_id completata senza data loss (backfill 100%)
- [ ] Trigger seed per nuovi tenant funzionante (origini + activity types)
- [ ] UI Settings: CRUD origini e tipi attività visibili e funzionanti
- [ ] 15+ test PASS su origini, migration, activity types

#### Risks
- **Migration data loss**: Mitigazione → rollback preserva campo `source` per 30 gg
- **Seed trigger race condition**: Mitigazione → seed in transaction con tenant creation

---

### Sprint 101: RBAC Engine — Ruoli + Permessi + Utenti Esterni

**Objective:** Implementare il motore RBAC granulare con matrice permessi, utenti esterni con scadenza accesso, e middleware di autorizzazione su tutti gli endpoint CRM. Al termine, l'accesso ai dati è controllato per ruolo e scope.

| ID | Titolo | SP | Priority | Dependencies |
|----|--------|:--:|----------|-------------|
| US-108 | Admin definisce ruolo custom con matrice RBAC | 8 | Must | — |
| US-109 | Admin crea utente esterno con scadenza | 8 | Must | US-108 |
| US-103 | Assegnare origine obbligatoria al contact | 5 | Must | US-100, US-102 |

**SP Totale:** 21

#### Task Breakdown

**US-108: Admin definisce ruolo custom con matrice RBAC**
| Task | Owner | Stima |
|------|-------|-------|
| Modelli `CrmRole` + `CrmRolePermission` + migration | Backend | 3h |
| Seed ruoli sistema (Owner, Admin, Sales Rep, Manager, Viewer) | Backend | 2h |
| Seed permission matrix per ruoli default | Backend | 2h |
| Endpoint GET/POST/DELETE `/api/v1/crm/roles` | Backend | 3h |
| Middleware RBAC: intercetta endpoint, verifica (role, entity, permission, scope) | Backend | 5h |
| UI: pagina Ruoli + matrice permessi checkbox editabile | Frontend | 4h |
| Test: permission evaluation, 403 su azione negata, ruoli sistema non modificabili | Test | 3h |

**US-109: Admin crea utente esterno con scadenza**
| Task | Owner | Stima |
|------|-------|-------|
| ALTER TABLE users: user_type, access_expires_at, crm_role_id, default_origin_id, default_product_id | Backend | 2h |
| Backfill utenti esistenti (user_type=internal, crm_role_id=Admin) | Backend | 1h |
| Endpoint POST users con tipo external + scadenza | Backend | 2h |
| Login middleware: blocca se access_expires_at < now() | Backend | 2h |
| Cron job nightly: disattiva utenti scaduti | Backend | 2h |
| UI: form nuovo utente esterno (WF-11) + badge scadenza | Frontend | 3h |
| Test: scadenza login, cron disattivazione, extend access | Test | 2h |

**US-103: Assegnare origine obbligatoria al contact**
| Task | Owner | Stima |
|------|-------|-------|
| Aggiornare form contatto: dropdown origini attive (required) | Frontend | 2h |
| Endpoint POST `/api/v1/crm/contacts/{id}/change-origin` (bulk) | Backend | 2h |
| Validazione origin_id NOT NULL su create/update contact | Backend | 1h |
| Test: required validation, bulk change, origine disattivata visibile ma non selezionabile | Test | 2h |

#### Completion Criteria
- [ ] Middleware RBAC funzionante su tutti gli endpoint `/api/v1/crm/*`
- [ ] 5 ruoli sistema creati per ogni tenant, matrice permessi completa
- [ ] Utenti esterni con scadenza: login bloccato dopo data, cron disattivazione
- [ ] Origine obbligatoria su contatto: dropdown, bulk change, validazione
- [ ] 20+ test PASS su RBAC, permessi, scadenza, origini

#### Risks
- **Middleware RBAC performance**: Mitigazione → cache permessi in Redis (TTL 5min)
- **Cron job scadenze**: Mitigazione → fallback con check a login-time (doppia verifica)

---

### Sprint 102: Pre-funnel + Attività Custom + Audit Trail

**Objective:** Completare il modulo attività con pre-funnel pipeline, logging custom, e audit trail immutabile. Al termine, la pipeline Kanban mostra stadi pre-funnel e ogni azione è tracciata.

| ID | Titolo | SP | Priority | Dependencies |
|----|--------|:--:|----------|-------------|
| US-106 | Admin definisce stadi pre-funnel | 5 | Should | — |
| US-105 | Admin modifica/disattiva tipo attività | 3 | Should | US-104 |
| US-107 | User logga attività con tipo custom | 5 | Must | US-104 |
| US-111 | Audit trail immutabile per azioni utenti | 8 | Must | US-108, US-109 |

**SP Totale:** 21

#### Task Breakdown

**US-106: Admin definisce stadi pre-funnel**
| Task | Owner | Stima |
|------|-------|-------|
| ALTER TABLE crm_pipeline_stages: ADD stage_type + constraint | Backend | 1h |
| Endpoint POST/PATCH/PUT reorder per pipeline stages | Backend | 3h |
| Validazione: pre_funnel sequence < first pipeline stage | Backend | 1h |
| UI Pipeline Kanban: rendering colonne pre-funnel (colore diverso) | Frontend | 3h |
| Test: creazione pre-funnel, validazione sequence, drag-and-drop | Test | 2h |

**US-105: Admin modifica/disattiva tipo attività**
| Task | Owner | Stima |
|------|-------|-------|
| Endpoint PATCH activity-types (codice read-only) + soft delete | Backend | 1h |
| UI: form modifica + badge disattivato + warning ultimo tipo | Frontend | 2h |
| Test: codice immutabile, soft delete, 409 su hard delete | Test | 1h |

**US-107: User logga attività con tipo custom**
| Task | Owner | Stima |
|------|-------|-------|
| Endpoint POST `/api/v1/crm/activities` con type_id FK | Backend | 2h |
| Logic: se counts_as_last_contact=true → update contact.last_contact_at | Backend | 2h |
| UI: form nuova attività con dropdown tipi custom + bulk log | Frontend | 3h |
| Test: type-driven behavior, last_contact_at update, bulk, required fields | Test | 2h |

**US-111: Audit trail immutabile**
| Task | Owner | Stima |
|------|-------|-------|
| Tabella `crm_audit_log` + trigger immutabilità (no UPDATE/DELETE) | Backend | 2h |
| Service `AuditLogService.log()` chiamato da tutti i service CRM | Backend | 3h |
| Logging: CRUD, login, logout, export, permission_denied con diff JSON | Backend | 2h |
| UI: pagina Audit Log con filtri (utente, data, azione, entità) + export CSV | Frontend | 3h |
| Test: immutabilità trigger, log permission_denied, export | Test | 2h |

#### Completion Criteria
- [ ] Pipeline Kanban estesa con stadi pre-funnel visivamente distinti
- [ ] Attività custom loggabili con aggiornamento automatico last_contact_at
- [ ] Audit log immutabile: trigger testato, UI con filtri, export CSV
- [ ] 15+ test PASS su pre-funnel, attività custom, audit trail

#### Risks
- **Audit log volume**: Mitigazione → indici su (tenant_id, created_at DESC), retention strategy via partitioning
- **Performance logging**: Mitigazione → audit log asincrono (background task)

---

### Sprint 103: Catalogo Prodotti + Deal-Product M2M

**Objective:** Implementare il catalogo prodotti con categorie, pricing model, e associazione M2M deal-prodotto. Al termine, ogni deal ha prodotti associati con revenue calcolata automaticamente.

| ID | Titolo | SP | Priority | Dependencies |
|----|--------|:--:|----------|-------------|
| US-112 | Admin definisce prodotto/servizio nel catalogo | 5 | Must | — |
| US-113 | Admin modifica/disattiva prodotto | 3 | Should | US-112 |
| US-114 | Associare 1+ prodotti a un deal | 5 | Must | US-112 |
| US-110 | Assegnare canale/prodotto default a utente esterno | 5 | Should | US-109 |

**SP Totale:** 18

#### Task Breakdown

**US-112: Admin definisce prodotto/servizio**
| Task | Owner | Stima |
|------|-------|-------|
| Modelli `CrmProduct` + `CrmProductCategory` + migration (categories PRIMA di products) | Backend | 3h |
| Endpoint CRUD `/api/v1/crm/products` + `/api/v1/crm/product-categories` | Backend | 3h |
| UI: pagina Catalogo Prodotti con filtri + form nuovo prodotto (pricing condizionale) | Frontend | 4h |
| Test: CRUD, pricing models, category inline creation, codice univoco | Test | 2h |

**US-113: Admin modifica/disattiva prodotto**
| Task | Owner | Stima |
|------|-------|-------|
| PATCH endpoint + soft delete logic (storico immutabile deal) | Backend | 1h |
| UI: form modifica + badge + pricing change non retroattivo | Frontend | 2h |
| Test: soft delete, deal mantiene prezzo originale, 409 su hard delete | Test | 1h |

**US-114: Associare 1+ prodotti a un deal**
| Task | Owner | Stima |
|------|-------|-------|
| Tabella pivot `crm_deal_products` + migration (no UNIQUE su deal+product) | Backend | 2h |
| Endpoint POST/DELETE `/api/v1/crm/deals/{id}/products` | Backend | 2h |
| Revenue calculation: line_total = (price_override ?? base_price) × quantity | Backend | 2h |
| UI: sezione Prodotti nel deal detail con add/remove + subtotali | Frontend | 3h |
| Test: revenue calc, multiple same product, almeno 1 prodotto required | Test | 2h |

**US-110: Assegnare canale/prodotto default a utente esterno**
| Task | Owner | Stima |
|------|-------|-------|
| Logic default_origin_id → pre-compila form contatto + row-level filter | Backend | 2h |
| Logic default_product_id → pre-seleziona prodotto su nuovo deal | Backend | 1h |
| Row-level security: utente esterno vede SOLO contatti del suo canale | Backend | 3h |
| UI: campi default nel profilo utente (read-only per external) | Frontend | 2h |
| Test: data segregation, 403 su accesso cross-canale, pre-compilazione | Test | 2h |

#### Completion Criteria
- [ ] Catalogo prodotti funzionante con 3 pricing models
- [ ] Deal detail mostra prodotti associati con revenue auto-calcolata
- [ ] Utenti esterni con canale/prodotto default e row-level security
- [ ] 15+ test PASS su prodotti, deal-product, row-level security

#### Risks
- **Row-level security bypass**: Mitigazione → test penetration su API dirette + middleware enforce
- **Revenue calculation precision**: Mitigazione → NUMERIC(12,2) + test con edge case decimali

---

### Sprint 104: Analytics — Dashboard KPI + Scorecard + Filtri

**Objective:** Costruire la dashboard KPI componibile con widget configurabili, scorecard per collaboratore, e filtri per prodotto sulla pipeline. Al termine, manager e admin hanno visibilità real-time su performance.

| ID | Titolo | SP | Priority | Dependencies |
|----|--------|:--:|----------|-------------|
| US-116 | Admin crea dashboard KPI componibile | 8 | Should | US-112, US-114 |
| US-117 | Scorecard collaboratore con metriche custom | 5 | Should | US-114 |
| US-115 | Filtrare pipeline e deal per prodotto | 5 | Should | US-114 |

**SP Totale:** 18

#### Task Breakdown

**US-116: Admin crea dashboard KPI componibile**
| Task | Owner | Stima |
|------|-------|-------|
| Tabella `crm_dashboard_widgets` + migration | Backend | 1h |
| Endpoint CRUD `/api/v1/crm/dashboards` con validazione DashboardLayoutSchema | Backend | 3h |
| Widget engine: revenue_mom, deal_count, win_rate, avg_deal_size, pipeline_by_stage | Backend | 5h |
| UI: dashboard builder con grid layout + widget picker + filtri per widget | Frontend | 6h |
| Cache Redis: pre-calcolo widget metrics (TTL 5min) | Backend | 2h |
| Test: widget calculation, JSON schema validation, filtri periodo/prodotto/utente | Test | 3h |

**US-117: Scorecard collaboratore**
| Task | Owner | Stima |
|------|-------|-------|
| Endpoint GET `/api/v1/crm/scorecard/{user_id}` con aggregazioni | Backend | 3h |
| Metriche: deal_count, revenue_closed, win_rate, avg_days_to_close, last_contact | Backend | 2h |
| UI: pagina Scorecard con KPI cards + trend vs periodo precedente | Frontend | 3h |
| Test: aggregation correctness, empty data handling, filter by product | Test | 2h |

**US-115: Filtrare pipeline e deal per prodotto**
| Task | Owner | Stima |
|------|-------|-------|
| Query filter: JOIN crm_deal_products su pipeline/deals con product_id | Backend | 2h |
| URL state: filtro salvato in query params | Frontend | 1h |
| UI: dropdown filtro prodotto su Pipeline Kanban e lista deal | Frontend | 2h |
| Test: filtro OR multi-product, analytics coerenti con filtro, default "tutti" | Test | 1h |

#### Completion Criteria
- [ ] Dashboard KPI con almeno 6 widget preset funzionanti
- [ ] Scorecard collaboratore con 5 metriche aggregate
- [ ] Pipeline filtrabile per prodotto con URL state
- [ ] Cache Redis per widget metrics
- [ ] 15+ test PASS su dashboard, scorecard, filtri

#### Risks
- **Dashboard performance con molti deal**: Mitigazione → aggregazioni CTE + cache Redis
- **Widget configuration complexity**: Mitigazione → preset widget con config semplice, builder avanzato in v2

---

### Sprint 105: Compensi — Regole + Calcolo + Export + Chiusura

**Objective:** Implementare il motore compensi con regole configurabili, calcolo automatico mensile, ciclo approvazione e export. Al termine, le provvigioni sono calcolate e gestite end-to-end.

| ID | Titolo | SP | Priority | Dependencies |
|----|--------|:--:|----------|-------------|
| US-118 | Admin configura modello compensi con regole | 8 | Could | US-117 |
| US-119 | Calcolo e visualizzazione compensi mensili | 8 | Should | US-118 |
| US-120 | Export e management ciclo pagamento | 5 | Should | US-119 |

**SP Totale:** 21

#### Task Breakdown

**US-118: Admin configura modello compensi**
| Task | Owner | Stima |
|------|-------|-------|
| Tabella `crm_compensation_rules` + migration | Backend | 2h |
| Endpoint CRUD `/api/v1/crm/compensation/rules` | Backend | 2h |
| Engine: percent_revenue, fixed_amount, tiered (NO formula per MVP) | Backend | 4h |
| Conditions evaluation: product_ids, origin_ids, user_ids, date range | Backend | 3h |
| UI: pagina Modello Compensi + form regola + preview calcolo | Frontend | 4h |
| Test: tiered calculation, conditions, priority ordering, conflict detection | Test | 3h |

**US-119: Calcolo e visualizzazione compensi mensili**
| Task | Owner | Stima |
|------|-------|-------|
| Tabella `crm_compensation_entries` + migration | Backend | 1h |
| Cron job: calcolo mensile con CTE pre-aggregata per user revenue | Backend | 4h |
| Indice `idx_crm_deals_comp_calc` per performance | Backend | 0.5h |
| Endpoint GET `/api/v1/crm/compensation/monthly` con filtri | Backend | 2h |
| UI: pagina Compensi Mensili con tabella + breakdown dettaglio per deal | Frontend | 4h |
| Notifica admin: "Compensi [mese] calcolati, attendono conferma" | Backend | 1h |
| Test: calcolo corretto, status draft→confirmed, error su conflitto regole | Test | 3h |

**US-120: Export e ciclo pagamento**
| Task | Owner | Stima |
|------|-------|-------|
| Endpoint POST `/api/v1/crm/compensation/confirm` (bulk) | Backend | 2h |
| Endpoint POST `/api/v1/crm/compensation/mark-paid` (bulk) | Backend | 1h |
| Export Excel: colonne con breakdown + hash SHA256 | Backend | 2h |
| UI: bottoni Conferma / Segna Pagato / Esporta + dialog conferma | Frontend | 2h |
| Audit log: registra conferma e pagamento | Backend | 1h |
| Test: stato transition, export integrity, bulk action, utente esterno vede solo sua riga | Test | 2h |

#### Completion Criteria
- [ ] Regole compensi configurabili (3 metodi di calcolo)
- [ ] Cron job calcolo mensile funzionante con CTE ottimizzata
- [ ] Ciclo draft → confirmed → paid completo con audit trail
- [ ] Export Excel con hash integrità
- [ ] 15+ test PASS su regole, calcolo, export, ciclo pagamento

#### Risks
- **Calcolo compensi errato**: Mitigazione → status "draft" obbligatorio, admin verifica prima di conferma
- **Regole in conflitto**: Mitigazione → status "error" con notifica, risoluzione manuale obbligatoria

---

### Sprint 106: Buffer — Integration Testing + Bug Fix + Stabilizzazione

**Objective:** Nessuna nuova feature. Sprint dedicato a integration testing end-to-end tra tutti i 5 moduli, fix bug emersi dagli sprint 100-105, performance tuning, e preparazione deploy. Al termine, il Pivot 8 è stabile e pronto per produzione.

| ID | Titolo | SP | Priority | Dependencies |
|----|--------|:--:|----------|-------------|
| BUF-01 | Integration test cross-modulo | 5 | Must | Sprint 100-105 |
| BUF-02 | Bug fix backlog Sprint 100-105 | 5 | Must | Sprint 100-105 |
| BUF-03 | Performance tuning + indici DB | 3 | Should | Sprint 100-105 |
| BUF-04 | E2E test Playwright (happy path 5 moduli) | 5 | Should | BUF-01 |
| BUF-05 | Runbook deploy + rollback migration | 2 | Must | Sprint 100 |

**SP Totale:** 20

#### Task Breakdown

**BUF-01: Integration test cross-modulo**
| Task | Owner | Stima |
|------|-------|-------|
| Test flusso completo: crea origine → crea contatto con origine → crea deal con prodotto → logga attività → verifica dashboard KPI | Test | 4h |
| Test RBAC end-to-end: utente esterno con canale default → verifica row-level filter su contatti, deal, pipeline, export | Test | 3h |
| Test compensi end-to-end: crea regola → chiudi deal → calcola compensi → verifica importo → conferma → export | Test | 3h |
| Test audit trail: verifica che ogni azione dei test precedenti è loggata con dettagli corretti | Test | 2h |
| Test concurrent access: 2 admin modificano stessa origine/ruolo simultaneamente | Test | 2h |

**BUF-02: Bug fix backlog Sprint 100-105**
| Task | Owner | Stima |
|------|-------|-------|
| Triage bug emersi durante Sprint 100-105 (classificare: critical/high/medium) | Backend | 1h |
| Fix bug critical e high (stima 3-5 bug) | Backend | 4h |
| Fix bug frontend (UI glitch, form validation edge case) | Frontend | 3h |
| Regression test su bug fixati | Test | 2h |

**BUF-03: Performance tuning + indici DB**
| Task | Owner | Stima |
|------|-------|-------|
| EXPLAIN ANALYZE su query critiche: dashboard widget, compensation calc, audit log filter | Backend | 2h |
| Aggiungere indici mancanti identificati da query plan | Backend | 1h |
| Verifica cache Redis: TTL corretti, hit rate su permission check e widget | Backend | 1h |
| Load test: 50 utenti concorrenti su dashboard + pipeline (k6 o locust) | Test | 2h |

**BUF-04: E2E test Playwright (happy path 5 moduli)**
| Task | Owner | Stima |
|------|-------|-------|
| Setup Playwright per pagine Settings (Origini, Tipi Attività, Ruoli, Prodotti) | Test | 2h |
| E2E: crea origine → verifica in dropdown contatto → crea contatto | Test | 2h |
| E2E: crea utente esterno → login → verifica visibilità limitata | Test | 2h |
| E2E: dashboard KPI → verifica widget rendering con dati reali | Test | 2h |
| E2E: compensi → calcola → conferma → verifica status change | Test | 2h |

**BUF-05: Runbook deploy + rollback migration**
| Task | Owner | Stima |
|------|-------|-------|
| Scrivere runbook: ordine migration Alembic (11 tabelle + 4 ALTER) | Backend | 1h |
| Scrivere runbook rollback: procedura step-by-step per down migration | Backend | 1h |
| Documentare seed data: cosa succede per tenant esistenti vs nuovi | Backend | 0.5h |
| Checklist pre-deploy: env vars, Redis config, cron job compensi | Backend | 0.5h |
| Dry-run deploy su staging | Backend | 1h |

#### Completion Criteria
- [ ] Integration test cross-modulo: tutti i flussi end-to-end passano
- [ ] 0 bug critical aperti, max 2 bug medium aperti (documentati)
- [ ] Query critiche < 100ms (p95) verificate con EXPLAIN ANALYZE
- [ ] E2E Playwright: 5+ test happy path passano su tutti i moduli
- [ ] Runbook deploy pronto e validato su staging
- [ ] Cache Redis hit rate > 80% su permission check

#### Risks
- **Bug critici scoperti tardi**: Mitigazione → se > 3 bug critical, estendere Sprint 106 di 1 settimana
- **Performance non accettabile**: Mitigazione → degradazione graceful (disabilita widget pesanti, fallback a query senza cache)

---

## Riepilogo Sprint 100-106 (Pivot 8)

| Sprint | Stories | SP | Focus |
|--------|---------|-----|-------|
| Sprint 100 | US-100, 101, 102, 104 | 21 | Fondamenta: Origini + Activity Types + Migration |
| Sprint 101 | US-108, 109, 103 | 21 | RBAC Engine: Ruoli + Permessi + Utenti Esterni |
| Sprint 102 | US-106, 105, 107, 111 | 21 | Pre-funnel + Attività Custom + Audit Trail |
| Sprint 103 | US-112, 113, 114, 110 | 18 | Catalogo Prodotti + Deal-Product M2M |
| Sprint 104 | US-116, 117, 115 | 18 | Dashboard KPI + Scorecard + Filtri Prodotto |
| Sprint 105 | US-118, 119, 120 | 21 | Compensi: Regole + Calcolo + Export |
| Sprint 106 | BUF-01→05 | 20 | Buffer: Integration Test + Bug Fix + Stabilizzazione |
| **TOTALE** | **21 stories + 5 buffer** | **140** | **7 sprint × 2 settimane = 14 settimane** |

**Timeline stimata:** 14 settimane (aprile → luglio 2026)

**Milestone intermedie:**
- Fine Sprint 101 (settimana 4): Core engine funzionante — origini, RBAC, migration completata
- Fine Sprint 103 (settimana 8): Prodotti e row-level security — MVP utilizzabile internamente
- Fine Sprint 105 (settimana 12): Analytics e compensi — feature-complete
- Fine Sprint 106 (settimana 14): Stabilizzato, testato E2E, pronto per deploy produzione

---

## Riepilogo Completo

| Blocco | Sprint | Stories | SP | Test |
|--------|--------|---------|-----|------|
| Base (v0.1-v0.4) | 1-10 | 40 | 224 | 369 |
| Pivot 5 (v0.5-v0.7) | 11-16 | 29 | 146 | ~90 |
| Pivot 6 (v0.8) | 17-22 | 17 | 72 | 75 |
| Pivot 7 (v0.9) | 23-27 | 13 | 63 | 67 |
| **Pivot 8 (v1.1)** | **100-106** | **21 + 5 buf** | **140** | **TBD** |
| **TOTALE** | **34** | **~125** | **~645** | **~601+** |

---
_Sprint Plan aggiornato: 2026-04-04 — Pivot 8 Social Selling pianificato (Sprint 100-106, incluso buffer)_
_Sprint Plan aggiornato post Pivot 5 — 2026-03-29_
_Sprint Plan generato — 2026-03-22_
