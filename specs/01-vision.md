# Vision — AgentFlow PMI (ContaBot → Piattaforma)

**Progetto:** AgentFlow PMI
**MVP:** ContaBot — "L'agente contabile che impara da te"
**Data:** 2026-03-22
**Stato:** Aggiornato post analisi gap CEO
**Fonte:** brainstorm/02-problem-framing.md, brainstorm/01-brainstorm.md

---

## Vision Statement

Creare il primo agente contabile AI per le PMI italiane che lavora autonomamente — sincronizza le fatture dal cassetto fiscale dell'Agenzia delle Entrate, le categorizza imparando dallo stile dell'utente, registra le scritture in partita doppia, e prevede il cash flow a 90 giorni. Non è un software che usi: è un agente che lavora per te.

**Visione evolutiva:** Da ContaBot (singolo agente contabile) a **AgentFlow Pro** — piattaforma multi-tenant SaaS con marketplace di agenti AI specializzati (fisco, cash flow, commerciale, HR, legale) venduti a PMI italiane tramite commercialisti.

---

## Target Users / Personas

### Persona 1: Libero Professionista (P.IVA)
- **JTBD:** "Quando devo scaricare fatture dal cassetto fiscale dell'AdE e registrarle manualmente ogni settimana, voglio che vengano sincronizzate e categorizzate automaticamente, così da recuperare 3-4 ore/settimana per il mio lavoro produttivo."
- **Regime fiscale:** Forfettario o semplificato
- **Pain principale:** Tempo perso in gestione amministrativa
- **Workaround attuale:** Download manuale da cassetto fiscale, Excel, carta, commercialista

### Persona 2: Titolare Micro-Impresa (1-5 dipendenti)
- **JTBD:** "Quando mi avvicino a una scadenza fiscale e non sono sicuro di avere tutto in ordine, voglio essere avvisato in anticipo con le azioni da fare, così da non rischiare sanzioni e vivere senza ansia."
- **Regime fiscale:** Semplificato o ordinario
- **Pain principale:** Paura di scadenze e sanzioni
- **Workaround attuale:** Commercialista + fogli Excel + ansia

### Persona 3: Titolare PMI (5-20 dipendenti)
- **JTBD:** "Quando devo decidere se prendere un nuovo progetto o assumere una persona, voglio sapere esattamente quanti soldi avrò in cassa nei prossimi 90 giorni, così da prendere decisioni basate su dati reali e non sull'istinto."
- **Regime fiscale:** Ordinario, contabilità per competenza
- **Pain principale:** Incertezza sulla liquidità futura
- **Workaround attuale:** Bilancio trimestrale dal commercialista (in ritardo), istinto

### Persona 4: CEO/Direttore PMI (10-50 dipendenti)
- **JTBD:** "Quando devo decidere se investire, assumere, o tagliare costi, voglio un cruscotto che mi mostri fatturato vs budget, margini per cliente/progetto, costo del personale e cash flow — tutto in un colpo d'occhio, così da guidare l'azienda con i dati e non con l'istinto."
- **Regime fiscale:** Ordinario, contabilità per competenza
- **Pain principale:** Decisioni al buio — dati sparsi tra commercialista, Excel, banca, testa
- **Workaround attuale:** Excel artigianali, bilancini trimestrali dal commercialista (sempre in ritardo), sensazioni
- **Nota:** Questa persona emerge da v1.0 in poi, quando AgentFlow diventa piattaforma con ControllerAgent e Dashboard CEO

### Anti-Personas (NON target)
- Contabile interno full-time (ha già workflow consolidato)
- Azienda media/grande >20 dipendenti (usa ERP strutturati: SAP, Oracle, Zucchetti)
- Commercialista "ore-centrico" (incentivi opposti all'automazione)
- Startup tech-savvy (già su Qonto/Finom, non nel sweet spot di "caos organizzativo")

---

## Mappa del Dolore

Le 3 frustrazioni del target sono collegate in un ciclo che si autorinforza:

```
TEMPO PERSO (scaricare fatture dal cassetto, categorizzare, registrare, preparare documenti)
    ↓ meno tempo per il business
PAURA SCADENZE (IVA, F24, INPS, dichiarazioni — ansia costante)
    ↓ gestione reattiva, errori
INCERTEZZA LIQUIDITÀ (non sa quanto ha, quanto avrà, se può pagare)
    ↓ decisioni rinviate, stress
DECISIONI AL BUIO (nessun cruscotto, dati sparsi, margini sconosciuti, costi personale stimati a occhio)
    ↓ l'azienda viene subìta invece che guidata
    ↓ torna al punto 1: più tempo perso a rincorrere
```

ContaBot rompe questo ciclo automatizzando il tempo perso (H1), prevenendo le dimenticanze (H2), rendendo visibile il futuro finanziario (H3), e offrendo un cruscotto CEO per decisioni informate (H4, v1.0+).

---

## Assumptions (Ipotesi Testabili)

### H1 — Critica: Sync cassetto fiscale = driver di activation
- **Ipotesi:** Se ContaBot sincronizza automaticamente le fatture dal cassetto fiscale dell'AdE e le categorizza, almeno il 60% degli utenti completerà l'onboarding nella prima settimana.
- **Soglia GO:** ≥60% activation rate
- **Soglia NO-GO:** <40%
- **Esperimento:** 50 beta tester, 3 settimane

### H2 — Importante: Learning riduce il lavoro di verifica
- **Ipotesi:** Dopo 30 fatture categorizzate, il sistema apprende lo stile dell'utente e l'80% delle categorizzazioni successive vengono accettate senza modifica.
- **Soglia GO:** ≥80% acceptance dopo 30 fatture
- **Soglia NO-GO:** <60% acceptance dopo 50 fatture
- **Esperimento:** A/B test, 30 utenti attivi, 5 settimane

### H3 — Nice-to-have: Cash flow predittivo = retention driver
- **Ipotesi:** Gli utenti che vedono la previsione di cash flow a 90 giorni tornano almeno 1 volta/settimana.
- **Soglia GO:** ≥40% weekly engagement + D30 retention ≥40%
- **Soglia NO-GO:** <20% weekly engagement
- **Esperimento:** Feature flag su 50% utenti, 4 settimane

### H4 — Strategica (v1.0): Cruscotto CEO = upgrade driver
- **Ipotesi:** I titolari di PMI che usano il cruscotto direzionale (fatturato vs budget, margini, costo personale, KPI) passano dal tier Starter/Business al tier Premium/Executive.
- **Soglia GO:** ≥30% degli utenti attivi accede al cruscotto almeno 2 volte/settimana + conversion rate al tier superiore ≥15%
- **Soglia NO-GO:** <10% weekly engagement con il cruscotto
- **Esperimento:** Rollout graduale su utenti v0.3+, 8 settimane

---

## Success Metrics

| Metrica | Target | Come misurare |
|---------|--------|---------------|
| Activation rate (D7) | ≥60% | Utenti che completano prima categorizzazione entro 7 giorni |
| XML parsing accuracy | ≥99% | Fatture XML SDI parsate correttamente / totale scaricate da cassetto |
| OCR accuracy (non-SDI) | ≥85% | Fatture non-XML estratte via OCR / totale fatture OCR (v0.2+) |
| Categorization acceptance | ≥80% | Categorie accettate senza modifica dopo 30 fatture |
| Retention D7 | ≥50% | Utenti attivi al giorno 7 / utenti registrati |
| Retention D30 | ≥35% | Utenti attivi al giorno 30 / utenti registrati |
| NPS | ≥30 | Survey in-app al giorno 14 |
| Task success rate | ≥90% | Flusso "cassetto fiscale → fattura registrata" completato senza errori |
| Time-to-value | ≤5 min | Tempo dal signup (con SPID) alla prima fattura categorizzata |
| Dashboard CEO engagement (v1.0) | ≥2x/settimana | Accessi al cruscotto direzionale per utente attivo |
| Tier upgrade rate (v1.0) | ≥15% | Utenti che passano a Premium/Executive dopo attivazione cruscotto |

---

## Constraints (Vincoli)

### Vincoli Normativi
- **GDPR:** DPIA obbligatoria prima del lancio (trattamento dati su larga scala)
- **Conservazione fatture:** 10 anni (art. 39 D.P.R. 633/1972) — integrità, leggibilità, accessibilità
- **NON diventare intermediario telematico AdE** — cambia completamente i requisiti normativi
- **PSD2/Open Banking:** SCA obbligatoria, consent 90gg rinnovabile per accesso conto corrente

### Vincoli di Mercato
- CAC alto in mercato saturo (keyword "fatturazione elettronica" CPC €3-8)
- PMI diffidenti verso AI — serve spiegabilità del ragionamento dell'agente
- ~60% PMI delega tutto al commercialista — go-to-market B2B2C via commercialisti

### Vincoli Tecnici
- Data residency EU obbligatoria (GDPR) — AWS eu-south-1 Milano
- Odoo Community 18 come dipendenza pesante ma necessaria per partita doppia italiana
- Dipendenza da provider terzi per dati critici (FiscoAPI, A-Cube) — serve fallback

### Vincoli di Budget
- Budget anno 1: €290-400k, 3.5→7 FTE
- Breakeven target: ~€30k MRR (230 clienti Starter o 60 Partner)
- Costi security anno 1: €20-35k

---

## Criteri Go/No-Go (fine MVP, 2-3 mesi)

**GO** se almeno 2 su 3 soglie sono raggiunte:
- H1: Activation ≥60%
- H2: Acceptance ≥80%
- H3: Weekly engagement ≥40%

**NO-GO** se:
- H1 < 40% (il core non funziona)
- XML parsing < 95% (dati inaffidabili)
- D30 retention < 30% (nessun valore percepito)
- NPS < 0 (il prodotto fa danni)

---

## Strategia Evolutiva

```
FASE 1 (v0.1-0.2): ContaBot + FiscoAgent(cassetto) singolo tenant — validazione
                    Fatturazione base + learning + partita doppia + dashboard tecnica

FASE 2 (v0.3-0.4): + CashFlowAgent + Open Banking + email MCP — agenti multipli
                    + Gap contabili (note spese, cespiti, ritenute, ratei, bollo)
                    + Gap fisco (F24, CU, conservazione digitale)
                    + Dashboard CEO base (fatturato, margini, scadenze)

FASE 3 (v1.0):     AgentFlow Pro — copilota del CEO
                    + ControllerAgent (centri di costo, budget vs consuntivo, KPI)
                    + HRAgent base (costo personale, budget HR, scadenze contratti)
                    + CommAgent base (CRM, pipeline, preventivi)
                    + Multi-tenant + white-label commercialisti

FASE 4 (v1.5):     AgentFlow Pro+ — gestione operativa completa
                    + ProjectAgent (commesse, timesheet, margine progetto, SAL)
                    + DocAgent (repository, contratti, scadenzario)
                    + FornitureAgent (ordini acquisto, albo fornitori)

FASE 5 (v2.0):     AgentFlow Enterprise
                    + ComplianceAgent (D.Lgs 81/08, GDPR, antiriciclaggio)
                    + Marketplace agenti third-party
                    + API pubblica per integrazioni custom
```

---
_Aggiornato con analisi gap CEO — 2026-03-22_
