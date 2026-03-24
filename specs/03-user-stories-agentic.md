# User Stories — Sistema Agentico Conversazionale (Pivot 3)

**Progetto:** AgentFlow PMI
**Data:** 2026-03-24
**Fase:** 3 — User Stories e Acceptance Criteria
**Fonte:** specs/02-prd.md (Epic A), specs/technical/pivot-3-agentic-system.md
**Nota:** Queste stories si aggiungono alle 40 stories esistenti (US-01 a US-40). Non le sostituiscono.

---

## Tabella Riassuntiva

| ID | Story | Epic | Req. PRD | MoSCoW | SP | Versione | Deps |
|----|-------|------|----------|--------|:--:|----------|------|
| US-A01 | Chat con orchestratore | EA: Agentico | AG1 | Must | 8 | v0.5 | US-01 |
| US-A02 | Conversazioni persistenti | EA: Agentico | AG2 | Must | 5 | v0.5 | US-A01 |
| US-A03 | Configurazione agenti (nomi, personalita) | EA: Agentico | AG3, AG10 | Must | 5 | v0.5 | US-A01 |
| US-A04 | Tool system per agenti | EA: Agentico | AG4 | Must | 8 | v0.5 | US-A01 |
| US-A05 | WebSocket streaming risposte | EA: Agentico | AG5 | Should | 5 | v0.5 | US-A01 |
| US-A06 | Onboarding conversazionale | EA: Agentico | AG7 | Must | 5 | v0.5 | US-A01, US-A04 |
| US-A07 | Multi-agent response | EA: Agentico | AG8 | Should | 5 | v0.5 | US-A01, US-A04 |
| US-A08 | Memoria conversazione | EA: Agentico | AG6 | Should | 5 | v0.5 | US-A02 |
| US-A09 | Frontend chat UI | EA: Agentico | AG1 | Must | 8 | v0.5 | US-A01, US-A05 |
| US-A10 | Agent skill discovery | EA: Agentico | AG9 | Could | 3 | v0.5 | US-A01 |

**Totale:** 10 stories | **Story Points totali:** 57
**Must Have:** 6 stories, 39 SP
**Should Have:** 3 stories, 15 SP
**Could Have:** 1 story, 3 SP

---

## Dettaglio User Stories

---

### US-A01: Chat con orchestratore

**Come** titolare di PMI, **voglio** parlare con AgentFlow in una chat, **in modo da** ottenere risposte sulla mia contabilita senza navigare menu e pagine.

**Story Points:** 8 | **MoSCoW:** Must | **Versione:** v0.5 | **Req. PRD:** AG1

**Acceptance Criteria:**

**AC-A01.1 — Happy Path: Invio messaggio e risposta**
DATO che sono autenticato e nella pagina chat,
QUANDO scrivo "Quante fatture ho ricevuto questo mese?" e invio,
ALLORA l'orchestratore analizza la richiesta, chiama il FiscoAgent/InvoiceService, e risponde con il numero e il totale delle fatture del mese corrente entro 5 secondi.

**AC-A01.2 — Happy Path: Routing a agente corretto**
DATO che chiedo "Come sta il mio cash flow?",
QUANDO l'orchestratore riceve il messaggio,
ALLORA identifica che serve il CashFlowAgent, lo chiama con i parametri corretti, e restituisce la previsione a 90 giorni con grafico.

**AC-A01.3 — Error: Richiesta non comprensibile**
DATO che scrivo qualcosa di incomprensibile o fuori contesto (es. "asdfghjkl"),
QUANDO l'orchestratore non riesce a interpretare,
ALLORA risponde con "Non ho capito la tua richiesta. Posso aiutarti con: fatture, contabilita, scadenze, cash flow, note spese, cespiti."

**AC-A01.4 — Error: Agente non disponibile (errore interno)**
DATO che l'agente chiamato fallisce (es. DB down),
QUANDO l'orchestratore riceve l'errore,
ALLORA mostra "Mi dispiace, c'e un problema temporaneo. Riprova tra qualche secondo." e logga l'errore.

**AC-A01.5 — Edge Case: Conversazione multi-turno**
DATO che ho gia chiesto "Mostrami le fatture da verificare",
QUANDO rispondo "Conferma la prima",
ALLORA l'orchestratore mantiene il contesto della conversazione e verifica la prima fattura della lista precedente.

---

### US-A02: Conversazioni persistenti

**Come** utente, **voglio** che le conversazioni siano salvate, **in modo da** poter riprendere dal punto lasciato quando torno il giorno dopo.

**Story Points:** 5 | **MoSCoW:** Must | **Versione:** v0.5 | **Deps:** US-A01 | **Req. PRD:** AG2

**Acceptance Criteria:**

**AC-A02.1 — Happy Path: Storico conversazioni**
DATO che ho avuto 5 conversazioni nelle ultime 2 settimane,
QUANDO accedo alla lista conversazioni,
ALLORA vedo le conversazioni ordinate per data con titolo auto-generato e preview dell'ultimo messaggio.

**AC-A02.2 — Happy Path: Ripresa conversazione**
DATO che ieri ho chiesto informazioni sulle scadenze,
QUANDO apro la conversazione di ieri,
ALLORA vedo lo storico completo e posso continuare a scrivere con il contesto preservato.

**AC-A02.3 — Error: Eliminazione conversazione**
DATO che voglio eliminare una conversazione,
QUANDO clicco "Elimina",
ALLORA la conversazione viene rimossa dalla lista (soft delete) e non e piu visibile.

**AC-A02.4 — Edge Case: Nuova conversazione**
DATO che sono nella chat,
QUANDO clicco "Nuova conversazione",
ALLORA si apre una chat vuota con un nuovo thread_id e il contesto viene resettato.

---

### US-A03: Configurazione agenti

**Come** utente, **voglio** personalizzare i nomi e la personalita degli agenti, **in modo da** sentirmi piu a mio agio nel dialogo.

**Story Points:** 5 | **MoSCoW:** Must | **Versione:** v0.5 | **Deps:** US-A01 | **Req. PRD:** AG3, AG10

**Acceptance Criteria:**

**AC-A03.1 — Happy Path: Rinominare agente**
DATO che vado in Impostazioni → Agenti,
QUANDO cambio il nome del FiscoAgent da "Agente Fisco" a "Mario",
ALLORA nella chat l'agente si presenta come "Mario" e il badge mostra "Mario".

**AC-A03.2 — Happy Path: Lista agenti con stato**
DATO che accedo alla configurazione agenti,
QUANDO la pagina carica,
ALLORA vedo tutti gli agenti disponibili con: nome corrente, tipo, stato (attivo/disattivo), icona.

**AC-A03.3 — Happy Path: Disabilitare agente**
DATO che non mi serve il CashFlowAgent,
QUANDO lo disabilito con il toggle,
ALLORA l'orchestratore non lo chiama piu e risponde "Questa funzionalita non e attiva. Vuoi attivarla dalle impostazioni?"

**AC-A03.4 — Error: Nome duplicato**
DATO che provo a dare lo stesso nome a due agenti,
QUANDO salvo,
ALLORA errore "Questo nome e gia usato da un altro agente".

**AC-A03.5 — Edge Case: Reset a default**
DATO che ho personalizzato i nomi,
QUANDO clicco "Ripristina nomi default",
ALLORA tutti i nomi tornano ai valori originali.

---

### US-A04: Tool system per agenti

**Come** sistema, **voglio** che gli agenti possano usare tools registrati, **in modo da** eseguire azioni concrete (query DB, calcoli, API esterne).

**Story Points:** 8 | **MoSCoW:** Must | **Versione:** v0.5 | **Deps:** US-A01 | **Req. PRD:** AG4

**Acceptance Criteria:**

**AC-A04.1 — Happy Path: Agente usa tool per rispondere**
DATO che l'utente chiede "Quante fatture ho?",
QUANDO l'orchestratore chiama il FiscoAgent,
ALLORA il FiscoAgent usa il tool `count_invoices` per fare la query SQL e restituisce il risultato.

**AC-A04.2 — Happy Path: Tool con parametri**
DATO che l'utente chiede "Mostrami le fatture di gennaio",
QUANDO l'orchestratore parsifica la richiesta,
ALLORA chiama il tool `list_invoices(date_from="2026-01-01", date_to="2026-01-31")` e mostra i risultati.

**AC-A04.3 — Happy Path: 9 agenti wrappati come tools**
DATO che il sistema si avvia,
QUANDO il tool registry viene inizializzato,
ALLORA tutti i 9 agenti esistenti sono registrati come tools con nome, descrizione, e schema parametri.

**AC-A04.4 — Error: Tool fallisce**
DATO che un tool fallisce (es. DB timeout),
QUANDO l'agente riceve l'errore,
ALLORA ritenta 1 volta, se fallisce ancora risponde "Non riesco a recuperare i dati. Riprova tra qualche secondo."

**AC-A04.5 — Edge Case: Tool restituisce dati grandi**
DATO che il tool `list_invoices` restituisce 500 fatture,
QUANDO l'agente riceve i risultati,
ALLORA li riassume ("Hai 500 fatture. Le prime 10 per importo sono: [lista]. Vuoi filtrare?") invece di mostrarli tutti.

---

### US-A05: WebSocket streaming risposte

**Come** utente, **voglio** vedere la risposta dell'agente che si scrive in tempo reale, **in modo da** sapere che il sistema sta lavorando.

**Story Points:** 5 | **MoSCoW:** Should | **Versione:** v0.5 | **Deps:** US-A01 | **Req. PRD:** AG5

**Acceptance Criteria:**

**AC-A05.1 — Happy Path: Streaming token by token**
DATO che invio un messaggio,
QUANDO l'agente genera la risposta,
ALLORA vedo il testo che appare progressivamente (come ChatGPT) via WebSocket.

**AC-A05.2 — Happy Path: Indicatore "sta scrivendo"**
DATO che ho inviato un messaggio,
QUANDO l'agente sta elaborando,
ALLORA vedo "AgentFlow sta scrivendo..." con animazione dots.

**AC-A05.3 — Error: WebSocket disconnesso**
DATO che la connessione WebSocket si interrompe,
QUANDO il frontend rileva la disconnessione,
ALLORA mostra "Connessione persa. Riconnessione..." e riprova automaticamente ogni 3 secondi.

**AC-A05.4 — Edge Case: Fallback a HTTP**
DATO che WebSocket non e supportato (proxy, firewall),
QUANDO il frontend non riesce a connettersi via WS,
ALLORA usa polling HTTP ogni 2 secondi come fallback.

---

### US-A06: Onboarding conversazionale

**Come** nuovo utente, **voglio** che l'agente mi guidi nell'onboarding con una conversazione, **in modo da** configurare la mia azienda parlando invece di compilare form.

**Story Points:** 5 | **MoSCoW:** Must | **Versione:** v0.5 | **Deps:** US-A01, US-A04 | **Req. PRD:** AG7

**Acceptance Criteria:**

**AC-A06.1 — Happy Path: Onboarding via chat**
DATO che sono un nuovo utente senza profilo configurato,
QUANDO apro la chat per la prima volta,
ALLORA l'orchestratore avvia il ContoEconomicoAgent che mi fa 5-6 domande sul mio business (basate sul codice ATECO) per creare il piano dei conti personalizzato.

**AC-A06.2 — Happy Path: ATECO detection**
DATO che ho inserito la P.IVA in fase di registrazione,
QUANDO l'agente avvia l'onboarding,
ALLORA rileva automaticamente il codice ATECO e usa il template corretto ("Vedo che sei un'azienda software. Fammi qualche domanda...").

**AC-A06.3 — Error: Utente abbandona onboarding**
DATO che rispondo a 3 domande su 6 e chiudo la chat,
QUANDO torno il giorno dopo,
ALLORA l'agente riprende dal punto lasciato ("Bentornato! Stavamo configurando il tuo piano. Mancano 3 domande.").

**AC-A06.4 — Edge Case: Utente gia configurato**
DATO che ho gia completato l'onboarding,
QUANDO apro la chat,
ALLORA l'orchestratore non ripropone l'onboarding ma risponde normalmente.

---

### US-A07: Multi-agent response

**Come** utente, **voglio** che l'orchestratore chiami piu agenti per una risposta completa, **in modo da** avere una visione d'insieme con una sola domanda.

**Story Points:** 5 | **MoSCoW:** Should | **Versione:** v0.5 | **Deps:** US-A01, US-A04 | **Req. PRD:** AG8

**Acceptance Criteria:**

**AC-A07.1 — Happy Path: Domanda multi-agente**
DATO che chiedo "Come sta la mia azienda?",
QUANDO l'orchestratore analizza la richiesta,
ALLORA chiama in parallelo: FiscoAgent (fatture mese), ContaAgent (saldo dare/avere), CashFlowAgent (previsione), e compone una risposta unica.

**AC-A07.2 — Happy Path: Badge agente nella risposta**
DATO che la risposta viene da piu agenti,
QUANDO viene visualizzata,
ALLORA ogni sezione mostra il badge dell'agente che ha fornito quel dato (es. "[Fisco] 12 fatture ricevute" "[Cash Flow] Saldo previsto €45.200").

**AC-A07.3 — Error: Un agente fallisce, gli altri rispondono**
DATO che chiedo info multi-agente e il CashFlowAgent fallisce,
QUANDO l'orchestratore riceve l'errore parziale,
ALLORA mostra i dati degli agenti che hanno risposto + "Non riesco a recuperare il cash flow al momento."

**AC-A07.4 — Edge Case: Timeout risposta lunga**
DATO che la domanda multi-agente richiede >10 secondi,
QUANDO l'orchestratore nota il ritardo,
ALLORA mostra risultati parziali man mano che arrivano + "Sto ancora recuperando i dati del cash flow..."

---

### US-A08: Memoria conversazione

**Come** utente, **voglio** che l'agente ricordi le mie preferenze e scelte passate, **in modo da** non ripetere le stesse informazioni ogni volta.

**Story Points:** 5 | **MoSCoW:** Should | **Versione:** v0.5 | **Deps:** US-A02 | **Req. PRD:** AG6

**Acceptance Criteria:**

**AC-A08.1 — Happy Path: Ricorda preferenze**
DATO che ho detto "Mostrami sempre gli importi in migliaia",
QUANDO in una conversazione successiva chiedo i totali,
ALLORA l'agente formatta in migliaia (€45.2k invece di €45.200,00).

**AC-A08.2 — Happy Path: Contesto cross-conversazione**
DATO che nella conversazione di ieri ho chiesto del fornitore "Rossi SRL",
QUANDO oggi chiedo "Aggiornamenti su Rossi?",
ALLORA l'agente sa di quale fornitore parlo senza che io specifichi la P.IVA.

**AC-A08.3 — Error: Memoria piena**
DATO che la memoria ha raggiunto il limite (es. 100 entries),
QUANDO l'agente deve salvare una nuova preferenza,
ALLORA rimuove la preferenza piu vecchia non usata da 30+ giorni.

**AC-A08.4 — Edge Case: Reset memoria**
DATO che voglio che l'agente dimentichi tutto,
QUANDO dico "Dimentica le mie preferenze" o vado in Impostazioni → Reset memoria,
ALLORA la memoria viene cancellata e l'agente ricomincia da zero.

---

### US-A09: Frontend chat UI

**Come** utente, **voglio** un'interfaccia chat moderna e intuitiva, **in modo da** dialogare con l'agente in modo naturale.

**Story Points:** 8 | **MoSCoW:** Must | **Versione:** v0.5 | **Deps:** US-A01, US-A05 | **Req. PRD:** AG1

**Acceptance Criteria:**

**AC-A09.1 — Happy Path: Layout chat**
DATO che apro AgentFlow,
QUANDO la pagina carica,
ALLORA vedo: sidebar con lista conversazioni (sinistra), area chat (centro), input messaggio (basso) con bottone invio.

**AC-A09.2 — Happy Path: Messaggi con formattazione**
DATO che l'agente risponde con una tabella di fatture,
QUANDO il messaggio viene renderizzato,
ALLORA le tabelle, i numeri formattati (€1.234,56), le date (DD/MM/YYYY), e i badge agente sono visualizzati correttamente.

**AC-A09.3 — Happy Path: Mobile responsive**
DATO che accedo da smartphone,
QUANDO la chat carica,
ALLORA la sidebar e nascosta (hamburger menu), la chat occupa tutto lo schermo, la tastiera non copre l'input.

**AC-A09.4 — Error: Messaggio troppo lungo**
DATO che l'agente risponde con un testo di 5000+ parole,
QUANDO il messaggio viene visualizzato,
ALLORA viene troncato con "Mostra tutto" e un'opzione per espandere.

**AC-A09.5 — Edge Case: Azioni rapide**
DATO che l'agente suggerisce "Vuoi verificare questa fattura?",
QUANDO vedo il suggerimento,
ALLORA ci sono bottoni cliccabili ["Si, verifica", "No, salta"] che inviano il comando corrispondente.

---

### US-A10: Agent skill discovery

**Come** nuovo utente, **voglio** che l'agente mi dica cosa sa fare, **in modo da** capire come usarlo al meglio.

**Story Points:** 3 | **MoSCoW:** Could | **Versione:** v0.5 | **Deps:** US-A01 | **Req. PRD:** AG9

**Acceptance Criteria:**

**AC-A10.1 — Happy Path: Comando "cosa sai fare?"**
DATO che scrivo "Cosa sai fare?" o "Aiuto",
QUANDO l'orchestratore riceve il messaggio,
ALLORA elenca gli agenti attivi con le loro capacita: "Posso aiutarti con: Fatture e contabilita (Agente Conta), Scadenze fiscali (Agente Fisco), Cash flow (Agente Cash), Note spese, Cespiti..."

**AC-A10.2 — Happy Path: Suggerimenti proattivi**
DATO che la conversazione e vuota (primo messaggio),
QUANDO l'utente non ha ancora scritto,
ALLORA mostra chip suggerimenti: "Come stanno le mie finanze?", "Fatture da verificare", "Prossime scadenze", "Aiuto".

**AC-A10.3 — Error: Agente disabilitato**
DATO che chiedo qualcosa che richiede un agente disabilitato,
QUANDO l'orchestratore rileva che serve il CashFlowAgent (disabilitato),
ALLORA risponde "Per il cash flow serve attivare l'Agente Cash Flow. Vuoi attivarlo ora?"

**AC-A10.4 — Edge Case: Suggerimento contestuale**
DATO che ho appena verificato una fattura,
QUANDO la verifica e completata,
ALLORA l'agente suggerisce "Fattura registrata! Vuoi vedere le altre fatture da verificare?"

---

## Riepilogo per Versione

### v0.5 — Sistema Agentico (10 stories, 57 SP)
US-A01, US-A02, US-A03, US-A04, US-A05, US-A06, US-A07, US-A08, US-A09, US-A10

**Dipendenze critiche:**
```
US-A01 (Orchestratore) → base per tutto
  ├── US-A02 (Persistenza) → US-A08 (Memoria)
  ├── US-A03 (Config agenti)
  ├── US-A04 (Tool system) → US-A06 (Onboarding chat) + US-A07 (Multi-agent)
  ├── US-A05 (WebSocket) → US-A09 (Chat UI)
  └── US-A10 (Skill discovery)
```

---
_User Stories Sistema Agentico — 2026-03-24_
