# Assessment Operativo — AgentFlow PMI

**Data:** 2026-03-22
**Tipo progetto:** T1 — Idea → Validazione

## Descrizione Progetto

Sistema agentico ispirato a OpenClaw per la gestione completa di piccole imprese italiane (SRL, SRLS, ditta individuale). Agenti autonomi che ascoltano eventi, gestiscono processi e supportano decisioni in ambito amministrativo, commerciale, forniture, personale e legale.

**Idea core:** Un ecosistema di agenti AI collaborativi che automatizza contabilità, fatturazione, gestione commerciale, forniture, personale e compliance legale per PMI e liberi professionisti italiani, collegandosi a conti correnti e sistemi esistenti.

---

## Scorecard Operativa

| # | Domanda | Punteggio | Note |
|---|---------|:---------:|------|
| 1 | Problema utente chiaro? | **0** | Il fondatore conosce bene il dolore delle PMI nella gestione quotidiana |
| 2 | Differenziazione vs competitor? | **2** | Non ancora analizzato il posizionamento vs Fatture in Cloud, Danea, TeamSystem, ecc. |
| 3 | Vincoli di tempo? | **0** | Nessuna fretta, fase esplorativa |
| 4 | UX/onboarding critica? | **0** | Il valore è nell'automazione backend/agentica, non nell'interfaccia |
| 5 | Codice non tuo? | **1** | Userà OpenClaw o framework open source come base, ma il grosso sarà custom |
| 6 | Repo instabile? | **0** | Non applicabile, progetto da zero |
| 7 | Dati sensibili/pagamenti? | **2** | Dati bancari, fatturazione SDI, dati dipendenti, GDPR — massima criticità |
| 8 | Integrazioni esterne? | **2** | Banche, SDI/AdE, PEC, INPS, commercialista, CRM — ecosistema complesso |
| 9 | Performance/costi critici? | **0** | Non prioritario in questa fase |
| 10 | Traction con numeri? | **0** | Fase esplorativa, nessuna necessità immediata di metriche |

**Punteggio totale:** 7/20

---

## Agenti Attivati

### Sempre attivi
- **Orchestratore** — Coordinamento centrale del brainstorming

### Attivati dalla scorecard

| Agente | Trigger | Priorità | Motivazione |
|--------|---------|----------|-------------|
| **Market Researcher** | D2=2 | ALTA | Critico mappare competitor (Fatture in Cloud, Danea, TeamSystem, Aruba, Legalinvoice) e trovare il posizionamento differenziante |
| **Cartographer** | D5=1 | MEDIA | Per mappare OpenClaw e capire cosa riusare vs cosa costruire da zero |
| **Doc Writer** | D5=1 | MEDIA | Documentazione delle scelte architetturali e delle integrazioni |
| **Security Agent** | D7=2 | CRITICA | Dati bancari, fatturazione elettronica, dati personali dipendenti — richiede threat model, GDPR compliance, audit auth |
| **Tech Architect** | D8=2 | CRITICA | Architettura per 6+ integrazioni esterne (banche, SDI, PEC, INPS), event-driven, agentica |
| **Dependency Auditor** | D8=2 | ALTA | Valutare rischi delle dipendenze per integrazioni critiche (SDK bancari, librerie SDI) |

### Non attivati (punteggio basso)
- Problem Framer (D1=0, problema già chiaro)
- MVP Scoper (D3=0, nessun vincolo tempo)
- UX Flow + Copy (D4=0, UX non prioritaria)
- Bug Triage (D6=0, nessun repo esistente)
- Performance Agent (D9=0, non rilevante ora)
- Analytics Agent (D10=0, nessuna necessità metriche)

---

## Workflow Consigliato

**Workflow A: Idea → MVP** (basato su T1)

### Ordine di esecuzione raccomandato

```
1. /bs-brainstorm     → Sessione creativa: esplorare angoli innovativi per PMI + AI agentica
2. /bs-problem        → Problem Framing leggero: JTBD specifici per target PMI italiane
3. /bs-research       → Market Research: mappatura competitor e posizionamento
4. /bs-scope          → MVP Scoping: cosa includere nel primo MVP (MoSCoW)
5. /bs-architect      → Architettura: event-driven, integrazioni, stack tecnologico
6. /bs-security       → Security: threat model, GDPR, gestione dati sensibili
7. /bs-onboarding     → Onboarding su OpenClaw: mappatura codice riusabile
```

### Focus strategici per questo progetto

1. **Differenziazione competitiva** — Il mercato italiano ha già player forti (Fatture in Cloud, TeamSystem). L'approccio agentico/event-driven è il potenziale differenziante. Serve validare se gli utenti target lo percepiscono come valore.

2. **Complessità integrazioni** — SDI, banche (PSD2/Open Banking), PEC, INPS, AdE sono integrazioni regolamentate e complesse. L'architettura deve essere pensata per gestire fallimenti, retry, e compliance normativa.

3. **Sicurezza e compliance** — Gestire dati bancari e fatturazione elettronica richiede standard di sicurezza elevati fin dal design. Non è qualcosa da aggiungere dopo.

4. **OpenClaw come base** — Capire cosa di OpenClaw è riusabile per il pattern agentico (orchestrazione, eventi, decisioni) vs cosa va costruito custom per il dominio PMI italiano.

---

## Rischi Identificati

| Rischio | Probabilità | Impatto | Mitigazione |
|---------|:-----------:|:-------:|-------------|
| Mercato saturo di soluzioni gestione PMI | Alta | Alto | Differenziarsi su automazione agentica, non su feature list |
| Complessità integrazioni SDI/banche | Alta | Alto | Iniziare con fatturazione passiva prima di quella attiva |
| Requisiti normativi sottovalutati | Media | Critico | Security Agent + consulenza legale per compliance |
| Scope creep (troppe aree da coprire) | Alta | Alto | MVP focalizzato su 1-2 aree, non tutte e 6 |

---

## Prossimi Step

1. **Immediato:** `/bs-brainstorm` — Sessione creativa per esplorare le 30-50 idee/angoli possibili
2. **Poi:** `/bs-research` — Mappatura competitor e posizionamento
3. **Alternativa:** `/bs-run` — Esecuzione automatica dell'intero workflow A

---
_Assessment completato — 2026-03-22_
