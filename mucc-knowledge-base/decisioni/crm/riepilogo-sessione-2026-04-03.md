---
tipo: decisione
progetto: agentflow-pmi
data: 2026-04-03
stack: python, fastapi, react, brevo, postgresql, pwa
confidenza: alta
tags: pivot-6, pivot-7, crm, brevo, scadenzario, pwa, kanban, email-tracking, sessione
---

# Riepilogo sessione 2026-04-03 — Pivot 6+7, CRM Sales, PWA

## Cosa e stato fatto in una sessione

### Pivot 6: Scadenzario e Finanza (Sprint 17-22)
- 17 stories, 72 SP, 75 test — tutto backend
- IVA scorporata da dashboard e budget (importo_netto ovunque)
- Scadenzario attivo/passivo con generazione auto da fatture
- Cash flow previsionale 30/60/90gg con alert soglia
- Fidi bancari: CRUD plafond/tasso/commissioni per banca
- Anticipo fatture: presentazione → incasso → insoluto (lifecycle completo)
- Confronto costi anticipo tra banche

### Pivot 7: CRM Sales + Email (Sprint 23-27)
- 13 stories, 63 SP, 67 test — backend + frontend
- CRM interno PostgreSQL (4 modelli: contacts, deals, stages, activities)
- Migrazione completa da Odoo JSON-RPC a DB interno
- Pipeline Kanban frontend con drag-and-drop HTML5
- Analytics: weighted pipeline, conversion, won/lost ratio
- Brevo adapter per email con tracking (open/click/bounce/unsub)
- Template email con variabili e preview
- Sequenze multi-step con condizioni (if_opened, if_not_opened)
- Trigger automatici su eventi CRM

### Frontend PWA (Fase 1-4)
- PWA installabile: manifest, service worker, icons, install prompt
- Code splitting: 1.27MB → 432KB (-66%, 96 chunk)
- Bottom nav mobile (5 tab), safe areas iOS, touch targets 44px
- React 19: useOptimistic (Kanban), Suspense+Skeleton, ErrorBoundary
- Design system: DM Sans, 20+ CSS variables, dark mode prep

## Decisioni chiave
- ADR-009: CRM interno + Brevo (Keap scartato 5x costo, Odoo non necessario)
- ChatbotFloating solo su Dashboard e Chat
- Service worker manuale (vite-plugin-pwa incompatibile con Vite 8/Rolldown)
- Pattern: build logic / buy infrastructure per email

## Numeri
- 30 stories implementate in una sessione
- 142 nuovi test (tutti PASS)
- 0 errori TypeScript
- Build frontend: 222ms

## Progetto origine
agentflow-pmi
