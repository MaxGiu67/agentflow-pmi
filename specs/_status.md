# Status Progetto: AgentFlow PMI
Ultimo aggiornamento: 2026-04-03

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

## Numeri del Progetto

| Metrica | Valore |
|---------|--------|
| **Stories totali implementate** | **70+** |
| **Test PASS** | **511+** (369 base + 75 Pivot 6 + 67 Pivot 7) |
| **Sprint completati** | **27** |
| **Endpoint API** | **160+** |
| **Modelli DB** | **40+** tabelle |
| **Pagine frontend** | **48+** |
| **Route frontend** | **42** |
| **React Query hooks** | **100+** |

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

## Frontend PWA — Fase 1-4 COMPLETATE (2026-04-03)

| Fase | Cosa | Impatto |
|------|------|---------|
| **PWA Foundation** | manifest.json, sw.js, icons SVG, install prompt, offline indicator | App installabile |
| **Responsive** | Bottom nav 5 tab, safe areas iOS, touch targets 44px, 100dvh | Mobile-first |
| **React 19** | React.lazy (96 chunk), Suspense+SkeletonPage, useOptimistic, ErrorBoundary, PageMeta | Bundle -66% (1.27MB→432KB) |
| **Design System** | DM Sans, CSS variables (20+), dark mode prep, Skeleton components | Identita visiva |

**Frontend CRM (3 pagine):**
- `/crm` — Pipeline Kanban drag-and-drop + analytics bar + toggle tabella
- `/crm/deals/:id` — Dettaglio deal + registrazione ordine + conferma
- `/crm/contatti` — Lista contatti con ricerca + creazione

**Sidebar aggiornata (5 sezioni):**
1. Principale: Setup, Dashboard, Budget
2. Operativo: Fatture, Banca, Personale, Spese, Corrispettivi
3. **Commerciale: Pipeline CRM, Contatti**
4. Gestione: Import, Scadenzario, Fisco
5. Sistema: Chat, Report, Impostazioni

**ChatbotFloating**: visibile solo su Dashboard e Chat (rimosso da tutte le altre pagine)

## Pagine Frontend DA COMPLETARE

| Pagina | Backend pronto | Priorita |
|--------|---------------|----------|
| Scadenzario (riscrivere con nuovi endpoint) | 12 endpoint | Alta |
| Email Templates (gestione) | CRUD + preview | Alta |
| Email Invio (da dettaglio contatto/deal) | POST /email/send | Alta |
| Email Analytics dashboard | GET /email/analytics | Media |
| Email Sequenze (creazione/gestione) | CRUD sequenze | Media |
| Cash Flow da scadenzario | GET /scadenzario/cash-flow | Media |
| Fidi bancari config | GET/POST /fidi | Bassa |
| Anticipo fatture UI | POST anticipa/incassa/insoluto | Bassa |

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

## Pivot 8 — Social Selling Configurabile (in corso)

**5 moduli — architettura Core Engine + Configuration Layer:**

| Modulo | Descrizione | Sprint | Stato |
|--------|-------------|--------|-------|
| M1 — Origini configurabili | US-100→103 (21 SP) | TBD | Stories pronte |
| M2 — Attività e pre-funnel | US-104→107 (18 SP) | TBD | Stories pronte |
| M3 — Ruoli e collaboratori esterni | US-108→111 (29 SP) | TBD | Stories pronte |
| M4 — Catalogo prodotti | US-112→115 (18 SP) | TBD | Stories pronte |
| M5 — Analytics e compensi | US-116→120 (34 SP) | TBD | Stories pronte |

**Documentazione:**
- `Docs/Spec_Modulo_Social_Selling.md` — Spec prodotto completa
- `brainstorm/13-15-social-selling-*.md` — Brainstorming strutturato

## Prossimi Passi
1. **User Stories Pivot 8** — generare stories per i 5 moduli
2. **Tech Spec Pivot 8** — schema DB, endpoint API, componenti frontend
3. **Sprint Planning** — organizzare stories in sprint
4. **Frontend scadenzario** — riscrivere con nuovi endpoint
5. **Frontend email** — template + invio dal CRM
6. **Account Brevo** — creare, API key, webhook
7. **Test E2E** Playwright
8. **Deploy** su Railway

---
_Ultimo aggiornamento: 2026-04-04 — Pivot 8 Social Selling_
