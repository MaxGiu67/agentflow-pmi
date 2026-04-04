# Technical Specification — AgentFlow PMI

**Progetto:** AgentFlow PMI
**MVP:** ContaBot — "L'agente contabile che impara da te"
**Data:** 2026-03-22
**Stato:** Aggiornato post review v4 — Fase 4 completa (61 endpoint, 18 tabelle, 10 BR)
**Fonte:** brainstorm/06-architecture.md, brainstorm/specialists/security.md, specs/03-user-stories.md (US-01→US-40)

---

## Technology Stack

| Layer | Tecnologia | Motivazione |
|-------|-----------|-------------|
| Backend API | **Python 3.12 + FastAPI** | Ecosistema OCR/ML, async-native, compatibile con Odoo |
| Task Queue | **Celery + Redis** | Processing asincrono, retry policy, event bus |
| Frontend | **React + TypeScript + Tailwind** | SPA responsive, dashboard cliente |
| Engine Contabile | **Odoo Community 18 + OCA l10n-italy** | Partita doppia, piano conti, IVA, bilancio CEE — 80+ moduli IT |
| Database | **PostgreSQL 16** | ACID per dati contabili, multi-database per multi-tenancy |
| Cache/Events | **Redis** | Pub/Sub inter-agente, cache, sessions |
| ML/Learning | **scikit-learn + rules engine** | Categorizzazione ibrida, no LLM API per costi |
| OCR | **Google Cloud Vision** | €1.50/1000 images, fallback Tesseract |
| API Cassetto Fiscale | **FiscoAPI** | F24, dichiarazioni, visure |
| API Fatturazione SDI | **A-Cube API** | SDI + Open Banking (AISP/PISP) |
| Open Banking Gateway | **A-Cube / Fabrick (fallback)** | PSD2 AISP lettura conto, PISP pagamenti |
| CRM Pipeline | **Odoo 18 Online** | Pipeline vendite, contatti, deal — integrato via JSON-RPC (ADR-008) |
| Infra | **AWS (eu-south-1 Milano)** | Data residency EU/GDPR |
| CI/CD | **GitHub Actions** | Standard, gratuito |
| Auth | **OAuth2 + JWT + SPID/CIE** | SPID/CIE per FiscoAPI (v0.1), Google OAuth per login alternativo |

---

## Architecture Decisions (ADR)

### ADR-001: Python over Node.js
- **Contesto:** Serve OCR, ML, parsing XML, e compatibilità con Odoo (Python/Frappe)
- **Decisione:** Python + FastAPI come API layer, Odoo come engine contabile
- **Trade-off:** Stack omogeneo Python, ma Odoo ha la sua complessità

### ADR-002: Odoo headless come engine contabile
- **Contesto:** Serve partita doppia, piano dei conti personalizzabile via API, localizzazione italiana completa (IVA, bilancio CEE, reverse charge, Ri.Ba.)
- **Decisione:** Odoo Community 18 + OCA l10n-italy, usato "headless" — il cliente non vede mai Odoo, interagisce solo con dashboard React
- **Trade-off:** Odoo pesante come dipendenza, ma 80+ moduli IT già testati. Partita doppia da zero = 6+ mesi
- **Piano conti:** L'agente crea il piano dei conti via API XML-RPC/JSON-2, personalizzato per tipo azienda (SRL, SRLS, P.IVA, ditta individuale)
- **Nota:** XML-RPC deprecato da v19, migrazione a JSON-2 API pianificata

### ADR-003: No LLM API per categorizzazione
- **Contesto:** LLM costoso (€0.01-0.05/fattura) e privacy dati
- **Decisione:** Hybrid rules + scikit-learn similarity
- **Revisione:** Se accuracy < 80% dopo 8 settimane, valutare LLM con batching

### ADR-004: FiscoAPI + A-Cube per integrazioni fiscali
- **Contesto:** Serve cassetto fiscale, fatturazione SDI, Open Banking
- **Decisione:** FiscoAPI per cassetto fiscale/AdE, A-Cube per SDI + Open Banking
- **Trade-off:** Due provider esterni, ognuno il migliore nel suo ambito
- **Fallback:** CWBI per cassetto fiscale, Invoicetronic per SDI

### ADR-005: Multi-database per multi-tenancy (v1.0)
- **Contesto:** Ogni tenant ha dati finanziari sensibili
- **Decisione:** Un database Odoo separato per tenant, gestito dal database manager di Odoo
- **Trade-off:** Più risorse server, ma isolamento GDPR totale
- **Alternativa scartata:** DB condiviso con company_id — troppo rischioso per dati finanziari

### ADR-008: Odoo 18 come CRM esterno (non contabile)
- **Contesto:** Nexa Data ha 3 commerciali, 65 risorse, 100 progetti/anno. Serve CRM per pipeline, contatti, deal (T&M, fixed, spot, hardware). La contabilita resta sull'engine interno (ADR-007).
- **Decisione:** Odoo 18 Online come CRM esterno, integrato via JSON-RPC adapter (`api/adapters/odoo_crm.py`). Nuovo modulo `api/modules/crm/` con 11 endpoint REST.
- **Keap scartato:** Pensato per e-commerce/marketing automation, non per IT consulting/body rental. Score 2/12 vs Odoo 10/12.
- **Alternative valutate:** Teamleader (8/12, buono ma meno personalizzabile), Pipedrive (6/12, no T&M nativo), HubSpot (3/12, overkill per 3 utenti).
- **Costo:** €93/mese (3 utenti). Campi custom Odoo con prefisso `x_` per deal_type, daily_rate, estimated_days, technology, hours_consumed, invoiced_amount.
- **Integrazione bidirezionale:** Odoo CRM → AgentFlow (pipeline, contatti) + AgentFlow → Odoo (write-back ore e fatturato)
- **Orchestrator:** 4 tool CRM nel sistema agentico, agente "crm" come settimo agente
- **Trade-off:** Dipendenza Odoo per CRM, ma l'adapter e astratto e sostituibile

### ADR-006: A-Cube come provider unico SDI + Open Banking
- **Contesto:** Serve leggere saldi/movimenti conto corrente per CashFlowAgent e riconciliazione. PSD2 (EU 2015/2366) obbliga le banche a esporre API via AISP/PISP.
- **Decisione:** A-Cube come provider unico SDI + Open Banking. Un contratto, un'API REST OpenAPI 3.0.
- **Fallback:** Fabrick (leader italiano Open Banking, licenza AISP propria, 400+ banche via CBI Globe)
- **Alternativa scartata:** Tink/Yapily/TrueLayer — overkill per MVP Italy-only
- **Infrastruttura:** CBI Globe (consorzio bancario italiano, 400+ banche, 80% mercato)
- **Trade-off:** Dipendenza A-Cube per 2 servizi critici. Mitigazione: `BankingAdapter` astratto per switch provider
- **Sicurezza:** Token PSD2 con SCA, consent 90gg, AES-256 at-rest

---

## Architecture Diagrams

### Fase 1-2: Singolo Tenant (MVP → Multi-agente)

```
┌──────────────────────────────────────────────────────────────────┐
│                    AGENTFLOW ORCHESTRATORE                        │
│                  (FastAPI + Event Router + Tenant Router)         │
└────┬──────────┬──────────┬──────────┬──────────┬────────────────┘
     │          │          │          │          │
┌────▼───┐ ┌───▼────┐ ┌───▼────┐ ┌───▼────┐ ┌───▼──────┐
│ FISCO  │ │ PARSER │ │LEARNING│ │ CONTA  │ │ EMAIL   │
│ AGENT  │ │ AGENT  │ │ AGENT  │ │ AGENT  │ │ AGENT   │
│        │ │        │ │        │ │        │ │(v0.2+)  │
│Cassetto│ │lxml    │ │sklearn │ │Crea    │ │Gmail MCP│
│fiscale │ │XML SDI │ │+rules  │ │piano   │ │PEC MCP  │
│FiscoAPI│ │+Vision │ │        │ │conti,  │ │OCR(v0.2)│
│SPID/CIE│ │(v0.2+) │ │        │ │registra│ │         │
│        │ │        │ │        │ │scritture│ │        │
└────┬───┘ └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘
     │         │          │          │          │
     ▼         ▼          ▼          ▼          ▼
┌─────────────────────────────────────────────────────────────┐
│                  REDIS EVENT BUS (Pub/Sub)                    │
│  invoice.downloaded → invoice.parsed → invoice.categorized    │
│  → journal.entry.created → deadline.approaching              │
└──────────┬──────────────────────────────┬───────────────────┘
           │                              │
┌──────────▼──────────┐    ┌──────────────▼──────────────────┐
│   ODOO CE 18        │    │     SERVIZI ESTERNI              │
│   (headless)        │    │                                  │
│                     │    │  FiscoAPI → Cassetto fiscale     │
│ • Partita doppia    │    │    (SPID/CIE) F24, dichiarazioni │
│ • Piano dei conti   │    │    ★ FONTE PRIMARIA v0.1 ★       │
│ • Registri IVA      │    │                                  │
│ • Bilancio CEE      │    │  A-Cube  → SDI webhook (v0.2+)   │
│ • Reverse charge    │    │    Open Banking AISP (v0.3+)     │
│ • Ri.Ba.            │    │    PISP pagamenti (v0.4+)        │
│ • l10n-italy (80+)  │    │                                  │
│                     │    │  CBI Globe (via A-Cube/Fabrick)  │
│                     │    │  → 400+ banche IT, PSD2 (v0.3+) │
│                     │    │                                  │
│                     │    │  Gmail/PEC MCP → Email (v0.2+)   │
│                     │    │                                  │
│                     │    │  Cloud Vision → OCR (v0.2+)      │
└──────────┬──────────┘    └──────────────────────────────────┘
           │
┌──────────▼──────────┐
│  React SPA          │
│  Dashboard Cliente   │
│                     │
│ • Fatture in/out    │
│ • Incassi/pagamenti │
│ • Saldo conto corr. │
│ • Movimenti banca   │
│ • Cash flow predict.│
│ • Scadenze fiscali  │
│ • Riconciliazione   │
│ • Stato agenti      │
│ • Report            │
└─────────────────────┘
```

### Fase 3: Multi-Tenant (AgentFlow Pro)

```
┌─────────────────────────────────────────────────────────────┐
│              API GATEWAY + TENANT ROUTER                     │
│         (auth, routing, rate limiting, billing)              │
└──────┬──────────────┬──────────────┬────────────────────────┘
       │              │              │
 ┌─────▼─────┐  ┌────▼─────┐  ┌────▼─────┐
 │ Tenant A  │  │ Tenant B │  │ Tenant C │
 │ SRL       │  │ P.IVA    │  │ SRLS     │
 │ Piano CEE │  │ Forfett. │  │ Piano CEE│
 │           │  │          │  │          │
 │ Agenti:   │  │ Agenti:  │  │ Agenti:  │
 │ Conta+    │  │ Conta    │  │ Conta+   │
 │ Fisco+    │  │ (base)   │  │ Fisco+   │
 │ Comm.     │  │          │  │ HR       │
 └─────┬─────┘  └────┬─────┘  └────┬─────┘
       │              │              │
 ┌─────▼──────────────▼──────────────▼─────┐
 │          ODOO Multi-Database             │
 │  DB_A (SRL) │ DB_B (P.IVA) │ DB_C (SRLS)│
 └─────────────────────────────────────────┘
```

---

## Data Model

### Database Applicativo (PostgreSQL — gestito da FastAPI)

> **Schema canonico completo:** vedi `specs/database/schema.md` (18 tabelle, 22 indici, DDL completo con tutti i campi, tipi, constraint e commenti).

**Riepilogo tabelle:**

| Categoria | Tabelle | Versione |
|-----------|---------|----------|
| Core | `tenants`, `users`, `invoices`, `fiscal_deadlines`, `agent_events`, `categorization_feedback` | v0.1 |
| Banking | `bank_accounts`, `bank_transactions` | v0.3 |
| Gap Contabili | `expense_policies`, `expenses`, `assets`, `withholding_taxes`, `stamp_duties`, `accruals_deferrals` | v0.3 |
| Fisco Avanzato | `f24_documents`, `digital_preservation`, `cu_certificates`, `budgets` | v0.4 |
### Database Contabile (Odoo — uno per tenant)

Gestito interamente da Odoo:
- `account.account` — Piano dei conti (creato dall'agente su misura)
- `account.move` — Registrazioni contabili (partita doppia)
- `account.move.line` — Righe dare/avere
- `account.journal` — Registri (vendite, acquisti, banca, vari)
- `account.tax` — Aliquote IVA
- `account.fiscal.position` — Posizioni fiscali
- Moduli OCA: registri IVA, liquidazione, bollo, Ri.Ba., bilancio CEE

---

## API Design

### API Pubblica (FastAPI → Dashboard)

| # | Endpoint | Method | Auth | Descrizione |
|---|----------|--------|------|-------------|
| 1 | `/auth/register` | POST | - | Registrazione utente (email+password) |
| 2 | `/auth/login` | POST | - | Login (email+password o OAuth2 Google) |
| 3 | `/auth/token` | POST | - | Refresh JWT |
| 4 | `/auth/spid/init` | POST | JWT | Avvia autenticazione SPID/CIE (redirect FiscoAPI) |
| 5 | `/auth/spid/callback` | GET | - | Callback SPID/CIE, salva token FiscoAPI |
| 6 | `/cassetto/sync` | POST | JWT | Forza sync cassetto fiscale |
| 7 | `/cassetto/status` | GET | JWT | Stato ultimo sync e token SPID |
| 8 | `/invoices` | GET | JWT | Lista fatture con filtri |
| 9 | `/invoices/{id}` | GET | JWT | Dettaglio fattura |
| 10 | `/invoices/{id}/verify` | PATCH | JWT | Conferma/correggi categoria |
| 11 | `/invoices/upload` | POST | JWT | Upload manuale PDF/foto |
| 12 | `/accounting/chart` | GET | JWT | Piano dei conti del tenant |
| 13 | `/accounting/journal-entries` | GET | JWT | Registrazioni contabili |
| 14 | `/accounting/balance-sheet` | GET | JWT | Bilancio (da Odoo) |
| 15 | `/deadlines` | GET | JWT | Scadenze fiscali |
| 16 | `/deadlines/{id}/complete` | PATCH | JWT | Segna scadenza completata |
| 17 | `/dashboard/summary` | GET | JWT | Overview completa |
| 18 | `/agents/status` | GET | JWT | Stato agenti attivi |
| 19 | `/reports/commercialista` | GET | JWT | Export per commercialista |
| 20 | `/bank-accounts` | GET | JWT | Lista conti collegati |
| 21 | `/bank-accounts/connect` | POST | JWT | Avvia collegamento conto (redirect SCA) |
| 22 | `/bank-accounts/{id}/transactions` | GET | JWT | Movimenti con filtri |
| 23 | `/bank-accounts/{id}/balance` | GET | JWT | Saldo corrente |
| 24 | `/reconciliation/pending` | GET | JWT | Movimenti non riconciliati |
| 25 | `/reconciliation/{tx_id}/match` | POST | JWT | Abbina movimento a fattura |
| 26 | `/expenses` | GET | JWT | Lista note spese con filtri (status, date) |
| 27 | `/expenses` | POST | JWT | Crea spesa (upload scontrino + OCR) |
| 28 | `/expenses/{id}` | GET | JWT | Dettaglio spesa con ricevuta |
| 29 | `/expenses/{id}/approve` | PATCH | JWT (owner) | Approva spesa → registrazione contabile |
| 30 | `/expenses/{id}/reject` | PATCH | JWT (owner) | Rifiuta spesa con motivazione |
| 31 | `/expenses/{id}/reimburse` | POST | JWT (owner) | Rimborsa (manuale o PISP v0.4) |
| 32 | `/expenses/policies` | GET | JWT | Policy spese aziendali |
| 33 | `/expenses/policies` | POST | JWT (owner) | Crea/aggiorna policy (es. max €25/pranzo) |
| 34 | `/assets` | GET | JWT | Registro cespiti con filtri (status, category) |
| 35 | `/assets` | POST | JWT | Crea scheda cespite (manuale o da fattura) |
| 36 | `/assets/{id}` | GET | JWT | Dettaglio cespite con piano ammortamento |
| 37 | `/assets/{id}/dispose` | POST | JWT | Registra dismissione/vendita/rottamazione |
| 38 | `/assets/depreciation/run` | POST | JWT (owner) | Calcola ammortamenti fine esercizio |
| 39 | `/withholding-taxes` | GET | JWT | Lista ritenute con filtri (paid, period) |
| 40 | `/withholding-taxes/{id}` | GET | JWT | Dettaglio ritenuta con fattura collegata |
| 41 | `/cu` | GET | JWT | Lista CU per anno |
| 42 | `/cu/generate/{year}` | POST | JWT (owner) | Genera CU annuali per tutti i percettori |
| 43 | `/cu/{id}/export` | GET | JWT | Export formato ministeriale o CSV |
| 44 | `/stamp-duties` | GET | JWT | Riepilogo bollo per trimestre |
| 45 | `/stamp-duties/quarter/{year}/{q}` | GET | JWT | Dettaglio bollo trimestre (fatture, totale, scadenza) |
| 46 | `/accruals-deferrals` | GET | JWT | Lista ratei/risconti proposti e confermati |
| 47 | `/accruals-deferrals/propose` | POST | JWT | Proponi scritture assestamento fine esercizio |
| 48 | `/accruals-deferrals/{id}/confirm` | PATCH | JWT (owner) | Conferma rateo/risconto → registrazione Odoo |
| 49 | `/preservation` | GET | JWT | Stato conservazione (conservati, in attesa, errori) |
| 50 | `/preservation/batch` | POST | JWT | Forza invio batch al provider |
| 51 | `/f24` | GET | JWT | Lista F24 generati con filtri (period, status) |
| 52 | `/f24/generate` | POST | JWT | Genera F24 per periodo (IVA + ritenute + contributi) |
| 53 | `/f24/{id}` | GET | JWT | Dettaglio F24 con sezioni compilate |
| 54 | `/f24/{id}/export` | GET | JWT | Export PDF + formato telematico |
| 55 | `/f24/{id}/mark-paid` | PATCH | JWT (owner/admin) | Segna F24 come pagato |
| 56 | `/ceo/dashboard` | GET | JWT (owner/admin) | KPI principali: fatturato, EBITDA, cash flow, DSO/DPO, top clienti/fornitori |
| 57 | `/ceo/dashboard/yoy` | GET | JWT (owner/admin) | Confronto anno precedente per tutti i KPI |
| 58 | `/ceo/budget` | GET | JWT (owner/admin) | Budget vs consuntivo per anno/mese |
| 59 | `/ceo/budget` | POST | JWT (owner) | Inserisci/aggiorna budget mensile per categoria |
| 60 | `/ceo/budget/projection` | GET | JWT (owner/admin) | Proiezione fine anno basata su trend |
| 61 | `/ceo/alerts` | GET | JWT (owner/admin) | Alert attivi (concentrazione clienti, scostamenti budget, scadenze) |

### API Interna (FastAPI → Odoo)

| Operazione | Odoo Model | Via |
|-----------|-----------|-----|
| Crea piano conti | `account.account` | XML-RPC / JSON-2 |
| Registra scrittura | `account.move` + `account.move.line` | XML-RPC / JSON-2 |
| Leggi bilancio | `account.financial.report` | XML-RPC / JSON-2 |
| Crea fattura | `account.move` (type=out_invoice) | XML-RPC / JSON-2 |
| Liquidazione IVA | `account.vat.period.end.statement` | XML-RPC / JSON-2 |

### API CRM (FastAPI → Odoo 18 JSON-RPC) — 11 Endpoint

| Operazione | Odoo Model | Endpoint AgentFlow |
|-----------|-----------|-------------------|
| Lista contatti | `res.partner` | GET /api/v1/crm/contacts |
| Crea contatto | `res.partner` | POST /api/v1/crm/contacts |
| Lista deal | `crm.lead` | GET /api/v1/crm/deals |
| Deal vinti | `crm.lead` (probability=100) | GET /api/v1/crm/deals/won |
| Dettaglio deal | `crm.lead` | GET /api/v1/crm/deals/{id} |
| Crea deal | `crm.lead` | POST /api/v1/crm/deals |
| Aggiorna deal | `crm.lead` | PATCH /api/v1/crm/deals/{id} |
| Registra ordine cliente | `crm.lead` (x_order_*) | POST /api/v1/crm/deals/{id}/order |
| Ordini in sospeso | `crm.lead` (stage=Ordine Ricevuto) | GET /api/v1/crm/orders/pending |
| Conferma ordine | `crm.lead` (x_order_confirmed=True) | POST /api/v1/crm/deals/{id}/order/confirm |
| Riepilogo pipeline | `crm.lead` + `crm.stage` | GET /api/v1/crm/pipeline/summary |
| Fasi pipeline | `crm.stage` | GET /api/v1/crm/pipeline/stages |

### API Esterne

| Servizio | Uso | Frequenza |
|----------|-----|-----------|
| **Odoo 18 CRM** | Pipeline vendite, contatti, deal (JSON-RPC) | On-demand (v1.0) |
| **FiscoAPI** | Scarico fatture cassetto fiscale, F24, dichiarazioni (SPID/CIE) | Giornaliero (v0.1) |
| **A-Cube SDI** | Ricezione fatture real-time + invio fatture attive | Real-time webhook (v0.2+) |
| **A-Cube AISP** | Saldi e movimenti conto corrente | Giornaliero + on-demand (v0.3+) |
| **A-Cube PISP** | Pagamenti fornitori | On-demand (v0.4+) |
| **CBI Globe** | Gateway PSD2 → 400+ banche IT (via A-Cube) | Infrastruttura (v0.3+) |
| **Gmail/PEC API** | Monitoraggio email per documenti non-SDI (via MCP server) | Polling/Webhook (v0.2+) |
| **Google Cloud Vision** | OCR su PDF/immagini non-XML | On-demand (v0.2+) |

---

## Integrations Detail

### Odoo Community 18 + OCA l10n-italy
- **Deploy:** Docker container dedicato, PostgreSQL separato
- **Moduli OCA:** `l10n_it_account`, `l10n_it_edi_extension`, `l10n_it_vat_registries`, `l10n_it_account_vat_period_end_settlement`, `l10n_it_account_stamp`, `l10n_it_financial_statements_report`, `l10n_it_fiscalcode`
- **API:** XML-RPC (attuale) → JSON-2 (migrazione v19+)
- **Costo:** €0 (Community LGPL)

### FiscoAPI
- **Funzionalità:** Cassetto fiscale, F24, dichiarazioni, visure, download massivo fatture multi-P.IVA
- **Autenticazione:** SPID/CIE/FiscoOnline dell'utente
- **Piano:** Gratuito per 2 mesi (100 API), poi personalizzato

### A-Cube API (SDI + Open Banking)
- **SDI:** Fatturazione elettronica, scontrini, conservazione
- **AISP:** Lettura saldi e movimenti conti correnti e carte, aggregazione multi-banca
- **PISP:** Disposizione pagamenti fornitori (v0.4+)
- **Infrastruttura:** Via CBI Globe → 400+ banche IT (80% mercato)
- **Formato:** REST, OpenAPI 3.0, Webhooks, sandbox gratuita
- **Sicurezza PSD2:** SCA obbligatoria, consent 90gg rinnovabile, token criptati

### Fabrick (fallback Open Banking)
- **AISP + PISP** con licenza propria, leader italiano
- **Copertura:** Tutte le banche italiane via CBI Globe
- **Pattern:** BankingAdapter astratto → switch senza toccare business logic

### Odoo 18 CRM (ADR-008 — Gestione Ordini Cliente)
- **Funzionalita:** Pipeline commerciale, contatti aziendali, deal/opportunita, registrazione e conferma ordini cliente
- **Deploy:** Odoo Online (SaaS) — https://nexadata.odoo.com
- **Costo:** €93/mese (3 utenti CRM)
- **API:** JSON-RPC (authenticate → execute), API key da Preferenze > Sicurezza
- **Adapter:** `api/adapters/odoo_crm.py` — client async con httpx, 18 metodi
- **Modulo:** `api/modules/crm/` — router (11 endpoint), service, schemas (Pydantic)
- **Orchestrator:** 4 tool CRM, agente "crm" (settimo agente)
- **Pipeline Odoo:** Nuovo Lead → Qualificato → Proposta Inviata → Ordine Ricevuto → Confermato
- **Campi custom (x_):** x_deal_type (T&M/fixed/spot/hardware), x_daily_rate, x_estimated_days, x_technology, x_order_type (PO/email/firma_word/portale), x_order_reference, x_order_date, x_order_notes
- **Flusso ordine:** POST /deals/{id}/order registra l'ordine ricevuto → GET /orders/pending mostra ordini in sospeso → POST /deals/{id}/order/confirm conferma (dopo conferma, commerciale crea commessa in Nexa Data)
- **Rate limit:** ~60 richieste/minuto su Odoo Online
- **Sicurezza:** API key (non password), webhook con secret validation
- **Pattern:** Stesso pattern Salt Edge / FiscoAPI (constructor injection, async, httpx)

---

## Agent Architecture

### Event-Driven Agent Pattern

```
1.  FiscoAgent → sync giornaliero cassetto fiscale via FiscoAPI (SPID/CIE)
2.  FiscoAgent → pubblica "invoice.downloaded" su Redis per ogni fattura scaricata
3.  A-Cube SDI webhook → ricezione fatture real-time (v0.2+)
4.  Parser Agent → sottoscrive, estrae dati da XML FatturaPA (lxml)
5.  Parser Agent → pubblica "invoice.parsed" con dati strutturati
6.  Learning Agent → sottoscrive, propone categoria
7.  Learning Agent → pubblica "invoice.categorized"
8.  ContaAgent → sottoscrive, registra scrittura in partita doppia su Odoo
9.  ContaAgent → pubblica "journal.entry.created"
10. FiscoAgent → monitora scadenze, pubblica "deadline.approaching"
11. Email Agent (v0.2+ via MCP) → cattura documenti non-SDI da email
12. OCR Agent (v0.2+) → estrae dati da PDF/immagini non-XML (Vision)
13. BankingAdapter (v0.3+) → sync giornaliero movimenti conto via A-Cube AISP
14. CashFlowAgent (v0.3+) → riconcilia fatture↔movimenti, previsione 90gg
15. Frontend → mostra tutto in dashboard real-time
16. Utente → conferma/corregge → feedback loop al Learning Agent
```

### Agent Marketplace (v1.0)

| Agente | Cosa fa | Tier |
|--------|---------|------|
| **ContaAgent** | Cattura fatture, categorizza, registra scritture, prima nota | Base (incluso) |
| **FiscoAgent** | Scadenze fiscali, F24, alert, liquidazione IVA | Business |
| **CashFlowAgent** | Previsione 90gg, riconciliazione fatture↔movimenti, alert | Business |
| **CommAgent** | Offerte, follow-up, pipeline | Premium |
| **FornitureAgent** | Ordini, tracking, pagamenti fornitori | Premium |
| **HRAgent** | Buste paga, ferie, contratti | Premium |
| **LegalAgent** | Scadenze legali, contratti, compliance | Premium |
| **NormativoAgent** | Monitor GU e circolari AdE, aggiorna regole | Incluso (critico) |

### Agent Roadmap

| Versione | Agenti | Integrazioni |
|----------|--------|-------------|
| v0.1 | FiscoAgent (cassetto), Parser XML, Learning, ContaAgent (base) | FiscoAPI (SPID/CIE), Odoo, lxml |
| v0.2 | + Email Agent (MCP), OCR Agent, Notification, Report, A-Cube SDI webhook | + Gmail/PEC MCP, Vision, WhatsApp, Telegram |
| v0.3 | + CashFlowAgent, + RiconciliazioneAgent, + gap contabili (cespiti, ritenute, bollo, ratei, note spese) | + A-Cube AISP, liquidazione IVA, bilancio CEE, tabelle ministeriali ammortamenti |
| v0.4 | + NormativoAgent, + PISP pagamenti, + Dashboard CEO, + F24Agent, + ConservazioneAgent | + A-Cube PISP, Feed GU/AdE, provider conservazione (Aruba/InfoCert) |
| v1.0 | + **ControllerAgent** (centri di costo, budget, KPI), + **HRAgent** (costo personale, anagrafica, scadenzario), + **CommAgent** (CRM, pipeline, preventivi) | + Multi-tenant, Fabrick fallback, multi-banca, CCNL digitali |
| v1.5 | + **ProjectAgent** (commesse, timesheet, margine, SAL), + **DocAgent** (repository, contratti) | + Integrazioni Zucchetti/TeamSystem (import buste paga) |
| v2.0 | + **ComplianceAgent** (81/08, GDPR, antiriciclaggio), + Marketplace agenti third-party | + API pubblica, plugin system |

### Nuovi Agenti (v1.0+) — Note Architetturali

**ControllerAgent (v1.0)**
- Consuma dati da: Odoo (scritture contabili), PostgreSQL (fatture categorizzate), HRAgent (costo personale)
- Produce: centri di costo, budget vs consuntivo, KPI, analisi scostamenti
- Pattern: read-only sugli stessi dati del ContaAgent, aggiunge layer analitico
- Evento Redis: `controller.kpi.updated`, `controller.budget.alert`

**HRAgent (v1.0)**
- Dati propri in PostgreSQL: `hr_employees`, `hr_contracts`, `hr_costs`
- Calcola costo azienda da RAL applicando tabelle CCNL (contributi INPS, INAIL, TFR, 13a/14a, ferie)
- NON fa buste paga — import da provider esterno
- Evento Redis: `hr.cost.computed`, `hr.contract.expiring`

**CommAgent (v1.0)**
- Dati propri in PostgreSQL: `crm_contacts`, `crm_opportunities`, `crm_quotes`
- Pipeline: opportunita → trattativa → preventivo → ordine → fattura (link a ContaAgent)
- Genera preventivi da template → conversione in fattura attiva SDI
- Evento Redis: `crm.opportunity.won`, `crm.quote.sent`

**ProjectAgent (v1.5)**
- Dati propri in PostgreSQL: `projects`, `timesheets`, `project_expenses`
- Margine commessa = fatturato progetto - (ore × costo orario HRAgent) - spese dirette
- Link bidirezionale con fatture (ContaAgent) e risorse (HRAgent)
- Evento Redis: `project.margin.updated`, `project.milestone.reached`

---

## Security & Compliance

### Threat Model (top 5)

| Vettore | Impatto | Mitigazione |
|---------|:-------:|-------------|
| Compromissione OAuth token Gmail | Critico | Encryption at-rest, rotation, scope minimo |
| IDOR su fatture (accesso dati altri utenti) | Critico | RBAC + row-level security + test automatici |
| SQL injection | Critico | ORM SQLAlchemy, Pydantic validation |
| Data leak via OCR service | Alto | Cloud Vision data residency EU, DPA |
| Backup non crittografati | Critico | AES-256 su S3, access logging |

### GDPR Requirements
- Informativa privacy (art. 13/14)
- Consenso OAuth esplicito
- Data retention: fatture 10 anni, account 2 anni post-cancellazione
- Diritto accesso, portabilità, cancellazione
- DPA con Google, AWS
- DPIA obbligatoria prima del lancio
- Registro trattamenti (art. 30)

### Security Roadmap

| Priorità | Controllo | Timeline |
|----------|-----------|----------|
| P0 | OAuth2+JWT, RBAC, TLS, Secrets Manager, Input validation, OWASP Top 10 | Prima beta |
| P1 | MFA (TOTP), Pentest esterno, DPA, DPIA, Incident response plan | Prima lancio |
| P2 | ISO 27001 assessment, SOC 2, Vulnerability scanning CI/CD | Entro 6 mesi |

### Compliance Italiana
- Conservazione fatture 10 anni (D.P.R. 633/1972) — hash SHA-256 + timestamp, partnership conservatore AgID per produzione
- NON essere intermediario telematico AdE
- PSD2: SCA + consent 90gg per Open Banking

### Security Budget
- P0 (Beta): €3-5k engineering + €1-2k legal
- P1 (Lancio): €5-10k pentest + €2-3k legal/DPIA
- P2 (6 mesi): €10-15k ISO + tooling
- **Totale anno 1: €20-35k**

---

## Infrastructure Costs

| Componente | v0.1 (MVP) | v1.0 (100 tenant) |
|------------|-----------|-------------------|
| AWS (compute + RDS + S3) | €200-400/mese | €2.000-4.000/mese |
| Odoo hosting (Docker) | Incluso in AWS | €500-1.000/mese |
| FiscoAPI | Gratuito (lancio) | €200-500/mese |
| A-Cube | Pay-per-use (~€50/mese) | €500-1.500/mese |
| Google Cloud Vision | ~€15/mese | ~€150/mese |
| **Totale** | **~€300-500/mese** | **~€3.500-7.000/mese** |

---

## Technical Risks

| Rischio | Probabilità | Impatto | Mitigazione |
|---------|:-----------:|:-------:|-------------|
| Odoo dipendenza pesante/complessa | Alta | Alto | Containerizzare, limitare moduli, team Odoo |
| OCR accuracy <85% | Media | Critico | XML SDI prioritario, OCR fallback |
| FiscoAPI/A-Cube down | Media | Alto | Abstraction layer, fallback |
| Multi-tenant Odoo ops | Alta | Alto | Terraform/Ansible provisioning |
| OCA breaking changes | Media | Medio | Pinning versioni, test suite |
| SPID/CIE integration complexity | Media | Alto | FiscoAPI gestisce flusso SPID, test precoce |
| Gmail OAuth review | Bassa (v0.2+) | Medio | MCP server, non bloccante per MVP |
| Learning non converge | Media | Alto | Baseline rule-based sempre attiva |
| PSD2 consent 90gg | Alta | Medio | Auto-rinnovo, graceful degradation |
| Banche minori non su CBI Globe | Bassa | Medio | Fabrick fallback, upload manuale |
| A-Cube down → no dati bancari | Media | Alto | Cache locale, retry, Fabrick |

---

## File Structure

```
agentflow-pmi/
├── docker-compose.yml              # Orchestrazione locale: API + Odoo + PostgreSQL + Redis
├── .env.example                    # Variabili d'ambiente (mai commitare .env)
├── .github/
│   └── workflows/
│       ├── ci.yml                  # Lint + test + coverage su PR
│       └── deploy.yml              # Deploy su AWS (staging/prod)
│
├── api/                            # Backend FastAPI
│   ├── main.py                     # Entry point FastAPI, CORS, lifespan
│   ├── config.py                   # Pydantic Settings (env vars)
│   ├── dependencies.py             # Dependency injection (DB, Redis, Odoo)
│   │
│   ├── modules/
│   │   ├── auth/
│   │   │   ├── router.py           # Endpoints auth (register, login, SPID)
│   │   │   ├── service.py          # Logica auth, JWT, SPID flow
│   │   │   ├── schemas.py          # Pydantic models request/response
│   │   │   └── __tests__/
│   │   │
│   │   ├── invoices/
│   │   │   ├── router.py           # CRUD fatture, upload, verify
│   │   │   ├── service.py          # Sync cassetto, dedup, processing
│   │   │   ├── schemas.py
│   │   │   └── __tests__/
│   │   │
│   │   ├── accounting/
│   │   │   ├── router.py           # Piano conti, scritture, bilancio
│   │   │   ├── service.py          # Bridge verso Odoo
│   │   │   ├── odoo_client.py      # XML-RPC / JSON-2 adapter
│   │   │   ├── schemas.py
│   │   │   └── __tests__/
│   │   │
│   │   ├── expenses/               # US-29, US-30
│   │   │   ├── router.py           # CRUD note spese, approvazione, rimborso
│   │   │   ├── service.py          # OCR scontrini, policy check, registrazione
│   │   │   ├── schemas.py
│   │   │   └── __tests__/
│   │   │
│   │   ├── assets/                 # US-31, US-32
│   │   │   ├── router.py           # Registro cespiti, dismissione
│   │   │   ├── service.py          # Ammortamento automatico, tabelle ministeriali
│   │   │   ├── depreciation.py     # Calcolo quote, pro-rata
│   │   │   ├── schemas.py
│   │   │   └── __tests__/
│   │   │
│   │   ├── withholding/            # US-33, US-34
│   │   │   ├── router.py           # Ritenute, CU
│   │   │   ├── service.py          # Riconoscimento da XML, calcolo netto
│   │   │   ├── cu_generator.py     # Generazione CU formato ministeriale
│   │   │   ├── schemas.py
│   │   │   └── __tests__/
│   │   │
│   │   ├── fiscal/                 # US-35, US-36, US-38
│   │   │   ├── router.py           # Bollo, ratei/risconti, F24
│   │   │   ├── stamp_duty.py       # Calcolo bollo, tracking trimestrale
│   │   │   ├── accruals.py         # Proposte ratei/risconti
│   │   │   ├── f24_generator.py    # Compilazione F24, export
│   │   │   ├── schemas.py
│   │   │   └── __tests__/
│   │   │
│   │   ├── preservation/           # US-37
│   │   │   ├── router.py           # Stato conservazione, batch
│   │   │   ├── service.py          # Invio provider, retry, verifica
│   │   │   ├── schemas.py
│   │   │   └── __tests__/
│   │   │
│   │   ├── banking/                # US-24, US-25, US-26, US-27
│   │   │   ├── router.py           # Conti, movimenti, riconciliazione
│   │   │   ├── service.py          # Sync AISP, reconciliation engine
│   │   │   ├── adapter.py          # BankingAdapter astratto (A-Cube/Fabrick)
│   │   │   ├── schemas.py
│   │   │   └── __tests__/
│   │   │
│   │   ├── dashboard/              # US-14, US-15
│   │   │   ├── router.py           # Summary, stato agenti
│   │   │   ├── service.py
│   │   │   ├── schemas.py
│   │   │   └── __tests__/
│   │   │
│   │   ├── ceo/                    # US-39, US-40
│   │   │   ├── router.py           # KPI, budget, proiezione, alert
│   │   │   ├── service.py          # Calcolo DSO/DPO, EBITDA, concentrazione
│   │   │   ├── budget_service.py   # Budget vs consuntivo, trend
│   │   │   ├── schemas.py
│   │   │   └── __tests__/
│   │   │
│   │   └── deadlines/              # US-17, US-20
│   │       ├── router.py           # Scadenzario
│   │       ├── service.py
│   │       ├── schemas.py
│   │       └── __tests__/
│   │
│   ├── agents/
│   │   ├── base_agent.py           # Classe base con Redis pub/sub
│   │   ├── fisco_agent.py          # Sync cassetto fiscale, scadenze
│   │   ├── parser_agent.py         # XML FatturaPA parser (lxml)
│   │   ├── learning_agent.py       # Categorizzazione ibrida
│   │   ├── conta_agent.py          # Registrazione scritture su Odoo
│   │   ├── cashflow_agent.py       # Previsione 90gg (v0.3)
│   │   ├── normativo_agent.py      # Monitor GU/AdE (v0.4)
│   │   └── notification_agent.py   # WhatsApp/Telegram (v0.2)
│   │
│   ├── adapters/
│   │   ├── fiscoapi.py             # Client FiscoAPI (SPID/CIE)
│   │   ├── acube.py                # Client A-Cube (SDI + AISP + PISP)
│   │   ├── odoo.py                 # Client Odoo XML-RPC / JSON-2
│   │   ├── ocr.py                  # Google Cloud Vision wrapper
│   │   └── preservation.py         # Client provider conservazione (Aruba/InfoCert)
│   │
│   ├── middleware/
│   │   ├── auth.py                 # JWT validation, RBAC
│   │   ├── tenant.py               # Tenant resolution da JWT
│   │   ├── rate_limit.py           # Rate limiting per tenant
│   │   └── logging.py              # Structured logging
│   │
│   ├── db/
│   │   ├── models.py               # SQLAlchemy models
│   │   ├── session.py              # DB session factory
│   │   └── migrations/             # Alembic migrations
│   │
│   └── utils/
│       ├── crypto.py               # AES-256 encryption per token
│       ├── validators.py           # P.IVA, IBAN, CF, ATECO
│       └── currency.py             # Conversione valuta via BCE
│
├── frontend/                       # React SPA
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx       # US-14, US-15
│   │   │   ├── Invoices.tsx        # US-04, US-05, US-06
│   │   │   ├── Expenses.tsx        # US-29, US-30
│   │   │   ├── Assets.tsx          # US-31, US-32
│   │   │   ├── FiscalDeadlines.tsx # US-17, US-20
│   │   │   ├── Banking.tsx         # US-24, US-25, US-26
│   │   │   ├── CeoDashboard.tsx    # US-39, US-40
│   │   │   ├── F24.tsx             # US-38
│   │   │   ├── Preservation.tsx    # US-37
│   │   │   └── Settings.tsx        # US-02
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── api/                    # API client (axios/fetch)
│   │   └── store/                  # Zustand state management
│   │
│   └── package.json
│
├── tests/
│   ├── conftest.py                 # Fixtures globali (DB, Redis, tenant)
│   ├── factories/                  # Factory Boy per generazione dati
│   ├── integration/                # Test API end-to-end
│   └── e2e/                        # Playwright critical paths
│
└── odoo/
    ├── Dockerfile                  # Odoo CE 18 containerizzato
    ├── addons/                     # Moduli custom ContaBot
    └── config/                     # Odoo server config
```

---

## Business Rules

### BR-01: Soglia cespiti (US-31)
Bene strumentale con importo > €516,46 (soglia ministeriale, configurabile per tenant). Sotto soglia → costo diretto. Sopra → scheda cespite con ammortamento automatico. Per fattura cumulativa: valutazione riga per riga (AC-31.5).

### BR-02: Aliquote ammortamento (US-31)
Tabelle ministeriali D.M. 31/12/1988 aggiornate. Categoria → aliquota. Primo anno: 50% dell'aliquota se acquisto in secondo semestre. Pro-rata per dismissioni in corso d'anno (AC-32.3).

### BR-03: Ritenuta d'acconto (US-33)
Riconoscimento da tag `<DatiRitenuta>` nel FatturaPA XML. Tipo RT01 (persone fisiche) / RT02 (società). Aliquote possibili: 20%, 23%, 26%, 30%. Netto da pagare = Totale fattura - ritenuta. Scadenza F24: 16 del mese successivo al pagamento (non alla fattura). La scadenza viene creata nello scadenzario (US-33), il documento F24 viene generato da US-38.

### BR-04: Imposta di bollo (US-35)
Obbligo bollo €2 su fatture esenti IVA (art. 10, art. 15, regime forfettario) con importo > €77,16. Per fatture miste (parte esente + parte imponibile): bollo solo se la somma delle righe esenti > €77,16 (AC-35.4). Versamento trimestrale via F24 codice tributo 2501. Rilevamento anche su fatture passive ricevute senza tag (AC-35.5 — warning).

### BR-05: Ratei e risconti (US-36)
Principio di competenza. Il sistema analizza fatture con periodo pluriennale. Risconto = quota di competenza esercizio successivo (es. assicurazione annuale pagata a ottobre → 9/12 risconto attivo). Rateo = costo maturato non ancora fatturato. Scrittura di assestamento al 31/12, scrittura di riapertura automatica al 1/1.

### BR-06: Conservazione digitale (US-37)
Obbligo 10 anni (art. 39 D.P.R. 633/1972). Batch giornaliero alle 02:00 (configurabile). Pacchetto di versamento: XML fattura + metadati + hash SHA-256. Provider certificato AgID (Aruba/InfoCert). Retry con backoff su errori, notifica utente se ritardo >48h.

### BR-07: F24 multi-sezione (US-38)
Un F24 mensile/trimestrale può contenere sezioni multiple: Erario (IVA, ritenute, imposte), INPS, Regioni, IMU. Compensazione: crediti IVA utilizzabili per ridurre debiti tributari (netto ≥ 0). Codici tributo principali: 6031-6034 (IVA trimestrale), 1040 (ritenute), 2501 (bollo).

### BR-08: Dashboard CEO — KPI (US-39)
Dati disponibili dopo minimo 1 mese (cruscotto completo dopo 3 mesi). DSO = (crediti commerciali / fatturato) × giorni. DPO = (debiti commerciali / acquisti) × giorni. Alert concentrazione se top 3 clienti > 60% fatturato. Confronto YoY con variazione % e freccia/colore.

### BR-09: Budget vs consuntivo (US-40)
Scostamento significativo: |delta| > 10% (soglia configurabile, default 10%). Proiezione fine anno: media mobile dei mesi precedenti × mesi rimanenti + consuntivo YTD. Voci non previste a budget evidenziate come "Non prevista".

### BR-10: Auto-approvazione note spese (US-30)
Se l'utente è l'unico con ruolo "owner" nel tenant (micro-impresa / P.IVA), le note spese vengono auto-approvate con log "auto-approvazione titolare unico". Altrimenti: workflow approvazione obbligatorio.

---

## Performance

| Metrica | Target | Note |
|---------|--------|------|
| API response time (p95) | < 200ms | Per endpoint CRUD standard |
| API response time (p95) | < 500ms | Per endpoint con calcoli (F24, ammortamenti, KPI) |
| API response time (p95) | < 2s | Per endpoint con chiamate esterne (FiscoAPI, A-Cube) |
| Sync cassetto fiscale | < 30s per 50 fatture | Batch giornaliero US-04 |
| Parsing XML FatturaPA | < 100ms per fattura | US-05, anche con 200+ righe < 5s |
| OCR scontrino/fattura | < 3s per immagine | Cloud Vision, US-09, US-29 |
| Riconciliazione batch | < 10s per 100 movimenti | US-26 |
| Dashboard CEO load | < 1s | US-39, con cache Redis 5 min |
| Calcolo ammortamenti | < 5s per 100 cespiti | US-31 batch fine esercizio |
| Generazione F24 | < 2s | US-38 |
| DB query (p95) | < 50ms | Con indici, query ottimizzate |
| Concurrent users | 50 per tenant | Con rate limiting |
| Frontend page load | < 2s (LCP) | React SPA con code splitting |

### Caching Strategy
- **Redis cache** per: saldi bancari (TTL 5min), KPI dashboard (TTL 5min), piano dei conti (TTL 1h), tabelle ministeriali ammortamento (TTL 24h)
- **No cache** per: scritture contabili, saldi Odoo, F24, CU (dati critici, sempre fresh)
- **Invalidazione**: event-driven via Redis pub/sub (es. `journal.entry.created` invalida cache KPI)

---

## Test Strategy

Dettaglio completo in `specs/testing/test-strategy.md`.

| Tipo | Framework | Coverage Target | Cosa Testa |
|------|-----------|----------------|------------|
| Unit | **pytest** + pytest-cov | 80% | Business logic (ammortamento, ritenute, bollo, ratei, F24), validators, adapters |
| Integration | **pytest** + httpx (TestClient) | 60% | API endpoints, DB queries, Odoo bridge |
| E2E | **Playwright** | Critical paths | Onboarding SPID, fattura→registrazione, note spese, F24, dashboard CEO |

---

## Story → Endpoint Mapping

| Story | Endpoints Principali | Note |
|-------|---------------------|------|
| US-01 | `POST /auth/register`, `POST /auth/login`, `POST /auth/token` | Auth base |
| US-02 | `GET/PATCH /profile`, `GET /settings` | Configurazione azienda |
| US-03 | `POST /auth/spid/init`, `GET /auth/spid/callback` | SPID/CIE flow |
| US-04 | `POST /cassetto/sync`, `GET /cassetto/status` | Sync cassetto fiscale |
| US-05 | (interno: Parser Agent) | Evento Redis invoice.parsed |
| US-06 | `POST /invoices/upload` | Upload manuale |
| US-07 | (interno: A-Cube SDI webhook) | Ricezione fatture real-time, evento Redis invoice.downloaded |
| US-08 | (interno: Email Agent via MCP) | Gmail/PEC monitoring, evento Redis email.document.found |
| US-09 | (interno: OCR Agent via Cloud Vision) | Estrazione dati da PDF/immagine, evento Redis invoice.ocr.completed |
| US-10 | (interno: Learning Agent) | Evento Redis invoice.categorized |
| US-11 | `PATCH /invoices/{id}/verify` | Feedback categorizzazione |
| US-12 | `GET /accounting/chart` | Piano dei conti |
| US-13 | `GET /accounting/journal-entries` | Scritture contabili |
| US-14 | `GET /dashboard/summary` | Dashboard fatture |
| US-15 | `GET /accounting/journal-entries` | Dashboard scritture |
| US-16 | (frontend: onboarding wizard) | Guida SPID→cassetto→fattura |
| US-17 | `GET /deadlines` | Scadenzario base |
| US-18 | (interno: Notification Agent) | WhatsApp/Telegram push via webhook |
| US-19 | `GET /reports/commercialista` | Export PDF/CSV per commercialista |
| US-20 | `GET /deadlines`, `GET /ceo/alerts` | Alert personalizzate |
| US-21 | (interno: Odoo + A-Cube SDI) | Fatturazione attiva |
| US-22 | (interno: Odoo OCA liquidazione) | Liquidazione IVA |
| US-23 | `GET /accounting/balance-sheet` | Bilancio CEE |
| US-24 | `POST /bank-accounts/connect`, `GET /bank-accounts` | Open Banking AISP |
| US-25 | (interno: CashFlowAgent) | Previsione 90gg |
| US-26 | `GET /reconciliation/pending`, `POST /reconciliation/{tx_id}/match` | Riconciliazione |
| US-27 | (interno: A-Cube PISP) | Pagamenti PISP |
| US-28 | (interno: NormativoAgent) | Monitor normativo |
| US-29 | `POST /expenses`, `GET /expenses`, `GET /expenses/policies` | Note spese upload + OCR |
| US-30 | `PATCH /expenses/{id}/approve`, `PATCH /expenses/{id}/reject`, `POST /expenses/{id}/reimburse` | Approvazione e rimborso |
| US-31 | `POST /assets`, `GET /assets/{id}`, `POST /assets/depreciation/run` | Cespiti e ammortamento |
| US-32 | `GET /assets`, `POST /assets/{id}/dispose` | Registro e dismissione |
| US-33 | `GET /withholding-taxes`, `GET /withholding-taxes/{id}` | Ritenute d'acconto |
| US-34 | `POST /cu/generate/{year}`, `GET /cu/{id}/export` | Certificazione Unica |
| US-35 | `GET /stamp-duties`, `GET /stamp-duties/quarter/{year}/{q}` | Imposta di bollo |
| US-36 | `POST /accruals-deferrals/propose`, `PATCH /accruals-deferrals/{id}/confirm` | Ratei e risconti |
| US-37 | `GET /preservation`, `POST /preservation/batch` | Conservazione digitale |
| US-38 | `POST /f24/generate`, `GET /f24/{id}/export`, `PATCH /f24/{id}/mark-paid` | F24 compilazione |
| US-39 | `GET /ceo/dashboard`, `GET /ceo/dashboard/yoy`, `GET /ceo/alerts` | Dashboard CEO |
| US-40 | `GET /ceo/budget`, `POST /ceo/budget`, `GET /ceo/budget/projection` | Budget vs consuntivo |

| US-44 | `POST /bank-accounts/{id}/import-statement` | Import PDF estratto conto (LLM extraction) |
| US-45 | `POST /bank-accounts/{id}/import-csv` | Import CSV movimenti bancari |
| US-46 | `POST/GET/PUT/DELETE /bank-transactions` | CRUD manuale movimenti |
| US-47 | `POST /corrispettivi/import-xml`, `GET /corrispettivi/sync` | Import XML corrispettivi COR10 |
| US-48 | `POST/GET/PUT/DELETE /corrispettivi` | CRUD manuale corrispettivi |
| US-49 | `POST /f24/import-pdf` | Import PDF ricevuta F24 (LLM) |
| US-50 | `POST/PUT/DELETE /f24/payments` | CRUD manuale versamenti F24 |
| US-51 | `POST /accounting/import-bilancio` (multipart: Excel/CSV) | Import saldi bilancio con mapping LLM |
| US-52 | `POST /accounting/import-bilancio` (multipart: PDF) | Import saldi bilancio da PDF |
| US-53 | `POST /accounting/import-bilancio` (multipart: XBRL) | Import saldi bilancio da XBRL |
| US-54 | `POST/GET/PUT/DELETE /accounting/initial-balances` | CRUD manuale saldi iniziali |
| US-55 | `POST /recurring-contracts/import-pdf` | Import contratti ricorrenti (LLM) |
| US-56 | `POST/GET/PUT/DELETE /recurring-contracts` | CRUD manuale contratti ricorrenti |
| US-57 | `POST /loans/import-pdf` | Import piano ammortamento (LLM) |
| US-58 | `POST/GET/PUT/DELETE /loans` | CRUD manuale finanziamenti |
| US-59 | (interno: auto-detect da LearningAgent + aliquote ministeriali) | Ammortamenti cespiti auto da fatture |
| US-60 | `POST /budget/generate`, `POST /budget/chat` | Budget Agent conversazionale |
| US-61 | `GET /budget/vs-actual/{year}/{month}` | Consuntivo mensile |
| US-62 | `GET /controller/summary`, `POST /controller/ask` | Controller Agent "Come sto andando?" |
| US-63 | `GET /controller/cost-analysis` | Controller Agent "Dove perdo soldi?" |
| US-64 | (interno: CashFlowAgent potenziato + dati banca) | Cash Flow con saldi reali |
| US-65 | (interno: AdempimentiAgent + push notifiche) | Adempimenti Agent proattivo |
| US-66 | (interno: AlertAgent + pattern detection) | Alert anomalie |
| US-67 | `POST /notifications/configure`, `POST /notifications/push` | Doppio canale notifiche |
| US-68 | `GET /home/summary` | Home conversazionale |
| US-69 | `GET /completeness-score` | Completeness Score |
| US-70 | `POST /communications/generate-email` | Email per commercialista |
| US-71 | (interno: import pipeline background + exception queue) | Import silenzioso |

---

## Pivot 5 — Architettura aggiuntiva

### ADR-008: LLM Extraction per PDF (banca, F24, bilancio)

**Decisione:** Usare LLM (Claude Haiku) per estrarre dati strutturati da PDF non standard, invece di parser regex specifici per ogni formato.

**Motivazione:** I parser regex sono fragili — l'abbiamo visto con le paghe (6/7 sbilanciati). Ogni banca/consulente ha un layout diverso. LLM extraction e' universale, costa <€0.01 per documento, e non richiede manutenzione parser.

**Flusso:**
```
PDF → pdftotext -layout → testo grezzo
  → LLM prompt strutturato (estrai campi X, Y, Z in JSON)
  → Validazione schema (Pydantic)
  → Preview utente → Conferma → Salvataggio
```

**Fallback:** Se LLM non riesce → errore + suggerimento CSV manuale

**Costo stimato:** ~€0.01 per documento (Haiku), ~€50/mese per 5000 documenti

### Nuove tabelle DB (Pivot 5)

```sql
-- Corrispettivi telematici (XML COR10 da cassetto fiscale)
CREATE TABLE corrispettivi (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    data DATE NOT NULL,
    dispositivo_id VARCHAR(50),
    piva_esercente VARCHAR(11),
    aliquota_iva DECIMAL(5,2),
    imponibile DECIMAL(12,2),
    imposta DECIMAL(12,2),
    totale_contanti DECIMAL(12,2),
    totale_elettronico DECIMAL(12,2),
    num_documenti INTEGER,
    source VARCHAR(20) NOT NULL DEFAULT 'import_xml', -- import_xml, manual
    journal_entry_id UUID REFERENCES journal_entries(id),
    raw_xml TEXT,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

-- Budget entries (header per anno)
CREATE TABLE budget_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    year INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'draft', -- draft, active, archived
    created_by_agent BOOLEAN DEFAULT false,
    notes TEXT,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    UNIQUE(tenant_id, year)
);

-- Budget lines (dettaglio mensile per categoria)
CREATE TABLE budget_lines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    budget_entry_id UUID NOT NULL REFERENCES budget_entries(id) ON DELETE CASCADE,
    month INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
    category VARCHAR(100) NOT NULL, -- ricavi, personale, fornitori, utenze, altro...
    description VARCHAR(255),
    amount_planned DECIMAL(12,2) NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT now(),
    UNIQUE(budget_entry_id, month, category)
);

-- Contratti ricorrenti (affitti, leasing, utenze)
CREATE TABLE recurring_contracts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    description VARCHAR(255) NOT NULL,
    counterpart VARCHAR(255),
    amount DECIMAL(12,2) NOT NULL,
    frequency VARCHAR(20) NOT NULL DEFAULT 'monthly', -- monthly, quarterly, annual
    category VARCHAR(100),
    start_date DATE NOT NULL,
    end_date DATE,
    source VARCHAR(20) NOT NULL DEFAULT 'manual', -- import_pdf, manual
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

-- Finanziamenti e mutui
CREATE TABLE loans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    description VARCHAR(255) NOT NULL,
    bank VARCHAR(255),
    original_amount DECIMAL(12,2) NOT NULL,
    interest_rate DECIMAL(5,2),
    start_date DATE NOT NULL,
    end_date DATE,
    monthly_payment DECIMAL(12,2),
    remaining_balance DECIMAL(12,2),
    source VARCHAR(20) NOT NULL DEFAULT 'manual', -- import_pdf, manual
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

-- Import statements log
CREATE TABLE bank_statement_imports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    bank_account_id UUID REFERENCES bank_accounts(id),
    filename VARCHAR(500),
    period_from DATE,
    period_to DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'pending', -- pending, processed, error
    extraction_method VARCHAR(20), -- llm, csv, api
    raw_text TEXT,
    movements_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT now()
);

-- Completeness Score tracking
CREATE TABLE completeness_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    source_type VARCHAR(50) NOT NULL, -- fatture, banca, paghe, corrispettivi, bilancio, f24
    status VARCHAR(20) NOT NULL DEFAULT 'not_configured', -- connected, pending, not_configured
    last_sync TIMESTAMP,
    unlocked_features JSONB DEFAULT '[]',
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    UNIQUE(tenant_id, source_type)
);
```

### Modifiche a tabelle esistenti

```sql
-- Aggiungere source a bank_transactions (se non presente)
ALTER TABLE bank_transactions ADD COLUMN IF NOT EXISTS
    source VARCHAR(20) NOT NULL DEFAULT 'open_banking'; -- import_pdf, import_csv, open_banking, manual

-- Aggiungere source a f24_documents
ALTER TABLE f24_documents ADD COLUMN IF NOT EXISTS
    source VARCHAR(20) NOT NULL DEFAULT 'calculated'; -- import_pdf, calculated, manual

-- Aggiungere auto-detection cespiti
ALTER TABLE assets ADD COLUMN IF NOT EXISTS
    source VARCHAR(20) NOT NULL DEFAULT 'manual'; -- auto_from_invoice, manual
ALTER TABLE assets ADD COLUMN IF NOT EXISTS
    detected_from_invoice_id UUID REFERENCES invoices(id);
```

---

## Pivot 6: Modelli DB Scadenzario + Finanza (Sprint 17-22)

### Nuove tabelle

```sql
-- Scadenzario attivo/passivo
CREATE TABLE scadenze (
    id UUID PRIMARY KEY, tenant_id UUID NOT NULL,
    tipo VARCHAR(10) NOT NULL, -- attivo, passivo
    source_type VARCHAR(20) NOT NULL, -- fattura, stipendio, f24, mutuo, contratto
    source_id UUID, controparte VARCHAR(255),
    importo_lordo FLOAT NOT NULL, importo_netto FLOAT NOT NULL, importo_iva FLOAT DEFAULT 0,
    data_scadenza DATE NOT NULL, data_pagamento DATE,
    stato VARCHAR(20) DEFAULT 'aperto', -- aperto, pagato, insoluto, parziale
    importo_pagato FLOAT DEFAULT 0,
    banca_appoggio_id UUID, anticipata BOOLEAN DEFAULT FALSE, anticipo_id UUID,
    created_at TIMESTAMP DEFAULT NOW(), updated_at TIMESTAMP DEFAULT NOW()
);

-- Fidi bancari
CREATE TABLE bank_facilities (
    id UUID PRIMARY KEY, tenant_id UUID NOT NULL, bank_account_id UUID NOT NULL,
    tipo VARCHAR(30) DEFAULT 'anticipo_fatture',
    plafond FLOAT NOT NULL, percentuale_anticipo FLOAT DEFAULT 80,
    tasso_interesse_annuo FLOAT DEFAULT 0, commissione_presentazione_pct FLOAT DEFAULT 0,
    commissione_incasso FLOAT DEFAULT 0, commissione_insoluto FLOAT DEFAULT 0,
    giorni_max INT DEFAULT 120, attivo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Anticipo fatture
CREATE TABLE invoice_advances (
    id UUID PRIMARY KEY, tenant_id UUID NOT NULL,
    facility_id UUID NOT NULL, invoice_id UUID NOT NULL,
    importo_fattura FLOAT NOT NULL, importo_anticipato FLOAT NOT NULL,
    commissione FLOAT DEFAULT 0, interessi_stimati FLOAT DEFAULT 0, interessi_effettivi FLOAT,
    data_presentazione DATE NOT NULL, data_scadenza_prevista DATE NOT NULL, data_chiusura DATE,
    stato VARCHAR(20) DEFAULT 'attivo', -- attivo, incassato, insoluto
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Nuovi endpoint (12 — modulo scadenzario)

| # | Method | Path | Descrizione |
|---|--------|------|-------------|
| E-P6-01 | POST | /scadenzario/generate | Genera scadenze da fatture |
| E-P6-02 | GET | /scadenzario/attivo | Lista scadenze attive (crediti) |
| E-P6-03 | GET | /scadenzario/passivo | Lista scadenze passive (debiti) |
| E-P6-04 | POST | /scadenzario/{id}/chiudi | Chiudi scadenza (full/partial) |
| E-P6-05 | POST | /scadenzario/{id}/insoluto | Segna insoluto |
| E-P6-06 | GET | /scadenzario/cash-flow | Cash flow 30/60/90gg |
| E-P6-07 | GET | /scadenzario/cash-flow/per-banca | Cash flow per banca |
| E-P6-08 | GET | /scadenzario/{id}/confronta-anticipi | Confronto costi anticipo |
| E-P6-09 | POST | /scadenzario/{id}/anticipa | Presenta anticipo fattura |
| E-P6-10 | POST | /anticipi/{id}/incassa | Incassa anticipo |
| E-P6-11 | POST | /anticipi/{id}/insoluto | Insoluto anticipo |
| E-P6-12 | GET | /fidi | Lista fidi bancari |
| E-P6-13 | POST | /fidi | Crea fido bancario |

---

## Pivot 7: CRM Sales + Email Marketing (Sprint 23-27)

### Nuove tabelle CRM

```sql
CREATE TABLE crm_contacts (
    id UUID PRIMARY KEY, tenant_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL, type VARCHAR(20) DEFAULT 'lead',
    piva VARCHAR(11), codice_fiscale VARCHAR(16), email VARCHAR(255), phone VARCHAR(20),
    website VARCHAR(255), address VARCHAR(500), city VARCHAR(100), province VARCHAR(2),
    sector VARCHAR(50), source VARCHAR(50), assigned_to UUID,
    notes TEXT, email_opt_in BOOLEAN DEFAULT TRUE, last_contact_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(), updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE crm_pipeline_stages (
    id UUID PRIMARY KEY, tenant_id UUID NOT NULL,
    name VARCHAR(100) NOT NULL, sequence INT NOT NULL,
    probability_default FLOAT DEFAULT 0, color VARCHAR(7) DEFAULT '#6B7280',
    is_won BOOLEAN DEFAULT FALSE, is_lost BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE crm_deals (
    id UUID PRIMARY KEY, tenant_id UUID NOT NULL,
    contact_id UUID, stage_id UUID, name VARCHAR(300) NOT NULL,
    deal_type VARCHAR(20), expected_revenue FLOAT DEFAULT 0,
    daily_rate FLOAT DEFAULT 0, estimated_days FLOAT DEFAULT 0,
    technology VARCHAR(255), probability FLOAT DEFAULT 10,
    assigned_to UUID, expected_close_date DATE,
    order_type VARCHAR(20), order_reference VARCHAR(100), order_date DATE, order_notes TEXT,
    lost_reason VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(), updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE crm_activities (
    id UUID PRIMARY KEY, tenant_id UUID NOT NULL,
    deal_id UUID, contact_id UUID, user_id UUID,
    type VARCHAR(20) NOT NULL, subject VARCHAR(255) NOT NULL,
    description TEXT, scheduled_at TIMESTAMP, completed_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'planned',
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Nuove tabelle Email

```sql
CREATE TABLE email_templates (
    id UUID PRIMARY KEY, tenant_id UUID NOT NULL,
    name VARCHAR(100) NOT NULL, subject VARCHAR(255) NOT NULL,
    html_body TEXT NOT NULL, text_body TEXT, variables JSON,
    category VARCHAR(50) DEFAULT 'followup', active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(), updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE email_campaigns (
    id UUID PRIMARY KEY, tenant_id UUID NOT NULL,
    name VARCHAR(200) NOT NULL, type VARCHAR(20) DEFAULT 'single',
    trigger_event VARCHAR(50), trigger_config JSON,
    status VARCHAR(20) DEFAULT 'draft',
    stats_sent INT DEFAULT 0, stats_opened INT DEFAULT 0, stats_clicked INT DEFAULT 0, stats_bounced INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(), updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE email_sends (
    id UUID PRIMARY KEY, tenant_id UUID NOT NULL,
    campaign_id UUID, contact_id UUID, template_id UUID,
    brevo_message_id VARCHAR(200), subject_sent VARCHAR(255) NOT NULL,
    to_email VARCHAR(255) NOT NULL, to_name VARCHAR(255),
    sent_at TIMESTAMP DEFAULT NOW(), status VARCHAR(20) DEFAULT 'sent',
    opened_at TIMESTAMP, clicked_at TIMESTAMP,
    open_count INT DEFAULT 0, click_count INT DEFAULT 0
);

CREATE TABLE email_events (
    id UUID PRIMARY KEY, send_id UUID NOT NULL,
    event_type VARCHAR(20) NOT NULL, url_clicked VARCHAR(500),
    ip_address VARCHAR(45), user_agent VARCHAR(500),
    timestamp TIMESTAMP NOT NULL, raw_payload JSON,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE email_sequence_steps (
    id UUID PRIMARY KEY, campaign_id UUID NOT NULL,
    step_order INT DEFAULT 1, template_id UUID NOT NULL,
    delay_days INT DEFAULT 0, delay_hours INT DEFAULT 0,
    condition_type VARCHAR(30) DEFAULT 'none',
    condition_link VARCHAR(500), skip_if_replied BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE email_sequence_enrollments (
    id UUID PRIMARY KEY, tenant_id UUID NOT NULL,
    campaign_id UUID NOT NULL, contact_id UUID NOT NULL,
    current_step INT DEFAULT 0, status VARCHAR(20) DEFAULT 'active',
    next_send_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(), updated_at TIMESTAMP DEFAULT NOW()
);
```

### Nuovi endpoint CRM (15+)

| # | Method | Path | Descrizione |
|---|--------|------|-------------|
| E-P7-01 | GET | /crm/contacts | Lista contatti con ricerca/filtri |
| E-P7-02 | POST | /crm/contacts | Crea contatto |
| E-P7-03 | PATCH | /crm/contacts/{id} | Aggiorna contatto |
| E-P7-04 | DELETE | /crm/contacts/{id} | Elimina contatto |
| E-P7-05 | GET | /crm/deals | Lista deal con filtri |
| E-P7-06 | POST | /crm/deals | Crea deal |
| E-P7-07 | PATCH | /crm/deals/{id} | Aggiorna deal (drag-drop stage) |
| E-P7-08 | GET | /crm/deals/{id} | Dettaglio deal |
| E-P7-09 | GET | /crm/deals/won | Deal vinti |
| E-P7-10 | POST | /crm/deals/{id}/order | Registra ordine |
| E-P7-11 | GET | /crm/orders/pending | Ordini da confermare |
| E-P7-12 | POST | /crm/deals/{id}/order/confirm | Conferma ordine |
| E-P7-13 | GET | /crm/pipeline/summary | Riepilogo pipeline |
| E-P7-14 | GET | /crm/pipeline/analytics | Analytics (weighted, conversion, won/lost) |
| E-P7-15 | GET | /crm/pipeline/stages | Stadi pipeline |
| E-P7-16 | GET | /crm/activities | Lista attivita |
| E-P7-17 | POST | /crm/activities | Crea attivita |
| E-P7-18 | POST | /crm/activities/{id}/complete | Completa attivita |

### Nuovi endpoint Email (10)

| # | Method | Path | Descrizione |
|---|--------|------|-------------|
| E-P7-19 | GET | /email/templates | Lista template |
| E-P7-20 | POST | /email/templates | Crea template |
| E-P7-21 | GET | /email/templates/{id} | Dettaglio template |
| E-P7-22 | PATCH | /email/templates/{id} | Aggiorna template |
| E-P7-23 | POST | /email/templates/{id}/preview | Preview con dati |
| E-P7-24 | POST | /email/send | Invia email |
| E-P7-25 | GET | /email/sends | Storico invii |
| E-P7-26 | GET | /email/stats | Stats base |
| E-P7-27 | GET | /email/analytics | Analytics avanzate |
| E-P7-28 | POST | /email/webhook | Webhook Brevo (no auth) |
| E-P7-29 | POST | /email/sequences | Crea sequenza |
| E-P7-30 | POST | /email/sequences/{id}/steps | Aggiungi step |
| E-P7-31 | GET | /email/sequences/{id}/steps | Lista step |
| E-P7-32 | POST | /email/sequences/{id}/enroll | Enrollment contatto |

### Adapter Brevo

```
api/adapters/brevo.py
- BrevoClient (async httpx)
- send_email(to, subject, html, params) → messageId
- Variable substitution: {{nome}} → valore
- Auth: api-key header
- Rate limit: 400/ora (Starter)
```

---
_Tech Spec aggiornata: 2026-04-03 — Pivot 6+7 (32 endpoint, 10 tabelle, Brevo adapter)_
_Tech Spec aggiornata post Pivot 5: Controller Aziendale AI — 2026-03-29_
