# Database Schema — Pivot 8: Social Selling Configurabile

**Progetto:** AgentFlow PMI
**Pivot:** 8 — Social Selling Configurabile
**Database:** PostgreSQL 16
**Data:** 2026-04-04
**Stato:** DDL Draft

---

## Migration Strategy

Le seguenti tabelle e colonne DEVONO essere create via Alembic migration (non direttamente in psql):

1. **Nuove tabelle** (10): crm_contact_origins, crm_activity_types, crm_roles, crm_role_permissions, crm_audit_log, crm_products, crm_product_categories, crm_deal_products, crm_dashboard_widgets, crm_compensation_rules, crm_compensation_entries
2. **Alter existing tables**: users (add 4 columns), crm_contacts (add origin_id), crm_pipeline_stages (add stage_type), crm_deals (modify deal_type enum)
3. **Backfill data**: Default origini, activity_types, ruoli per ogni tenant
4. **Triggers e constraints**: Audit log immutability, last_contact_at update, uniqueness constraints

---

## DDL — Nuove Tabelle

### 1. crm_contact_origins

Definisce i canali di acquisizione custom (origini) per tenant.

```sql
CREATE TABLE crm_contact_origins (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    code VARCHAR(50) NOT NULL,
    label VARCHAR(255) NOT NULL,
    parent_channel VARCHAR(50),
    icon_name VARCHAR(100),
    is_active BOOLEAN NOT NULL DEFAULT true,
    metadata JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT crm_contact_origins_code_tenant_unique UNIQUE (tenant_id, code),
    CONSTRAINT crm_contact_origins_code_length CHECK (char_length(code) <= 50),
    CONSTRAINT crm_contact_origins_label_length CHECK (char_length(label) <= 255)
);

CREATE INDEX idx_crm_contact_origins_tenant_active ON crm_contact_origins(tenant_id, is_active);
CREATE INDEX idx_crm_contact_origins_tenant_code ON crm_contact_origins(tenant_id, code);

COMMENT ON TABLE crm_contact_origins IS 'Canali di acquisizione contatti custom (es. LinkedIn, Referral, Evento)';
COMMENT ON COLUMN crm_contact_origins.code IS 'Codice univoco per tenant, max 50 char, immutabile dopo creazione';
COMMENT ON COLUMN crm_contact_origins.parent_channel IS 'Canale padre per raggruppamento (social, direct, event, etc.)';
```

---

### 2. crm_activity_types

Tipi di attività tracciabili (Call, Email, LinkedIn DM, etc.).

```sql
CREATE TABLE crm_activity_types (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    code VARCHAR(50) NOT NULL,
    label VARCHAR(255) NOT NULL,
    category VARCHAR(50) NOT NULL,
    counts_as_last_contact BOOLEAN NOT NULL DEFAULT false,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT crm_activity_types_code_tenant_unique UNIQUE (tenant_id, code),
    CONSTRAINT crm_activity_types_category_enum CHECK (category IN ('sales', 'marketing', 'support')),
    CONSTRAINT crm_activity_types_code_length CHECK (char_length(code) <= 50)
);

CREATE INDEX idx_crm_activity_types_tenant_active ON crm_activity_types(tenant_id, is_active);

COMMENT ON TABLE crm_activity_types IS 'Tipi di attività custom e standard per il tenant';
COMMENT ON COLUMN crm_activity_types.counts_as_last_contact IS 'Se true, aggiorna contact.last_contact_at';
```

---

### 3. crm_roles

Ruoli RBAC per tenant (Admin, Sales Rep, Manager, etc.).

```sql
CREATE TABLE crm_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    is_system_role BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT crm_roles_name_tenant_unique UNIQUE (tenant_id, name),
    CONSTRAINT crm_roles_name_length CHECK (char_length(name) <= 255)
);

CREATE INDEX idx_crm_roles_tenant ON crm_roles(tenant_id);

COMMENT ON TABLE crm_roles IS 'Ruoli RBAC per controllo accesso granulare';
COMMENT ON COLUMN crm_roles.is_system_role IS 'Se true, è un ruolo di sistema (Owner, Admin, Viewer) non modificabile';
```

---

### 4. crm_role_permissions

Matrice permessi per ruolo.

```sql
CREATE TABLE crm_role_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES crm_roles(id) ON DELETE CASCADE,
    entity VARCHAR(50) NOT NULL,
    permission VARCHAR(50) NOT NULL,
    scope VARCHAR(50) NOT NULL DEFAULT 'own_only',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT crm_role_permissions_entity_enum CHECK (entity IN (
        'contacts', 'deals', 'activities', 'pipelines', 'sequences', 'reports', 'audit_log', 'settings'
    )),
    CONSTRAINT crm_role_permissions_permission_enum CHECK (permission IN (
        'create', 'read', 'update', 'delete', 'export', 'view_all'
    )),
    CONSTRAINT crm_role_permissions_scope_enum CHECK (scope IN (
        'own_only', 'team', 'all'
    )),
    CONSTRAINT crm_role_permissions_unique UNIQUE (tenant_id, role_id, entity, permission)
);

CREATE INDEX idx_crm_role_permissions_role ON crm_role_permissions(role_id);
CREATE INDEX idx_crm_role_permissions_tenant_role_entity ON crm_role_permissions(tenant_id, role_id, entity);

COMMENT ON TABLE crm_role_permissions IS 'Matrice permessi fine-grained per ruolo (RBAC)';
COMMENT ON COLUMN crm_role_permissions.scope IS 'own_only = dati assegnati a user, team = team members, all = tutti (con row-level security se applicato)';
```

---

### 5. crm_audit_log

Log immutabile di azioni utenti.

```sql
CREATE TABLE crm_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
    user_id UUID NOT NULL REFERENCES "user"(id) ON DELETE RESTRICT,
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID,
    entity_name VARCHAR(255),
    change_details JSONB,
    ip_address INET,
    user_agent TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'success',
    error_message TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT crm_audit_log_action_enum CHECK (action IN (
        'create_contact', 'update_contact', 'delete_contact',
        'create_deal', 'update_deal', 'delete_deal', 'move_deal_stage',
        'log_activity', 'create_activity',
        'export_csv', 'login', 'logout', 'permission_denied',
        'bulk_update_origin', 'calculate_compensation', 'confirm_compensation'
    )),
    CONSTRAINT crm_audit_log_entity_type_enum CHECK (entity_type IN (
        'contact', 'deal', 'activity', 'user', 'role', 'origin', 'product', 'compensation', 'pipeline_stage'
    )),
    CONSTRAINT crm_audit_log_status_enum CHECK (status IN ('success', 'error', 'denied'))
);

CREATE INDEX idx_crm_audit_log_tenant_created ON crm_audit_log(tenant_id, created_at DESC);
CREATE INDEX idx_crm_audit_log_tenant_user_created ON crm_audit_log(tenant_id, user_id, created_at DESC);
CREATE INDEX idx_crm_audit_log_tenant_entity ON crm_audit_log(tenant_id, entity_type, entity_id);

COMMENT ON TABLE crm_audit_log IS 'Log immutabile di tutte le azioni (CRUD, login, export, permission denied). Trigger nega UPDATE/DELETE.';
```

**Trigger immutabilità:**

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

COMMENT ON TRIGGER trig_audit_log_immutable ON crm_audit_log IS 'Nega qualsiasi UPDATE/DELETE su audit log per immutabilità GDPR-compliant';

-- RETENTION STRATEGY (GDPR - 90 giorni configurabili):
-- Opzione consigliata: Partitioning by month + DROP PARTITION per retention.
-- Il trigger immutabilità impedisce DELETE, ma DROP PARTITION è un'operazione DDL
-- che bypassa i trigger row-level, consentendo la pulizia senza violare l'immutabilità
-- a livello di singola riga.
--
-- Esempio implementazione (v2):
-- CREATE TABLE crm_audit_log (...) PARTITION BY RANGE (created_at);
-- CREATE TABLE crm_audit_log_2026_03 PARTITION OF crm_audit_log
--     FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');
-- Cron mensile: DROP TABLE crm_audit_log_2025_12; (retention 90gg)
--
-- Per MVP: usare tabella flat + cron job con utente 'audit_gc' esente dal trigger.
```

---

### 6. crm_product_categories

Categorie di raggruppamento prodotti. **NOTA: Deve essere creata PRIMA di crm_products (FK dependency).**

```sql
CREATE TABLE crm_product_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT crm_product_categories_name_tenant_unique UNIQUE (tenant_id, name)
);

CREATE INDEX idx_crm_product_categories_tenant ON crm_product_categories(tenant_id);

COMMENT ON TABLE crm_product_categories IS 'Categorie di raggruppamento prodotti (Sviluppo, Supporto, Training, etc.)';
```

---

### 7. crm_products

Catalogo prodotti/servizi.

```sql
CREATE TABLE crm_products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    code VARCHAR(50) NOT NULL,
    category_id UUID REFERENCES crm_product_categories(id) ON DELETE SET NULL,
    pricing_model VARCHAR(50) NOT NULL,
    base_price NUMERIC(12, 2),
    hourly_rate NUMERIC(10, 2),
    estimated_duration_days INTEGER,
    technology_type VARCHAR(50),
    target_margin_percent NUMERIC(5, 2),
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT crm_products_code_tenant_unique UNIQUE (tenant_id, code),
    CONSTRAINT crm_products_pricing_model_enum CHECK (pricing_model IN ('fixed', 'hourly', 'custom')),
    CONSTRAINT crm_products_name_length CHECK (char_length(name) <= 255),
    CONSTRAINT crm_products_code_length CHECK (char_length(code) <= 50)
);

CREATE INDEX idx_crm_products_tenant ON crm_products(tenant_id);
CREATE INDEX idx_crm_products_tenant_active ON crm_products(tenant_id, is_active);
CREATE INDEX idx_crm_products_category ON crm_products(category_id);

COMMENT ON TABLE crm_products IS 'Catalogo prodotti/servizi vendibili (es. Sviluppo Custom, Supporto SLA)';
COMMENT ON COLUMN crm_products.pricing_model IS 'fixed = prezzo fisso, hourly = €/ora, custom = negoziato caso-per-caso';
```

---

### 8. crm_deal_products

Pivot table: associa prodotti a deal.

```sql
CREATE TABLE crm_deal_products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    deal_id UUID NOT NULL REFERENCES crm_deals(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES crm_products(id) ON DELETE RESTRICT,
    quantity NUMERIC(10, 2) NOT NULL DEFAULT 1,
    price_override NUMERIC(12, 2),
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- NOTA: Nessun UNIQUE su (deal_id, product_id) — lo stesso prodotto può apparire
    -- su più righe dello stesso deal (es. fasi diverse, lotti separati). Vedi AC-114.4.
    CONSTRAINT crm_deal_products_quantity_positive CHECK (quantity > 0)
);

CREATE INDEX idx_crm_deal_products_tenant_deal ON crm_deal_products(tenant_id, deal_id);
CREATE INDEX idx_crm_deal_products_product ON crm_deal_products(product_id);

COMMENT ON TABLE crm_deal_products IS 'Associazione M2M tra deal e prodotti con quantità e price override';
COMMENT ON COLUMN crm_deal_products.price_override IS 'Se NOT NULL, sostituisce il base_price del prodotto';
```

---

### 9. crm_dashboard_widgets

Configurazione dashboard KPI personalizate.

```sql
CREATE TABLE crm_dashboard_widgets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    dashboard_layout JSONB NOT NULL,
    created_by UUID NOT NULL REFERENCES "user"(id) ON DELETE SET NULL,
    is_shared BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT crm_dashboard_widgets_name_length CHECK (char_length(name) <= 255)
);

CREATE INDEX idx_crm_dashboard_widgets_tenant ON crm_dashboard_widgets(tenant_id);
CREATE INDEX idx_crm_dashboard_widgets_created_by ON crm_dashboard_widgets(created_by);

COMMENT ON TABLE crm_dashboard_widgets IS 'Configurazione dashboard con layout JSON e widget preset';
COMMENT ON COLUMN crm_dashboard_widgets.dashboard_layout IS 'JSON schema con array di widget: {layout: [{widget_id, type, title, period, filters, position}]}';
```

---

### 10. crm_compensation_rules

Regole per calcolo compensi.

```sql
CREATE TABLE crm_compensation_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    trigger VARCHAR(50) NOT NULL,
    calculation_method VARCHAR(50) NOT NULL,
    base_config JSONB NOT NULL,
    conditions JSONB,
    priority INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_by UUID NOT NULL REFERENCES "user"(id) ON DELETE SET NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT crm_compensation_rules_trigger_enum CHECK (trigger IN (
        'deal_won', 'revenue_threshold', 'activity_count', 'quarterly', 'custom'
    )),
    CONSTRAINT crm_compensation_rules_calculation_method_enum CHECK (calculation_method IN (
        'percent_revenue', 'fixed_amount', 'tiered'
    ))
    -- NOTA: 'formula' rimossa per MVP (rischio injection senza sandbox). Rimandata a v2.
);

CREATE INDEX idx_crm_compensation_rules_tenant ON crm_compensation_rules(tenant_id);
CREATE INDEX idx_crm_compensation_rules_tenant_active_priority ON crm_compensation_rules(tenant_id, is_active, priority);

COMMENT ON TABLE crm_compensation_rules IS 'Regole trigger e calcolo per compensi/provvigioni mensili';
COMMENT ON COLUMN crm_compensation_rules.base_config IS 'JSON: {method, rate/tiers/amount, description} dipende da calculation_method';
COMMENT ON COLUMN crm_compensation_rules.conditions IS 'JSON: {product_ids, origin_ids, user_ids, min_revenue, start_date, end_date}';
```

---

### 11. crm_compensation_entries

Risultato calcolo compensi mensili per user.

```sql
CREATE TABLE crm_compensation_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    month DATE NOT NULL,
    amount_gross NUMERIC(12, 2) NOT NULL,
    rules_applied JSONB NOT NULL,
    deal_contributions JSONB,
    status VARCHAR(50) NOT NULL DEFAULT 'draft',
    error_message TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100) NOT NULL DEFAULT 'system',
    confirmed_at TIMESTAMP,
    paid_at TIMESTAMP,

    CONSTRAINT crm_compensation_entries_month_user_unique UNIQUE (tenant_id, user_id, month),
    CONSTRAINT crm_compensation_entries_status_enum CHECK (status IN ('draft', 'confirmed', 'paid', 'error')),
    CONSTRAINT crm_compensation_entries_amount_positive CHECK (amount_gross >= 0)
);

CREATE INDEX idx_crm_compensation_entries_tenant_month ON crm_compensation_entries(tenant_id, month DESC);
CREATE INDEX idx_crm_compensation_entries_tenant_user_month ON crm_compensation_entries(tenant_id, user_id, month DESC);
CREATE INDEX idx_crm_compensation_entries_tenant_status ON crm_compensation_entries(tenant_id, status);

COMMENT ON TABLE crm_compensation_entries IS 'Compensi mensili calcolati per user (draft → confirmed → paid)';
COMMENT ON COLUMN crm_compensation_entries.rules_applied IS 'JSON: {applied_rules: [{rule_id, rule_name, contribution, details}], total_amount}';
```

---

## DDL — Alterazioni Tabelle Esistenti

### users (aggiungi colonne)

```sql
ALTER TABLE "user" ADD COLUMN user_type VARCHAR(50) DEFAULT 'internal' NOT NULL;
ALTER TABLE "user" ADD CONSTRAINT user_type_enum CHECK (user_type IN ('internal', 'external', 'admin', 'system'));
-- 'system' per service accounts (es. cron job compensi, audit GC). Creare un user di sistema per tenant.

ALTER TABLE "user" ADD COLUMN access_expires_at TIMESTAMP;

ALTER TABLE "user" ADD COLUMN crm_role_id UUID REFERENCES crm_roles(id) ON DELETE SET NULL;

ALTER TABLE "user" ADD COLUMN default_origin_id UUID REFERENCES crm_contact_origins(id) ON DELETE SET NULL;

ALTER TABLE "user" ADD COLUMN default_product_id UUID REFERENCES crm_products(id) ON DELETE SET NULL;

CREATE INDEX idx_user_crm_role ON "user"(crm_role_id);
CREATE INDEX idx_user_access_expires ON "user"(access_expires_at) WHERE user_type = 'external';

COMMENT ON COLUMN "user".user_type IS 'internal = utente standard, external = collaboratore esterno con scadenza, admin = admin sistema';
COMMENT ON COLUMN "user".access_expires_at IS 'Data scadenza accesso per external users. NULL = senza scadenza.';
COMMENT ON COLUMN "user".crm_role_id IS 'Ruolo RBAC assegnato. FK a crm_roles.';
COMMENT ON COLUMN "user".default_origin_id IS 'Canale default per pre-compilazione contatto (row-level security se external)';
COMMENT ON COLUMN "user".default_product_id IS 'Prodotto default per pre-selezione deal';
```

**Backfill:**

```sql
-- Per utenti esistenti, setta user_type='internal' e assegna ruolo Admin (se non già assegnato)
UPDATE "user"
SET user_type = 'internal'
WHERE user_type IS NULL OR user_type = '';

-- Backfill crm_role_id con ruolo "Admin" del tenant (assumi colonna tenant_id esista in users)
-- Questo è pseudo-codice, adattare a schema reale:
UPDATE "user" u
SET crm_role_id = (
    SELECT id FROM crm_roles
    WHERE tenant_id = u.tenant_id AND name = 'Admin'
    LIMIT 1
)
WHERE u.crm_role_id IS NULL;
```

---

### crm_contacts (aggiungi colonna)

```sql
-- STEP 1: Aggiungere colonna NULLABLE (prima del backfill)
ALTER TABLE crm_contacts ADD COLUMN origin_id UUID REFERENCES crm_contact_origins(id) ON DELETE RESTRICT;

CREATE INDEX idx_crm_contacts_origin ON crm_contacts(origin_id);
CREATE INDEX idx_crm_contacts_tenant_origin ON crm_contacts(tenant_id, origin_id);

COMMENT ON COLUMN crm_contacts.origin_id IS 'Canale di acquisizione (FK a crm_contact_origins). Replace della colonna source (string).';

-- STEP 2: Eseguire backfill (vedi sezione Migration sotto)
-- STEP 3: Dopo backfill completato, aggiungere constraint NOT NULL
-- ALTER TABLE crm_contacts ADD CONSTRAINT crm_contacts_origin_required CHECK (
--     origin_id IS NOT NULL OR status IN ('archived', 'deleted')
-- );
-- NOTA: Questo constraint va aggiunto in una migration SEPARATA, dopo aver verificato
-- che tutti i contatti attivi hanno origin_id valorizzato.
```

**Migration: source (string) → origin_id (FK)**

```sql
-- 1. Per ogni valore univoco di source, crea origin automaticamente
INSERT INTO crm_contact_origins (tenant_id, code, label, parent_channel, is_active)
SELECT DISTINCT
    tenant_id,
    LOWER(REGEXP_REPLACE(source, '\s+', '_', 'g')), -- code: source con spazi → underscore
    source, -- label: source originale
    'other', -- parent_channel default
    true
FROM crm_contacts
WHERE source IS NOT NULL AND source != ''
GROUP BY tenant_id, source
ON CONFLICT (tenant_id, code) DO NOTHING;

-- 2. Backfill origin_id da source
UPDATE crm_contacts c
SET origin_id = (
    SELECT id FROM crm_contact_origins
    WHERE tenant_id = c.tenant_id
      AND code = LOWER(REGEXP_REPLACE(c.source, '\s+', '_', 'g'))
    LIMIT 1
)
WHERE c.source IS NOT NULL AND c.source != '';

-- 3. Contatti con source NULL: assegna origine "da_classificare"
INSERT INTO crm_contact_origins (tenant_id, code, label, parent_channel, is_active)
SELECT DISTINCT tenant_id, 'da_classificare', 'Da Classificare', 'other', true
FROM crm_contacts
WHERE source IS NULL OR source = ''
ON CONFLICT (tenant_id, code) DO NOTHING;

UPDATE crm_contacts c
SET origin_id = (
    SELECT id FROM crm_contact_origins
    WHERE tenant_id = c.tenant_id AND code = 'da_classificare'
    LIMIT 1
)
WHERE (c.source IS NULL OR c.source = '') AND c.origin_id IS NULL;

-- 4. STEP 3 (migration separata): Dopo verifica backfill, aggiungere constraint
ALTER TABLE crm_contacts ADD CONSTRAINT crm_contacts_origin_required CHECK (
    origin_id IS NOT NULL OR status IN ('archived', 'deleted')
);

-- 5. Mantieni source per rollback temporaneo (drop dopo 30 gg in produzione)
-- ALTER TABLE crm_contacts DROP COLUMN source;
```

---

### crm_pipeline_stages (aggiungi colonna)

```sql
ALTER TABLE crm_pipeline_stages ADD COLUMN stage_type VARCHAR(50) DEFAULT 'pipeline' NOT NULL;
ALTER TABLE crm_pipeline_stages ADD CONSTRAINT crm_pipeline_stages_type_enum CHECK (stage_type IN ('pre_funnel', 'pipeline'));

CREATE INDEX idx_crm_pipeline_stages_tenant_type ON crm_pipeline_stages(tenant_id, stage_type);

COMMENT ON COLUMN crm_pipeline_stages.stage_type IS 'pre_funnel = stadi prima della pipeline (es. Prospect), pipeline = stadi standard (es. Nuovo Lead)';
```

---

### crm_deals (modifica enum deal_type)

```sql
-- PostgreSQL: Aggiungi nuovi valori all'enum
ALTER TYPE deal_type_enum ADD VALUE 'subscription' AFTER 'spot';
ALTER TYPE deal_type_enum ADD VALUE 'mixed' AFTER 'subscription';

-- Oppure, se deal_type è VARCHAR (non enum):
-- Nessuna modifica necessaria, il constraint check è nel servizio
```

---

## Backfill Data — Seed Origini, Tipi Attività, Ruoli

### Per ogni nuovo tenant (trigger su tenants INSERT):

```sql
-- Crea tabella di seed data per il tenant appena creato
CREATE OR REPLACE FUNCTION fn_seed_tenant_config()
RETURNS TRIGGER AS $$
DECLARE
    v_tenant_id UUID := NEW.id;
BEGIN
    -- 1. Seed origini default
    INSERT INTO crm_contact_origins (tenant_id, code, label, parent_channel, icon_name, is_active) VALUES
        (v_tenant_id, 'web_form', 'Web Form', 'direct', 'icon-globe', true),
        (v_tenant_id, 'linkedin_organic', 'LinkedIn Organico', 'social', 'icon-linkedin', true),
        (v_tenant_id, 'linkedin_dm', 'LinkedIn DM', 'social', 'icon-message', true),
        (v_tenant_id, 'referral', 'Referral', 'direct', 'icon-users', true),
        (v_tenant_id, 'event', 'Evento/Conferenza', 'event', 'icon-calendar', true),
        (v_tenant_id, 'cold_outreach', 'Cold Email', 'direct', 'icon-mail', true);

    -- 2. Seed tipi attività default
    INSERT INTO crm_activity_types (tenant_id, code, label, category, counts_as_last_contact, is_active) VALUES
        (v_tenant_id, 'call', 'Chiamata', 'sales', true, true),
        (v_tenant_id, 'email', 'Email', 'sales', true, true),
        (v_tenant_id, 'meeting', 'Incontro', 'sales', true, true),
        (v_tenant_id, 'note', 'Nota Interna', 'sales', false, true),
        (v_tenant_id, 'task', 'Task/Reminder', 'sales', false, true),
        (v_tenant_id, 'linkedin_inmail', 'Inmail LinkedIn', 'sales', true, true),
        (v_tenant_id, 'linkedin_comment', 'Commento LinkedIn', 'marketing', true, true),
        (v_tenant_id, 'linkedin_engagement', 'Engagement LinkedIn', 'marketing', true, true);

    -- 3. Seed ruoli default (system roles)
    INSERT INTO crm_roles (tenant_id, name, description, is_system_role) VALUES
        (v_tenant_id, 'Owner', 'Proprietario — accesso illimitato', true),
        (v_tenant_id, 'Admin', 'Administrator — configura ruoli, utenti, audit', true),
        (v_tenant_id, 'Sales Rep', 'Sales Representative — CRUD deal/contacts, limited export', false),
        (v_tenant_id, 'Sales Manager', 'Sales Manager — view all, KPI, scorecard', false),
        (v_tenant_id, 'Viewer', 'Read-only viewer', true);

    -- 4. Seed permission matrix per ruoli (Owner ha tutto, Admin ha quasi tutto, etc.)
    -- Owner: tutti i permessi su tutte le entità
    INSERT INTO crm_role_permissions (tenant_id, role_id, entity, permission, scope)
    SELECT
        v_tenant_id,
        (SELECT id FROM crm_roles WHERE tenant_id = v_tenant_id AND name = 'Owner'),
        perms.entity,
        perms.permission,
        'all'
    FROM (
        SELECT 'contacts' as entity, 'create' as permission UNION ALL
        SELECT 'contacts', 'read' UNION ALL
        SELECT 'contacts', 'update' UNION ALL
        SELECT 'contacts', 'delete' UNION ALL
        SELECT 'contacts', 'export' UNION ALL
        SELECT 'contacts', 'view_all' UNION ALL
        SELECT 'deals', 'create' UNION ALL
        SELECT 'deals', 'read' UNION ALL
        SELECT 'deals', 'update' UNION ALL
        SELECT 'deals', 'delete' UNION ALL
        SELECT 'deals', 'export' UNION ALL
        SELECT 'deals', 'view_all' UNION ALL
        SELECT 'activities', 'create' UNION ALL
        SELECT 'activities', 'read' UNION ALL
        SELECT 'activities', 'update' UNION ALL
        SELECT 'activities', 'delete' UNION ALL
        SELECT 'pipelines', 'read' UNION ALL
        SELECT 'pipelines', 'update' UNION ALL
        SELECT 'reports', 'read' UNION ALL
        SELECT 'reports', 'export' UNION ALL
        SELECT 'audit_log', 'read' UNION ALL
        SELECT 'audit_log', 'export' UNION ALL
        SELECT 'settings', 'read' UNION ALL
        SELECT 'settings', 'update'
    ) as perms;

    -- Admin: tutti tranne delete su entity critiche
    INSERT INTO crm_role_permissions (tenant_id, role_id, entity, permission, scope)
    SELECT
        v_tenant_id,
        (SELECT id FROM crm_roles WHERE tenant_id = v_tenant_id AND name = 'Admin'),
        perms.entity,
        perms.permission,
        'all'
    FROM (
        SELECT 'contacts' as entity, 'create' as permission UNION ALL
        SELECT 'contacts', 'read' UNION ALL
        SELECT 'contacts', 'update' UNION ALL
        SELECT 'contacts', 'export' UNION ALL
        SELECT 'contacts', 'view_all' UNION ALL
        SELECT 'deals', 'create' UNION ALL
        SELECT 'deals', 'read' UNION ALL
        SELECT 'deals', 'update' UNION ALL
        SELECT 'deals', 'export' UNION ALL
        SELECT 'deals', 'view_all' UNION ALL
        SELECT 'activities', 'create' UNION ALL
        SELECT 'activities', 'read' UNION ALL
        SELECT 'activities', 'update' UNION ALL
        SELECT 'pipelines', 'read' UNION ALL
        SELECT 'pipelines', 'update' UNION ALL
        SELECT 'reports', 'read' UNION ALL
        SELECT 'reports', 'export' UNION ALL
        SELECT 'audit_log', 'read' UNION ALL
        SELECT 'audit_log', 'export' UNION ALL
        SELECT 'settings', 'read' UNION ALL
        SELECT 'settings', 'update'
    ) as perms;

    -- Sales Rep: CRUD su dati propri, no export, no delete
    INSERT INTO crm_role_permissions (tenant_id, role_id, entity, permission, scope)
    SELECT
        v_tenant_id,
        (SELECT id FROM crm_roles WHERE tenant_id = v_tenant_id AND name = 'Sales Rep'),
        perms.entity,
        perms.permission,
        'own_only'
    FROM (
        SELECT 'contacts' as entity, 'create' as permission UNION ALL
        SELECT 'contacts', 'read' UNION ALL
        SELECT 'contacts', 'update' UNION ALL
        SELECT 'deals', 'create' UNION ALL
        SELECT 'deals', 'read' UNION ALL
        SELECT 'deals', 'update' UNION ALL
        SELECT 'activities', 'create' UNION ALL
        SELECT 'activities', 'read' UNION ALL
        SELECT 'reports', 'read'
    ) as perms;

    -- Sales Manager: view_all, CRUD, export, no delete
    INSERT INTO crm_role_permissions (tenant_id, role_id, entity, permission, scope)
    SELECT
        v_tenant_id,
        (SELECT id FROM crm_roles WHERE tenant_id = v_tenant_id AND name = 'Sales Manager'),
        perms.entity,
        perms.permission,
        CASE WHEN perms.permission = 'view_all' THEN 'all' ELSE 'own_only' END
    FROM (
        SELECT 'contacts' as entity, 'create' as permission UNION ALL
        SELECT 'contacts', 'read' UNION ALL
        SELECT 'contacts', 'update' UNION ALL
        SELECT 'contacts', 'view_all' UNION ALL
        SELECT 'contacts', 'export' UNION ALL
        SELECT 'deals', 'create' UNION ALL
        SELECT 'deals', 'read' UNION ALL
        SELECT 'deals', 'update' UNION ALL
        SELECT 'deals', 'view_all' UNION ALL
        SELECT 'deals', 'export' UNION ALL
        SELECT 'activities', 'read' UNION ALL
        SELECT 'activities', 'view_all' UNION ALL
        SELECT 'pipelines', 'read' UNION ALL
        SELECT 'reports', 'read' UNION ALL
        SELECT 'reports', 'export'
    ) as perms;

    -- Viewer: read-only su tutto
    INSERT INTO crm_role_permissions (tenant_id, role_id, entity, permission, scope)
    SELECT
        v_tenant_id,
        (SELECT id FROM crm_roles WHERE tenant_id = v_tenant_id AND name = 'Viewer'),
        perms.entity,
        perms.permission,
        'all'
    FROM (
        SELECT 'contacts' as entity, 'read' as permission UNION ALL
        SELECT 'contacts', 'view_all' UNION ALL
        SELECT 'deals', 'read' UNION ALL
        SELECT 'deals', 'view_all' UNION ALL
        SELECT 'activities', 'read' UNION ALL
        SELECT 'pipelines', 'read' UNION ALL
        SELECT 'reports', 'read'
    ) as perms;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trig_seed_tenant_config
AFTER INSERT ON tenants
FOR EACH ROW
EXECUTE FUNCTION fn_seed_tenant_config();

COMMENT ON TRIGGER trig_seed_tenant_config ON tenants IS 'Auto-seed origini, tipi attività, ruoli default quando un nuovo tenant è creato';
```

---

## Triggers e Utility Functions

### Trigger: Update contact.last_contact_at quando attività loggata

```sql
CREATE OR REPLACE FUNCTION fn_update_contact_last_contact()
RETURNS TRIGGER AS $$
DECLARE
    v_counts_as_last BOOLEAN;
BEGIN
    -- Verifica se il tipo attività ha counts_as_last_contact = true
    SELECT counts_as_last_contact INTO v_counts_as_last
    FROM crm_activity_types
    WHERE id = NEW.type_id;

    IF v_counts_as_last THEN
        UPDATE crm_contacts
        SET last_contact_at = NEW.occurred_at,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = NEW.contact_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trig_update_contact_last_contact
AFTER INSERT ON crm_activities
FOR EACH ROW
WHEN (NEW.contact_id IS NOT NULL)
EXECUTE FUNCTION fn_update_contact_last_contact();

COMMENT ON TRIGGER trig_update_contact_last_contact ON crm_activities IS 'Aggiorna contact.last_contact_at se activity.type.counts_as_last_contact=true';
```

---

### Trigger: Denygate hard-delete su crm_audit_log

```sql
-- Già definito sopra, vedi section 5 (crm_audit_log)
```

---

### Function: Disable utenti esterni scaduti (per job notturna)

```sql
CREATE OR REPLACE FUNCTION fn_disable_expired_external_users()
RETURNS TABLE (disabled_count INT) AS $$
DECLARE
    v_count INT;
BEGIN
    UPDATE "user"
    SET is_active = false,
        updated_at = CURRENT_TIMESTAMP
    WHERE user_type = 'external'
      AND access_expires_at < CURRENT_TIMESTAMP
      AND is_active = true;

    GET DIAGNOSTICS v_count = ROW_COUNT;

    RETURN QUERY SELECT v_count AS disabled_count;
END;
$$ LANGUAGE plpgsql;

-- Invoked nightly da Celery task:
-- SELECT fn_disable_expired_external_users();
```

---

## Indices Summary

| Tabella | Indice | Colonne | Scopo |
|---------|--------|---------|-------|
| crm_contact_origins | idx_crm_contact_origins_tenant_active | (tenant_id, is_active) | Dropdown speedup |
| crm_activity_types | idx_crm_activity_types_tenant_active | (tenant_id, is_active) | Dropdown |
| crm_roles | idx_crm_roles_tenant | (tenant_id) | List roles |
| crm_role_permissions | idx_crm_role_permissions_tenant_role_entity | (tenant_id, role_id, entity) | RBAC check |
| crm_audit_log | idx_crm_audit_log_tenant_created | (tenant_id, created_at DESC) | Audit trail query |
| crm_audit_log | idx_crm_audit_log_tenant_user_created | (tenant_id, user_id, created_at DESC) | Filter per user |
| crm_audit_log | idx_crm_audit_log_tenant_entity | (tenant_id, entity_type, entity_id) | Find actions on entity |
| crm_products | idx_crm_products_tenant_active | (tenant_id, is_active) | Dropdown |
| crm_products | idx_crm_products_category | (category_id) | Filter per categoria |
| crm_deal_products | idx_crm_deal_products_tenant_deal | (tenant_id, deal_id) | Prodotti di un deal |
| crm_compensation_rules | idx_crm_compensation_rules_tenant_active_priority | (tenant_id, is_active, priority) | Apply rules in order |
| crm_compensation_entries | idx_crm_compensation_entries_tenant_month | (tenant_id, month DESC) | Query per mese |
| crm_compensation_entries | idx_crm_compensation_entries_tenant_status | (tenant_id, status) | Draft/confirmed query |
| "user" | idx_user_crm_role | (crm_role_id) | Role lookup |
| "user" | idx_user_access_expires | (access_expires_at) WHERE user_type='external' | Find expired users |
| crm_contacts | idx_crm_contacts_origin | (origin_id) | Origin lookup |
| crm_contacts | idx_crm_contacts_tenant_origin | (tenant_id, origin_id) | Filter per origin |
| crm_pipeline_stages | idx_crm_pipeline_stages_tenant_type | (tenant_id, stage_type) | Filter pre_funnel |

---

## Constraints Summary

| Tabella | Constraint | Regola | Severity |
|---------|-----------|--------|----------|
| crm_contact_origins | UNIQUE (tenant_id, code) | Codice unico per tenant | ERROR |
| crm_activity_types | UNIQUE (tenant_id, code) | Codice unico per tenant | ERROR |
| crm_roles | UNIQUE (tenant_id, name) | Nome ruolo unico per tenant | ERROR |
| crm_role_permissions | UNIQUE (tenant_id, role_id, entity, permission) | No duplicati permessi | ERROR |
| crm_products | UNIQUE (tenant_id, code) | Codice prodotto unico per tenant | ERROR |
| crm_deal_products | UNIQUE (tenant_id, deal_id, product_id) | No duplicati prodotto per deal | ERROR |
| crm_compensation_entries | UNIQUE (tenant_id, user_id, month) | Una riga per user/mese | ERROR |
| crm_audit_log | (trigger) BEFORE UPDATE/DELETE | Nega modifica audit log | ERROR |
| crm_contacts | CHECK (origin_id NOT NULL \| status IN (...)) | Origine obbligatoria | WARNING (app-level) |

---

## Views (Optional)

```sql
-- View per debugging: mostra compensation breakdown per user e mese
CREATE OR REPLACE VIEW v_compensation_summary AS
SELECT
    ce.tenant_id,
    ce.user_id,
    u.email,
    u.name,
    ce.month,
    ce.amount_gross,
    (ce.rules_applied -> 'applied_rules')::jsonb as rules_details,
    ce.status,
    ce.created_at,
    ce.confirmed_at,
    ce.paid_at
FROM crm_compensation_entries ce
JOIN "user" u ON ce.user_id = u.id;

COMMENT ON VIEW v_compensation_summary IS 'View per inspection compensi calcolati (debug + reporting)';
```

---

## Migration Order (Alembic)

1. **Revision 001:** Create new tables (origini, activity_types, roles, role_permissions, audit_log, products, categories, deal_products, dashboard_widgets, compensation_rules, compensation_entries)
2. **Revision 002:** Add columns to users (user_type, access_expires_at, crm_role_id, default_origin_id, default_product_id)
3. **Revision 003:** Add origin_id to crm_contacts con trigger migration source → origin_id
4. **Revision 004:** Add stage_type a crm_pipeline_stages
5. **Revision 005:** Extend crm_deals.deal_type enum (subscription, mixed)
6. **Revision 006:** Create triggers (audit_log immutability, contact.last_contact_at update, fn_seed_tenant_config)
7. **Revision 007:** Seed data untuk existing tenants (origini, activity_types, ruoli + backfill crm_role_id)

---

**Documento compilato da:** Roberto, Backend Architect
**Data:** 2026-04-04
**Stato:** DDL Draft — review da DBA/DevOps prima di apply

