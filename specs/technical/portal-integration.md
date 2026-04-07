# ADR-011: Integrazione AgentFlow ↔ PortalJS.be

**Data**: 2026-04-07
**Stato**: Approvato
**Decisione**: Integrazione progressiva (Light → Auto-Sync → AI) con conferma umana obbligatoria

---

## Contesto

AgentFlow gestisce il ciclo commerciale (Lead → Ordine). PortalJS.be gestisce il ciclo operativo (Commesse → Rapportini → Dipendenti). Serve un ponte tra i due sistemi per:
1. Creare commesse quando un deal viene confermato
2. Assegnare collaboratori alle commesse
3. Leggere ore fatte e stato avanzamento per monitoraggio margini

## Principi architetturali

1. **Conferma umana obbligatoria** — nessuna scrittura automatica su Portal senza OK esplicito
2. **Portal è master per dati operativi** — rapportini, ore, stato commessa
3. **AgentFlow è master per dati commerciali** — deal, pipeline, valore, margine
4. **Nessuna sync bidirezionale** — flusso unidirezionale per ogni dato
5. **Service account** — AgentFlow si autentica su Portal con account dedicato (ruolo AMMI)

---

## Architettura

```
AgentFlow                         PortalJS.be (NestJS + Prisma + PostgreSQL)
   │                                   │
   │  ── SCRITTURA (con conferma) ──   │
   │  POST /projects/create ─────────→ │  Crea commessa
   │  POST /activities/create ───────→ │  Assegna collaboratore
   │                                   │
   │  ── LETTURA (automatica) ──       │
   │ ←── GET /crud/Person              │  Dipendenti + contratti
   │ ←── GET /crud/EmploymentContract  │  Costi, tariffe, CCNL
   │ ←── GET /crud/Timesheet           │  Rapportini mensili
   │ ←── GET /crud/TimesheetDetail     │  Dettaglio ore giornaliero
   │ ←── GET /crud/Project             │  Stato commesse
   │ ←── GET /crud/Customer            │  Anagrafica clienti
   │ ←── GET /crud/Activity            │  Assegnazioni attive
```

---

## Stack tecnico PortalJS.be

| Componente | Tecnologia |
|---|---|
| Backend | NestJS 10 (TypeScript) |
| ORM | Prisma 5.15 |
| Database | PostgreSQL |
| Auth | JWT + Azure AD + Google OAuth |
| API | REST, prefix `/api/v1`, Swagger a `/api` |
| CRUD generico | `GET/POST /crud/:resourceType` |

---

## Mapping dati

### Deal → Project (Commessa)

| AgentFlow (CrmDeal) | PortalJS (Project) | Note |
|---|---|---|
| `name` | `name` | Nome opportunità |
| `company_id` → CrmCompany.name | `customer_id` | Match per P.IVA o crea nuovo |
| `deal_type = "T&M"` | `billing_type: "Daily"` | |
| `deal_type = "fixed"` | `billing_type: "LumpSum"` | |
| `deal_type = "spot"` | `billing_type: "LumpSum"` | |
| `expected_revenue` | `amount` | Valore commessa |
| `daily_rate` | `rate` | Solo per T&M |
| auto-generato | `project_code` | `AF-{deal_id[:8]}` |
| `assigned_to` (commerciale) | `accountManager_id` | Match per email |
| pipeline_template → vendita_diretta | `project_type_id` → Consulenza | Mapping configurabile |
| pipeline_template → progetto_corpo | `project_type_id` → Progetto | |

### Resource → Activity (Assegnazione)

| AgentFlow (Resource) | PortalJS (Activity) | Note |
|---|---|---|
| `resource.name` | `person_id` | Match per employee_id o nome |
| deal.start_date o oggi | `start_date` | Inizio assegnazione |
| deal.start_date + estimated_days | `end_date` | Fine stimata |
| `daily_rate` (vendita) | `rate` | Tariffa cliente |
| `expected_revenue` | `amount` | Valore assegnazione |
| auto-generato | `code` | `AF-{deal_id[:4]}-{resource_id[:4]}` |
| tipo attività "produttiva" | `activityType_id` | Da configurare su Portal |

### Timesheet → AgentFlow (lettura)

| PortalJS (Timesheet/Detail) | AgentFlow (uso) |
|---|---|
| `employee_id` + `year` + `month` | Identificazione rapportino |
| `TimesheetDetail.hours` + `minutes` | Ore lavorate per attività |
| `finalized` | Solo rapportini finalizzati sono affidabili |
| `activity_id` → `project_id` | Collegamento ore → commessa → deal |
| Somma ore per commessa | Confronto con `estimated_days` del deal |

---

## Fasi implementazione

### Fase 1: Portal Client + Lettura (Sprint 35 — 5 SP)

**File**: `api/adapters/portal_client.py`

```python
class PortalClient:
    """Async client per PortalJS.be API."""

    def __init__(self, base_url: str, email: str, password: str):
        self.base_url = base_url
        self.token = None

    async def authenticate(self) -> str:
        """Login con service account → JWT token."""

    # ── LETTURA ──
    async def list_persons(self, include=True) -> list[dict]:
        """GET /crud/Person — dipendenti con contratti."""

    async def list_customers(self) -> list[dict]:
        """GET /crud/Customer — clienti."""

    async def list_projects(self, include=True) -> list[dict]:
        """GET /crud/Project — commesse attive."""

    async def list_activities_for_project(self, project_id: int) -> list[dict]:
        """GET /crud/Activity — assegnazioni per commessa."""

    async def get_timesheets(self, year: int, month: int) -> list[dict]:
        """GET /crud/Timesheet — rapportini mensili."""

    async def get_timesheet_details(self, timesheet_id: int) -> list[dict]:
        """GET /crud/TimesheetDetail — ore giornaliere."""
```

**Endpoint AgentFlow (lettura proxy):**
- `GET /api/v1/portal/persons` — lista dipendenti (cache 15 min)
- `GET /api/v1/portal/projects` — lista commesse
- `GET /api/v1/portal/timesheets?year=2026&month=4` — rapportini
- `GET /api/v1/portal/project/{id}/hours` — ore fatte per commessa

**Env vars:**
```
PORTAL_API_URL=https://portal.iridia.tech/api/v1
PORTAL_SERVICE_EMAIL=agentflow@iridia.tech
PORTAL_SERVICE_PASSWORD=xxx
```

### Fase 2: Creazione Commessa con conferma umana (Sprint 36 — 8 SP)

**Trigger**: Deal passa a "Confermato" (Won)

**Flusso UX:**
1. Deal detail mostra bottone "Crea Commessa su Portal"
2. Click → modale di conferma con dati pre-compilati:
   - Nome commessa (dal deal)
   - Cliente (match per P.IVA o nuovo)
   - Tipo fatturazione (Daily/LumpSum da deal_type)
   - Importo
   - Date inizio/fine
   - Account Manager
3. Utente conferma → AgentFlow chiama Portal API
4. Successo → salva `portal_project_id` sul deal
5. Errore → mostra messaggio, riprova

**Endpoint AgentFlow (scrittura con conferma):**
```
POST /api/v1/portal/projects/create-from-deal
Body: { deal_id, project_code?, customer_match?, ... }
Response: { portal_project_id, status }
```

**Campo nuovo su CrmDeal:**
```python
portal_project_id: Mapped[int | None]  # FK verso Portal Project.id
portal_synced_at: Mapped[datetime | None]  # Ultimo sync
```

**Portal API chiamata:**
```
POST /projects/create
{
  project_code: "AF-{deal_id[:8]}",
  name: deal.name,
  customer_id: matched_customer_id,
  billing_type: "Daily" | "LumpSum",
  amount: deal.expected_revenue,
  rate: deal.daily_rate (se T&M),
  start_date: oggi,
  end_date: oggi + estimated_days,
  accountManager_id: matched_account_id,
  project_type_id: mapped_from_pipeline
}
```

### Fase 3: Assegnazione Collaboratori con conferma (Sprint 37 — 8 SP)

**Trigger**: Utente clicca "Assegna collaboratore" nella commessa

**Flusso UX:**
1. Sezione "Risorse" nel deal detail (solo se portal_project_id esiste)
2. Dropdown con dipendenti da Portal (GET /crud/Person)
3. Seleziona persona + date + tariffa
4. Conferma → AgentFlow chiama Portal API
5. Successo → mostra assegnazione attiva

**Endpoint AgentFlow:**
```
POST /api/v1/portal/activities/create-assignment
Body: { deal_id, person_id, start_date, end_date, rate, amount }
```

**Portal API chiamata:**
```
POST /activities/create
{
  code: "AF-{deal_id[:4]}-{person_id}",
  project_id: deal.portal_project_id,
  person_id: person_id,
  start_date: "2026-04-10",
  end_date: "2026-07-10",
  rate: 600,
  amount: 36000,
  activityType_id: productive_type_id
}
```

### Fase 4: Sync Rapportini → Dashboard Margini (Sprint 38 — 5 SP)

**Job periodico** (ogni 6 ore o on-demand):
1. Per ogni deal con `portal_project_id`:
   - GET activities per quel project
   - GET timesheet details per quelle activities
   - Calcola ore totali fatte
   - Confronta con `estimated_days * 8` (ore pianificate)
   - Calcola margine reale: `(hours_worked * daily_rate) - (hours_worked * daily_cost)`
2. Salva su CrmDeal: `portal_hours_worked`, `portal_margin_actual`
3. Alert se `hours_worked > 80% * estimated_hours`

**Frontend — Deal Detail:**
- Sezione "Avanzamento Operativo" (solo se portal_project_id)
  - Ore fatte: 120h / 480h pianificate (25%)
  - Margine reale: 18.000 € (30%)
  - Barra progresso verde/giallo/rosso
  - Link ai rapportini su Portal

### Fase 5: AI Agent Integration (Sprint 39+ — future)

Il Sales Agent può:
- Suggerire "Questo deal è Won, vuoi creare la commessa?"
- Auto-match risorse AgentFlow ↔ Person Portal per competenze
- Monitorare avanzamento e suggerire: "Progetto al 80% ore, contatta il cliente per estensione"
- Generare fattura pro-forma da timesheet finalizzati

---

## Configurazione Portal su AgentFlow

### Nuova tabella: `PortalConfig`

```python
class PortalConfig(Base):
    __tablename__ = "portal_config"
    id: Mapped[uuid.UUID]
    tenant_id: Mapped[uuid.UUID]
    portal_url: Mapped[str]  # https://portal.iridia.tech/api/v1
    service_email: Mapped[str]
    service_password_encrypted: Mapped[str]  # AES encrypted
    default_project_type_id: Mapped[int | None]
    default_activity_type_id: Mapped[int | None]
    sync_enabled: Mapped[bool] = True
    last_sync_at: Mapped[datetime | None]
```

### Mapping tabella: `PortalMapping`

```python
class PortalMapping(Base):
    __tablename__ = "portal_mappings"
    id: Mapped[uuid.UUID]
    tenant_id: Mapped[uuid.UUID]
    entity_type: Mapped[str]  # "customer", "person", "project_type"
    agentflow_id: Mapped[str]  # UUID del record AgentFlow
    portal_id: Mapped[int]  # ID numerico del record Portal
```

---

## Rischi e mitigazioni

| Rischio | Mitigazione |
|---|---|
| Portal down quando serve | Retry con exponential backoff, stato "pending" |
| Customer non esiste su Portal | Pre-check + creazione automatica (con conferma) |
| Person match ambiguo | Match per employee_id o taxCode, fallback manuale |
| Dati inconsistenti | Portal è master operativo, AgentFlow è master commerciale |
| Token JWT scade | Auto-refresh prima di ogni chiamata |
| Rate limiting Portal | Cache lettura 15 min, batch per scritture |

---

## Story breakdown (per /dev-implement)

| ID | Story | SP | Sprint | Tipo |
|---|---|---|---|---|
| US-230 | Portal Client adapter (auth + read) | 5 | 35 | Backend |
| US-231 | Read persons + employment contracts | 3 | 35 | Backend |
| US-232 | Read projects + timesheets | 3 | 35 | Backend |
| US-233 | Proxy endpoints `/portal/*` | 3 | 35 | Backend |
| US-234 | Create Project from Deal (con conferma) | 8 | 36 | Full-stack |
| US-235 | Customer matching/creation su Portal | 3 | 36 | Backend |
| US-236 | Deal detail: bottone "Crea Commessa" | 3 | 36 | Frontend |
| US-237 | Create Activity/Assignment (con conferma) | 8 | 37 | Full-stack |
| US-238 | Deal detail: sezione "Risorse assegnate" | 3 | 37 | Frontend |
| US-239 | Timesheet sync job + margine reale | 5 | 38 | Backend |
| US-240 | Deal detail: "Avanzamento Operativo" | 3 | 38 | Frontend |
| US-241 | PortalConfig + PortalMapping admin | 3 | 38 | Full-stack |

**Totale: 50 SP, 4 sprint (35-38)**

---

## Test E2E previsti

Per ogni fase, test contro Portal di staging:

1. **Fase 1**: Read persons, read projects, read timesheets → verificare dati restituiti
2. **Fase 2**: Create project from deal Won → verificare su Portal che esiste
3. **Fase 3**: Create activity/assignment → verificare su Portal
4. **Fase 4**: Sync timesheet → verificare ore e margine su AgentFlow

**Totale stimato: 40+ E2E test**
