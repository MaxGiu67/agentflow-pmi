# Architettura — AgentFlow PMI (ContaBot → Piattaforma)

**Data:** 2026-03-22 (aggiornato)
**Principio:** MVP pragmatico, architettura pensata per evoluzione multi-tenant

---

## Visione Architetturale Evoluta

Il sistema nasce come ContaBot (singolo tenant) ma l'architettura è disegnata per scalare verso **AgentFlow Pro** — una piattaforma multi-tenant SaaS con marketplace di agenti AI per PMI italiane.

```
FASE 1 (v0.1-0.2): ContaBot singolo tenant — validazione
FASE 2 (v0.3-0.4): ContaBot + FiscoBot — agenti multipli
FASE 3 (v1.0):     AgentFlow Pro — multi-tenant + marketplace agenti
```

---

## Stack Tecnologico

| Layer | Tecnologia | Motivazione |
|-------|-----------|-------------|
| Backend API | **Python 3.12 + FastAPI** | Ecosistema OCR/ML, async-native, compatibile con Odoo |
| Task Queue | **Celery + Redis** | Processing asincrono, retry policy, event bus |
| Frontend | **React + TypeScript + Tailwind** | SPA responsive, dashboard cliente |
| Engine Contabile | **Odoo Community 18 + OCA l10n-italy** | Partita doppia, piano conti, IVA, bilancio CEE, fatturazione SDI — 80+ moduli IT |
| Database | **PostgreSQL 16** | ACID per dati contabili, multi-database per multi-tenancy |
| Cache/Events | **Redis** | Pub/Sub inter-agente, cache, sessions |
| ML/Learning | **scikit-learn + rules engine** | Categorizzazione ibrida, no LLM API per costi |
| OCR | **Google Cloud Vision** | €1.50/1000 images, fallback Tesseract |
| API Cassetto Fiscale | **FiscoAPI** | F24, dichiarazioni, visure, download massivo fatture |
| API Fatturazione SDI | **A-Cube API** | Invio/ricezione fatture SDI + Open Banking (AISP/PISP) |
| Open Banking Gateway | **A-Cube / Fabrick (fallback)** | Lettura conto corrente (PSD2 AISP), pagamenti (PISP futuro) |
| Infra | **AWS (eu-south-1 Milano)** | Data residency EU/GDPR |
| CI/CD | **GitHub Actions** | Standard, gratuito |
| Auth | **OAuth2 + JWT** | Multi-provider (Google, SPID futuro) |

---

## ADR — Decisioni Architetturali Chiave

### ADR-001: Python over Node.js
- **Contesto:** Serve OCR, ML, parsing XML, e compatibilità con Odoo (Python/Frappe)
- **Decisione:** Python + FastAPI come API layer, Odoo come engine contabile
- **Trade-off:** Stack omogeneo Python, ma Odoo ha la sua complessità

### ADR-002: Odoo headless come engine contabile
- **Contesto:** Serve partita doppia, piano dei conti personalizzabile via API, localizzazione italiana completa (IVA, bilancio CEE, reverse charge, Ri.Ba.)
- **Decisione:** Odoo Community 18 + moduli OCA l10n-italy, usato "headless" — il cliente non vede mai Odoo, interagisce solo con la nostra dashboard React
- **Trade-off:** Odoo è pesante come dipendenza, ma offre 80+ moduli IT già testati. Costruire la partita doppia da zero richiederebbe 6+ mesi
- **Piano conti:** L'agente crea il piano dei conti via API XML-RPC/JSON-2 di Odoo, personalizzato per tipo azienda (SRL, SRLS, P.IVA forfettaria, ditta individuale)
- **Nota:** XML-RPC deprecato da v19, migrazione a JSON-2 API pianificata

### ADR-003: No LLM API per categorizzazione
- **Contesto:** LLM costoso (€0.01-0.05/fattura) e privacy dati
- **Decisione:** Hybrid rules + scikit-learn similarity
- **Revisione:** Se accuracy < 80% dopo 8 settimane, valutare LLM con batching

### ADR-004: FiscoAPI + A-Cube per integrazioni fiscali
- **Contesto:** Serve accesso a cassetto fiscale (F24, dichiarazioni), fatturazione SDI, e Open Banking
- **Decisione:** FiscoAPI per cassetto fiscale/AdE, A-Cube per SDI + Open Banking
- **Trade-off:** Due provider esterni, ma ognuno è il migliore nel suo ambito. Alternative: CWBI per cassetto fiscale, Invoicetronic per SDI
- **Rischio:** Dipendenza da provider terzi per dati fiscali critici — serve fallback

### ADR-005: Multi-database per multi-tenancy (v1.0)
- **Contesto:** Ogni tenant (PMI) ha dati finanziari sensibili che devono essere isolati
- **Decisione:** Un database Odoo separato per ogni tenant, gestito dal database manager di Odoo
- **Trade-off:** Più risorse server, aggiornamenti per-tenant, ma isolamento GDPR totale
- **Alternativa scartata:** DB condiviso con company_id — troppo rischioso per dati finanziari

### ADR-006: A-Cube come provider unico SDI + Open Banking
- **Contesto:** Serve leggere saldi e movimenti del conto corrente aziendale per alimentare il CashFlowAgent, riconciliare fatture↔pagamenti, e in futuro disporre pagamenti (PISP). La direttiva PSD2 (EU 2015/2366) obbliga le banche a esporre API tramite provider autorizzati (AISP/PISP).
- **Decisione:** A-Cube come provider unico per SDI + Open Banking (già nel nostro stack per fatturazione). Un contratto, un'integrazione, un'API REST con OpenAPI 3.0.
- **Alternativa valutata — Fabrick:** Leader italiano Open Banking, licenza AISP propria, copre tutte le banche italiane tramite CBI Globe (~400 istituti, 80% del mercato). Mantenuto come fallback se copertura A-Cube insufficiente.
- **Alternativa scartata — Tink/Yapily/TrueLayer:** Aggregatori europei con buona copertura IT (Yapily 90-99%), ma overkill per MVP Italy-only. Valutare da v1.0 se espansione EU.
- **Infrastruttura sottostante — CBI Globe:** Gateway PSD2 del consorzio bancario italiano (CBI), collega 400+ banche. Non ci integriamo direttamente — ci arriviamo tramite A-Cube o Fabrick.
- **Trade-off:** Dipendenza da A-Cube per due servizi critici (SDI + banca). Mitigazione: `BankingAdapter` astratto che permette switch a Fabrick senza toccare la business logic.
- **Sicurezza:** Token bancari PSD2 richiedono SCA (Strong Customer Authentication). Consent utente con scadenza 90gg (rinnovabile). Token criptati at-rest (AES-256).

---

## Schema Architetturale

### Fase 1-2: Singolo Tenant (MVP → Multi-agente)

```
┌──────────────────────────────────────────────────────────────────┐
│                    AGENTFLOW ORCHESTRATORE                        │
│                  (FastAPI + Event Router + Tenant Router)         │
└────┬──────────┬──────────┬──────────┬──────────┬────────────────┘
     │          │          │          │          │
┌────▼───┐ ┌───▼────┐ ┌───▼────┐ ┌───▼────┐ ┌───▼──────┐
│ EMAIL  │ │  OCR   │ │LEARNING│ │ CONTA  │ │ FISCO   │
│ AGENT  │ │ AGENT  │ │ AGENT  │ │ AGENT  │ │ AGENT   │
│        │ │        │ │        │ │        │ │         │
│Gmail   │ │Vision +│ │sklearn │ │Crea    │ │Scadenze │
│Outlook │ │Tesser. │ │+rules  │ │piano   │ │F24,IVA  │
│PEC     │ │+lxml   │ │        │ │conti,  │ │alert    │
│        │ │        │ │        │ │registra│ │normativi│
│        │ │        │ │        │ │scritture│ │        │
└────┬───┘ └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘
     │         │          │          │          │
     ▼         ▼          ▼          ▼          ▼
┌─────────────────────────────────────────────────────────────┐
│                  REDIS EVENT BUS (Pub/Sub)                    │
│  email.received → invoice.parsed → invoice.categorized       │
│  → journal.entry.created → deadline.approaching              │
└──────────┬──────────────────────────────┬───────────────────┘
           │                              │
┌──────────▼──────────┐    ┌──────────────▼──────────────────┐
│   ODOO CE 18        │    │     SERVIZI ESTERNI              │
│   (headless)        │    │                                  │
│                     │    │  FiscoAPI → Cassetto fiscale,    │
│ • Partita doppia    │    │             F24, dichiarazioni   │
│ • Piano dei conti   │    │                                  │
│ • Registri IVA      │    │  A-Cube  → SDI fatture +         │
│ • Bilancio CEE      │    │    Open Banking AISP (saldi,     │
│ • Reverse charge    │    │    movimenti) + PISP (pag. v0.4) │
│ • Ri.Ba.            │    │                                  │
│ • l10n-italy (80+)  │    │  CBI Globe (via A-Cube/Fabrick)  │
│                     │    │  → 400+ banche IT, PSD2          │
│                     │    │                                  │
│                     │    │  Gmail API → Email monitoring    │
│                     │    │                                  │
│                     │    │  Cloud Vision → OCR              │
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

## Flusso Dati Principale (v0.1+)

```
1.  Email/PEC arriva → Email Agent riceve
2.  Email Agent → pubblica "email.received" su Redis
3.  OCR Agent → sottoscrive, estrae dati fattura (Vision/lxml per XML SDI)
4.  OCR Agent → pubblica "invoice.parsed" con dati strutturati
5.  Learning Agent → sottoscrive, propone categoria
6.  Learning Agent → pubblica "invoice.categorized"
7.  ContaAgent → sottoscrive, registra scrittura in partita doppia su Odoo
8.  ContaAgent → pubblica "journal.entry.created"
9.  FiscoAgent → monitora scadenze, pubblica "deadline.approaching"
10. BankingAdapter → sync giornaliero movimenti conto via A-Cube AISP
11. CashFlowAgent → riconcilia fatture↔movimenti bancari, previsione 90gg
12. CashFlowAgent → pubblica "payment.matched" o "payment.unmatched"
13. Frontend → mostra tutto in dashboard real-time
14. Utente → conferma/corregge → feedback loop al Learning Agent
```

---

## Schema Dati

### Database Applicativo (PostgreSQL — gestito da FastAPI)

```sql
-- Tenant (v1.0 multi-tenant)
CREATE TABLE tenants (
    id UUID PRIMARY KEY,
    name VARCHAR(255),
    type VARCHAR(20),            -- srl, srls, piva, ditta_individuale
    regime_fiscale VARCHAR(50),  -- forfettario, semplificato, ordinario
    odoo_db_name VARCHAR(100),   -- nome database Odoo associato
    subscription_tier VARCHAR(20), -- starter, business, premium, partner
    active_agents JSONB,         -- ["conta", "fisco", "comm"]
    created_at TIMESTAMP DEFAULT NOW()
);

-- Utenti (possono appartenere a un tenant)
CREATE TABLE users (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    role VARCHAR(20),            -- owner, admin, viewer
    oauth_tokens JSONB,          -- encrypted at rest
    created_at TIMESTAMP DEFAULT NOW()
);

-- Fatture (cache locale + sync con Odoo)
CREATE TABLE invoices (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id),
    odoo_move_id INTEGER,        -- ID corrispondente in Odoo
    type VARCHAR(10),            -- attiva, passiva
    source VARCHAR(20),          -- email, upload, sdi, cassetto_fiscale
    raw_data JSONB,
    structured_data JSONB,
    category_id UUID,
    category_confidence FLOAT,
    verified BOOLEAN DEFAULT FALSE,
    file_path VARCHAR(500),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Scadenze fiscali
CREATE TABLE fiscal_deadlines (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id),
    type VARCHAR(50),            -- iva_trimestrale, f24, inps, irpef, ecc.
    description TEXT,
    due_date DATE,
    status VARCHAR(20),          -- pending, notified, completed, overdue
    amount DECIMAL(12,2),
    source VARCHAR(30),          -- calculated, fiscoapi, manual
    created_at TIMESTAMP DEFAULT NOW()
);

-- Eventi agente (event sourcing)
CREATE TABLE agent_events (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id),
    event_type VARCHAR(100),
    agent_name VARCHAR(50),
    payload JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Feedback categorizzazione (learning)
CREATE TABLE categorization_feedback (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id),
    invoice_id UUID REFERENCES invoices(id),
    suggested_category VARCHAR(100),
    final_category VARCHAR(100),
    was_correct BOOLEAN,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Conti correnti collegati (Open Banking PSD2)
CREATE TABLE bank_accounts (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id),
    provider VARCHAR(20),            -- acube, fabrick
    bank_name VARCHAR(255),
    iban VARCHAR(34),
    consent_token TEXT,              -- encrypted AES-256
    consent_expires_at TIMESTAMP,    -- PSD2: max 90gg
    sca_last_auth TIMESTAMP,         -- ultima Strong Customer Auth
    last_sync_at TIMESTAMP,
    status VARCHAR(20),              -- active, expired, revoked
    created_at TIMESTAMP DEFAULT NOW()
);

-- Movimenti bancari (sync da Open Banking)
CREATE TABLE bank_transactions (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id),
    bank_account_id UUID REFERENCES bank_accounts(id),
    transaction_id VARCHAR(255),     -- ID dal provider (dedup)
    date DATE,
    amount DECIMAL(12,2),
    direction VARCHAR(10),           -- credit, debit
    counterpart_name VARCHAR(255),
    counterpart_iban VARCHAR(34),
    description TEXT,
    category VARCHAR(50),            -- auto-categorizzato
    matched_invoice_id UUID REFERENCES invoices(id),  -- riconciliazione
    reconciled BOOLEAN DEFAULT FALSE,
    raw_data JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_bank_tx_tenant_date ON bank_transactions(tenant_id, date);
CREATE INDEX idx_bank_tx_unreconciled ON bank_transactions(tenant_id, reconciled) WHERE reconciled = FALSE;
```

### Database Contabile (Odoo — uno per tenant)

Gestito interamente da Odoo, include:
- `account.account` — Piano dei conti (creato dall'agente su misura)
- `account.move` — Registrazioni contabili (partita doppia)
- `account.move.line` — Righe dare/avere
- `account.journal` — Registri (vendite, acquisti, banca, vari)
- `account.tax` — Aliquote IVA
- `account.fiscal.position` — Posizioni fiscali
- Moduli OCA: registri IVA, liquidazione, bollo, Ri.Ba., bilancio CEE

---

## API Contract

### API Pubblica (FastAPI → Dashboard)

| # | Endpoint | Method | Auth | Descrizione |
|---|----------|--------|------|-------------|
| 1 | `/auth/login` | POST | - | Login OAuth2 (Google, futuro SPID) |
| 2 | `/auth/token` | POST | - | Refresh JWT |
| 3 | `/invoices` | GET | JWT | Lista fatture con filtri |
| 4 | `/invoices/{id}` | GET | JWT | Dettaglio fattura |
| 5 | `/invoices/{id}/verify` | PATCH | JWT | Conferma/correggi categoria |
| 6 | `/invoices/upload` | POST | JWT | Upload manuale PDF/foto |
| 7 | `/accounting/chart` | GET | JWT | Piano dei conti del tenant |
| 8 | `/accounting/journal-entries` | GET | JWT | Registrazioni contabili |
| 9 | `/accounting/balance-sheet` | GET | JWT | Bilancio (da Odoo) |
| 10 | `/deadlines` | GET | JWT | Scadenze fiscali |
| 11 | `/deadlines/{id}/complete` | PATCH | JWT | Segna scadenza come completata |
| 12 | `/dashboard/summary` | GET | JWT | Overview completa |
| 13 | `/agents/status` | GET | JWT | Stato agenti attivi |
| 14 | `/reports/commercialista` | GET | JWT | Export per commercialista |
| 15 | `/bank-accounts` | GET | JWT | Lista conti collegati |
| 16 | `/bank-accounts/connect` | POST | JWT | Avvia collegamento conto (redirect SCA) |
| 17 | `/bank-accounts/{id}/transactions` | GET | JWT | Movimenti con filtri data/importo |
| 18 | `/bank-accounts/{id}/balance` | GET | JWT | Saldo corrente |
| 19 | `/reconciliation/pending` | GET | JWT | Movimenti non riconciliati |
| 20 | `/reconciliation/{tx_id}/match` | POST | JWT | Abbina movimento a fattura |

### API Interna (FastAPI → Odoo)

| Operazione | Odoo Model | Via |
|-----------|-----------|-----|
| Crea piano conti | `account.account` | XML-RPC / JSON-2 |
| Registra scrittura | `account.move` + `account.move.line` | XML-RPC / JSON-2 |
| Leggi bilancio | `account.financial.report` | XML-RPC / JSON-2 |
| Crea fattura | `account.move` (type=out_invoice) | XML-RPC / JSON-2 |
| Liquidazione IVA | `account.vat.period.end.statement` | XML-RPC / JSON-2 |

### API Esterne

| Servizio | Uso | Frequenza |
|----------|-----|-----------|
| **FiscoAPI** | Scarico fatture cassetto, F24, dichiarazioni | Giornaliero |
| **A-Cube SDI** | Invio/ricezione fatture SDI | Real-time (webhook) |
| **A-Cube AISP** | Saldi e movimenti conto corrente | Giornaliero (batch) + on-demand |
| **A-Cube PISP** | Pagamenti fornitori (v0.4+) | On-demand |
| **CBI Globe** | Gateway PSD2 → 400+ banche IT (via A-Cube) | Infrastruttura sottostante |
| **Gmail API** | Monitoraggio email per fatture | Real-time (Pub/Sub) |
| **Google Cloud Vision** | OCR su PDF/immagini | On-demand |

---

## Integrazioni Esterne — Dettaglio

### Odoo Community 18 + OCA l10n-italy
- **Deploy:** Docker container dedicato, PostgreSQL separato
- **Moduli OCA attivi:** `l10n_it_account`, `l10n_it_edi_extension`, `l10n_it_vat_registries`, `l10n_it_account_vat_period_end_settlement`, `l10n_it_account_stamp`, `l10n_it_financial_statements_report`, `l10n_it_fiscalcode`
- **API:** XML-RPC (attuale) → JSON-2 (migrazione v19+)
- **Costo:** €0 (Community LGPL)

### FiscoAPI
- **Funzionalità:** Cassetto fiscale, F24, dichiarazioni, visure, download massivo fatture multi-P.IVA
- **Autenticazione:** SPID/CIE/FiscoOnline dell'utente
- **Piano:** Gratuito per 2 mesi (100 API), poi personalizzato
- **Rischio:** Dipende dalla stabilità del provider

### A-Cube API (SDI + Open Banking)
- **Funzionalità SDI:** Fatturazione elettronica (invio/ricezione), scontrini, conservazione
- **Funzionalità Open Banking AISP:** Lettura saldi e movimenti conti correnti e carte, aggregazione multi-banca
- **Funzionalità Open Banking PISP:** Disposizione pagamenti fornitori (v0.4+)
- **Infrastruttura:** Via CBI Globe → accesso a 400+ banche italiane (80% del mercato)
- **Formato:** REST, OpenAPI 3.0, Webhooks, sandbox gratuita
- **Costo:** Pay-per-use
- **Vantaggio:** Unico provider per SDI + Open Banking — un contratto, un'integrazione
- **Sicurezza PSD2:** SCA (Strong Customer Authentication) obbligatoria, consent con scadenza 90gg rinnovabile, token criptati

### Fabrick (fallback Open Banking)
- **Funzionalità:** AISP + PISP con licenza propria, leader italiano Open Banking
- **Copertura:** Tutte le banche italiane via CBI Globe
- **Uso previsto:** Fallback se copertura A-Cube insufficiente su banche locali minori
- **Pattern:** BankingAdapter astratto → switch senza toccare business logic

---

## Marketplace Agenti (v1.0)

| Agente | Cosa fa | Tier |
|--------|---------|------|
| **ContaAgent** | Cattura fatture, categorizza, registra scritture in Odoo, prima nota | Base (incluso) |
| **FiscoAgent** | Scadenze fiscali, F24, alert normativi, liquidazione IVA | Business |
| **CashFlowAgent** | Previsione liquidità 90gg, riconciliazione fatture↔movimenti bancari, alert insolvenza | Business |
| **CommAgent** | Gestione offerte, follow-up, pipeline | Premium |
| **FornitureAgent** | Ordini, tracking, pagamenti fornitori | Premium |
| **HRAgent** | Buste paga, ferie, contratti (piccole aziende) | Premium |
| **LegalAgent** | Scadenze legali, contratti, compliance | Premium |
| **NormativoAgent** | Monitora GU e circolari AdE, aggiorna regole | Incluso (critico) |

Ogni agente:
1. Si registra sull'event bus Redis
2. Sottoscrive gli eventi di suo interesse
3. Può chiamare Odoo API per leggere/scrivere dati contabili
4. Può chiamare API esterne (FiscoAPI, A-Cube)
5. Pubblica risultati come nuovi eventi
6. L'orchestratore gestisce attivazione/disattivazione per tenant

---

## Rischi Tecnici

| Rischio | Probabilità | Impatto | Mitigazione |
|---------|:-----------:|:-------:|-------------|
| Odoo come dipendenza pesante/complessa | Alta | Alto | Containerizzare, limitare moduli, team con competenza Odoo |
| OCR accuracy <85% su fatture italiane | Media | Critico | Priorità parsing XML SDI (dati già strutturati), OCR come fallback |
| FiscoAPI/A-Cube down o cambio pricing | Media | Alto | Abstraction layer, fallback CWBI/Invoicetronic |
| Multi-tenant Odoo → complessità ops | Alta | Alto | Automazione provisioning, Terraform/Ansible |
| Aggiornamenti OCA rompono moduli | Media | Medio | Pinning versioni, test suite pre-upgrade |
| Gmail OAuth review lenta | Media | Alto | Iniziare subito + fallback upload manuale |
| Learning non converge con pochi dati | Media | Alto | Baseline rule-based sempre attiva |
| PSD2 consent scade ogni 90gg | Alta | Medio | Auto-rinnovo con notifica utente, graceful degradation |
| Banche minori non su CBI Globe | Bassa | Medio | Fabrick come fallback, upload estratto conto manuale |
| A-Cube down → no dati bancari | Media | Alto | Cache locale movimenti, retry con backoff, Fabrick fallback |

---

## Roadmap Agenti

| Versione | Agenti | Integrazioni |
|----------|--------|-------------|
| v0.1 | Email Agent, OCR Agent, Learning Agent, ContaAgent (base) | Gmail, Vision, Odoo, lxml |
| v0.2 | + Notification Agent, + Report Agent | + WhatsApp, Telegram |
| v0.3 | + FiscoAgent, + CashFlowAgent | + FiscoAPI, + A-Cube SDI + AISP (conto corrente) |
| v0.4 | + NormativoAgent, riconciliazione automatica | + A-Cube PISP (pagamenti), Feed GU/AdE |
| v1.0 | Multi-tenant + Marketplace (tutti gli agenti) | + Fabrick (fallback), aggregazione multi-banca |

---

## Costi Infrastruttura Stimati

| Componente | v0.1 (MVP) | v1.0 (100 tenant) |
|------------|-----------|-------------------|
| AWS (compute + RDS + S3) | €200-400/mese | €2.000-4.000/mese |
| Odoo hosting (Docker) | Incluso in AWS | €500-1.000/mese (multi-DB) |
| FiscoAPI | Gratuito (lancio) | €200-500/mese |
| A-Cube | Pay-per-use (~€50/mese) | €500-1.500/mese |
| Google Cloud Vision | ~€15/mese (10k fatture) | ~€150/mese (100k fatture) |
| **Totale** | **~€300-500/mese** | **~€3.500-7.000/mese** |

---
_Architettura aggiornata con Open Banking PSD2 + visione evoluta — 2026-03-22_
