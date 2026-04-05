# Technical Specification — Pivot 8: Social Selling Configurabile

**Progetto:** AgentFlow PMI — CRM B2B per PMI italiane
**Pivot:** 8 — Social Selling Configurabile
**Data:** 2026-04-04
**Stato:** Draft
**Fonte:** specs/03-user-stories-pivot8-social.md (US-100→US-120)
**Stack:** Python 3.12 + FastAPI + SQLAlchemy 2.0 (async) / PostgreSQL 16 / Redis / React 19 + TS + Vite 8

---

## Riferimenti
- **PRD:** specs/02-prd.md, sezione "Pivot 8: Social Selling Configurabile"
- **User Stories:** specs/03-user-stories-pivot8-social.md (US-100 → US-120, 5 Epic, 21 story)
- **Tech Stack Attuale:** specs/04-tech-spec.md (stack immutato)

---

## Architecture Decision

### ADR-011: Social Selling Engine Configurabile

**Stato:** Accettato

**Contesto:**
AgentFlow PMI richiede un motore configurabile per social selling che consenta ai tenant (PMI) di:
1. Definire custom le loro origini di contatti (canali di acquisizione)
2. Creare tipi di attività custom tracciando interazioni social
3. Gestire ruoli granulari con RBAC e utenti esterni con scadenza accesso
4. Catalogo prodotti con tracciamento deal-prodotto
5. Analytics real-time con dashboard KPI componibile e compensi calcolati automaticamente

**Opzioni considerate:**

| Opzione | Pro | Contro | Valutazione |
|---------|-----|--------|------------|
| **A) Config-driven (scelta)** | Massima flessibilità, multi-tenant, no hard-coding, audit trail built-in, RBAC granulare | Complesso a livello DB (7 tabelle nuove), logica bizz in Python | 9/10 |
| **B) Hardcoded per tenant** | Veloce al primo deploy | Poco scalabile, manutenzione difficile, risch... di regression | 3/10 |
| **C) GraphQL con schema dinamic** | Potente per query flexible | Over-engineering per MVP, learning curve | 5/10 |

**Decisione:** **Opzione A — Config-driven + modello a strati**

**Architettura:**

```
┌─────────────────────────────────────────────────────────────┐
│                    CONFIG LAYER (REST API)                  │
│        Admins definiscono: Origini, Attività, Ruoli,        │
│        Prodotti, Compensi, Dashboard widgets                │
└────────────┬────────────────────────────┬──────────────────┘
             │                            │
   ┌─────────▼────────────┐      ┌────────▼────────────┐
   │  BUSINESS LOGIC      │      │  RBAC ENGINE        │
   │  (Services Layer)    │      │  (Permission Check) │
   │                      │      │                     │
   │ • Origin mgmt        │      │ • Role definitions  │
   │ • Activity tracking  │      │ • Row-level access  │
   │ • Deal-Product M2M   │      │ • Audit logging     │
   │ • Compensation calc  │      │ • External users    │
   │ • KPI aggregation    │      │                     │
   └─────────┬────────────┘      └────────┬────────────┘
             │                            │
             └────────────┬───────────────┘
                          │
             ┌────────────▼──────────────┐
             │   DATA LAYER (SQLAlchemy) │
             │                           │
             │ 7 nuove tabelle:          │
             │ • crm_contact_origins     │
             │ • crm_activity_types      │
             │ • crm_roles               │
             │ • crm_role_permissions    │
             │ • crm_audit_log           │
             │ • crm_products            │
             │ • crm_deal_products       │
             │ • crm_dashboard_widgets   │
             │ • crm_compensation_rules  │
             │ • crm_compensation_entries│
             │                           │
             │ Estensioni tabelle        │
             │ esistenti                 │
             └───────────────────────────┘
```

**Motivazione:**
- **Config-driven** perché ogni tenant PMI ha esigenze diverse (origini LinkedIn vs Referral, ruoli: commerciale vs manager)
- **RBAC granulare** perché serve segregare dati per collaboratori esterni (scadenza accesso, visibilità per canale)
- **Audit log immutabile** per compliance e tracciabilità (obbligatorio in EU per dati sensibili)
- **M2M Deal-Prodotto** per tracciare revenue per prodotto (analitica commerciale essenziale)
- **Compensi calcolati** con regole non hardcoded (ogni PMI ha modello diverso: % su revenue, bonus per prodotto, penalità inattività)

**Conseguenze:**
- **Performance:** Query più complesse (join su ruoli/permessi), mitigato con indici strategici su (tenant_id, user_id, entity)
- **Maintenance:** 10 nuove tabelle da testare (unit + integration test), migrazioni Alembic complesse
- **Scalabilità:** Design supporta fino a 1000 tenant senza modifiche architetturali, con opportune partizioni PostgreSQL se necessario (v2.0+)
- **Dev time:** +2-3 settimane vs hardcoded, ma -4 settimane a long-term per customizzazioni client

---

## Data Model — Nuove Tabelle

### M1: Origini Contatti

#### **crm_contact_origins**
Definisce i canali di acquisizione custom per tenant (es. "LinkedIn Sales", "Referral", "Evento", "Cold Email")

| Campo | Tipo | Constraint | Descrizione |
|-------|------|-----------|-------------|
| id | UUID PRIMARY KEY | - | ID univoco |
| tenant_id | UUID FK (tenants) | NOT NULL | Multi-tenancy |
| code | VARCHAR(50) | NOT NULL, UNIQUE (tenant_id, code) | Codice interno univoco per tenant (es. "linkedin_dm") |
| label | VARCHAR(255) | NOT NULL | Etichetta UX (es. "LinkedIn DM") |
| parent_channel | VARCHAR(50) | NULLABLE | Canale padre per raggruppamento (es. "social", "direct", "event") |
| icon_name | VARCHAR(100) | NULLABLE | Nome icona Tailwind (es. "icon-linkedin", "icon-referral") |
| is_active | BOOLEAN | DEFAULT true | Soft delete logico |
| metadata | JSONB | NULLABLE | Custom fields futuri (es. rate_limit, api_config) |
| created_at | TIMESTAMP | DEFAULT now() | Audit |
| updated_at | TIMESTAMP | DEFAULT now() | Audit |

**Indici:**
- `(tenant_id, code)` UNIQUE
- `(tenant_id, is_active)` per dropdown speedup

**Seed data (esempio documentativo — in produzione usare il trigger `fn_seed_tenant_config()` definito in schema-pivot8.md):**
```sql
-- ESEMPIO: Non eseguire direttamente. Il trigger su INSERT tenants popola automaticamente.
INSERT INTO crm_contact_origins (tenant_id, code, label, parent_channel, icon_name, is_active) VALUES
('tenant-123', 'web_form', 'Web Form', 'direct', 'icon-globe', true),
('tenant-123', 'linkedin_organic', 'LinkedIn Organico', 'social', 'icon-linkedin', true),
('tenant-123', 'linkedin_dm', 'LinkedIn DM', 'social', 'icon-linkedin', true),
('tenant-123', 'referral', 'Referral', 'direct', 'icon-users', true),
('tenant-123', 'event', 'Evento/Conferenza', 'event', 'icon-calendar', true),
('tenant-123', 'cold_outreach', 'Cold Email', 'direct', 'icon-mail', true);
```

---

### M2: Attività Custom e Pre-funnel

#### **crm_activity_types**
Tipi di attività custom tracciabili (es. "Inmail LinkedIn", "Commento Post", "Story View", "Call", "Email")

| Campo | Tipo | Constraint | Descrizione |
|-------|------|-----------|-------------|
| id | UUID PRIMARY KEY | - | ID univoco |
| tenant_id | UUID FK (tenants) | NOT NULL | Multi-tenancy |
| code | VARCHAR(50) | NOT NULL, UNIQUE (tenant_id, code) | Codice univoco per tenant |
| label | VARCHAR(255) | NOT NULL | Etichetta UX |
| category | VARCHAR(50) | NOT NULL, ENUM | Categoria: "sales", "marketing", "support" |
| counts_as_last_contact | BOOLEAN | DEFAULT false | Se true, aggiorna contact.last_contact_at |
| is_active | BOOLEAN | DEFAULT true | Soft delete |
| created_at | TIMESTAMP | DEFAULT now() | Audit |
| updated_at | TIMESTAMP | DEFAULT now() | Audit |

**Seed data (default):**
```sql
INSERT INTO crm_activity_types (tenant_id, code, label, category, counts_as_last_contact, is_active) VALUES
('tenant-123', 'call', 'Chiamata', 'sales', true, true),
('tenant-123', 'email', 'Email', 'sales', true, true),
('tenant-123', 'meeting', 'Incontro', 'sales', true, true),
('tenant-123', 'note', 'Nota', 'sales', false, true),
('tenant-123', 'task', 'Task/Reminder', 'sales', false, true),
('tenant-123', 'linkedin_inmail', 'Inmail LinkedIn', 'sales', true, true),
('tenant-123', 'linkedin_comment', 'Commento LinkedIn', 'marketing', true, true),
('tenant-123', 'linkedin_engagement', 'Engagement LinkedIn', 'marketing', true, true);
```

#### **Estensione: crm_pipeline_stages**
Nuovo campo per distinguere stadi pre-funnel dalla pipeline standard

| Campo | Tipo | Alter | Descrizione |
|-------|------|-------|-------------|
| stage_type | VARCHAR(50) | ADD COLUMN | ENUM: "pre_funnel", "pipeline". Default "pipeline". Stadi pre_funnel hanno sequence < first pipeline stage (es. "Nuovo Lead") |

---

### M3: Ruoli e Collaboratori Esterni

#### **crm_roles**
Ruoli custom con granular permessi (admin, commerciale, viewer, manager, fractional, etc.)

| Campo | Tipo | Constraint | Descrizione |
|-------|------|-----------|-------------|
| id | UUID PRIMARY KEY | - | ID univoco |
| tenant_id | UUID FK (tenants) | NOT NULL | Multi-tenancy |
| name | VARCHAR(255) | NOT NULL, UNIQUE (tenant_id, name) | Nome ruolo (es. "Account Executive") |
| description | TEXT | NULLABLE | Descrizione scopo |
| is_system_role | BOOLEAN | DEFAULT false | Se true, è un ruolo di sistema (owner, admin, viewer) — non modificabile |
| created_at | TIMESTAMP | DEFAULT now() | Audit |
| updated_at | TIMESTAMP | DEFAULT now() | Audit |

**Seed data (default):**
```sql
INSERT INTO crm_roles (tenant_id, name, description, is_system_role) VALUES
('tenant-123', 'Owner', 'Proprietario — accesso illimitato', true),
('tenant-123', 'Admin', 'Administrator — configura ruoli, utenti, audit', true),
('tenant-123', 'Sales Rep', 'Sales Representative — CRUD deal/contacts, limited export', false),
('tenant-123', 'Sales Manager', 'Sales Manager — view all, KPI, scorecard', false),
('tenant-123', 'Viewer', 'Read-only viewer', true);
```

#### **crm_role_permissions**
Matrice permessi per ruolo (RBAC fine-grained)

| Campo | Tipo | Constraint | Descrizione |
|-------|------|-----------|-------------|
| id | UUID PRIMARY KEY | - | ID univoco |
| tenant_id | UUID FK (tenants) | NOT NULL | Multi-tenancy |
| role_id | UUID FK (crm_roles) | NOT NULL | Role |
| entity | VARCHAR(50) | NOT NULL, ENUM | Entità: "contacts", "deals", "activities", "pipelines", "sequences", "reports", "audit_log", "settings" |
| permission | VARCHAR(50) | NOT NULL, ENUM | "create", "read", "update", "delete", "export", "view_all" |
| scope | VARCHAR(50) | DEFAULT "own_only" | ENUM: "own_only" (dati assegnati a user), "team" (team user), "all" (row-level security se applicato) |
| created_at | TIMESTAMP | DEFAULT now() | Audit |

**Indice:** `(tenant_id, role_id, entity, permission)` UNIQUE

**Seed data (default):**
```sql
-- Owner: tutti i permessi
INSERT INTO crm_role_permissions (tenant_id, role_id, entity, permission, scope)
SELECT id, (SELECT id FROM crm_roles WHERE name='Owner'), entity, permission, 'all'
FROM (
  SELECT DISTINCT 'contacts' as entity, 'create' as permission UNION
  SELECT 'contacts', 'read' UNION SELECT 'contacts', 'update' UNION SELECT 'contacts', 'delete' UNION SELECT 'contacts', 'export' UNION SELECT 'contacts', 'view_all' UNION
  SELECT 'deals', 'create' UNION SELECT 'deals', 'read' UNION SELECT 'deals', 'update' UNION SELECT 'deals', 'delete' UNION SELECT 'deals', 'export' UNION SELECT 'deals', 'view_all' UNION
  SELECT 'activities', 'create' UNION SELECT 'activities', 'read' UNION SELECT 'activities', 'update' UNION SELECT 'activities', 'delete' UNION
  SELECT 'reports', 'read' UNION SELECT 'reports', 'export' UNION
  SELECT 'audit_log', 'read' UNION SELECT 'audit_log', 'export' UNION
  SELECT 'settings', 'read' UNION SELECT 'settings', 'update'
) as perms
WHERE 'Owner' = (SELECT name FROM crm_roles WHERE id = role_id);

-- Sales Rep: limited
INSERT INTO crm_role_permissions (tenant_id, role_id, entity, permission, scope) VALUES
('tenant-123', (SELECT id FROM crm_roles WHERE name='Sales Rep'), 'contacts', 'create', 'own_only'),
('tenant-123', (SELECT id FROM crm_roles WHERE name='Sales Rep'), 'contacts', 'read', 'own_only'),
('tenant-123', (SELECT id FROM crm_roles WHERE name='Sales Rep'), 'contacts', 'update', 'own_only'),
('tenant-123', (SELECT id FROM crm_roles WHERE name='Sales Rep'), 'deals', 'create', 'own_only'),
('tenant-123', (SELECT id FROM crm_roles WHERE name='Sales Rep'), 'deals', 'read', 'own_only'),
('tenant-123', (SELECT id FROM crm_roles WHERE name='Sales Rep'), 'deals', 'update', 'own_only'),
('tenant-123', (SELECT id FROM crm_roles WHERE name='Sales Rep'), 'activities', 'create', 'own_only'),
('tenant-123', (SELECT id FROM crm_roles WHERE name='Sales Rep'), 'activities', 'read', 'own_only'),
('tenant-123', (SELECT id FROM crm_roles WHERE name='Sales Rep'), 'reports', 'read', 'own_only');
```

#### **Estensione: crm_users (users)**
Campi aggiunti per supportare utenti esterni e row-level security

| Campo | Tipo | Alter | Descrizione |
|-------|------|-------|-------------|
| user_type | VARCHAR(50) | ADD COLUMN | ENUM: "internal", "external", "admin". Default "internal". Utenti "external" hanno scadenza accesso |
| access_expires_at | TIMESTAMP | ADD COLUMN | Data scadenza accesso per utenti esterni. NULL = senza scadenza (internal/admin) |
| crm_role_id | UUID FK (crm_roles) | ADD COLUMN | Ruolo RBAC assegnato. Nullable (di default usa ruolo "Viewer" se NULL) |
| default_origin_id | UUID FK (crm_contact_origins) | ADD COLUMN | Canale default per pre-compilazione form (es. utente LinkedIn-only ha default="LinkedIn Sales") |
| default_product_id | UUID FK (crm_products) | ADD COLUMN | Prodotto default per pre-selezione deal |

**Migration:** Backfill `user_type='internal'` per utenti esistenti, `crm_role_id` con role "Admin" per tenant owner

---

#### **crm_audit_log**
Log immutabile di tutte le azioni utente (CRUD, login, export, permission denied)

| Campo | Tipo | Constraint | Descrizione |
|-------|------|-----------|-------------|
| id | UUID PRIMARY KEY | - | ID univoco |
| tenant_id | UUID FK (tenants) | NOT NULL | Multi-tenancy |
| user_id | UUID FK (users) | NOT NULL | Utente che ha eseguito l'azione |
| action | VARCHAR(100) | NOT NULL, ENUM | "create_contact", "update_contact", "delete_contact", "create_deal", "update_deal", "move_deal_stage", "log_activity", "export_csv", "login", "logout", "permission_denied", "bulk_update_origin", "calculate_compensation" |
| entity_type | VARCHAR(50) | NOT NULL, ENUM | "contact", "deal", "activity", "user", "role", "origin", "product", "compensation" |
| entity_id | UUID | NULLABLE | ID dell'entità affetta |
| entity_name | VARCHAR(255) | NULLABLE | Nome human-readable (es. "ACME Corp" per contact_id=123) |
| change_details | JSONB | NULLABLE | Diff prima/dopo (es. {"from": {"stage": "Prospect"}, "to": {"stage": "Qualificato"}}) |
| ip_address | INET | NULLABLE | IP client (da X-Forwarded-For header) |
| user_agent | TEXT | NULLABLE | User-Agent browser |
| status | VARCHAR(50) | DEFAULT "success" | ENUM: "success", "error", "denied" |
| error_message | TEXT | NULLABLE | Messaggio errore se status != success |
| created_at | TIMESTAMP | DEFAULT now() | Timestamp immutabile |

**Indici:**
- `(tenant_id, created_at DESC)` per audit trail ordinato
- `(tenant_id, user_id, created_at DESC)` per filtrare per utente
- `(tenant_id, entity_type, entity_id)` per trovare tutte le azioni su un'entità

**Immutabilità DB:**
```sql
CREATE OR REPLACE FUNCTION fn_audit_log_prevent_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Audit log cannot be updated or deleted. Action: %', TG_OP;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trig_audit_log_immutable
BEFORE UPDATE OR DELETE ON crm_audit_log
FOR EACH ROW
EXECUTE FUNCTION fn_audit_log_prevent_modification();
```
**NOTA:** Nome unificato con schema-pivot8.md: `fn_audit_log_prevent_modification` + `trig_audit_log_immutable`.

---

### M4: Catalogo Prodotti

#### **crm_products**
Catalogo prodotti/servizi vendibili (Sviluppo Custom, Supporto SLA, Hosting, Training, etc.)

| Campo | Tipo | Constraint | Descrizione |
|-------|------|-----------|-------------|
| id | UUID PRIMARY KEY | - | ID univoco |
| tenant_id | UUID FK (tenants) | NOT NULL | Multi-tenancy |
| name | VARCHAR(255) | NOT NULL | Nome prodotto (es. "Sviluppo Custom Backend") |
| code | VARCHAR(50) | NOT NULL, UNIQUE (tenant_id, code) | Codice univoco per tenant |
| category_id | UUID FK (crm_product_categories) | NULLABLE | Categoria prodotto |
| pricing_model | VARCHAR(50) | NOT NULL, ENUM | "fixed" (price fisso), "hourly" (€/ora), "custom" (negoziato caso-per-caso) |
| base_price | NUMERIC(12, 2) | NULLABLE | Prezzo base per fixed/hourly |
| hourly_rate | NUMERIC(10, 2) | NULLABLE | €/ora se pricing_model=hourly |
| estimated_duration_days | INTEGER | NULLABLE | Stima gg default per hourly (es. 20gg) |
| technology_type | VARCHAR(50) | NULLABLE | Tipo tecn. se hourly (es. "frontend", "backend", "mobile") |
| target_margin_percent | NUMERIC(5, 2) | NULLABLE | Margine target % per margin analysis (es. 35%) |
| description | TEXT | NULLABLE | Descrizione commerciale |
| is_active | BOOLEAN | DEFAULT true | Soft delete |
| created_at | TIMESTAMP | DEFAULT now() | Audit |
| updated_at | TIMESTAMP | DEFAULT now() | Audit |

**Indici:**
- `(tenant_id, code)` UNIQUE
- `(tenant_id, is_active)` per dropdown

#### **crm_product_categories**
Categorie di raggruppamento prodotti (Sviluppo, Supporto, Infra, Training, etc.)

| Campo | Tipo | Constraint | Descrizione |
|-------|------|-----------|-------------|
| id | UUID PRIMARY KEY | - | ID univoco |
| tenant_id | UUID FK (tenants) | NOT NULL | Multi-tenancy |
| name | VARCHAR(255) | NOT NULL | Nome categoria |
| is_active | BOOLEAN | DEFAULT true | Soft delete |
| created_at | TIMESTAMP | DEFAULT now() | Audit |

**Indice:** `(tenant_id, name)` UNIQUE

#### **crm_deal_products**
Pivot table: associa prodotti a deal con quantità e prezzo override

| Campo | Tipo | Constraint | Descrizione |
|-------|------|-----------|-------------|
| id | UUID PRIMARY KEY | - | ID univoco |
| tenant_id | UUID FK (tenants) | NOT NULL | Multi-tenancy |
| deal_id | UUID FK (crm_deals) | NOT NULL | Deal |
| product_id | UUID FK (crm_products) | NOT NULL | Prodotto |
| quantity | NUMERIC(10, 2) | DEFAULT 1 | Quantità (es. 1 per fixed, 12 per monthly support) |
| price_override | NUMERIC(12, 2) | NULLABLE | Prezzo override negoziato (NULL = usa base_price da product) |
| notes | TEXT | NULLABLE | Note linea (es. "Fase 1 di 2") |
| created_at | TIMESTAMP | DEFAULT now() | Audit |

**Indice:** `(tenant_id, deal_id)` per query rapide sui prodotti del deal. **Nessun UNIQUE su (deal_id, product_id)** — lo stesso prodotto può apparire su più righe (fasi diverse, lotti). Vedi AC-114.4.

**Computed column (view o calcolato in service):**
- `line_total = CASE WHEN price_override IS NOT NULL THEN price_override * quantity ELSE product.base_price * quantity END`
- `deal_total_revenue = SUM(line_total)` per tutti i prodotti del deal

---

### M5: Analytics e Compensi

#### **crm_dashboard_widgets**
Configurazione widget KPI personalizzabili per dashboard

| Campo | Tipo | Constraint | Descrizione |
|-------|------|-----------|-------------|
| id | UUID PRIMARY KEY | - | ID univoco |
| tenant_id | UUID FK (tenants) | NOT NULL | Multi-tenancy |
| name | VARCHAR(255) | NOT NULL | Nome dashboard (es. "Q1 2026 Pipeline") |
| dashboard_layout | JSONB | NOT NULL, validato da Pydantic `DashboardLayoutSchema` | Configurazione JSON schema (vedi sotto). **Validazione API:** ogni widget deve avere widget_id, type, title, period. CHECK DB: `jsonb_typeof(dashboard_layout) = 'object'` |
| created_by | UUID FK (users) | NOT NULL | Utente che ha creato |
| is_shared | BOOLEAN | DEFAULT false | Se true, visibile a tutto il team |
| created_at | TIMESTAMP | DEFAULT now() | Audit |
| updated_at | TIMESTAMP | DEFAULT now() | Audit |

**Esempio dashboard_layout JSON:**
```json
{
  "layout": [
    {
      "widget_id": "w1",
      "type": "revenue_mom",
      "title": "Revenue MoM",
      "period": "last_3_months",
      "filters": {
        "product_id": "prod-123",
        "origin_id": null,
        "user_id": null
      },
      "position": {"row": 0, "col": 0, "width": 6, "height": 4}
    },
    {
      "widget_id": "w2",
      "type": "deal_count",
      "title": "Deal Count by Stage",
      "period": "current_month",
      "filters": {},
      "position": {"row": 0, "col": 6, "width": 6, "height": 4}
    },
    {
      "widget_id": "w3",
      "type": "win_rate",
      "title": "Win Rate %",
      "period": "ytd",
      "filters": {"user_id": "user-456"},
      "position": {"row": 4, "col": 0, "width": 6, "height": 3}
    }
  ]
}
```

**Widget presets:**
- `revenue_mom` — Revenue per mese (line chart)
- `deal_count` — Num deal per stage (stacked bar)
- `win_rate` — % deal chiusi / totali (gauge)
- `avg_deal_size` — Revenue media (KPI card)
- `pipeline_by_stage` — Pipeline Kanban o tabella
- `forecast` — Forecast revenue prossimi 90gg
- `top_contacts` — Top 10 contatti per revenue
- `activity_heatmap` — Attività per giorno/ora
- `scorecard` — Aggregazione metriche user

#### **crm_compensation_rules**
Regole per calcolo compensi (provvigioni, bonus, penalità)

| Campo | Tipo | Constraint | Descrizione |
|-------|------|-----------|-------------|
| id | UUID PRIMARY KEY | - | ID univoco |
| tenant_id | UUID FK (tenants) | NOT NULL | Multi-tenancy |
| name | VARCHAR(255) | NOT NULL | Nome regola (es. "Base Commission 5%") |
| trigger | VARCHAR(50) | NOT NULL, ENUM | "deal_won", "revenue_threshold", "activity_count", "quarterly", "custom" |
| calculation_method | VARCHAR(50) | NOT NULL, ENUM | "percent_revenue" (%), "fixed_amount" (€), "tiered" (tier progressivi). **NOTA: "formula" rimossa per MVP — richiede sandbox safe-eval, rimandata a v2** |
| base_config | JSONB | NOT NULL | Configurazione calcolo (vedi sotto) |
| conditions | JSONB | NULLABLE | Condizioni trigger (prodotto, canale, user, date range) |
| priority | INTEGER | DEFAULT 0 | Ordine applicazione (0=first, higher=later) |
| is_active | BOOLEAN | DEFAULT true | Attiva/disattiva |
| created_by | UUID FK (users) | NOT NULL | Utente che ha creato |
| created_at | TIMESTAMP | DEFAULT now() | Audit |
| updated_at | TIMESTAMP | DEFAULT now() | Audit |

**Esempio base_config JSON (percent_revenue):**
```json
{
  "method": "percent_revenue",
  "rate": 5.0,
  "description": "5% su revenue chiusa"
}
```

**Esempio base_config JSON (tiered):**
```json
{
  "method": "tiered",
  "tiers": [
    {"min": 0, "max": 50000, "rate": 5.0},
    {"min": 50000, "max": 100000, "rate": 7.0},
    {"min": 100000, "max": null, "rate": 10.0}
  ],
  "description": "5% 0-50k, 7% 50-100k, 10% >100k"
}
```

**Esempio conditions JSON:**
```json
{
  "product_ids": ["prod-123", "prod-456"],
  "origin_ids": ["origin-linkedin"],
  "user_ids": ["user-111"],
  "min_revenue": 50000,
  "start_date": "2026-01-01",
  "end_date": "2026-12-31"
}
```

#### **crm_compensation_entries**
Risultato calcolo compensi mensili per user

| Campo | Tipo | Constraint | Descrizione |
|-------|------|-----------|-------------|
| id | UUID PRIMARY KEY | - | ID univoco |
| tenant_id | UUID FK (tenants) | NOT NULL | Multi-tenancy |
| user_id | UUID FK (users) | NOT NULL | User |
| month | DATE | NOT NULL | Primo giorno del mese (es. 2026-03-01) |
| amount_gross | NUMERIC(12, 2) | NOT NULL | Importo lordo compenso in € |
| rules_applied | JSONB | NOT NULL | Dettaglio quale regola ha contribuito quanto (vedi sotto) |
| deal_contributions | JSONB | NULLABLE | Breakdown per deal: deal_id → contribution amount |
| status | VARCHAR(50) | DEFAULT "draft" | ENUM: "draft" (calcolato, non confermato), "confirmed" (confermato), "paid" (pagato), "error" (conflitto/errore) |
| error_message | TEXT | NULLABLE | Messaggio errore se status=error |
| created_at | TIMESTAMP | DEFAULT now() | Auto-generato da job |
| created_by | VARCHAR(100) | DEFAULT 'system' | Chi ha creato (system o user per correzioni manuali) |
| confirmed_at | TIMESTAMP | NULLABLE | Quando confermato |
| paid_at | TIMESTAMP | NULLABLE | Quando marcato pagato |

**Esempio rules_applied JSON:**
```json
{
  "applied_rules": [
    {
      "rule_id": "rule-123",
      "rule_name": "Base Commission 5%",
      "contribution": 2500.00,
      "details": {
        "method": "percent_revenue",
        "base_revenue": 50000,
        "rate": 5.0
      }
    },
    {
      "rule_id": "rule-456",
      "rule_name": "Product Bonus +2% su Sviluppo",
      "contribution": 1000.00,
      "details": {
        "method": "percent_revenue",
        "filtered_revenue": 50000,
        "product_ids": ["prod-123"],
        "rate": 2.0
      }
    }
  ],
  "total_amount": 3500.00
}
```

**Indici:**
- `(tenant_id, month, user_id)` UNIQUE
- `(tenant_id, status)` per query draft/confirmed/paid

---

## Estensioni Tabelle Esistenti

### crm_contacts
| Campo | Alter | Descrizione |
|-------|-------|-------------|
| origin_id | ADD COLUMN UUID FK (crm_contact_origins) | Origine contatto (canale acquisizione). NOT NULL with default migration |

**Migration:** Backfill da campo `source` string → origin_id FK, creando automaticamente origini per valori unici di source

### crm_deals
| Campo | Alter | Descrizione |
|-------|-------|-------------|
| deal_type | MODIFY ENUM | Aggiungere nuovi valori: "subscription" (ricorrente), "mixed" (una tantum + ricorrente). Esistenti: "T&M" (time & materials), "fixed" (prezzo fisso), "spot" (occasionale), "hardware" |

---

## Business Rules

### BR-P8.1: Origine Obbligatoria su Contatto
**Regola:** Ogni contatto DEVE avere un'origine assegnata (NOT NULL), selezionata da lista origini attive del tenant
**Verifica:** Validazione form + constraint DB
**Story:** US-103.2 (AC)

### BR-P8.2: Codice Origine Univoco per Tenant
**Regola:** Campo `crm_contact_origins.code` UNIQUE per coppia (tenant_id, code)
**Verifica:** UNIQUE constraint DB + validazione API 409
**Story:** US-100.2, US-101

### BR-P8.3: Tipo Attività Richiesto
**Regola:** Ogni attività loggata DEVE avere un tipo da `crm_activity_types` attivo
**Comportamento:** Se tipo ha `counts_as_last_contact=true`, aggiorna `contact.last_contact_at` al timestamp dell'attività
**Verifica:** Validazione form + trigger DB
**Story:** US-107.2, AC-104.3

### BR-P8.4: Soft Delete per Origini e Prodotti
**Regola:** Origini e Prodotti con dati associati (contatti/deal) NON possono essere hard-deleted, solo soft-deleted (is_active=false)
**Comportamento:** Disattivare = is_active=false, rimane storico intatto, non appare in dropdown new/edit form
**Verifica:** Trigger/constraint che nega DELETE, API 409 se tentato hard delete
**Story:** US-101.2, US-113.2

### BR-P8.5: Ruoli di Sistema Non Modificabili
**Regola:** Ruoli con `is_system_role=true` (Owner, Admin, Viewer) NON possono essere modificati/cancellati
**Verifica:** Constraint DB + API check
**Story:** US-108

### BR-P8.6: RBAC Granulare con Row-Level Security
**Regola:** Validazione permessi su ogni azione:
1. **Scope "own_only":** User vede solo dati assegnati a loro (contact.assigned_to=user_id oppure deal.assigned_to=user_id)
2. **Scope "team":** User vede dati del team
3. **Scope "all":** User vede tutti i dati (row-level security può essere ulteriormente limitato se utente esterno ha canale default)
4. **External users con canale default:** Row-level filtering obbligatorio — vedono SOLO contatti/deal con origin_id=default_origin_id

**Verifica:** Middleware che intercetta ogni endpoint, verifica permessi su (action, entity_type), applica filtri SQL
**Story:** US-108.3, US-108.4, US-110

### BR-P8.7: Audit Log Immutabile
**Regola:** Ogni azione su entità (create, update, delete, login, export, permission denied) è registrata in `crm_audit_log` con trigger immutabilità (no update/delete)
**Dettagli registrati:** user_id, action, entity_type, entity_id, change_details (JSON diff), ip_address, user_agent, status (success/error/denied)
**Verifica:** Trigger DB che nega UPDATE/DELETE su audit_log
**Story:** US-111

### BR-P8.8: Scadenza Accesso per Utenti Esterni
**Regola:** Utenti con `user_type='external'` e `access_expires_at < NOW()` sono automaticamente disattivati (is_active=false)
**Trigger:** Job notturna (cron) che verifica scadenze e aggiorna is_active
**Middleware:** Login fallisce se access_expires_at < NOW()
**Verifica:** Validazione form che richiede access_expires_at > NOW() per utenti external
**Story:** US-109

### BR-P8.9: M2M Deal-Prodotto Obbligatorio
**Regola:** Ogni deal DEVE avere almeno 1 prodotto associato in `crm_deal_products` (non può avere 0 prodotti)
**Revenue calculation:** deal.expected_revenue = SUM(crm_deal_products.line_total per tutti i prodotti) dove line_total = (price_override ?? product.base_price) * quantity
**Verifica:** Trigger DB che nega DELETE se ultimo prodotto, validazione form
**Story:** US-114.3

### BR-P8.10: Prodotto Disattivato Rimane Associato
**Regola:** Se un prodotto è disattivato (is_active=false), deal già creati rimangono associati (storico immutabile), ma il prodotto non appare nei dropdown per nuovi deal
**Verifica:** Query dropdown filtra `is_active=true`, join query di analytics non esclude disattivati (storico)
**Story:** US-113.2

### BR-P8.11: Compensi Calcolati Automaticamente da Job
**Regola:** Job notturna (schedulato al 1° di ogni mese o configurabile) calcola compensi di mese precedente per tutti gli user attivi, applicando regole in ordine di priorità
**Logica:** Per ogni user, esegui:
```
1. Aggrega deal chiusi (is_won=true) nel mese con user_id=assigned_to
2. Per ogni deal, somma revenue (crm_deal_products.line_total)
3. Applica rules in ordine di priorità, valutando conditions
4. Se rule è applicabile, calcola contribution (percent/fixed/tiered)
5. Aggrega tutte le contributions per total
6. Crea crm_compensation_entries con status='draft'
7. Se conflitto (due regole incompatibili), status='error' + notifica admin
```
**Verifica:** Log nella job, notifica admin, entità creata con status=draft (admin conferma prima di pagare)

**Ottimizzazione performance:** Pre-aggregare deal revenue per user con una singola CTE anziché query N+1:
```sql
WITH user_revenue AS (
    SELECT d.assigned_to AS user_id, d.tenant_id,
           SUM(dp.quantity * COALESCE(dp.price_override, p.base_price)) AS total_revenue,
           COUNT(d.id) AS deal_count,
           json_agg(json_build_object('deal_id', d.id, 'revenue', ...)) AS deal_details
    FROM crm_deals d
    JOIN crm_deal_products dp ON dp.deal_id = d.id
    JOIN crm_products p ON p.id = dp.product_id
    WHERE d.is_won = true AND d.closed_at BETWEEN :month_start AND :month_end
    GROUP BY d.assigned_to, d.tenant_id
)
SELECT * FROM user_revenue;
```
Poi applicare le regole in-memory per user.
**Indice consigliato:** `CREATE INDEX idx_crm_deals_comp_calc ON crm_deals(tenant_id, assigned_to, is_won, closed_at);`

**Story:** US-118, US-119

### BR-P8.12: Compensi Non Retroattivi di Default
**Regola:** Se aggiungi una regola nuova a metà mese, applica solo ai deal che chiudono da quel punto in poi. Per recalcolare mesi passati, admin DEVE eseguire "Recalculate" manualmente con conferma
**Verifica:** Storico compensi precedenti non è sovrascritto, sono create nuove entry in crm_compensation_entries con timestamp creazione
**Story:** US-119.4

---

## Security

### Autenticazione e Autorizzazione
- **JWT + Bearer token** per API (come attuale)
- **RBAC granulare** via matrice permessi in `crm_role_permissions` (vedi BR-P8.6)
- **Row-level security** per utenti esterni con `default_origin_id` (vedono solo dati di quel canale)
- **Middleware RBAC** che intercetta ogni endpoint `/api/v1/crm/*`, verifica `(user.crm_role_id → permessi, entity, action)`, applica filtri SQL

### Audit e Compliance
- **Immutable audit log** in `crm_audit_log` (trigger DB che nega UPDATE/DELETE)
- **Tracciamento azioni:** CRUD, login, logout, export CSV, permission_denied
- **GDPR compliance:** Log retention per 90 gg (configurabile), export audit su richiesta
- **Signature digitale** su export CSV (hash SHA256 per integrità)

### Input Validation
- **Pydantic schemas** per validazione request body (come attuale)
- **Max length su stringhe:** codice origine/tipo max 50 char, etichetta max 255 char
- **Enum validation** su campi: user_type, stage_type, pricing_model, etc.
- **FK validation:** Verifica che origin_id/product_id/role_id appartengono al tenant loggato

### Rate Limiting
- **General API:** 1000 req/min per authenticated user (come attuale)
- **Export endpoint:** 10 export/min per user (limita bulk CSV export abuse)

### Data Protection
- **Password:** bcrypt (come attuale)
- **Sensibili:** Sconti negoziati in deal, revenue forecast criptati a rest (future v2)
- **CORS:** Configurato per domain specifico del frontend

---

## API Endpoints — Pivot 8

### M1: Gestione Origini

#### **GET /api/v1/crm/origins**
**Scopo:** Elenco origini contatti del tenant
**Auth:** JWT, permesso read su "contacts"
**Query params:**
- `is_active` (bool, optional): filtro stato
- `parent_channel` (str, optional): filtro canale padre

**Response 200:**
```json
{
  "data": [
    {
      "id": "uuid",
      "tenant_id": "uuid",
      "code": "linkedin_dm",
      "label": "LinkedIn DM",
      "parent_channel": "social",
      "icon_name": "icon-linkedin",
      "is_active": true,
      "contact_count": 42,
      "created_at": "2026-03-15T10:00:00Z",
      "updated_at": "2026-03-15T10:00:00Z"
    }
  ],
  "meta": {"total": 8, "page": 1, "limit": 50}
}
```

**Story:** US-100, US-101

---

#### **POST /api/v1/crm/origins**
**Scopo:** Crea nuova origine
**Auth:** JWT, admin only (crm_role: permesso create su "contacts" + is_system_role check)
**Request body:**
```json
{
  "code": "event_webinar",
  "label": "Webinar B2B",
  "parent_channel": "event",
  "icon_name": "icon-calendar",
  "is_active": true
}
```

**Response 201:**
```json
{
  "id": "uuid",
  "code": "event_webinar",
  "label": "Webinar B2B",
  "parent_channel": "event",
  "icon_name": "icon-calendar",
  "is_active": true,
  "created_at": "2026-04-04T12:00:00Z"
}
```

**Response 400:** Codice duplicato
**Response 403:** Insufficiente permesso

**Story:** US-100

---

#### **PATCH /api/v1/crm/origins/{origin_id}**
**Scopo:** Modifica origine (codice read-only)
**Auth:** JWT, admin only
**Request body:**
```json
{
  "label": "Webinar Aggiornato",
  "parent_channel": "event",
  "is_active": false
}
```

**Response 200:** Origin aggiornata
**Response 409:** Tentativo di modificare codice

**Story:** US-101

---

#### **POST /api/v1/crm/contacts/{contact_id}/change-origin**
**Scopo:** Cambia origine a un contatto (bulk action)
**Auth:** JWT, permesso update su "contacts"
**Request body:**
```json
{
  "new_origin_id": "uuid",
  "contact_ids": ["uuid1", "uuid2", "uuid3"]
}
```

**Response 200:** Bulk update completato
**Audit:** Registra bulk_update_origin per ogni contact

**Story:** US-103.3

---

### M2: Gestione Attività Custom

#### **GET /api/v1/crm/activity-types**
**Scopo:** Elenco tipi attività
**Auth:** JWT, read su "activities"
**Query params:**
- `is_active` (bool): filtro
- `category` (str): filtro categoria

**Response 200:** Lista tipi attività con count utilizzi

**Story:** US-104, US-105

---

#### **POST /api/v1/crm/activity-types**
**Scopo:** Crea tipo attività
**Auth:** JWT, admin only
**Request body:**
```json
{
  "code": "linkedin_poll",
  "label": "LinkedIn Poll Vote",
  "category": "marketing",
  "counts_as_last_contact": true
}
```

**Response 201:** Tipo creato

**Story:** US-104

---

#### **PATCH /api/v1/crm/activity-types/{type_id}**
**Scopo:** Modifica tipo (codice read-only)
**Auth:** JWT, admin only

**Story:** US-105

---

#### **GET /api/v1/crm/pipeline/stages**
**Scopo:** Elenco stadi pipeline con stage_type (pre_funnel vs pipeline)
**Auth:** JWT, read

**Response 200:**
```json
{
  "data": [
    {
      "id": "uuid",
      "name": "Prospect",
      "sequence": 1,
      "stage_type": "pre_funnel",
      "probability": 10,
      "color": "#CCCCCC",
      "is_active": true
    },
    {
      "id": "uuid",
      "name": "Nuovo Lead",
      "sequence": 3,
      "stage_type": "pipeline",
      "probability": 20,
      "color": "#FF0000"
    }
  ]
}
```

**Story:** US-106

---

#### **POST /api/v1/crm/pipeline/stages**
**Scopo:** Crea stadio pre-funnel o pipeline
**Auth:** JWT, admin only
**Request body:**
```json
{
  "name": "Contatto Qualificato",
  "sequence": 2,
  "probability": 15,
  "color": "#00FF00",
  "stage_type": "pre_funnel",
  "is_active": true
}
```

**Validazione:** Se stage_type='pre_funnel', sequence DEVE essere < sequence di first pipeline stage (es. "Nuovo Lead")
**Response 201:** Stadio creato

**Story:** US-106

---

#### **PATCH /api/v1/crm/pipeline/stages/{stage_id}**
**Scopo:** Modifica stadio pipeline (nome, probabilità, colore, is_active)
**Auth:** JWT, admin only
**Request body:**
```json
{
  "name": "Prospect Qualificato",
  "probability": 20,
  "color": "#00AAFF",
  "is_active": true
}
```

**Validazione:** Non è possibile cambiare stage_type dopo creazione. Se stage_type='pre_funnel', sequence deve restare < first pipeline stage.
**Response 200:** Stadio aggiornato

**Story:** US-106

---

#### **PUT /api/v1/crm/pipeline/stages/reorder**
**Scopo:** Riordina stadi pipeline (drag-and-drop)
**Auth:** JWT, admin only
**Request body:**
```json
{
  "stage_order": [
    {"stage_id": "uuid1", "sequence": 1},
    {"stage_id": "uuid2", "sequence": 2},
    {"stage_id": "uuid3", "sequence": 3}
  ]
}
```

**Validazione:** Tutti gli stadi pre_funnel devono avere sequence < tutti gli stadi pipeline.
**Response 200:** Ordine aggiornato

**Story:** US-106

---

#### **POST /api/v1/crm/activities**
**Scopo:** Crea attività per contatto o deal
**Auth:** JWT, create su "activities"
**Request body:**
```json
{
  "type_id": "uuid",
  "subject": "Inmail ricevuta",
  "description": "Risposta positiva, interessa collaborazione",
  "contact_id": "uuid",
  "deal_id": "uuid (optional)",
  "occurred_at": "2026-04-04T14:30:00Z",
  "status": "completed"
}
```

**Logica:** Se activity.type.counts_as_last_contact=true → aggiorna contact.last_contact_at
**Response 201:** Attività creata

**Story:** US-107

---

### M3: Gestione Ruoli e Utenti Esterni

#### **GET /api/v1/crm/roles**
**Scopo:** Elenco ruoli del tenant
**Auth:** JWT, admin only

**Response 200:**
```json
{
  "data": [
    {
      "id": "uuid",
      "name": "Owner",
      "description": "...",
      "is_system_role": true,
      "permissions": {
        "contacts": ["create", "read", "update", "delete", "export", "view_all"],
        "deals": ["create", "read", "update", "delete", "export", "view_all"],
        ...
      }
    }
  ]
}
```

**Story:** US-108

---

#### **POST /api/v1/crm/roles**
**Scopo:** Crea ruolo custom
**Auth:** JWT, admin only
**Request body:**
```json
{
  "name": "Account Executive",
  "description": "Gestisce pipeline e scorecard per il suo book",
  "permissions": {
    "contacts": ["create", "read", "update", "view_all"],
    "deals": ["create", "read", "update", "view_all", "export"],
    "activities": ["create", "read"],
    "reports": ["read", "export"],
    "pipelines": ["read"],
    "settings": []
  }
}
```

**Validazione:** Matrice permessi vs entità/azioni allowed (enum)
**Response 201:** Ruolo creato

**Story:** US-108

---

#### **DELETE /api/v1/crm/roles/{role_id}**
**Scopo:** Elimina ruolo custom
**Auth:** JWT, admin only
**Validazione:**
- Non è possibile eliminare ruoli di sistema (`is_system_role = true`) → 403 Forbidden
- Non è possibile eliminare ruoli con utenti assegnati → 409 Conflict con messaggio "Ruolo ha N utenti assegnati. Riassegnarli prima di eliminare."

**Response 204:** Ruolo eliminato
**Response 403:** Ruolo di sistema
**Response 409:** Ruolo con utenti assegnati

**Story:** US-108

---

#### **GET /api/v1/users?role_filter=external**
**Scopo:** Elenco utenti (con filtro tipo)
**Auth:** JWT, admin only

**Response 200:**
```json
{
  "data": [
    {
      "id": "uuid",
      "email": "contractor@example.com",
      "name": "Marco Contractor",
      "user_type": "external",
      "access_expires_at": "2026-06-01T23:59:59Z",
      "crm_role_id": "uuid",
      "crm_role_name": "Sales Rep",
      "default_origin_id": "uuid",
      "default_origin_label": "LinkedIn Sales",
      "default_product_id": "uuid (optional)",
      "is_active": true,
      "created_at": "2026-03-15T00:00:00Z"
    }
  ]
}
```

**Story:** US-109

---

#### **POST /api/v1/users**
**Scopo:** Crea utente (interno o esterno)
**Auth:** JWT, admin only
**Request body:**
```json
{
  "email": "contractor@example.com",
  "name": "Marco Contractor",
  "user_type": "external",
  "access_expires_at": "2026-06-01T23:59:59Z",
  "crm_role_id": "uuid",
  "default_origin_id": "uuid",
  "default_product_id": "uuid (optional)"
}
```

**Logica:**
1. Valida access_expires_at > NOW() se user_type='external'
2. Crea user in DB con is_active=true
3. Invia email invito con link temporaneo per reset password

**Response 201:** User creato

**Story:** US-109

---

#### **PATCH /api/v1/users/{user_id}**
**Scopo:** Modifica utente (admin modifica, o self per alcuni campi)
**Auth:** JWT
**Request body (admin):**
```json
{
  "access_expires_at": "2026-09-01T23:59:59Z",
  "crm_role_id": "uuid",
  "default_origin_id": "uuid (non bypassabile da utente esterno)"
}
```

**Response 200:** Utente aggiornato
**Response 403:** Utente esterno non può modificare proprio default_origin_id

**Story:** US-110

---

#### **GET /api/v1/audit-log**
**Scopo:** Elenco audit log (admin/auditor only)
**Auth:** JWT, admin
**Query params:**
- `user_id` (uuid): filtro utente
- `action` (str): filtro azione
- `entity_type` (str): filtro entità
- `start_date`, `end_date` (date): range
- `limit`, `offset` (int): paginazione

**Response 200:**
```json
{
  "data": [
    {
      "id": "uuid",
      "timestamp": "2026-04-04T14:30:00Z",
      "user_id": "uuid",
      "user_email": "marco@azienda.it",
      "action": "create_contact",
      "entity_type": "contact",
      "entity_id": "uuid",
      "entity_name": "ACME Corp",
      "change_details": null,
      "status": "success",
      "ip_address": "192.168.1.100",
      "user_agent": "Mozilla/5.0..."
    }
  ],
  "meta": {"total": 342, "page": 1}
}
```

**Story:** US-111

---

#### **GET /api/v1/audit-log/export**
**Scopo:** Export audit log in CSV
**Auth:** JWT, admin con export=true
**Query params:** stesso di GET /audit-log

**Response 200:** CSV scaricato con header `Content-Disposition: attachment`
**Header:** `X-Signature-SHA256: <hash>` per verificare integrità

**Story:** US-111.4

---

### M4: Catalogo Prodotti

#### **GET /api/v1/crm/products**
**Scopo:** Elenco prodotti catalogo
**Auth:** JWT, read
**Query params:**
- `is_active` (bool): filtro
- `category_id` (uuid): filtro categoria
- `pricing_model` (str): filtro modello pricing

**Response 200:**
```json
{
  "data": [
    {
      "id": "uuid",
      "name": "Sviluppo Custom Backend",
      "code": "dev_backend",
      "category": "Sviluppo",
      "pricing_model": "hourly",
      "base_price": null,
      "hourly_rate": 85.00,
      "estimated_duration_days": 20,
      "technology_type": "backend",
      "target_margin_percent": 35.0,
      "is_active": true,
      "deal_count": 12
    }
  ]
}
```

**Story:** US-112

---

#### **POST /api/v1/crm/products**
**Scopo:** Crea prodotto
**Auth:** JWT, admin only
**Request body:**
```json
{
  "name": "Supporto SLA Annuale",
  "code": "support_sla",
  "category_id": "uuid (or null per create inline)",
  "pricing_model": "fixed",
  "base_price": 5000.00,
  "target_margin_percent": 50.0,
  "description": "Supporto tecnico 24/7 con SLA 4h"
}
```

**Validazione:** Codice unique per tenant
**Response 201:** Prodotto creato

**Story:** US-112

---

#### **PATCH /api/v1/crm/products/{product_id}**
**Scopo:** Modifica prodotto (codice read-only)
**Auth:** JWT, admin only

**Story:** US-113

---

#### **POST /api/v1/crm/deals/{deal_id}/products**
**Scopo:** Aggiungi prodotto a deal
**Auth:** JWT, update su "deals"
**Request body:**
```json
{
  "product_id": "uuid",
  "quantity": 1,
  "price_override": 55000.00,
  "notes": "Fase 1"
}
```

**Logica:** Crea row in crm_deal_products, aggiorna deal.expected_revenue (somma line_total)
**Response 201:** Prodotto aggiunto

**Story:** US-114

---

#### **DELETE /api/v1/crm/deals/{deal_id}/products/{product_id}**
**Scopo:** Rimuovi prodotto da deal
**Auth:** JWT, update su "deals"

**Validazione:** Deal DEVE avere almeno 1 prodotto (409 se ultimo)
**Response 204:** Rimosso

**Story:** US-114.3

---

#### **GET /api/v1/crm/deals?product_ids=uuid1,uuid2**
**Scopo:** Filtra pipeline deal per prodotto
**Auth:** JWT, read su "deals"
**Query params:**
- `product_ids` (csv): Prodotti da filtrare (OR logic)
- `stage_id`, `origin_id`, `user_id`: altri filtri

**Response 200:** Deal filtrati

**Story:** US-115

---

### M5: Analytics e Compensi

#### **GET /api/v1/crm/dashboards**
**Scopo:** Elenco dashboard create nel tenant
**Auth:** JWT, read

**Response 200:**
```json
{
  "data": [
    {
      "id": "uuid",
      "name": "Q1 2026 Pipeline",
      "created_by": "uuid",
      "is_shared": true,
      "created_at": "2026-01-15T00:00:00Z",
      "widget_count": 4
    }
  ]
}
```

**Story:** US-116

---

#### **POST /api/v1/crm/dashboards**
**Scopo:** Crea dashboard personalizzata
**Auth:** JWT
**Request body:**
```json
{
  "name": "Sales Pipeline Q2",
  "layout": [
    {
      "widget_id": "w1",
      "type": "revenue_mom",
      "title": "Revenue MoM",
      "period": "last_3_months",
      "filters": {
        "product_id": null,
        "origin_id": null,
        "user_id": null
      },
      "position": {"row": 0, "col": 0, "width": 6, "height": 4}
    }
  ],
  "is_shared": true
}
```

**Validazione:** Widget type vs schema allowed, periodo obbligatorio
**Response 201:** Dashboard creata

**Story:** US-116

---

#### **GET /api/v1/crm/dashboards/{dashboard_id}/data**
**Scopo:** Calcola e restituisce dati widget per rendering
**Auth:** JWT
**Query params:**
- `widget_ids` (csv, optional): widget specifici da calcolare

**Response 200:**
```json
{
  "widgets": {
    "w1": {
      "type": "revenue_mom",
      "title": "Revenue MoM",
      "data": [
        {"month": "2026-02", "revenue": 125000, "trend": 5.2},
        {"month": "2026-03", "revenue": 132000, "trend": 5.6},
        {"month": "2026-04", "revenue": 128000, "trend": -3.0}
      ]
    }
  }
}
```

**Logica:** Per ogni widget, calcola dal DB, applica filtri tenant + RBAC user
**Performance:** Cache result per 5 min se no filters, invalidate on deal update

**Story:** US-116

---

#### **GET /api/v1/crm/scorecard/{user_id}**
**Scopo:** Scorecard collaboratore con KPI
**Auth:** JWT, admin o self (per propria scorecard)
**Query params:**
- `period` (str): "last_30_days", "last_quarter", "ytd", "custom"
- `start_date`, `end_date` (date): se custom
- `product_ids` (csv): filtro prodotto

**Response 200:**
```json
{
  "user_id": "uuid",
  "user_name": "Marco Rossi",
  "period": "last_30_days",
  "metrics": {
    "deal_count": {
      "value": 5,
      "trend": 10.0,
      "trend_direction": "up",
      "target": null
    },
    "revenue_closed": {
      "value": 125000.00,
      "trend": 25.0,
      "trend_direction": "up",
      "target": 100000.00
    },
    "win_rate": {
      "value": 60.0,
      "trend": 5.0,
      "trend_direction": "up",
      "target": 50.0
    },
    "avg_days_to_close": {
      "value": 42,
      "trend": -10.0,
      "trend_direction": "down",
      "target": 30
    },
    "last_contact_date": {
      "value": "2026-04-03T15:30:00Z",
      "days_since": 1
    }
  }
}
```

**Story:** US-117

---

#### **GET /api/v1/crm/compensation-rules**
**Scopo:** Elenco regole compensi configurate
**Auth:** JWT, admin

**Response 200:**
```json
{
  "data": [
    {
      "id": "uuid",
      "name": "Base Commission 5%",
      "trigger": "deal_won",
      "calculation_method": "percent_revenue",
      "priority": 0,
      "is_active": true,
      "base_config": {"method": "percent_revenue", "rate": 5.0},
      "conditions": null
    }
  ]
}
```

**Story:** US-118

---

#### **POST /api/v1/crm/compensation-rules**
**Scopo:** Crea regola compensi
**Auth:** JWT, admin only
**Request body:**
```json
{
  "name": "Product Bonus Sviluppo +2%",
  "trigger": "deal_won",
  "calculation_method": "percent_revenue",
  "base_config": {
    "method": "percent_revenue",
    "rate": 2.0,
    "description": "+2% su revenue Sviluppo Custom"
  },
  "conditions": {
    "product_ids": ["prod-123"],
    "min_revenue": null
  },
  "priority": 1,
  "is_active": true
}
```

**Validazione:** Logica non-circolare (non referenzia se stessa indirettamente)
**Response 201:** Regola creata

**Story:** US-118

---

#### **GET /api/v1/crm/compensation/monthly**
**Scopo:** Elenco compensi mensili calcolati
**Auth:** JWT, admin
**Query params:**
- `month` (date, YYYY-MM-01): mese
- `status` (str): "draft", "confirmed", "paid", "error"
- `user_id` (uuid): filtro user

**Response 200:**
```json
{
  "data": [
    {
      "id": "uuid",
      "user_id": "uuid",
      "user_name": "Marco Rossi",
      "month": "2026-03-01",
      "deal_count": 3,
      "revenue_closed": 150000.00,
      "amount_gross": 3900.00,
      "rules_applied": {
        "applied_rules": [
          {
            "rule_id": "uuid",
            "rule_name": "Base Commission 5%",
            "contribution": 3500.00
          },
          {
            "rule_id": "uuid",
            "rule_name": "Product Bonus +2%",
            "contribution": 400.00
          }
        ],
        "total_amount": 3900.00
      },
      "status": "draft",
      "created_at": "2026-04-01T00:15:00Z"
    }
  ]
}
```

**Story:** US-119

---

#### **PATCH /api/v1/crm/compensation/monthly/{entry_id}/confirm**
**Scopo:** Conferma compenso (da "draft" a "confirmed")
**Auth:** JWT, admin

**Response 200:** Entry aggiornata, status="confirmed"
**Audit:** Log confirm_compensation

**Story:** US-120

---

#### **GET /api/v1/crm/compensation/monthly/export**
**Scopo:** Export compensi mensili in Excel/PDF
**Auth:** JWT, admin con export=true
**Query params:**
- `month` (date): mese da esportare
- `format` (str): "excel", "pdf"
- `status` (str, optional): filtro "confirmed", "paid"

**Response 200:** File scaricato (application/vnd.openxmlformats-officedocument.spreadsheetml.sheet o application/pdf)

**Story:** US-120

---

## Story → Endpoint Mapping

| US | Story | Endpoint (Method) | Dettagli |
|----|----|-----------|----------|
| US-100 | Admin definisce origine custom | POST /api/v1/crm/origins | Crea origine |
| US-100.1-4 | AC di US-100 | POST + GET /api/v1/crm/origins | Validazione, dropdown |
| US-101 | Admin modifica origine | PATCH /api/v1/crm/origins/{id} | Soft delete, read-only code |
| US-102 | Migrazione source → origin_id | (Schema only, no endpoint) | Alembic migration |
| US-103 | Assegnare origine a contact | POST /api/v1/contacts + POST .../contacts/{id}/change-origin | Bulk action |
| US-104 | Admin definisce tipo attività | POST /api/v1/crm/activity-types | CRUD |
| US-105 | Admin modifica tipo attività | PATCH /api/v1/crm/activity-types/{id} | Soft delete |
| US-106 | Admin definisce stadi pre-funnel | POST /api/v1/crm/pipeline/stages | stage_type, sequenza |
| US-107 | User logga attività | POST /api/v1/crm/activities | last_contact_at update |
| US-108 | Admin definisce ruolo RBAC | POST /api/v1/crm/roles | Matrice permessi |
| US-109 | Admin crea utente esterno | POST /api/v1/users | user_type=external, access_expires_at |
| US-110 | Assegna canale/prodotto default | PATCH /api/v1/users/{id} | default_origin_id, row-level filter |
| US-111 | Audit trail immutabile | GET /api/v1/audit-log + /api/v1/audit-log/export | Immutable trigger, signature |
| US-112 | Admin definisce prodotto | POST /api/v1/crm/products | Pricing models |
| US-113 | Admin modifica prodotto | PATCH /api/v1/crm/products/{id} | Soft delete, pricing snapshot |
| US-114 | Associa prodotti a deal | POST /api/v1/crm/deals/{id}/products | M2M, revenue calc |
| US-115 | Filtra pipeline per prodotto | GET /api/v1/crm/deals?product_ids=... | Query filter |
| US-116 | Admin crea dashboard KPI | POST /api/v1/crm/dashboards | Widget config JSON |
| US-117 | Scorecard collaboratore | GET /api/v1/crm/scorecard/{user_id} | KPI aggregation |
| US-118 | Admin configura modello compensi | POST /api/v1/crm/compensation-rules | Regole trigger, calcolo |
| US-119 | Calcolo compensi mensili | GET /api/v1/crm/compensation/monthly | Job + query |
| US-120 | Export e manage pagamento | PATCH .../compensation/.../confirm + GET .../export | Workflow conferma→pagamento |

---

## Performance e Caching

### Database Query Optimization
- **Indici strategici** su (tenant_id, is_active) per origini/prodotti/tipi attività
- **Denormalizzazione controllata:** contact_count in crm_contact_origins (aggiornato via trigger on INSERT/UPDATE/DELETE contact.origin_id)
- **Partitioning future (v2.0):** crm_audit_log partizionato per mese per query veloci su large datasets

### Caching Redis
- **Dashboard data:** Cache widget per 5 min, invalidate on deal/contact update
- **Role-permission cache:** 1 ora per ruolo (invalidate on role change)
- **Product list:** 1 ora (invalidate on product create/update)

### Query Patterns
```python
# RBAC check + row-level filter combinato (middleware)
async def get_contacts_with_rbac(user_id: str, tenant_id: str):
    user = await get_user(user_id)
    perms = await get_permissions(user.role_id, "contacts", "read")

    query = select(CrmContact).where(CrmContact.tenant_id == tenant_id)

    if perms.scope == "own_only":
        query = query.where(CrmContact.assigned_to == user_id)
    elif perms.scope == "team":
        team_ids = await get_team_members(user_id)
        query = query.where(CrmContact.assigned_to.in_(team_ids))

    # External user? Filter by origin
    if user.user_type == "external" and user.default_origin_id:
        query = query.where(CrmContact.origin_id == user.default_origin_id)

    return await db.execute(query)
```

---

## Testing Strategy

### Unit Tests
- **Models:** SQLAlchemy model validation, constraint checking
- **Services:** Business logic per origin CRUD, activity tracking, compensation calc
- **RBAC:** Permission matrix evaluation, scope logic

### Integration Tests
- **API endpoints:** Happy path + error cases per endpoint (400, 403, 409)
- **Migrations:** Data integrity post-migration source → origin_id
- **Audit log:** Immutability trigger test
- **Job scheduling:** Compensation calculation monthly job

### E2E Tests
- **Complete flow:** Create origin → create contact with origin → log activity → cascade to last_contact_at
- **RBAC enforcement:** External user cannot see different origin data
- **Compensation workflow:** Deal win → monthly job → confirmation → export

---

## Deployment Plan

### 1. Database Migrations (Alembic)
```
1. Create new tables: origins, activity_types, roles, role_permissions, audit_log, products, product_categories, deal_products, dashboard_widgets, compensation_rules, compensation_entries
2. Add columns to existing: users (user_type, access_expires_at, crm_role_id, default_origin_id, default_product_id), contacts (origin_id), pipeline_stages (stage_type), deals (deal_type enum extend)
3. Backfill: user_type='internal' for existing, crm_role_id with preset roles, seed default origins/activity_types/roles per tenant
4. Create indices, triggers (audit_log immutable, contact.last_contact_at update on activity)
```

### 2. Backend Code Changes (Python/FastAPI)
- **New routers:** `modules/crm/origins.py`, `modules/crm/activity_types.py`, `modules/crm/roles.py`, `modules/crm/products.py`, `modules/crm/analytics.py`, `modules/crm/compensation.py`
- **New services:** `services/crm_origin.py`, `services/crm_activity.py`, `services/crm_rbac.py`, `services/crm_compensation.py`
- **New schemas:** Pydantic DTO per ogni entità (CrmOriginCreate, CrmActivityTypeCreate, etc.)
- **Middleware RBAC:** `middleware/rbac_middleware.py` che intercetta richieste, verifica permessi, applica filtri
- **Jobs:** Celery task per calcolo compensi mensili (`tasks/monthly_compensation.py`)

### 3. Frontend Code Changes (React/TS)
- **Pages:** `/settings/origins`, `/settings/activities`, `/settings/roles`, `/settings/products`, `/analytics/dashboard`, `/analytics/compensation`
- **Components:** Form CRUD per origine, tipo attività, ruolo, prodotto; DashboardBuilder; CompensationTable
- **Stores (Zustand):** State per origini, ruoli, prodotti, dashboard config
- **API client:** `api/crm.ts` con funzioni GET/POST/PATCH per nuovi endpoint

### 4. Testing
- Unit test: 60+ test case per services RBAC, compensation calc, data integrity
- Integration test: 40+ endpoint test
- E2E test: 5+ critical user journey (setup origin → create contact → log activity, create compensation rule → monthly calc)

### 5. Deployment
- **Staging:** Esegui migration su staging DB, test e2e su staging env
- **Production:** Zero-downtime deploy con blue-green (Railway supports)
  - Deploy backend con feature flags OFF per nuovi endpoint
  - Esegui migration
  - Enable feature flags
  - Frontend deploy
- **Rollback:** Migration down script disponibile (reversibile fino a 30 gg, poi manual)

---

## Timeline Stima

| Fase | Durata | Chi |
|------|--------|-----|
| Database design & migration scripts | 3-4 gg | Backend Architect + DB Expert |
| Backend API implementation (7 router + 7 service) | 10-12 gg | Backend Dev (1-2 pers) |
| Frontend pages & components | 8-10 gg | Frontend Dev (1-2 pers) |
| Testing (unit + integration + e2e) | 5-7 gg | QA + Dev |
| Documentation & deployment prep | 2-3 gg | Architect |
| **TOTAL** | **30-40 gg** | ~3 week sprint (2 dev) |

---

## ADR Cross-References

- **ADR-001:** Python + FastAPI per backend — confermato
- **ADR-008:** Odoo 18 per CRM — confermato, Pivot 8 estende CRM internal con config layer
- **ADR-011:** Config-driven Social Selling Engine — nuovo, deciso in questa spec

---

## Open Issues & Future Enhancements

1. **v2.0: Compensation Formula Custom Engine**
   - Linguaggio rule-based custom (es. Drools Java integration) per regole complesse
   - Attualmente tiered + conditions, v2.0 supporterà script arbitrario con sandbox

2. **v2.0: Dashboard Real-time Updates**
   - WebSocket per push update widget KPI quando deal cambia stage
   - Attualmente HTTP polling (5 min cache)

3. **v2.0: Integrazione con Slack/Teams**
   - Notifiche di nuovi lead, deal vinto, compenso confermato
   - Thread nello slack per Audit Log tracciabilità

4. **v2.0: ML-powered Compensation Analysis**
   - Anomaly detection su regole applicate
   - Suggestion di rule ottimizzate basato su storico

5. **v2.0: Granular Data Export Audit**
   - Attualmente CSV + hash SHA256, v2.0 PGP sign per E2E integrity

---

**Documento compilato da:** Roberto, Backend Architect
**Data:** 2026-04-04
**Stato:** Draft — in attesa review da PM e Frontend Tech Lead
