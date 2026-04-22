# ADR-012: Integrazione A-Cube Open Banking (AISP) + Scarico Massivo Fatture

**Data:** 2026-04-19
**Stato:** APPROVATA
**Decisori:** Massimiliano Giurelli (Nexa Data, CTO)
**Contratto:** Firmato 10/04/2026 da Gennaro Vallo (rif. offerta `Offerta_NexaData_firmato.pdf`)
**Correlata:** ADR-004 (FiscoAPI + A-Cube originaria, superata per la parte FiscoAPI rimossa)

---

## Contesto

AgentFlow PMI ha due filoni di sviluppo:
1. **Filone Sales** — CRM, pipeline, Sales Agent (completato fino a Pivot 10)
2. **Filone Finance** — fatturazione attiva/passiva, banca, cash flow, budget (Pivot 11, "Finance Cockpit")

Per automatizzare il filone Finance servono due integrazioni con partner italiani qualificati:
- **Open Banking PSD2 (AISP)** — lettura conti bancari, movimenti, saldi dei clienti finali
- **Scarico Massivo Fatture Cassetto Fiscale** — import automatico fatture elettroniche dall'Agenzia delle Entrate

Sono state valutate 3 alternative principali:

1. **A-Cube** — provider italiano, già usato in AgentFlow come adapter stub per SDI (ADR-004)
2. **Salt Edge** — Open Banking internazionale, CRIF (FiscoAPI) per cassetto
3. **Fabrick / Banca Sella** — Open Banking italiano

## Analisi Comparativa

| Criterio | A-Cube | Salt Edge + CRIF | Fabrick |
|----------|--------|------------------|---------|
| Copertura geografica | Italia + EU | Globale | Italia |
| Open Banking italiano | Completo | Completo | Completo |
| Scarico Massivo Cassetto | ✅ Integrato | ❌ CRIF separato | ❌ non offre |
| Costo annuo (50 P.IVA + 5K fatture) | €1.800 | ~€3.500 (OB + CRIF) | ~€2.200 (solo OB) |
| Setup una tantum | €900 (OB) | €0 + commesse integrazione | €0 |
| Conti per P.IVA | Illimitati | 5 conti/tenant | 5 conti/tenant |
| Email supporto PSD2 conformità | Best-effort | Ticket premium | Commerciale |
| Dashboard amministrativa | Sì (italiano) | Sì (inglese) | Sì (italiano) |
| Documentazione | Media (vedi KB) | Completa | Buona |
| Sandbox OB | ✅ Disponibile | ✅ Disponibile | ✅ Disponibile |
| Sandbox Scarico Massivo | ⚠️ Non disponibile (call tecnica) | N/A | N/A |
| JWT token-based auth | ✅ email+password | ✅ API key + HMAC | ✅ OAuth2 |
| Webhook | ✅ Connect/Reconnect/Payment | ✅ Status callback | ✅ Push |
| Corrispettivi elettronici 2026 | ✅ Incluso canone | ❌ Out of scope | ❌ Out of scope |
| Relazione precedente | ADR-004 (SDI) | Nessuna | Nessuna |
| Rischio vendor | Medio (piccolo player) | Basso (leader) | Medio (banca) |

## Decisione

**A-Cube per entrambi i servizi (AISP + Scarico Massivo Fatture).**

### Motivazioni

1. **Provider unico per Finance** — semplifica vendor management, fatturazione unificata, contratto unico
2. **Costo contenuto** — €1.800/anno vs €3.500 di alternativa, con possibilità sconto triennale 20%
3. **Copertura completa** — OB PSD2 + Scarico Massivo + futuri Corrispettivi 2026 (inclusi gratis)
4. **Ambito italiano** — interfaccia italiana, supporto in italiano, SLA calibrati su mercato italiano
5. **Conti illimitati per P.IVA** — tariffazione per cliente (Business Registry), non per conto
6. **Relazione preesistente** — già cablato come adapter stub per SDI, vendor conosciuto
7. **Delega AdE chiara** — modalità "proxy A-Cube" (P.IVA 10442360961) evita rotazione password Fisconline
8. **Scalabilità pricing** — tier progressivo 1-50 / 51-100 / 101-500 / 500+ con costo decrescente per cliente

### Compromessi accettati

- ⚠️ **Sandbox Scarico Massivo non disponibile** → richiede call tecnica preliminare (tempo extra)
- ⚠️ **Supporto best-effort** base senza SLA garantito → valutare upgrade prioritario (€600/anno) a ≥10 clienti attivi
- ⚠️ **Vendor più piccolo** di Salt Edge → rischio mitigato da contratto scritto + possibile switch futuro
- ⚠️ **Auth via email+password** → non ideale per SaaS, da chiarire se esiste alternativa (OAuth client_credentials)

---

## Architettura

```
AgentFlow PMI (backend)                A-Cube Platform
┌──────────────────────────┐          ┌─────────────────────────────┐
│ api/adapters/acube.py    │          │ common.api.acubeapi.com     │
│ ├─ ACubeSDIAdapter (già) │          │ └─ POST /login → JWT 24h    │
│ ├─ ACubeOBClient ← NEW   │──HTTPS──→│                             │
│ └─ ACubeCassettoClient   │          │ ob.api.acubeapi.com         │
│   ← NEW (post call tec.) │          │ ├─ /business-registry       │
│                          │          │ ├─ /accounts                │
│ api/modules/banking/     │          │ ├─ /transactions            │
│ api/modules/cashflow/    │          │ ├─ /payments                │
│ api/modules/scadenzario/ │          │ ├─ /categories              │
│ api/modules/reconciliation/│         │ ├─ /bank-managers           │
│                          │          │ └─ /connect (PSD2 flow)     │
│ api/modules/invoices/    │          │                             │
│ (passive fatt. esistenti)│          │ [cassetto endpoint post-call]│
│                          │          │ └─ /business-registry-      │
│ DB: bank_connection,     │          │    configurations           │
│     bank_account,        │          │                             │
│     bank_movement,       │          │                             │
│     acube_usage          │          │                             │
└──────────────────────────┘          └─────────────────────────────┘
                                                    │
                                                    ▼
                                          Webhook endpoints:
                                          POST /api/v1/webhooks/acube/connect
                                          POST /api/v1/webhooks/acube/reconnect
                                          POST /api/v1/webhooks/acube/payment
```

### Modello multi-cliente

Ogni cliente AgentFlow = 1 Business Registry A-Cube (mappato su P.IVA cliente).
Tariffazione A-Cube per **numero BR attivi**, non per numero conti.

```
AgentFlow Tenant (Nexa Data admin)
 └─ AgentFlow Customer #1 (PMI cliente)  →  Business Registry A-Cube (P.IVA-1)
 └─ AgentFlow Customer #2 (PMI cliente)  →  Business Registry A-Cube (P.IVA-2)
 └─ ...
 └─ AgentFlow Customer #50 (PMI cliente) →  Business Registry A-Cube (P.IVA-50)  ← soglia
```

### Ciclo di vita Consenso PSD2

```
Day 0:   Cliente avvia connect → SCA su banca → consenso attivo 90gg
Day 70:  Webhook Reconnect noticeLevel=0 → notifica email cliente
Day 80:  Webhook Reconnect noticeLevel=1 → notifica urgente
Day 90:  Webhook Reconnect noticeLevel=2 → banner app bloccante
         Cliente rinnova SCA → consenso esteso altri 90gg
```

---

## Conseguenze

### Positive

1. ✅ Unblocking filone Finance: import automatico movimenti bancari + fatture passive
2. ✅ Zero maintenance cassetto fiscale — A-Cube gestisce scadenza password Fisconline
3. ✅ Riconciliazione automatica movimenti↔fatture con CRO/IBAN
4. ✅ Cash flow predittivo su dati reali
5. ✅ Ordine di magnitudine di valore per clienti PMI (attualmente ore di data entry manuale)
6. ✅ Corrispettivi 2026 inclusi nel canone — gratuito futuro

### Negative

1. ⚠️ **Commitment minimo 50 clienti fascia base** — anche se abbiamo 4 clienti, paghiamo €1.200/anno fisso
2. ⚠️ **Soglia 5.000 fatture/anno** per Scarico Massivo → Usage Monitor interno obbligatorio
3. ⚠️ **Rinnovo automatico contratto** → serve disdetta entro 31/10 se vogliamo cambiare
4. ⚠️ **Dipendenza vendor** — se A-Cube ha outage, Finance è impattato
5. ⚠️ **PISP separato** — Outbound Payment probabilmente richiede contratto aggiuntivo

### Azioni da intraprendere

| Azione | Responsabile | Tempistica |
|---|---|---|
| Invio email tecnica kick-off ad A-Cube | CTO | Immediata |
| Prenotazione call tecnica Scarico Massivo | CTO | 2 settimane |
| Implementazione Pivot 11 Sprint 48-53 | Dev team | 5-6 settimane |
| Delega AdE per ognuno dei 4 clienti attivi | Admin (cliente) | Durante onboarding |
| Go-live sandbox | Dev team | Sprint 48 |
| Go-live prod per 1° cliente | Dev team | Sprint 53 |

---

## Costi totali anno 1

| Voce | Importo |
|---|---|
| Setup Open Banking (una tantum) | €900 |
| Canone AISP (1-50 clienti) | €1.200 |
| Canone Scarico Massivo (5 clienti + 5.000 doc) | €600 |
| **Totale anno 1 (listino)** | **€2.700** |
| **Totale con sconto triennale -20%** | **€2.460** |
| Opzionale: Supporto prioritario | +€600/anno |

Costo per cliente AgentFlow (media 4 clienti attivi): **€675/anno** (€56/mese).
A regime con 50 clienti: **€54/anno** per cliente (€4,5/mese). Margine ottimo.

---

## Riferimenti

- Contratto firmato: `Offerta_NexaData_firmato.pdf` (10/04/2026)
- Knowledge base tecnica: `Docs/acube-openbanking-kb/` (13 file)
- Email kick-off tecnico: `Docs/Email_A-Cube_Kickoff_Tecnico.md`
- Procedura delega AdE: `Docs/A-Cube API - Procedura manuale per delega_v1.0.docx.pdf`
- Procedura incarico AdE: `Docs/A-Cube API - Procedura manuale per incarico (2).pdf`
- Documentazione pubblica: `https://docs.acubeapi.com/documentation/open-banking/`
- OpenAPI spec: `https://docs.acubeapi.com/openapi/open-banking-api.json`
- User Stories implementazione: `specs/03-user-stories-pivot11-openbanking.md`
- Sprint plan: `specs/05-sprint-plan-pivot11.md`

---

## Storico modifiche

| Data | Versione | Modifiche |
|---|---|---|
| 2026-04-19 | 1.0 | Creazione ADR basato su contratto + KB |
