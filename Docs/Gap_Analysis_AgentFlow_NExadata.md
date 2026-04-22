# Gap Analysis — AgentFlow CRM per Nexa Data

> Analisi delle funzionalità mancanti nel CRM AgentFlow per supportare l'attività commerciale di Nexa Data, con focus sulla vendita di **elevia** tramite **social selling su LinkedIn** gestito da un **fractional account**.

**Data:** 4 aprile 2026
**Autore:** Nexa Data — Ufficio Commerciale & Prodotto

---

## 1. Contesto

Nexa Data opera su due fronti commerciali paralleli:

**Canale classico** — vendita diretta di consulenza IT, progetti T&M, servizi managed e hardware. Questo canale è ben coperto dall'attuale CRM AgentFlow, che gestisce pipeline, ordini, email marketing e analytics.

**Canale LinkedIn / elevia** — vendita del prodotto elevia (piattaforma AI per la gestione della conoscenza aziendale) attraverso un fractional account dedicato che fa social selling su LinkedIn. Questo canale presenta esigenze specifiche che l'attuale sistema non copre.

Il presente documento dettaglia ogni lacuna identificata, il motivo per cui è critica, e una proposta funzionale per colmarla.

---

## 2. Gap identificati

---

### GAP-01 — LinkedIn come origine contatto

**Stato attuale:** Il campo "Origine" del contatto prevede solo quattro valori: `web`, `referral`, `evento`, `cold`.

**Cosa manca:** Non esiste `linkedin` come origine, né sotto-categorie che distinguano il tipo di interazione LinkedIn che ha generato il lead (post organico, DM, InMail, commento, webinar LinkedIn Live, articolo).

**Perché è critico:** Senza questa informazione è impossibile misurare il ROI dell'attività di social selling e capire quali tattiche LinkedIn generano lead di qualità. Il fractional non ha visibilità sull'efficacia del proprio lavoro.

**Proposta funzionale:**

Aggiungere le seguenti origini al campo "Origine contatto":

| Nuova origine | Quando usarla |
|---------------|---------------|
| `linkedin_organico` | Il lead ha interagito con un post e poi è stato contattato |
| `linkedin_dm` | Il lead è stato acquisito tramite messaggio diretto |
| `linkedin_inmail` | Acquisito tramite InMail a pagamento |
| `linkedin_evento` | Partecipante a un LinkedIn Live o evento LinkedIn |
| `linkedin_ads` | Arrivato tramite campagna LinkedIn Ads |
| `linkedin_referral` | Presentato da un contatto LinkedIn comune |

---

### GAP-02 — Attività di tipo "LinkedIn"

**Stato attuale:** I tipi di attività disponibili sono: `call`, `email`, `meeting`, `note`, `task`.

**Cosa manca:** Non esistono attività specifiche per il social selling. Su LinkedIn il commerciale compie azioni diverse da una telefonata o un'email: invia connection request, scrive DM, commenta post del prospect, condivide contenuti, partecipa a gruppi.

**Perché è critico:** Il fractional account non può tracciare nel CRM ciò che fa quotidianamente. Le sue attività restano invisibili, rendendo impossibile correlare azioni LinkedIn con avanzamento dei deal.

**Proposta funzionale:**

Aggiungere i seguenti tipi di attività:

| Tipo attività | Descrizione | Esempio |
|---------------|-------------|---------|
| `linkedin_connection` | Richiesta di connessione inviata/accettata | "Connessione accettata da Mario Bianchi, CTO di Acme" |
| `linkedin_dm` | Messaggio diretto inviato o ricevuto | "DM di approfondimento su elevia, ha chiesto demo" |
| `linkedin_engagement` | Commento, like o condivisione su post del prospect | "Commentato post su digital transformation" |
| `linkedin_content` | Contenuto pubblicato che ha generato interazione | "Post su case study elevia — 3 prospect hanno interagito" |
| `linkedin_inmail` | InMail inviata tramite Sales Navigator | "InMail a 15 decision maker settore manifattura" |

---

### GAP-03 — Pre-funnel social selling (prima del "Nuovo Lead")

**Stato attuale:** La pipeline parte dallo stage "Nuovo Lead" (10% probabilità). Non esiste nulla prima.

**Cosa manca:** Su LinkedIn il percorso di acquisizione è lungo e graduale. Prima che un contatto diventi un "Nuovo Lead" nel CRM, passa attraverso fasi di warming che sono il cuore del lavoro del fractional.

**Perché è critico:** Il fractional lavora su centinaia di contatti in fase di warm-up. Se il CRM parte solo dal "Nuovo Lead", perde visibilità su tutto il lavoro a monte che genera quei lead. Non può dimostrare il valore della propria attività e non può ottimizzare il funnel.

**Proposta funzionale:**

Introdurre un **pre-funnel LinkedIn** con questi stadi, che precedono l'ingresso nella pipeline classica:

```
Pre-funnel LinkedIn:
| Profilo identificato | Connesso | In conversazione | Interesse mostrato | → Nuovo Lead (pipeline classica) |
```

| Stage pre-funnel | Descrizione | Azione tipica |
|------------------|-------------|---------------|
| **Profilo identificato** | Target individuato ma non ancora contattato | Ricerca su Sales Navigator, lista prospect |
| **Connesso** | Connection request accettata | Primo messaggio di benvenuto |
| **In conversazione** | Scambio di DM attivo | Condivisione contenuti, domande esplorative |
| **Interesse mostrato** | Ha chiesto info, demo o approfondimento | Passaggio al commerciale o booking demo |
| → **Nuovo Lead** | Entra nella pipeline classica | Il deal viene creato nel CRM |

---

### GAP-04 — Catalogo prodotti (elevia come entità)

**Stato attuale:** Il CRM ragiona per "tipo di deal" (T&M, fixed, spot, hardware). Non esiste il concetto di prodotto o servizio specifico.

**Cosa manca:** Elevia non è un progetto T&M né hardware. È un **prodotto SaaS/AI** con un proprio modello di pricing (subscription, licenza, setup + canone). Il CRM non permette di associare un deal a un prodotto specifico, né di filtrare o analizzare la pipeline per prodotto.

**Perché è critico:** Nexa Data deve poter rispondere a domande come: "Quanti deal elevia abbiamo in pipeline? Qual è il valore medio di un deal elevia? Qual è il conversion rate di elevia rispetto alla consulenza classica?" Oggi queste domande non hanno risposta.

**Proposta funzionale:**

Aggiungere un'entità **Prodotto/Servizio** con almeno questi campi:

| Campo | Esempio |
|-------|---------|
| Nome prodotto | elevia |
| Categoria | SaaS, Consulenza, Hardware, Managed Service |
| Modello pricing | Subscription, one-time, T&M |
| Prezzo base | 500 EUR/mese oppure da 15.000 EUR |
| Margine target | 65% |

E collegare ogni deal a uno o più prodotti, con un nuovo tipo deal:

| Nuovo tipo deal | Come funziona | Calcolo valore |
|-----------------|---------------|----------------|
| **SaaS/Subscription** | Canone ricorrente | Canone mensile x mesi contratto |
| **Licenza + Setup** | Importo una tantum + canone | Setup + (canone x mesi) |

---

### GAP-05 — Ruolo "Fractional / Collaboratore esterno"

**Stato attuale:** I ruoli disponibili sono: Owner, Admin, Commerciale, Viewer. Il commerciale vede solo i propri deal e contatti.

**Cosa manca:** Il fractional è un collaboratore esterno che lavora su un perimetro definito (solo lead LinkedIn, solo prodotto elevia) con esigenze specifiche: visibilità limitata, nessun accesso ai dati dei clienti storici, possibilmente un modello di compenso legato alle performance.

**Perché è critico:** Dare al fractional il ruolo "Commerciale" gli darebbe accesso a tutti i propri contatti senza distinzione. Non c'è modo di limitare la visibilità per canale o prodotto, né di tracciare le sue performance separatamente.

**Proposta funzionale:**

Nuovo ruolo **"External / Fractional"** con queste caratteristiche:

| Aspetto | Comportamento |
|---------|---------------|
| Visibilità contatti | Solo quelli creati da lui o assegnati a lui |
| Visibilità deal | Solo deal associati al suo canale/prodotto |
| Creazione contatti | Sì, con origine automatica "linkedin_*" |
| Invio email | Sì, solo sui propri contatti, con template approvati |
| Accesso analytics | Solo dashboard propria (non pipeline generale) |
| Gestione utenti | No |
| Configurazione | No |

Aggiungere inoltre un campo **"Canale di acquisizione"** al deal per poter filtrare: *LinkedIn/elevia* vs *Diretto/consulenza classica*.

---

### GAP-06 — Attribution contenuto → lead → deal

**Stato attuale:** Non esiste alcun collegamento tra contenuti pubblicati e lead generati.

**Cosa manca:** Il fractional pubblica post su LinkedIn per generare interesse su elevia. Serve sapere quale contenuto ha portato quale lead, per ottimizzare la strategia editoriale e dimostrare il ROI del content marketing.

**Perché è critico:** Senza attribution, il fractional pubblica "alla cieca" senza sapere cosa funziona. Nexa Data non può decidere se investire di più in post tecnici, case study, video o articoli.

**Proposta funzionale:**

Aggiungere un'entità **"Contenuto / Campagna"** collegabile ai contatti:

| Campo | Esempio |
|-------|---------|
| Titolo contenuto | "Come elevia ha ridotto del 60% i tempi di onboarding" |
| Tipo | Post LinkedIn, articolo, video, carousel, webinar |
| Data pubblicazione | 2026-03-15 |
| URL | Link al post |
| Metriche | Impressioni, like, commenti, condivisioni |
| Lead generati | Lista contatti che hanno interagito e sono entrati in pipeline |

E un campo **"Contenuto di origine"** nel contatto, compilabile manualmente o tramite integrazione.

---

### GAP-07 — Dashboard e KPI per social selling

**Stato attuale:** Le analytics mostrano: pipeline pesata, win rate, vinti/persi, statistiche email. Sono KPI da CRM classico.

**Cosa manca:** Mancano metriche specifiche per valutare l'efficacia del canale LinkedIn e del fractional.

**Perché è critico:** Il fractional viene pagato per risultati. Nexa Data deve poter valutare oggettivamente se l'investimento nel social selling sta rendendo, confrontandolo con il canale classico.

**Proposta funzionale:**

Nuova sezione **"Social Selling Analytics"** con:

| KPI | Calcolo | Obiettivo |
|-----|---------|-----------|
| **Lead da LinkedIn** | Contatti con origine linkedin_* creati nel periodo | Volume del canale |
| **Tasso connessione → lead** | Lead / connection request inviate | Efficacia outreach |
| **Tasso lead → deal** | Deal creati / lead LinkedIn | Qualità dei lead |
| **Tempo medio LinkedIn → deal** | Giorni da prima interazione LinkedIn a creazione deal | Velocità del funnel |
| **Valore pipeline LinkedIn** | Somma deal con origine LinkedIn | Peso del canale |
| **Win rate LinkedIn** | Deal vinti LinkedIn / deal chiusi LinkedIn | Confronto con altri canali |
| **ROI fractional** | Valore deal chiusi LinkedIn / costo fractional | Ritorno sull'investimento |
| **Top contenuti** | Contenuti con più lead generati | Guida strategia editoriale |

---

### GAP-08 — Sequenze email dedicate a elevia

**Stato attuale:** I template predefiniti sono generici: Benvenuto, Follow-up proposta, Reminder scadenza. Le sequenze si attivano su stage change, nuovo contatto o manualmente.

**Cosa manca:** Non esistono template né sequenze specifiche per il journey di vendita di elevia, che è diverso dalla consulenza classica. Il prospect elevia tipicamente vuole vedere una demo, provare il prodotto, capire l'integrazione con i propri sistemi.

**Perché è critico:** Usare template generici per elevia risulta impersonale e poco efficace. Il ciclo di vendita elevia ha touchpoint specifici (demo, trial, onboarding) che richiedono comunicazioni dedicate.

**Proposta funzionale:**

Nuovi template per il journey elevia:

| Template | Quando | Contenuto |
|----------|--------|-----------|
| **Intro elevia** | Dopo primo contatto LinkedIn | Presentazione prodotto, link a landing page |
| **Post-demo elevia** | Dopo la demo | Recap funzionalità viste, prossimi passi |
| **Invito trial** | Prospect qualificato | Accesso trial gratuito, guida quick start |
| **Follow-up trial** | 3-5 giorni dopo inizio trial | Come sta andando? Serve supporto? |
| **Case study elevia** | Prospect in fase di valutazione | Risultati ottenuti da clienti simili |
| **Proposta elevia** | Proposta inviata | Dettaglio pricing, ROI atteso, timeline |
| **Reminder decisione** | 7 giorni dopo proposta | Scadenza offerta, disponibilità per dubbi |

Nuova sequenza **"LinkedIn → elevia demo → deal":**

```
Giorno 0:  Contatto entra da LinkedIn → email "Intro elevia"
Giorno 2:  Se ha aperto → email "Vuoi vedere una demo?"
Giorno 5:  Se NON ha aperto → email "Il tuo settore sta cambiando"
Giorno 7:  Post-demo (trigger manuale) → email "Post-demo elevia"
Giorno 10: Se ha aperto post-demo → email "Invito trial"
Giorno 17: Se trial attivo → email "Follow-up trial"
Giorno 21: → email "Case study elevia"
Giorno 28: → email "Proposta elevia"
```

---

## 3. Matrice di priorità

| Gap | Impatto | Urgenza | Effort stimato | Priorità |
|-----|---------|---------|----------------|----------|
| GAP-01 — Origini LinkedIn | Alto | Alta | Basso (config) | P1 |
| GAP-02 — Attività LinkedIn | Alto | Alta | Medio (nuovo tipo) | P1 |
| GAP-04 — Catalogo prodotti | Alto | Alta | Alto (nuova entità) | P1 |
| GAP-05 — Ruolo Fractional | Alto | Alta | Alto (permessi) | P1 |
| GAP-03 — Pre-funnel | Medio | Media | Alto (nuovo modulo) | P2 |
| GAP-07 — Dashboard social | Alto | Media | Medio (analytics) | P2 |
| GAP-08 — Sequenze elevia | Medio | Media | Basso (config) | P2 |
| GAP-06 — Attribution | Medio | Bassa | Alto (integrazione) | P3 |

---

## 4. Raccomandazione

L'attuale CRM AgentFlow è solido per la vendita classica B2B ma non è pronto per supportare il canale LinkedIn/elevia con fractional account. Le lacune non sono marginali: riguardano la struttura stessa del dato (origini, attività, prodotti, ruoli) e l'analitica necessaria per governare un canale di vendita moderno basato sul social selling.

Si raccomanda di procedere in tre fasi:

**Fase 1 (immediata)** — Implementare GAP-01, GAP-02, GAP-04, GAP-05. Sono le fondamenta: senza origini LinkedIn, attività social, catalogo prodotti e ruolo fractional, il CRM non può nemmeno registrare ciò che accade.

**Fase 2 (entro 30 giorni)** — Implementare GAP-03, GAP-07, GAP-08. Pre-funnel, dashboard e sequenze dedicate permettono di gestire e misurare il canale in modo strutturato.

**Fase 3 (entro 60 giorni)** — Implementare GAP-06. L'attribution contenuto→lead richiede integrazione con LinkedIn Analytics ed è il tassello finale per ottimizzare la strategia.

---

*Documento generato il 4 aprile 2026 — Nexa Data*
