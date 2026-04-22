# 11 — Servizi Italia (catalogo completo A-Cube)

**Fonte:** https://docs.acubeapi.com/documentation/italy

---

## Catalogo A-Cube per Italia

### Cassetto Fiscale
> "Automatically download invoices from your Tax Drawer"

- Link: `/documentation/italy/gov-it/cassettofiscale`
- **✅ Incluso contratto NexaData** (Scarico Massivo)
- Vedi `10-cassetto-fiscale.md`

### Invoices
> "Manage the exchange of your electronic invoices with REST APIs"

- Link: `/documentation/italy/gov-it/invoices/composing-invoice`
- ❓ Non chiaro se è servizio separato SDI outbound o stesso del Cassetto
- Da valutare se utile per l'emissione fatture attive (oggi A-Cube adapter stub in AgentFlow)

### Corrispettivi
> "Manage electronic receipts (Corrispettivi Elettronici)"

- Link: `/documentation/italy/ereceipts`
- ⏳ Incluso in contratto NexaData quando AdE rilascerà canale Corrispettivi 2026

### Smart Receipts
> "Replace the issuance of a receipt via a telematic cash register"

- Link: `/documentation/italy/gov-it/smart-receipts/introduction`
- ❓ Non incluso contratto, potenziale upsell

### Legal Storage
> "A-Cube's Preservation API allows you to manage document preservation"

- Link: `/documentation/italy/gov-it/legal-storage`
- Alternativa a conservazione digitale di terzi
- AgentFlow ha già `api/modules/preservation` — valutare se sostituire/integrare

### Sistema Tessera Sanitaria
> "Automatically manage the sending of healthcare expense data"

- Link: `/documentation/italy/gov-it/sistemaTS/introduction`
- Per clienti sanitari specifici — non rilevante MVP

### Verify
> "Verification services for Italian entities including VAT numbers"

- Link: `/documentation/italy/gov-it/verify/introduction`
- Utile per onboarding clienti AgentFlow (validare P.IVA, intestatario conto)

### NSO (Nodo Smistamento Ordini)
> "Simplifies the management of orders from public companies in healthcare"

- Link: `/documentation/italy/peppol-it/introduction`
- Per PA sanitaria — non rilevante MVP

---

## Servizi di interesse AgentFlow (ranking)

| Priorità | Servizio | Rationale |
|---|---|---|
| **P0** | Cassetto Fiscale (Scarico Massivo) | Contratto firmato, automation fatture passive |
| **P0** | Open Banking AISP | Contratto firmato, automation movimenti |
| **P1** | Invoices (SDI outbound) | Completare adapter A-Cube stub per fatturazione attiva |
| **P2** | Verify | Validazione P.IVA in onboarding |
| **P2** | Corrispettivi (quando disponibili) | Incluso nel canone attuale |
| **P3** | Legal Storage | Alternativa a soluzione attuale |
| **P4** | Smart Receipts, Sistema TS, NSO | Non rilevanti MVP |

---

## Menu navigazione globale A-Cube

Dalla sidebar doc:

- **Countries**: Italia, Belgio, Polonia, Mondiale (Peppol)
- **Connectors**: Transfer, Stripe
- **Sezioni principali**: Platform, Open Banking, Legal Archive, Support

Per Italia sub-sidebar:
- Peppol API for NSO (Italian Authority)
- Getting started
- API Reference
