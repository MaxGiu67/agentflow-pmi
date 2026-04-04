<!-- Aggiornato: 2026-04-03 — Pivot 6+7 completati, PWA, CRM Sales+Email -->
# CLAUDE.md

## Project Overview
- **Nome**: AgentFlow PMI
- **Vision**: Controller aziendale AI per PMI italiane — fatture, scadenzario, cash flow, CRM sales, email marketing, budget. Da gestionale a copilota del CEO.
- **Stack Backend**: Python 3.12 + FastAPI, PostgreSQL 16, Redis, Celery
- **Stack Frontend**: React 19 + TypeScript + Vite 8 + Tailwind 4, PWA installabile
- **CRM**: Interno PostgreSQL — pipeline Kanban, contatti, deal, ordini, attivita (ADR-009)
- **Email Marketing**: Brevo (ex Sendinblue) — invio, open/click tracking, sequenze automatiche (ADR-009)
- **Database**: PostgreSQL applicativo, 40+ tabelle, multi-tenant
- **Deploy**: Railway (api + frontend), GitHub
- **Clienti**: 4-5 clienti Nexa Data interessati ad AgentFlow PMI

## Architecture Decisions (ADR)
- ADR-001: Python over Node.js
- ADR-003: Hybrid rules + scikit-learn per categorizzazione (no LLM API)
- ADR-004: FiscoAPI + A-Cube per cassetto fiscale + SDI + Open Banking
- ADR-005: Multi-database per multi-tenancy (GDPR)
- ADR-007: Drop Odoo contabile → engine interno PostgreSQL
- ADR-008: Odoo 18 CRM (SOSTITUITA da ADR-009 — resta opzione bundle)
- **ADR-009**: CRM interno + Brevo email — zero dipendenza Odoo, 300 EUR/anno

## Stato Implementazione

### Backend — 70+ stories, 500+ test
| Fase | Stories | Test | Cosa |
|------|---------|------|------|
| v0.1-v0.4 (Sprint 1-10) | 40 | 369 | Auth, fatture, contabilita, fisco, banca, spese, cespiti, F24, CU, CEO |
| Pivot 5 (Sprint 11-16) | - | - | Import pipeline, agenti, chatbot, puzzle dashboard |
| Pivot 6 (Sprint 17-22) | 17 | 75 | IVA scorporo, scadenzario, cash flow, fidi, anticipo fatture |
| Pivot 7 (Sprint 23-27) | 13 | 67 | CRM interno, Kanban, Brevo email, sequenze |

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
- `api/modules/crm/` — **15+ endpoint**: contatti CRUD, deal CRUD, pipeline stages, ordini, attivita, analytics (weighted, conversion, won/lost)
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

### Sistema
- `api/modules/chat/` — chatbot AI con orchestratore 19+ tools
- `api/modules/dashboard/` — puzzle dashboard, yearly stats, widget layout
- `api/modules/ceo/` — KPI CEO, budget vs consuntivo, proiezioni

## Modelli DB (40+ tabelle)

### CRM (Pivot 7 — ADR-009)
- `CrmContact` — contatti (name, type, piva, email, sector, source, assigned_to, email_opt_in)
- `CrmPipelineStage` — stadi pipeline (name, sequence, probability, color, is_won, is_lost)
- `CrmDeal` — deal (contact_id, stage_id, deal_type, revenue, daily_rate, order_*)
- `CrmActivity` — attivita (call, email, meeting, note, task)

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

## Config .env
```env
# Core
DATABASE_URL, JWT_SECRET_KEY, REDIS_URL

# Email Marketing (Brevo)
BREVO_API_KEY, BREVO_WEBHOOK_SECRET, BREVO_SENDER_EMAIL, BREVO_SENDER_NAME

# Servizi esterni
SALTEDGE_APP_ID, SALTEDGE_SECRET
OPENAI_API_KEY

# Odoo (opzionale — per bundle clienti)
ODOO_URL, ODOO_DB, ODOO_USER, ODOO_API_KEY
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
