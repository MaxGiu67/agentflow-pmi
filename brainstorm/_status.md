# Status Brainstorming: AgentFlow PMI → ContaBot → Piattaforma
Ultimo aggiornamento: 2026-03-22

## Progetto
- **Nome**: AgentFlow PMI
- **Concept MVP**: ContaBot — "L'agente contabile che impara da te"
- **Visione finale**: AgentFlow Pro — Piattaforma multi-tenant SaaS con marketplace agenti AI per PMI italiane
- **Tipo**: T1 (Idea → Validazione)
- **Workflow**: A (Idea → MVP)

## Fasi Brainstorming
| Fase | File | Status | Progresso |
|------|------|--------|-----------|
| 0 | 00-assessment.md | ✅ Completato | 100% |
| 1 | 01-brainstorm.md | ✅ Completato | 100% |
| 2 | 02-problem-framing.md | ✅ Completato | 100% |
| 3 | 03-market-research.md | ✅ Completato | 100% |
| 4 | 04-mvp-scope.md | ✅ Aggiornato (visione evoluta) | 100% |
| 5 | 05-ux-flows.md | ⏭️ Skipped | N/A (D4=0) |
| 6 | 06-architecture.md | ✅ Aggiornato (Odoo + multi-tenant) | 100% |

## Specialisti
| Specialista | File | Status |
|-------------|------|--------|
| Security | specialists/security.md | ✅ Completato |
| Performance | specialists/performance.md | ⏭️ Non attivato (D9=0) |
| Accessibility | specialists/accessibility.md | ⏭️ Non attivato (D4=0) |
| Analytics | specialists/analytics.md | ⏭️ Non attivato (D10=0) |

## Fase Attuale
✅ **Handoff completato verso dev-methodology (UMCC)**. Specs/ popolati con 3 documenti.

## Decisioni Chiave
1. Concept ContaBot scelto come MVP (su 3: ContaBot, FiscoBot, AgentFlow Pro)
2. Evoluzione a 3 fasi: ContaBot → Multi-agente → Piattaforma multi-tenant
3. **Odoo Community 18 + OCA l10n-italy** come engine contabile headless (partita doppia, piano conti personalizzabile, 80+ moduli IT)
4. **FiscoAPI** per cassetto fiscale, F24, dichiarazioni
5. **A-Cube API** per fatturazione SDI + Open Banking (AISP + PISP)
6. **Open Banking PSD2** — lettura conto corrente via A-Cube AISP (CBI Globe → 400+ banche IT). Fabrick come fallback. Anticipato da v0.4 a v0.3.
7. Multi-tenancy via database Odoo separato per tenant (isolamento GDPR)
8. Stack: Python/FastAPI + React + PostgreSQL + Redis + Odoo + AWS
9. Marketplace agenti con pricing a tier (€49-€499/mese)
10. Go-to-market via commercialisti (B2B2C) — tier Partner a €499/mese
11. Anti-scope: costruisci in layer, ogni fase si sblocca solo se la precedente valida
12. **ADR-006:** A-Cube provider unico SDI + Open Banking, BankingAdapter astratto per switch provider

## Integrazioni Esterne Mappate
| Servizio | Uso | Fase |
|----------|-----|------|
| Odoo CE 18 + OCA | Partita doppia, piano conti, IVA, bilancio | v0.1 |
| Gmail API | Cattura email fatture | v0.1 |
| Google Cloud Vision | OCR fatture PDF | v0.1 |
| FiscoAPI | Cassetto fiscale, F24, dichiarazioni | v0.3 |
| A-Cube API SDI | Fatturazione elettronica SDI | v0.3 |
| A-Cube API AISP | Lettura saldi e movimenti conto corrente | v0.3 |
| A-Cube API PISP | Pagamenti fornitori via API | v0.4 |
| CBI Globe | Gateway PSD2 → 400+ banche IT (via A-Cube) | Infrastruttura |
| Fabrick | Open Banking fallback (AISP + PISP, licenza propria) | Fallback v0.3+ |

## Prossimi Passi
1. ✅ ~~`/bs-handoff` per passare a dev-methodology e popolare specs/~~ — COMPLETATO
2. `/dev-stories` per generare User Stories con Acceptance Criteria
3. `/dev-sprint` per pianificare gli sprint

---
_Ultimo aggiornamento: 2026-03-22_
