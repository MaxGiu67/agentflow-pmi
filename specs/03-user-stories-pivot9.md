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
| **TOTALE** | | **116 SP** | | **16 Must, 6 Should** |
