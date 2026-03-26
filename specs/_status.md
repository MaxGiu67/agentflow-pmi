# Status Progetto: AgentFlow PMI
Ultimo aggiornamento: 2026-03-22

## Progetto
- **Nome**: AgentFlow PMI
- **MVP**: ContaBot — "L'agente contabile che impara da te"
- **Visione finale**: AgentFlow Pro — Copilota AI del CEO di PMI italiana
- **Metodologia**: SDD (Spec-Driven Development)
- **Pivot 1**: Cassetto fiscale come fonte primaria (non email)
- **Pivot 2**: Integrazione analisi gap CEO (gap contabili, adempimenti, cruscotto CEO, roadmap v1.0-v2.0)
- **Pivot 3**: Sistema Agentico Conversazionale — orchestratore OpenClaw-like, chat persistente, agent naming, tools/skills

## Fasi Dev-Methodology
| Fase | File | Status | Progresso |
|------|------|--------|-----------|
| 1 - Vision | specs/01-vision.md | ✅ Aggiornato post analisi gap CEO | 95% |
| 2 - PRD | specs/02-prd.md | ✅ Aggiornato post analisi gap CEO | 95% |
| 3 - User Stories | specs/03-user-stories.md | ✅ Aggiornato post analisi gap CEO | 95% |
| 4 - Tech Spec | specs/04-tech-spec.md | ✅ Review PASS (post-fix) — 61 endpoints, 18 tabelle, 10 BR | 100% |
| 5 - Sprint Planning | specs/05-sprint-plan.md | ✅ 10 sprint, 224 SP, velocity 20-24 SP/sprint | 100% |
| 6 - Setup | — | ✅ Struttura progetto creata | 100% |
| 7 - Implementazione | specs/07-implementation.md | ✅ COMPLETATA — 40/40 stories, 10/10 sprint | 100% (40/40 stories, 224 SP) |
| 8 - Validazione | specs/08-validation.md | ✅ APPROVED — 369 test PASS, 72.84% coverage, 0 bug | 100% |

## Pivot 1: Cassetto Fiscale come Fonte Primaria
Gerarchia fonti dati:
1. **Cassetto Fiscale (FiscoAPI + SPID/CIE)** — v0.1 Must, 95%+ fatture XML strutturate
2. **A-Cube SDI webhook** — v0.2 Should, ricezione real-time
3. **Email (Gmail/PEC) via MCP server** — v0.2 Should, canale secondario
4. **Upload manuale** — v0.2 Should, fallback

## Pivot 2: Analisi Gap CEO
Aree aggiunte alla roadmap:
- **v0.3**: Note spese, cespiti, ritenute d'acconto, imposta bollo, ratei/risconti
- **v0.4**: F24, CU annuale, conservazione digitale, Dashboard CEO base
- **v1.0**: ControllerAgent, HRAgent, CommAgent, multi-tenant
- **v1.5**: ProjectAgent, DocAgent, FornitureAgent
- **v2.0**: ComplianceAgent, marketplace, API pubblica

## Stato Stories
- **Totale**: 40 stories, 224 SP
- **v0.1 Must**: 12 stories, 69 SP (invariato)
- **v0.2 Should**: 7 stories, 32 SP (invariato)
- **v0.3 Could**: 14 stories, 79 SP (+7 stories gap contabili)
- **v0.4 Could**: 7 stories, 44 SP (+5 stories: F24, CU, conservazione, dashboard CEO)

## Documenti Tecnici
- `specs/technical/flusso-informazioni.md` — Flusso completo (fatturazione + banca + adempimenti)
- `specs/technical/analisi-gap-ceo.md` — Analisi gap CEO: cosa manca al titolare di PMI
- `specs/technical/pivot-impact-analysis.md` — Impatto pivot 1 (cassetto fiscale)
- `specs/technical/pivot-impact-analysis-v2.md` — Impatto pivot 2 (analisi gap CEO)
- `specs/technical/review-report-v2.md` — Review avversaria (PASS 95%)
- `specs/technical/review-report-v3.md` — Review avversaria v3 (PASS)
- `specs/technical/review-report-v4.md` — Review avversaria Fase 4 (PASS post-fix)
- `specs/technical/review-report-v5.md` — Review avversaria Fase 5 (PASS)
- `specs/database/schema.md` — Schema DB completo (18 tabelle, 22 indici)
- `specs/ux/wireframes.md` — Wireframe ASCII 6 schermate principali
- `specs/testing/test-strategy.md` — Test strategy (pytest, Playwright, coverage targets)
- `specs/05-sprint-plan.md` — Sprint plan (10 sprint, 224 SP, task breakdown)
- `CLAUDE.md` — Project context per implementazione

## Review
- **Review v1 (pre-pivot)**: FAIL — 40 finding → tutti risolti nel pivot 1
- **Review v2 (post-pivot 1)**: PASS 95% — 17 non-blocking, 6 minor per fase 4
- **Review v3 (post-pivot 2)**: PASS — 9 AC aggiunti, completeness 9/9 (100%). 8 edge case non-blocking rimasti (priorita bassa).
- **Review v4 (Fase 4 tech spec)**: PASS (post-fix) — 3 contraddizioni risolte, mapping 40/40, 61 endpoint numerati. Restano 3 finding non-blocking e 9 edge case.
- **Review v5 (Fase 5 sprint plan)**: PASS — 9/9 completeness, 0 contraddizioni, 5 finding non-blocking, 6 edge case.

## Sprint 1: COMPLETATO
| Story | Status | Tests |
|-------|--------|-------|
| US-01 Registrazione e login | ✅ Completata | 17/17 PASS |
| US-02 Profilo utente | ✅ Completata | 12/12 PASS |
| US-03 SPID/CIE | ✅ Completata | 9/9 PASS |
| US-12 Piano dei conti | ✅ Completata | 8/8 PASS |

**Sprint 1 Totale:** 24 SP | 4/4 stories | 46 test | 46 PASS | 0 bugs

## Sprint 2: COMPLETATO
| Story | Status | Tests |
|-------|--------|-------|
| US-04 Sync fatture cassetto fiscale | ✅ Completata | 6/6 PASS |
| US-05 Parsing XML FatturaPA | ✅ Completata | 4/4 PASS |
| US-10 Categorizzazione automatica | ✅ Completata | 5/5 PASS |
| US-14 Dashboard fatture e agenti | ✅ Completata | 6/6 PASS |

**Sprint 2 Totale:** 24 SP | 4/4 stories | 21 test | 21 PASS | 0 bugs

## Sprint 3: COMPLETATO
| Story | Status | Tests |
|-------|--------|-------|
| US-11 Verifica e correzione categoria | ✅ Completata | 7/7 PASS |
| US-13 Registrazione scritture partita doppia | ✅ Completata | 7/7 PASS |
| US-15 Dashboard scritture contabili | ✅ Completata | 6/6 PASS |
| US-16 Onboarding guidato | ✅ Completata | 5/5 PASS |

**Sprint 3 Totale:** 21 SP | 4/4 stories | 25 test | 25 PASS | 0 bugs

**v0.1 MVP COMPLETATO** — 12/12 Must Have stories (69 SP), flusso end-to-end funzionante:
SPID → sync → parse → categorizza → verifica → registra → dashboard

## ADR-007: Drop Odoo — AccountingEngine interno (APPROVATA)
- Odoo CE 18 rimosso — sostituito con AccountingEngine interno
- Piano dei conti salvato in tabella `chart_accounts` (non piu Odoo XML-RPC)
- 10 regole fiscali italiane in tabella `fiscal_rules` (configurabili, con validita temporale)
- Mapping CEE integrato nel piano conti (cee_code, cee_name)
- Deploy: 3 container (api + postgres + redis) — niente Odoo
- 103 test PASS (92 precedenti + 11 nuovi fiscal rules)

## Sprint 4: COMPLETATO
- US-06 Upload manuale | US-07 SDI webhook | US-08 Email MCP | US-17 Scadenzario | US-19 Report
- **22 SP | 5/5 stories | 39 test PASS**

## Sprint 5: COMPLETATO
- US-09 OCR | US-18 Notifiche | US-20 Alert fiscali | US-23 Bilancio CEE
- **20 SP | 4/4 stories | 47 test PASS**

## Sprint 6: COMPLETATO
- US-21 Fatturazione attiva | US-24 Open Banking | US-22 Liquidazione IVA
- **24 SP | 3/3 stories | 32 test PASS**

## Sprint 7: COMPLETATO
- US-25 Cash flow | US-26 Riconciliazione | US-33 Ritenute | US-35 Bollo
- **24 SP | 4/4 stories | 37 test PASS**

## Sprint 8: COMPLETATO
- US-29 Note spese | US-30 Approvazione | US-31 Cespiti | US-32 Dismissione | US-36 Ratei
- **21 SP | 5/5 stories | 44 test PASS**

## Sprint 9: COMPLETATO
- US-34 CU annuale | US-37 Conservazione | US-27 Pagamenti PISP | US-28 Monitor normativo
- **23 SP | 4/4 stories | 32 test PASS**

## Sprint 10: COMPLETATO
- US-38 F24 | US-39 Dashboard CEO | US-40 Budget vs consuntivo
- **21 SP | 3/3 stories | 35 test PASS**

## PROGETTO COMPLETATO
- **40/40 stories** implementate (224 SP)
- **369 test** tutti PASS, 0 bug
- **10/10 sprint** completati
- v0.1 Must Have (69 SP) + v0.2 Should Have (32 SP) + v0.3 Could Have (79 SP) + v0.4 Could Have (44 SP)

## Post-Sprint: Miglioramenti Chatbot (2026-03-26)
- **Chatbot ElevIA Redesign**: input bar always-visible, framer-motion, glassmorphism, suggestion pills
- **Action Commands (Level 3)**: chatbot controlla UI — navigate, set_year, set_filter
  - Auto actions + toast feedback
  - Suggested actions come bottoni cliccabili
  - Whitelist, batch execution, user priority
- **Context Engineering (Level 2)**: pagina + anno iniettati nel system prompt
- **Smart Response**: text/table/link in base a quantità risultati
- **Open Banking**: richieste inviate a Fabrick (AISP) e Salt Edge (Partner Program)

## PIVOT 4 IN CORSO: Fatturazione Attiva Completa + Costi Personale
- **US-41**: Fattura attiva completa (XML FatturaPA v1.2, multi-linea, RegimeFiscale, Sede, DatiPagamento)
- **US-42**: Impostazioni fatturazione (IBAN, modalità pagamento, regime fiscale, sede) salvate in Tenant
- **US-43**: Copia di cortesia PDF da fattura attiva
- **US-44**: Importazione costi del personale (cedolini/stipendi come voce di costo)

## Prossimi Passi
1. Implementare US-41/42/43/44 (fatturazione attiva + costi personale)
2. Call tecnica con A-Cube per SDI produzione
3. Creare adapter `api/adapters/fabrick.py` dopo risposta Fabrick
4. Completare KYC Salt Edge come piano B
5. Ingaggiare commercialista per validazione contabile

---
_Ultimo aggiornamento: 2026-03-26_
