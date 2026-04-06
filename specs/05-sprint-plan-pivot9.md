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
