# Test Strategy — AgentFlow PMI

**Aggiornato:** 2026-03-22
**Stack:** Python 3.12 + FastAPI + PostgreSQL 16 + Redis + Odoo CE 18

---

## Framework e Librerie

| Tool | Uso | Motivazione |
|------|-----|-------------|
| **pytest** 8.x | Unit + integration | Standard Python, fixtures potenti, plugin ecosystem |
| **pytest-cov** | Coverage | Report HTML + CI badge |
| **pytest-asyncio** | Test async | FastAPI e async, serve support nativo |
| **httpx** (AsyncClient) | Test API | Client async per TestClient FastAPI |
| **factory-boy** | Test data | Factory pattern per generare dati realistici |
| **pytest-redis** | Redis mock | Test pub/sub, cache, events |
| **Playwright** | E2E browser | Cross-browser, async, screenshot su failure |
| **Faker** (it_IT) | Dati italiani | P.IVA, CF, IBAN, nomi italiani realistici |

---

## Configurazione Base

### pytest.ini / pyproject.toml

```toml
[tool.pytest.ini_options]
testpaths = ["tests", "api/modules"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
asyncio_mode = "auto"
markers = [
    "unit: unit tests (fast, no DB)",
    "integration: integration tests (needs DB + Redis)",
    "e2e: end-to-end browser tests (needs full stack)",
    "slow: tests that take >5s",
]

[tool.coverage.run]
source = ["api"]
omit = ["*/tests/*", "*/migrations/*", "*/__tests__/*"]

[tool.coverage.report]
fail_under = 70
show_missing = true
```

---

## Directory Structure

```
tests/
├── conftest.py                     # Fixtures globali: DB, Redis, tenant, user, token JWT
├── factories/
│   ├── __init__.py
│   ├── tenant_factory.py           # TenantFactory (SRL, P.IVA, forfettario...)
│   ├── user_factory.py             # UserFactory (owner, admin, viewer)
│   ├── invoice_factory.py          # InvoiceFactory (attiva, passiva, TD01, TD04)
│   ├── expense_factory.py          # ExpenseFactory (draft, approved, rejected)
│   ├── asset_factory.py            # AssetFactory (active, disposed, fully_depreciated)
│   └── bank_factory.py             # BankAccountFactory, TransactionFactory
├── fixtures/
│   ├── sample_fatturapa.xml        # XML FatturaPA di esempio (TD01)
│   ├── sample_nota_credito.xml     # XML nota di credito (TD04)
│   ├── sample_ritenuta.xml         # XML con <DatiRitenuta>
│   └── sample_receipt.jpg          # Scontrino di test per OCR
├── integration/
│   ├── test_auth_api.py            # Register, login, SPID flow
│   ├── test_invoices_api.py        # CRUD fatture, upload, verify
│   ├── test_expenses_api.py        # CRUD note spese, approvazione
│   ├── test_assets_api.py          # Cespiti, ammortamento, dismissione
│   ├── test_withholding_api.py     # Ritenute, CU
│   ├── test_fiscal_api.py          # Bollo, ratei, F24
│   ├── test_preservation_api.py    # Conservazione digitale
│   ├── test_banking_api.py         # Conti, movimenti, riconciliazione
│   ├── test_ceo_api.py             # Dashboard CEO, budget
│   └── test_deadlines_api.py       # Scadenzario
└── e2e/
    ├── test_onboarding.py          # SPID → cassetto → prima fattura (US-16)
    ├── test_invoice_flow.py        # Download → parse → categorize → register (US-04→US-13)
    ├── test_expense_flow.py        # Upload → approve → reimburse (US-29→US-30)
    ├── test_f24_flow.py            # Liquidazione → F24 → export (US-22→US-38)
    └── test_ceo_dashboard.py       # Dashboard con dati → KPI → budget (US-39→US-40)

api/modules/
├── expenses/__tests__/
│   ├── test_expense_service.py     # Policy check, OCR, auto-approvazione
│   └── test_expense_schemas.py     # Validazione input
├── assets/__tests__/
│   ├── test_depreciation.py        # Calcolo quote, pro-rata, tabelle ministeriali
│   └── test_disposal.py            # Plus/minusvalenza, rottamazione
├── withholding/__tests__/
│   ├── test_withholding_service.py # Riconoscimento da XML, calcolo netto
│   └── test_cu_generator.py        # Generazione CU formato ministeriale
├── fiscal/__tests__/
│   ├── test_stamp_duty.py          # Bollo: soglia, trimestre, mista
│   ├── test_accruals.py            # Ratei/risconti: competenza, pro-rata
│   └── test_f24_generator.py       # F24: multi-sezione, compensazione
├── preservation/__tests__/
│   └── test_preservation_service.py # Batch, retry, rifiuto
├── ceo/__tests__/
│   ├── test_kpi_service.py         # DSO, DPO, EBITDA, concentrazione
│   └── test_budget_service.py      # Budget vs consuntivo, proiezione
└── ...
```

---

## Coverage Targets

| Livello | Target | Cosa Testa | CI Gate |
|---------|--------|------------|---------|
| **Unit** | 80% | Business logic (ammortamento, ritenute, bollo, ratei, F24, KPI), validators (P.IVA, IBAN, CF), adapters (FiscoAPI mock, Odoo mock) | Fail build se < 70% |
| **Integration** | 60% | API endpoints (request/response/status), DB queries (CRUD, dedup, indici), Redis events (pub/sub, dead letter) | Fail build se < 50% |
| **E2E** | Critical paths | 5 flussi critici: onboarding, fattura, note spese, F24, dashboard CEO | Fail build se 1+ path fallisce |

---

## Fixtures Principali (conftest.py)

```python
@pytest.fixture
async def db_session():
    """PostgreSQL test DB, rollback after each test."""

@pytest.fixture
async def redis_client():
    """Redis test instance, flush after each test."""

@pytest.fixture
async def tenant(db_session):
    """Tenant SRL ordinario di default."""

@pytest.fixture
async def owner_user(db_session, tenant):
    """User owner con JWT valido."""

@pytest.fixture
async def auth_client(owner_user):
    """httpx AsyncClient con JWT header."""

@pytest.fixture
async def sample_invoice(db_session, tenant):
    """Fattura passiva registrata con categoria."""

@pytest.fixture
async def odoo_mock():
    """Mock Odoo XML-RPC/JSON-2 per test senza Odoo."""
```

---

## Test Prioritari per le Nuove Stories

| Story | Test Critici | Tipo |
|-------|-------------|------|
| US-29 | OCR scontrino, policy check (>€25), valuta estera, duplicato | Unit + Integration |
| US-30 | Auto-approvazione titolare, rimborso PISP fallito, registrazione dare/avere | Unit + Integration |
| US-31 | Soglia €516,46, aliquota ministeriale, pro-rata primo anno, fattura cumulativa | Unit |
| US-32 | Plus/minusvalenza, pro-rata dismissione, rottamazione | Unit |
| US-33 | Parsing <DatiRitenuta>, aliquote 20/23/26/30%, calcolo netto, scadenza F24 | Unit + Integration |
| US-34 | Generazione CU, rivalsa INPS 4%, ritenute non versate warning | Integration |
| US-35 | Soglia €77,16, fattura mista, conteggio trimestrale, bollo passive | Unit |
| US-36 | Risconto pro-rata, rateo passivo, scrittura assestamento + riapertura | Unit |
| US-37 | Batch invio, retry su errore, rifiuto provider, nota credito post-conservazione | Integration |
| US-38 | F24 multi-sezione, compensazione crediti, export PDF/telematico | Unit + Integration |
| US-39 | DSO/DPO, concentrazione clienti >60%, dati insufficienti, YoY | Unit + Integration |
| US-40 | Budget vs consuntivo, scostamento >10%, proiezione, voce non prevista | Unit + Integration |
