# Changelog Specs: AgentFlow PMI

## Formato
- **Data**: ISO timestamp
- **Fase**: numero fase
- **Azione**: cosa è stato fatto
- **Contesto**: motivo/background

---

### Handoff da BrainStorming
- **Data**: 2026-03-22
- **Fase**: Handoff BS → UMCC
- **Azione**: Creati specs/01-vision.md, specs/02-prd.md, specs/04-tech-spec.md tramite mappatura strutturata dal brainstorming.
- **Contesto**: Brainstorming completato con 12 documenti (assessment, brainstorm trio, problem framing, market research, MVP scope, architecture, security). Mappatura: problem-framing → vision (JTBD, personas, metriche, vincoli), market-research + mvp-scope → PRD (competitor, MoSCoW, milestones, pricing, rischi), architecture + security → tech-spec (stack, ADR, schema DB, API, agent architecture, compliance). Fase 3 (User Stories) è il prossimo step.

---

### Fase 3: User Stories generate
- **Data**: 2026-03-22
- **Fase**: 3 — User Stories e Acceptance Criteria
- **Azione**: Generati 23 user stories con 92 acceptance criteria (4 AC ciascuna, formato DATO-QUANDO-ALLORA). Copertura: 6 epic (Cattura Fatture, Categorizzazione, Contabilità, Dashboard, Fisco, Open Banking/Cash Flow). 141 story points totali. v0.1=11 stories (60 SP), v0.2=4 stories (20 SP), v0.3=7 stories (53 SP), v0.4=1 story (8 SP).
- **Contesto**: Stories derivate da specs/02-prd.md (8 epic funzionali) e specs/01-vision.md (3 personas JTBD). Ogni story ha: happy path, 2 error cases, 1 edge case. Dipendenze tra stories mappate. Story points in Fibonacci (1-13).

---

### Review Fase 3 — User Stories
- **Data**: 2026-03-22
- **Fase**: 3 — Review avversaria
- **Agente**: Review
- **Risultato**: FAIL
- **Finding**: 20 critici (5 assunzioni, 5 contraddizioni, 5 linguaggio vago, 5 error path mancanti), 20 edge case
- **Azioni**: (1) Aggiungere US autenticazione/signup, (2) Aggiungere US Bilancio CEE F8, (3) Creare matrice tracciabilità PRD→Stories, (4) Aggiungere error path mancanti a 5 stories, (5) Chiarire soglia learning e limiti sync, (6) Performance target per operazioni Odoo/OCR
- **Report**: specs/technical/review-report.md

---

### PIVOT: Cassetto fiscale come fonte primaria
- **Data**: 2026-03-22
- **Causa**: Le fatture elettroniche (95%+ del totale) si leggono dal cassetto fiscale AdE, non dall'email. L'email va aggiunta come MCP server in un secondo tempo.
- **Impatto**: 4 file aggiornati, 1 file rigenerato
- **File aggiornati**: specs/01-vision.md (H1, personas, metriche), specs/02-prd.md (Epic 0+1 riscritte, MoSCoW, milestones), specs/04-tech-spec.md (agent flow, roadmap, API, auth SPID)
- **File rigenerato**: specs/03-user-stories.md — da 23 a 28 stories, da 141 a 168 SP. Aggiunte: Epic 0 Auth (US-01/02/03), US-23 Bilancio CEE, US-28 Monitor Normativo. FiscoAPI da v0.3 a v0.1 Must. Gmail da v0.1 Must a v0.2 Should (MCP).
- **Fix review inclusi**: 40 finding della review pre-pivot risolti (autenticazione, tracciabilita PRD, error path, edge case, performance target, dead letter queue, concurrent access, soglie configurabili)
- **Report impatto**: specs/technical/pivot-impact-analysis.md

---

### PIVOT v2: Integrazione Analisi Gap CEO
- **Data**: 2026-03-22
- **Causa**: L'analisi gap ha evidenziato che il PRD copre bene il ciclo fattura ma manca di 7 aree critiche per un CEO di PMI: Controllo di Gestione (0%), HR (0%), CRM (0%), Progetti (0%), gap contabili (note spese, cespiti, ritenute, ratei, bollo), gap fisco (F24, CU, conservazione digitale), Dashboard CEO.
- **Impatto**: 5 file aggiornati, 1 nuovo (analisi-gap-ceo.md), 1 nuovo (pivot-impact-analysis-v2.md)
- **File aggiornati**:
  - `specs/01-vision.md` — Persona 4 CEO, 4a frustrazione, H4 cruscotto CEO, strategia a 5 fasi (v0.1→v2.0)
  - `specs/02-prd.md` — Epic 8-12 nuove (Gap Contabili, Cruscotto CEO, HR, CRM, Progetti), MoSCoW espanso, milestones v1.0-v2.0, budget anno 2, pricing tier Executive
  - `specs/03-user-stories.md` — 12 nuove stories (US-29→US-40): note spese, cespiti, ritenute, CU, bollo, ratei, conservazione, F24, dashboard CEO. Da 28 a 40 stories, da 168 a 233 SP.
  - `specs/04-tech-spec.md` — Agent Roadmap esteso v1.0-v2.0, note architetturali ControllerAgent/HRAgent/CommAgent/ProjectAgent, schema DB con tabelle expenses/assets/withholding_taxes/budgets
  - `specs/technical/flusso-informazioni.md` — Sezioni 9 (adempimenti) e 10 (riepilogo) aggiornate con v1.0-v2.0
- **Invariato**: v0.1 (12 stories, 69 SP) e v0.2 (7 stories, 32 SP) non modificati
- **Report impatto**: specs/technical/pivot-impact-analysis-v2.md
- **Report analisi**: specs/technical/analisi-gap-ceo.md

---

### Review Fase 3 v3 — Stories US-29→US-40 (post-pivot 2)
- **Data**: 2026-03-22
- **Fase**: 3 — Review avversaria (3-pass)
- **Agente**: Review
- **Risultato**: PASS (condizionato)
- **Finding**: 0 critici, 6 non-blocking, 8 edge case
- **Dettaglio**:
  - Pass 1 Completeness: 7/9 (78%) — 3 stories con <4 AC, 5 stories con <2 error path
  - Pass 2 Adversarial: 6 finding (deps OCR US-29, bollo su fatture passive, overlap scadenza/F24, batch orario, soglie fisse, soft-dep CU→F24)
  - Pass 3 Edge Case: 8 edge case (dedup note spese, limiti upload, auto-approvazione titolare, beni raggruppabili, aliquote ritenuta diverse, risconti IVA indetraibile, F24 multi-sezione, permessi dashboard CEO)
- **Azioni**: (1) Aggiungere AC a US-30/US-32/US-35, (2) Aggiungere error path a US-31/US-37, (3) Fix deps US-29, (4) Chiarire ownership scadenza vs F24
- **Report**: specs/technical/review-report-v3.md

---

### Fix Review v3 — AC mancanti integrati
- **Data**: 2026-03-22
- **Fase**: 3 — Fix post-review
- **Azione**: Aggiunti 9 AC a 5 stories (US-30, US-31, US-32, US-35, US-37). Fix deps US-29 (+US-09). Chiarito overlap scadenza US-33 vs F24 US-38. Tutte le stories ora hanno >=4 AC e >=2 error path.
- **Risultato**: Review v3 aggiornata a PASS (da PASS condizionato). Completeness 9/9.

---

### Review Fase 5 — Sprint Plan
- **Data**: 2026-03-22
- **Fase**: 5 — Review avversaria
- **Agente**: Review
- **Risultato**: PASS (9/9 completeness, 0 contraddizioni)
- **Finding**: 5 non-blocking (team size, buffer, frontend setup, accuracy target, stime ore)
- **Edge case**: 6 (carico sprint 1-2, regression testing, infra setup, catena dipendenze)
- **Azioni**: (1) Aggiungere task frontend setup + CI/CD in Sprint 1, (2) Documentare team size, (3) Budget regression testing da Sprint 4
- **Report**: specs/technical/review-report-v5.md

---

### Fase 5: Sprint Planning
- **Data**: 2026-03-22
- **Fase**: 5 — Sprint Planning
- **Azione**: Generato sprint plan con 10 sprint (224 SP totali, velocity 20-24 SP/sprint, 2 settimane):
  - Sprint 1-3: v0.1 Must Have (69 SP) — Auth, SPID, pipeline fatture, contabilità, onboarding
  - Sprint 4-5: v0.2 Should Have (32 SP) + inizio v0.3 — canali secondari, OCR, notifiche, scadenzario, bilancio CEE
  - Sprint 6-8: v0.3 Could Have (69 SP) — Open Banking, fatturazione attiva, IVA, riconciliazione, gap contabili (note spese, cespiti, ritenute, bollo, ratei)
  - Sprint 9-10: v0.4 Could Have (44 SP) — CU, conservazione, PISP, F24, Dashboard CEO, budget
  - Task breakdown per ogni story (3-8 task con owner e stima)
  - Rischi del piano documentati (6 rischi con mitigazione)
- **File creati**: specs/05-sprint-plan.md, CLAUDE.md (project context)

---

### Review Fase 4 — Tech Spec
- **Data**: 2026-03-22
- **Fase**: 4 — Review avversaria
- **Agente**: Review
- **Risultato**: FAIL (3 contraddizioni)
- **Completeness**: 9.5/11 (86%) — 2 item parziali (API schema mancanti, 5 stories non mappate)
- **Contraddizioni**: 3 (schema inline vs canonico, numerazione endpoint duplicata, campo raw_data/raw_xml)
- **Finding critici**: 5 (mapping incompleto, no req/res schema, Cloud Vision residency, Odoo timeline, costi vaghi)
- **Edge case**: 11 (concurrency 3, empty state 2, limiti 2, permessi 2, network 2)
- **Azioni blocking**: (1) Sincronizzare/rimuovere schema inline, (2) Rinumerare endpoint 1-56, (3) Allineare campo invoices raw_xml, (4) Completare mapping 5 stories mancanti
- **Report**: specs/technical/review-report-v4.md

---

### Fix Review v4 — Contraddizioni risolte
- **Data**: 2026-03-22
- **Fase**: 4 — Fix post-review
- **Azione**: Applicati 4 fix blocking:
  - (1) Rimosso schema inline (~280 righe SQL) da 04-tech-spec.md, sostituito con tabella riepilogativa + riferimento a database/schema.md canonico. Risolve CONTRADICTION-01 e CONTRADICTION-03.
  - (2) Rinumerati endpoint da 1-61 (erano 1-7 + 3-56 con duplicati). Totale effettivo: 61 endpoint.
  - (3) Aggiunte 5 stories mancanti al mapping (US-07, US-08, US-09, US-18, US-19). Mapping ora 40/40.
  - (4) Aggiornati ruoli RBAC: CEO endpoints a "owner/admin", F24 mark-paid a "owner/admin".
- **Risultato**: Review v4 aggiornata a PASS. Completeness 10.5/11.

---

### Frontend React IMPLEMENTATO — 31 pagine, 13 componenti, build PASS
- **Data**: 2026-03-23
- **Fase**: 7 (Frontend)
- **Azione**: Implementato frontend React completo con tutte le pagine del PRD
- **Stack**: React 19 + TypeScript + Vite 8 + Tailwind CSS 4 + Zustand + TanStack Query + Recharts
- **Metriche**: 52 file TypeScript, 31 pagine, 13 componenti riutilizzabili, 50+ API hooks, 30+ route
- **Pagine**: Auth (3), Onboarding (1), Dashboard (1), Fatture (4), Contabilita (4), Scadenzario (1), Fisco (7), Banca (4), Spese (1), Cespiti (1), CEO (2), Report (1), Impostazioni (1)
- **Build**: `npm run build` PASS (0 errori TS, 240KB gzipped)
- **UI**: testo italiano, formato numeri it-IT (€1.234,56), date DD/MM/YYYY
- **Directory**: `frontend/` (separata dal backend)

---

### PRD Frontend React creato
- **Data**: 2026-03-23
- **Fase**: 2 (Frontend)
- **Azione**: Creato PRD frontend con 10 epic, 47 pagine/feature, mapping completo ai 96 endpoint API
- **Stack**: React 19 + TypeScript + Tailwind 4 + shadcn/ui + Zustand + TanStack Query + Recharts
- **Navigazione**: 20+ route, sidebar collapsibile, responsive
- **MoSCoW**: Must Have (10 feature, 2 settimane), Should Have (+2 settimane), Could Have (+1 settimana)
- **Timeline**: ~4 settimane stimate, 6 milestone
- **File**: specs/frontend/02-prd-frontend.md

---

### Fase 8: VALIDAZIONE COMPLETATA — APPROVED FOR PRODUCTION
- **Data**: 2026-03-23
- **Fase**: 8 — Validazione
- **Risultato**: **APPROVED** — 369/369 test PASS, 72.84% coverage (>70% target), 0 bug
- **Metriche**: 40 stories, 182 AC, 224 SP, 96 endpoint, 32 modelli DB, 17.578 righe codice
- **Quality Score**: 73/100, Security Score: 78/100
- **E2E browser**: skipped (backend-only, frontend non ancora implementato)
- **Report**: specs/08-validation.md, specs/sprint-reviews/sprint-final-review.md

---

### Fase 7: IMPLEMENTAZIONE COMPLETATA — 40/40 stories, 369 test, 0 bugs
- **Data**: 2026-03-23
- **Fase**: 7 — Implementazione completa
- **Azione**: Implementati tutti i 10 sprint (224 SP, 40 stories):
  - **Sprint 4** (22 SP): Upload, SDI webhook, Email MCP, Scadenzario, Report — 39 test
  - **Sprint 5** (20 SP): OCR, Notifiche, Alert fiscali, Bilancio CEE — 47 test
  - **Sprint 6** (24 SP): Fatturazione attiva SDI, Open Banking, Liquidazione IVA — 32 test
  - **Sprint 7** (24 SP): Cash flow 90gg, Riconciliazione, Ritenute, Bollo — 37 test
  - **Sprint 8** (21 SP): Note spese, Approvazione, Cespiti, Ammortamento, Ratei — 44 test
  - **Sprint 9** (23 SP): CU annuale, Conservazione digitale, Pagamenti PISP, Monitor normativo — 32 test
  - **Sprint 10** (21 SP): F24 compilazione, Dashboard CEO, Budget vs consuntivo — 35 test
- **Totale finale**: 369 test PASS, 0 bug, tutte le versioni implementate (v0.1-v0.4)

---

### ADR-007 APPROVATA E IMPLEMENTATA — Drop Odoo, AccountingEngine interno
- **Data**: 2026-03-23
- **Fase**: 7 — Refactoring architetturale
- **Azione**: Eliminato Odoo CE 18 come dipendenza. Sostituito con AccountingEngine interno.
- **Motivazione**: Dopo 3 sprint, il 70% della contabilita era gia nel nostro codice. Odoo headless via XML-RPC aggiungeva complessita (doppio DB, latenza, multi-tenancy esplosiva) senza valore reale. Il mock OdooClient funzionava perfettamente — Odoo non era mai entrato nel flusso.
- **Dettaglio tecnico**:
  - Nuovo `AccountingEngine` in `api/modules/fiscal/` — piano dei conti salvato in tabella `chart_accounts`
  - 10 regole fiscali italiane in tabella `fiscal_rules` con validita temporale (`valid_from`/`valid_to`)
  - Mapping CEE integrato: ogni conto ha `cee_code` e `cee_name` per bilancio art. 2424-2425 c.c.
  - Endpoint `GET /fiscal/rules` per consultare regole fiscali
  - Riferimenti normativi: DPR 633/72, DPR 642/72, DPR 917/86, DPR 600/73, L. 197/2022
  - Conoscenza fiscale estratta da analisi codice OCA l10n-italy (clean room, non copia)
  - 11 nuovi test. Tutti 103 test PASS (92 precedenti intatti)
- **Architettura target**: 3 container (api + postgres + redis) — niente Odoo
- **ADR documento**: `specs/technical/ADR-007-drop-odoo.md`

---

### Fase 7: Sprint 3 COMPLETATO — Contabilita e Onboarding — v0.1 MVP COMPLETATO
- **Data**: 2026-03-22
- **Fase**: 7 — Implementazione
- **Azione**: Implementate tutte le 4 stories dello Sprint 3 (21 SP):
  - **US-11** (5 SP): Verifica e correzione categoria — 7 test, 5/5 AC PASS
  - **US-13** (8 SP): Registrazione automatica scritture partita doppia — 7 test, 6/6 AC PASS
  - **US-15** (3 SP): Dashboard scritture contabili — 6 test, 5/5 AC PASS
  - **US-16** (5 SP): Onboarding guidato — 5 test, 5/5 AC PASS
- **Dettaglio tecnico**:
  - ContaAgent: registrazione partita doppia con ACCOUNT_MAPPINGS, multi-aliquota IVA, reverse charge, idempotency check, balance validation
  - Journal entries dashboard con filtri periodo e quadratura dare/avere
  - Verifica/correzione categorie con feedback loop al LearningAgent
  - Onboarding wizard 4 step con resume, SPID fallback, tipo "Altro"
  - 3 nuovi models: JournalEntry, JournalLine, OnboardingState
  - 25 nuovi test, tutti PASS. Totale cumulativo: 92 test
- **MILESTONE: v0.1 MVP COMPLETATO** — 12/12 Must Have stories (69 SP)
  - Flusso end-to-end: Registrazione → SPID → Sync cassetto → Parse XML → Categorizza → Verifica → Registra partita doppia → Dashboard
- **Totale cumulativo**: 12/40 stories (30%), 69/224 SP, 92 test PASS

---

### Fase 7: Sprint 2 COMPLETATO — Pipeline Fatture
- **Data**: 2026-03-22
- **Fase**: 7 — Implementazione
- **Azione**: Implementate tutte le 4 stories dello Sprint 2 (24 SP):
  - **US-04** (8 SP): Sync fatture dal cassetto fiscale — 6 test, 5/5 AC PASS
  - **US-05** (3 SP): Parsing XML FatturaPA — 4 test, 4/4 AC PASS
  - **US-10** (8 SP): Categorizzazione automatica con learning — 5 test, 5/5 AC PASS
  - **US-14** (5 SP): Dashboard fatture e stato agenti — 6 test, 4/4 AC PASS
- **Dettaglio tecnico**:
  - 6 nuovi endpoint REST (sync, invoices CRUD, dashboard, agents status)
  - Invoice, AgentEvent, CategorizationFeedback models aggiunti al DB
  - FiscoAgent con retry backoff e dedup (numero+piva+data)
  - ParserAgent FatturaPA XML (xml.etree.ElementTree, namespace handling, TD01-TD04)
  - LearningAgent con rules engine + similarity matching + feedback loop
  - BaseAgent + EventBus in-memory pub/sub con dead letter queue
  - Dashboard con contatori per status, ultime 10 fatture, stato agenti
  - Lista fatture con filtri (data, tipo, source, status) e paginazione
  - 21 nuovi test, tutti PASS. Totale cumulativo: 67 test
- **Totale cumulativo**: 8/40 stories (20%), 48/224 SP, 67 test PASS

---

### Fase 7: Sprint 1 COMPLETATO — 4 stories, 46 test, 0 bugs
- **Data**: 2026-03-22
- **Fase**: 7 — Implementazione
- **Azione**: Implementate tutte le 4 stories dello Sprint 1 (24 SP):
  - **US-01** (5 SP): Registrazione e login utente — 17 test, 5/5 AC PASS
  - **US-02** (3 SP): Profilo utente e configurazione azienda — 12 test, 4/4 AC PASS
  - **US-03** (8 SP): Autenticazione SPID/CIE per cassetto fiscale — 9 test, 5/5 AC PASS
  - **US-12** (8 SP): Setup piano dei conti personalizzato — 8 test, 4/4 AC PASS
- **Dettaglio tecnico**:
  - 19 endpoint REST implementati (auth, profile, SPID, cassetto, accounting)
  - JWT auth middleware con brute force protection
  - Validatori P.IVA (Luhn) e codice ATECO
  - FiscoAPI adapter (SPID init/callback/delega)
  - Odoo adapter con templates piano conti (SRL, forfettario, generico)
  - Retry con backoff su Odoo connection failure (3 tentativi)
  - 46 test integration tutti PASS, 0 bug

---

### Fase 7: Implemented US-01 — Registrazione e login utente
- **Data**: 2026-03-22
- **Fase**: 7 — Implementazione
- **Azione**: Implemented US-01 (AC: 5/5 passed, 17 tests written, 0 bugs found)
- **Dettaglio**:
  - Creata struttura progetto (pyproject.toml, api/, tests/)
  - Implementati 6 endpoint auth: register, login, token refresh, verify-email, password-reset, password-reset/confirm
  - SQLAlchemy models: Tenant, User con campi per brute force protection e email verification
  - JWT con access token 24h e refresh token 7gg
  - Brute force protection: 5 tentativi → lockout 15 minuti
  - Password validation: min 8 char, 1 maiuscola, 1 numero
  - Anti-enumeration: email duplicata e password reset non rivelano esistenza account
  - 17 test integration tutti PASS
- **File creati**: api/ (7 file), tests/ (5 file), pyproject.toml, specs/07-implementation.md, specs/testing/test-map.md

---

### Fase 4: Tech Spec completa
- **Data**: 2026-03-22
- **Fase**: 4 — Technical Specification
- **Azione**: Tech spec aggiornata con tutte le sezioni richieste dal template:
  - **56 API endpoints** (da 20 a 56): +36 nuovi per expenses, assets, withholding, CU, stamp duties, accruals, preservation, F24, CEO dashboard, budget
  - **18 tabelle DB** (da 10 a 18): +8 nuove (stamp_duties, accruals_deferrals, f24_documents, digital_preservation, cu_certificates, expense_policies + campi aggiuntivi a tabelle esistenti). 22 indici.
  - **10 Business Rules** documentate (soglia cespiti, aliquote ammortamento, ritenuta, bollo, ratei, conservazione, F24 multi-sezione, KPI CEO, budget, auto-approvazione)
  - **File Structure** completa (backend FastAPI modules + agents + adapters + frontend React pages)
  - **Performance targets** (p95 API <200ms, OCR <3s, Dashboard CEO <1s, caching Redis)
  - **Test Strategy** con framework (pytest + Playwright), coverage targets (unit 80%, integration 60%)
  - **Story→Endpoint Mapping** completa per tutte le 40 stories
  - **Nuovi file creati**: specs/database/schema.md, specs/ux/wireframes.md (6 schermate ASCII), specs/testing/test-strategy.md

---
