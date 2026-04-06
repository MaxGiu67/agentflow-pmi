# Vision — AgentFlow PMI v3.0

**Progetto:** AgentFlow PMI
**Tagline:** "L'AI che vende con te e gestisce per te"
**Data:** 2026-04-06
**Stato:** Pivot 9 — Da Controller Contabile a Sales AI Platform
**Fonte:** AI_Dorsey/01_CONTESTO_PROGETTO.md, Paper Dorsey-Botha, specs/technical/agent-architecture.md

---

## Vision Statement

AgentFlow PMI e un sistema dove l'AI e il **DRI (Directly Responsible Individual) del processo di vendita** per PMI italiane. Non e un CRM con AI sovrapposta: e un assistente che conosce ogni passo del processo, guida il commerciale, prepara bozze, controlla la qualita e misura i risultati.

Il commerciale apre AgentFlow, dice "prepara l'offerta per ACME" e il sistema sa gia: qual e il prodotto, in che stato e il deal, quali info mancano, qual e il margine, e genera la bozza. Il commerciale conferma e va avanti. **L'AI aiuta, non impone.**

Sotto il cofano, AgentFlow e anche il **controller aziendale**: fatture, scadenze, cash flow, budget. Ma il commerciale non lo vede — vede solo il suo assistente.

---

## Ispirazione: Paper Dorsey-Botha

"From Hierarchy to Intelligence" (Block, 31 marzo 2026) propone di sostituire la gerarchia aziendale con un sistema di intelligenza AI. AgentFlow applica questa visione alla PMI italiana:

- **Company World Model:** l'AI conosce il processo di vendita leggendolo dal DB del tenant — stati, trigger, regole, SLA. Non ha conoscenza pre-programmata.
- **Customer World Model:** comprensione per-cliente da dati transazionali (fatture, banca), interazioni (email, call, LinkedIn), storico deal.
- **Intelligence Layer:** agenti AI che compongono azioni specifiche per clienti specifici — un messaggio LinkedIn per un prospect metallurgico e diverso da uno per un commercio all'ingrosso.
- **Tre ruoli:** Venditore (IC), Responsabile (Player-Coach), AI (DRI del processo).

---

## Principi architetturali v3.0

### 1. Il prodotto determina la pipeline

Quando il commerciale crea un deal, sceglie il prodotto dal catalogo. Il sistema attiva automaticamente la pipeline corretta:

```
Commerciale sceglie "Consulenza T&M"    → Pipeline T&M (6 stati)
Commerciale sceglie "Progetto a corpo"   → Pipeline Corpo (7 stati)
Commerciale sceglie "Elevia AI"          → Pipeline Elevia (8 stati)
Admin crea pipeline custom               → Qualsiasi processo
```

Il **canale di acquisizione** (LinkedIn, referral, fiera, cold call) e un attributo del lead, non il selettore della pipeline. Qualsiasi commerciale puo vendere qualsiasi prodotto.

### 2. Entita separate e condivise

Aziende e Contatti esistono indipendentemente dalle pipeline. La stessa azienda puo avere deal in pipeline diverse contemporaneamente. Un'azienda e un'azienda: ha la sua PIVA, il suo ATECO, i suoi referenti.

### 3. FSM dinamica da DB

Gli stati del processo sono letti dal database del tenant, non hardcoded. Ogni tenant puo personalizzare: stati, required fields, SLA, azioni AI. L'agente carica la FSM a ogni interazione.

### 4. L'AI aiuta, non impone

L'agente suggerisce la prossima azione, chiede le info mancanti, prepara bozze. Ma il commerciale puo **sempre saltare stati**. Non ci sono blocchi obbligatori (tranne margine sotto soglia, che richiede approvazione manager).

### 5. Multi-tenant first

Ogni PMI cliente ha il proprio tenant isolato. AgentFlow nasce per servire Nexa Data come primo tenant, ma l'architettura e pronta per qualsiasi PMI.

---

## Il primo tenant: Nexa Data / TAAL

### Due linee di business che coesistono

**Pipeline T&M — Consulenza IT / Staff Augmentation**
- Vendita relazionale B2B di consulenti IT (Java, Angular, .NET, DevOps)
- Commerciali: Massimiliano + team, vendita per conoscenza e referral (~80%)
- Ciclo lungo (3-12 mesi), ticket alto, relazione continuativa
- Fattore critico: **match-ability** — incrociare richiesta cliente con competenze interne
- Margine: tariffa giornaliera vs costo risorsa
- Pipeline: Lead → Qualifica → Match risorse → Offerta → Negoziazione → Won/Lost → Delivery

**Pipeline Corpo — Progetti custom a prezzo fisso**
- Stessa rete commerciale di T&M, ma con fase specifiche (analisi requisiti, definizione specifiche)
- Demo opzionale (a volte il cliente sa gia cosa vuole)
- Pipeline: Lead → Analisi requisiti → Specifiche → [Demo] → Offerta → Negoziazione → Won/Lost → Delivery

**Pipeline Elevia — Prodotto AI via LinkedIn**
- Elevia: soluzione AI modulare con 20+ use case per PMI (HR, Customer Service, Operations)
- Venditore: Pietro Landri, Fractional Account Manager su LinkedIn Navigator
- 50 connection request/settimana, ~200/mese, social selling puro
- Ciclo breve (2-8 settimane), volume alto, content-driven
- Fattore critico: **ATECO fit** — matching use case Elevia con settore prospect
- Settori target: Metallurgia (ATECO 24-25), Commercio ingrosso (46), Chimica (20)
- Pipeline: Prospect → Connessione → Engagement → Discovery Call → [Demo] → Offerta → Won/Lost → Onboarding

### Cross-sell tra pipeline

- Da T&M verso Elevia: cliente enterprise menziona documentazione/processi → suggerire Elevia
- Da Elevia verso T&M: prospect PMI menziona sviluppo custom → suggerire consulenza T&M
- Il customer world model unificato vede entrambe le relazioni

---

## Architettura agentica

### Tre agenti, tre domini

```
     Utente parla con AgentFlow
              │
              ▼
     AgentFlow capisce l'intento
              │
    ┌─────────┼─────────┐
    ▼         ▼         ▼
 SALES     CONTROLLER  ANALYTICS
 AGENT     AGENT       AGENT
```

**Sales Agent** — Un solo assistente commerciale per tutti i prodotti. Carica la pipeline corretta dal DB in base al deal. Ha tool core (sempre disponibili) + tool specifici che si attivano per prodotto:
- Tool T&M: match risorse, calcolo margine, offerta T&M, bench tracking
- Tool Corpo: specifiche, stima effort, offerta a corpo
- Tool Elevia: ATECO scoring, bundle use case, messaggi LinkedIn, warmth score, ROI, onboarding

**Controller Agent** — Il ragioniere. Fatture, prima nota, bilancio, scadenze, F24, CU, budget, spese, cespiti. 17 tool esistenti, funzionanti.

**Analytics Agent** — L'analista. Cash flow predittivo, scenari what-if, pipeline analytics, KPI commerciale, report cross-sell.

> Dettaglio completo: `specs/technical/agent-architecture.md` (ADR-010)

---

## Target Users / Personas

### Persona 1: Commerciale Senior (Marco)
- **JTBD:** "Quando devo seguire 15 deal contemporaneamente su prodotti diversi, voglio un assistente che mi dica cosa fare oggi, prepari le bozze, e non mi faccia perdere tempo a compilare form."
- **Come usa AgentFlow:** Apre il deal, l'agente gli dice cosa manca. Chiede "prepara l'offerta" e la trova pronta. Conferma e passa al deal successivo.

### Persona 2: Fractional Account LinkedIn (Pietro)
- **JTBD:** "Quando devo gestire 200 prospect LinkedIn al mese per Elevia, voglio un sistema che mi dica chi contattare oggi, generi messaggi personalizzati per settore, e tracci la cadence senza che io debba aggiornare un Excel."
- **Come usa AgentFlow:** Vede la lista prospect con warmth score. L'agente suggerisce "Questi 5 prospect metallurgici sono pronti per la call, ecco il brief." Pietro prenota la call su Calendly.

### Persona 3: Titolare/CEO (Massimiliano)
- **JTBD:** "Voglio sapere in un colpo d'occhio: quanti deal abbiamo, quanto vale la pipeline, quali commerciali performano, e come sta il cash flow — senza chiedere a nessuno."
- **Come usa AgentFlow:** Dashboard con KPI vendita + controller. L'agente gli segnala: "Deal ACME fermo da 10 giorni, vuoi che mandi un follow-up?"

### Persona 4: Admin/Operations
- **JTBD:** "Devo configurare il sistema per il mio team: prodotti, pipeline, ruoli, origini, compensi. Deve essere veloce e senza sviluppatore."
- **Come usa AgentFlow:** Admin panel per configurare tutto. Crea un nuovo prodotto → il sistema crea la pipeline. Assegna ruoli e permessi.

### Anti-Personas
- Azienda >50 dipendenti (usa Salesforce/HubSpot enterprise)
- Commercialista puro (non vende, non ha pipeline)
- Startup tech che usa solo Notion + Slack

---

## Success Metrics v3.0

| Metrica | Target | Come misurare |
|---------|--------|---------------|
| Deal tracciati / mese | 100% (tutti i deal in AgentFlow) | Deal creati vs deal reali |
| Tempo risposta agente | < 3 sec per suggerimento | Latenza API |
| Offerte generate dall'AI | ≥ 50% delle offerte totali | Offerte via tool / offerte totali |
| Pipeline accuracy | ≥ 80% deal in stato corretto | Audit mensile |
| Adoption commerciale | ≥ 4 sessioni/settimana per commerciale | Login + azioni |
| LinkedIn cadence compliance | ≥ 80% touchpoint rispettati | Cadence tracker |
| Cross-sell signals | ≥ 2/mese rilevati | CrossSellSignal count |
| Controller metrics | Invariati da Pivot 1-8 | Tutti i KPI contabili esistenti |

---

## Vincoli

### Vincoli tecnici (confermati)
- **Stack: Python 3.12 + FastAPI** — non si riscrive a Node.js (91 stories, 809 test, 196 endpoint esistenti)
- **DB: PostgreSQL** — multi-tenant, FSM dinamica
- **Frontend: React 19 + TypeScript + Vite 8 + Tailwind 4** — PWA installabile
- **AI: OpenAI/Claude** per agenti + scikit-learn per categorizzazione contabile
- **Email: Brevo** (25 EUR/mese)
- **Deploy: Railway**

### Vincoli di business
- Nexa Data e il primo tenant (dogfooding)
- 3 commerciali + 1 fractional — il sistema deve funzionare per team piccoli
- Budget contenuto — niente integrazioni enterprise (Salesforce, SAP)

### Vincoli normativi (invariati)
- GDPR, conservazione fatture 10 anni, PSD2 per Open Banking
- LinkedIn ToS: no automazione diretta, solo assistenza alla composizione messaggi

---

## Strategia evolutiva (aggiornata)

```
FATTO (v0.1-v0.8):
  Auth, fatture, contabilita, Open Banking, cash flow, scadenzario,
  CRM interno, Kanban, Brevo email, Social Selling configurabile,
  Calendario + Microsoft 365, PWA, 91 stories, 809 test

PIVOT 9 — v3.0 (in corso):
  Fase 1: Agent Foundation — refactor da tool-dispatch a agent-dispatch
  Fase 2: Pipeline Templates + Resource DB (T&M matching, margini)
  Fase 3: Elevia Engine (ATECO scoring, LinkedIn cadence, use case bundles)
  Fase 4: Cross-sell + Intelligence Layer

FUTURO (v3.1+):
  - OrderAgent (gestione ordini, consegne)
  - InvoiceAgent (fatturazione attiva SDI integrata con deal)
  - WhatsApp Business API
  - LinkedIn API diretta (non solo CSV import)
  - Editor visuale FSM (drag-and-drop stati)
  - Lead scoring predittivo (ML su dati storici)
  - AgentFlow come prodotto per altre PMI
```

---

_Aggiornato: 2026-04-06 — Pivot 9: AgentFlow v3.0, Sales AI Platform_
