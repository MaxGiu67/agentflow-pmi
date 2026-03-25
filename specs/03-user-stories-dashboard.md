# User Stories — Agentic Dashboard (Epic B)

**Data:** 2026-03-25
**Fonte:** specs/02-prd.md (Epic B)

---

## Stories

| ID | Story | SP | MoSCoW | Deps |
|----|-------|:--:|--------|------|
| US-B01 | Dashboard JSON-driven con widget renderer | 8 | Must | — |
| US-B02 | Chatbot floating nella dashboard | 5 | Must | US-A01 |
| US-B03 | Tool modify_dashboard (add/remove widget via chat) | 5 | Must | US-B01, US-B02 |
| US-B04 | Drag & drop riposizionamento widget | 3 | Must | US-B01 |
| US-B05 | Chatbot proattivo con notifiche | 3 | Should | US-B02 |

**Totale:** 24 SP

---

### US-B01: Dashboard JSON-driven con widget renderer

**Come** amministratore, **voglio** una dashboard composta da widget configurabili via JSON, **in modo da** personalizzare la vista con i KPI e grafici che mi servono.

**SP:** 8 | **MoSCoW:** Must

**AC:**

**AC-B01.1 — Widget renderer da JSON config**
DATO un layout JSON con widget definiti (tipo, titolo, data_source, posizione),
QUANDO la dashboard carica,
ALLORA renderizza ogni widget nel tipo corretto (stat_card, bar_chart, table, etc.).

**AC-B01.2 — 6 tipi di widget**
DATO il sistema,
QUANDO un widget ha tipo "stat_card", "bar_chart", "pie_chart", "line_chart", "table" o "alert",
ALLORA viene renderizzato con il componente Recharts/HTML corretto.

**AC-B01.3 — Selettore anno globale**
DATO che seleziono anno 2024,
QUANDO il filtro cambia,
ALLORA tutti i widget si aggiornano con i dati dell'anno selezionato.

**AC-B01.4 — Salvataggio layout nel DB**
DATO che personalizzo la dashboard,
QUANDO salvo,
ALLORA il layout JSON viene persistito nel DB per il mio tenant e ricaricato al prossimo login.

---

### US-B02: Chatbot floating nella dashboard

**Come** utente, **voglio** un chatbot sempre visibile in basso a destra della dashboard, **in modo da** chiedere informazioni e modificare la dashboard senza cambiare pagina.

**SP:** 5 | **MoSCoW:** Must | **Deps:** US-A01

**AC:**

**AC-B02.1 — Chatbot floating bottom-right**
DATO che sono sulla dashboard,
QUANDO clicco l'icona chat in basso a destra,
ALLORA si apre un pannello chat sovrapposto (non navigazione a /chat) con input e messaggi.

**AC-B02.2 — Collapsibile**
DATO che il chatbot e aperto,
QUANDO clicco la X o l'icona,
ALLORA si chiude a icona minimizzata.

**AC-B02.3 — Usa lo stesso orchestratore**
DATO che scrivo nel chatbot floating,
QUANDO invio un messaggio,
ALLORA usa la stessa API POST /chat/send e lo stesso orchestratore della pagina Chat completa.

---

### US-B03: Tool modify_dashboard

**Come** utente, **voglio** che l'agente possa aggiungere e rimuovere widget dalla dashboard quando glielo chiedo, **in modo da** configurare la dashboard parlando.

**SP:** 5 | **MoSCoW:** Must | **Deps:** US-B01, US-B02

**AC:**

**AC-B03.1 — Aggiungi widget via chat**
DATO che dico "aggiungi un grafico del fatturato mensile",
QUANDO l'orchestratore interpreta la richiesta,
ALLORA aggiunge un widget bar_chart alla dashboard e salva il layout.

**AC-B03.2 — Rimuovi widget via chat**
DATO che dico "togli la tabella fornitori",
QUANDO l'orchestratore esegue,
ALLORA rimuove il widget corrispondente dal layout.

**AC-B03.3 — Suggerimento widget dopo risposta**
DATO che chiedo "quanto ho fatturato a NTT Data?",
QUANDO l'agente risponde con i dati,
ALLORA suggerisce "Vuoi aggiungerlo come widget nella dashboard?"

---

### US-B04: Drag & drop

**Come** utente, **voglio** spostare e ridimensionare i widget con drag & drop, **in modo da** organizzare la dashboard come preferisco.

**SP:** 3 | **MoSCoW:** Must | **Deps:** US-B01

**AC:**

**AC-B04.1 — Drag per spostare**
DATO che trascino un widget,
QUANDO lo rilascio in una nuova posizione,
ALLORA il widget si sposta e il layout viene salvato.

**AC-B04.2 — Resize**
DATO che trascino il bordo di un widget,
QUANDO lo ridimensiono,
ALLORA il widget cambia dimensione e il layout viene salvato.

---

### US-B05: Chatbot proattivo

**Come** utente, **voglio** che il chatbot mi avvisi di cose importanti quando apro la dashboard, **in modo da** non perdere scadenze o fatture da verificare.

**SP:** 3 | **MoSCoW:** Should | **Deps:** US-B02

**AC:**

**AC-B05.1 — Notifica all'apertura**
DATO che apro la dashboard e ci sono fatture da verificare o scadenze imminenti,
QUANDO la pagina carica,
ALLORA il chatbot mostra un messaggio: "Buongiorno! 3 fatture da verificare, scadenza IVA tra 12 giorni."

---
