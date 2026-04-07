# Sprint Plan — Pivot 9: AgentFlow v3.0

**Data:** 2026-04-06
**Stories:** 22 (US-200→US-221), 116 SP
**Sprint:** 34→41 (~8 settimane)
**Principio:** Agent Foundation prima, poi pipeline specifiche. Zero regressione sui 809+ test esistenti.

---

## Sprint 34: Agent Foundation (2 settimane)

**Goal:** Refactor orchestratore da tool-dispatch a agent-dispatch. Controller Agent funzionante. Tutti i test passano.

| Story | Titolo | SP | Prio |
|-------|--------|:--:|:----:|
| US-211 | Agent registry e dispatch | 8 | Must |
| US-213 | Controller Agent (wrapper 17 tool) | 5 | Must |

**SP totale:** 13

**Task breakdown:**

1. **Agent base class + registry** (`api/agents/`)
   - `base.py`: classe BaseAgent con name, description, tools, system_prompt
   - `registry.py`: dizionario agenti, metodo get_agent(name), list_agents()
   - Test: agent esiste nel registry, get_agent restituisce istanza corretta

2. **Refactor graph.py**
   - Router node: da "quale tool?" a "quale agente?"
   - Nuovo flusso: Router → Agent.execute(context) → Responder
   - Keyword map: fattura/IVA/bilancio → controller, deal/offerta/cliente → sales, cashflow/trend → analytics

3. **Controller Agent**
   - `api/agents/controller_agent.py`: wrappa i 17 tool esistenti
   - System prompt: identico al RESPONSE_SYSTEM_PROMPT attuale per contabilita
   - Test: tutti i test chat/orchestrator esistenti passano senza modifiche

4. **Analytics Agent** (shell)
   - `api/agents/analytics_agent.py`: predict_cashflow + pipeline_analytics + crm_stats
   - Migra 3 tool da tool_registry.py

5. **Sales Agent** (shell con 8 tool core)
   - `api/agents/sales_agent.py`: ask_missing_info, suggest_next_action, generate_email_draft, move_deal_stage, log_activity, get_deal_summary, classify_loss, detect_cross_sell
   - Per ora wrappa i tool CRM esistenti (crm_pipeline_summary, crm_list_deals, etc.)

6. **Gate di uscita sprint:**
   - `python3 -m pytest tests/` → tutti i 809+ test PASS
   - Ruff 0 errori
   - TypeScript 0 errori

---

## Sprint 35: Pipeline Templates + Seed (1 settimana)

**Goal:** Pipeline template nel DB. Prodotto determina pipeline. 3 template seed.

| Story | Titolo | SP | Prio |
|-------|--------|:--:|:----:|
| US-200 | Pipeline template da DB | 5 | Must |
| US-201 | Prodotto determina pipeline | 5 | Must |

**SP totale:** 10

**Task breakdown:**

1. **Modelli DB**
   - `PipelineTemplate`: id, tenant_id, code, name, pipeline_type, description, is_active
   - `PipelineTemplateStage`: id, template_id, code, name, sequence, required_fields (JSON), sla_days, is_won, is_lost, is_optional
   - Migration: ALTER TABLE crm_products ADD pipeline_template_id UUID
   - Migration: ALTER TABLE crm_deals ADD pipeline_template_id UUID

2. **Seed 3 template** (nel lifespan o service)
   - T&M: Lead(1) → Qualifica(2) → Match risorse(3) → Offerta(4) → Negoziazione(5) → Won(6)/Lost
   - Corpo: Lead(1) → Analisi req(2) → Specifiche(3) → Demo(4,optional) → Offerta(5) → Negoziazione(6) → Won(7)/Lost
   - Elevia: Prospect(1) → Connessione(2) → Engagement(3) → Discovery(4) → Demo(5,optional) → Offerta(6) → Won(7)/Lost → Onboarding(8)

3. **Endpoint API**
   - GET /pipeline-templates (list per tenant)
   - GET /pipeline-templates/{id} (con stages)
   - POST /pipeline-templates (admin)
   - PATCH /pipeline-templates/{id} (admin)

4. **Prodotto → Pipeline**
   - Modifica create_deal: se prodotto ha pipeline_template_id, il deal lo eredita
   - Lo stage_id iniziale e il primo stage del template
   - Frontend CrmNewDealPage: quando selezioni prodotto, mostra la pipeline che si attivera

5. **Test:** 10+ test (seed, CRUD, prodotto→pipeline, deal creation)

---

## Sprint 36: Kanban Multi-Pipeline + Resource DB (2 settimane)

**Goal:** Vista Kanban con tab per pipeline. CRUD risorse interne con skill.

| Story | Titolo | SP | Prio |
|-------|--------|:--:|:----:|
| US-203 | Kanban multi-pipeline | 5 | Must |
| US-204 | CRUD risorse interne | 5 | Must |

**SP totale:** 10

**Task breakdown:**

1. **Kanban multi-pipeline** (frontend)
   - Tab: "Tutti", "T&M", "Corpo", "Elevia" (dinamico da pipeline_templates)
   - Ogni tab mostra colonne della pipeline corrispondente
   - Badge colorato per pipeline nella vista "Tutti"
   - Conteggio deal + valore per tab
   - Hook: `usePipelineTemplates()` per caricare i template

2. **Resource DB** (backend)
   - Modelli: `Resource` (nome, seniority, costo_giornaliero, tariffa_suggerita, disponibile_dal, attivo)
   - Modelli: `ResourceSkill` (resource_id, skill_name, skill_level 1-5, certificazioni)
   - Service: CRUD risorse + CRUD skill
   - Endpoint: GET/POST/PATCH /resources, GET/POST/DELETE /resources/{id}/skills

3. **Resource page** (frontend)
   - Pagina `/risorse`: lista risorse con filtri (skill, seniority, disponibilita)
   - Dettaglio risorsa: profilo + skill con barre livello
   - Form creazione/modifica risorsa + gestione skill
   - Sidebar: voce "Risorse" nella sezione Commerciale (ruoli admin, commerciale)

4. **Test:** 10+ test (CRUD risorse, skill, Kanban API)

---

## Sprint 37: Matching + Margine + Tool Corpo + Sales Agent filtering (2 settimane)

**Goal:** Il Sales Agent sa fare matching risorse, calcolare margini per T&M, e generare offerte a corpo. Tool filtering per prodotto funzionante.

| Story | Titolo | SP | Prio |
|-------|--------|:--:|:----:|
| US-205 | Matching richiesta-risorse | 8 | Must |
| US-206 | Calcolo margine offerta | 5 | Must |
| US-212 | Sales Agent tool filtering | 8 | Must |
| US-219 | Specifiche + effort + offerta Corpo | 8 | Must |

**SP totale:** 29

**Task breakdown:**

1. **Tool match_resources**
   - Input: tech_stack[], seniority, min_disponibilita, durata_mesi
   - Algoritmo: filtra disponibilita → match skill → score (tech 60% + seniority 25% + disponibilita 15%)
   - Output: top 5 profili con match_score, nome, skill, disponibilita, costo

2. **Tool calc_margin**
   - Input: tariffa_proposta, resource_id (o costo diretto)
   - Output: margine_euro, margine_pct, alert se < 15%

3. **Tool generate_tm_offer**
   - Genera bozza offerta: tariffe per seniority/tech, durata, condizioni
   - Include placeholder per CV anonimi

4. **Tool check_bench**
   - Lista risorse che si liberano entro 30gg
   - Incrocia con deal in pipeline che cercano skill simili

5. **Tool filtering nel Sales Agent**
   - Quando deal.pipeline_template.code == "tm_consulting": aggiungere tool T&M
   - Quando deal.pipeline_template.code == "elevia_product": aggiungere tool Elevia
   - Il prompt contiene SOLO i tool disponibili per quel prodotto

6. **Context injection**
   - Quando l'orchestratore attiva il Sales Agent, inietta: deal, prodotto, pipeline stages, stato corrente, missing fields

7. **Tool Corpo: prefill_specs**
   - Input: note call (testo libero)
   - Output: scheda specifiche pre-compilata (scope, deliverable, tech, team, vincoli, milestone)
   - L'agente evidenzia info mancanti

8. **Tool Corpo: estimate_effort**
   - Input: scope + deliverable + tech
   - Output: giornate per profilo (senior/mid/junior), durata mesi, costo interno

9. **Tool Corpo: generate_fixed_offer**
   - Input: specifiche + effort + margine target
   - Output: bozza offerta a corpo con milestone, prezzo, condizioni pagamento (30/30/30/10)

10. **Test:** 20+ test (matching, margine, filtering, context, specifiche, effort, offerta corpo)

---

## Sprint 38: Elevia Engine + Discovery + Onboarding (2 settimane)

**Goal:** Use case catalog, ATECO scoring, score prospect, discovery brief, demo config, onboarding plan, adoption monitoring.

| Story | Titolo | SP | Prio |
|-------|--------|:--:|:----:|
| US-208 | Catalogo use case Elevia | 5 | Must |
| US-209 | Score prospect Elevia | 5 | Must |
| US-220 | Discovery brief + demo Elevia | 5 | Must |
| US-221 | Onboarding + adozione Elevia | 5 | Must |

**SP totale:** 20

**Task breakdown:**

1. **Modelli DB**
   - `EleviaUseCase`: id, tenant_id, code, name, description, is_active
   - `AtecoUseCaseMatrix`: id, use_case_id, ateco_code, fit_score (0-100)
   - `UseCaseBundle`: id, tenant_id, name, ateco_codes[], use_case_ids[]

2. **Seed dati**
   - 15 use case (UC01→UC15) da AI_Dorsey docs
   - Matrice ATECO: Metallurgia (24,25), Commercio (46), Chimica (20) con fit score
   - 3 bundle: Metallurgia Standard, Commercio Standard, Chimica Standard

3. **Tool score_prospect**
   - Input: ateco_code, employee_count, has_decision_maker, engagement_level
   - Calcolo: ATECO (30%) + dimensione (15%) + use case count (25%) + engagement (20%) + decision maker (10%)
   - Output: score, use case applicabili, bundle suggerito

4. **Tool suggest_use_case_bundle**
   - Input: ateco_code
   - Output: bundle name, use case list con fit score, descrizione per settore

5. **Endpoint API**
   - GET/POST/PATCH /elevia/use-cases
   - GET /elevia/ateco-matrix
   - POST /elevia/score-prospect
   - GET /elevia/bundles

6. **UI pagina Use Case**
   - Lista use case con fit per settore (tabella/card)
   - Matrice ATECO visualizzata come heatmap o tabella

7. **Tool prefill_discovery_brief** (US-220)
   - Input: prospect ATECO, dimensione, ruolo decisore
   - Output: pain point probabili per settore, use case candidati con fit score, domande discovery personalizzate
   - Testo generato dall'LLM con contesto settoriale

8. **Tool prepare_demo** (US-220)
   - Input: use case identificati dalla discovery
   - Output: scaletta demo (UC per ordine, tempo suggerito), dati esempio per settore, materiale presentazione
   - Se nessuna discovery fatta: suggerisce demo standard per settore

9. **Tool plan_onboarding** (US-221)
   - Input: deal won con bundle use case
   - Output: timeline (settimana 1: config, settimana 2-3: training per UC, settimana 4: go-live), KPI adozione target
   - Personalizzato per numero di use case acquistati

10. **Tool monitor_adoption** (US-221)
    - Input: deal_id in stato Onboarding
    - Output: metriche adozione (login frequency, feature usage per UC, trend vs target)
    - Alert se adoption < threshold dopo 30gg
    - Suggerisce re-training se UC specifico sotto-utilizzato

11. **Test:** 15+ test (seed, scoring, bundles, brief, demo, onboarding, adoption)

---

## Sprint 39: LinkedIn Social Selling (2 settimane)

**Goal:** Messaggi LinkedIn personalizzati, warmth score, cadence tracking.

| Story | Titolo | SP | Prio |
|-------|--------|:--:|:----:|
| US-214 | Messaggi LinkedIn | 5 | Must |
| US-215 | Warmth score + cadence | 5 | Must |

**SP totale:** 10

**Task breakdown:**

1. **Tool generate_linkedin_message**
   - Input: prospect (ATECO, nome, azienda, ruolo), message_type (connection_request, conversation_starter, value_share, soft_ask, breakup), trigger_detail
   - Output: messaggio personalizzato per settore + fase
   - Regole: connection_request < 200 char, DM < 300 char, mai pitch al primo contatto

2. **Tool suggest_content**
   - Input: ateco_code, engagement_phase
   - Output: tipo contenuto (case study, whitepaper, post), titolo suggerito, motivo

3. **Tool calc_warmth_score**
   - Input: contact_id (legge attivita dal DB)
   - Calcolo: connessione accettata +20, risposta DM +30, like +15, commento +25, profile view +10
   - Output: score 0-100, threshold labels (cold <30, warm 30-60, hot >60)

4. **Tool check_linkedin_cadence**
   - Input: contact_id
   - Calcolo: guarda attivita per tipo e data, mappa sulla cadence 21gg
   - Output: giorno corrente nella cadence, prossima azione suggerita, giorni dall'ultimo contatto

5. **Cadence come serie di attivita**
   - Nessun modello nuovo — la cadence e una sequenza di CrmActivity con tipo "linkedin_*"
   - L'agente traccia: linkedin_view, linkedin_follow, linkedin_like, linkedin_comment, linkedin_connection, linkedin_dm, linkedin_content_share, linkedin_voice_note, linkedin_call_ask

6. **Test:** 10+ test (messaggi, warmth, cadence)

---

## Sprint 40: Cross-sell + Should Have (2 settimane)

**Goal:** Cross-sell engine. Pipeline admin. Bench tracking. ROI calculator.

| Story | Titolo | SP | Prio |
|-------|--------|:--:|:----:|
| US-217 | Segnali cross-sell | 5 | Must |
| US-202 | Admin personalizza template | 5 | Should |
| US-207 | Bench tracking | 3 | Should |
| US-210 | ROI calculator | 3 | Should |

**SP totale:** 16

**Task breakdown:**

1. **Cross-sell signal detection**
   - Modello: `CrossSellSignal` (tenant_id, deal_source_id, signal_type, keyword_matched, suggested_product, priority, status, created_at)
   - Tool detect_cross_sell: analizza ultime N attivita/note del deal per keyword
   - Keyword default: documentazione/processi/knowledge → Elevia; sviluppo/integrazione/custom → T&M
   - Crea segnale + notifica commerciale

2. **Admin pipeline editor**
   - Pagina `/impostazioni/pipeline-templates`: lista template, click per modificare
   - Modifica stati: nome, sequence, required_fields, SLA, is_optional
   - Aggiungi/rimuovi stati
   - Crea template custom

3. **Bench tracking**
   - Tool check_bench: query risorse con disponibile_dal <= today + 30
   - Alert proattivo nell'agente
   - Incrocio con deal in pipeline che matchano

4. **ROI calculator**
   - Tool calc_roi: ore_risparmiate × costo_orario × 12 - costo_elevia
   - Parametri configurabili per settore

5. **Test:** 10+ test

---

## Sprint 41: Import CSV + Report + Polish (1 settimana)

**Goal:** Import LinkedIn, report cross-sell, polish e stabilizzazione.

| Story | Titolo | SP | Prio |
|-------|--------|:--:|:----:|
| US-216 | Import CSV LinkedIn | 5 | Should |
| US-218 | Report cross-sell | 3 | Should |

**SP totale:** 8

**Task breakdown:**

1. **Import CSV LinkedIn**
   - Endpoint POST /elevia/import-csv (multipart upload)
   - Parser: nome, cognome, azienda, ruolo, settore → CrmCompany + CrmContact + CrmDeal (Elevia, stato Prospect)
   - Dedup su nome+azienda
   - Report: importati, duplicati, errori

2. **Report cross-sell**
   - Endpoint GET /cross-sell/report?period=month
   - Dati: segnali totali, convertiti, valore, breakdown per direzione
   - Frontend: card con KPI + tabella segnali

3. **Polish e stabilizzazione**
   - Fix bug emersi durante sprint 34-40
   - Test E2E dei flussi principali
   - Aggiornamento specs/07-implementation.md
   - Aggiornamento test-map.md

4. **Test:** 5+ test

---

## Riepilogo Sprint

| Sprint | Settimane | Stories | SP | Focus |
|--------|:---------:|:-------:|:--:|-------|
| 34 | 2 | US-211, US-213 | 13 | Agent Foundation |
| 35 | 1 | US-200, US-201 | 10 | Pipeline Templates |
| 36 | 2 | US-203, US-204 | 10 | Kanban + Resource DB |
| 37 | 2 | US-205, US-206, US-212, US-219 | 29 | Matching + Margine + Corpo + Tool Filtering |
| 38 | 2 | US-208, US-209, US-220, US-221 | 20 | Elevia Engine + Discovery + Onboarding |
| 39 | 2 | US-214, US-215 | 10 | LinkedIn Selling |
| 40 | 2 | US-217, US-202, US-207, US-210 | 16 | Cross-sell + Should Have |
| 41 | 1 | US-216, US-218 | 8 | Import + Report + Polish |
| **TOTALE** | **~14** | **22** | **116** | |

### Verifica copertura tool

Tutti i 26 tool del Sales Agent sono ora coperti da stories:

| Tool | Story | Sprint |
|------|:-----:|:------:|
| ask_missing_info, suggest_next_action, generate_email_draft, move_deal_stage, log_activity, get_deal_summary, classify_loss | US-212 | 37 |
| detect_cross_sell | US-217 | 40 |
| match_resources | US-205 | 37 |
| calc_margin, generate_tm_offer | US-206 | 37 |
| check_bench | US-207 | 40 |
| prefill_specs, estimate_effort, generate_fixed_offer | US-219 | 37 |
| score_prospect, suggest_bundle | US-209 | 38 |
| prefill_discovery_brief, prepare_demo | US-220 | 38 |
| plan_onboarding, monitor_adoption | US-221 | 38 |
| calc_roi | US-210 | 40 |
| generate_linkedin_message, suggest_content | US-214 | 39 |
| calc_warmth_score, check_linkedin_cadence | US-215 | 39 |

---

## Gate di qualita per ogni sprint

1. `python3 -m pytest tests/` → tutti i test PASS (esistenti + nuovi)
2. `ruff check api/` → 0 errori
3. `npx tsc --noEmit` → 0 errori TypeScript
4. `npx vite build` → build OK
5. Nuove stories: almeno 1 test per AC

---

## Rischi e mitigazioni

| Rischio | Probabilita | Mitigazione |
|---------|:-----------:|-------------|
| Refactor orchestratore rompe test esistenti | Media | Sprint 34 dedicato a questo, gate "tutti i test passano" |
| Matching risorse troppo complesso | Bassa | Algoritmo semplice (filter + score), no ML |
| LinkedIn ToS (automazione) | Media | L'agente COMPONE messaggi, non li invia. L'utente fa copia-incolla |
| Prompt troppo grande con 26 tool | Media | Tool filtering: l'agente vede solo 8-12 tool per volta |
| Scope creep su pipeline editor | Alta | US-202 e Should Have, si fa solo se c'e tempo |

---

# Sprint Plan — Pivot 10: Portal Integration (ADR-011)

**Data:** 2026-04-07
**Stories:** 12 (US-230 -> US-241), 52 SP
**Sprint:** 42 -> 45 (~8 settimane)
**Principio:** Portal master anagrafico (Customer), AgentFlow master commerciale (Deal/Contact). Conferma umana per ogni scrittura su Portal. Zero regressione sui 1029+ test esistenti.

**Connessione:** JWT auto-generato con JWTSECRET condiviso, nessun login/password.
**Staging API:** `https://portaaljsbe-staging.up.railway.app/api/v1`
**DB staging:** 2149 persone, 315 commesse, 66 clienti, 365 attivita, 1543 timesheet

---

## Sprint 42: Portal Client + Read (2 settimane)

**Goal:** Adapter Portal funzionante. Lettura Customer/Person/Project. Proxy endpoint. CrmCompany sostituito da Portal Customer per nuovi deal.

| Story | Titolo | SP | Prio |
|-------|--------|:--:|:----:|
| US-230 | Portal Client adapter (JWT + read) | 5 | Must |
| US-231 | Aziende da Portal (sostituisce CrmCompany) | 5 | Must |
| US-232 | Read persons + employment contracts | 3 | Must |
| US-233 | Proxy endpoints /portal/* | 3 | Must |

**SP totale:** 16

**Task breakdown:**

1. **Portal Client adapter** (`api/adapters/portal_client.py`)
   - Classe `PortalClient` async con httpx
   - JWT auto-generation: HS256, payload {tenant, exp}, PORTAL_JWT_SECRET
   - Metodi: `get_customers()`, `get_persons()`, `get_projects()`, `get_timesheets()`
   - Graceful degradation: se Portal offline, ritorna empty con warning
   - Test: JWT generation, customer list, error handling, disabled mode

2. **Aziende da Portal**
   - Migration: ALTER TABLE crm_deals ADD portal_customer_id INTEGER
   - Migration: ALTER TABLE crm_contacts ADD portal_customer_id INTEGER
   - Service: `get_portal_customers()` con cache in-memory (TTL 5 min)
   - Frontend: dropdown "Azienda" nel NewDeal legge da `/portal/customers` invece di `/crm/companies`
   - Retrocompatibilita: deal esistenti mantengono company_id FK
   - Test: dropdown, portal_customer_id su deal/contact, fallback

3. **Read persons + contracts**
   - `PortalClient.get_persons()` con paginazione e filtro
   - `PortalClient.get_employment_contracts()` per contratti attivi
   - Badge "In scadenza" per contratti < 30gg
   - Test: person list, contract filter, pagination

4. **Proxy endpoints** (`api/modules/portal/router.py`)
   - GET /portal/customers, /portal/customers/{id}
   - GET /portal/persons, /portal/persons/{id}
   - GET /portal/projects, /portal/projects/{id}
   - GET /portal/timesheets
   - Middleware: solo ruoli admin/commerciale
   - Cache: in-memory TTL 5 min per letture
   - Test: proxy endpoints, auth, cache

5. **Gate di uscita sprint:**
   - `python3 -m pytest tests/` -> tutti i test PASS
   - Ruff 0 errori
   - TypeScript 0 errori
   - Portal Client testato con staging API

---

## Sprint 43: Create Commessa (2 settimane)

**Goal:** Deal Won crea commessa su Portal. Customer matching automatico. Bottone "Crea Commessa" nel deal detail.

| Story | Titolo | SP | Prio |
|-------|--------|:--:|:----:|
| US-234 | Create Project from Deal Won | 5 | Must |
| US-235 | Customer matching by P.IVA | 5 | Must |
| US-236 | Deal detail "Crea Commessa su Portal" | 4 | Must |

**SP totale:** 14

**Task breakdown:**

1. **Create Project from Deal Won**
   - `PortalClient.create_project()` — POST /projects su Portal
   - Service: `create_portal_project_from_deal(deal_id)` — mappa campi deal -> project
   - Dialog conferma su cambio stage Won: "Vuoi creare la commessa su Portal?"
   - Migration: ALTER TABLE crm_deals ADD portal_project_id INTEGER
   - Aggiornamento deal con portal_project_id dopo creazione
   - Test: project creation, confirmation flow, error handling, retry

2. **Customer matching by P.IVA**
   - Service: `match_portal_customer(piva)` — cerca Customer Portal per vatNumber
   - Gestione: match singolo (auto), match multiplo (scelta utente), nessun match (propone creazione)
   - Batch matching: endpoint per matchare tutti i deal legacy senza portal_customer_id
   - Test: match singolo, multiplo, nessuno, batch

3. **Deal detail "Crea Commessa"**
   - Frontend: bottone condizionale (visibile se Won e senza portal_project_id)
   - Dialog con form precompilato (nome, cliente, valore, date)
   - Link "Vedi Commessa su Portal" se portal_project_id presente
   - Permessi: portal:write per commerciale
   - Test: bottone visibilita, dialog, permessi

4. **Gate di uscita sprint:**
   - `python3 -m pytest tests/` -> tutti i test PASS
   - Creazione commessa testata su staging Portal

---

## Sprint 44: Assign Collaborators (2 settimane)

**Goal:** Assegnazione collaboratori a commessa Portal da AgentFlow. Sezione "Risorse assegnate" nel deal detail.

| Story | Titolo | SP | Prio |
|-------|--------|:--:|:----:|
| US-237 | Create Activity/Assignment on Portal | 5 | Must |
| US-238 | Deal detail "Risorse assegnate da Portal" | 6 | Must |

**SP totale:** 11

**Task breakdown:**

1. **Create Activity/Assignment**
   - `PortalClient.create_activity()` — POST /activities su Portal
   - Dialog: dropdown persone Portal (filtrate per competenza), ruolo, ore/settimana, periodo
   - Conferma umana obbligatoria prima della scrittura
   - Validazione: persona non gia assegnata, commessa esistente
   - Test: assignment creation, duplicate check, validation, error handling

2. **Sezione "Risorse assegnate"**
   - Frontend: sezione nel deal detail (sotto info commessa)
   - Lettura da Portal: `GET /activities?project_id={portal_project_id}`
   - Mostra: nome, ruolo, ore/settimana, periodo, stato
   - Placeholder se nessuna commessa/nessuna risorsa
   - Aggiornamento al reload (no cache per risorse — dati freschi)
   - Test: sezione rendering, empty state, refresh

3. **Gate di uscita sprint:**
   - `python3 -m pytest tests/` -> tutti i test PASS
   - Assegnazione testata su staging Portal

---

## Sprint 45: Sync Timesheets + Dashboard (2 settimane)

**Goal:** Sync periodico timesheet da Portal. Margine reale calcolato. Sezione "Avanzamento Operativo" nel deal detail. Pagina admin PortalConfig.

| Story | Titolo | SP | Prio |
|-------|--------|:--:|:----:|
| US-239 | Timesheet sync job + margine reale | 5 | Must |
| US-240 | Deal detail "Avanzamento Operativo" | 3 | Must |
| US-241 | PortalConfig admin page | 3 | Should |

**SP totale:** 11

**Task breakdown:**

1. **Timesheet sync job**
   - Celery task: `sync_portal_timesheets` — eseguito ogni 6 ore (configurabile)
   - Delta sync: solo timesheet con updated_at > ultimo sync
   - Storage locale: tabella `portal_timesheet_cache` (project_id, person_id, date, hours, cost, synced_at)
   - Calcolo margine reale: valore_deal - somma(ore x costo_orario)
   - Alert margine < 15%: notifica in-app + log
   - Test: sync job, delta logic, margin calculation, alert threshold

2. **Sezione "Avanzamento Operativo"**
   - Frontend: sezione nel deal detail (sotto risorse assegnate)
   - Barra progresso ore fatte / ore pianificate con %
   - Costo effettivo vs budget (badge verde/giallo/rosso)
   - Margine reale EUR e % con trend proiezione
   - Warning se margine < 15% o ore > 100%
   - Placeholder se nessun dato
   - Test: rendering, colors, edge cases

3. **PortalConfig admin page**
   - Frontend: `/impostazioni/portal` — form URL, JWT Secret (masked), Tenant Code
   - Backend: modello `PortalConfig` (tenant_id, api_url, jwt_secret_encrypted, portal_tenant)
   - Bottone "Test Connessione" — chiama Portal e mostra risultato
   - Statistiche: N clienti, N persone, N commesse, ultimo/prossimo sync
   - Mapping tenant: AgentFlow tenant -> Portal tenant
   - Solo admin (middleware + sidebar filter)
   - Test: config CRUD, test connection, permissions

4. **Gate di uscita sprint:**
   - `python3 -m pytest tests/` -> tutti i test PASS
   - Sync testato con staging Portal (1543 timesheet)

---

## Riepilogo Sprint Pivot 10

| Sprint | Settimane | Stories | SP | Focus |
|--------|:---------:|:-------:|:--:|-------|
| 42 | 2 | US-230, US-231, US-232, US-233 | 16 | Portal Client + Read |
| 43 | 2 | US-234, US-235, US-236 | 14 | Create Commessa |
| 44 | 2 | US-237, US-238 | 11 | Assign Collaborators |
| 45 | 2 | US-239, US-240, US-241 | 11 | Sync Timesheets + Dashboard |
| **TOTALE** | **~8** | **12** | **52** | |

---

## Rischi e mitigazioni Pivot 10

| Rischio | Probabilita | Mitigazione |
|---------|:-----------:|-------------|
| Portal API non stabile | Media | Staging copiato e testato, graceful degradation |
| Latenza chiamate Portal | Bassa | Cache in-memory TTL 5min per letture, delta sync per timesheet |
| JWT Secret rotation | Bassa | PortalConfig admin page per aggiornare senza redeploy |
| CrmCompany deprecation rompe frontend | Media | Retrocompatibilita: deal legacy mantengono company_id, nuovi usano portal_customer_id |
| Portal offline durante demo | Media | Fallback campo testo libero per azienda, placeholder sezioni Portal |
