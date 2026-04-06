# Status Progetto: AgentFlow PMI
Ultimo aggiornamento: 2026-04-05

## Progetto
- **Nome**: AgentFlow PMI
- **Vision**: Controller aziendale AI per PMI italiane — copilota del CEO
- **Metodologia**: SDD (Spec-Driven Development)
- **Stack**: Python 3.12 + FastAPI | React 19 + TypeScript + Vite 8 + Tailwind 4 | PostgreSQL | Redis
- **CRM**: Interno PostgreSQL + Brevo email (ADR-009)
- **Deploy**: Railway

## Evoluzione Pivot
| Pivot | Data | Focus |
|-------|------|-------|
| 1 | 2026-03 | Cassetto fiscale come fonte primaria |
| 2 | 2026-03 | Analisi gap CEO (adempimenti, cruscotto) |
| 3 | 2026-03 | Sistema agentico conversazionale |
| 4 | 2026-03 | Fatturazione attiva + costi personale |
| 5 | 2026-03 | Controller AI: import silenziosi, budget agent, puzzle dashboard |
| **6** | **2026-04** | **IVA scorporo, scadenzario, cash flow, fidi, anticipi fatture** |
| **7** | **2026-04** | **CRM Sales interno + Brevo email marketing + Kanban** |
| **8** | **2026-04** | **Social Selling configurabile + Ruoli fractional + Catalogo prodotti + Analytics multi-canale** |
| **9** | **2026-04** | **v3.0: Dual pipeline (T&M+Corpo+Elevia), Sales Agent AI, Resource Matching, ATECO Engine, Cross-sell** |

## Numeri del Progetto

| Metrica | Valore |
|---------|--------|
| **Stories totali implementate** | **91+** |
| **Test PASS** | **809+** (789 precedenti + 20 Calendar) |
| **Sprint completati** | **33** |
| **Endpoint API** | **196+** |
| **Modelli DB** | **50+** tabelle |
| **Pagine frontend** | **56+** |
| **Route frontend** | **50+** |
| **React Query hooks** | **130+** |

## Sprint 1-10: Base COMPLETATA (v0.1-v0.4)
- 40/40 stories, 369 test PASS, 224 SP
- Auth, SPID, fatture, parsing XML, categorizzazione, partita doppia
- Open Banking, riconciliazione, cash flow, note spese, cespiti
- F24, CU, conservazione digitale, Dashboard CEO, Budget

## Sprint 11-16: Pivot 5 — Controller AI
- Import pipeline (PDF, banca, paghe, corrispettivi, F24, bilancio)
- Self-healing LLM extraction
- Budget wizard conversazionale
- Puzzle Dashboard setup visivo
- Chatbot orchestratore 19+ tools
- Sidebar riorganizzata, fattura attiva multi-linea

## Pivot 6 COMPLETATO — Sprint 17-22 (2026-04-02)
**17 stories (US-70→US-86), 72 SP, 75 test PASS**

| Sprint | Focus | Stories | Test |
|--------|-------|---------|------|
| 17 | IVA scorporo + modelli DB | US-70/71/84/85/86 | 13 |
| 18 | Scadenzario attivo/passivo | US-72/73/74 | 19 |
| 19 | Chiusura scadenze + insoluti + cash flow | US-75/76/77 | 16 |
| 20 | Cash flow per banca + config fidi | US-78/79 | 9 |
| 21 | Anticipo fatture completo | US-80/81/82 | 14 |
| 22 | Confronto costi anticipo | US-83 | 4 |

**Funzionalita:**
- Dashboard e Budget usano `importo_netto` (IVA scorporata)
- Widget IVA Netta (debito - credito = da versare)
- Scadenzario attivo (crediti) e passivo (debiti) con colori, filtri, totali
- Generazione automatica scadenze da fatture
- Chiusura scadenze (full/parziale), gestione insoluti
- Cash flow previsionale 30/60/90 giorni con alert soglia
- Cash flow per banca separato
- Fidi bancari: CRUD plafond, tasso, commissioni per banca
- Anticipo fatture: presentazione, verifica plafond, incasso, insoluto
- Confronto costi anticipo tra banche (migliore evidenziata)

## Pivot 7 COMPLETATO — Sprint 23-27 (2026-04-03)
**13 stories (US-87→US-99), 63 SP, 67 test PASS**

| Sprint | Focus | Stories | Test |
|--------|-------|---------|------|
| 23 | CRM modelli DB + migrazione Odoo→interno | US-87/88/89/99 | 23 |
| 24 | Kanban drag-and-drop + pipeline analytics | US-90/91 | 8 |
| 25 | Adapter Brevo + webhook tracking + template | US-92/93/94 | 16 |
| 26 | Invio email singola + dashboard analytics | US-95/96 | 10 |
| 27 | Sequenze email automatiche + trigger | US-97/98 | 10 |

**CRM Sales (ADR-009 — Odoo rimosso come dipendenza):**
- 4 modelli DB: CrmContact, CrmPipelineStage, CrmDeal, CrmActivity
- Pipeline: Nuovo Lead → Qualificato → Proposta → Ordine Ricevuto → Confermato → Perso
- 6 stadi default auto-creati, probabilita auto su cambio stage
- Deal type: T&M, fixed, spot, hardware (con daily_rate, estimated_days)
- Ordini cliente: 4 tipi (PO, email, firma_word, portale)
- Attivita: call, email, meeting, note, task con last_contact_at
- Kanban frontend drag-and-drop (HTML5 nativo + useOptimistic React 19)
- Analytics: weighted pipeline, conversion per stage, won/lost ratio
- 15+ endpoint REST per CRM

**Email Marketing (Brevo — 25 EUR/mese):**
- Adapter `api/adapters/brevo.py` async (invio + variable substitution)
- Webhook tracking: open (pixel), click (link), bounce, unsubscribe, spam
- Template email con variabili {{nome}}, {{azienda}}, {{deal_name}}
- 3 template default italiani (Benvenuto, Follow-up, Reminder)
- Preview template con dati campione
- Storico email per contatto con status tracking
- Dashboard analytics: open rate, click rate, bounce rate, breakdown per template, top contacts
- Sequenze multi-step con condizioni (if_opened, if_not_opened, if_clicked)
- Trigger automatici: deal_stage_changed (con filtro stage), contact_created
- Enrollment con protezione duplicati
- 10 endpoint REST per email marketing

## Pivot 8 IN CORSO — Sprint 28-32 (2026-04-05)
**21 stories (US-130→US-150) + 3 stories infra (US-109→US-111), 90 SP, 87 test PASS**

| Sprint | Focus | Stories | Test |
|--------|-------|---------|------|
| 28 | Origini + Activity Types + Pre-funnel | US-130→137 | 35 |
| 29 | RBAC Ruoli + Audit trail | US-138/141 | 13 |
| 30 | Catalogo Prodotti + Deal-Product | US-142→144 | 11 |
| 31 | Dashboard KPI + Scorecard + Compensi | US-146→150 | 14 |
| 32 | User Mgmt + Role-based UI + Company/Contact 1:N | US-109→111 + infra | 14 |

**Social Selling (5 moduli implementati):**
- M1 Origini: CRUD + migration + seed 4 default, filtro contatti per origine
- M2 Activity Types: CRUD + seed 8 default, pre-funnel stages con auto-reorder
- M3 RBAC: Ruoli custom + matrice permessi + seed 5 default, audit trail immutabile + CSV
- M4 Prodotti: Catalogo + categorie auto-create, deal-product M2M con revenue calc
- M5 Analytics: Dashboard KPI + Scorecard, compensi con regole tiered + confirm/pay

**Company/Contact 1:N Split:**
- `CrmCompany` (NEW): azienda separata da referente
- `CrmContact.company_id` FK: referente legato a 1 azienda, N referenti per azienda
- `CrmDeal.company_id` FK: deal appartiene ad azienda
- Frontend: form 2 step (seleziona/crea azienda → aggiungi referente)

**Role-Based UI:**
- Sidebar/BottomNav filtrata per `user.role` (admin/owner: tutto, commerciale: solo CRM)
- Dashboard admin: KPI finanziari (ricavi, costi, EBITDA)
- Dashboard commerciale: KPI vendite (pipeline, win rate, attivita)
- Scorecard auto-load per commerciale, dropdown utenti per admin
- Widget auto-reset se cambio ruolo (widget ID prefix a→admin, c→commerciale)

**External Users:**
- `User.user_type`: "internal"/"external" con `access_expires_at`
- Middleware check scadenza: auto-deactivazione utente scaduto
- CRM role assegnabile per utente, default origin/product per utente esterno
- Row-level filtering: commerciale vede solo propri deal/contatti

**Infrastruttura:**
- TipTap rich text editor per template email (toolbar, variabili quick-insert)
- Service Worker network-first per HTML (fix stale chunk post-deploy)
- ErrorBoundary auto-reload su "Failed to fetch dynamically imported module"
- Activity logging automatico su cambio fase pipeline (dialog ibrido)
- Planned activities con stile amber e bottone "Completa"

**30+ nuovi endpoint REST, 10 nuovi modelli DB, 8 nuove pagine frontend**

## Frontend PWA — Fase 1-4 COMPLETATE (2026-04-03)

| Fase | Cosa | Impatto |
|------|------|---------|
| **PWA Foundation** | manifest.json, sw.js, icons SVG, install prompt, offline indicator | App installabile |
| **Responsive** | Bottom nav 5 tab, safe areas iOS, touch targets 44px, 100dvh | Mobile-first |
| **React 19** | React.lazy (96 chunk), Suspense+SkeletonPage, useOptimistic, ErrorBoundary, PageMeta | Bundle -66% (1.27MB→432KB) |
| **Design System** | DM Sans, CSS variables (20+), dark mode prep, Skeleton components | Identita visiva |

**Frontend CRM (6 pagine):**
- `/crm` — Pipeline Kanban + dialog ibrido cambio fase + analytics
- `/crm/deals/:id` — Dettaglio deal + prodotti + timeline attivita + planned activities
- `/crm/deals/new` — Nuovo deal con selettore stage + prima attivita
- `/crm/contatti` — Contatti con form 2 step (azienda → referente) + invio email
- `/crm/deals/:id` — Bottone Modifica + registrazione ordine

**Frontend Social Selling (8 pagine):**
- `/social/origini` — CRUD origini con edit inline, toggle, delete
- `/social/tipi-attivita` — CRUD tipi attivita con badge categorie
- `/social/prodotti` — Card grid prodotti con edit, badge pricing
- `/social/ruoli` — Matrice RBAC con checkbox entity/permission
- `/social/audit` — Log immutabile con filtri, paginazione, CSV export
- `/social/scorecard` — KPI cards (auto-load commerciale, dropdown admin)
- `/social/compensi` — Compensi mensili con calculate/confirm/pay
- `/social/pipeline-settings` — Gestione stadi + pre-funnel

**Sidebar filtrata per ruolo:**
- **Admin/Owner** (tutte le sezioni):
  1. Principale: Setup, Dashboard, Budget
  2. Operativo: Fatture, Banca, Personale, Spese, Corrispettivi
  3. Commerciale: Pipeline CRM, Contatti, Email Template, Sequenze, Email Stats, Scorecard
  4. Gestione: Import, Scadenzario, Fisco
  5. Sistema: Chat, Report, Impostazioni
- **Commerciale** (solo sezione vendite):
  Dashboard, Pipeline CRM, Contatti, Email Template, Sequenze, Email Stats, Scorecard, Chat

**ChatbotFloating**: visibile solo su Dashboard e Chat (rimosso da tutte le altre pagine)

## Pagine Frontend DA COMPLETARE

| Pagina | Backend pronto | Priorita |
|--------|---------------|----------|
| Aziende CRM (pagina dedicata /crm/aziende) | CRUD companies | Alta |
| Scadenzario (riscrivere con nuovi endpoint) | 12 endpoint | Alta |
| Email Analytics dashboard | GET /email/analytics | Media |
| Email Sequenze (creazione/gestione) | CRUD sequenze | Media |
| Cash Flow da scadenzario | GET /scadenzario/cash-flow | Media |
| Fidi bancari config | GET/POST /fidi | Bassa |
| Anticipo fatture UI | POST anticipa/incassa/insoluto | Bassa |
| Calendar integration (Google/Outlook/Calendly) | Non iniziato | Futura |

## Decisioni Architetturali Recenti

### ADR-009: CRM Interno + Brevo (2026-04-03)
- **Keap scartato**: $400+/mese, no italiano, no EUR, acquisita Thryv
- **Odoo declassato**: non necessario — CRM costruito internamente
- **Brevo scelto**: 25 EUR/mese per email tracking (open/click/bounce)
- **Pattern**: build logic (sequenze, template, analytics) / buy infrastructure (SMTP, deliverability)
- **Costo totale**: 300 EUR/anno (vs 5.600 Keap, vs 0-1.100 Odoo)
- Odoo resta come opzione bundle per clienti (partnership Achraf Kanice)

## Servizi Esterni
| Servizio | Status | Note |
|----------|--------|------|
| FiscoAPI | Integrato | Free plan esaurito |
| A-Cube | Integrato | SDI |
| Salt Edge | In attesa | Test mode approvazione |
| Brevo | Da configurare | Account + API key + webhook |
| Odoo 18 | Opzionale | Bundle clienti, partnership |

## Documenti Tecnici
- `specs/technical/ADR-009-crm-interno-brevo.md` — CRM + Brevo decisione
- `specs/03-user-stories-pivot6.md` — 17 stories IVA/scadenzari/anticipi
- `specs/03-user-stories-pivot7-crm.md` — 13 stories CRM/email
- `specs/07-implementation.md` — Log implementazione Sprint 1-27
- `brainstorm/12-crm-interno-brevo-email.md` — Analisi completa CRM+email
- `Docs/Analisi_Frontend_PWA_Roadmap.md` — Roadmap PWA 6 fasi
- `Docs/Guida_Setup_Odoo18_CRM.md` — Setup Odoo (opzionale)

## Pivot 8 — Social Selling Configurabile (implementazione in corso)

**5 moduli — architettura Core Engine + Configuration Layer:**

| Modulo | Descrizione | Sprint | Stato |
|--------|-------------|--------|-------|
| M1 — Origini configurabili | US-130→133 | 28 | **COMPLETATO** (18 test) |
| M2 — Attività e pre-funnel | US-134→137 | 28 | **COMPLETATO** (17 test) |
| M3 — Ruoli e collaboratori esterni | US-138/141 + US-109→111 | 29/32 | **COMPLETATO** (27 test) |
| M4 — Catalogo prodotti | US-142→144 | 30 | **COMPLETATO** (11 test) |
| M5 — Analytics e compensi | US-146→150 | 31 | **COMPLETATO** (14 test) |
| — Company/Contact 1:N + Role UI | Sprint 32 infra | 32 | **COMPLETATO** (14 test) |

**Stories residue (parziali):** US-139 (external users E2E), US-140 (origin filter E2E), US-145 (pipeline filter per prodotto)

**Documentazione:**
- `Docs/Spec_Modulo_Social_Selling.md` — Spec prodotto completa
- `specs/03-user-stories-pivot8-social.md` — 21 user stories, 120 SP
- `specs/04-tech-spec-pivot8.md` — Tech spec: 32 endpoint, 11 tabelle, 21 BR
- `specs/database/schema-pivot8.md` — DDL SQL completo con migrations
- `specs/ux/wireframes-pivot8.md` — 10 wireframe ASCII
- `brainstorm/13-15-social-selling-*.md` — Brainstorming strutturato

## Prossimi Passi
1. ~~User Stories Pivot 8~~ ✅ 21 stories, 120 SP
2. ~~Tech Spec Pivot 8~~ ✅ 32+ endpoint, 11 tabelle, 21 BR
3. ~~Sprint Planning Pivot 8~~ ✅ 6 sprint (100-105)
4. ~~Implementazione Pivot 8~~ ✅ 21 stories, 87 test, 30+ endpoint, 10 modelli DB
5. ~~Company/Contact 1:N split~~ ✅ CrmCompany, form 2 step
6. ~~Role-based UI~~ ✅ Sidebar, Dashboard, Scorecard filtrati per ruolo
7. **Pagina Aziende CRM** — `/crm/aziende` per gestione diretta
8. **Update New Deal form** — seleziona Company invece di Contact
9. **Frontend scadenzario** — riscrivere con nuovi endpoint
10. ~~Calendar integration~~ ✅ FullCalendar + .ics + Microsoft 365 OAuth + Calendly
11. **Account Brevo** — creare, API key, webhook
12. **Test E2E** Playwright
13. **Deploy** su Railway

---
_Ultimo aggiornamento: 2026-04-05 — Pivot 8 Social Selling implementato, Company/Contact 1:N, Role-based UI_
