---
tipo: decisione
progetto: agentflow-pmi
data: 2026-04-02
aggiornamento: 2026-04-03
stack: odoo, keap, brevo, python, fastapi
confidenza: alta
tags: crm, odoo, keap, brevo, pipeline, body-rental, consulenza-it, T&M
---

# Evoluzione scelta CRM per consulenza IT e body rental

## Contesto
Nexa Data (3 commerciali, 65 risorse, 100 progetti/anno) cercava un CRM per gestire pipeline vendite con deal T&M (tariffa giornaliera x giorni), fixed price, spot consulting e hardware.

## Cronologia decisioni

### 2026-04-02: Odoo 18 scelto, Keap scartato (ADR-008)
- Keap scartato con score 2/12 (e-commerce oriented, no T&M, no italiano)
- Odoo 18 Online scelto (93 EUR/mese, pipeline custom, JSON-RPC API, italiano)

### 2026-04-03: CRM interno + Brevo sostituisce Odoo (ADR-009)
- **Keap riesaminato**: score migliorato a 3/12 (pipeline multi ok) ma confermato inadeguato
  - $400+/mese (5x Odoo), no italiano, no EUR, acquisita Thryv (futuro incerto)
  - Unico punto forte: email automation (ma replicabile con Brevo a 25 EUR/mese)
- **Odoo declassato**: non necessario — il CRM era gia costruito internamente
- **Decisione finale**: CRM interno PostgreSQL + Brevo per email = 300 EUR/anno

## Scorecard finale (aggiornata 2026-04-03)

| CRM | Score | Costo/anno | Italiano | EUR | Note |
|-----|-------|-----------|----------|-----|------|
| **CRM interno + Brevo** | **11/12** | **300 EUR** | **Si** | **Si** | Massimo controllo, minimo costo |
| Odoo 18 Online | 10/12 | 0-1.100 EUR | Si | Si | Resta opzione bundle clienti |
| Teamleader | 8/12 | ~3.000 EUR | Si | Si | Non valutato in profondita |
| Pipedrive | 6/12 | ~2.500 EUR | Si | Si | No T&M nativo |
| HubSpot | 3/12 | 0-6.000 EUR | Si | Si | Overkill per 3 utenti |
| Keap | 3/12 | 5.600 EUR | No | No | Email automation ok, tutto il resto no |

## Lezione
- Per team piccoli (3-5 utenti) con esigenze specifiche (T&M, body rental), costruire internamente e spesso meglio che comprare
- L'email marketing automation e un servizio infrastrutturale: compra l'infrastruttura (Brevo/Resend/SES), costruisci la logica
- Non innamorarsi di un tool: riesamina le decisioni quando il contesto evolve

## Progetto origine
agentflow-pmi — specs/technical/ADR-009-crm-interno-brevo.md
