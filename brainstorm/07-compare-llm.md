# Confronto Multi-LLM + Sessione Brainstorming — 2026-03-28

## Modelli utilizzati
| Ruolo | Provider | Modello | Tipo |
|-------|----------|---------|------|
| Analista 1 | Anthropic | claude-opus-4-6 | locale |
| Analista 2 | OpenAI | gpt-4o | via API |

## Focus: Strategia di importazione dati + architettura agenti per AgentFlow PMI

---

# PARTE 1 — Confronto LLM (analisi iniziale)

## Prospettiva claude-opus-4-6 (Anthropic)

### 1. Prioritizzazione

| Fase | Flusso | Perche ora | Effort |
|------|--------|-----------|--------|
| Sprint A | Movimenti bancari (Open Banking) | Senza banca non c'e cash flow reale | M |
| Sprint A | Corrispettivi telematici | Completano fatturato, stessa fonte cassetto | S |
| Sprint B | F24 versamenti | Cash flow incompleto senza uscite fiscali | M |
| Sprint B | Ritenute d'acconto (completamento) | Parser gia le rileva, serve solo calcolo | S |
| Sprint C | Note spese + OCR | Differenziante per chi ha trasferte | M |
| Sprint C | Ammortamenti cespiti | Necessari per bilancio, calcolo interno | S |
| Sprint D | CU + Ratei/Risconti | Annuali/periodici, meno urgenti | S |

**Dipendenze critiche:**
```
Banca → Riconciliazione → Cash flow reale
Corrispettivi → Liquidazione IVA completa
F24 → Quadratura pagamenti fiscali
Paghe + F24 → Costo totale personale
```

### 2. Architettura agenti — 3 pattern di interazione

**Pattern A: Proattivo (Push)** — scadenze e alert
```
Agente: "Tra 5gg scade F24. IRPEF €1.243 + INPS €1.350 = €2.593. Preparo il modello?"
```

**Pattern B: Consulente (Conversazionale)** — l'utente chiede
```
Utente: "Come sto messo?"
Agente: "Fatturato €45k (+12%), Costi €32k, Margine 29%. 3 fatture scadute per €8.5k"
```

**Pattern C: Orchestratore (Onboarding)** — guida passo passo
```
Agente: "Per il cash flow mi mancano: ❌ Banca ❌ Paghe Feb ✅ Fatture aggiornate.
         Collegando la banca saliresti dal 45% al 65% di completezza."
```

## Prospettiva gpt-4o (OpenAI)

### Prioritizzazione
1. **Movimenti bancari** — Fondamentale per cash flow e riconciliazione
2. **Corrispettivi telematici** — Completa il quadro vendite giornaliere
3. **F24 versamenti** — Critico per gestione scadenze fiscali
4. Note spese (media), CU (media), Ammortamenti e Ratei (bassa)

### Architettura agenti
- Principalmente proattivi (push per urgenze, pull per report)
- Mix conversazionale (chatbot) + dashboard per visione d'insieme

## Meta-analisi

### Convergenze (segnale forte)
1. **Banca prima di tutto**: priorita #1 dopo le fatture
2. **Corrispettivi + F24 subito dopo**: stessa top-3
3. **Agenti proattivi**: push per scadenze, conversazionale per situazione
4. **Roadmap 3-6-12 mesi**: stessa struttura temporale

### Divergenze chiave
| Tema | Claude | GPT |
|------|--------|-----|
| Onboarding | Completeness Score (%) con framing positivo | Wizard + tooltips |
| Gap analysis | 6 gap specifici (mutui, magazzino, compensazioni) | 3 gap generici |
| ESG | Non rilevante per micro-PMI | Menzionato |

### Blind spot condivisi
1. Integrazione con il commercialista (portale/export)
2. Gestione multi-periodo (chiusure, passaggio anno)
3. Deleghe e ruoli
4. Import storico iniziale

---

# PARTE 2 — Decisione fondamentale: Posizionamento prodotto

## AgentFlow NON e' un gestionale contabile. E' un CONTROLLER AZIENDALE AI.

Il sistema non sostituisce il programma di contabilita — lo affianca. Non deve essere rigido, deve essere di supporto. L'imprenditore non vuole fare il contabile, vuole capire come va la sua azienda.

| Aspetto | Gestionale classico | AgentFlow |
|---------|-------------------|-----------|
| **Data entry** | L'utente inserisce | I dati arrivano da soli |
| **Interfaccia** | Tabelle, griglie, form | Conversazione, insight, azioni |
| **Valore** | "Registra correttamente" | "Capisci cosa sta succedendo" |
| **Budget** | Foglio Excel da compilare | Chiacchierata con l'agente |
| **Bilancio** | L'utente lo legge (se sa come) | L'agente lo spiega |
| **Errore** | "Risolvi tu" | "Ho trovato questo, vuoi che sistemi?" |
| **Competizione** | Fatture in Cloud, TeamSystem | Nessuna — nuovo posizionamento |

### Principio di design: ZERO data entry, MASSIMA interpretazione

```
PRIMA (approccio contabile):
  Utente → carica file → conferma categorie → verifica scritture → corregge errori
  80% tempo su data entry, 20% su valore

DOPO (approccio controller):
  Fonti automatiche → AgentFlow importa silenziosamente → agente interpreta → parla
  0% data entry, 100% su valore
```

### Import silenzioso, non interattivo
```
Invece di:  "Ho importato 47 fatture, verificale una per una"
Meglio:     "47 fatture importate. 2 hanno bisogno di attenzione:
             - Fattura #234: importo anomalo (€45.000 vs media €2.000)
             - Fattura #567: fornitore nuovo, non so come categorizzarla"
```

---

# PARTE 3 — Principio CRUD: ogni voce = import + manuale

**Il CRUD e' la base. L'import e' l'acceleratore.** L'utente deve SEMPRE poter inserire, modificare, eliminare qualsiasi voce a mano. L'import automatico e' una comodita, non un obbligo.

| Voce | Import automatico | CRUD manuale |
|------|------------------|-------------|
| Movimenti banca | PDF/CSV/Open Banking | Aggiungi/modifica/elimina singolo movimento |
| Corrispettivi | XML da cassetto fiscale | Inserisci corrispettivo giornaliero |
| Costo personale | PDF riepilogo paghe | Inserisci voce stipendio (gia fatto) |
| Saldi bilancio | PDF/Excel/XBRL | Inserisci saldo conto manuale |
| F24 | PDF ricevuta | Inserisci versamento manuale |
| Note spese | Foto/PDF con OCR | Inserisci nota spesa |
| Cespiti | Auto da fatture | Inserisci cespite manuale |
| Contratti ricorrenti | PDF contratto | Inserisci ricorrenza |
| Finanziamenti | PDF piano ammortamento | Inserisci rata manuale |
| Budget | Proposta agente da storico | Modifica ogni voce liberamente |

---

# PARTE 4 — Mappa completa importazioni

## Gia implementati
| # | Flusso | Formato | Stato |
|---|--------|---------|-------|
| A1 | Fatture passive (ricevute) | XML FatturaPA | FATTO |
| A2 | Fatture attive (emesse) | XML FatturaPA | FATTO |
| A3 | Costo personale (paghe) | PDF Riepilogo Paghe | FATTO (parser da migliorare) |
| A4 | Bolli virtuali | Calcolo automatico | FATTO |

## Da implementare

| # | Flusso | Approccio | Priorita |
|---|--------|-----------|----------|
| B1 | Estratto conto bancario | PDF → LLM extraction + CSV fallback + Open Banking API | MUST |
| B2 | Corrispettivi telematici | XML COR10 da cassetto fiscale → parser → scrittura | MUST |
| B3 | F24 versamenti | PDF → LLM extraction codici tributo + importi | MUST |
| B4 | Saldi bilancio — Excel/CSV | Auto-detect colonne → mapping LLM → preview | MUST |
| B5 | Saldi bilancio — PDF | pdftotext → LLM extraction → mapping | MUST |
| B6 | Saldi bilancio — XBRL | Parser tassonomia itcc-ci → mapping CEE | SHOULD |
| B7 | Note spese | OCR → LLM categorizzazione → approvazione | SHOULD |
| B8 | Ammortamenti cespiti | Auto da fatture — no file esterno | SHOULD |
| B9 | Ritenute d'acconto | Completamento: calcolo netto + scadenza F24 | SHOULD |
| B10 | CU Certificazione Unica | LLM extraction da PDF | COULD |
| B11 | Contratti ricorrenti | LLM extraction → importo/frequenza/scadenza | SHOULD |
| B12 | Finanziamenti e mutui | LLM extraction piano ammortamento | SHOULD |

## Strategia banca: 3 canali complementari
- **PDF + LLM** (subito): funziona con tutte le banche, storico illimitato
- **CSV fallback** (subito): export da home banking
- **Open Banking API** (quando Fabrick/Salt Edge pronti): automatico
- **Il PDF copre lo storico, l'API copre il futuro**

## Ammortamenti: auto-generati da fatture
Le fatture di beni strumentali arrivano dal cassetto fiscale. L'agente:
1. Rileva categoria "Immobilizzazione"
2. Applica aliquota ministeriale (20% HW, 25% auto, 12% mobili)
3. Chiede conferma
4. Genera scritture periodiche
5. Beni sotto €516,46 → costo intero nell'anno

---

# PARTE 5 — Budget Agent e controllo di gestione

## Budget come conversazione, non come form

```
Agente: "Costruiamo il budget 2026? Parto dai dati del 2025.
         L'anno scorso hai fatturato €480k. Con +5% saremmo a €504k."
Utente: "Si ma perdo il cliente Rossi che valeva 50k"
Agente: "OK, budget ricavi: €454k. Aggiustiamo i costi?"
```

## Controllo di gestione = 3 domande

| Domanda | Come risponde l'agente | Fonte dati |
|---------|----------------------|------------|
| "Come sto andando?" | Budget vs consuntivo, trend, scostamenti | Fatture + banca + paghe vs budget |
| "Ce la faccio a pagare tutto?" | Cash flow previsionale 90gg | Banca + scadenze + F24 + paghe |
| "Dove perdo soldi?" | Analisi costi per categoria, confronto periodi | Fatture passive categorizzate |

## Budget vs Consuntivo mensile (esempio)
```
MARZO 2026           Budget    Consuntivo    Scostamento
Ricavi               €45.000    €38.000      -15% ⚠️
Personale            €18.000    €18.200      +1%  ✅
Fornitori            €9.000     €12.300      +37% 🔴
Utenze               €1.500     €1.480       -1%  ✅
Margine              €16.500    €6.020       -63% 🔴

Agente: "Marzo sotto budget del 15% sui ricavi. Il problema
sono i costi fornitori (+€3.300). Vedo 2 fatture straordinarie
da TechSupply — sono ricorrenti o una tantum?"
```

---

# PARTE 6 — Agenti di gestione aziendale

## 6 agenti con trigger e doppio canale

| Agente | Quando parla | Cosa dice | Canale |
|--------|-------------|-----------|--------|
| **Cash Flow** | Saldo sotto soglia / previsione negativa | "Tra 12gg il conto scende sotto €5k" | Dashboard + WhatsApp |
| **Adempimenti** | 10gg prima di scadenza | "F24 del 16/04: IRPEF + INPS = €2.593" | Dashboard + WhatsApp |
| **Controller** | Fine mese / su richiesta | "Budget vs consuntivo. Margine -63%" | Dashboard + chatbot |
| **Riconciliazione** | Dopo ogni sync banca | "3 movimenti non abbinati" | Dashboard |
| **Alert** | Anomalia rilevata | "Fattura scaduta da 45gg, P.IVA cessata" | Dashboard + WhatsApp |
| **Onboarding** | Dato mancante che blocca un agente | "Per il Cash Flow mi serve la banca" | Dashboard |

### Regole UX
- **Mai piu di 3 azioni pendenti** visibili — le altre in backlog
- **Doppio canale**: Dashboard + WhatsApp/Telegram (l'imprenditore non apre l'app ogni giorno)
- **Framing positivo** nell'onboarding: "Hai sbloccato X", non "Ti manca il 55%"

---

# PARTE 7 — File esempio disponibili per sviluppo

## Inventario `esempi_import/`

### Banca/ (4 file, 2 banche diverse)
| File | Banca | Periodo | Layout |
|------|-------|---------|--------|
| `104371230_Estratto_conto_30_06_2024_2.pdf` | UniCredit | Q2 2024 | Data, Valuta, Descrizione, Uscite, Entrate |
| `104371230_Estratto_conto_31_03_2024_3.pdf` | UniCredit | Q1 2024 | Stesso layout |
| `31_05_2024_Estratto_Conto_rapporto_0000063948866.pdf` | Credit Agricole | Mag 2024 | Data, Valuta, Dare, Avere, Descrizione |
| `31_07_2024_Estratto_Conto_rapporto_0000063948866.pdf` | Credit Agricole | Lug 2024 | Stesso layout |

### bilanci/ (1 file)
| File | Contenuto |
|------|-----------|
| `Taal srl Bilancio contabile al 31.12.2023.pdf` | Bilancio completo: Situazione Patrimoniale (Attivo €10.691.368 / Passivo €10.490.937 + Utile €200.430) + Conto Economico (Costi €5.427.498 / Ricavi €5.627.928) + Elenco Clienti/Fornitori. Codici conto a 6+3 cifre. 856 righe di testo. |

### corrispettivi/ (~90 file XML)
| Formato | Namespace | Dati per file |
|---------|-----------|---------------|
| XML COR10 | `ivaservizi.agenziaentrate.it/docs/xsd/corrispettivi/dati/v1.0` | P.IVA esercente, data trasmissione, riepilogo per aliquota IVA (4%, 5%, 10%, 22%, N4), totale contanti + elettronico, numero documenti commerciali |

### pesonale/ (24 file PDF)
- 12 PDF paghe 2024 (Gen-Dic)
- 12 PDF paghe 2025 (Gen-Dic, alcuni splittati da multi-mese)
- Formati diversi: "Riepilogo Paghe", "Nota Contabile", "Paghe e Contributi"

---

# PARTE 8 — Blind spot risolti

| Blind spot | Soluzione |
|-----------|-----------|
| Commercialista | Export periodico + ruolo read-only + email auto-generata |
| Multi-periodo | Chiusura mensile proposta dall'agente + wizard passaggio anno |
| Deleghe | 2 ruoli base (Titolare + Collaboratore), ruoli custom dopo |
| Import storico | Cassetto fiscale (fatture anno) + PDF banca (storico) + saldi bilancio |

---

# PARTE 9 — Roadmap rivista

## Fase 1 (3 mesi): "Vedo tutto"
- Import banca (PDF+LLM, CSV, poi Open Banking API)
- Corrispettivi telematici (parser XML COR10)
- Saldi bilancio iniziali (PDF/Excel/XBRL)
- Riconciliazione automatica fatture ↔ movimenti
- Cash Flow Agent con dati reali
- CRUD manuale per ogni voce
- Onboarding con framing positivo

## Fase 2 (6 mesi): "Capisco tutto"
- **Budget Agent** (conversazionale, costruzione + controllo consuntivo)
- F24 import + calcolo automatico
- Controller Agent (budget vs consuntivo mensile)
- Ammortamenti auto da fatture
- Adempimenti Agent proattivo (scadenze push)
- Doppio canale notifiche (dashboard + WhatsApp/Telegram)

## Fase 3 (12 mesi): "Gestisco tutto"
- Note spese OCR
- Contratti ricorrenti + finanziamenti
- CU + ritenute complete
- Ratei e risconti
- Ruolo commercialista (portale read-only)
- Agent Consulente (suggerimenti fiscali, ottimizzazioni)

---

_Documento generato da sessione bs-chat + bs-compare — 2026-03-28_
_Agenti coinvolti: Alessandro, Davide, Nicola, Chiara, Marta_
_Modelli LLM: claude-opus-4-6 + gpt-4o_
