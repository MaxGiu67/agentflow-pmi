# Problem Framing — ContaBot

**Data:** 2026-03-22
**Concept:** ContaBot — "L'agente contabile che impara da te"

---

## Mappa del Dolore

Le 3 frustrazioni del target sono collegate in un ciclo che si autorinforza:

```
TEMPO PERSO (registrare fatture, categorizzare, preparare documenti)
    ↓ meno tempo per il business
PAURA SCADENZE (IVA, F24, INPS, dichiarazioni — ansia costante)
    ↓ gestione reattiva, errori
INCERTEZZA LIQUIDITÀ (non sa quanto ha, quanto avrà, se può pagare)
    ↓ decisioni rinviate, stress
    ↓ torna al punto 1: più tempo perso a rincorrere
```

**ContaBot rompe questo ciclo** automatizzando il tempo perso (H1), prevenendo le dimenticanze (H2), e rendendo visibile il futuro finanziario (H3).

---

## Job-to-be-Done

### JTBD 1 — Libero Professionista (P.IVA)
> Quando ricevo fatture via email e devo registrarle manualmente ogni settimana, voglio che vengano catturate e categorizzate automaticamente, così da recuperare 3-4 ore/settimana per il mio lavoro produttivo.

### JTBD 2 — Titolare Micro-Impresa (1-5 dipendenti)
> Quando mi avvicino a una scadenza fiscale e non sono sicuro di avere tutto in ordine, voglio essere avvisato in anticipo con le azioni da fare, così da non rischiare sanzioni e vivere senza ansia.

### JTBD 3 — Titolare PMI (5-20 dipendenti)
> Quando devo decidere se prendere un nuovo progetto o assumere una persona, voglio sapere esattamente quanti soldi avrò in cassa nei prossimi 90 giorni, così da prendere decisioni basate su dati reali e non sull'istinto.

---

## Ipotesi Testabili

### H1 — Critica: Cattura automatica = driver di activation
**Ipotesi:** Se ContaBot cattura automaticamente fatture da email/foto e le categorizza, almeno il 60% degli utenti completerà l'onboarding e registrerà fatture nella prima settimana.

| Campo | Dettaglio |
|-------|-----------|
| Condizione | L'utente connette email e/o scatta foto ricevute |
| Risultato atteso | Fatture estratte e categorizzate con accuratezza ≥85% |
| Metrica | Activation rate (utenti che completano prima categorizzazione in D7) |
| Soglia GO | ≥60% |
| Soglia NO-GO | <40% |
| Esperimento | 50 beta tester, 3 settimane. Misura: quanti completano onboarding + prima categorizzazione |

### H2 — Importante: Learning riduce il lavoro di verifica
**Ipotesi:** Dopo 30 fatture categorizzate, il sistema apprende lo stile dell'utente e l'80% delle categorizzazioni successive vengono accettate senza modifica.

| Campo | Dettaglio |
|-------|-----------|
| Condizione | L'utente ha processato almeno 30 fatture |
| Risultato atteso | Accuracy di categorizzazione automatica ≥80% |
| Metrica | Acceptance rate (fatture accettate senza modifica / totale) |
| Soglia GO | ≥80% acceptance dopo 30 fatture |
| Soglia NO-GO | <60% acceptance dopo 50 fatture |
| Esperimento | A/B test: categorizzazione naive vs learning. 5 settimane, 30 utenti attivi |

### H3 — Nice-to-have: Cash flow predittivo = retention driver
**Ipotesi:** Gli utenti che vedono la previsione di cash flow a 90 giorni tornano almeno 1 volta/settimana e hanno il 40% di retention a D30.

| Campo | Dettaglio |
|-------|-----------|
| Condizione | Dashboard cash flow disponibile con almeno 20 fatture storiche |
| Risultato atteso | Engagement settimanale sulla dashboard previsionale |
| Metrica | WAU sulla sezione cash flow + D30 retention |
| Soglia GO | ≥40% weekly engagement + D30 retention ≥40% |
| Soglia NO-GO | <20% weekly engagement |
| Esperimento | Feature flag su 50% utenti: con/senza cash flow view. 4 settimane |

---

## Metriche di Successo MVP

| Metrica | Target | Come misurare |
|---------|--------|---------------|
| Activation rate (D7) | ≥60% | Utenti che completano prima categorizzazione entro 7 giorni |
| OCR accuracy | ≥85% | Fatture estratte correttamente / totale fatture processate |
| Categorization acceptance | ≥80% | Categorie accettate senza modifica dopo 30 fatture |
| Retention D7 | ≥50% | Utenti attivi al giorno 7 / utenti registrati |
| Retention D30 | ≥35% | Utenti attivi al giorno 30 / utenti registrati |
| NPS | ≥30 | Survey in-app al giorno 14 |
| Task success rate | ≥90% | Flusso "email → fattura registrata" completato senza errori |
| Time-to-value | ≤5 min | Tempo dal signup alla prima fattura categorizzata |

---

## Anti-Personas (chi NON è il target)

1. **Contabile interno full-time** — Ha già una soluzione e un workflow consolidato, non cerca automazione
2. **Azienda media/grande (>20 dip.)** — Usa ERP strutturati (SAP, Oracle, Zucchetti), compliance troppo complessa
3. **Commercialista "ore-centrico"** — Il cui business model si basa sulle ore spese, incentivi opposti all'automazione
4. **Startup tech-savvy** — Già su Qonto/Finom/tools moderni, non nel nostro sweet spot di "caos organizzativo"

---

## Criteri Go/No-Go (fine MVP, 2-3 mesi)

**GO** se almeno 2 su 3 soglie sono raggiunte:
- H1: Activation ≥60%
- H2: Acceptance ≥80%
- H3: Weekly engagement ≥40%

**NO-GO** se:
- H1 < 40% (il core non funziona)
- OCR < 75% (dati inaffidabili)
- D30 retention < 30% (nessun valore percepito)
- NPS < 0 (il prodotto fa danni)

---
_Problem Framing completato — 2026-03-22_
