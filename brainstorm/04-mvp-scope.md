# MVP Scope — AgentFlow PMI (ContaBot → Piattaforma)

**Data:** 2026-03-22 (aggiornato)
**Principio guida:** Proteggi H1. Costruisci in layer. Ogni fase si sblocca solo se la precedente valida.

---

## Strategia Evolutiva

```
FASE 1 → ContaBot (validazione core)
FASE 2 → ContaBot + FiscoBot (agenti multipli)
FASE 3 → AgentFlow Pro (multi-tenant + marketplace)
```

---

## FASE 1: ContaBot MVP (v0.1 + v0.2)

### MoSCoW v0.1 — "Cattura, registra, impara"

#### Must Have (6 feature)

| # | Feature | Giustificazione | Effort |
|---|---------|----------------|--------|
| M1 | **Connessione email (Gmail)** | H1: activation driver | M |
| M2 | **OCR + Parser fatture XML/PDF** | H1: estrazione dati. XML SDI prioritario (dati strutturati) | L |
| M3 | **Categorizzazione con learning** | H2: differenziante core | L |
| M4 | **UI di verifica/correzione** | H1+H2: feedback loop per insegnare al sistema | M |
| M5 | **Odoo headless + ContaAgent** | Registrazione scritture in partita doppia, piano conti creato dall'agente su misura per tipo azienda | L |
| M6 | **Dashboard minima** | Fatture, scritture contabili, stato agenti | M |

#### Should Have (v0.2)

| # | Feature | Motivo | Effort |
|---|---------|--------|--------|
| S1 | Outlook/IMAP/PEC | Amplia target | S |
| S2 | Notifiche WhatsApp/Telegram | Retention driver | M |
| S3 | Report per commercialista | Abilita B2B2C | M |
| S4 | Upload manuale PDF/foto | Fallback no-email | S |
| S5 | Scadenzario fiscale base | Alert IVA, F24, INPS basati su regime | M |

#### Won't Have v0.1-0.2 (Anti-Scope)

| # | Feature | Motivo | Quando |
|---|---------|--------|--------|
| W1 | Integrazione cassetto fiscale (FiscoAPI) | Complessità auth SPID, non serve per validare H1 | v0.3 |
| W2 | ~~Open Banking / sync conto corrente~~ | **ANTICIPATO a v0.3** — A-Cube AISP, CBI Globe 400+ banche | v0.3 |
| W3 | Fatturazione attiva (emissione) | Odoo lo supporta ma non è il differenziante | v0.3 |
| W4 | App mobile nativa | Web responsive sufficiente | v1.0 se retention lo giustifica |
| W5 | Multi-tenant | Serve solo quando c'è product-market fit | v1.0 |
| W6 | Marketplace agenti | Serve solo con multi-tenant | v1.0 |
| W7 | Gestione HR/personale | Agente separato, fuori scope | v1.0 |
| W8 | Gestione legale | Agente separato, fuori scope | v1.0 |
| W9 | Gestione forniture | Agente separato, fuori scope | v1.0 |
| W10 | Gestione commerciale/offerte | Agente separato, fuori scope | v1.0 |

---

## FASE 2: Multi-Agente (v0.3 + v0.4)

**Prerequisito:** H1 validata (activation ≥60%), 50+ utenti attivi

| # | Feature | Agente | Effort |
|---|---------|--------|--------|
| F1 | Cash flow predittivo 90gg (con dati bancari reali) | CashFlowAgent | L |
| F2 | Integrazione FiscoAPI (cassetto fiscale, F24) | FiscoAgent | L |
| F3 | Alert scadenze fiscali personalizzate | FiscoAgent | M |
| F4 | **Open Banking AISP — lettura saldi e movimenti conto corrente** | CashFlowAgent + A-Cube | M |
| F5 | **Riconciliazione automatica fatture ↔ movimenti bancari** | ContaAgent + CashFlowAgent | M |
| F6 | Fatturazione attiva via Odoo + SDI (A-Cube) | ContaAgent esteso | L |
| F7 | Liquidazione IVA automatica | FiscoAgent + Odoo OCA | M |
| F8 | Bilancio CEE via Odoo | ContaAgent + Odoo OCA | S |

**v0.4 aggiunge:**

| # | Feature | Agente | Effort |
|---|---------|--------|--------|
| F9 | Monitor aggiornamenti normativi (GU, circolari AdE) | NormativoAgent | M |
| F10 | **Open Banking PISP — pagamenti fornitori via API** | ContaAgent + A-Cube | L |
| F11 | **Riconciliazione automatica completa (fattura → pagamento → chiusura partita)** | ContaAgent | M |

---

## FASE 3: Piattaforma Multi-Tenant (v1.0)

**Prerequisito:** 200+ utenti paganti, 10+ commercialisti pilota, PMF confermato

| # | Feature | Effort |
|---|---------|--------|
| P1 | Infra multi-tenant (un DB Odoo per tenant, provisioning automatico) | XL |
| P2 | API Gateway + Tenant Router | L |
| P3 | Dashboard white-label per commercialisti (multi-azienda) | L |
| P4 | Marketplace agenti (attiva/disattiva per tenant) | L |
| P5 | Billing + subscription management (Stripe) | M |
| P6 | Onboarding self-service (tipo azienda → piano conti → agenti suggeriti) | M |
| P7 | CommAgent (offerte, pipeline) | L |
| P8 | FornitureAgent (ordini, tracking) | L |
| P9 | HRAgent (buste paga, ferie, contratti) | XL |
| P10 | LegalAgent (scadenze legali, compliance) | L |
| P11 | Aggregazione multi-banca (Fabrick fallback) + analytics cross-conto | L |

---

## Milestone Dettagliate

### v0.1 — "Cattura e registra" (Settimane 1-10)

| Settimana | Deliverable |
|-----------|-------------|
| 1-2 | Setup infra AWS, deploy Odoo CE Docker + moduli OCA l10n-italy, auth OAuth2 |
| 3-4 | Gmail API integration, pipeline OCR (Vision + lxml per XML SDI) |
| 5-6 | ContaAgent: crea piano conti via Odoo API, registra scritture in partita doppia |
| 7-8 | Learning engine (rules + similarity), UI verifica/correzione |
| 9-10 | Dashboard minima, deploy beta, 20 utenti test |

**Kill gate settimana 10:** Se activation < 40% → pivot o kill.

### v0.2 — "Notifica e esporta" (Settimane 11-16)

| Deliverable |
|-------------|
| Outlook/IMAP/PEC support |
| Notifiche WhatsApp/Telegram |
| Report per commercialista (export da Odoo) |
| Scadenzario fiscale base |
| 50 utenti beta, 5 commercialisti pilota |

**Kill gate settimana 16:** Se acceptance < 60% dopo 30 fatture → rivedere learning.

### v0.3 — "Fisco, banca e predizione" (Settimane 17-26)

| Deliverable |
|-------------|
| FiscoAgent + integrazione FiscoAPI |
| CashFlowAgent (previsione 90gg con dati bancari reali) |
| **Open Banking AISP via A-Cube — lettura saldi e movimenti conto corrente** |
| **Riconciliazione automatica fatture ↔ movimenti bancari** |
| Alert scadenze fiscali personalizzate |
| Fatturazione attiva via Odoo + A-Cube SDI |
| 200 utenti, pricing tier attivo |

### v0.4 — "Compliance, pagamenti e automazione" (Settimane 27-36)

| Deliverable |
|-------------|
| NormativoAgent (monitor GU/circolari) |
| **Open Banking PISP — pagamenti fornitori via API bancaria** |
| **Riconciliazione completa (fattura → pagamento → chiusura partita in Odoo)** |
| Liquidazione IVA automatica |
| Bilancio CEE |
| 500 utenti, 20 commercialisti partner |

### v1.0 — "AgentFlow Pro" (Mesi 10-15)

| Deliverable |
|-------------|
| Multi-tenant (DB per tenant, provisioning) |
| Dashboard white-label commercialisti |
| Marketplace agenti |
| Billing Stripe |
| CommAgent + FornitureAgent |
| Target: 50 commercialisti = 500+ PMI gestite |

---

## Budget Effort Stimato

| Risorsa | v0.1-0.2 | v0.3-0.4 | v1.0 |
|---------|----------|----------|------|
| Backend + Odoo developer | 1.5 FTE | 2 FTE | 3 FTE |
| Frontend developer | 1 FTE | 1 FTE | 1.5 FTE |
| ML/AI engineer | 0.5 FTE | 0.5 FTE | 1 FTE |
| DevOps | 0.25 FTE | 0.5 FTE | 1 FTE |
| Designer UX | 0.25 FTE | 0.25 FTE | 0.5 FTE |
| **Totale** | **3.5 FTE** | **4.25 FTE** | **7 FTE** |

| Fase | Costo stimato | Timeline |
|------|--------------|----------|
| v0.1-0.2 | €60-80k | 4 mesi |
| v0.3-0.4 | €80-120k | 5 mesi |
| v1.0 | €150-200k | 5 mesi |
| **Totale anno 1** | **€290-400k** | **~14 mesi** |

---

## Pricing Target

| Tier | Agenti inclusi | Prezzo | Target |
|------|---------------|--------|--------|
| **Starter** | ContaAgent + Dashboard | €49/mese | P.IVA |
| **Business** | + FiscoAgent + CashFlow | €129/mese | Micro-impresa |
| **Premium** | + Tutti gli agenti | €249/mese | PMI |
| **Partner** | Multi-azienda + white-label | €499/mese (fino 20 clienti) | Commercialisti |

**Breakeven:** ~€30k MRR → 230 clienti Starter oppure 60 Partner

---

## Regole Anti-Scope Creep

1. **Fase 1:** Solo ContaBot. Nessun agente aggiuntivo finché H1 non è validata.
2. **Fase 2:** Si sbloccano solo gli agenti che hanno una richiesta diretta da almeno 10 utenti beta.
3. **Fase 3:** Multi-tenant SOLO se ci sono 10+ commercialisti in attesa. No build speculativo.
4. Ogni nuova feature va confrontata con la fase attuale — se appartiene a una fase successiva, va nel Won't Have.

---
_MVP Scope aggiornato con Open Banking PSD2 + visione evoluta — 2026-03-22_
