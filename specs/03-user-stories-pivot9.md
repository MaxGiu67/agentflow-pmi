# User Stories — Pivot 9: AgentFlow v3.0 — Dual Pipeline + Sales Agent AI

**AgentFlow PMI — Sales AI Platform per PMI italiane**

---

## Overview

Il Pivot 9 trasforma AgentFlow da controller contabile a **piattaforma AI per vendita + controller**. 6 Epic, ~25 stories.

**Principio guida:** Il prodotto scelto dal commerciale determina la pipeline. Un Sales Agent unico si adatta al prodotto. L'agente aiuta, non impone — il commerciale puo sempre saltare stati.

**Formato AC:** DATO-QUANDO-ALLORA, 4+ AC per story (1 happy path, 2 error/edge, 1 boundary).

---

## EPIC 17: Pipeline Templates

### US-200: Sistema pipeline template da DB

**Come** sistema
**Voglio** che ogni pipeline sia definita come template nel DB con stati, required_fields e SLA
**Per** permettere pipeline diverse per prodotti diversi e personalizzazione per tenant

**AC-200.1 (Happy Path)**: DATO che il sistema si avvia, QUANDO il tenant non ha pipeline template, ALLORA:
  - Vengono create automaticamente 3 pipeline template: T&M (6 stati), Corpo (7 stati), Elevia (8 stati)
  - Ogni stato ha: code, name, sequence, required_fields (JSONB), sla_days, is_won, is_lost

**AC-200.2 (Schema)**: DATO che creo un pipeline template, ALLORA:
  - La tabella `pipeline_templates` contiene: id, tenant_id, code, name, pipeline_type (services/product/custom), description, is_active
  - La tabella `pipeline_template_stages` contiene: id, template_id, code, name, sequence, required_fields, sla_days, is_won, is_lost, is_optional

**AC-200.3 (Tenant isolation)**: DATO che tenant A ha 3 template e tenant B ha 2 template custom, QUANDO listo i template, ALLORA:
  - Ogni tenant vede solo i propri template
  - I seed default sono creati per-tenant, non condivisi

**AC-200.4 (Boundary)**: DATO che un template ha 0 stati, QUANDO provo a usarlo per un deal, ALLORA:
  - Il sistema mostra errore "Pipeline template senza stati configurati"

**SP**: 5 | **Priorita**: Must Have | **Epic**: Pipeline Templates | **Dipendenze**: Nessuna

---

### US-201: Prodotto determina pipeline

**Come** commerciale
**Voglio** che quando creo un deal e scelgo il prodotto, il sistema attivi automaticamente la pipeline corretta
**Per** non dover pensare quale processo seguire — il prodotto lo decide

**AC-201.1 (Happy Path)**: DATO che il prodotto "Consulenza Java Senior" ha `pipeline_template_id` = T&M, QUANDO creo un deal con quel prodotto, ALLORA:
  - Il deal viene creato con `pipeline_template_id` = T&M
  - Lo stato iniziale e il primo stato della pipeline T&M ("Lead")
  - Il Kanban mostra il deal nella colonna "Lead" della pipeline T&M

**AC-201.2 (Cambio prodotto)**: DATO che un deal ha prodotto T&M e lo cambio a "Progetto a corpo", QUANDO salvo, ALLORA:
  - Il sistema chiede conferma: "Cambiando prodotto cambia la pipeline. Le info specifiche della pipeline precedente verranno conservate. Procedere?"
  - Se confermo, il deal passa alla pipeline Corpo, stato "Lead"

**AC-201.3 (Prodotto senza pipeline)**: DATO che creo un prodotto senza assegnare una pipeline template, QUANDO creo un deal con quel prodotto, ALLORA:
  - Il deal usa la pipeline default del tenant (prima pipeline attiva)

**AC-201.4 (Multi-deal stessa azienda)**: DATO che ACME SRL ha un deal T&M in corso, QUANDO creo un nuovo deal Elevia per la stessa azienda, ALLORA:
  - Il sistema accetta (stessa azienda, pipeline diverse)
  - Entrambi i deal sono visibili, ognuno nella propria pipeline

**SP**: 5 | **Priorita**: Must Have | **Epic**: Pipeline Templates | **Dipendenze**: US-200

---

### US-202: Admin personalizza pipeline template

**Come** admin
**Voglio** modificare i template pipeline (aggiungere/rimuovere/riordinare stati, cambiare required_fields e SLA)
**Per** adattare i processi di vendita alla mia azienda

**AC-202.1 (Happy Path)**: DATO che sono in Impostazioni > Pipeline, QUANDO seleziono il template T&M, ALLORA:
  - Vedo la lista ordinata degli stati con: nome, required_fields, SLA giorni, optional flag
  - Posso modificare nome, required_fields, SLA di ogni stato
  - Posso aggiungere uno stato in qualsiasi posizione
  - Posso riordinare gli stati (drag o sequence number)

**AC-202.2 (Stato opzionale)**: DATO che marco lo stato "Demo" come is_optional=true nella pipeline Corpo, ALLORA:
  - Il commerciale puo saltare direttamente da "Specifiche" a "Offerta"
  - L'agente non chiede info relative alla Demo se saltata

**AC-202.3 (Non modificare deal esistenti)**: DATO che ho 5 deal nella pipeline T&M e modifico un nome stato, ALLORA:
  - I deal esistenti mantengono lo stage_id (immutabile)
  - Solo i nuovi deal vedono il nome aggiornato

**AC-202.4 (Crea pipeline custom)**: DATO che clicco "Nuova pipeline", ALLORA:
  - Posso creare una pipeline custom con stati da zero
  - La pipeline e associabile ai prodotti del catalogo

**SP**: 5 | **Priorita**: Should Have | **Epic**: Pipeline Templates | **Dipendenze**: US-200

---

### US-203: Vista Kanban multi-pipeline

**Come** commerciale/manager
**Voglio** vedere i deal raggruppati per pipeline (tab T&M / Corpo / Elevia / Tutti)
**Per** focalizzarmi su un processo alla volta o avere la vista globale

**AC-203.1 (Happy Path — Tab "Tutti" = Kanban stacked per pipeline)**: DATO che ho deal in 3 pipeline diverse, QUANDO apro la pagina Pipeline CRM con tab "Tutti", ALLORA:
  - Vedo tab in alto: "Tutti", "Vendita Diretta", "Corpo", "Social Selling" (+ eventuali custom)
  - "Tutti" mostra **Kanban stacked per pipeline**: ogni pipeline e una riga orizzontale con il suo Kanban
  - Ogni riga mostra: nome pipeline, conteggio deal, valore totale + colonne Kanban con le card
  - Ogni tab specifico mostra il **Kanban classico full-width** con le colonne di quella pipeline

**AC-203.2 (Card deal arricchita)**: DATO che vedo una card deal nel Kanban, ALLORA:
  - La card mostra: nome deal, cliente/azienda, valore, tipo deal, **commerciale assegnato**, **giorni in questo stato**
  - Bottone "Apri" per andare al dettaglio

**AC-203.3 (Filtro commerciale — solo admin)**: DATO che sono admin/owner, ALLORA:
  - Vedo filtro commerciale sotto i tab: chip/bottoni con "Tutti", "Marco", "Pietro", "Sara"
  - Selezionando un commerciale, il Kanban filtra solo i suoi deal
  - Se sono commerciale, il filtro non appare (vedo solo i miei deal — row-level)

**AC-203.4 (Drag tra stati stessa pipeline)**: DATO che sposto un deal da "Qualifica" a "Match risorse" (stessa pipeline), ALLORA:
  - Il deal si sposta normalmente
  - Per cambiare pipeline, cambia il tipo di vendita sul deal

**SP**: 5 | **Priorita**: Must Have | **Epic**: Pipeline Templates | **Dipendenze**: US-200, US-201

---

## EPIC 18: Resource DB e Matching

### US-204: CRUD risorse interne

**Come** admin
**Voglio** gestire le risorse interne (consulenti, sviluppatori) con le loro competenze e disponibilita
**Per** sapere chi ho disponibile quando un cliente chiede un profilo

**AC-204.1 (Happy Path)**: DATO che vado in Risorse > Nuova risorsa, QUANDO compilo: nome, seniority (junior/mid/senior/lead), costo_giornaliero, disponibile_dal, ALLORA:
  - La risorsa viene salvata in `resources` con tenant_id
  - Appare nella lista risorse con badge seniority

**AC-204.2 (Skill)**: DATO che ho una risorsa "Marco Bianchi", QUANDO aggiungo skill: Java (livello 4/5), Spring (3/5), Angular (2/5), ALLORA:
  - Le skill vengono salvate in `resource_skills` con livello 1-5
  - Nel profilo risorsa vedo le skill con barre livello

**AC-204.3 (Disponibilita)**: DATO che la risorsa e assegnata a un progetto fino al 2026-06-30, QUANDO aggiorno `disponibile_dal` = 2026-07-01, ALLORA:
  - La risorsa non appare nei risultati di matching prima di quella data
  - Badge "Occupata fino al 30/06" nella lista

**AC-204.4 (Filtri)**: DATO che ho 20 risorse, QUANDO filtro per skill="Java" e seniority="senior", ALLORA:
  - Vedo solo risorse senior con Java nelle skill

**SP**: 5 | **Priorita**: Must Have | **Epic**: Resource DB | **Dipendenze**: Nessuna

---

### US-205: Matching richiesta-risorse

**Come** commerciale T&M
**Voglio** che l'agente mi dica quali risorse sono disponibili per la richiesta del cliente
**Per** rispondere velocemente al cliente senza cercare manualmente su Excel

**AC-205.1 (Happy Path)**: DATO che il deal T&M e in stato "Qualifica" e il cliente chiede un "Senior Java con Spring", QUANDO chiedo all'agente "chi abbiamo disponibile?", ALLORA:
  - L'agente chiama il tool `match_resources` con stack=["Java","Spring"], seniority="senior"
  - Restituisce top 5 profili con match_score (0-100): nome, seniority, skill match %, disponibilita, costo_giornaliero
  - "Ho trovato 3 profili senior Java: Marco (match 92%, disponibile subito), Luca (match 85%, dal 15/05)..."

**AC-205.2 (Zero match)**: DATO che cerco "Senior Golang" e non ho risorse Golang, ALLORA:
  - L'agente risponde: "Non ho risorse Golang disponibili. Vuoi che cerchi profili mid con skill simili, o segno che serve recruiting?"

**AC-205.3 (Match score)**: DATO che cerco "Senior Java Spring Angular", ALLORA:
  - Il match_score pesa: tech match (60%) + seniority match (25%) + disponibilita (15%)
  - Una risorsa Java+Spring senza Angular ha score piu basso di una Java+Spring+Angular

**AC-205.4 (Disponibilita futura)**: DATO che cerco risorse per un progetto che parte tra 2 mesi, ALLORA:
  - Il matching include risorse con disponibile_dal <= data_inizio_progetto
  - Risorse che si liberano prima hanno score piu alto

**SP**: 8 | **Priorita**: Must Have | **Epic**: Resource DB | **Dipendenze**: US-204

---

### US-206: Calcolo margine offerta T&M

**Come** commerciale T&M
**Voglio** che l'agente calcoli automaticamente il margine quando preparo un'offerta
**Per** sapere subito se l'offerta e sostenibile prima di inviarla

**AC-206.1 (Happy Path)**: DATO che preparo un'offerta con tariffa 600 EUR/gg per una risorsa che costa 400 EUR/gg, QUANDO chiedo "calcola il margine", ALLORA:
  - L'agente risponde: "Margine: 33% (600-400=200 EUR/gg). Sopra la soglia minima (15%). Offerta OK."

**AC-206.2 (Sotto soglia)**: DATO che la tariffa proposta e 450 EUR/gg e il costo e 400 EUR/gg (margine 11%), ALLORA:
  - L'agente avvisa: "Attenzione: margine 11%, sotto la soglia minima del 15%. Serve approvazione del manager. Vuoi procedere?"
  - Il deal viene flaggato "margine sotto soglia" nel DB

**AC-206.3 (Multi-risorsa)**: DATO che l'offerta include 2 risorse (Senior Java 600/gg costo 400, Mid Angular 400/gg costo 280), ALLORA:
  - Margine calcolato per risorsa e totale
  - "Margine totale: 32% (Senior 33%, Mid 30%). Offerta complessiva OK."

**AC-206.4 (Genera offerta)**: DATO che il margine e OK, QUANDO chiedo "genera l'offerta", ALLORA:
  - L'agente prepara bozza: tariffe per seniority/tech, durata stimata, condizioni
  - CV anonimi allegabili (nome risorsa non visibile al cliente)

**SP**: 5 | **Priorita**: Must Have | **Epic**: Resource DB | **Dipendenze**: US-205

---

### US-207: Bench tracking

**Come** manager/commerciale
**Voglio** sapere quali risorse si liberano nei prossimi 30 giorni
**Per** evitare bench (risorse ferme non fatturabili)

**AC-207.1 (Happy Path)**: DATO che 2 risorse hanno contratto in scadenza nei prossimi 30gg, QUANDO chiedo "chi si libera?", ALLORA:
  - L'agente lista le risorse: nome, skill, data fine contratto, giorni rimanenti

**AC-207.2 (Alert proattivo)**: DATO che una risorsa si libera tra 30 giorni, ALLORA:
  - L'agente segnala proattivamente: "Marco Bianchi (Senior Java) si libera il 15/05. Vuoi cercaregli un nuovo progetto?"

**AC-207.3 (Suggerimento)**: DATO che ho deal T&M in stato "Qualifica" che cercano Java Senior, ALLORA:
  - L'agente incrocia: "Marco si libera il 15/05 e matcherebbe con il deal ACME (Java Senior). Vuoi proporlo?"

**SP**: 3 | **Priorita**: Should Have | **Epic**: Resource DB | **Dipendenze**: US-205

---

## EPIC 19: Elevia Use Case Engine

### US-208: Catalogo use case Elevia

**Come** admin
**Voglio** gestire il catalogo dei 20+ use case Elevia con la mappatura per settore ATECO
**Per** permettere all'agente di suggerire i prodotti giusti per ogni prospect

**AC-208.1 (Happy Path)**: DATO che accedo a Impostazioni > Use Case Elevia, ALLORA:
  - Vedo lista dei use case: codice (UC01-UC15), nome, descrizione, settori target con fit score
  - Seed automatico con 15+ use case e matrice ATECO pre-compilata

**AC-208.2 (Matrice ATECO)**: DATO che seleziono UC02 (Knowledge Navigator), ALLORA:
  - Vedo fit score per settore: Metallurgia (24-25) = 90, Commercio (46) = 80, Chimica (20) = 85
  - Posso modificare i fit score

**AC-208.3 (CRUD)**: DATO che la mia azienda ha un use case custom "UC20: Chatbot HR", QUANDO lo creo, ALLORA:
  - Viene salvato con codice, nome, descrizione
  - Posso assegnare fit score per settore ATECO

**AC-208.4 (Bundle)**: DATO che configuro un bundle "Metallurgia Standard" = UC02+UC04+UC13+UC14, ALLORA:
  - Il bundle appare come suggerimento per prospect ATECO 24-25

**SP**: 5 | **Priorita**: Must Have | **Epic**: Elevia Engine | **Dipendenze**: Nessuna

---

### US-209: Score prospect Elevia

**Come** fractional account (Pietro)
**Voglio** che l'agente calcoli automaticamente il fit score di un prospect
**Per** sapere su chi concentrarmi e chi ha piu probabilita di chiudere

**AC-209.1 (Happy Path)**: DATO che creo un deal Elevia per "Fonderia Rossi SRL" (ATECO 25.11, 80 dipendenti, decision maker = CTO), QUANDO chiedo "quanto e in target?", ALLORA:
  - L'agente calcola fit score composito:
    - ATECO priority (30%): 25 = P1 → 100 punti
    - Dimensione (15%): 80 dip → 100 punti (sweet spot 50-200)
    - Use case applicabili (25%): 4 UC con score >50 → 80 punti
    - Engagement (20%): nuovo prospect → 20 punti
    - Decision maker (10%): CTO diretto → 100 punti
  - Score totale: ~76/100. "Prospect qualificato. 4 use case applicabili: UC02, UC04, UC13, UC14."

**AC-209.2 (Fuori target)**: DATO che il prospect e ATECO 56 (ristorazione), ALLORA:
  - Score basso: ATECO non target → 10 punti (peso 30%)
  - "Prospect fuori target primario. Score 28/100. Vuoi procedere comunque?"

**AC-209.3 (Suggerimento bundle)**: DATO che il prospect e Metallurgia, ALLORA:
  - L'agente suggerisce il bundle Metallurgia: UC02+UC04+UC13+UC14
  - "Per la metallurgia suggerisco: Knowledge Navigator, Report automatici, Classificazione email, Predizione guasti."

**AC-209.4 (Aggiornamento score)**: DATO che il prospect risponde ai messaggi LinkedIn (engagement alto), ALLORA:
  - Il warmth_score sale → il fit score composito si aggiorna dinamicamente

**SP**: 5 | **Priorita**: Must Have | **Epic**: Elevia Engine | **Dipendenze**: US-208

---

### US-210: ROI calculator Elevia

**Come** commerciale Elevia
**Voglio** che l'agente calcoli il ROI stimato per il prospect
**Per** inserire il dato nell'offerta e convincere il cliente

**AC-210.1 (Happy Path)**: DATO che il prospect ha 80 dipendenti e il bundle Metallurgia (4 UC), QUANDO chiedo "calcola ROI", ALLORA:
  - Stima ore risparmiate per UC: UC02 (10h/mese), UC04 (8h/mese), UC13 (5h/mese), UC14 (3h/mese)
  - Costo orario medio settore: 35 EUR/h
  - Risparmio annuo: (26h/mese * 35 EUR * 12) = 10.920 EUR
  - Costo Elevia bundle: ~6.000 EUR/anno
  - ROI: 82% → "ROI stimato 82%. Payback in 7 mesi."

**AC-210.2 (Personalizzabile)**: DATO che il prospect ha costo orario diverso, QUANDO modifico a 50 EUR/h, ALLORA:
  - ROI ricalcolato: 160%. "Con costo orario 50 EUR, ROI sale al 160%."

**SP**: 3 | **Priorita**: Should Have | **Epic**: Elevia Engine | **Dipendenze**: US-209

---

## EPIC 20: Agent Refactor

### US-211: Agent registry e dispatch

**Come** sistema
**Voglio** un registry di agenti con pattern plugin dove l'orchestratore smista all'agente giusto
**Per** poter aggiungere nuovi agenti (Order, Invoice, HR) senza modificare il codice esistente

**AC-211.1 (Registry)**: DATO che il sistema si avvia, ALLORA:
  - Il registry contiene 3 agenti: sales_agent, controller_agent, analytics_agent
  - Ogni agente ha: name, description, tool list, system prompt template

**AC-211.2 (Dispatch)**: DATO che l'utente scrive "prepara l'offerta per ACME", ALLORA:
  - L'orchestratore identifica intent = vendita → attiva sales_agent
  - Il sales_agent riceve il contesto: deal ACME, prodotto, pipeline, stato corrente

**AC-211.3 (Fallback)**: DATO che l'utente scrive qualcosa di ambiguo "come sta ACME?", ALLORA:
  - L'orchestratore chiede: "Vuoi info sul deal ACME o sulle fatture ACME?"
  - In base alla risposta, attiva sales_agent o controller_agent

**AC-211.4 (Plugin)**: DATO che aggiungo un nuovo agente "order_agent" al registry, ALLORA:
  - L'orchestratore lo vede automaticamente senza modifiche al router
  - Le keyword "ordine", "consegna", "tracking" attivano il nuovo agente

**SP**: 8 | **Priorita**: Must Have | **Epic**: Agent Refactor | **Dipendenze**: Nessuna

---

### US-212: Sales Agent con tool filtering per prodotto

**Come** commerciale
**Voglio** che l'agente sappia automaticamente quali tool usare in base al prodotto del deal
**Per** avere suggerimenti pertinenti senza confusione tra processi diversi

**AC-212.1 (T&M tools)**: DATO che il deal corrente ha prodotto T&M, QUANDO parlo con l'agente, ALLORA:
  - L'agente ha accesso a: 8 tool core + match_resources, calc_margin, generate_tm_offer, check_bench
  - NON ha accesso a: score_prospect, linkedin_message, warmth_score (tool Elevia)

**AC-212.2 (Elevia tools)**: DATO che il deal corrente ha prodotto Elevia, ALLORA:
  - L'agente ha accesso a: 8 tool core + score_prospect, suggest_bundle, linkedin_message, warmth_score, calc_roi, plan_onboarding, monitor_adoption, check_cadence, suggest_content, prefill_brief, prepare_demo
  - NON ha accesso a: match_resources, calc_margin (tool T&M)

**AC-212.3 (Nessun deal)**: DATO che non c'e un deal attivo nel contesto, ALLORA:
  - L'agente ha solo gli 8 tool core
  - Puo cercare deal, contatti, mostrare pipeline summary

**AC-212.4 (Cambio deal)**: DATO che passo dal deal T&M "ACME" al deal Elevia "Fonderia Rossi", ALLORA:
  - I tool disponibili cambiano automaticamente
  - Il prompt dell'agente si aggiorna con la nuova pipeline FSM

**SP**: 8 | **Priorita**: Must Have | **Epic**: Agent Refactor | **Dipendenze**: US-211

---

### US-213: Controller Agent (wrapper tool esistenti)

**Come** utente
**Voglio** che le funzionalita contabili continuino a funzionare esattamente come prima
**Per** zero regressione — il controller non cambia

**AC-213.1 (Invarianza)**: DATO che chiedo "quante fatture ho questo mese?", ALLORA:
  - Il controller_agent risponde esattamente come prima del refactor
  - Stessi 17 tool, stesse risposte, stessa formattazione

**AC-213.2 (Routing)**: DATO che chiedo "mostra il bilancio", ALLORA:
  - L'orchestratore attiva controller_agent (non sales_agent)
  - La risposta usa get_balance_sheet_summary come prima

**AC-213.3 (Multi-agent)**: DATO che chiedo "come sta l'azienda?", ALLORA:
  - L'orchestratore attiva sia controller_agent (KPI finanziari) sia analytics_agent (pipeline)
  - La risposta assembla entrambe le viste: "[controller] Fatturato YTD... [analytics] Pipeline..."

**AC-213.4 (Test regressione)**: DATO che eseguo tutti i 809+ test esistenti, ALLORA:
  - Tutti passano senza modifiche ai test

**SP**: 5 | **Priorita**: Must Have | **Epic**: Agent Refactor | **Dipendenze**: US-211

---

## EPIC 21: LinkedIn Social Selling

### US-214: Generazione messaggi LinkedIn

**Come** fractional account Elevia
**Voglio** che l'agente generi messaggi LinkedIn personalizzati per settore e fase della cadence
**Per** non scrivere 200 messaggi diversi a mano ogni mese

**AC-214.1 (Connection request)**: DATO che il prospect e Metallurgia ATECO 25 e non e connesso, QUANDO chiedo "scrivi connection request", ALLORA:
  - L'agente genera messaggio < 200 caratteri, personalizzato: menziona il settore, un trigger specifico (post recente, gruppo condiviso), no pitch
  - "Buongiorno [Nome], ho visto il suo intervento su [tema]. Lavoriamo con PMI metallurgiche su temi simili. Mi farebbe piacere connetterci."

**AC-214.2 (Follow-up)**: DATO che il prospect ha accettato la connessione 3 giorni fa, QUANDO chiedo "scrivi il primo messaggio", ALLORA:
  - Conversation starter, < 300 char, nessun pitch
  - "Grazie per la connessione! Ho notato che [azienda] opera nel [settore]. Come state gestendo [pain point comune del settore]?"

**AC-214.3 (Soft ask)**: DATO che il warmth score > 60, QUANDO chiedo "proponi la call", ALLORA:
  - Messaggio con soft ask per call 10 min, include link Calendly se configurato
  - "Mi piacerebbe capire meglio le vostre esigenze. Ha 10 minuti questa settimana per una chiacchierata? [link Calendly]"

**AC-214.4 (Mai pitch al primo contatto)**: DATO che il prospect e appena connesso (warmth < 30), QUANDO chiedo "scrivi offerta", ALLORA:
  - L'agente rifiuta: "E presto per un'offerta. Suggerisco prima un messaggio di valore. Vuoi che prepari un contenuto da condividere?"

**SP**: 5 | **Priorita**: Must Have | **Epic**: LinkedIn Selling | **Dipendenze**: US-209

---

### US-215: Warmth score e cadence tracking

**Come** fractional account
**Voglio** sapere quanto e "caldo" ogni prospect e cosa fare dopo nella cadence
**Per** concentrarmi sui prospect pronti e non perdere il timing

**AC-215.1 (Warmth score)**: DATO che il prospect ha: connessione accettata (+20), risposto a 1 DM (+30), likato 2 post (+30), ALLORA:
  - Warmth score = 80/100
  - L'agente segnala: "Prospect caldo (80). Suggerisco di proporre la discovery call."

**AC-215.2 (Cadence check)**: DATO che chiedo "dove sono con questo prospect?", ALLORA:
  - L'agente mostra: "Giorno 7 della cadence. Hai fatto: view profilo, connection request (accettata), primo messaggio. Prossimo step: condividi un case study metallurgico."

**AC-215.3 (Alert stallo)**: DATO che non c'e interazione da 10+ giorni, ALLORA:
  - L'agente suggerisce: "Prospect fermo da 12 giorni. Suggerisco: passa a nurturing passivo o prova un contenuto diverso."

**AC-215.4 (Ready for call)**: DATO che warmth > 60, ALLORA:
  - Badge "Pronto per call" visibile nel deal
  - L'agente suggerisce proattivamente la call

**SP**: 5 | **Priorita**: Must Have | **Epic**: LinkedIn Selling | **Dipendenze**: US-214

---

### US-216: Import CSV LinkedIn

**Come** fractional account
**Voglio** importare la lista prospect da LinkedIn Sales Navigator (export CSV)
**Per** caricare in bulk i 200 prospect mensili senza inserirli uno a uno

**AC-216.1 (Happy Path)**: DATO che ho un CSV da Sales Navigator con: nome, cognome, azienda, ruolo, settore, QUANDO lo carico, ALLORA:
  - Il sistema crea CrmCompany (se non esiste) + CrmContact per ogni riga
  - Il deal Elevia viene creato con stato "Prospect" per ogni contatto
  - Report: "Importati 187 prospect. 13 duplicati ignorati."

**AC-216.2 (Dedup)**: DATO che il prospect "Mario Rossi di ACME" esiste gia, ALLORA:
  - Non viene creato un duplicato
  - Il contatto esistente viene aggiornato se ci sono dati nuovi

**AC-216.3 (ATECO enrichment)**: DATO che il CSV ha il settore ma non il codice ATECO, ALLORA:
  - Il sistema tenta di mappare il settore a un codice ATECO
  - Se non riesce, lascia ATECO vuoto e chiede conferma

**AC-216.4 (Errori)**: DATO che il CSV ha righe con dati mancanti (no azienda), ALLORA:
  - Le righe invalide vengono skippate
  - Report: "12 righe ignorate per dati mancanti"

**SP**: 5 | **Priorita**: Should Have | **Epic**: LinkedIn Selling | **Dipendenze**: US-209

---

## EPIC 22: Cross-sell Engine

### US-217: Rilevamento segnali cross-sell

**Come** sistema
**Voglio** analizzare note e attivita dei deal per rilevare segnali di cross-sell tra pipeline
**Per** suggerire prodotti complementari ai commerciali

**AC-217.1 (T&M → Elevia)**: DATO che un deal T&M ha nota "il cliente ha problemi di documentazione tecnica dispersa", ALLORA:
  - Il sistema rileva keyword: "documentazione" → segnale Elevia (UC02 Knowledge Navigator)
  - Crea CrossSellSignal: deal_source, signal_type="documentation_pain", priority="high", suggested_product="Elevia UC02"

**AC-217.2 (Elevia → T&M)**: DATO che un deal Elevia ha nota "il prospect chiede anche sviluppo custom del chatbot", ALLORA:
  - Keyword: "sviluppo custom" → segnale T&M
  - Crea CrossSellSignal con target pipeline T&M

**AC-217.3 (Notifica)**: DATO che viene creato un segnale cross-sell, ALLORA:
  - Il commerciale assegnato al deal riceve suggerimento: "Segnale cross-sell: ACME (deal T&M) potrebbe essere interessata a Elevia UC02. Vuoi creare un deal Elevia?"

**AC-217.4 (Keyword configurabili)**: DATO che l'admin va in Impostazioni > Cross-sell, ALLORA:
  - Puo configurare le keyword trigger per ogni direzione (T&M→Elevia, Elevia→T&M)
  - Default pre-caricati: documentazione, processi, knowledge base → Elevia; sviluppo, integrazione, custom → T&M

**SP**: 5 | **Priorita**: Must Have | **Epic**: Cross-sell | **Dipendenze**: US-211

---

### US-218: Report cross-sell

**Come** manager
**Voglio** vedere un report dei segnali cross-sell rilevati, convertiti e valore generato
**Per** misurare l'efficacia della strategia dual-pipeline

**AC-218.1 (Happy Path)**: DATO che ci sono 10 segnali cross-sell questo mese, ALLORA:
  - Report mostra: segnali totali, convertiti (deal creato), valore deal convertiti
  - Breakdown per direzione: 6 T&M→Elevia, 4 Elevia→T&M

**AC-218.2 (Filtri)**: DATO che filtro per periodo e direzione, ALLORA:
  - Il report si aggiorna
  - Posso esportare in CSV

**SP**: 3 | **Priorita**: Should Have | **Epic**: Cross-sell | **Dipendenze**: US-217

---

## EPIC 18b: Tool Corpo (Progetti a prezzo fisso)

### US-219: Analisi requisiti e specifiche progetto a corpo

**Come** commerciale che vende un progetto a corpo
**Voglio** che l'agente mi aiuti a raccogliere requisiti e generare il documento di specifiche
**Per** arrivare all'offerta con un perimetro chiaro senza dimenticare nulla

**AC-219.1 (Prefill specs)**: DATO che il deal Corpo e in stato "Analisi requisiti" e ho fatto una call con il cliente, QUANDO dico all'agente "ho fatto la call, ecco gli appunti: [note]", ALLORA:
  - L'agente chiama `prefill_specs` e pre-compila la scheda specifiche: scope, deliverable previsti, tecnologie, team necessario, vincoli, milestone suggerite
  - "Ho preparato la scheda specifiche da questi appunti. Scope: [x]. Deliverable: [y]. Ti manca ancora: timeline e budget stimato."

**AC-219.2 (Stima effort)**: DATO che le specifiche sono compilate (scope + deliverable + tech), QUANDO chiedo "stima l'effort", ALLORA:
  - L'agente chiama `estimate_effort` e calcola: giornate per profilo (senior, mid, junior), durata stimata, costo interno
  - "Stima: 45gg Senior Java + 30gg Mid Angular = 75gg totali. Costo interno: ~30.000 EUR. Durata: ~4 mesi."

**AC-219.3 (Genera offerta corpo)**: DATO che ho effort e specifiche, QUANDO chiedo "genera l'offerta", ALLORA:
  - L'agente chiama `generate_fixed_offer`: scope, milestone, prezzo totale (costo + margine), condizioni di pagamento (30/30/30/10 standard)
  - "Offerta generata: 45.000 EUR (margine 33%). Pagamento: 30% anticipo, 30% SAL1, 30% SAL2, 10% collaudo."

**AC-219.4 (Specifiche incomplete)**: DATO che chiedo l'offerta senza aver definito le specifiche, ALLORA:
  - L'agente avvisa: "Per un progetto a corpo servono specifiche chiare. Ti mancano: [scope, deliverable, timeline]. Vuoi che ti aiuti a raccoglierle?"

**SP**: 8 | **Priorita**: Must Have | **Epic**: 18b | **Dipendenze**: US-212

---

## EPIC 19b: Tool Elevia Avanzati (Discovery, Demo, Onboarding)

### US-220: Discovery brief e preparazione demo Elevia

**Come** fractional account Elevia
**Voglio** che l'agente pre-compili il brief per la discovery call e prepari la configurazione demo
**Per** arrivare preparato alla call e alla demo senza partire da zero

**AC-220.1 (Prefill brief)**: DATO che il deal Elevia e in stato "Discovery Call" e il prospect e ATECO 25 (Metallurgia, 80 dip), QUANDO chiedo "prepara il brief", ALLORA:
  - L'agente chiama `prefill_discovery_brief`: pain point probabili per metallurgia (know-how disperso, report manuali, documentazione tecnica non trovabile), use case candidati (UC02, UC04, UC13, UC14), domande discovery personalizzate
  - "Brief preparato per Fonderia Rossi. Pain point probabili: [lista]. Use case da esplorare: [lista]. Domande suggerite: [lista]."

**AC-220.2 (Prepare demo)**: DATO che la discovery e fatta e sono emersi UC02 e UC04, QUANDO chiedo "prepara la demo", ALLORA:
  - L'agente chiama `prepare_demo`: seleziona use case da mostrare, suggerisce dati esempio per il settore, genera scaletta presentazione
  - "Demo configurata: 1. Knowledge Navigator con documenti tecnici metallurgici (15 min). 2. Report automatici produzione (10 min). Materiale settoriale allegato."

**AC-220.3 (No discovery = no demo)**: DATO che salto la discovery e chiedo la demo, ALLORA:
  - L'agente avvisa: "Non ho info sui pain point del prospect. Vuoi fare una demo standard per metallurgia o preferisci prima una call esplorativa?"

**AC-220.4 (Demo opzionale)**: DATO che il prospect dice "non serve la demo, mandami direttamente l'offerta", ALLORA:
  - Il commerciale salta lo stato Demo (is_optional=true)
  - L'agente non insiste: "OK, passo direttamente alla preparazione dell'offerta."

**SP**: 5 | **Priorita**: Must Have | **Epic**: 19b | **Dipendenze**: US-209

---

### US-221: Onboarding e monitoraggio adozione Elevia

**Come** account manager Elevia
**Voglio** che l'agente generi il piano onboarding e monitori l'adozione post-vendita
**Per** assicurare che il cliente usi davvero il prodotto e non faccia churn

**AC-221.1 (Plan onboarding)**: DATO che il deal Elevia passa a "Won" con bundle Metallurgia (UC02+UC04), QUANDO chiedo "pianifica l'onboarding", ALLORA:
  - L'agente chiama `plan_onboarding`: timeline setup (settimana 1: config, settimana 2: training UC02, settimana 3: training UC04, settimana 4: go-live)
  - KPI target: login 3x/settimana, usage UC02 5x/settimana entro 30gg
  - "Piano onboarding generato. Training in 3 settimane, go-live settimana 4. KPI: 3 login/settimana."

**AC-221.2 (Monitor adoption)**: DATO che il cliente e in stato "Onboarding" da 30 giorni, QUANDO chiedo "come sta andando l'adozione?", ALLORA:
  - L'agente chiama `monitor_adoption`: login frequency, feature usage per UC, trend
  - "Adozione: UC02 usato 4x/settimana (target 5x). UC04 usato 1x/settimana (sotto target). Suggerisco re-training su UC04."

**AC-221.3 (Churn alert)**: DATO che l'usage scende del 50% rispetto al mese precedente, ALLORA:
  - L'agente segnala proattivamente: "Attenzione: usage Fonderia Rossi calato del 50%. Rischio churn. Vuoi programmare un check-in?"

**AC-221.4 (Check-in 30/60/90)**: DATO che sono passati 30 giorni dal go-live, ALLORA:
  - L'agente suggerisce: "Check-in 30 giorni per Fonderia Rossi. Vuoi che prepari un riepilogo adozione e suggerimenti?"

**SP**: 5 | **Priorita**: Must Have | **Epic**: 19b | **Dipendenze**: US-209

---

## Riepilogo

| Story | Titolo | SP | Epic | Priorita |
|-------|--------|:--:|------|----------|
| US-200 | Pipeline template da DB | 5 | 17 | Must |
| US-201 | Prodotto determina pipeline | 5 | 17 | Must |
| US-202 | Admin personalizza template | 5 | 17 | Should |
| US-203 | Kanban multi-pipeline | 5 | 17 | Must |
| US-204 | CRUD risorse interne | 5 | 18 | Must |
| US-205 | Matching richiesta-risorse | 8 | 18 | Must |
| US-206 | Calcolo margine offerta | 5 | 18 | Must |
| US-207 | Bench tracking | 3 | 18 | Should |
| US-208 | Catalogo use case Elevia | 5 | 19 | Must |
| US-209 | Score prospect Elevia | 5 | 19 | Must |
| US-210 | ROI calculator | 3 | 19 | Should |
| US-211 | Agent registry e dispatch | 8 | 20 | Must |
| US-212 | Sales Agent tool filtering | 8 | 20 | Must |
| US-213 | Controller Agent (zero regressione) | 5 | 20 | Must |
| US-214 | Messaggi LinkedIn | 5 | 21 | Must |
| US-215 | Warmth score + cadence | 5 | 21 | Must |
| US-216 | Import CSV LinkedIn | 5 | 21 | Should |
| US-217 | Segnali cross-sell | 5 | 22 | Must |
| US-218 | Report cross-sell | 3 | 22 | Should |
| **US-219** | **Specifiche + effort + offerta Corpo** | **8** | **18b** | **Must** |
| **US-220** | **Discovery brief + demo Elevia** | **5** | **19b** | **Must** |
| **US-221** | **Onboarding + adozione Elevia** | **5** | **19b** | **Must** |
| **TOTALE Pivot 9** | | **116 SP** | | **16 Must, 6 Should** |

---

# Pivot 10 — Portal Integration (ADR-011)

**AgentFlow PMI — Integrazione PortalJS.be per gestione operativa**

---

## Overview

Il Pivot 10 integra AgentFlow con PortalJS.be (sistema gestionale operativo: commesse, rapportini, dipendenti). Portal diventa **master anagrafico** per Aziende/Clienti. AgentFlow resta **master commerciale** (deal, referenti, pipeline).

**Principio guida:** Portal gestisce l'operativo (commesse, dipendenti, timesheet). AgentFlow gestisce il commerciale (deal, referenti, pipeline). Il ponte tra i due e il `portal_customer_id` su CrmContact e CrmDeal. Ogni scrittura su Portal richiede conferma umana.

**Connessione:** JWT auto-generato con JWTSECRET condiviso tra i due sistemi, nessun login/password.

**Staging API:** `https://portaaljsbe-staging.up.railway.app/api/v1`

**DB staging (copia produzione):** 2149 persone, 315 commesse, 66 clienti, 365 attivita, 1543 timesheet, 214 contratti.

**Tenant mapping:** AgentFlow tenant "Nexa Data" <-> Portal tenant "NEXA"

**Formato AC:** DATO-QUANDO-ALLORA, 4+ AC per story.

---

## EPIC 23: Portal Client & Read

### US-230: Portal Client adapter (auth JWT + lettura customer/person/project)

**Come** sistema
**Voglio** un adapter async per PortalJS.be che si autentica via JWT auto-generato e legge Customer, Person, Project
**Per** avere un punto unico di integrazione con Portal, disaccoppiato dal resto dell'applicazione

**AC-230.1 (Happy Path — JWT)**: DATO che PORTAL_API_URL e PORTAL_JWT_SECRET sono configurati, QUANDO il PortalClient si inizializza, ALLORA:
  - Genera un JWT firmato con PORTAL_JWT_SECRET (HS256) contenente tenant="NEXA" e exp=5min
  - Non serve login/password — il JWT e autosufficiente
  - Il JWT viene rigenerato automaticamente prima della scadenza

**AC-230.2 (Read Customers)**: DATO che il PortalClient e autenticato, QUANDO chiamo `get_customers()`, ALLORA:
  - Ritorna la lista dei clienti Portal (66 in staging) con: id, name, vatNumber, fiscalCode, address, city
  - Supporta paginazione e filtro per nome/P.IVA

**AC-230.3 (Read Persons)**: DATO che il PortalClient e autenticato, QUANDO chiamo `get_persons()`, ALLORA:
  - Ritorna la lista delle persone Portal (2149 in staging) con: id, firstName, lastName, fiscalCode, email
  - Supporta paginazione e filtro per nome

**AC-230.4 (Errore connessione)**: DATO che PORTAL_API_URL punta a un server non raggiungibile, QUANDO chiamo qualsiasi metodo, ALLORA:
  - Ritorna un errore chiaro: "Portal non raggiungibile: {url}"
  - Non blocca il funzionamento di AgentFlow (graceful degradation)

**AC-230.5 (JWT Secret mancante)**: DATO che PORTAL_JWT_SECRET non e configurato, QUANDO il sistema si avvia, ALLORA:
  - Il PortalClient si inizializza in modalita "disabled"
  - Le chiamate a Portal ritornano empty result con warning nel log

**SP**: 5 | **Priorita**: Must Have | **Epic**: Portal Client & Read | **Dipendenze**: Nessuna

---

### US-231: Aziende da Portal (dropdown Customer nel deal, sostituisce CrmCompany)

**Come** commerciale
**Voglio** che le aziende/clienti nel CRM vengano lette direttamente da Portal Customer invece che dalla tabella CrmCompany locale
**Per** avere un'unica fonte dati anagrafica (Portal) ed evitare duplicati e disallineamenti

**AC-231.1 (Happy Path)**: DATO che Portal ha 66 clienti, QUANDO apro il form "Nuovo Deal" e clicco sul dropdown azienda, ALLORA:
  - Il dropdown mostra i clienti da Portal (non da CrmCompany locale)
  - Ogni cliente mostra: nome, P.IVA, citta
  - La ricerca e filtrata lato server (typeahead con debounce 300ms)

**AC-231.2 (CrmContact legato a portal_customer_id)**: DATO che seleziono il cliente Portal "ACME SRL" (id=42), QUANDO creo un referente per quel deal, ALLORA:
  - Il CrmContact viene creato con `portal_customer_id=42` (invece di `company_id` FK locale)
  - Il referente resta in AgentFlow (tabella CrmContact) ma punta al cliente Portal

**AC-231.3 (CrmCompany deprecato)**: DATO che il sistema e aggiornato a Pivot 10, ALLORA:
  - La tabella CrmCompany resta in DB ma non viene piu usata per nuovi deal
  - I deal esistenti mantengono il company_id FK locale per retrocompatibilita
  - I nuovi deal usano `portal_customer_id` al posto di `company_id`

**AC-231.4 (Portal non disponibile)**: DATO che Portal e offline, QUANDO apro il form Nuovo Deal, ALLORA:
  - Il dropdown mostra un messaggio "Portal non raggiungibile — usa il campo testo libero"
  - L'utente puo digitare il nome azienda manualmente (sara matchato in seguito)

**SP**: 5 | **Priorita**: Must Have | **Epic**: Portal Client & Read | **Dipendenze**: US-230

---

### US-232: Lettura persone e contratti da Portal (per resource matching)

**Come** commerciale
**Voglio** vedere i collaboratori disponibili da Portal con i loro contratti di lavoro
**Per** sapere chi e disponibile quando devo proporre risorse per un deal T&M

**AC-232.1 (Happy Path)**: DATO che Portal ha 2149 persone e 214 contratti, QUANDO cerco "sviluppatori Java disponibili", ALLORA:
  - Il sistema legge le persone da Portal con relativi contratti (tipo, inizio, fine, ore settimanali)
  - Mostra solo le persone con contratto attivo

**AC-232.2 (Filtro per competenze)**: DATO che Portal Person ha campi skill/ruolo, QUANDO filtro per "backend developer", ALLORA:
  - La lista mostra solo le persone con ruolo/skill corrispondente
  - Include: nome, ruolo, tipo contratto, scadenza contratto

**AC-232.3 (Contratto in scadenza)**: DATO che un collaboratore ha contratto in scadenza entro 30gg, ALLORA:
  - Il sistema lo evidenzia con badge "In scadenza"
  - L'informazione e utile per il bench tracking

**AC-232.4 (Paginazione)**: DATO che ci sono 2149 persone, QUANDO carico la pagina, ALLORA:
  - I risultati sono paginati (50 per pagina)
  - Il filtro ricerca e server-side per performance

**SP**: 3 | **Priorita**: Must Have | **Epic**: Portal Client & Read | **Dipendenze**: US-230

---

### US-233: Proxy endpoint /portal/*

**Come** frontend
**Voglio** accedere ai dati Portal tramite endpoint proxy `/api/v1/portal/*` del backend AgentFlow
**Per** non esporre le credenziali Portal al browser e centralizzare l'autenticazione

**AC-233.1 (Happy Path)**: DATO che il backend ha il PortalClient configurato, QUANDO il frontend chiama `GET /api/v1/portal/customers`, ALLORA:
  - Il backend fa la richiesta a Portal con JWT auto-generato
  - Ritorna i dati al frontend in formato AgentFlow (schema normalizzato)
  - Il frontend non conosce l'URL di Portal ne il JWT

**AC-233.2 (Endpoint disponibili)**: DATO che il proxy e attivo, ALLORA i seguenti endpoint sono disponibili:
  - `GET /api/v1/portal/customers` — lista clienti
  - `GET /api/v1/portal/customers/{id}` — dettaglio cliente
  - `GET /api/v1/portal/persons` — lista persone
  - `GET /api/v1/portal/persons/{id}` — dettaglio persona
  - `GET /api/v1/portal/projects` — lista commesse
  - `GET /api/v1/portal/projects/{id}` — dettaglio commessa
  - `GET /api/v1/portal/timesheets` — timesheet per commessa

**AC-233.3 (Autorizzazione)**: DATO che l'utente corrente e un commerciale, QUANDO chiama `/portal/customers`, ALLORA:
  - L'accesso e consentito (il proxy rispetta i ruoli AgentFlow)
  - Solo admin e commerciale possono accedere ai dati Portal

**AC-233.4 (Rate limiting)**: DATO che il frontend fa molte richieste, ALLORA:
  - Il proxy implementa cache in-memory (TTL 5 min) per le letture
  - Evita di sovraccaricare Portal con richieste ripetute

**SP**: 3 | **Priorita**: Must Have | **Epic**: Portal Client & Read | **Dipendenze**: US-230

---

## EPIC 24: Create Commessa su Portal

### US-234: Crea Commessa (Project) da Deal Won (con conferma umana)

**Come** commerciale
**Voglio** che quando un deal viene marcato come Won, il sistema proponga di creare una commessa su Portal
**Per** evitare di dover inserire manualmente i dati della commessa nel gestionale operativo

**AC-234.1 (Happy Path)**: DATO che il deal "Consulenza Java Senior" passa allo stato Won, QUANDO confermo la vittoria, ALLORA:
  - Il sistema mostra un dialog: "Vuoi creare la commessa su Portal?"
  - Precompila i campi: nome commessa (= deal name), cliente Portal (da portal_customer_id), valore, date
  - L'utente puo modificare i campi prima di confermare

**AC-234.2 (Conferma umana obbligatoria)**: DATO che il dialog e aperto, QUANDO clicco "Crea Commessa", ALLORA:
  - Il sistema chiama Portal `POST /projects` con i dati confermati
  - Il deal viene aggiornato con `portal_project_id` = ID della commessa creata
  - Un toast conferma: "Commessa creata su Portal: {nome}"

**AC-234.3 (Annulla)**: DATO che il dialog e aperto, QUANDO clicco "Non ora", ALLORA:
  - Il deal resta Won ma senza commessa Portal
  - Nella deal detail appare un bottone "Crea Commessa su Portal" per farlo in seguito

**AC-234.4 (Errore Portal)**: DATO che Portal e offline, QUANDO provo a creare la commessa, ALLORA:
  - Il sistema mostra: "Portal non raggiungibile. La commessa potra essere creata in seguito."
  - Il deal resta Won, il bottone "Crea Commessa" resta visibile

**SP**: 5 | **Priorita**: Must Have | **Epic**: Create Commessa | **Dipendenze**: US-230, US-231

---

### US-235: Customer matching (AgentFlow deal -> Portal customer by P.IVA)

**Come** sistema
**Voglio** trovare automaticamente il cliente Portal corrispondente al deal AgentFlow usando la P.IVA
**Per** collegare i deal ai clienti Portal senza intervento manuale

**AC-235.1 (Happy Path — match P.IVA)**: DATO che il deal ha un'azienda con P.IVA "IT12345678901" e Portal ha un Customer con vatNumber "IT12345678901", QUANDO il sistema cerca il match, ALLORA:
  - Trova il Customer Portal corrispondente
  - Propone il match all'utente: "Azienda ACME SRL matchata con cliente Portal ACME SRL (P.IVA: IT12345678901)"

**AC-235.2 (Match multiplo)**: DATO che 2 Customer Portal hanno la stessa P.IVA (dato sporco), QUANDO cerco il match, ALLORA:
  - Il sistema mostra entrambi i risultati
  - L'utente sceglie manualmente quale associare

**AC-235.3 (Nessun match)**: DATO che la P.IVA del deal non esiste su Portal, QUANDO cerco il match, ALLORA:
  - Il sistema mostra: "Nessun cliente Portal trovato con P.IVA {piva}. Vuoi crearlo su Portal?"
  - Se confermato, crea il Customer su Portal e associa

**AC-235.4 (Match automatico su deal creation)**: DATO che creo un nuovo deal e seleziono un cliente Portal dal dropdown (US-231), ALLORA:
  - Il portal_customer_id e gia impostato (nessun matching necessario)
  - Il matching serve solo per deal legacy senza portal_customer_id

**SP**: 5 | **Priorita**: Must Have | **Epic**: Create Commessa | **Dipendenze**: US-230, US-231

---

### US-236: Deal detail — bottone "Crea Commessa su Portal"

**Come** commerciale
**Voglio** un bottone nella pagina dettaglio deal per creare la commessa su Portal in qualsiasi momento
**Per** poter creare la commessa anche se non l'ho fatto al momento del Won

**AC-236.1 (Happy Path)**: DATO che il deal e in stato Won e non ha portal_project_id, QUANDO apro il deal detail, ALLORA:
  - Vedo un bottone "Crea Commessa su Portal" nella sezione azioni
  - Il bottone e visibile solo se il deal e Won e non ha gia una commessa Portal

**AC-236.2 (Commessa gia creata)**: DATO che il deal ha portal_project_id, QUANDO apro il deal detail, ALLORA:
  - Invece del bottone, vedo un link "Vedi Commessa su Portal" che apre il dettaglio
  - Mostra: nome commessa, stato, valore, ore registrate

**AC-236.3 (Form pre-compilato)**: DATO che clicco "Crea Commessa", ALLORA:
  - Si apre un dialog con campi precompilati dal deal (nome, cliente, valore, date stimate)
  - Posso modificare i campi prima di confermare
  - Il cliente Portal e gia selezionato (da portal_customer_id del deal)

**AC-236.4 (Permessi)**: DATO che sono un commerciale base (non admin), QUANDO vedo il deal Won, ALLORA:
  - Il bottone "Crea Commessa" e visibile solo se ho il permesso "portal:write"
  - Commerciale senza permesso vede solo "Richiedi creazione commessa" (notifica admin)

**SP**: 4 | **Priorita**: Must Have | **Epic**: Create Commessa | **Dipendenze**: US-234

---

## EPIC 25: Assign Collaborators

### US-237: Crea Activity/Assignment su Portal (con conferma)

**Come** project manager
**Voglio** assegnare collaboratori a una commessa Portal direttamente da AgentFlow
**Per** gestire le assegnazioni dal CRM senza entrare nel gestionale operativo

**AC-237.1 (Happy Path)**: DATO che il deal ha una commessa Portal (portal_project_id), QUANDO clicco "Assegna Collaboratore", ALLORA:
  - Vedo un dropdown con le persone Portal filtrate per competenza/disponibilita
  - Seleziono la persona, specifico: ruolo, ore settimanali, data inizio, data fine
  - Il sistema chiede conferma: "Assegnare Mario Rossi alla commessa XYZ?"

**AC-237.2 (Conferma e creazione)**: DATO che confermo l'assegnazione, ALLORA:
  - Il sistema chiama Portal `POST /activities` con: person_id, project_id, role, weekly_hours, start_date, end_date
  - Un toast conferma: "Mario Rossi assegnato alla commessa XYZ"
  - La sezione "Risorse assegnate" si aggiorna

**AC-237.3 (Persona gia assegnata)**: DATO che Mario Rossi e gia assegnato alla commessa XYZ, QUANDO provo ad assegnarlo di nuovo, ALLORA:
  - Il sistema mostra: "Mario Rossi e gia assegnato a questa commessa. Vuoi modificare l'assegnazione?"

**AC-237.4 (Nessuna commessa Portal)**: DATO che il deal non ha portal_project_id, QUANDO clicco "Assegna Collaboratore", ALLORA:
  - Il sistema mostra: "Prima crea la commessa su Portal (bottone sopra)"

**SP**: 5 | **Priorita**: Must Have | **Epic**: Assign Collaborators | **Dipendenze**: US-234, US-232

---

### US-238: Deal detail — sezione "Risorse assegnate da Portal"

**Come** commerciale
**Voglio** vedere le risorse assegnate alla commessa Portal direttamente nella pagina dettaglio deal
**Per** avere una vista completa del deal (commerciale + operativo) in un unico posto

**AC-238.1 (Happy Path)**: DATO che il deal ha portal_project_id e 3 persone assegnate, QUANDO apro il deal detail, ALLORA:
  - Vedo la sezione "Risorse Assegnate" con: nome, ruolo, ore/settimana, periodo, stato
  - I dati vengono letti da Portal `GET /activities?project_id={portal_project_id}`

**AC-238.2 (Nessuna risorsa)**: DATO che la commessa Portal esiste ma non ha assegnazioni, ALLORA:
  - La sezione mostra: "Nessuna risorsa assegnata. Usa il bottone 'Assegna Collaboratore'."

**AC-238.3 (Aggiornamento real-time)**: DATO che un PM assegna una risorsa direttamente su Portal, QUANDO ricarico il deal detail, ALLORA:
  - La sezione si aggiorna con la nuova risorsa (lettura da Portal, non cache locale)

**AC-238.4 (Nessuna commessa)**: DATO che il deal non ha portal_project_id, ALLORA:
  - La sezione non viene mostrata (appare solo dopo la creazione della commessa)

**SP**: 6 | **Priorita**: Must Have | **Epic**: Assign Collaborators | **Dipendenze**: US-237

---

## EPIC 26: Sync Timesheets & Dashboard

### US-239: Timesheet sync job + margine reale

**Come** manager
**Voglio** che i rapportini (timesheet) da Portal vengano sincronizzati periodicamente per calcolare il margine reale della commessa
**Per** confrontare il costo effettivo con il budget e intervenire prima che il margine si eroda

**AC-239.1 (Happy Path)**: DATO che la commessa Portal ha 50 timesheet finalizzati, QUANDO il sync job viene eseguito, ALLORA:
  - I timesheet vengono letti da Portal `GET /timesheets?project_id={id}&status=finalized`
  - Per ogni timesheet: persona, ore, data, descrizione
  - Il costo viene calcolato: ore x costo_orario (da contratto Portal)
  - Il margine reale = valore_deal - somma_costi_timesheet

**AC-239.2 (Sync periodico)**: DATO che il sync job e configurato, ALLORA:
  - Viene eseguito ogni 6 ore (configurabile in PortalConfig)
  - Sincronizza solo i timesheet nuovi/modificati (delta sync basato su updated_at)

**AC-239.3 (Alert margine basso)**: DATO che il margine reale scende sotto il 15%, ALLORA:
  - Il sistema genera un alert: "Commessa XYZ: margine reale 12% (sotto soglia 15%). Ore registrate: 120, Costo: 18.000 EUR, Valore deal: 20.000 EUR"

**AC-239.4 (Nessun timesheet)**: DATO che la commessa non ha ancora timesheet, ALLORA:
  - Il margine reale mostra "N/D — nessun rapportino registrato"
  - Il margine stimato (da calcolo offerta) resta visibile

**SP**: 5 | **Priorita**: Must Have | **Epic**: Sync Timesheets | **Dipendenze**: US-234

---

### US-240: Deal detail — "Avanzamento Operativo" (ore fatte vs pianificate)

**Come** commerciale/manager
**Voglio** vedere l'avanzamento operativo della commessa (ore fatte vs pianificate, margine reale, % completamento)
**Per** avere una vista istantanea dello stato della commessa senza entrare in Portal

**AC-240.1 (Happy Path)**: DATO che il deal ha una commessa Portal con timesheet sincronizzati, QUANDO apro il deal detail, ALLORA:
  - Vedo la sezione "Avanzamento Operativo" con:
    - Barra progresso: ore fatte / ore pianificate (es. 80/120 = 67%)
    - Costo effettivo vs budget
    - Margine reale (EUR e %) con colore verde/giallo/rosso
    - Trend: margine proiettato a fine commessa

**AC-240.2 (Margine rosso)**: DATO che il margine reale e sotto 15%, ALLORA:
  - La barra margine e rossa
  - Appare un warning: "Margine in erosione. Azione consigliata: rinegoziare scope o tariffe."

**AC-240.3 (Commessa completata)**: DATO che le ore fatte superano le ore pianificate, ALLORA:
  - La barra progresso mostra 120% in rosso
  - Il margine reale riflette lo sforamento

**AC-240.4 (Nessun dato operativo)**: DATO che il deal non ha commessa Portal o non ci sono timesheet, ALLORA:
  - La sezione mostra placeholder: "Dati operativi non disponibili. Crea la commessa su Portal per abilitare il tracking."

**SP**: 3 | **Priorita**: Must Have | **Epic**: Sync Timesheets | **Dipendenze**: US-239

---

### US-241: PortalConfig — pagina admin configurazione Portal

**Come** admin
**Voglio** una pagina nelle impostazioni per configurare la connessione a Portal
**Per** gestire URL, credenziali e mapping tenant senza modificare variabili d'ambiente

**AC-241.1 (Happy Path)**: DATO che sono admin e vado in Impostazioni > Portal, ALLORA:
  - Vedo un form con: Portal API URL, JWT Secret (masked), Portal Tenant Code
  - Vedo lo stato connessione: "Connesso" (verde) o "Non raggiungibile" (rosso)
  - Bottone "Test Connessione" che chiama Portal e mostra il risultato

**AC-241.2 (Statistiche Portal)**: DATO che la connessione e attiva, ALLORA:
  - Vedo le statistiche: N clienti, N persone, N commesse, N timesheet
  - Ultimo sync: data/ora
  - Prossimo sync: data/ora stimata

**AC-241.3 (Mapping)**: DATO che configuro il mapping, ALLORA:
  - Posso associare il tenant AgentFlow al tenant Portal (es. "Nexa Data" -> "NEXA")
  - Il mapping e salvato in DB (tabella PortalConfig)

**AC-241.4 (Solo admin)**: DATO che sono un commerciale (non admin), QUANDO provo ad accedere alla pagina Portal, ALLORA:
  - La pagina non e visibile nella sidebar
  - L'accesso diretto via URL ritorna 403

**SP**: 3 | **Priorita**: Should Have | **Epic**: Sync Timesheets | **Dipendenze**: US-230

---

## Riepilogo Pivot 10

| Story | Titolo | SP | Epic | Priorita |
|-------|--------|:--:|------|----------|
| US-230 | Portal Client adapter (JWT + read) | 5 | 23 | Must |
| US-231 | Aziende da Portal (sostituisce CrmCompany) | 5 | 23 | Must |
| US-232 | Read persons + employment contracts | 3 | 23 | Must |
| US-233 | Proxy endpoints /portal/* | 3 | 23 | Must |
| US-234 | Create Project from Deal Won | 5 | 24 | Must |
| US-235 | Customer matching by P.IVA | 5 | 24 | Must |
| US-236 | Deal detail "Crea Commessa su Portal" | 4 | 24 | Must |
| US-237 | Create Activity/Assignment on Portal | 5 | 25 | Must |
| US-238 | Deal detail "Risorse assegnate da Portal" | 6 | 25 | Must |
| US-239 | Timesheet sync job + margine reale | 5 | 26 | Must |
| US-240 | Deal detail "Avanzamento Operativo" | 3 | 26 | Must |
| US-241 | PortalConfig admin page | 3 | 26 | Should |
| **TOTALE Pivot 10** | | **52 SP** | | **11 Must, 1 Should** |
