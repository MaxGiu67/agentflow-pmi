# ADR-009: CRM Interno + Brevo per Email Marketing

**Data:** 2026-04-03
**Stato:** APPROVATA
**Decisori:** Massimiliano Giurelli (Nexa Data)
**Sostituisce:** ADR-008 (Odoo 18 come CRM) — Odoo resta opzione per bundle clienti, ma AgentFlow non ne dipende

---

## Contesto

Nexa Data ha valutato 3 opzioni per il CRM commerciale:

1. **Odoo 18 Online** — CRM esterno via JSON-RPC (ADR-008, implementato)
2. **Keap** (ex Infusionsoft) — CRM + email automation
3. **CRM interno** in AgentFlow + servizio email esterno

La valutazione ha coinvolto 3 criteri: costo, complessita, valore aggiunto.

## Analisi Comparativa

| Criterio | Odoo CRM | Keap | CRM interno + Brevo |
|----------|----------|------|---------------------|
| Costo annuo | 0-1.100 EUR | 5.600 EUR | 300 EUR |
| UI Italiana | Si | No | Si (nostra) |
| Valuta EUR | Si | No (solo USD) | Si |
| Dipendenza esterna | JSON-RPC latenza | REST API gaps v2 | Zero (DB interno) |
| Email tracking | Base | Eccellente | Eccellente (via Brevo) |
| Custom fields | Illimitati | 150, limitati | Illimitati (nostro DB) |
| Rischio vendor | Basso | Alto (acquisita Thryv) | Basso (Brevo sostituibile) |
| Tempo implementazione | Gia fatto | 2+ sprint | 2 sprint |
| Manutenzione | Adapter esterno | Adapter esterno | Codice interno |

## Decisione

**CRM interno in AgentFlow PMI + Brevo per email marketing.**

### Motivazioni
1. **Il CRM e gia costruito**: 12 endpoint, 3 pagine frontend, adapter — serve solo spostare i dati da Odoo al DB interno
2. **Zero costo CRM**: i dati vivono nel PostgreSQL applicativo, nessuna licenza
3. **Email tracking**: Brevo fornisce open/click/bounce tracking via webhook a 25 EUR/mese — stessa qualita di Keap
4. **Nessuna dipendenza esterna** per il CRM: zero latenza, query SQL dirette, backup unico
5. **Keap scartato**: 5x il costo, no italiano, no EUR, acquisita da Thryv, API immatura

### Architettura

```
AgentFlow PMI (PostgreSQL)          Brevo (Email Infrastructure)
┌─────────────────────────┐         ┌─────────────────────────┐
│ crm_contacts            │         │ Invio SMTP (IP reputati)│
│ crm_deals               │         │ Open tracking (pixel)   │
│ crm_activities          │ ──API──▶│ Click tracking (redirect│
│ email_templates         │         │ Bounce handling         │
│ email_campaigns         │◀─Hook───│ Unsubscribe management  │
│ email_sends             │         │ SPF/DKIM/DMARC          │
│ email_events            │         └─────────────────────────┘
└─────────────────────────┘
```

### Modelli DB (Fase 1)

**CRM:**
- `crm_contacts` — contatti aziendali (name, piva, email, phone, type)
- `crm_deals` — opportunita pipeline (contact_id, stage, deal_type, daily_rate, estimated_days, revenue)
- `crm_activities` — attivita su deal (type: call/email/meeting/note)

**Email:**
- `email_templates` — template HTML con variabili
- `email_campaigns` — campagne (single/sequence)
- `email_sequence_steps` — step sequenza con delay e condizioni
- `email_sends` — singoli invii tracciati
- `email_events` — eventi webhook (open, click, bounce, unsubscribe)

### Fasi

**Fase 1 (Sprint 23-24):** CRM interno + email base con tracking
**Fase 2 (Sprint 25-26):** Automation avanzata (campaign builder, A/B, lead scoring) — solo se validata dall'uso

### Brevo Config

```env
BREVO_API_KEY=<api-key>
BREVO_WEBHOOK_SECRET=<webhook-secret>
BREVO_SENDER_EMAIL=commerciale@nexadata.it
BREVO_SENDER_NAME=Nexa Data
```

### Odoo

Odoo 18 resta come **opzione bundle per i clienti** Nexa Data che lo vogliono (partnership commerciale), ma AgentFlow PMI non dipende da Odoo per funzionare. L'adapter `odoo_crm.py` resta nel codice come integrazione opzionale.

## Conseguenze

- I 12 endpoint `/crm/*` esistenti vengono migrati da Odoo a DB interno
- L'adapter `odoo_crm.py` diventa opzionale (per clienti che usano Odoo)
- Nuovo adapter `brevo.py` per email (invio + webhook)
- 5 tool CRM nel chatbot restano invariati (cambiano solo la source dei dati)
- Costo operativo: 300 EUR/anno (Brevo) vs 0-1.100 EUR (Odoo) vs 5.600 EUR (Keap)
