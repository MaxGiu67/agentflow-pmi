---
tipo: decisione
progetto: agentflow-pmi
data: 2026-04-03
stack: python, fastapi, postgresql, brevo, react
confidenza: alta
tags: crm, brevo, keap, odoo, email-tracking, kanban, pipeline, build-vs-buy
---

# CRM interno + Brevo sostituisce Odoo e Keap (ADR-009)

## Contesto
Nexa Data (3 commerciali, ~100 progetti/anno) ha riesaminato la scelta CRM dopo aver implementato l'integrazione Odoo 18 (ADR-008). La domanda: ha senso dipendere da un sistema esterno grande come Odoo quando serve solo pipeline + email?

## Opzioni valutate

### Keap (ex Infusionsoft) — SCARTATO
- **Costo**: $399-470/mese (~5.600 EUR/anno) — 5x Odoo
- **UI**: Solo inglese, nessuna localizzazione italiana
- **Valuta**: Solo USD ($), nessun campo EUR nativo
- **API**: REST v2 immatura — custom fields non queryabili, gap su deal
- **Rischio**: Acquisita da Thryv (Oct 2024, $80M) — futuro incerto
- **Punto forte**: Email marketing automation eccellente (sequenze, A/B, pixel tracking)
- **Conclusione**: Paghi 5.600 EUR/anno per email automation — il CRM e inadeguato per IT consulting

### Odoo 18 Online — DECLASSATO A OPZIONALE
- **Costo**: 0-93 EUR/mese
- **Funziona**: pipeline, contatti, deal con campi custom x_*
- **Problema**: dipendenza esterna (API JSON-RPC, latenza, rate limit ~60 req/min)
- **Il CRM era gia costruito internamente**: 12 endpoint, 3 pagine frontend, adapter — i dati possono vivere nel DB interno
- **Conclusione**: non necessario come dipendenza, resta come opzione bundle per clienti

### CRM interno + Brevo — SCELTO
- **Costo**: 25 EUR/mese Brevo = 300 EUR/anno totale
- **CRM**: 3 tabelle nel DB PostgreSQL (crm_contacts, crm_deals, crm_activities)
- **Email tracking**: Brevo fornisce open/click/bounce/unsubscribe via webhook
- **Vista**: Kanban drag-and-drop (stile Trello) per i commerciali
- **Vantaggi**: zero dipendenza CRM, zero latenza, query SQL dirette, Brevo sostituibile

## Decisione
CRM interno in AgentFlow + Brevo per email marketing. Odoo resta opzionale per partnership.

## Lezione appresa
- **Build vs Buy**: per 3 utenti e ~100 deal/anno, un CRM interno e perfettamente gestibile
- **Separare logica da infrastruttura**: costruisci la logica (workflow, template, analytics), delega l'infrastruttura pesante (SMTP, deliverability, tracking pixel) a chi la fa di mestiere
- **Non copiare feature — copia pattern**: di Keap prendiamo il pattern (email tracking, sequenze, A/B) non il prodotto
- **Scope fisso**: Fase 1 = CRM + email base. Fase 2 solo se validata dall'uso reale

## Progetto origine
agentflow-pmi — specs/technical/ADR-009-crm-interno-brevo.md
