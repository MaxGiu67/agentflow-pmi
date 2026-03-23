# Changelog Brainstorming: AgentFlow PMI

## Formato
- **Data**: ISO timestamp
- **Fase**: numero fase
- **Agente**: nome agente
- **Decisione**: cosa è stato deciso/fatto
- **Contesto**: motivo/background

---

### Inizializzazione Brainstorming
- **Data**: 2026-03-22T16:45:12.073Z
- **Fase**: 0
- **Agente**: init-brainstorm.ts
- **Decisione**: Creazione struttura iniziale brainstorm/
- **Contesto**: Progetto: AgentFlow PMI — Sistema agentico ispirato a OpenClaw per la gestione completa di piccole imprese italiane (SRL, SRLS, ditta individuale). Agenti autonomi che ascoltano eventi, gestiscono processi e supportano decisioni in ambito amministrativo, commerciale, forniture, personale e legale.

---

### Assessment Operativo Completato
- **Data**: 2026-03-22
- **Fase**: 0 — Assessment
- **Agente**: Orchestratore
- **Decisione**: Tipo T1 (Idea→Validazione), Workflow A. Attivati: Market Researcher, Cartographer, Doc Writer, Security Agent (critico), Tech Architect (critico), Dependency Auditor. Punteggio scorecard: 7/20.
- **Contesto**: Punti critici emersi: D7=2 (dati sensibili/bancari/SDI), D8=2 (molte integrazioni esterne), D2=2 (posizionamento competitor da analizzare). Focus su sicurezza, architettura integrazioni e differenziazione competitiva.

---

### Brainstorming Trio Creativo
- **Data**: 2026-03-22
- **Fase**: 1 — Brainstorming
- **Agente**: Divergent Explorer → Devil's Advocate → Synthesizer
- **Decisione**: 75 idee generate, 12 sopravvissute alla sfida critica, 3 concept sintetizzati. Utente sceglie **Concept 1: ContaBot** ("L'agente contabile che impara da te").
- **Contesto**: Strategia evolutiva possibile: ContaBot → FiscoBot → AgentFlow Pro. MVP focus su cattura fatture + learning.

---

### Problem Framing ContaBot
- **Data**: 2026-03-22
- **Fase**: 2 — Problem Framing
- **Agente**: Problem Framer
- **Decisione**: 3 JTBD definiti (P.IVA, micro-impresa, PMI). H1: activation via cattura email (≥60%). H2: learning acceptance (≥80%). H3: cash flow retention (≥40%). Criteri Go/No-Go definiti.
- **Contesto**: Target = tutti e 3 i profili, workaround = mix caotico, frustrazione = triade collegata (tempo + ansia + incertezza).

---

### Market Research ContaBot
- **Data**: 2026-03-22
- **Fase**: 3 — Market Research
- **Agente**: Market Researcher
- **Decisione**: 8 competitor diretti mappati, nessuno offre agenticità/learning/predictive. Gap confermato. GTM consigliato: via commercialisti (B2B2C). Rischio principale: CAC alto in mercato saturo.
- **Contesto**: Fatture in Cloud ~100k clienti, Qonto unicorno, ~60% PMI delega a commercialista. Differenziante: "Non è un software che usi, è un agente che lavora per te."

---

### MVP Scoping ContaBot
- **Data**: 2026-03-22
- **Fase**: 4 — MVP Scope
- **Agente**: MVP Scoper
- **Decisione**: 5 Must Have (Gmail, OCR, Learning, UI verifica, Dashboard). 10 Won't Have (anti-scope spietato). v0.1 in 8 settimane, 2.75 FTE. Kill gate settimana 8.
- **Contesto**: Principio "Proteggi H1, tutto il resto segue." Scope creep è il rischio #1.

---

### Architettura ContaBot
- **Data**: 2026-03-22
- **Fase**: 6 — Architecture
- **Agente**: Tech Architect
- **Decisione**: Python/FastAPI + React + PostgreSQL + Redis + AWS eu-south-1. Pattern agentico OpenClaw-inspired: orchestratore + 3 agenti + Redis Pub/Sub. No LLM API (ADR-003).
- **Contesto**: Pragmatismo MVP. 4 ADR documentati. Schema dati 5 tabelle. 8 endpoint API. Architettura scalabile verso v0.2/v0.3 senza refactoring.

---

### Security & Privacy ContaBot
- **Data**: 2026-03-22
- **Fase**: Specialist — Security
- **Agente**: Security Agent
- **Decisione**: Threat model con 8 vettori. GDPR checklist completa. P0/P1/P2 roadmap. Costo security anno 1: €20-35k. NON diventare intermediario AdE.
- **Contesto**: D7=2 confermato critico. OAuth tokens = asset più sensibile. DPIA obbligatoria. Conservazione fatture 10 anni.

---

### Ricerca Piattaforme Fatturazione con API
- **Data**: 2026-03-22
- **Fase**: Chat — Ricerca integrazioni
- **Agente**: Davide (Tech Architect) + Federica (Market Researcher)
- **Decisione**: Mappate 6 API fatturazione SDI (Fatture in Cloud, A-Cube, Invoicetronic, OpenAPI, Fattura Elettronica API, Effatta) e 3 API cassetto fiscale (FiscoAPI, CWBI, A-Cube). Decisione: NON costruire sistema fatturazione, integrarsi con esistenti.
- **Contesto**: Il mercato API italiano è maturo. Fatture in Cloud ha SDK Python. A-Cube offre SDI + Open Banking. FiscoAPI dà accesso a cassetto fiscale/F24.

---

### Ricerca Engine Contabile per Partita Doppia
- **Data**: 2026-03-22
- **Fase**: Chat — Ricerca engine contabile
- **Agente**: Davide + Nicola (Devil's Advocate)
- **Decisione**: Valutate 5 librerie (python-accounting, Medici, Beancount, hledger, Blnk) e 2 ERP (ERPNext, Akaunting). Raccomandazione: Odoo Community 18 + OCA l10n-italy come engine contabile headless — piano conti personalizzabile via API, partita doppia nativa, 80+ moduli localizzazione italiana.
- **Contesto**: Nessuna libreria Python copre il piano dei conti CEE italiano + IVA + bilancio. Odoo è l'unico con localizzazione completa + API + open source.

---

### Decisione Architettura a 3 Componenti
- **Data**: 2026-03-22
- **Fase**: Chat — Architettura integrazioni
- **Agente**: Alessandro (Orchestratore)
- **Decisione**: Architettura a 3 pilastri: Odoo CE (engine contabile) + FiscoAPI (cassetto fiscale/F24) + A-Cube (SDI + Open Banking). Layer agentico FastAPI sopra, dashboard React per il cliente.
- **Contesto**: Ogni componente fa quello che sa fare meglio. L'agente ContaBot orchestra le 3 fonti. Il cliente non vede Odoo.

---

### Evoluzione verso Piattaforma Multi-Tenant
- **Data**: 2026-03-22
- **Fase**: Chat — Visione evoluta
- **Agente**: Davide + Nicola + Federica + Alessandro
- **Decisione**: Visione confermata di evoluzione a 3 fasi: (1) ContaBot singolo tenant validazione, (2) Multi-agente (FiscoBot, CashFlow), (3) AgentFlow Pro multi-tenant con marketplace agenti. Multi-tenancy via DB Odoo separato per tenant. Pricing a tier €49-€499/mese. Breakeven a ~€30k MRR.
- **Contesto**: Massimiliano vuole vendere agenti come servizio a PMI, con dashboard web real-time. L'architettura è stata ridisegnata per supportare questa visione fin dalla fondazione, mantenendo il principio di build incrementale.

---

### Aggiornamento Documenti (Architettura + Scope)
- **Data**: 2026-03-22
- **Fase**: Aggiornamento documenti
- **Agente**: Orchestratore
- **Decisione**: Riscritti 06-architecture.md (5 ADR, schema multi-tenant, marketplace agenti, costi infra) e 04-mvp-scope.md (3 fasi evolutive, MoSCoW aggiornato con Odoo nei Must Have, milestone dettagliate v0.1→v1.0, budget €290-400k anno 1).
- **Contesto**: I documenti originali non riflettevano le decisioni emerse dalle sessioni di chat (Odoo, FiscoAPI, A-Cube, multi-tenant).

---

### Open Banking PSD2 — Lettura Conto Corrente
- **Data**: 2026-03-22
- **Fase**: Chat — Ricerca Open Banking
- **Agente**: Davide (Tech Architect)
- **Decisione**: Lettura conto corrente via Open Banking PSD2. Provider primario: **A-Cube AISP** (stesso provider SDI — un contratto, un'API). Fallback: **Fabrick** (leader italiano Open Banking, licenza AISP propria). Infrastruttura sottostante: **CBI Globe** (consorzio bancario italiano, 400+ banche, 80% mercato). Aggregatori EU (Tink, Yapily, TrueLayer) scartati per MVP. **ADR-006** documentato. Anticipato da v0.4 a v0.3.
- **Contesto**: CashFlowAgent necessita dati bancari reali per previsioni accurate. Riconciliazione fatture↔movimenti bancari è feature chiave. PSD2 richiede SCA + consent 90gg. BankingAdapter astratto per switch provider senza impatto su business logic. Schema DB aggiornato con tabelle bank_accounts e bank_transactions. 6 nuovi endpoint API. Nuovi rischi PSD2 mappati.

---

### Aggiornamento Documenti (Open Banking)
- **Data**: 2026-03-22
- **Fase**: Aggiornamento documenti
- **Agente**: Orchestratore
- **Decisione**: Aggiornati 06-architecture.md (ADR-006, schema DB + 2 tabelle, 20 endpoint API, diagramma servizi esterni, roadmap agenti, rischi PSD2), 04-mvp-scope.md (Open Banking anticipato a v0.3, PISP a v0.4, feature F4-F5 + F10-F11 aggiunte), _status.md (decisione #6 + #12, tabella integrazioni espansa), _changelog.md.
- **Contesto**: Integrazione Open Banking completa la visione dei 3 pilastri: Odoo (contabilità) + FiscoAPI (fisco) + A-Cube (SDI + banca).

---

### Handoff completato verso UMCC (dev-methodology)
- **Data**: 2026-03-22
- **Fase**: Handoff BS → UMCC
- **Agente**: Orchestratore
- **Decisione**: Creata struttura specs/ con 3 documenti: 01-vision.md (da problem-framing: JTBD, personas, metriche, vincoli, Go/No-Go), 02-prd.md (da market-research + mvp-scope: competitor, MoSCoW, epics, milestones, pricing, rischi), 04-tech-spec.md (da architecture + security: stack, 6 ADR, schema DB 8 tabelle, 20 API, agent architecture, compliance). File tracking creati: specs/_status.md e specs/_changelog.md.
- **Contesto**: Brainstorming completato. Tutti i 12 documenti BS mappati in 3 specs strutturati per il workflow SDD. Prossimo step: `/dev-stories` per generare User Stories con Acceptance Criteria.

---
