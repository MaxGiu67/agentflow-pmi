# Analisi Gap: Cosa Manca al CEO per Gestire l'Azienda

**Progetto:** AgentFlow PMI
**Data:** 2026-03-22
**Obiettivo:** Confrontare ciò che il PRD copre con ciò che serve realmente a un CEO di PMI italiana per gestire la sua azienda. Identificare i gap e proporre agenti futuri.

---

## 1. Cosa Copre il PRD Attuale

Il PRD definisce 8 Epic (0-8) organizzate in 4 versioni (v0.1→v1.0). Ecco cosa copre, raggruppato per area di gestione:

### Area CONTABILITÀ E FATTURAZIONE (coperta al 90%)

| Funzione | Epic | Versione | Stato |
|----------|------|----------|-------|
| Registrazione utente e auth SPID | E0 | v0.1 | ✅ Definito |
| Sync fatture passive dal cassetto fiscale | E1 | v0.1 | ✅ Definito |
| Parsing XML FatturaPA | E1 | v0.1 | ✅ Definito |
| Upload manuale fatture | E1 | v0.2 | ✅ Definito |
| Email MCP per documenti non-SDI | E1 | v0.2 | ✅ Definito |
| OCR su fatture non-XML | E1 | v0.2 | ✅ Definito |
| Categorizzazione con learning | E2 | v0.1 | ✅ Definito |
| Feedback loop (utente corregge) | E2 | v0.1 | ✅ Definito |
| Piano dei conti personalizzato | E3 | v0.1 | ✅ Definito |
| Registrazione partita doppia | E3 | v0.1 | ✅ Definito |
| Fatturazione attiva SDI | E5 | v0.3 | ✅ Definito |

**Gap nella contabilità:**
- ❌ **Note spese** — Non esiste nessuna story per gestione note spese dipendenti/titolare
- ❌ **Cespiti e ammortamenti** — Nessun tracking di beni strumentali, piani di ammortamento, registro cespiti
- ❌ **Gestione ritenute d'acconto** — Manca completamente (certificazione unica CU, versamento ritenute)
- ❌ **Prima nota cassa** — Solo banca, manca la gestione contanti (cassa contanti, piccola cassa)
- ❌ **Corrispettivi giornalieri** — Per attività con scontrini/ricevute (registratore telematico)
- ❌ **Gestione multi-valuta avanzata** — Solo conversione BCE base in riconciliazione, manca contabilità multi-valuta
- ❌ **Ratei e risconti** — Nessuna gestione di competenza temporale (canoni, affitti, assicurazioni)
- ❌ **Gestione Intrastat** — Obbligatorio per chi commercia con UE

### Area FISCO E COMPLIANCE (coperta al 65%)

| Funzione | Epic | Versione | Stato |
|----------|------|----------|-------|
| Scadenzario fiscale base | E4 | v0.2 | ✅ Definito |
| Alert scadenze personalizzate | E5 | v0.3 | ✅ Definito |
| Liquidazione IVA automatica | E5 | v0.3 | ✅ Definito |
| Bilancio CEE | E5 | v0.3 | ✅ Definito |
| Monitor normativo | E7 | v0.4 | ✅ Definito |

**Gap nel fisco:**
- ❌ **Dichiarazione dei redditi** — Nessun supporto alla compilazione del Modello Redditi SC/SP/PF
- ❌ **Modello F24** — Lo scadenzario mostra quando pagare, ma non genera/compila il modello F24
- ❌ **LIPE (Comunicazione Liquidazione IVA)** — Obbligo trimestrale, manca l'invio telematico
- ❌ **Esterometro** — Comunicazione operazioni transfrontaliere (dal 2024 via SDI, ma serve gestione)
- ❌ **Certificazione Unica (CU)** — Obbligatoria per chi paga collaboratori/professionisti con ritenuta
- ❌ **Modello 770** — Dichiarazione sostituti d'imposta
- ❌ **IMU/TARI** — Calcolo e scadenze imposte locali (immobili aziendali)
- ❌ **Imposta di bollo** — €2 su fatture esenti IVA >€77,16 (obbligo, calcolo automatico)
- ❌ **Conservazione digitale a norma** — Citata come rischio nel PRD, ma nessuna story per l'implementazione (serve provider certificato: Aruba, InfoCert)

### Area BANCA E TESORERIA (coperta al 70%)

| Funzione | Epic | Versione | Stato |
|----------|------|----------|-------|
| Open Banking AISP (lettura conto) | E6 | v0.3 | ✅ Definito |
| Cash flow predittivo 90gg | E6 | v0.3 | ✅ Definito |
| Riconciliazione fatture↔pagamenti | E6 | v0.3 | ✅ Definito |
| Pagamenti PISP (bonifici) | E6 | v0.4 | ✅ Definito |

**Gap nella tesoreria:**
- ❌ **Budget annuale** — Nessuno strumento per creare budget previsionale e confrontarlo con il consuntivo
- ❌ **Gestione multi-conto** — La story US-24 parla di "un conto", ma una PMI ha spesso 2-3 conti su banche diverse
- ❌ **Gestione finanziamenti** — Mutui, leasing, fidi bancari, linee di credito — il CEO deve sapere rate, scadenze, piano di ammortamento
- ❌ **Gestione RiBa/SDD** — Ricevute bancarie e addebiti diretti — strumenti fondamentali per incassi B2B italiani
- ❌ **Rapporto banca** — Rating bancario, Centrale Rischi, affidamenti — il CEO deve sapere come la banca lo vede
- ❌ **Gestione anticipi su fatture** — Anticipo fatture/factoring è usatissimo dalle PMI per liquidità

### Area DASHBOARD E REPORTING (coperta al 40%)

| Funzione | Epic | Versione | Stato |
|----------|------|----------|-------|
| Dashboard fatture e stato agenti | E4 | v0.1 | ✅ Definito |
| Dashboard scritture contabili | E4 | v0.1 | ✅ Definito |
| Report per commercialista (PDF/CSV) | E4 | v0.2 | ✅ Definito |

**Gap nella reportistica:**
- ❌ **Dashboard CEO/Cruscotto direzionale** — Il CEO non vuole vedere "stato agenti". Vuole:
  - Fatturato mese/trimestre/anno vs budget vs anno precedente
  - Margine operativo lordo (EBITDA)
  - Andamento costi per categoria
  - Top 10 clienti per fatturato
  - Top 10 fornitori per costo
  - Indice di liquidità corrente
  - DSO (Days Sales Outstanding — tempo medio incasso)
  - DPO (Days Payable Outstanding — tempo medio pagamento)
- ❌ **Confronto budget vs consuntivo** — Fondamentale per il controllo di gestione
- ❌ **Report personalizzabili** — Solo PDF/CSV fisso, nessun report builder
- ❌ **Export contabilità per software studio** — Manca integrazione con Zucchetti, TeamSystem, Profis oltre al CSV base
- ❌ **Analisi marginalità** — Margine per cliente, per progetto, per servizio
- ❌ **Break-even analysis** — Quando raggiungo il pareggio?

---

## 2. Aree Completamente Assenti

Queste sono le aree che il PRD menziona solo nell'anti-scope ("Won't Have") ma che un CEO di PMI gestisce quotidianamente.

### 2.1 GESTIONE DEL PERSONALE (HR) — Assente

Un titolare di PMI con 5-20 dipendenti dedica il 15-20% del suo tempo alla gestione del personale.

**Cosa serve al CEO:**

| Funzione | Urgenza per CEO | Complessità | Note |
|----------|:--------------:|:-----------:|------|
| Anagrafica dipendenti | Alta | Bassa | Nome, contratto, data assunzione, livello, RAL |
| Costo del personale | Critica | Alta | RAL → costo azienda (contributi INPS, INAIL, TFR, 13a, 14a, ferie) |
| Buste paga (cedolini) | Alta | Molto Alta | Calcolo netto da lordo, trattenute, addizionali regionali/comunali |
| Gestione presenze | Media | Media | Ferie, permessi, malattia, straordinari, ROL |
| CCNL e livelli | Alta | Alta | Ogni settore ha il suo CCNL con tabelle retributive diverse |
| TFR e accantonamenti | Alta | Alta | Calcolo, rivalutazione, destinazione (azienda/fondo/INPS) |
| Budget HR | Alta | Media | Simulazione: "se assumo 2 persone, quanto mi costa in più all'anno?" |
| Scadenze HR | Media | Bassa | Scadenza contratti a tempo determinato, periodi di prova |
| F24 contributi | Alta | Alta | Versamento INPS, IRPEF dipendenti, addizionali — mensile |
| CU e 770 | Alta | Alta | Certificazione Unica annuale, Modello 770 |

**Perché è critico:** Il costo del personale è la voce di spesa #1 per il 70% delle PMI italiane. Un CEO che non sa quanto gli costa un dipendente non può fare budget.

**Agente proposto:** `HRAgent` — v1.0 o v1.5
- Integrazione con CCNL digitali
- Calcolo costo azienda da RAL
- Simulazione assunzioni
- Gestione presenze base
- Per le buste paga vere: integrazione con provider specializzato (Zucchetti Paghe, TeamSystem HR)

### 2.2 GESTIONE COMMERCIALE E CRM — Assente

Il CEO di una PMI è quasi sempre anche il commerciale.

**Cosa serve al CEO:**

| Funzione | Urgenza per CEO | Complessità | Note |
|----------|:--------------:|:-----------:|------|
| Anagrafica clienti | Alta | Bassa | Ragione sociale, P.IVA, contatti, settore, note |
| Anagrafica fornitori | Alta | Bassa | Stessa cosa, lato acquisti |
| Pipeline vendite | Alta | Media | Opportunità → trattativa → preventivo → ordine → fattura |
| Preventivi/offerte | Critica | Media | Genera preventivo, invia al cliente, traccia stato |
| Ordini clienti | Alta | Media | Conferma d'ordine → DDT → fattura |
| Listini e tariffe | Media | Media | Listino base, sconti per cliente, condizioni commerciali |
| Analisi clienti | Alta | Media | Fatturato per cliente, trend, margine, affidabilità pagamenti |
| Analisi fornitori | Media | Bassa | Spesa per fornitore, confronto prezzi, affidabilità consegne |
| Contratti attivi | Alta | Media | Scadenze contrattuali, rinnovi automatici, clausole |

**Perché è critico:** ContaBot sa che hai fatturato €120K con il cliente X, ma non sa se hai una pipeline di €80K in trattativa. Il CEO decide il futuro guardando la pipeline, non il passato.

**Agente proposto:** `CommAgent` — v1.0+
- CRM base (anagrafiche + pipeline + note)
- Generazione preventivi da template
- Conversione preventivo → ordine → fattura (collegamento con ContaAgent)
- Dashboard commerciale (pipeline, win rate, tempo medio chiusura)

### 2.3 GESTIONE PROGETTI E COMMESSE — Assente

Per le PMI di servizi (consulenza, IT, ingegneria, design), la gestione progetti è il cuore del business.

**Cosa serve al CEO:**

| Funzione | Urgenza per CEO | Complessità | Note |
|----------|:--------------:|:-----------:|------|
| Anagrafica progetti/commesse | Alta | Bassa | Cliente, budget, date, stato |
| Budget di progetto | Critica | Media | Budget previsto vs costi effettivi (ore + spese) |
| Timesheet / Ore lavorate | Alta | Media | Chi ha lavorato su cosa, per quante ore, a quale tariffa |
| SAL (Stato Avanzamento Lavori) | Alta | Media | Milestone, % avanzamento, fatturato vs lavoro |
| Margine di commessa | Critica | Alta | Ricavi - Costi (personale + spese dirette + overhead) |
| Allocazione risorse | Media | Alta | Chi è disponibile, chi è sovraccaricato |
| Report progetto | Alta | Media | Report per il cliente + report interno |

**Perché è critico:** Una PMI di servizi che non traccia il margine per commessa può fatturare €500K e scoprire a fine anno di aver perso soldi su metà dei progetti.

**Agente proposto:** `ProjectAgent` — v1.0+
- Anagrafica commesse con budget
- Timesheet base (ore per persona per progetto)
- Calcolo margine: fatturato - (ore × costo orario) - spese dirette
- SAL con milestone e % avanzamento
- Collegamento con ContaAgent (fatture legate a commessa)

### 2.4 GESTIONE ACQUISTI E FORNITORI — Assente

Oltre alla fattura passiva (che ContaBot gestisce), serve la gestione del processo d'acquisto.

**Cosa serve al CEO:**

| Funzione | Urgenza per CEO | Complessità | Note |
|----------|:--------------:|:-----------:|------|
| Ordini d'acquisto | Media | Media | Ordine → ricezione → fattura → pagamento |
| Confronto preventivi fornitori | Media | Bassa | 3 preventivi, confronta e scegli |
| Albo fornitori qualificati | Bassa | Bassa | Lista fornitori approvati per categoria |
| Contratti di fornitura | Media | Media | Scadenze, rinnovi, condizioni |
| DDT (Documenti di Trasporto) | Media | Media | Per chi ha merce fisica |

**Agente proposto:** `FornitureAgent` — v1.5+
- Gestione ordini d'acquisto
- Matching ordine → fattura (già parzialmente in riconciliazione)
- Albo fornitori con rating

### 2.5 GESTIONE DOCUMENTALE E CONTRATTI — Assente

Ogni PMI ha contratti, NDA, accordi quadro, polizze. Nessuno li gestisce.

**Cosa serve al CEO:**

| Funzione | Urgenza per CEO | Complessità | Note |
|----------|:--------------:|:-----------:|------|
| Repository documentale | Alta | Media | Tutti i documenti aziendali in un posto, ricercabili |
| Gestione contratti | Alta | Media | Scadenze, rinnovi automatici, alert pre-scadenza |
| Polizze assicurative | Media | Bassa | RC, D&O, infortuni — scadenze e coperture |
| Verbali assemblea/CdA | Media | Bassa | Per SRL: obbligo legale |
| Gestione deleghe e poteri | Bassa | Media | Chi può firmare cosa, procure |

**Agente proposto:** `DocAgent` — v1.5+
- Repository con ricerca full-text
- Scadenzario contratti (alert 30/60/90 giorni prima)
- Template contratti base

### 2.6 COMPLIANCE E GOVERNANCE — Assente

Il CEO ha obblighi legali oltre al fisco.

**Cosa serve al CEO:**

| Funzione | Urgenza per CEO | Complessità | Note |
|----------|:--------------:|:-----------:|------|
| Privacy/GDPR | Alta | Alta | Registro trattamenti, DPO, informative, consensi |
| Sicurezza sul lavoro D.Lgs 81/08 | Critica | Alta | DVR, formazione obbligatoria, scadenze visite mediche |
| Antiriciclaggio (se applicabile) | Media | Alta | Per studi professionali e intermediari |
| Registro revisori/sindaci | Bassa | Bassa | Per SRL sopra soglia |
| Modello 231 (se applicabile) | Bassa | Alta | Responsabilità amministrativa enti |

**Perché è critico:** La sicurezza sul lavoro ha sanzioni penali. Un CEO che dimentica la visita medica di un dipendente rischia personalmente.

**Agente proposto:** `ComplianceAgent` — v2.0
- Scadenzario obblighi (sicurezza, privacy, formazione)
- Checklist conformità per tipo azienda
- Alert proattivi

### 2.7 CONTROLLO DI GESTIONE — Assente

Questa è la carenza più grande per un CEO. La contabilità generale (che ContaBot fa) risponde alla domanda "quanto ho speso?". Il controllo di gestione risponde a "dove ho guadagnato e dove ho perso?".

**Cosa serve al CEO:**

| Funzione | Urgenza per CEO | Complessità | Note |
|----------|:--------------:|:-----------:|------|
| Centri di costo | Critica | Media | Ogni spesa allocata a un centro (reparto, progetto, sede) |
| Budget annuale | Critica | Media | Previsione per voce di costo, confronto mensile con consuntivo |
| Analisi scostamenti | Critica | Media | Budget vs actual, cause, trend |
| Margine per servizio/prodotto | Critica | Alta | Prezzo - costo diretto - overhead allocato |
| Break-even point | Alta | Media | Quanti clienti/progetti servono per coprire i costi fissi |
| KPI personalizzabili | Alta | Media | Il CEO vuole i SUOI numeri, non quelli standard |
| Piano investimenti | Media | Media | ROI di un acquisto, payback period |
| Simulazioni "what-if" | Alta | Alta | "Se alzo i prezzi del 10%, che impatto ha?" |

**Perché è critico:** È la differenza tra un CEO che guida l'azienda e uno che la subisce. Senza controllo di gestione, il bilancio è solo un documento storico.

**Agente proposto:** `ControllerAgent` — v1.0-v1.5
- Centri di costo + allocazione automatica dalle fatture categorizzate
- Budget previsionale con confronto mensile
- Dashboard KPI CEO personalizzabile
- Collegamento con ProjectAgent per margine commessa

---

## 3. Matrice Priorità: Cosa Aggiungere e Quando

```
IMPATTO SUL CEO
      Alto │  CONTROLLO      HR             COMMERCIALE
           │  DI GESTIONE    (costo pers.)  (pipeline)
           │  ★★★★★          ★★★★★          ★★★★
           │
           │  PROGETTI       CONTABILITÀ    TESORERIA
           │  (margine comm.)  (gap minori)   (gap minori)
           │  ★★★★           ★★★            ★★★
     Medio │
           │  DOCUMENTALE    COMPLIANCE     ACQUISTI
           │  (contratti)    (81/08, GDPR)  (ordini)
           │  ★★★            ★★★            ★★
           │
     Basso │
           └────────────────────────────────────────────
              Bassa         Media         Alta
                      COMPLESSITÀ IMPLEMENTATIVA
```

### Priorità Raccomandata

| # | Area | Agente | Versione Proposta | Motivo |
|---|------|--------|:-----------------:|--------|
| 1 | Controllo di Gestione | ControllerAgent | **v1.0** | CEO VUOLE QUESTO. È il differenziante. Senza, ContaBot è un altro software di fatturazione. |
| 2 | Gap contabilità minori | (integra ContaAgent) | **v0.3-v0.4** | Note spese, cespiti, ritenute, imposta di bollo sono obblighi contabili base |
| 3 | HR — Costo del personale | HRAgent (base) | **v1.0** | Il CEO deve sapere quanto gli costa un dipendente. Non serve fare le buste paga. |
| 4 | Commerciale — CRM base | CommAgent | **v1.0** | Pipeline + preventivi + anagrafiche. Collega vendite a fatturazione. |
| 5 | Gap fisco | (integra FiscoAgent) | **v0.4-v1.0** | F24 compilazione, CU, conservazione digitale sono obblighi |
| 6 | Progetti e commesse | ProjectAgent | **v1.0-v1.5** | Critico per PMI di servizi (>50% target) |
| 7 | Documentale | DocAgent | **v1.5** | Repository + scadenzario contratti |
| 8 | Compliance | ComplianceAgent | **v2.0** | D.Lgs 81/08, GDPR — necessario ma complesso |
| 9 | Acquisti avanzato | FornitureAgent | **v1.5-v2.0** | Ordini d'acquisto, albo fornitori |

---

## 4. Dettaglio Gap Contabili da Risolvere Prima (v0.3-v0.4)

Questi non richiedono un nuovo agente — sono estensioni del ContaAgent/FiscoAgent esistente.

### 4.1 Note Spese

```
FLUSSO:
Titolare/Dipendente
  ├─> Fotografa scontrino/ricevuta
  ├─> App categorizza (carburante, pranzo, viaggio...)
  ├─> Validazione (policy aziendale: max €25/pranzo)
  └─> ContaAgent registra:
      DARE: 6200 Trasferte    €45,00
      AVERE: 5010 Dipendenti  €45,00
      (oppure AVERE: 1010 Cassa se rimborso immediato)

STORIES MANCANTI:
- US-XX: Upload nota spese (foto + importo + categoria)
- US-XX: Policy di spesa configurabile per tipo
- US-XX: Approvazione nota spese (se >1 persona)
- US-XX: Rimborso e registrazione contabile
```

### 4.2 Cespiti e Ammortamenti

```
FLUSSO:
Acquisto bene strumentale (es. MacBook Pro €2.500)
  ├─> ContaAgent riconosce (importo > soglia, categoria "attrezzature")
  ├─> Crea scheda cespite
  │   └─ Valore: €2.500, Categoria: "attrezzature informatiche"
  │   └─ Aliquota ammortamento: 20% (tabelle ministeriali)
  │   └─ Durata: 5 anni
  ├─> Ogni anno, registra ammortamento:
  │   DARE: 6500 Ammortamento attrezzature    €500
  │   AVERE: 2500 Fondo ammortamento attr.    €500
  └─> Registro cespiti aggiornato

STORIES MANCANTI:
- US-XX: Creazione automatica scheda cespite da fattura
- US-XX: Calcolo ammortamento (ordinario, anticipato, ridotto)
- US-XX: Registro cespiti con stato e valore residuo
- US-XX: Dismissione/vendita cespite con plusvalenza/minusvalenza
```

### 4.3 Ritenute d'Acconto

```
FLUSSO:
Ricevo fattura da professionista con ritenuta 20%:
  Imponibile: €1.000 + IVA 22% = €1.220
  Ritenuta 20% su €1.000 = €200
  Da pagare al fornitore: €1.220 - €200 = €1.020
  Da versare all'Erario (F24): €200 entro il 16 del mese successivo

  ContaAgent registra:
  DARE: 6110 Consulenze         €1.000
  DARE: 2212 IVA a credito        €220
  AVERE: 4010 Fornitori         €1.020
  AVERE: 2310 Erario c/ritenute   €200

STORIES MANCANTI:
- US-XX: Riconoscimento automatico fatture con ritenuta
- US-XX: Calcolo importo da pagare (netto ritenuta)
- US-XX: Scadenzario versamento ritenute (F24 cod. tributo 1040)
- US-XX: Generazione Certificazione Unica (CU) annuale
```

### 4.4 Imposta di Bollo

```
FLUSSO:
Fattura esente IVA (art. 10, art. 15, regime forfettario) con importo > €77,16
  ├─> Imposta di bollo €2 obbligatoria
  ├─> Nella fattura XML: <DatiBollo><BolloVirtuale>SI</BolloVirtuale><ImportoBollo>2.00</ImportoBollo></DatiBollo>
  ├─> Versamento cumulativo trimestrale via F24 (cod. tributo 2501-2504)
  └─> ContaAgent registra:
      DARE: 6300 Imposte e tasse   €2
      AVERE: 2320 Erario c/bollo   €2

STORIES MANCANTI:
- US-XX: Rilevamento automatico obbligo bollo (fattura esente + importo > €77,16)
- US-XX: Calcolo e conteggio bolli nel periodo
- US-XX: Scadenza versamento trimestrale F24
```

### 4.5 Ratei e Risconti

```
FLUSSO:
Pago assicurazione annuale €1.200 il 1° ottobre (copre ott-set anno successivo):
  ├─> Al pagamento:
  │   DARE: 6400 Assicurazioni     €1.200
  │   AVERE: 1110 Banca c/c        €1.200
  │
  ├─> Al 31/12 (chiusura esercizio), risconto attivo:
  │   9 mesi pagati ma di competenza anno successivo = €900
  │   DARE: 1800 Risconti attivi     €900
  │   AVERE: 6400 Assicurazioni      €900
  │
  └─> Al 1/1 anno successivo, riapre:
      DARE: 6400 Assicurazioni       €900
      AVERE: 1800 Risconti attivi    €900

STORIES MANCANTI:
- US-XX: Identificazione automatica costi/ricavi pluriennali (affitto, assicurazione, canoni)
- US-XX: Calcolo ratei/risconti a fine esercizio
- US-XX: Scritture automatiche di assestamento
```

---

## 5. La Dashboard che il CEO Vuole Davvero

La dashboard attuale (US-14, US-15) è pensata per un contabile. Il CEO vuole questo:

```
┌────────────────────────────────────────────────────────────────────────┐
│                    CRUSCOTTO CEO — AgentFlow PMI                       │
│                    Marzo 2026                                          │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  FATTURATO                    MARGINE                   LIQUIDITÀ      │
│  ┌──────────────┐             ┌──────────────┐         ┌────────────┐ │
│  │ Mese:  €45K  │ ▲ +12%     │ EBITDA: 22%  │         │ Cassa:     │ │
│  │ YTD:  €135K  │ vs 2025    │              │         │ €23.400    │ │
│  │ Budget: €150K│             │ vs 2025: 19% │ ▲       │            │ │
│  │ Delta: -€15K │ ⚠️         │              │         │ 90gg: OK   │ │
│  └──────────────┘             └──────────────┘         └────────────┘ │
│                                                                        │
│  INCASSI / PAGAMENTI          TOP CLIENTI              SCADENZE       │
│  ┌──────────────┐             ┌──────────────┐         ┌────────────┐ │
│  │ Da incassare:│             │ 1. Acme  €40K│         │ 🔴 IVA     │ │
│  │   €34K       │             │ 2. Beta  €28K│         │    16 apr  │ │
│  │ DSO: 45gg    │ ⚠️ (era 38)│ 3. Gamma €22K│         │ 🟡 INPS   │ │
│  │              │             │              │         │    16 mag  │ │
│  │ Da pagare:   │             │ Concentr.    │         │ 🟢 F24     │ │
│  │   €28K       │             │ Top3 = 67% ⚠️│         │    16 giu  │ │
│  │ DPO: 32gg    │             └──────────────┘         └────────────┘ │
│  └──────────────┘                                                      │
│                                                                        │
│  COSTO PERSONALE              PROGETTI                 ALERT          │
│  ┌──────────────┐             ┌──────────────┐         ┌────────────┐ │
│  │ Mese: €18.5K │             │ Attivi: 4    │         │ ⚠️ Cliente │ │
│  │ YTD:  €55.5K │             │ In ritardo: 1│         │ Rossi: 45gg│ │
│  │ vs budget:   │             │ Margine medio│         │ senza pag. │ │
│  │   +€2K ⚠️    │             │   28%        │         │            │ │
│  │ (straordinari)│             │ A rischio: 1 │ 🔴      │ ⚠️ Contratto│ │
│  └──────────────┘             └──────────────┘         │ TIM: scade │ │
│                                                         │ tra 30gg   │ │
│                                                         └────────────┘ │
│                                                                        │
│  [Fatturato ▼] [Cash Flow ▼] [Personale ▼] [Progetti ▼] [Fisco ▼]   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Riepilogo Finale: PRD Attuale vs CEO Reale

```
AREA DI GESTIONE              PRD ATTUALE    COSA MANCA          IMPATTO CEO
─────────────────────────────────────────────────────────────────────────────
Contabilità generale          ████████░░ 80%  Note spese, cespiti,  Medio
                                              ritenute, ratei

Fatturazione passiva          █████████░ 95%  Corrispettivi,        Basso
                                              Intrastat

Fatturazione attiva           ████████░░ 80%  Imposta bollo auto,   Medio
                                              note credito avanzate

Fisco e compliance            ██████░░░░ 65%  F24, CU, 770, LIPE,  Alto
                                              conservazione

Banca e tesoreria             ███████░░░ 70%  Multi-conto, budget,  Alto
                                              finanziamenti, RiBa

Dashboard e reporting         ████░░░░░░ 40%  Cruscotto CEO, KPI,   CRITICO
                                              budget vs actual

Controllo di gestione         ░░░░░░░░░░  0%  TUTTO                 CRITICO
Gestione personale (HR)       ░░░░░░░░░░  0%  TUTTO                 CRITICO
Gestione commerciale (CRM)    ░░░░░░░░░░  0%  TUTTO                 ALTO
Gestione progetti/commesse    ░░░░░░░░░░  0%  TUTTO                 ALTO
Gestione acquisti             ░░░░░░░░░░  0%  TUTTO                 MEDIO
Gestione documentale          ░░░░░░░░░░  0%  TUTTO                 MEDIO
Compliance e governance       ░░░░░░░░░░  0%  TUTTO                 MEDIO
```

### Conclusione

Il PRD attuale copre bene il **ciclo della fattura** (ricezione → categorizzazione → registrazione → pagamento → riconciliazione). Questo è il cuore della promessa MVP e va bene così per v0.1-v0.4.

Ma per diventare il "team di agenti AI che gestisce l'azienda" (come dice la vision), servono almeno 4 aree in più per v1.0:

1. **ControllerAgent** — Trasforma i dati contabili in informazioni decisionali per il CEO
2. **HRAgent (base)** — Almeno il costo del personale e il budget HR
3. **CommAgent** — CRM base + pipeline + preventivi
4. **Dashboard CEO** — Il cruscotto direzionale al posto della dashboard tecnica

Queste 4 aggiunte trasformerebbero ContaBot da "software di fatturazione intelligente" a "copilota del CEO".

---

_Analisi gap — 2026-03-22_
