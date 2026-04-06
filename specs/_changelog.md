# Changelog Specs: AgentFlow PMI

## Formato
- **Data**: ISO timestamp
- **Fase**: numero fase
- **Azione**: cosa è stato fatto
- **Contesto**: motivo/background

---

## 2026-04-06 — PIVOT 9: AgentFlow v3.0 — Da Controller a Sales AI Platform

- **Causa**: Documento v3.0 (AI_Dorsey/) ridefinisce AgentFlow come piattaforma AI per vendita + controller. Dual pipeline (T&M + Elevia), prodotto determina pipeline, Sales Agent unico.
- **Impatto**: 4 file da rifare (vision, PRD, stories pivot9, sprint plan), 4 da aggiornare (tech spec, schema DB, status, CLAUDE.md), 15+ invariati
- **Decisioni chiave**: Stack Python resta, un Sales Agent unico (non agenti separati per pipeline), pipeline snelle e non bloccanti, commerciale vende tutto
- **Nuove Epic**: Pipeline Templates (13), Resource DB (14), Elevia Engine (15), Agent Refactor (16), LinkedIn Selling (17), Cross-sell (18)
- **Stories stimate**: ~25 nuove (US-200→US-225)
- **Sprint stimati**: 34→41 (~8 settimane)
- **Azioni**: Scrivere vision → PRD → stories → tech spec → sprint plan → implementare

---

## 2026-04-06 — Agent Architecture v3.0 rev.2 (ADR-010)

- **Tipo**: B — Coordinator snello con Sales Agent unico product-aware
- **Agenti**: Sales Agent (26 tool, filtrati per prodotto), Controller (17 tool, esistenti), Analytics (6 tool)
- **Principio**: Il prodotto determina la pipeline. Un solo Sales Agent che si adatta al deal corrente.
- **Pipeline template**: T&M (6 stati), Corpo (7 stati), Elevia (8 stati), Custom (da DB)
- **Tool filtering**: il Sales Agent vede solo i tool del prodotto corrente (~8-12 su 26)
- **Estensibilita**: Nuovo prodotto = nuova pipeline nel DB, zero codice. Nuovo agente = 1 file + 1 riga registry.
- **File**: `specs/technical/agent-architecture.md`
- **Checklist**: 4 fasi (~8 settimane)

---

## 2026-04-06 — Sprint 33: Integrazione Calendario Commerciali (US-151→US-155)

- **5 user stories**: Vista calendario, .ics export, Microsoft 365 OAuth, Outlook push, Calendly
- **Backend**: `api/modules/calendar/` — microsoft_service.py (OAuth2 + Graph API push), router.py (6 endpoint)
- **Frontend**: `CrmCalendarPage.tsx` (FullCalendar daygrid+timegrid), .ics client-side, impostazioni calendario
- **DB**: 3 campi aggiunti — `User.microsoft_token`, `User.calendly_url`, `CrmActivity.outlook_event_id`
- **Test**: 20 test PASS (OAuth, status, disconnect, push, Calendly CRUD, API endpoints, data availability)
- **Sidebar**: voce "Calendario" aggiunta per owner/admin/commerciale
- **Impostazioni**: sezione "Calendario e Appuntamenti" con Microsoft 365 connect/disconnect + Calendly URL
- **Deal detail**: bottone "Prenota appuntamento" (Calendly) visibile se configurato
- **Principio**: AgentFlow = source of truth, Outlook = slave one-way push, no sync bidirezionale

---

## 2026-04-05 — Pivot 8: Implementazione Completata (Sprint 28-32)

- **Fase 7**: Implementazione 21 stories Social Selling (US-130→US-150) + 3 infra (US-109→111)
  - Sprint 28: Origini + Activity Types + Pre-funnel (8 stories, 35 test)
  - Sprint 29: RBAC Ruoli + Audit trail (2 stories, 13 test)
  - Sprint 30: Catalogo Prodotti + Deal-Product M2M (3 stories, 11 test)
  - Sprint 31: Dashboard KPI + Scorecard + Compensi (5 stories, 14 test)
  - Sprint 32: User Mgmt + Role-based UI + Company/Contact 1:N (3 stories + 4 infra, 14 test)
- **Totale**: 90 SP, 87 test PASS, 30+ endpoint, 10 nuovi modelli DB, 8 pagine frontend

### Company/Contact 1:N Split
- **CrmCompany** (NEW): separazione azienda da contatto/referente
- `CrmContact.company_id` FK: 1 azienda → N referenti
- `CrmDeal.company_id` FK: deal appartiene ad azienda
- Frontend form 2 step: seleziona/crea azienda → aggiungi referente

### Role-Based UI
- Sidebar/BottomNav filtrata per `user.role` (admin tutto, commerciale solo CRM)
- Dashboard admin: KPI finanziari vs Dashboard commerciale: KPI vendite
- Scorecard auto-load per commerciale, dropdown utenti per admin
- Widget auto-reset su cambio ruolo

### External Users
- `User.user_type` internal/external con `access_expires_at`
- Middleware auto-deactivazione utente scaduto
- CRM role assegnabile per utente

### Infrastruttura
- TipTap rich text editor per template email
- Service Worker network-first per HTML (fix stale chunk post-deploy)
- ErrorBoundary auto-reload su dynamic import failure
- Activity logging su cambio fase pipeline (dialog ibrido)
- Planned activities con stile amber e "Completa"
- Pre-funnel stages con auto-reorder sequence

---

## 2026-04-04 — Pivot 8: Social Selling Configurabile

- **Fase 5**: Sprint Planning — 6 sprint (100-105), 120 SP, 12 settimane stimate
  - Sprint 100: Fondamenta (Origini + Activity Types + Migration) — 21 SP
  - Sprint 101: RBAC Engine (Ruoli + Permessi + Utenti Esterni) — 21 SP
  - Sprint 102: Pre-funnel + Attività Custom + Audit Trail — 21 SP
  - Sprint 103: Catalogo Prodotti + Deal-Product M2M — 18 SP
  - Sprint 104: Dashboard KPI + Scorecard + Filtri — 18 SP
  - Sprint 105: Compensi (Regole + Calcolo + Export) — 21 SP
- **Review Phase 4**: 16 fix applicati (4 CRITICAL + 5 HIGH + 5 MEDIUM + 2 LOW), overall 8/10
- **Fase 1**: Vision aggiornata con Pivot 8
- **Fase 3**: User Stories generate — 21 stories (US-100 → US-120), 120 SP totali, 5 Epic
- **Azione**: Aggiunto modulo Social Selling con architettura Core Engine + Configuration Layer
- **5 moduli**: Origini configurabili, Attività e pre-funnel, Ruoli RBAC per esterni, Catalogo prodotti, Analytics e compensi
- **Fase 4**: Tech Spec generata — 32 endpoint, 11 nuove tabelle, 21 business rules, 10 wireframe
- **File stories**: `specs/03-user-stories-pivot8-social.md`
- **File tech spec**: `specs/04-tech-spec-pivot8.md`
- **File schema DB**: `specs/database/schema-pivot8.md`
- **File wireframe**: `specs/ux/wireframes-pivot8.md`
- **Brainstorming**: 85 idee (divergenza), analisi critica (sfida), 3 concept (sintesi)
- **Spec prodotto**: `Docs/Spec_Modulo_Social_Selling.md`
- **Contesto**: NExadata attiva vendita LinkedIn con fractional account. Il modulo è progettato generico per qualsiasi PMI.
- **Principio**: Tutto configurabile dall'admin, nessun riferimento hardcoded a clienti/prodotti specifici

---

## 2026-04-02 — Odoo Partnership Program — Opportunita Rivendita

- **Contatto Odoo:** Achraf Kanice, Partnership Program Manager (acka@odoo.com, +32 2 616 86 72)
- **Status:** Valutazione in corso per diventare Odoo Partner
- **Clienti interessati:** 4-5 clienti Nexa Data interessati ad AgentFlow PMI con Odoo CRM integrato
- **Test interno:** Nexa Data valuterà Odoo CRM internamente prima della commercializzazione
- **Potenziale revenue stream:** Bundle AgentFlow PMI + Odoo CRM per clienti IT consulting di Nexa Data
- **Impatto:** Nuovo mercato B2B2C, multi-tenant readiness, separazione chiara tra pre-vendita (Odoo) e gestione progetti/contabilità (AgentFlow)

---

## 2026-04-02 — PIVOT: Rimosso Write-Back Timesheet/Billing, Aggiunta Gestione Ordini Cliente
- **Causa**: Odoo CRM deve gestire SOLO il ciclo pre-vendita (pipeline → offerta → ordine → conferma). NON è responsabile della contabilità. Dopo conferma ordine, il commerciale crea la "commessa" nel sistema proprietario Nexa Data. Write-back ore/fatturato verso Odoo rimosso.
- **Impatto**: 5 file modificati, 11 endpoint CRM stabili, nuovi campi x_order_type/reference/date/notes, nuova pipeline
- **Decisione**: Odoo CRM rimane integrato (ADR-008), ma con ruolo definito in modo più ristretto
- **File modificati**: _status.md, 02-prd.md (EPIC 11), 04-tech-spec.md (API CRM), ADR-008-odoo-crm.md (_changelog.md)
- **Endpoint (11 totali):** GET /contacts, POST /contacts, GET /deals, POST /deals, PATCH /deals/{id}, GET /deals/{id}, GET /deals/won, POST /deals/{id}/order, GET /orders/pending, POST /deals/{id}/order/confirm, GET /pipeline/summary, GET /pipeline/stages
- **Campi custom Odoo aggiunti**: x_order_type (PO/email/firma_word/portale), x_order_reference, x_order_date, x_order_notes
- **Pipeline fasi**: Nuovo Lead → Qualificato → Proposta Inviata → Ordine Ricevuto → Confermato
- **Flusso ordinale**: POST /deals/{id}/order (registra) → GET /orders/pending (visualizza ordini in sospeso) → POST /deals/{id}/order/confirm (conferma e passa a Nexa Data)

---

## 2026-04-02 — Integrazione CRM Odoo 18 (ADR-008)
- **Causa**: Nexa Data ha 3 commerciali, 65 risorse, 100 progetti/anno. Serve CRM per pipeline, contatti, deal. Keap valutato e scartato (e-commerce oriented, score 2/12). Odoo 18 scelto (score 10/12, €93/mese).
- **Decisione**: Odoo 18 Online SOLO come CRM esterno. La contabilita resta sull'engine interno (ADR-007).
- **Impatto**: 7 file nuovi/modificati, 11 endpoint REST, 4 tool orchestrator, 1 nuovo agente "crm"
- **File nuovi**: `api/adapters/odoo_crm.py`, `api/modules/crm/` (router.py, service.py, schemas.py)
- **File modificati**: `api/config.py` (+5 settings), `api/main.py` (+router), `api/orchestrator/tool_registry.py` (+4 tool), `api/orchestrator/graph.py` (+keyword routing)
- **Specs aggiornate**: _status.md, 02-prd.md (EPIC 11), 04-tech-spec.md (ADR-008, stack, endpoint, integrazione)
- **ADR-008**: Odoo come CRM esterno (non contabile) — vedi specs/technical/ADR-008-odoo-crm.md

---

## 2026-04-01 — PIVOT 6: IVA, Scadenzari, Cash Flow, Anticipi Fatture
- **Causa**: Dashboard e Budget usano importo_totale (IVA inclusa) invece di netto. Mancano scadenzari attivi/passivi per cash flow. Anticipo fatture non gestito.
- **Impatto**: 17 nuove stories (US-70 a US-86), 72 SP, 6 sprint (17-22)
- **Stories**: Scorporo IVA (US-70/71), Scadenzario (US-72-76), Cash Flow (US-77/78), Anticipi (US-79-83), Modelli DB (US-84-86)
- **File**: specs/03-user-stories-pivot6.md (NUOVO)

---

### Feature: Self-Healing Import (Livello 1 + 2)
- **Data**: 2026-03-30
- **Causa**: I parser LLM falliscono sul 17% dei PDF (formati non previsti). Servono retry automatico e auto-tuning del prompt.
- **Impatto**: 2 nuove stories (US-73, US-74), 1 nuova tabella DB (import_prompt_templates)
- **Stories**: US-73 (Retry prompt adattato, 5 SP), US-74 (Meta-prompt per-tenant, 5 SP)
- **Approccio**: NON genera codice — migliora i prompt LLM. Il sistema impara dal formato di ogni commercialista.
- **Analisi**: brainstorm/08-self-healing-compare.md

---

### PIVOT 5: Da Gestionale Contabile a Controller Aziendale AI
- **Data**: 2026-03-28
- **Causa**: Cambio posizionamento fondamentale. AgentFlow non sostituisce il gestionale contabile — lo affianca come controller AI. Zero data entry, massima interpretazione. L'imprenditore vuole capire come va l'azienda, non fare il contabile.
- **Impatto**: 3 file da rifare (stories, sprint plan, wireframes), 6 da aggiornare (vision, PRD, tech spec, schema DB, test strategy, test map), 6 invariati
- **Nuove stories**: US-44 a US-71 (28 stories, ~148 SP, 6-7 sprint stimati)
- **Nuovi Epic**: EPIC 10 (Import Pipeline silenzioso + CRUD), EPIC 11 (Management Agents doppio canale), EPIC 12 (UX Controller)
- **Feature core aggiunte**: Budget Agent conversazionale, Controller Agent (budget vs consuntivo), import banca (PDF+LLM+CSV+API), corrispettivi XML, F24 import, saldi bilancio (Excel/PDF/XBRL), CRUD manuale per ogni voce, Completeness Score, doppio canale notifiche, home conversazionale, import silenzioso (max 3 azioni)
- **Nuove tabelle DB**: corrispettivi, budget_entries, budget_lines, recurring_contracts, loans, bank_statement_imports, completeness_scores
- **Nuovi endpoint API**: 62-76 (15 nuovi)
- **Principi di design**: (1) zero data entry, (2) import silenzioso, (3) eccezioni segnalate, (4) max 3 azioni, (5) CRUD come base import come acceleratore, (6) framing positivo onboarding, (7) doppio canale (dashboard + messaging)
- **File esempio disponibili**: esempi_import/ (banca UniCredit+Credit Agricole, bilancio TAAL 2023, 90 XML corrispettivi, 24 PDF paghe)
- **Analisi completa**: brainstorm/07-compare-llm.md + specs/technical/pivot-impact-analysis-v3.md
- **Ordine riesecuzione**: /dev-prd → /dev-stories → /dev-spec → /dev-sprint → /dev-review → /dev-implement

---

### PIVOT 4: Fatturazione Attiva Completa + Costi del Personale
- **Data**: 2026-03-27
- **Causa**: La fatturazione attiva (US-21) è incompleta (mancano XML completo, PDF cortesia, impostazioni ricorrenti, multi-linea). Serve importazione costi personale per EBITDA reale.
- **Impatto**: 12 file da aggiornare, 0 da rifare, modelli + servizi + frontend
- **Nuove stories**: US-41 (fattura completa XML+PDF), US-42 (impostazioni fatturazione), US-43 (costi personale)
- **Azioni**: Tenant model + XML generator + PDF + PayrollCost model + frontend
- **Ordine**: impostazioni → XML → multi-linea → PDF → frontend → personale → CEO

---

### Action Commands — Chatbot controlla la UI (Level 3 Agent)
- **Data**: 2026-03-26
- **Fase**: 7 — Implementazione
- **Azione**: Implementato pattern Action Commands — il chatbot può navigare pagine, cambiare anno e applicare filtri sull'app web
- **Backend**: `_build_actions()` in `api/orchestrator/graph.py` — analizza context (pagina+anno) e tool results per generare action commands
- **Frontend**: `useActionExecutor` hook con whitelist statica (navigate, set_year, set_filter), batch execution, priorità utente
- **Frontend**: `Toast.tsx` component per feedback visivo delle auto-actions
- **Frontend**: `ChatbotFloating.tsx` — suggestedActions come bottoni cliccabili nella risposta, auto-actions eseguite + toast
- **Modalità**: `auto` (esegue subito) per navigazione/anno espliciti, `suggest` (bottone) per >5 risultati
- **Sicurezza**: whitelist path, validazione anno 2020-2030, batch render, user priority
- **Contesto**: Brainstorming con Davide (architettura), Marta (UX), Nicola (sicurezza), Valentina (sintesi)

---

### Chatbot Floating Redesign — Stile ElevIA
- **Data**: 2026-03-26
- **Fase**: 7 — Implementazione
- **Azione**: Ridisegnato chatbot da pannello tradizionale a input bar sempre visibile in basso al centro (stile ElevIA)
- **Dettaglio**: framer-motion AnimatePresence, glassmorphism, Sparkles icon, suggestion pills contestuali, response panel animato
- **File**: `frontend/src/components/chat/ChatbotFloating.tsx`, `frontend/src/components/layout/AppLayout.tsx`
- **Dipendenza**: aggiunto framer-motion

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

### Epic B: Agentic Dashboard — PRD + Stories + Tech Spec
- **Data**: 2026-03-25
- **PRD**: Epic B (DB1-DB10) — dashboard JSON-driven, chatbot floating, drag & drop, modify_dashboard tool
- **Stories**: 5 nuove (US-B01 a US-B05, 24 SP)
- **Tech Spec**: Widget renderer, react-grid-layout, dashboard_layouts table, chatbot floating
- **File**: specs/03-user-stories-dashboard.md, specs/technical/04-tech-spec-dashboard.md

---

### Fase 5 (Agentic): Sprint Plan — 3 sprint, 57 SP, 10 stories
- **Data**: 2026-03-24
- **Sprint 11**: Orchestratore LangGraph + Tool Registry + Chat API + Persistenza (21 SP)
- **Sprint 12**: Frontend Chat UI + WebSocket + Agent Config + Onboarding chat (23 SP)
- **Sprint 13**: Multi-agent response + Memoria + Skill discovery + Polish (13 SP)
- **File**: specs/05-sprint-plan-agentic.md

---

### Fase 5 (Agentic): Tech Spec + Stories + PRD + Vision aggiornati
- **Data**: 2026-03-24
- **Fase**: 1-4 aggiornate per Pivot 3
- **Vision**: "Non e un software che usi: e un agente con cui parli" + sezione Sistema Agentico
- **PRD**: Epic A (AG1-AG10) + MoSCoW v0.5
- **Stories**: 10 nuove (US-A01 a US-A10, 57 SP, 44 AC)
- **Tech Spec**: LangGraph StateGraph, 25+ tools, 5 nuove tabelle DB, 10 nuovi endpoint, WebSocket streaming
- **File**: specs/technical/04-tech-spec-agentic.md, specs/03-user-stories-agentic.md

---

### PIVOT 3: Sistema Agentico Conversazionale — OpenClaw-like
- **Data**: 2026-03-24
- **Causa**: L'utente non deve usare un gestionale — deve parlare con un agente AI. Serve orchestratore centrale, chat persistente, agenti con nomi personalizzabili, tools/skills.
- **Impatto**: 3 file da rifare, 8 da aggiornare, 5 invariati
- **Nuove stories**: US-A01 a US-A10 (sistema agentico)
- **Tech**: LangGraph StateGraph + Claude API + WebSocket + PostgreSQL conversations
- **Strategia**: ADDITIVE — 9 agenti esistenti diventano tools, nessun codice riscritto
- **Stima**: ~17 giorni, Sprint 11-14
- **Report**: specs/technical/pivot-3-agentic-system.md
- **Ordine**: vision → PRD → stories → tech spec → sprint → review → implement

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
