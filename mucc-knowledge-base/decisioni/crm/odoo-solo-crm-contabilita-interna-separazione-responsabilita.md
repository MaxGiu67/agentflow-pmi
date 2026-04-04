---
tipo: decisione
progetto: agentflow-pmi
data: 2026-04-02
aggiornamento: 2026-04-03
stack: odoo, python, fastapi, postgresql, brevo
confidenza: alta
tags: odoo, crm, contabilita, separazione-responsabilita, architettura, brevo
---

# Separazione responsabilita: contabilita interna, CRM interno, email esterna

## Contesto
AgentFlow PMI ha attraversato 3 fasi di evoluzione architetturale:
1. ADR-007 (2026-03): Drop Odoo contabile → engine interno PostgreSQL
2. ADR-008 (2026-04-02): Odoo 18 Online SOLO per CRM
3. ADR-009 (2026-04-03): CRM interno + Brevo → Odoo declassato a opzionale

## Decisione finale (ADR-009)
Tre sistemi separati per tre responsabilita:

| Responsabilita | Sistema | Costo |
|---------------|---------|-------|
| Contabilita (partita doppia, IVA, bilancio) | Engine interno PostgreSQL | 0 EUR |
| CRM (pipeline, contatti, deal, ordini) | DB interno PostgreSQL | 0 EUR |
| Email marketing (invio, tracking, bounce) | Brevo SaaS | 300 EUR/anno |
| Timesheet, billing, commesse | Nexa Data proprietario | Esistente |

**Flusso dati aggiornato:**
- Commerciale gestisce deal nel CRM interno AgentFlow → pipeline Kanban
- Email automatiche via Brevo con tracking (open, click, bounce)
- Ordine ricevuto → registrato con tipo (PO, email, firma, portale)
- Ordine confermato → commerciale crea commessa nel sistema Nexa Data
- Timesheet, billing e commesse restano INTERAMENTE su Nexa Data (invariato)
- Engine contabile interno gestisce partita doppia, bilancio, IVA (indipendente)

**Odoo 18 resta come opzione:**
- L'adapter odoo_crm.py resta nel codice
- I clienti Nexa Data che preferiscono Odoo possono usarlo (bundle commerciale)
- Partnership Odoo in valutazione (contatto: Achraf Kanice)

## Vantaggi
- Zero dipendenze esterne per il core business
- Tutti i dati in un unico DB PostgreSQL (backup unico, query dirette)
- Costo totale: 300 EUR/anno (solo Brevo per email)
- Brevo sostituibile con qualsiasi servizio email (Resend, SES, Postmark)

## Progetto origine
agentflow-pmi — specs/technical/ADR-007-drop-odoo.md, ADR-008-odoo-crm.md, ADR-009-crm-interno-brevo.md
