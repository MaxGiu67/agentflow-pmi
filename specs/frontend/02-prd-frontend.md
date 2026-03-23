# PRD Frontend — ContaBot React SPA

**Progetto:** AgentFlow PMI — Frontend
**Data:** 2026-03-23
**Fase:** 2 — Product Requirements Document (Frontend)
**Backend:** 96 endpoint REST pronti, 369 test PASS

---

## Overview

ContaBot e il primo agente contabile AI per PMI italiane. Il backend Python/FastAPI e completo con 96 endpoint. Serve una SPA React che dia vita all'esperienza utente: dall'onboarding SPID alla dashboard CEO, passando per fatture, note spese, cespiti e scadenzario. L'interfaccia deve essere semplice come un'app consumer ma potente come un gestionale — pensata per titolari che non sono contabili.

---

## Personas Frontend

### P1: Marco — Titolare SRL (utente primario)
- **Device:** Desktop (70%), tablet (20%), mobile (10%)
- **Tech-savvy:** Medio-basso (usa WhatsApp, email, home banking)
- **Sessione tipo:** 5-10 min mattina (controllo dashboard), 20-30 min settimana (verifica fatture)
- **Priorita UX:** Speed, chiarezza, zero-learning-curve

### P2: Anna — Libera professionista (utente secondario)
- **Device:** Mobile (60%), desktop (40%)
- **Sessione tipo:** 2-3 min (upload scontrino), 10 min (verifica fatture settimanale)
- **Priorita UX:** Mobile-first, upload rapido, notifiche push

### P3: Dott. Rossi — Commercialista (utente partner)
- **Device:** Desktop (95%)
- **Sessione tipo:** 30 min (scarico report trimestrale, verifica scritture)
- **Priorita UX:** Export dati, tabelle dense, filtri avanzati

---

## Stack Tecnico

| Layer | Tecnologia | Motivazione |
|-------|-----------|-------------|
| Framework | **React 19 + TypeScript** | SPA, ecosystem maturo |
| Styling | **Tailwind CSS 4 + shadcn/ui** | Utility-first, componenti pronti, accessibili |
| State | **Zustand** | Leggero, no boilerplate |
| Data fetching | **TanStack Query (React Query)** | Cache, retry, optimistic updates |
| Routing | **React Router 7** | File-based routing |
| Forms | **React Hook Form + Zod** | Validazione type-safe |
| Charts | **Recharts** | Dashboard CEO, cash flow, trend |
| Tables | **TanStack Table** | Paginazione, filtri, sort |
| Date | **date-fns** | Leggero, locale it |
| i18n | Italiano nativo (no i18n framework per MVP) | Target solo Italia |
| Build | **Vite 6** | Fast HMR, ESBuild |
| Test | **Vitest + Testing Library** | Coerente con Vite |

---

## Requisiti Funzionali — Pagine

### Epic F1: Autenticazione e Onboarding

| # | Pagina | API Backend | Priorita |
|---|--------|-------------|----------|
| F1.1 | Login (email + password) | POST /auth/login | Must |
| F1.2 | Registrazione + verifica email | POST /auth/register, POST /auth/verify-email | Must |
| F1.3 | Password dimenticata | POST /auth/password-reset, POST /password-reset/confirm | Must |
| F1.4 | Onboarding wizard 4-step | GET/POST /onboarding/status, /onboarding/step/{n} | Must |
| F1.5 | Profilo azienda | GET/PATCH /profile | Must |

### Epic F2: Dashboard Operativa

| # | Pagina | API Backend | Priorita |
|---|--------|-------------|----------|
| F2.1 | Dashboard home (contatori, recenti, agenti) | GET /dashboard/summary, GET /agents/status | Must |
| F2.2 | Widget scadenze con countdown | GET /deadlines | Must |
| F2.3 | Widget cash flow mini-chart | GET /cashflow/prediction?days=30 | Should |

### Epic F3: Fatture

| # | Pagina | API Backend | Priorita |
|---|--------|-------------|----------|
| F3.1 | Lista fatture passive (filtri, paginazione) | GET /invoices?page=&status=&date_from= | Must |
| F3.2 | Dettaglio fattura | GET /invoices/{id} | Must |
| F3.3 | Verifica/conferma categoria | PATCH /invoices/{id}/verify | Must |
| F3.4 | Vista "Da verificare" con batch | GET /invoices/pending-review | Must |
| F3.5 | Upload fattura (drag & drop) | POST /invoices/upload | Must |
| F3.6 | Lista fatture attive + emissione | GET/POST /invoices/active | Should |
| F3.7 | Invio SDI + tracking stato | POST /invoices/active/{id}/send | Should |

### Epic F4: Contabilita

| # | Pagina | API Backend | Priorita |
|---|--------|-------------|----------|
| F4.1 | Piano dei conti | GET /accounting/chart | Must |
| F4.2 | Scritture contabili (journal entries) | GET /accounting/journal-entries | Must |
| F4.3 | Dettaglio scrittura (righe dare/avere) | GET /accounting/journal-entries/{id} | Must |
| F4.4 | Bilancio CEE | GET /accounting/balance-sheet?year= | Should |

### Epic F5: Fisco e Scadenze

| # | Pagina | API Backend | Priorita |
|---|--------|-------------|----------|
| F5.1 | Scadenzario (lista con countdown, colori) | GET /deadlines | Must |
| F5.2 | Alert fiscali personalizzati | GET /deadlines/alerts | Should |
| F5.3 | Liquidazione IVA | GET/POST /fiscal/vat-settlement | Should |
| F5.4 | F24 (genera, esporta, segna pagato) | GET/POST /f24, GET /f24/{id}/export | Should |
| F5.5 | Imposta di bollo trimestrale | GET /fiscal/stamp-duties | Could |
| F5.6 | Regole fiscali (informativo) | GET /fiscal/rules | Could |

### Epic F6: Banca e Cash Flow

| # | Pagina | API Backend | Priorita |
|---|--------|-------------|----------|
| F6.1 | Conti collegati + collega nuovo | GET /bank-accounts, POST /bank-accounts/connect | Should |
| F6.2 | Movimenti bancari | GET /bank-accounts/{id}/transactions | Should |
| F6.3 | Riconciliazione (suggerimenti + match) | GET /reconciliation/pending, POST /reconciliation/{tx_id}/match | Should |
| F6.4 | Cash flow predittivo (grafico 90gg) | GET /cashflow/prediction | Should |
| F6.5 | Pagamenti fornitori | POST /payments/execute | Could |

### Epic F7: Note Spese e Cespiti

| # | Pagina | API Backend | Priorita |
|---|--------|-------------|----------|
| F7.1 | Note spese (lista + upload scontrino) | GET/POST /expenses | Should |
| F7.2 | Approvazione/rifiuto spese | PATCH /expenses/{id}/approve, /reject | Should |
| F7.3 | Registro cespiti | GET /assets | Should |
| F7.4 | Dettaglio cespite + dismissione | GET /assets/{id}, POST /assets/{id}/dispose | Should |

### Epic F8: Adempimenti

| # | Pagina | API Backend | Priorita |
|---|--------|-------------|----------|
| F8.1 | Ritenute d'acconto | GET /withholding-taxes | Should |
| F8.2 | Certificazione Unica | GET /cu, POST /cu/generate/{year} | Could |
| F8.3 | Conservazione digitale | GET /preservation | Could |
| F8.4 | Monitor normativo | GET /normativo/alerts | Could |

### Epic F9: Cruscotto CEO (solo role=owner)

| # | Pagina | API Backend | Priorita |
|---|--------|-------------|----------|
| F9.1 | KPI principali + grafici | GET /ceo/dashboard | Should |
| F9.2 | Confronto YoY | GET /ceo/dashboard/yoy | Should |
| F9.3 | Budget vs consuntivo | GET/POST /ceo/budget | Should |
| F9.4 | Proiezione fine anno | GET /ceo/budget/projection | Could |
| F9.5 | Alert CEO | GET /ceo/alerts | Should |

### Epic F10: Impostazioni

| # | Pagina | API Backend | Priorita |
|---|--------|-------------|----------|
| F10.1 | Profilo utente + azienda | GET/PATCH /profile | Must |
| F10.2 | Connessioni (SPID, email, banca) | GET /cassetto/status, /email/status | Must |
| F10.3 | Configurazione notifiche | GET/POST /notifications/config | Should |
| F10.4 | Report per commercialista | GET /reports/commercialista | Must |

---

## Requisiti Non-Funzionali

| Requisito | Target | Misura |
|-----------|--------|--------|
| **First Contentful Paint** | <1.5s | Lighthouse |
| **Time to Interactive** | <3s | Lighthouse |
| **Bundle size** | <300KB gzipped | Vite build |
| **Responsive** | Desktop + tablet + mobile | Tailwind breakpoints |
| **Accessibilita** | WCAG 2.1 AA | axe-core |
| **Browser** | Chrome, Safari, Firefox (ultimi 2 major) | BrowserStack |
| **Offline** | Dashboard leggibile con dati cached | Service Worker |

---

## MoSCoW Prioritization

### Must Have (MVP Frontend — 2 settimane)
- Login/registrazione/password reset
- Onboarding wizard
- Dashboard operativa (contatori + fatture recenti + agenti)
- Lista fatture con filtri + dettaglio
- Verifica categoria (conferma/correggi)
- Upload fattura
- Scritture contabili
- Scadenzario
- Profilo/impostazioni
- Report commercialista

### Should Have (+2 settimane)
- Fatturazione attiva + invio SDI
- Banca (movimenti, riconciliazione)
- Cash flow grafico
- Note spese + approvazione
- Cespiti
- Liquidazione IVA + F24
- Dashboard CEO + budget
- Notifiche
- Alert fiscali

### Could Have (+1 settimana)
- CU annuale
- Conservazione digitale
- Pagamenti PISP
- Monitor normativo
- Bilancio CEE export

### Won't Have (v1.0+)
- App mobile nativa
- Multi-lingua
- White-label per commercialisti
- Chat/assistente AI

---

## Navigazione (da wireframes.md)

```
Sidebar (sempre visibile, collassabile su mobile):
├── Dashboard           → /
├── Fatture             → /fatture
│   ├── Passive         → /fatture/passive
│   ├── Attive          → /fatture/attive
│   ├── Da verificare   → /fatture/verifica
│   └── Upload          → /fatture/upload
├── Contabilita         → /contabilita
│   ├── Scritture       → /contabilita/scritture
│   ├── Piano conti     → /contabilita/piano-conti
│   └── Bilancio        → /contabilita/bilancio
├── Note Spese          → /spese
├── Cespiti             → /cespiti
├── Banca               → /banca
│   ├── Movimenti       → /banca/movimenti
│   ├── Riconciliazione → /banca/riconciliazione
│   └── Cash Flow       → /banca/cashflow
├── Scadenzario         → /scadenze
├── Fisco               → /fisco
│   ├── F24             → /fisco/f24
│   ├── Liquidazione    → /fisco/liquidazione
│   ├── Ritenute        → /fisco/ritenute
│   ├── CU              → /fisco/cu
│   └── Conservazione   → /fisco/conservazione
├── Cruscotto CEO       → /ceo (solo owner)
│   ├── KPI             → /ceo/kpi
│   └── Budget          → /ceo/budget
├── Report              → /report
└── Impostazioni        → /impostazioni
```

---

## Timeline & Milestones

| Milestone | Contenuto | Durata |
|-----------|-----------|--------|
| **M1: Skeleton** | Progetto Vite, routing, layout, auth, API client | 2 giorni |
| **M2: Core** | Dashboard, fatture, verifica, upload, scritture | 5 giorni |
| **M3: Fisco** | Scadenzario, F24, liquidazione, report | 3 giorni |
| **M4: Finance** | Banca, cash flow, riconciliazione, spese, cespiti | 4 giorni |
| **M5: CEO** | Dashboard CEO, budget, alert, notifiche | 3 giorni |
| **M6: Polish** | Responsive, accessibilita, performance, test E2E | 3 giorni |

**Totale stimato: ~4 settimane** (1 developer full-time)

---

## Rischi e Mitigazioni

| Rischio | Impatto | Mitigazione |
|---------|---------|-------------|
| Troppe pagine per MVP | Ritardo | Implementare solo Must Have, iterare |
| Performance con molti dati | UX degradata | TanStack Query cache + paginazione server-side |
| Complessita form fisco (F24, IVA) | Errori utente | Wizard step-by-step, preview prima di conferma |
| Mobile UX su tabelle dense | Inutilizzabile | Card view su mobile, tabella su desktop |
| Accessibilita dimenticata | Compliance | shadcn/ui (accessibile by default) + axe-core in CI |

---
_PRD Frontend generato — 2026-03-23_
