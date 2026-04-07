<!-- Aggiornato: 2026-04-06 — Pivot 9: AgentFlow v3.0 Sales AI Platform -->
# CLAUDE.md

## Project Overview
- **Nome**: AgentFlow PMI
- **Vision**: L'AI che vende con te e gestisce per te — piattaforma AI per vendita + controller aziendale per PMI italiane
- **Stack Backend**: Python 3.12 + FastAPI, PostgreSQL 16, Redis, Celery
- **Stack Frontend**: React 19 + TypeScript + Vite 8 + Tailwind 4, PWA installabile
- **CRM**: Interno PostgreSQL — pipeline Kanban multi-template, contatti, aziende (1:N), deal, ordini, attivita (ADR-009)
- **Email Marketing**: Brevo (ex Sendinblue) — invio, open/click tracking, sequenze automatiche (ADR-009)
- **Agenti AI**: Sales Agent (product-aware) + Controller Agent + Analytics Agent (ADR-010)
- **Pipeline Templates**: Vendita Diretta, Progetto a Corpo, Social Selling — prodotto determina pipeline
- **Database**: PostgreSQL applicativo, 50+ tabelle, multi-tenant
- **Deploy**: Railway (api + frontend), GitHub
- **Primo tenant**: Nexa Data / TAAL — T&M consulting + Elevia AI product

## Architecture Decisions (ADR)
- ADR-001: Python over Node.js
- ADR-003: Hybrid rules + scikit-learn per categorizzazione (no LLM API)
- ADR-004: FiscoAPI + A-Cube per cassetto fiscale + SDI + Open Banking
- ADR-005: Multi-database per multi-tenancy (GDPR)
- ADR-007: Drop Odoo contabile → engine interno PostgreSQL
- ADR-008: Odoo 18 CRM (SOSTITUITA da ADR-009 — resta opzione bundle)
- **ADR-009**: CRM interno + Brevo email — zero dipendenza Odoo, 300 EUR/anno
- **ADR-010**: Coordinator con Sales Agent unico product-aware — prodotto determina pipeline, tool filtrati per pipeline_type
- **ADR-011**: Integrazione PortalJS.be — commesse, rapportini, dipendenti. Conferma umana per scritture. Portal master operativo, AgentFlow master commerciale

## Agent Architecture (ADR-010)

3 agenti, l'orchestratore smista per intent:
- **Sales Agent** (`api/agents/sales_agent.py`): 26 tool (8 core + 4 vendita diretta + 3 corpo + 11 social selling), filtrati per pipeline_type del deal
- **Controller Agent** (`api/agents/controller_agent.py`): 17 tool (fatture, contabilita, scadenze, fisco, budget)
- **Analytics Agent** (`api/agents/analytics_agent.py`): pipeline analytics, cashflow, KPI
- **Registry** (`api/agents/registry.py`): plugin pattern — aggiungere agente = 1 file + 1 riga

## Stato Implementazione

### Backend — 91+ stories, 1096+ test
| Fase | Stories | Test | Cosa |
|------|---------|------|------|
| v0.1-v0.4 (Sprint 1-10) | 40 | 369 | Auth, fatture, contabilita, fisco, banca, spese, cespiti, F24, CU, CEO |
| Pivot 5 (Sprint 11-16) | - | - | Import pipeline, agenti, chatbot, puzzle dashboard |
| Pivot 6 (Sprint 17-22) | 17 | 75 | IVA scorporo, scadenzario, cash flow, fidi, anticipo fatture |
| Pivot 7 (Sprint 23-27) | 13 | 67 | CRM interno, Kanban, Brevo email, sequenze |
| Pivot 8 (Sprint 28-34) | 26 | 327 | Social Selling, Company/Contact 1:N, RBAC, prodotti, compensi, Calendar, E2E |
| Pivot 9 (Sprint 35-41) | 22 | 67 | Agent Foundation, Pipeline Templates, Resource DB, Elevia Engine, LinkedIn, Cross-sell |

### Frontend — PWA React 19
| Feature | Status |
|---------|--------|
| PWA installabile (manifest, SW, icons) | Completato |
| Code splitting (React.lazy, 96 chunk) | Completato |
| Bottom nav mobile (5 tab) | Completato |
| Safe areas iOS (notch, gesture) | Completato |
| Skeleton loading + ErrorBoundary | Completato |
| useOptimistic Kanban | Completato |
| Design system (DM Sans, CSS variables) | Completato |
| ChatbotFloating solo su Dashboard/Chat | Completato |
| 48+ pagine, 42 route | Attivo |

## Moduli Backend

### Contabilita & Fisco
- `api/modules/invoices/` — fatture attive/passive, parsing XML FatturaPA
- `api/modules/active_invoices/` — fatturazione attiva SDI
- `api/modules/journal/` — scritture partita doppia
- `api/modules/accounting/` — piano conti, engine contabile
- `api/modules/f24/` — F24 compilazione
- `api/modules/fiscal/` — regole fiscali, IVA, ritenute, bollo, CU

### Banca & Cash Flow
- `api/modules/banking/` — conti, movimenti, Open Banking
- `api/modules/reconciliation/` — riconciliazione fatture-movimenti
- `api/modules/cashflow/` — cash flow base
- `api/modules/scadenzario/` — **12 endpoint**: scadenzario attivo/passivo, chiusura, insoluti, cash flow 30/60/90, cash flow per banca, fidi bancari, anticipo fatture, confronto costi

### CRM Sales + Email Marketing (Pivot 7)
- `api/modules/crm/` — **16+ endpoint**: contatti CRUD, deal CRUD, pipeline stages, ordini, attivita, analytics (weighted, conversion, won/lost), DELETE companies
- `api/modules/email_marketing/` — **10 endpoint**: template CRUD+preview, invio email, webhook tracking, storico, stats, analytics, sequenze multi-step, enrollment
- `api/adapters/brevo.py` — client async Brevo API (invio + tracking)
- `api/adapters/odoo_crm.py` — legacy, opzionale per bundle clienti

### Gestione
- `api/modules/expenses/` — note spese
- `api/modules/assets/` — cespiti e ammortamenti
- `api/modules/payroll/` — costi personale
- `api/modules/loans/` — finanziamenti
- `api/modules/recurring/` — contratti ricorrenti
- `api/modules/corrispettivi/` — corrispettivi elettronici

### Pivot 9: Sales AI (v3.0)
- `api/agents/` — Sales Agent, Controller Agent, Analytics Agent, registry (ADR-010)
- `api/modules/pipeline_templates/` — Pipeline templates CRUD + seed (Vendita Diretta, Corpo, Social Selling)
- `api/modules/resources/` — Resource DB + matching + margine + bench (T&M)
- `api/modules/elevia/` — Use case catalog + ATECO scoring + ROI + discovery brief
- `api/modules/sales_tools/` — LinkedIn messages + warmth + cadence + cross-sell detection
- `api/modules/calendar/` — Microsoft 365 OAuth + push + Calendly URL

### Integrazione PortalJS.be (Pivot 10 — ADR-011)
- `api/adapters/portal_client.py` — Client async per PortalJS.be API (NestJS + Prisma + PostgreSQL)
- Lettura: dipendenti, contratti, commesse, rapportini, timesheet
- Scrittura (con conferma umana): crea commessa da deal Won, assegna collaboratori
- Sync: rapportini finalizzati → margine reale su AgentFlow
- Endpoint proxy: `/api/v1/portal/*`
- Config: `PortalConfig` (URL, service account) + `PortalMapping` (entity mapping AF↔Portal)

### Sistema
- `api/modules/chat/` — chatbot AI con orchestratore → agent dispatch (ADR-010)
- `api/modules/dashboard/` — puzzle dashboard, yearly stats, widget layout
- `api/modules/ceo/` — KPI CEO, budget vs consuntivo, proiezioni

## Modelli DB (50+ tabelle)

### CRM (Pivot 7-10)
- `CrmCompany` — **DEPRECATO (Pivot 10)**: sostituito da Portal Customer per nuovi deal. Tabella mantenuta per retrocompatibilita deal legacy.
- `CrmContact` — contatti/referenti (company_id FK legacy, **portal_customer_id** per nuovi deal, contact_name, contact_role, origin_id)
- `CrmPipelineStage` — stadi pipeline (name, sequence, stage_type, is_won, is_lost)
- `CrmDeal` — deal (company_id legacy, **portal_customer_id**, **portal_project_id**, contact_id, stage_id, pipeline_template_id, deal_type, revenue)
- `CrmActivity` — attivita (type: call/video_call/meeting/email/task/note, activity_type_id, scheduled_at datetime, outlook_event_id, user_id auto-assigned)

### Pipeline Templates (Pivot 9)
- `PipelineTemplate` — template FSM (code, name, pipeline_type: services/product/custom)
- `PipelineTemplateStage` — stati per template (required_fields JSON, sla_days, is_optional)

### Resources (Pivot 9 — T&M)
- `Resource` — risorse interne (name, seniority, daily_cost, available_from)
- `ResourceSkill` — skill per risorsa (skill_name, skill_level 1-5, certification)

### Elevia (Pivot 9)
- `EleviaUseCase` — use case AI (code, name, description)
- `AtecoUseCaseMatrix` — ATECO × use case fit score
- `CrossSellSignal` — segnali cross-sell tra pipeline

### Email (Pivot 7)
- `EmailTemplate` — template HTML con variabili
- `EmailCampaign` — campagne (single, sequence, trigger)
- `EmailSend` — invii con brevo_message_id, open/click tracking
- `EmailEvent` — eventi webhook (delivered, opened, clicked, bounce, unsub)
- `EmailSequenceStep` — step sequenza con delay e condizioni
- `EmailSequenceEnrollment` — enrollment contatto in sequenza

### Scadenzario (Pivot 6)
- `Scadenza` — scadenze attive/passive (fattura, stipendio, mutuo, contratto)
- `BankFacility` — fidi bancari (plafond, tasso, commissioni)
- `InvoiceAdvance` — anticipo fatture (presentazione, incasso, insoluto)

## Frontend Structure
```
frontend/src/
├── api/hooks.ts          — 100+ React Query hooks (CRM, email, scadenzario)
├── components/
│   ├── ui/               — 17 componenti (Card, Badge, DataTable, Skeleton, ErrorBoundary, BottomNav, ResponsiveTable, PageMeta...)
│   ├── pwa/              — InstallPrompt, OfflineIndicator
│   ├── layout/           — AppLayout (Suspense+ErrorBoundary+BottomNav)
│   └── chat/             — ChatbotFloating (solo Dashboard/Chat)
├── pages/
│   ├── crm/              — CrmPipelinePage (Kanban), DealDetail, Contacts
│   ├── fatture/          — Lista, Crea, Dettaglio, Verifica, Upload
│   ├── banca/            — Conti, Movimenti, Riconciliazione, CashFlow
│   └── [40+ altre pagine]
└── public/
    ├── manifest.json     — PWA manifest
    ├── sw.js             — Service Worker
    └── icon-*.svg        — Icone PWA
```

## Pipeline CRM
Nuovo Lead → Qualificato → Proposta Inviata → Ordine Ricevuto → Confermato (→ Perso)

## Email Marketing (Brevo)
- Template con variabili {{nome}}, {{azienda}}, {{deal_name}}
- Tracking: open (pixel), click (link redirect), bounce, unsubscribe
- Sequenze: multi-step con condizioni (if_opened, if_not_opened, if_clicked)
- Trigger automatici: deal_stage_changed, contact_created

## Servizi Esterni

| Servizio | Cosa fa | Status |
|----------|---------|--------|
| **A-Cube** | Fatturazione SDI + Open Banking PSD2 (unico provider) | Attivo |
| **Brevo** | Email marketing + tracking (open/click/bounce) | Attivo |
| **OpenAI** | Chatbot AI + PDF extraction | Attivo |
| ~~Salt Edge~~ | ~~Open Banking~~ — rimosso, A-Cube gestisce | Disabilitato |
| ~~FiscoAPI~~ | ~~Cassetto fiscale~~ — rimosso, A-Cube gestisce | Disabilitato |
| Odoo 18 | CRM opzionale per bundle clienti | Opzionale |
| **PortalJS.be** | Gestione operativa: commesse, rapportini, dipendenti (NestJS + Prisma) | **Pivot 10** |

## Config .env
```env
# Core
DATABASE_URL, JWT_SECRET_KEY, REDIS_URL, AES_KEY

# A-Cube (unico provider: SDI + Open Banking)
ACUBE_API_KEY, ACUBE_BASE_URL

# Brevo (email marketing)
BREVO_API_KEY, BREVO_SENDER_EMAIL, BREVO_SENDER_NAME

# OpenAI (chatbot + extraction)
OPENAI_API_KEY

# PortalJS.be (gestione operativa — Pivot 10)
PORTAL_API_URL, PORTAL_JWT_SECRET, PORTAL_TENANT
```

## MCP Server
- `mcp-server/server.py` — auto-generato, espone DB + endpoint
- `python3 mcp-server/generate_mcp.py` — rigenerare dopo modifiche modelli/endpoint
- **REGOLA**: Sempre rigenerare dopo aggiunta modelli DB o endpoint API

## Coding Conventions
- Python: snake_case, Service Layer, Adapter Pattern, Pydantic schemas
- TypeScript: camelCase, PascalCase componenti, React Query hooks
- DB: snake_case tabelle/colonne
- API: /api/v1/kebab-case
- Test: 1+ test per AC, pytest + httpx

## Rules
1. Implementa una story alla volta
2. Ogni AC deve avere almeno 1 test
3. Non procedere alla story successiva finche i test non passano
4. Dopo modifiche DB/endpoint: `python3 mcp-server/generate_mcp.py`
5. CRM interno — Odoo solo come opzione bundle (ADR-009)
6. Email: logica interna, infrastruttura Brevo (pattern build logic / buy infrastructure)
7. ChatbotFloating: solo su Dashboard e Chat (non su altre pagine)

## Key Specs
- Stories Pivot 6: `specs/03-user-stories-pivot6.md`
- Stories Pivot 7: `specs/03-user-stories-pivot7-crm.md`
- Implementation: `specs/07-implementation.md`
- ADR-009: `specs/technical/ADR-009-crm-interno-brevo.md`
- Brainstorm CRM: `brainstorm/12-crm-interno-brevo-email.md`
- PWA Roadmap: `Docs/Analisi_Frontend_PWA_Roadmap.md`
