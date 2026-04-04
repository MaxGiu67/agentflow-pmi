# Vision — AgentFlow PMI (ContaBot → Piattaforma)

**Progetto:** AgentFlow PMI
**MVP:** AgentFlow — "L'agente contabile con cui parli"
**Data:** 2026-03-24
**Stato:** Aggiornato post Pivot 3 (Sistema Agentico Conversazionale)
**Fonte:** brainstorm/02-problem-framing.md, brainstorm/01-brainstorm.md

---

## Vision Statement

Creare il primo **agente contabile AI conversazionale** per le PMI italiane — non un gestionale da navigare, ma un assistente con cui parlare. L'utente apre una chat, dice "come stanno le mie finanze?" e l'orchestratore chiama gli agenti specializzati (fisco, contabilita, cash flow, cespiti) per assemblare la risposta. Sincronizza le fatture dal cassetto fiscale, le categorizza imparando dallo stile dell'utente, registra le scritture in partita doppia, e prevede il cash flow a 90 giorni. **Non e un software che usi: e un agente con cui parli.**

**Visione evolutiva:** Da AgentFlow (sistema agentico contabile) a **AgentFlow Pro** — piattaforma multi-tenant SaaS con marketplace di agenti AI specializzati (fisco, cash flow, commerciale, HR, legale) venduti a PMI italiane tramite commercialisti. Ogni agente ha un nome, una personalita, e tools specifici — personalizzabili dall'utente.

---

## Sistema Agentico Conversazionale (Pivot 3)

### Architettura

```
Utente ↔ Chat Interface ↔ Orchestratore
                              ↓
              ┌───────────────┼───────────────┐
              ↓               ↓               ↓
        FiscoAgent      ContaAgent      CashFlowAgent
        (fatture,       (scritture,     (previsioni,
         SPID, F24)     categorie)      riconciliazione)
              ↓               ↓               ↓
           Tools           Tools           Tools
        (sync_fatture,  (registra,      (calcola_cashflow,
         scarica_xml)    verifica)       alert_soglia)
```

### Principi

1. **L'utente parla, non naviga** — la chat e l'interfaccia principale
2. **L'orchestratore decide** quale agente chiamare basandosi sul contesto
3. **Gli agenti sono specialisti** — ognuno ha competenze e tools specifici
4. **I nomi sono personalizzabili** — l'utente puo chiamare l'agente fisco "Mario"
5. **Le conversazioni sono persistenti** — ripresa dal punto lasciato
6. **I tools sono modulari** — aggiungibili senza modificare gli agenti

### Esempi di conversazione

```
Utente: "Quante fatture ho ricevuto questo mese?"
Orchestratore: → chiama FiscoAgent.count_invoices(mese=corrente)
AgentFlow: "Hai ricevuto 12 fatture passive questo mese per un totale di €15.430."

Utente: "Quali non sono ancora registrate?"
Orchestratore: → chiama ContaAgent.get_unregistered()
AgentFlow: "3 fatture sono in attesa di verifica categoria. Vuoi che te le mostri?"

Utente: "Si, e dimmi anche come sta il cash flow"
Orchestratore: → chiama ContaAgent.show_pending() + CashFlowAgent.predict(90d)
AgentFlow: "Ecco le 3 fatture da verificare: [lista].
           Il cash flow previsto a 90 giorni mostra un saldo di €45.200,
           con un calo previsto a marzo per l'IVA trimestrale (€898)."
```

### Ipotesi (H5) — Chat = engagement driver

- **Ipotesi:** Gli utenti che usano la chat come interfaccia principale tornano 3x piu spesso di chi naviga le pagine.
- **Soglia GO:** Weekly engagement chat ≥60% vs ≥20% navigazione
- **Soglia NO-GO:** <30% usa la chat dopo 2 settimane
- **Esperimento:** A/B test chat vs dashboard, 50 utenti, 4 settimane

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
- AccountingEngine interno (ADR-007: Odoo rimosso) — partita doppia gestita internamente
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

## Pivot 6: Finanza Operativa (2026-04-02)

AgentFlow non e solo un contabile — e un **controller finanziario**. Il Pivot 6 aggiunge:
- **IVA scorporata** — tutti i KPI usano importo_netto (l'IVA e transito, non ricavo/costo)
- **Scadenzario intelligente** — generazione automatica scadenze da fatture, colori per urgenza, chiusura automatica da banca
- **Cash flow previsionale** — saldo_banca + incassi_previsti - pagamenti_previsti, vista 30/60/90gg, alert soglia
- **Gestione fidi bancari** — plafond, tasso, commissioni per ogni banca
- **Anticipo fatture** — presentazione → verifica plafond → incasso/insoluto, confronto costi tra banche

## Pivot 7: Sales & Email Marketing (2026-04-03)

AgentFlow diventa anche il **CRM del commerciale**. Il Pivot 7 aggiunge:
- **CRM interno** — pipeline Kanban drag-and-drop, contatti, deal (T&M, fixed, spot, hardware), attivita
- **Email marketing** — template con variabili, tracking (open/click/bounce), sequenze automatiche con condizioni
- **Trigger CRM→Email** — quando un deal cambia stage, parte la sequenza email
- **Zero dipendenza Odoo** — tutto in PostgreSQL interno, Brevo per l'infrastruttura email (25 EUR/mese)

**ADR-009**: Keap scartato (5x costo, no italiano), Odoo declassato a opzionale. Pattern: build logic / buy infrastructure.

## PWA (2026-04-03)

AgentFlow e una **Progressive Web App** installabile:
- Manifest + Service Worker + install prompt
- Code splitting React.lazy (bundle -66%)
- Bottom nav mobile (5 tab), safe areas iOS
- Skeleton loading, ErrorBoundary, useOptimistic (React 19)
- Design system: DM Sans, CSS variables, dark mode prep

## Pivot 8: Social Selling Configurabile (2026-04-04)

AgentFlow diventa una **piattaforma CRM configurabile per social selling B2B**, adatta a qualsiasi PMI che affianca al canale tradizionale un'attività di vendita su LinkedIn (o altri social) gestita da collaboratori esterni (fractional account manager).

**Principio architetturale:** Core engine generico + Configuration layer per PMI. Tutto ciò che è specifico di una singola azienda (origini, attività, stadi, prodotti, template, ruoli, KPI, commissioni) è configurabile dall'admin. Il codice non contiene mai riferimenti a clienti, prodotti o settori specifici.

### I 5 moduli del Pivot 8

| Modulo | Cosa aggiunge | Impatto |
|--------|---------------|---------|
| **M1 — Origini configurabili** | L'admin definisce origini custom (linkedin_dm, fiera_mecspe, web...) con canale padre, icona, filtri | Qualsiasi canale tracciabile |
| **M2 — Attività e pre-funnel** | Tipi attività custom (social_dm, visita_stabilimento...) + stadi pre-funnel configurabili prima del "Nuovo Lead" | Funnel completo dal warm-up al deal |
| **M3 — Ruoli e collaboratori esterni** | Ruoli custom con matrice permessi granulare (RBAC), scadenza accesso, segregazione dati row-level, audit trail, export limitato | Governance sicura per fractional |
| **M4 — Catalogo prodotti** | Entità Prodotto/Servizio con categoria, pricing model, margine target. Deal associabili a prodotti. Pipeline filtrabile per prodotto | Analytics per prodotto |
| **M5 — Analytics e compensi** | Dashboard componibili con widget KPI configurabili. Modello compensi con regole definibili (% su deal, condizioni per canale/prodotto) | ROI misurabile per canale e collaboratore |

### Differenziazione

- **vs HubSpot**: HubSpot è omnibus e caro (>$500/mese). AgentFlow è snello, focalizzato PMI italiane, prezzo 10x inferiore
- **vs Pipedrive**: Pipedrive non ha governance per collaboratori esterni, né pre-funnel social, né catalogo prodotti configurabile
- **vs Apollo/Lemlist**: Sono tool di outreach puro (fire & forget). AgentFlow è relationship management con CRM integrato, analytics, e sequenze multi-canale
- **Differenziatore core**: Unico CRM per PMI che combina vendita tradizionale + social selling + governance fractional + configurabilità totale in un'unica piattaforma a 25 EUR/mese di infrastruttura

### Configurabilità: due esempi

**PMI IT (es. NExadata):**
Origini: linkedin_organico, linkedin_dm, linkedin_inmail | Prodotti: SaaS AI, Consulenza, Assessment | Ruolo: Fractional LinkedIn | Sequenze: LinkedIn → Demo → Proposta

**PMI Manifatturiera:**
Origini: fiera_mecspe, linkedin_dm, agente_zona | Prodotti: Linea CNC, Ricambi, Manutenzione | Ruolo: Agente di zona | Sequenze: Fiera → Campione → Preventivo → Ordine

### Ipotesi Pivot 8

- **H6 — Critica:** Le PMI che attivano il modulo social selling con almeno 1 fractional generano il 30%+ della pipeline da canale social entro 90 giorni
- **H7 — Importante:** La configurabilità (origini, attività, ruoli custom) riduce il time-to-value a <1 giorno (vs 2-4 settimane per CRM enterprise)
- **H8 — Strategica:** Il modello "piattaforma configurabile" abilita la rivendita tramite partner (consulenti, system integrator) senza fork del codice

### Anti-scope Pivot 8

| Escluso | Motivo |
|---------|--------|
| ML/NLP (sentiment, prediction) | PMI non ha dati né data scientist |
| Sync real-time con LinkedIn | API non lo permettono, on-demand è sufficiente |
| Social listening enterprise | Costo sproporzionato per PMI |
| Multi-touch attribution complessa | First-touch semplice basta, il resto è over-engineering |
| Scraping social | Violazione ToS, rischio ban |

### Fonte
- `Docs/Spec_Modulo_Social_Selling.md` — Spec completa con 5 moduli
- `Docs/Gap_Analysis_AgentFlow_NExadata.md` — Gap analysis originale
- `brainstorm/13-social-selling-divergenza.md` — 85 idee
- `brainstorm/14-social-selling-sfida.md` — Analisi critica
- `brainstorm/15-social-selling-sintesi.md` — 3 concept

---

## Strategia Evolutiva (aggiornata)

```
FASE 1 (v0.1-0.2): ContaBot + FiscoAgent — validazione
FASE 2 (v0.3-0.4): + CashFlowAgent + Open Banking — agenti multipli
FASE 3 (v1.0):     AgentFlow Pro — copilota del CEO + CRM + Email
FASE 3b (v1.1):    + Social Selling Configurabile (Pivot 8)        ← NUOVA
                    + Pre-funnel social + Ruoli fractional + Catalogo prodotti
                    + Analytics multi-canale + Compensi configurabili
FASE 4 (v1.5):     AgentFlow Pro+ — gestione operativa completa
FASE 5 (v2.0):     AgentFlow Enterprise — marketplace agenti
```

---
_Aggiornato: 2026-04-04 — Pivot 8 Social Selling Configurabile_
