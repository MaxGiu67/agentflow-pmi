# Database Schema — AgentFlow PMI

**Aggiornato:** 2026-03-22
**Engine:** PostgreSQL 16
**Architettura:** Dual-database (PostgreSQL applicativo + PostgreSQL Odoo per tenant)

---

## Database Applicativo (FastAPI)

### Tabelle Core (v0.1)

```sql
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    type VARCHAR(20) NOT NULL,              -- srl, srls, piva, ditta_individuale
    regime_fiscale VARCHAR(50) NOT NULL,    -- forfettario, semplificato, ordinario
    codice_ateco VARCHAR(10),
    piva VARCHAR(11) UNIQUE,
    odoo_db_name VARCHAR(100),
    subscription_tier VARCHAR(20) DEFAULT 'starter',
    active_agents JSONB DEFAULT '["conta", "fisco"]',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    role VARCHAR(20) DEFAULT 'viewer',      -- owner, admin, viewer
    spid_token TEXT,                         -- encrypted AES-256
    spid_token_expires_at TIMESTAMP,
    oauth_tokens JSONB,                      -- encrypted at rest
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    odoo_move_id INTEGER,
    type VARCHAR(10) NOT NULL,              -- attiva, passiva
    document_type VARCHAR(10),              -- TD01 (fattura), TD04 (nota credito), TD05, TD06...
    source VARCHAR(20) NOT NULL,            -- cassetto_fiscale, sdi, email, upload
    numero_fattura VARCHAR(50),
    emittente_piva VARCHAR(11),
    emittente_nome VARCHAR(255),
    data_fattura DATE,
    importo_netto DECIMAL(12,2),
    importo_iva DECIMAL(12,2),
    importo_totale DECIMAL(12,2),
    raw_xml TEXT,
    structured_data JSONB,
    category_id UUID,
    category_confidence FLOAT,
    verified BOOLEAN DEFAULT FALSE,
    file_path VARCHAR(500),
    has_ritenuta BOOLEAN DEFAULT FALSE,
    has_bollo BOOLEAN DEFAULT FALSE,
    processing_status VARCHAR(20) DEFAULT 'pending', -- pending, parsed, categorized, registered, error
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE fiscal_deadlines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,
    codice_tributo VARCHAR(10),
    description TEXT,
    due_date DATE NOT NULL,
    amount DECIMAL(12,2),
    status VARCHAR(20) DEFAULT 'pending',
    source VARCHAR(30),
    related_f24_id UUID,                    -- link a f24_documents se generato
    notified_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE agent_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    event_type VARCHAR(100) NOT NULL,
    agent_name VARCHAR(50) NOT NULL,
    payload JSONB,
    status VARCHAR(20) DEFAULT 'published', -- published, consumed, dead_letter
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE categorization_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    invoice_id UUID REFERENCES invoices(id) ON DELETE CASCADE,
    suggested_category VARCHAR(100),
    final_category VARCHAR(100),
    was_correct BOOLEAN,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Tabelle Banking (v0.3-v0.4)

```sql
CREATE TABLE bank_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    provider VARCHAR(20) NOT NULL,
    bank_name VARCHAR(255),
    iban VARCHAR(34) NOT NULL,
    consent_token TEXT,                      -- encrypted AES-256
    consent_expires_at TIMESTAMP,
    sca_last_auth TIMESTAMP,
    last_sync_at TIMESTAMP,
    balance DECIMAL(12,2),
    balance_updated_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE bank_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    bank_account_id UUID REFERENCES bank_accounts(id) ON DELETE CASCADE,
    transaction_id VARCHAR(255) NOT NULL,    -- dedup key
    date DATE NOT NULL,
    value_date DATE,
    amount DECIMAL(12,2) NOT NULL,
    direction VARCHAR(10) NOT NULL,
    counterpart_name VARCHAR(255),
    counterpart_iban VARCHAR(34),
    description TEXT,
    category VARCHAR(50),
    matched_invoice_id UUID REFERENCES invoices(id),
    match_type VARCHAR(20),                  -- exact, partial, suggested, manual
    match_confidence FLOAT,
    reconciled BOOLEAN DEFAULT FALSE,
    raw_data JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(tenant_id, bank_account_id, transaction_id)
);
```

### Tabelle Gap Contabili (v0.3)

```sql
CREATE TABLE expense_policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    category VARCHAR(100) NOT NULL,
    max_amount DECIMAL(12,2),
    requires_approval BOOLEAN DEFAULT TRUE,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE expenses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id),
    date DATE NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'EUR',
    original_amount DECIMAL(12,2),
    exchange_rate DECIMAL(10,6),
    category VARCHAR(100),
    description TEXT,
    merchant VARCHAR(255),
    receipt_path VARCHAR(500),
    ocr_data JSONB,
    status VARCHAR(20) DEFAULT 'draft',
    approved_by UUID REFERENCES users(id),
    approved_at TIMESTAMP,
    rejection_reason TEXT,
    reimbursement_status VARCHAR(20),        -- pending, paid, failed
    odoo_move_id INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    invoice_id UUID REFERENCES invoices(id),
    description VARCHAR(500) NOT NULL,
    category VARCHAR(100) NOT NULL,
    ministerial_code VARCHAR(20),
    purchase_date DATE NOT NULL,
    purchase_amount DECIMAL(12,2) NOT NULL,
    depreciation_rate DECIMAL(5,2) NOT NULL,
    useful_life_years INTEGER NOT NULL,
    accumulated_depreciation DECIMAL(12,2) DEFAULT 0,
    residual_value DECIMAL(12,2),
    status VARCHAR(20) DEFAULT 'active',
    disposal_date DATE,
    disposal_amount DECIMAL(12,2) DEFAULT 0,
    disposal_type VARCHAR(20),               -- sale, scrapping, theft
    gain_loss DECIMAL(12,2),
    odoo_asset_id INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE withholding_taxes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    invoice_id UUID REFERENCES invoices(id),
    type VARCHAR(10) NOT NULL,
    rate DECIMAL(5,2) NOT NULL,
    taxable_amount DECIMAL(12,2) NOT NULL,
    withheld_amount DECIMAL(12,2) NOT NULL,
    net_payable DECIMAL(12,2) NOT NULL,
    payment_date DATE,
    payment_deadline DATE NOT NULL,
    f24_paid BOOLEAN DEFAULT FALSE,
    f24_document_id UUID,
    cu_generated BOOLEAN DEFAULT FALSE,
    cu_certificate_id UUID,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE stamp_duties (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    invoice_id UUID REFERENCES invoices(id),
    quarter INTEGER NOT NULL,
    year INTEGER NOT NULL,
    amount DECIMAL(12,2) DEFAULT 2.00,
    f24_code VARCHAR(10) DEFAULT '2501',
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE accruals_deferrals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    invoice_id UUID REFERENCES invoices(id),
    type VARCHAR(20) NOT NULL,
    total_amount DECIMAL(12,2) NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    current_year_amount DECIMAL(12,2) NOT NULL,
    deferred_amount DECIMAL(12,2) NOT NULL,
    odoo_move_id INTEGER,
    odoo_reversal_move_id INTEGER,
    status VARCHAR(20) DEFAULT 'proposed',
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Tabelle Fisco Avanzato (v0.4)

```sql
CREATE TABLE f24_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    period_month INTEGER,
    period_quarter INTEGER,
    year INTEGER NOT NULL,
    sections JSONB NOT NULL,
    total_debit DECIMAL(12,2) NOT NULL,
    total_credit DECIMAL(12,2) DEFAULT 0,
    net_amount DECIMAL(12,2) NOT NULL,
    due_date DATE NOT NULL,
    status VARCHAR(20) DEFAULT 'draft',
    pdf_path VARCHAR(500),
    telematic_path VARCHAR(500),
    paid_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE digital_preservation (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    invoice_id UUID REFERENCES invoices(id),
    provider VARCHAR(50) NOT NULL,
    batch_id VARCHAR(255),
    package_hash VARCHAR(64),
    sent_at TIMESTAMP,
    confirmed_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'queued',
    rejection_reason TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE cu_certificates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    year INTEGER NOT NULL,
    recipient_name VARCHAR(255) NOT NULL,
    recipient_cf VARCHAR(16),
    recipient_piva VARCHAR(11),
    gross_amount DECIMAL(12,2) NOT NULL,
    withheld_amount DECIMAL(12,2) NOT NULL,
    net_amount DECIMAL(12,2) NOT NULL,
    inps_contribution DECIMAL(12,2) DEFAULT 0,
    status VARCHAR(20) DEFAULT 'draft',
    export_path VARCHAR(500),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE budgets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    category VARCHAR(100) NOT NULL,
    budget_amount DECIMAL(12,2) NOT NULL,
    actual_amount DECIMAL(12,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(tenant_id, year, month, category)
);
```

### Indici

```sql
-- Core
CREATE INDEX idx_users_tenant ON users(tenant_id);
CREATE INDEX idx_invoices_tenant_date ON invoices(tenant_id, created_at);
CREATE INDEX idx_invoices_tenant_category ON invoices(tenant_id, category_id);
CREATE INDEX idx_invoices_tenant_status ON invoices(tenant_id, processing_status);
CREATE INDEX idx_invoices_dedup ON invoices(tenant_id, numero_fattura, emittente_piva, data_fattura);
CREATE INDEX idx_deadlines_tenant_date ON fiscal_deadlines(tenant_id, due_date);
CREATE INDEX idx_deadlines_pending ON fiscal_deadlines(tenant_id, status) WHERE status = 'pending';
CREATE INDEX idx_events_tenant_type ON agent_events(tenant_id, event_type, created_at);
CREATE INDEX idx_feedback_tenant ON categorization_feedback(tenant_id, created_at);

-- Banking
CREATE INDEX idx_bank_tx_tenant_date ON bank_transactions(tenant_id, date);
CREATE INDEX idx_bank_tx_unreconciled ON bank_transactions(tenant_id, reconciled) WHERE reconciled = FALSE;
CREATE INDEX idx_bank_accounts_tenant ON bank_accounts(tenant_id, status);

-- Gap Contabili
CREATE INDEX idx_expenses_tenant_status ON expenses(tenant_id, status);
CREATE INDEX idx_expenses_tenant_date ON expenses(tenant_id, date);
CREATE INDEX idx_assets_tenant_status ON assets(tenant_id, status);
CREATE INDEX idx_withholding_tenant_paid ON withholding_taxes(tenant_id, f24_paid) WHERE f24_paid = FALSE;
CREATE INDEX idx_stamp_duties_tenant_quarter ON stamp_duties(tenant_id, year, quarter);
CREATE INDEX idx_accruals_tenant_type ON accruals_deferrals(tenant_id, type);

-- Fisco Avanzato
CREATE INDEX idx_budgets_tenant_year ON budgets(tenant_id, year);
CREATE INDEX idx_f24_tenant_period ON f24_documents(tenant_id, year, period_month);
CREATE INDEX idx_preservation_tenant_status ON digital_preservation(tenant_id, status);
CREATE INDEX idx_cu_tenant_year ON cu_certificates(tenant_id, year);
```

---

## Database Contabile (Odoo CE 18)

Un database PostgreSQL separato per tenant (ADR-005), gestito interamente da Odoo.

**Modelli principali:**
- `account.account` — Piano dei conti (creato dall'agente su misura per tipo azienda)
- `account.move` — Registrazioni contabili (partita doppia)
- `account.move.line` — Righe dare/avere
- `account.journal` — Registri (vendite, acquisti, banca, vari)
- `account.tax` — Aliquote IVA
- `account.fiscal.position` — Posizioni fiscali

**Moduli OCA l10n-italy:**
- `l10n_it_account` — Piano conti italiano base
- `l10n_it_edi_extension` — FatturaPA elettronica
- `l10n_it_vat_registries` — Registri IVA
- `l10n_it_account_vat_period_end_settlement` — Liquidazione IVA
- `l10n_it_account_stamp` — Imposta di bollo
- `l10n_it_financial_statements_report` — Bilancio CEE
- `l10n_it_fiscalcode` — Codice fiscale

---

## Riepilogo

| Categoria | Tabelle | Versione |
|-----------|---------|----------|
| Core | tenants, users, invoices, fiscal_deadlines, agent_events, categorization_feedback | v0.1 |
| Banking | bank_accounts, bank_transactions | v0.3 |
| Gap Contabili | expenses, expense_policies, assets, withholding_taxes, stamp_duties, accruals_deferrals | v0.3 |
| Fisco Avanzato | f24_documents, digital_preservation, cu_certificates, budgets | v0.4 |
| **Totale** | **18 tabelle + 22 indici** | v0.1-v0.4 |
