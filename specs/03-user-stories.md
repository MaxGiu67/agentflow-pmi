# User Stories — AgentFlow PMI (ContaBot)

**Progetto:** AgentFlow PMI
**Data:** 2026-03-22 (aggiornato post-pivot)
**Fase:** 3 — User Stories e Acceptance Criteria
**Fonte:** specs/01-vision.md, specs/02-prd.md, specs/04-tech-spec.md
**Pivot:** Cassetto fiscale come fonte primaria (non email)

---

## Tabella Riassuntiva

| ID | Story | Epic | Req. PRD | MoSCoW | SP | Versione | Deps |
|----|-------|------|----------|--------|:--:|----------|------|
| US-01 | Registrazione e login utente | E0: Auth | A1, A2 | Must | 5 | v0.1 | — |
| US-02 | Profilo utente e configurazione azienda | E0: Auth | A3 | Must | 3 | v0.1 | US-01 |
| US-03 | Autenticazione SPID/CIE per cassetto fiscale | E0: Auth | A4 | Must | 8 | v0.1 | US-01 |
| US-04 | Sync fatture dal cassetto fiscale AdE | E1: Acquisizione | M1 | Must | 8 | v0.1 | US-03 |
| US-05 | Parsing XML FatturaPA | E1: Acquisizione | M2 | Must | 3 | v0.1 | US-04 |
| US-06 | Upload manuale fattura | E1: Acquisizione | S4 | Should | 2 | v0.2 | — |
| US-07 | Ricezione fatture real-time A-Cube SDI | E1: Acquisizione | S1 | Should | 5 | v0.2 | US-02 |
| US-08 | Connessione email via MCP server | E1: Acquisizione | S6 | Should | 5 | v0.2 | — |
| US-09 | OCR su fattura PDF/immagine (non-XML) | E1: Acquisizione | S7 | Should | 5 | v0.2 | US-08 o US-06 |
| US-10 | Categorizzazione automatica con learning | E2: Categorizzazione | M3 | Must | 8 | v0.1 | US-05 |
| US-11 | Verifica e correzione categoria | E2: Categorizzazione | M4 | Must | 5 | v0.1 | US-10 |
| US-12 | Setup piano dei conti personalizzato | E3: Contabilita | M5 | Must | 8 | v0.1 | US-02 |
| US-13 | Registrazione automatica scritture partita doppia | E3: Contabilita | M5 | Must | 8 | v0.1 | US-10, US-12 |
| US-14 | Dashboard fatture e stato agenti | E4: Dashboard | M6 | Must | 5 | v0.1 | US-05 |
| US-15 | Dashboard scritture contabili | E4: Dashboard | M6 | Must | 3 | v0.1 | US-13 |
| US-16 | Onboarding guidato (SPID -> cassetto -> prima fattura) | E4: Dashboard | — | Must | 5 | v0.1 | US-03, US-12 |
| US-17 | Scadenzario fiscale base | E4: Dashboard | S5 | Should | 5 | v0.2 | US-02 |
| US-18 | Notifiche WhatsApp/Telegram | E4: Dashboard | S2 | Should | 5 | v0.2 | US-17 |
| US-19 | Report export per commercialista | E4: Dashboard | S3 | Should | 5 | v0.2 | US-13 |
| US-20 | Alert scadenze fiscali personalizzate | E5: Fisco | F3 | Could | 5 | v0.3 | US-04 |
| US-21 | Fatturazione attiva SDI via A-Cube | E5: Fisco | F6 | Could | 8 | v0.3 | US-12 |
| US-22 | Liquidazione IVA automatica | E5: Fisco | F7 | Could | 8 | v0.3 | US-13, US-04 |
| US-23 | Bilancio CEE via Odoo OCA | E5: Fisco | F8 | Could | 5 | v0.3 | US-13 |
| US-24 | Collegamento conto corrente Open Banking | E6: Banca/Cash | F4 | Could | 8 | v0.3 | — |
| US-25 | Cash flow predittivo 90gg | E6: Banca/Cash | F1 | Could | 8 | v0.3 | US-24, US-13 |
| US-26 | Riconciliazione fatture - movimenti bancari | E6: Banca/Cash | F5 | Could | 8 | v0.3 | US-24, US-13 |
| US-27 | Pagamenti fornitori via PISP | E6: Banca/Cash | F10 | Could | 8 | v0.4 | US-24, US-26 |
| US-28 | Monitor aggiornamenti normativi | E7: Normativo | F9 | Could | 5 | v0.4 | — |
| US-29 | Note spese — upload e categorizzazione | E8: Gap Contabili | G1 | Could | 5 | v0.3 | US-02, US-09, US-10 |
| US-30 | Note spese — approvazione e rimborso | E8: Gap Contabili | G1 | Could | 3 | v0.3 | US-29 |
| US-31 | Cespiti — scheda cespite e ammortamento automatico | E8: Gap Contabili | G2 | Could | 5 | v0.3 | US-13 |
| US-32 | Cespiti — registro e dismissione | E8: Gap Contabili | G2 | Could | 3 | v0.3 | US-31 |
| US-33 | Ritenute d'acconto — riconoscimento e calcolo netto | E8: Gap Contabili | G3 | Could | 5 | v0.3 | US-05, US-13 |
| US-34 | Certificazione Unica (CU) annuale | E8: Gap Contabili | G4 | Could | 5 | v0.4 | US-33 |
| US-35 | Imposta di bollo automatica | E8: Gap Contabili | G5 | Could | 3 | v0.3 | US-21 |
| US-36 | Ratei e risconti di fine esercizio | E8: Gap Contabili | G6 | Could | 5 | v0.3 | US-13 |
| US-37 | Conservazione digitale a norma | E8: Gap Contabili | G8 | Could | 5 | v0.4 | US-04 |
| US-38 | F24 compilazione e generazione | E8: Gap Contabili | G7 | Could | 5 | v0.4 | US-22, US-33 |
| US-39 | Dashboard CEO — cruscotto direzionale | E9: Cruscotto CEO | C1 | Could | 8 | v0.4 | US-13, US-14, US-24 |
| US-40 | Dashboard CEO — KPI e budget vs consuntivo | E9: Cruscotto CEO | C1,C3 | Could | 8 | v0.4 | US-39 |

**Totale:** 40 stories | **Story Points totali:** 224
**v0.1 (Must Have):** 12 stories, 69 SP
**v0.2 (Should Have):** 7 stories, 32 SP
**v0.3 (Could Have):** 14 stories, 79 SP
**v0.4 (Could Have):** 7 stories, 44 SP

---

## Dettaglio User Stories

---

### EPIC 0: Autenticazione e Profilo

---

#### US-01: Registrazione e login utente
**Come** nuovo utente, **voglio** registrarmi e accedere a ContaBot, **in modo da** avere un account sicuro per gestire i miei dati contabili.

**Story Points:** 5 | **MoSCoW:** Must | **Versione:** v0.1 | **Req. PRD:** A1, A2

**Acceptance Criteria:**

**AC-01.1 — Happy Path: Registrazione con email e password**
DATO che sono nella pagina di registrazione,
QUANDO inserisco email valida, password (min 8 char, 1 maiuscola, 1 numero) e confermo,
ALLORA il mio account e creato, ricevo un'email di verifica, e dopo la conferma posso accedere alla dashboard.

**AC-01.2 — Happy Path: Login e logout**
DATO che ho un account verificato,
QUANDO inserisco email e password corretti,
ALLORA ottengo un JWT valido per 24h con refresh token (7gg), vedo la dashboard, e posso fare logout invalidando il token.

**AC-01.3 — Error: Email gia registrata**
DATO che provo a registrarmi con un'email gia in uso,
QUANDO invio il form,
ALLORA il sistema mostra "Email gia registrata" senza rivelare se l'account esiste (per sicurezza) e offre il link "Hai dimenticato la password?".

**AC-01.4 — Error: Password reset**
DATO che ho dimenticato la password,
QUANDO clicco "Password dimenticata" e inserisco la mia email,
ALLORA ricevo un link di reset valido per 1 ora, con possibilita di impostare una nuova password.

**AC-01.5 — Edge Case: Brute force protection**
DATO che qualcuno tenta 5 login falliti consecutivi sul mio account,
QUANDO il sistema rileva il pattern,
ALLORA blocca i tentativi per 15 minuti, logga l'evento, e mi notifica via email del tentativo sospetto.

---

#### US-02: Profilo utente e configurazione azienda
**Come** utente registrato, **voglio** configurare il profilo della mia azienda (tipo, regime fiscale, P.IVA), **in modo da** avere piano dei conti e scadenze personalizzate.

**Story Points:** 3 | **MoSCoW:** Must | **Versione:** v0.1 | **Deps:** US-01 | **Req. PRD:** A3

**Acceptance Criteria:**

**AC-02.1 — Happy Path: Configurazione completa**
DATO che sono autenticato e accedo al profilo,
QUANDO inserisco tipo azienda (SRL, SRLS, P.IVA, ditta individuale), regime fiscale (forfettario, semplificato, ordinario), P.IVA e codice ATECO,
ALLORA il profilo e salvato e il sistema puo generare piano conti e scadenze personalizzate.

**AC-02.2 — Error: P.IVA formato invalido**
DATO che inserisco una P.IVA con formato errato (non 11 cifre o checksum invalido),
QUANDO invio il form,
ALLORA il sistema mostra errore di validazione specifico con formato corretto atteso.

**AC-02.3 — Error: Codice ATECO inesistente**
DATO che inserisco un codice ATECO non valido,
QUANDO il sistema verifica contro la tabella ATECO ISTAT,
ALLORA mostra errore con suggerimento dei codici piu simili e un link alla classificazione ATECO.

**AC-02.4 — Edge Case: Modifica profilo dopo setup**
DATO che ho gia un piano dei conti creato e cambio tipo azienda (es. da P.IVA forfettario a SRL ordinario),
QUANDO salvo la modifica,
ALLORA il sistema avvisa che il piano dei conti dovra essere ricreato, chiede conferma, e segnala le scritture che potrebbero necessitare riallineamento.

---

#### US-03: Autenticazione SPID/CIE per cassetto fiscale
**Come** titolare di PMI, **voglio** autenticarmi con SPID o CIE per accedere al cassetto fiscale, **in modo da** scaricare automaticamente le mie fatture dall'Agenzia delle Entrate.

**Story Points:** 8 | **MoSCoW:** Must | **Versione:** v0.1 | **Deps:** US-01 | **Req. PRD:** A4

**Acceptance Criteria:**

**AC-03.1 — Happy Path: Autenticazione SPID riuscita**
DATO che sono autenticato in ContaBot e clicco "Collega cassetto fiscale",
QUANDO completo il flusso SPID/CIE via redirect FiscoAPI (livello 2),
ALLORA il token FiscoAPI e salvato (encrypted AES-256), vedo la conferma "Cassetto fiscale collegato", e il primo sync viene lanciato automaticamente.

**AC-03.2 — Error: Autenticazione SPID annullata**
DATO che avvio il flusso SPID,
QUANDO annullo o fallisco l'autenticazione sul provider SPID,
ALLORA torno alla dashboard con messaggio "Autenticazione annullata — serve SPID o CIE per accedere al cassetto fiscale" e posso riprovare.

**AC-03.3 — Error: Token SPID scaduto**
DATO che il token FiscoAPI e scaduto,
QUANDO il FiscoAgent tenta il sync giornaliero,
ALLORA il sistema sospende il sync, mi notifica "Sessione cassetto fiscale scaduta — riautentica con SPID", e continua a funzionare con i dati gia scaricati.

**AC-03.4 — Edge Case: Utente senza SPID/CIE**
DATO che non ho SPID ne CIE abilitata,
QUANDO accedo alla sezione cassetto fiscale,
ALLORA il sistema spiega come ottenere SPID (link ai provider certificati), e offre l'upload manuale come alternativa temporanea.

**AC-03.5 — Edge Case: Delega a terzi (commercialista)**
DATO che il mio commercialista ha una delega per accedere al mio cassetto fiscale,
QUANDO configuro l'accesso delegato,
ALLORA il sistema supporta il flusso di delega FiscoAPI, con consenso esplicito dell'utente e log dell'operazione.

---

### EPIC 1: Acquisizione Fatture

---

#### US-04: Sync fatture dal cassetto fiscale AdE
**Come** titolare di PMI, **voglio** che ContaBot scarichi automaticamente le fatture dal mio cassetto fiscale, **in modo da** avere tutte le fatture elettroniche senza doverle scaricare manualmente.

**Story Points:** 8 | **MoSCoW:** Must | **Versione:** v0.1 | **Deps:** US-03 | **Req. PRD:** M1

**Acceptance Criteria:**

**AC-04.1 — Happy Path: Primo sync (storico ultimi 90gg)**
DATO che ho collegato il cassetto fiscale con SPID,
QUANDO il FiscoAgent lancia il primo sync,
ALLORA scarica le fatture degli ultimi 90 giorni (lookback configurabile), le salva con source="cassetto_fiscale", e mostra il contatore fatture importate nella dashboard.

**AC-04.2 — Happy Path: Sync giornaliero incrementale**
DATO che il cassetto e collegato e il token e valido,
QUANDO il FiscoAgent esegue il sync giornaliero (schedulato alle 06:00),
ALLORA scarica solo le fatture nuove (data > ultimo sync), le processa, e aggiorna il timestamp last_sync. Tempo massimo: 30 secondi per 50 fatture.

**AC-04.3 — Error: FiscoAPI non disponibile**
DATO che FiscoAPI e down o in manutenzione,
QUANDO il FiscoAgent tenta il sync,
ALLORA riprova con backoff esponenziale (1h, 2h, 4h, max 3 tentativi), logga l'errore, e non perde le richieste pendenti. L'utente e notificato solo se il problema persiste >24h.

**AC-04.4 — Error: Fattura duplicata (gia presente nel sistema)**
DATO che una fattura e gia presente (match su numero_fattura + P.IVA_emittente + data),
QUANDO il sync scarica la stessa fattura,
ALLORA il sistema la riconosce come duplicato, non crea un record doppio, e arricchisce i metadati se mancanti.

**AC-04.5 — Edge Case: Cassetto fiscale vuoto (nuova P.IVA)**
DATO che l'utente ha una P.IVA appena aperta senza fatture nel cassetto,
QUANDO il primo sync restituisce 0 fatture,
ALLORA mostra "Nessuna fattura trovata — verranno importate automaticamente quando arriveranno" e suggerisce l'upload manuale per fatture cartacee.

---

#### US-05: Parsing XML FatturaPA
**Come** utente ContaBot, **voglio** che le fatture XML del cassetto vengano analizzate automaticamente, **in modo da** avere i dati strutturati senza intervento manuale.

**Story Points:** 3 | **MoSCoW:** Must | **Versione:** v0.1 | **Deps:** US-04 | **Req. PRD:** M2

**Acceptance Criteria:**

**AC-05.1 — Happy Path: Parsing XML FatturaPA**
DATO che il FiscoAgent ha scaricato un file XML dal cassetto,
QUANDO il Parser Agent riceve l'evento "invoice.downloaded",
ALLORA estrae tutti i campi (emittente, P.IVA, importo netto, IVA per aliquota, data, numero fattura, tipo documento, regime fiscale, righe dettaglio), salva come dati strutturati, e pubblica "invoice.parsed" su Redis. Accuracy target: >=99%.

**AC-05.2 — Happy Path: Nota di credito (TD04)**
DATO che arriva un XML con TipoDocumento = TD04 (nota di credito),
QUANDO il parser analizza il tipo documento,
ALLORA identifica correttamente il tipo, lo marca come nota di credito con riferimento alla fattura originale, e lo passa al flusso di registrazione separato.

**AC-05.3 — Error: XML malformato o non FatturaPA**
DATO che il file XML non rispetta lo schema FatturaPA (namespace errato, campi obbligatori mancanti),
QUANDO il parser tenta l'estrazione,
ALLORA la fattura e segnata come "parsing_fallito" con il motivo specifico, l'utente e notificato, e puo inserire i dati manualmente.

**AC-05.4 — Edge Case: Fattura con 200+ righe**
DATO che una fattura XML contiene piu di 200 righe dettaglio,
QUANDO il parser la processa,
ALLORA estrae tutte le righe entro 5 secondi, gestisce aliquote IVA multiple per riga, e logga warning se >500 righe.

---

#### US-06: Upload manuale fattura
**Come** utente ContaBot, **voglio** caricare manualmente un file PDF o foto di fattura, **in modo da** registrare fatture non presenti nel cassetto fiscale (cartacee, estere, proforma).

**Story Points:** 2 | **MoSCoW:** Should | **Versione:** v0.2 | **Req. PRD:** S4

**Acceptance Criteria:**

**AC-06.1 — Happy Path: Upload e processing**
DATO che sono nella dashboard,
QUANDO carico un file PDF/JPG/PNG/XML tramite drag-and-drop o file picker (max 10MB),
ALLORA il file viene processato (XML parser se .xml, OCR se PDF/immagine), i dati estratti vengono mostrati per verifica, e la fattura entra nel flusso di categorizzazione.

**AC-06.2 — Error: Formato non supportato**
DATO che provo a caricare un file .docx, .txt o altro formato,
QUANDO il sistema valida il formato,
ALLORA mostra i formati accettati (PDF, JPG, PNG, XML) e rifiuta il file.

**AC-06.3 — Error: File troppo grande**
DATO che provo a caricare un file >10MB,
QUANDO il sistema valida la dimensione,
ALLORA mostra errore con il limite massimo e suggerisce di comprimere l'immagine.

**AC-06.4 — Edge Case: Upload di fattura gia presente**
DATO che la fattura caricata ha lo stesso numero e P.IVA di una gia nel sistema,
QUANDO il sistema completa il parsing,
ALLORA avvisa del possibile duplicato con dettaglio della fattura esistente, e chiede conferma prima di salvare.

---

#### US-07: Ricezione fatture real-time A-Cube SDI
**Come** utente ContaBot, **voglio** ricevere le fatture in tempo reale appena transitano dal SDI, **in modo da** non aspettare il sync giornaliero del cassetto.

**Story Points:** 5 | **MoSCoW:** Should | **Versione:** v0.2 | **Deps:** US-02 | **Req. PRD:** S1

**Acceptance Criteria:**

**AC-07.1 — Happy Path: Ricezione fattura via webhook**
DATO che A-Cube e configurato con il webhook del mio tenant,
QUANDO una fattura indirizzata alla mia P.IVA transita su SDI,
ALLORA A-Cube notifica ContaBot via webhook, il sistema salva con source="sdi_realtime", la passa al parser, e aggiorna la dashboard.

**AC-07.2 — Error: Webhook non raggiungibile**
DATO che il server ContaBot e temporaneamente offline,
QUANDO A-Cube tenta la consegna del webhook,
ALLORA A-Cube riprova secondo la sua retry policy, e al ripristino le fatture vengono recuperate dal sync cassetto (fallback).

**AC-07.3 — Error: Fattura gia presente da cassetto**
DATO che la stessa fattura e gia stata scaricata dal cassetto fiscale,
QUANDO arriva via webhook SDI,
ALLORA la riconosce come duplicato e aggiorna solo metadati mancanti (es. stato consegna SDI real-time).

**AC-07.4 — Edge Case: Webhook con payload corrotto**
DATO che il webhook arriva con payload malformato o firma non valida,
QUANDO il sistema riceve la richiesta,
ALLORA rifiuta con HTTP 400, logga l'evento, e non crea record corrotti.

---

#### US-08: Connessione email via MCP server
**Come** utente ContaBot, **voglio** connettere il mio account email (Gmail, PEC, Outlook) come canale secondario, **in modo da** catturare documenti non-SDI (proforma, ricevute, fatture estere).

**Story Points:** 5 | **MoSCoW:** Should | **Versione:** v0.2 | **Req. PRD:** S6

**Acceptance Criteria:**

**AC-08.1 — Happy Path: Connessione Gmail via MCP**
DATO che scelgo "Connetti email" e seleziono Gmail,
QUANDO completo il flusso OAuth2 via MCP server,
ALLORA il mio account e collegato, vedo l'indirizzo email connesso, e il sistema monitora le email per allegati fattura.

**AC-08.2 — Happy Path: Connessione PEC/IMAP**
DATO che scelgo "Connetti PEC/IMAP",
QUANDO inserisco server, porta, email e password,
ALLORA il sistema testa la connessione, conferma il successo, e inizia il monitoraggio.

**AC-08.3 — Error: Permessi negati o credenziali errate**
DATO che rifiuto i permessi OAuth o inserisco credenziali IMAP errate,
QUANDO la connessione fallisce,
ALLORA torno alla dashboard con messaggio specifico e posso riprovare.

**AC-08.4 — Edge Case: Email come canale secondario**
DATO che ho gia il cassetto fiscale collegato,
QUANDO l'email cattura una fattura gia presente nel cassetto,
ALLORA la riconosce come duplicato (match numero+P.IVA) e non crea record doppi.

---

#### US-09: OCR su fattura PDF/immagine (non-XML)
**Come** utente ContaBot, **voglio** che le fatture PDF o foto vengano lette tramite OCR, **in modo da** registrare fatture non elettroniche (cartacee, estere, proforma).

**Story Points:** 5 | **MoSCoW:** Should | **Versione:** v0.2 | **Deps:** US-08 o US-06 | **Req. PRD:** S7

**Acceptance Criteria:**

**AC-09.1 — Happy Path: OCR con accuracy >=85%**
DATO che un PDF/immagine di fattura arriva (da upload o email),
QUANDO il sistema esegue OCR via Google Cloud Vision,
ALLORA estrae i campi principali con accuracy >=85%, crea il record con confidence score per campo. Tempo: <=10 secondi.

**AC-09.2 — Error: OCR con confidence bassa**
DATO che l'OCR restituisce dati con confidence <60%,
QUANDO il risultato viene valutato,
ALLORA la fattura e marcata "verifica richiesta", l'utente e notificato, e i campi a bassa confidence sono evidenziati nella UI.

**AC-09.3 — Error: File non leggibile**
DATO che il file e un PDF protetto da password o un'immagine corrotta,
QUANDO il sistema tenta il processing,
ALLORA mostra errore specifico ("PDF protetto" o "immagine illeggibile — risoluzione minima 300dpi") con suggerimento.

**AC-09.4 — Edge Case: Email con piu allegati**
DATO che un'email contiene 3 allegati PDF di cui solo 2 sono fatture,
QUANDO il sistema processa gli allegati,
ALLORA crea un record per ciascuna fattura, ignora gli allegati non-fattura, e logga il motivo dello scarto.

---

### EPIC 2: Categorizzazione Intelligente

---

#### US-10: Categorizzazione automatica con learning
**Come** libero professionista, **voglio** che ContaBot categorizzi automaticamente le fatture imparando dal mio stile, **in modo da** non dover piu categorizzare manualmente dopo le prime settimane.

**Story Points:** 8 | **MoSCoW:** Must | **Versione:** v0.1 | **Deps:** US-05 | **Req. PRD:** M3

**Acceptance Criteria:**

**AC-10.1 — Happy Path: Categorizzazione con rules engine**
DATO che una fattura e stata parsata con dati strutturati,
QUANDO il Learning Agent riceve l'evento "invoice.parsed",
ALLORA propone una categoria basata su regole (P.IVA nota -> fornitore noto -> categoria storica) con confidence score, e pubblica "invoice.categorized". Tempo: <=2 secondi.

**AC-10.2 — Happy Path: Learning migliora dopo 30 fatture verificate (ultimi 90gg)**
DATO che l'utente ha verificato/corretto 30+ fatture negli ultimi 90 giorni,
QUANDO arriva una nuova fattura da un pattern simile,
ALLORA il modello similarity propone la categoria con acceptance rate >=80%.

**AC-10.3 — Error: Nessuna regola applicabile**
DATO che arriva una fattura da un fornitore mai visto e senza pattern riconoscibile,
QUANDO il Learning Agent non raggiunge confidence >40%,
ALLORA la fattura e marcata "categoria suggerita: nessuna", presentata per categorizzazione manuale, e il feedback alimenta il modello.

**AC-10.4 — Error: Redis down — evento non consegnato**
DATO che Redis e temporaneamente non raggiungibile,
QUANDO il Parser Agent pubblica "invoice.parsed",
ALLORA l'evento e salvato in dead letter queue locale, il sistema riprova con backoff (5s, 15s, 60s), e la fattura non viene persa.

**AC-10.5 — Edge Case: Fornitore cambia ragione sociale, stessa P.IVA**
DATO che un fornitore noto cambia ragione sociale ma mantiene la stessa P.IVA,
QUANDO arriva una fattura con il nuovo nome,
ALLORA il sistema riconosce il fornitore tramite P.IVA e applica la stessa categorizzazione storica.

---

#### US-11: Verifica e correzione categoria
**Come** utente ContaBot, **voglio** verificare e correggere le categorizzazioni proposte, **in modo da** insegnare all'agente il mio stile contabile.

**Story Points:** 5 | **MoSCoW:** Must | **Versione:** v0.1 | **Deps:** US-10 | **Req. PRD:** M4

**Acceptance Criteria:**

**AC-11.1 — Happy Path: Conferma categoria**
DATO che una fattura ha categoria proposta con confidence >70%,
QUANDO clicco "Conferma",
ALLORA la categoria e registrata come verificata, il feedback positivo alimenta il modello, e la fattura passa alla registrazione contabile.

**AC-11.2 — Happy Path: Correzione categoria**
DATO che la categoria proposta e sbagliata,
QUANDO seleziono la categoria corretta dal menu a tendina,
ALLORA la fattura e aggiornata, il feedback negativo alimenta il modello (con motivo), e la fattura passa alla registrazione.

**AC-11.3 — Error: Categoria non presente nel piano dei conti**
DATO che cerco una categoria che non esiste,
QUANDO cerco una categoria inesistente,
ALLORA il sistema suggerisce le 3 categorie piu simili e offre l'opzione di crearne una nuova (propagata a Odoo).

**AC-11.4 — Edge Case: Verifica batch di piu fatture**
DATO che ci sono 10+ fatture in attesa di verifica,
QUANDO accedo alla vista "da verificare",
ALLORA posso scorrere in sequenza, confermare/correggere con shortcuts (Enter=conferma, Tab=prossima), e vedere il conteggio rimanente.

**AC-11.5 — Edge Case: Verifica concorrente (mobile + desktop)**
DATO che verifico la stessa fattura da due dispositivi,
QUANDO entrambi inviano una modifica,
ALLORA vince l'ultimo aggiornamento (last-write-wins con timestamp), il dispositivo piu lento riceve refresh con la versione corrente.

---

### EPIC 3: Contabilita in Partita Doppia

---

#### US-12: Setup piano dei conti personalizzato
**Come** titolare di PMI, **voglio** che ContaBot crei un piano dei conti su misura, **in modo da** avere la struttura contabile corretta fin dall'inizio.

**Story Points:** 8 | **MoSCoW:** Must | **Versione:** v0.1 | **Deps:** US-02 | **Req. PRD:** M5

**Acceptance Criteria:**

**AC-12.1 — Happy Path: Piano conti per SRL in regime ordinario**
DATO che il mio profilo indica SRL in regime ordinario,
QUANDO il ContaAgent riceve la configurazione,
ALLORA crea via API Odoo un piano dei conti CEE conforme al codice civile, con conti per stato patrimoniale e conto economico, registri IVA, e journal banca/cassa. Tempo: <=15 secondi.

**AC-12.2 — Happy Path: Piano conti per P.IVA forfettaria**
DATO che indico P.IVA in regime forfettario,
QUANDO il ContaAgent configura Odoo,
ALLORA crea un piano conti semplificato (senza IVA), con categorie costo/ricavo per forfettario.

**AC-12.3 — Error: Connessione Odoo fallita**
DATO che il ContaAgent tenta di creare il piano conti,
QUANDO la connessione a Odoo e interrotta,
ALLORA riprova con backoff (5s, 15s, 60s, max 3 tentativi), logga l'errore, e notifica l'utente se persiste.

**AC-12.4 — Edge Case: Tipo azienda non standard**
DATO che il tipo di azienda non e tra le opzioni standard,
QUANDO seleziono "Altro" con codice ATECO,
ALLORA crea un piano conti generico CEE con nota: "Piano generico — verifica consigliata dal commercialista".

---

#### US-13: Registrazione automatica scritture partita doppia
**Come** titolare di micro-impresa, **voglio** che le fatture categorizzate vengano registrate in partita doppia, **in modo da** avere la contabilita sempre aggiornata.

**Story Points:** 8 | **MoSCoW:** Must | **Versione:** v0.1 | **Deps:** US-10, US-12 | **Req. PRD:** M5

**Acceptance Criteria:**

**AC-13.1 — Happy Path: Registrazione fattura passiva**
DATO che una fattura passiva e stata categorizzata (es. "Consulenze"),
QUANDO il ContaAgent processa l'evento "invoice.categorized",
ALLORA crea su Odoo: DARE 6110 (Consulenze) netto + DARE 2212 (IVA credito) IVA + AVERE 4010 (Fornitori) totale, e pubblica "journal.entry.created". Tempo: <=5 secondi.

**AC-13.2 — Happy Path: Fattura con reverse charge**
DATO che arriva una fattura intra-UE con reverse charge,
QUANDO il ContaAgent rileva il regime dalla fattura XML,
ALLORA registra la doppia scrittura IVA (credito + debito) secondo normativa italiana.

**AC-13.3 — Error: Conto contabile mancante**
DATO che la categoria non ha un conto corrispondente in Odoo,
QUANDO il ContaAgent tenta la registrazione,
ALLORA la scrittura e sospesa, l'utente e notificato con suggerimento di mappatura, e la fattura resta "pending_accounting".

**AC-13.4 — Error: Sbilanciamento dare/avere**
DATO che per errore di calcolo IVA il totale DARE != AVERE,
QUANDO il ContaAgent invia la scrittura a Odoo,
ALLORA Odoo rifiuta, il sistema logga con dettagli importi, notifica l'utente, e la fattura passa a "errore_contabile".

**AC-13.5 — Edge Case: Fattura con piu aliquote IVA**
DATO che una fattura contiene righe con aliquote diverse (22%, 10%, 4%),
QUANDO il ContaAgent crea la scrittura,
ALLORA registra righe dare/avere separate per aliquota, mantenendo la quadratura.

**AC-13.6 — Edge Case: Registrazione concorrente (doppio evento)**
DATO che due eventi "invoice.categorized" arrivano per la stessa fattura,
QUANDO il ContaAgent riceve il secondo,
ALLORA verifica se la scrittura esiste gia (idempotency check su invoice_id) e ignora il duplicato loggando.

---

### EPIC 4: Dashboard e Reporting

---

#### US-14: Dashboard fatture e stato agenti
**Come** utente ContaBot, **voglio** una dashboard con fatture e stato agenti, **in modo da** avere una visione d'insieme immediata.

**Story Points:** 5 | **MoSCoW:** Must | **Versione:** v0.1 | **Deps:** US-05 | **Req. PRD:** M6

**Acceptance Criteria:**

**AC-14.1 — Happy Path: Vista completa**
DATO che sono autenticato,
QUANDO accedo alla home,
ALLORA vedo: contatore fatture (totale, da verificare, registrate), ultime 10 fatture con stato, pannello agenti (attivi/inattivi/errori), e stato ultimo sync cassetto.

**AC-14.2 — Happy Path: Filtri e ricerca**
DATO che sono nella lista fatture,
QUANDO uso filtri (data, tipo, fornitore, stato, importo, fonte),
ALLORA la lista si aggiorna mostrando solo le fatture corrispondenti.

**AC-14.3 — Error: Nessuna fattura (empty state)**
DATO che e il mio primo accesso senza fatture,
QUANDO accedo alla dashboard,
ALLORA vedo empty state: "Collega il cassetto fiscale con SPID per importare le tue fatture" con CTA prominente.

**AC-14.4 — Edge Case: 1000+ fatture**
DATO che ho 1000+ fatture,
QUANDO accedo alla dashboard,
ALLORA la lista e paginata (50/pagina), contatori corretti, caricamento <=2s. Per <=100 fatture, <=500ms.

---

#### US-15: Dashboard scritture contabili
**Come** titolare di PMI, **voglio** visualizzare le scritture contabili, **in modo da** verificare che la partita doppia sia corretta.

**Story Points:** 3 | **MoSCoW:** Must | **Versione:** v0.1 | **Deps:** US-13 | **Req. PRD:** M6

**Acceptance Criteria:**

**AC-15.1 — Happy Path: Lista scritture dare/avere**
DATO che sono nella sezione "Contabilita",
QUANDO accedo alle scritture,
ALLORA vedo journal entries con data, descrizione, conti dare/avere, importi, e link alla fattura.

**AC-15.2 — Happy Path: Quadratura dare/avere**
DATO che visualizzo una scrittura,
QUANDO verifico i totali,
ALLORA DARE = AVERE sempre (garantito da ContaAgent + validazione Odoo).

**AC-15.3 — Error: Scrittura con errore Odoo**
DATO che Odoo ha rifiutato una registrazione (es. periodo chiuso),
QUANDO accedo alla scrittura,
ALLORA vedo stato "Errore" con messaggio Odoo specifico e azione suggerita.

**AC-15.4 — Edge Case: Empty state (fatture senza scritture)**
DATO che ho fatture importate ma non categorizzate/registrate,
QUANDO accedo alle scritture,
ALLORA vedo "Nessuna scrittura — le fatture devono essere categorizzate prima" con link a "da verificare".

**AC-15.5 — Edge Case: Filtro per periodo contabile**
DATO che voglio le scritture Q1 2026,
QUANDO applico il filtro,
ALLORA vedo solo scritture nel range con totali parziali corretti.

---

#### US-16: Onboarding guidato
**Come** nuovo utente, **voglio** essere guidato dalla registrazione alla prima fattura categorizzata, **in modo da** capire il valore di ContaBot in meno di 5 minuti.

**Story Points:** 5 | **MoSCoW:** Must | **Versione:** v0.1 | **Deps:** US-03, US-12

**Acceptance Criteria:**

**AC-16.1 — Happy Path: Onboarding in <5 minuti**
DATO che mi registro,
QUANDO seguo il wizard (1. tipo azienda -> 2. regime fiscale/P.IVA -> 3. SPID -> 4. attendi sync cassetto),
ALLORA setup completato in <5 min, piano conti creato, cassetto collegato, prime fatture nella dashboard.

**AC-16.2 — Happy Path: Time-to-value**
DATO che l'onboarding e completato e il cassetto ha fatture,
QUANDO il primo sync completa,
ALLORA fatture nella dashboard entro 60 secondi, con categorie proposte.

**AC-16.3 — Error: Onboarding abbandonato**
DATO che abbandono al passo 2,
QUANDO torno il giorno dopo,
ALLORA riprende dal punto lasciato senza perdere dati.

**AC-16.4 — Error: SPID fallisce durante onboarding**
DATO che il flusso SPID fallisce al passo 3,
QUANDO l'errore e rilevato,
ALLORA completa passi 1-2 (profilo + piano conti), suggerisce di riprovare SPID, e offre upload manuale.

**AC-16.5 — Edge Case: Tipo azienda non standard**
DATO che seleziono "Altro",
QUANDO inserisco codice ATECO (validato),
ALLORA crea piano conti generico CEE con nota: "Verifica consigliata dal commercialista".

---

#### US-17: Scadenzario fiscale base
**Come** titolare di micro-impresa, **voglio** vedere le scadenze fiscali imminenti, **in modo da** non dimenticare IVA, F24, INPS.

**Story Points:** 5 | **MoSCoW:** Should | **Versione:** v0.2 | **Deps:** US-02 | **Req. PRD:** S5

**Acceptance Criteria:**

**AC-17.1 — Happy Path: Scadenze per regime**
DATO che il mio profilo indica regime ordinario,
QUANDO accedo allo scadenzario,
ALLORA vedo scadenze standard (IVA trimestrale/mensile, F24, INPS) con date corrette.

**AC-17.2 — Happy Path: Countdown e priorita**
DATO che ci sono 3 scadenze nei prossimi 15 giorni,
QUANDO accedo alla dashboard,
ALLORA vedo widget con countdown, colore (verde >15gg, giallo 7-15gg, rosso <7gg).

**AC-17.3 — Error: Regime non configurato**
DATO che il profilo fiscale e incompleto,
QUANDO accedo allo scadenzario,
ALLORA invita a completare il profilo per scadenze personalizzate.

**AC-17.4 — Edge Case: Scadenze su festivo/weekend**
DATO che una scadenza cade di sabato,
QUANDO il sistema calcola le date,
ALLORA sposta al primo giorno lavorativo (normativa italiana).

---

#### US-18: Notifiche WhatsApp/Telegram
**Come** utente ContaBot, **voglio** ricevere notifiche su WhatsApp o Telegram, **in modo da** essere avvisato anche fuori dalla dashboard.

**Story Points:** 5 | **MoSCoW:** Should | **Versione:** v0.2 | **Deps:** US-17 | **Req. PRD:** S2

**Acceptance Criteria:**

**AC-18.1 — Happy Path: Notifica scadenza Telegram**
DATO che ho connesso Telegram e una scadenza e tra 3 giorni,
QUANDO il sistema invia la notifica,
ALLORA ricevo messaggio con tipo, data, importo stimato, e link dashboard.

**AC-18.2 — Happy Path: Configurazione canale**
DATO che accedo a impostazioni notifiche,
QUANDO scelgo WhatsApp o Telegram e verifico,
ALLORA le notifiche future vanno sul canale scelto.

**AC-18.3 — Error: Consegna fallita**
DATO che il canale e irraggiungibile,
QUANDO il sistema tenta l'invio,
ALLORA riprova dopo 1h (max 3 tentativi), poi email come fallback.

**AC-18.4 — Edge Case: Troppe notifiche**
DATO che ci sono 10 fatture e 3 scadenze nello stesso giorno,
QUANDO prepara le notifiche,
ALLORA raggruppa in un singolo digest.

---

#### US-19: Report export per commercialista
**Come** titolare di PMI, **voglio** esportare un report contabile per il commercialista, **in modo da** semplificare la consegna dei dati.

**Story Points:** 5 | **MoSCoW:** Should | **Versione:** v0.2 | **Deps:** US-13 | **Req. PRD:** S3

**Acceptance Criteria:**

**AC-19.1 — Happy Path: Export trimestrale PDF**
DATO che seleziono Q1 2026 e PDF,
QUANDO clicco "Genera report",
ALLORA genera PDF con: riepilogo fatture, registri IVA, prima nota, totali per categoria.

**AC-19.2 — Happy Path: Export CSV**
DATO che seleziono CSV,
QUANDO genero il report,
ALLORA CSV compatibile con software di studio (data, numero, importo, IVA, conto).

**AC-19.3 — Error: Periodo senza dati**
DATO che il trimestre non ha fatture,
QUANDO genero il report,
ALLORA avvisa "Nessuna fattura nel periodo" anziche PDF vuoto.

**AC-19.4 — Edge Case: Fatture non categorizzate nel periodo**
DATO che ci sono 5 fatture non registrate nel periodo,
QUANDO genero il report,
ALLORA include avviso "5 fatture in attesa" e offre opzione di includerle o escluderle.

---

### EPIC 5: Fisco Avanzato e Compliance (v0.3)

---

#### US-20: Alert scadenze fiscali personalizzate
**Come** titolare di micro-impresa, **voglio** alert specifici per il mio regime con importi stimati, **in modo da** sapere cosa pagare e quando.

**Story Points:** 5 | **MoSCoW:** Could | **Versione:** v0.3 | **Deps:** US-04 | **Req. PRD:** F3

**Acceptance Criteria:**

**AC-20.1 — Happy Path: Alert IVA con importo stimato**
DATO che il mio regime prevede IVA trimestrale,
QUANDO mancano 10 giorni,
ALLORA ricevo alert con importo stimato dalle fatture registrate, data limite, e link al dettaglio.

**AC-20.2 — Happy Path: Alert con importo da FiscoAPI**
DATO che FiscoAPI fornisce l'importo esatto F24,
QUANDO il FiscoAgent lo riceve,
ALLORA l'alert include importo ufficiale con codice tributo.

**AC-20.3 — Error: Stima imprecisa**
DATO che ci sono fatture non registrate,
QUANDO calcola la stima,
ALLORA mostra "stima provvisoria — N fatture in attesa" e suggerisce completare verifiche.

**AC-20.4 — Edge Case: Cambio regime in corso d'anno**
DATO che passo da forfettario a ordinario a meta anno,
QUANDO aggiorno il profilo,
ALLORA le scadenze vengono ricalcolate per il nuovo regime dalla data di cambio.

---

#### US-21: Fatturazione attiva SDI via A-Cube
**Come** libero professionista, **voglio** emettere fatture elettroniche da ContaBot, **in modo da** avere un unico sistema per fatture attive e passive.

**Story Points:** 8 | **MoSCoW:** Could | **Versione:** v0.3 | **Deps:** US-12 | **Req. PRD:** F6

**Acceptance Criteria:**

**AC-21.1 — Happy Path: Emissione e invio SDI**
DATO che compilo la fattura (cliente, importo, IVA, descrizione),
QUANDO clicco "Invia via SDI",
ALLORA creata su Odoo, generato XML FatturaPA, inviato ad A-Cube, stato aggiornato real-time.

**AC-21.2 — Error: Rifiuto SDI**
DATO che l'SDI rifiuta (es. P.IVA errata),
QUANDO il webhook notifica il rifiuto,
ALLORA mostra "Rifiutata" con motivazione SDI, e l'utente puo correggere e reinviare.

**AC-21.3 — Error: Numero fattura duplicato**
DATO che tento di emettere con numero gia usato,
QUANDO il sistema valida,
ALLORA blocca con "Numero gia utilizzato" e suggerisce il prossimo disponibile.

**AC-21.4 — Error: Importo zero o negativo**
DATO che inserisco importo <=0,
QUANDO il sistema valida,
ALLORA mostra "Importo deve essere positivo — usa nota di credito per rettifiche".

**AC-21.5 — Edge Case: Nota di credito**
DATO che devo emettere nota di credito,
QUANDO la creo con riferimento alla fattura originale,
ALLORA genera XML con TD04, riferimenti corretti, e scritture contabili inverse.

---

#### US-22: Liquidazione IVA automatica
**Come** titolare di SRL, **voglio** che ContaBot calcoli la liquidazione IVA, **in modo da** avere l'importo da versare senza calcoli manuali.

**Story Points:** 8 | **MoSCoW:** Could | **Versione:** v0.3 | **Deps:** US-13, US-04 | **Req. PRD:** F7

**Acceptance Criteria:**

**AC-22.1 — Happy Path: Calcolo trimestrale**
DATO che e il 10 del mese successivo al trimestre,
QUANDO il FiscoAgent lancia il calcolo via Odoo OCA,
ALLORA vedo prospetto IVA: vendite, acquisti, IVA debito/credito, saldo, con drill-down registri.

**AC-22.2 — Happy Path: Reverse charge**
DATO che ci sono fatture con reverse charge,
QUANDO il calcolo viene eseguito,
ALLORA IVA reverse charge computata a debito e credito correttamente.

**AC-22.3 — Error: Fatture non registrate**
DATO che ci sono fatture non registrate,
QUANDO il calcolo viene eseguito,
ALLORA warning "N fatture non incluse" con opzione di forzare registrazione.

**AC-22.4 — Edge Case: Credito IVA precedente**
DATO che il trimestre precedente chiuse con credito IVA di E1.200,
QUANDO calcola il nuovo trimestre,
ALLORA il credito e riportato e sottratto dal debito corrente.

---

#### US-23: Bilancio CEE via Odoo OCA
**Come** titolare di SRL, **voglio** generare il bilancio CEE, **in modo da** adempiere all'obbligo di deposito.

**Story Points:** 5 | **MoSCoW:** Could | **Versione:** v0.3 | **Deps:** US-13 | **Req. PRD:** F8

**Acceptance Criteria:**

**AC-23.1 — Happy Path: Generazione bilancio CEE**
DATO che tutte le scritture dell'esercizio sono registrate,
QUANDO clicco "Genera bilancio",
ALLORA genera via Odoo OCA Stato Patrimoniale e Conto Economico formato CEE, esportabile PDF e XBRL.

**AC-23.2 — Error: Scritture non chiuse**
DATO che ci sono scritture provvisorie,
QUANDO tento la generazione,
ALLORA avvisa "N scritture provvisorie da chiudere" con lista e azione suggerita.

**AC-23.3 — Edge Case: Bilancio abbreviato micro-impresa**
DATO che il profilo indica micro-impresa (sotto soglie art. 2435-ter c.c.),
QUANDO genero il bilancio,
ALLORA genera formato abbreviato.

**AC-23.4 — Edge Case: Primo esercizio**
DATO che e il primo anno,
QUANDO genero il bilancio,
ALLORA la colonna "anno precedente" e vuota o "primo esercizio", senza errori.

---

### EPIC 6: Open Banking e Cash Flow (v0.3-v0.4)

---

#### US-24: Collegamento conto corrente Open Banking
**Come** titolare di PMI, **voglio** collegare il mio conto corrente, **in modo da** avere saldi e movimenti sincronizzati.

**Story Points:** 8 | **MoSCoW:** Could | **Versione:** v0.3 | **Req. PRD:** F4

**Acceptance Criteria:**

**AC-24.1 — Happy Path: Collegamento con SCA**
DATO che clicco "Collega conto",
QUANDO seleziono la banca (400+ via CBI Globe) e completo la SCA,
ALLORA conto collegato, vedo IBAN e saldo, consent PSD2 attivo 90gg.

**AC-24.2 — Happy Path: Sync giornaliero (ultimi 90gg al primo sync)**
DATO che il conto e collegato e il consent attivo,
QUANDO il BankingAdapter esegue il sync via A-Cube AISP,
ALLORA importa movimenti. Primo sync: ultimi 90gg. Successivi: solo incrementali.

**AC-24.3 — Error: Consent PSD2 scaduto**
DATO che sono passati 90 giorni,
QUANDO il consent scade,
ALLORA notifica 7gg prima, al giorno della scadenza banner con link per rinnovare (nuova SCA).

**AC-24.4 — Error: Revoca consent da portale bancario**
DATO che l'utente revoca il consent dalla banca,
QUANDO il BankingAdapter riceve 403/consent_revoked,
ALLORA aggiorna stato a "revocato", notifica, e offre re-collegamento.

**AC-24.5 — Edge Case: Banca non su CBI Globe**
DATO che la banca non e nella lista,
QUANDO cerco e non trovo,
ALLORA suggerisce upload manuale estratto conto (CSV/XLS) e registra la richiesta.

**AC-24.6 — Edge Case: IBAN non italiano (Wise, Revolut)**
DATO che ho conto con IBAN non IT,
QUANDO tento il collegamento,
ALLORA verifica se A-Cube supporta la banca, in caso negativo suggerisce Fabrick o upload manuale.

---

#### US-25: Cash flow predittivo 90gg
**Come** titolare di PMI, **voglio** una previsione cash flow a 90 giorni, **in modo da** decidere basandomi su dati reali.

**Story Points:** 8 | **MoSCoW:** Could | **Versione:** v0.3 | **Deps:** US-24, US-13 | **Req. PRD:** F1

**Acceptance Criteria:**

**AC-25.1 — Happy Path: Previsione con dati bancari + fatture**
DATO che ho conto collegato e 20+ fatture storiche,
QUANDO accedo a "Cash Flow",
ALLORA grafico 90gg: saldo attuale, entrate previste, uscite previste, saldo proiettato giorno per giorno.

**AC-25.2 — Happy Path: Alert soglia critica (configurabile)**
DATO che il saldo scende sotto soglia configurata (default E5.000, modificabile per tenant),
QUANDO il CashFlowAgent rileva,
ALLORA alert con data prevista e dettaglio uscite critiche.

**AC-25.3 — Error: Dati insufficienti**
DATO che ho solo 5 fatture,
QUANDO accedo al cash flow,
ALLORA saldo attuale + movimenti recenti + "Servono 20+ fatture — attualmente N/20".

**AC-25.4 — Error: Dati bancari stale (>3 giorni)**
DATO che il sync e fallito per 3+ giorni,
QUANDO accedo al cash flow,
ALLORA banner "Dati aggiornati al [data] — previsione potrebbe non essere accurata" con azione per rinnovare.

**AC-25.5 — Edge Case: Pagamento in ritardo**
DATO che una fattura emessa e scaduta da 15gg,
QUANDO proietta il cash flow,
ALLORA evidenziata come "incasso in ritardo" con due scenari: con e senza incasso.

---

#### US-26: Riconciliazione fatture - movimenti bancari
**Come** utente ContaBot, **voglio** che il sistema abbini fatture e movimenti bancari, **in modo da** sapere quali fatture sono pagate.

**Story Points:** 8 | **MoSCoW:** Could | **Versione:** v0.3 | **Deps:** US-24, US-13 | **Req. PRD:** F5

**Acceptance Criteria:**

**AC-26.1 — Happy Path: Match automatico**
DATO che arriva un movimento in uscita di E1.220 verso "Studio Rossi",
QUANDO il CashFlowAgent cerca match,
ALLORA abbina alla fattura corrispondente, marca "riconciliati", pubblica "payment.matched".

**AC-26.2 — Happy Path: Suggerimento con confidence**
DATO che un movimento non ha match esatto,
QUANDO cerca possibili match,
ALLORA propone le 3 fatture piu probabili con confidence, l'utente conferma o abbina manualmente.

**AC-26.3 — Error: Nessun match**
DATO che il movimento non corrisponde a nessuna fattura,
QUANDO la riconciliazione fallisce,
ALLORA appare in "non riconciliati" con opzioni: abbinare, creare fattura, o segnare come "non-fattura".

**AC-26.4 — Error: Movimento in valuta estera**
DATO che il conto ha un movimento in USD/GBP,
QUANDO tenta riconciliazione,
ALLORA converte al cambio del giorno (BCE), abbina in EUR, logga tasso applicato.

**AC-26.5 — Edge Case: Pagamento parziale**
DATO che la fattura e E3.000 ma il pagamento e E1.500,
QUANDO rileva pagamento parziale,
ALLORA registra il parziale, marca "parzialmente pagata (E1.500/E3.000)", residuo nel cash flow.

**AC-26.6 — Edge Case: Sync concorrente**
DATO che sync giornaliero in corso e l'utente chiede refresh manuale,
QUANDO entrambi tentano insert,
ALLORA lock per tenant_id+bank_account_id, il secondo attende, nessun duplicato (dedup su transaction_id).

---

#### US-27: Pagamenti fornitori via PISP
**Come** titolare di PMI, **voglio** pagare fornitori da ContaBot, **in modo da** completare il ciclo fattura->pagamento->registrazione.

**Story Points:** 8 | **MoSCoW:** Could | **Versione:** v0.4 | **Deps:** US-24, US-26 | **Req. PRD:** F10

**Acceptance Criteria:**

**AC-27.1 — Happy Path: Pagamento con SCA**
DATO che ho una fattura da pagare (E2.440, IBAN visibile),
QUANDO clicco "Paga" e confermo con SCA,
ALLORA pagamento via A-Cube PISP, registra uscita, riconcilia fattura, chiude partita Odoo.

**AC-27.2 — Error: Fondi insufficienti**
DATO che il saldo < importo,
QUANDO tento pagamento,
ALLORA "Fondi insufficienti — saldo: EX" e suggerisce data futura.

**AC-27.3 — Error: IBAN non valido**
DATO che l'IBAN fornitore e errato,
QUANDO valida prima dell'invio,
ALLORA errore validazione IBAN, permette correzione.

**AC-27.4 — Edge Case: Pagamento batch**
DATO che ho 5 fatture dello stesso fornitore,
QUANDO seleziono tutte e "Paga",
ALLORA propone bonifico cumulativo con causale che elenca numeri fattura, riconcilia tutte.

---

### EPIC 7: Normativo (v0.4)

---

#### US-28: Monitor aggiornamenti normativi
**Come** titolare di PMI, **voglio** essere avvisato quando cambiano norme fiscali, **in modo da** restare in regola senza monitorare la Gazzetta Ufficiale.

**Story Points:** 5 | **MoSCoW:** Could | **Versione:** v0.4 | **Req. PRD:** F9

**Acceptance Criteria:**

**AC-28.1 — Happy Path: Alert su circolare AdE**
DATO che l'AdE pubblica una circolare che impatta il mio regime,
QUANDO il NormativoAgent rileva (feed RSS GU + API AdE),
ALLORA alert con riepilogo semplificato, impatto sul mio profilo, e azioni suggerite.

**AC-28.2 — Happy Path: Aggiornamento regole**
DATO che una legge modifica aliquote o scadenze,
QUANDO il NormativoAgent valida il cambiamento,
ALLORA propone aggiornamento regole con preview impatto, in attesa conferma utente.

**AC-28.3 — Error: Feed non disponibile**
DATO che i feed GU/AdE sono offline,
QUANDO il NormativoAgent tenta il polling,
ALLORA riprova con backoff, logga, e continua con regole attuali.

**AC-28.4 — Edge Case: Norma con decorrenza futura**
DATO che una norma entra in vigore tra 3 mesi,
QUANDO il NormativoAgent la rileva,
ALLORA schedula per la data di decorrenza, avvisa in anticipo, non modifica regole correnti.

---

### EPIC 8: Gap Contabili (v0.3-v0.4)

---

#### US-29: Note spese — upload e categorizzazione
**Come** titolare/dipendente, **voglio** caricare scontrini e ricevute e categorizzarli, **in modo da** tracciare le spese aziendali e preparare i rimborsi.

**Story Points:** 5 | **MoSCoW:** Could | **Versione:** v0.3 | **Deps:** US-02, US-09, US-10 | **Req. PRD:** G1

**Acceptance Criteria:**

**AC-29.1 — Happy Path: Upload scontrino**
DATO che ho uno scontrino di un pranzo di lavoro,
QUANDO carico la foto o il PDF,
ALLORA il sistema estrae importo, data, esercente (OCR), e propone la categoria (es. "Trasferte e rappresentanza") con il learning delle fatture.

**AC-29.2 — Happy Path: Policy di spesa**
DATO che la policy aziendale prevede max €25/pranzo,
QUANDO carico uno scontrino di €32,
ALLORA warning "Supera il limite di €25 — richiede approvazione" con flag per il titolare.

**AC-29.3 — Error: Scontrino illeggibile**
DATO che la foto e sfocata o tagliata,
QUANDO l'OCR non riesce a estrarre i dati,
ALLORA mostra "Non riesco a leggere — inserisci manualmente" con campi importo, data, descrizione.

**AC-29.4 — Edge Case: Spesa in valuta estera**
DATO che lo scontrino e in USD (trasferta estera),
QUANDO carica la spesa,
ALLORA converte al cambio BCE del giorno, salva sia importo originale che convertito.

---

#### US-30: Note spese — approvazione e rimborso
**Come** titolare, **voglio** approvare le note spese e registrare i rimborsi, **in modo da** chiudere il ciclo spesa→rimborso→contabilità.

**Story Points:** 3 | **MoSCoW:** Could | **Versione:** v0.3 | **Deps:** US-29 | **Req. PRD:** G1

**Acceptance Criteria:**

**AC-30.1 — Happy Path: Approvazione e registrazione**
DATO che il dipendente ha inserito 5 spese nel mese,
QUANDO il titolare approva la nota spese,
ALLORA ContaAgent registra: DARE 6200 Trasferte / AVERE 5010 Debiti vs dipendenti, e marca come "da rimborsare".

**AC-30.2 — Happy Path: Rimborso da conto**
DATO che la nota spese e approvata,
QUANDO il titolare clicca "Rimborsa" (v0.4: via PISP, prima: manuale),
ALLORA registra DARE 5010 Debiti vs dipendenti / AVERE 1110 Banca c/c.

**AC-30.3 — Error: Rifiuto spesa**
DATO che una spesa non e conforme,
QUANDO il titolare rifiuta con motivazione,
ALLORA il dipendente riceve notifica con motivo del rifiuto.

**AC-30.4 — Error: Rimborso PISP fallito**
DATO che il rimborso e approvato e il titolare clicca "Rimborsa" via PISP (v0.4),
QUANDO il pagamento fallisce (fondi insufficienti, errore banca),
ALLORA la nota spese resta in stato "approvata — rimborso fallito", l'utente vede il motivo, e puo riprovare o segnare come "rimborsato manualmente".

**AC-30.5 — Edge Case: Auto-approvazione titolare**
DATO che il titolare e l'unico utente dell'azienda e inserisce una spesa,
QUANDO la nota spese viene creata,
ALLORA viene auto-approvata con log "auto-approvazione titolare unico" e procede direttamente alla registrazione contabile.

---

#### US-31: Cespiti — scheda cespite e ammortamento automatico
**Come** titolare di PMI, **voglio** che il sistema riconosca i beni strumentali e calcoli l'ammortamento, **in modo da** avere il registro cespiti aggiornato e le scritture corrette.

**Story Points:** 5 | **MoSCoW:** Could | **Versione:** v0.3 | **Deps:** US-13 | **Req. PRD:** G2

**Acceptance Criteria:**

**AC-31.1 — Happy Path: Creazione automatica scheda cespite**
DATO che registro una fattura per "MacBook Pro" (importo €2.500, categoria "Attrezzature informatiche"),
QUANDO l'importo supera la soglia cespiti (default €516,46 — configurabile),
ALLORA il sistema propone creazione scheda cespite con: descrizione, valore, categoria, aliquota ministeriale (20% per attrezzature informatiche), durata ammortamento (5 anni).

**AC-31.2 — Happy Path: Calcolo ammortamento annuale**
DATO che e fine esercizio e ci sono 3 cespiti attivi,
QUANDO il ContaAgent calcola gli ammortamenti,
ALLORA registra per ciascuno: DARE Ammortamento / AVERE Fondo ammortamento, con quote proporzionali se acquistato in corso d'anno.

**AC-31.3 — Error: Categoria non mappata**
DATO che il bene non corrisponde a nessuna categoria ministeriale nota,
QUANDO tenta la creazione automatica,
ALLORA propone le 3 categorie piu probabili e chiede conferma all'utente.

**AC-31.4 — Edge Case: Cespite usato (acquisto da privato)**
DATO che il bene e usato e la fattura non ha IVA (acquisto da privato),
QUANDO crea la scheda,
ALLORA non computa IVA a credito, e imposta valore cespite = importo lordo.

**AC-31.5 — Error: Fattura cumulativa con beni sopra e sotto soglia**
DATO che una fattura contiene 10 sedie a €100 (tot €1.000) e 1 monitor a €600,
QUANDO il sistema analizza le righe,
ALLORA propone cespite solo per il monitor (>€516,46), i beni sotto soglia vanno a costo diretto, e chiede conferma per eventuale raggruppamento dei beni fungibili.

---

#### US-32: Cespiti — registro e dismissione
**Come** titolare, **voglio** consultare il registro cespiti e registrare dismissioni/vendite, **in modo da** avere la situazione patrimoniale aggiornata.

**Story Points:** 3 | **MoSCoW:** Could | **Versione:** v0.3 | **Deps:** US-31 | **Req. PRD:** G2

**Acceptance Criteria:**

**AC-32.1 — Happy Path: Registro cespiti**
DATO che ho 8 cespiti attivi,
QUANDO accedo al registro,
ALLORA vedo lista con: descrizione, data acquisto, valore originale, fondo ammortamento, valore residuo, % ammortamento.

**AC-32.2 — Happy Path: Dismissione/vendita**
DATO che vendo il MacBook usato a €800 (valore residuo €1.000),
QUANDO registro la vendita,
ALLORA il sistema calcola minusvalenza (€200), registra le scritture di chiusura, e rimuove dal registro attivi.

**AC-32.3 — Error: Dismissione con ammortamento in corso d'anno**
DATO che vendo un cespite a luglio (meta esercizio),
QUANDO registro la vendita,
ALLORA il sistema calcola la quota ammortamento pro-rata (7/12) prima della dismissione, aggiorna il fondo, e poi registra plus/minusvalenza sul valore residuo aggiornato.

**AC-32.4 — Error: Vendita senza prezzo (rottamazione/furto)**
DATO che un cespite viene rottamato o rubato (prezzo vendita = €0),
QUANDO registro la dismissione con motivo "rottamazione" o "furto/smarrimento",
ALLORA il sistema registra la minusvalenza pari al valore residuo, rimuove dal registro attivi, e per il furto suggerisce "Verificare copertura assicurativa e denuncia".

**AC-32.5 — Edge Case: Cespite completamente ammortizzato**
DATO che un cespite ha valore residuo €0 ma e ancora in uso,
QUANDO consulto il registro,
ALLORA appare con stato "Ammortizzato — ancora in uso", nessuna nuova quota.

---

#### US-33: Ritenute d'acconto — riconoscimento e calcolo netto
**Come** titolare, **voglio** che il sistema riconosca le fatture con ritenuta d'acconto e calcoli l'importo netto da pagare, **in modo da** versare il giusto al fornitore e all'Erario.

**Story Points:** 5 | **MoSCoW:** Could | **Versione:** v0.3 | **Deps:** US-05, US-13 | **Req. PRD:** G3

**Acceptance Criteria:**

**AC-33.1 — Happy Path: Riconoscimento automatico da XML**
DATO che il Parser trova il campo <DatiRitenuta> nel FatturaPA XML,
QUANDO parsa la fattura,
ALLORA estrae: tipo ritenuta (RT01/RT02), aliquota (20%), importo, e calcola netto da pagare.

**AC-33.2 — Happy Path: Registrazione contabile con ritenuta**
DATO che la fattura ha ritenuta 20% su imponibile €1.000,
QUANDO il ContaAgent registra,
ALLORA: DARE 6110 Consulenze €1.000 + DARE 2212 IVA credito €220 / AVERE 4010 Fornitori €1.020 + AVERE 2310 Erario c/ritenute €200.

**AC-33.3 — Happy Path: Scadenza versamento ritenuta**
DATO che la fattura con ritenuta e stata registrata,
QUANDO il FiscoAgent calcola le scadenze,
ALLORA aggiunge scadenza nello scadenzario (codice tributo 1040, 16 del mese successivo al pagamento, importo €200). **Nota:** questa AC crea la SCADENZA; il DOCUMENTO F24 effettivo viene generato da US-38.

**AC-33.4 — Error: Fattura senza tag ritenuta ma da professionista**
DATO che la fattura e da un professionista (codice ATECO servizi) ma manca il tag <DatiRitenuta>,
QUANDO il sistema analizza,
ALLORA warning "Possibile ritenuta mancante — verificare con il fornitore".

---

#### US-34: Certificazione Unica (CU) annuale
**Come** sostituto d'imposta, **voglio** generare le Certificazioni Uniche a fine anno, **in modo da** adempiere all'obbligo di legge entro il 16 marzo.

**Story Points:** 5 | **MoSCoW:** Could | **Versione:** v0.4 | **Deps:** US-33 | **Req. PRD:** G4

**Acceptance Criteria:**

**AC-34.1 — Happy Path: Generazione CU**
DATO che nell'anno ho pagato 5 professionisti con ritenuta,
QUANDO clicco "Genera CU [anno]",
ALLORA genera per ciascuno: compensi lordi, ritenute versate, netto corrisposto, dati anagrafici.

**AC-34.2 — Happy Path: Export formato telematico**
DATO che le CU sono pronte,
QUANDO clicco "Esporta",
ALLORA genera file nel formato ministeriale per invio telematico (o CSV per il commercialista).

**AC-34.3 — Error: Ritenute non tutte versate**
DATO che 2 ritenute non risultano versate (F24 mancante),
QUANDO genera la CU,
ALLORA warning "Ritenute non versate per [fornitore] — verificare F24 prima dell'invio".

**AC-34.4 — Edge Case: Professionista con contributo INPS 4%**
DATO che il professionista applica rivalsa INPS 4%,
QUANDO genera la CU,
ALLORA il contributo e indicato separatamente come previsto dal modello CU.

---

#### US-35: Imposta di bollo automatica
**Come** libero professionista in regime forfettario, **voglio** che il sistema calcoli automaticamente l'imposta di bollo sulle fatture esenti, **in modo da** non dimenticare l'obbligo e il versamento trimestrale.

**Story Points:** 3 | **MoSCoW:** Could | **Versione:** v0.3 | **Deps:** US-21 | **Req. PRD:** G5

**Acceptance Criteria:**

**AC-35.1 — Happy Path: Rilevamento automatico obbligo bollo**
DATO che emetto una fattura esente IVA (art. 10, art. 15, forfettario) con importo >€77,16,
QUANDO genero il FatturaPA XML,
ALLORA il tag <BolloVirtuale>SI e <ImportoBollo>2.00 sono inseriti automaticamente.

**AC-35.2 — Happy Path: Conteggio e scadenza trimestrale**
DATO che nel Q1 ho emesso 15 fatture con bollo,
QUANDO il FiscoAgent calcola le scadenze,
ALLORA mostra "Bollo Q1: €30 (15 fatture x €2) — scadenza 31 maggio, F24 cod. tributo 2501".

**AC-35.3 — Error: Fattura sotto soglia ma esente**
DATO che emetto fattura esente da €50 (sotto €77,16),
QUANDO genera la fattura,
ALLORA NON applica il bollo (sotto soglia), nessun tag nel XML.

**AC-35.4 — Edge Case: Fattura mista (parte esente, parte imponibile)**
DATO che emetto una fattura con righe esenti (art. 15, €500) e righe con IVA 22% (€300),
QUANDO il sistema valuta l'obbligo di bollo,
ALLORA applica il bollo solo se la somma delle righe esenti supera €77,16, e lo indica nel tag XML con riferimento alle sole righe esenti.

**AC-35.5 — Happy Path: Rilevamento bollo su fatture passive ricevute**
DATO che ricevo una fattura esente IVA >€77,16 ma senza tag <BolloVirtuale>,
QUANDO il Parser Agent la analizza,
ALLORA warning "Fattura ricevuta senza bollo — il bollo e a carico del fornitore. Verificare conformita prima della registrazione".

---

#### US-36: Ratei e risconti di fine esercizio
**Come** titolare di SRL, **voglio** che il sistema proponga le scritture di assestamento a fine anno, **in modo da** avere il bilancio per competenza senza calcoli manuali.

**Story Points:** 5 | **MoSCoW:** Could | **Versione:** v0.3 | **Deps:** US-13 | **Req. PRD:** G6

**Acceptance Criteria:**

**AC-36.1 — Happy Path: Identificazione automatica costi pluriennali**
DATO che ho una fattura "Assicurazione RC annuale" di €1.200 pagata il 1/10,
QUANDO il sistema analizza a fine esercizio (31/12),
ALLORA propone risconto attivo: €900 (9 mesi di competenza anno successivo) con anteprima scrittura.

**AC-36.2 — Happy Path: Generazione scritture di assestamento**
DATO che confermo il risconto proposto,
QUANDO il ContaAgent registra,
ALLORA: DARE 1800 Risconti attivi €900 / AVERE 6400 Assicurazioni €900. Al 1/1 successivo, scrittura di riapertura inversa.

**AC-36.3 — Error: Importo non ripartibile**
DATO che la fattura non indica chiaramente il periodo di competenza,
QUANDO il sistema tenta la ripartizione,
ALLORA chiede all'utente: "Periodo di competenza? Da [data] a [data]" con suggerimento basato sulla descrizione.

**AC-36.4 — Edge Case: Rateo passivo (costo maturato non ancora fatturato)**
DATO che a fine anno devo al commercialista €3.000 per consulenza annuale ma non ha ancora fatturato,
QUANDO registro il rateo,
ALLORA: DARE 6110 Consulenze €3.000 / AVERE 2800 Ratei passivi €3.000. Si chiudera con la fattura effettiva.

---

#### US-37: Conservazione digitale a norma
**Come** titolare, **voglio** che le fatture siano conservate a norma per 10 anni, **in modo da** rispettare l'obbligo di legge senza pensarci.

**Story Points:** 5 | **MoSCoW:** Could | **Versione:** v0.4 | **Deps:** US-04 | **Req. PRD:** G8

**Acceptance Criteria:**

**AC-37.1 — Happy Path: Invio automatico a provider certificato**
DATO che una fattura e registrata,
QUANDO il processo di conservazione si attiva (batch giornaliero),
ALLORA il sistema invia il pacchetto di versamento (fattura XML + metadati) al provider certificato (Aruba/InfoCert) via API.

**AC-37.2 — Happy Path: Verifica stato conservazione**
DATO che accedo alla sezione "Conservazione",
QUANDO consulto lo stato,
ALLORA vedo: fatture conservate, in attesa, errori, con data ultimo lotto e certificato del provider.

**AC-37.3 — Error: Provider non raggiungibile**
DATO che il provider di conservazione e temporaneamente offline,
QUANDO il batch tenta l'invio,
ALLORA riprova con backoff, accoda le fatture, e notifica se il ritardo supera 48h.

**AC-37.4 — Error: Pacchetto rifiutato dal provider**
DATO che il provider rifiuta il pacchetto di versamento (metadati incompleti, hash non valido, formato errato),
QUANDO il sistema riceve il rifiuto via callback,
ALLORA marca le fatture del lotto come "conservazione rifiutata" con il motivo specifico, notifica l'utente, e accoda per rinvio dopo correzione automatica (se possibile) o manuale.

**AC-37.5 — Edge Case: Fattura rettificata dopo conservazione**
DATO che una nota di credito rettifica una fattura gia conservata,
QUANDO il sistema la rileva,
ALLORA invia anche la nota di credito al provider, collegata alla fattura originale.

---

#### US-38: F24 compilazione e generazione
**Come** titolare, **voglio** che ContaBot compili il modello F24 con i tributi dovuti, **in modo da** pagare senza errori di codice tributo o importo.

**Story Points:** 5 | **MoSCoW:** Could | **Versione:** v0.4 | **Deps:** US-22, US-33 | **Req. PRD:** G7

**Acceptance Criteria:**

**AC-38.1 — Happy Path: F24 da liquidazione IVA**
DATO che la liquidazione IVA Q1 indica €898 da versare,
QUANDO clicco "Genera F24",
ALLORA compila: sezione Erario, codice tributo 6031, periodo 01/2026-03/2026, importo €898. Esportabile PDF e formato telematico.

**AC-38.2 — Happy Path: F24 da ritenute d'acconto**
DATO che nel mese ho versato ritenute per €1.200 totali a 3 fornitori,
QUANDO genera F24 mensile,
ALLORA compila: codice tributo 1040, periodo mese/anno, importo €1.200.

**AC-38.3 — Error: Importo FiscoAPI diverso da stima interna**
DATO che FiscoAPI fornisce un importo F24 diverso dalla stima Odoo,
QUANDO il sistema confronta,
ALLORA mostra entrambi gli importi con evidenza della differenza e suggerisce "Verificare con il commercialista".

**AC-38.4 — Edge Case: Compensazione crediti**
DATO che ho un credito IVA di €500 dal trimestre precedente,
QUANDO genera l'F24,
ALLORA compila la sezione compensazione (codice tributo a credito + a debito), con netto da versare.

---

### EPIC 9: Cruscotto CEO (v0.4)

---

#### US-39: Dashboard CEO — cruscotto direzionale
**Come** CEO/titolare di PMI, **voglio** un cruscotto che mi dia la fotografia dell'azienda in un colpo d'occhio, **in modo da** prendere decisioni basate sui dati.

**Story Points:** 8 | **MoSCoW:** Could | **Versione:** v0.4 | **Deps:** US-13, US-14, US-24 | **Req. PRD:** C1

**Acceptance Criteria:**

**AC-39.1 — Happy Path: Cruscotto con KPI principali**
DATO che ho almeno 3 mesi di dati contabili,
QUANDO accedo al "Cruscotto CEO",
ALLORA vedo in una schermata: fatturato mese/YTD, EBITDA %, cash flow attuale, scadenze imminenti, top 5 clienti per fatturato, top 5 fornitori per costo.

**AC-39.2 — Happy Path: Confronto anno precedente**
DATO che ho dati dell'anno precedente,
QUANDO il cruscotto carica,
ALLORA ogni KPI mostra variazione % vs anno precedente con freccia su/giu e colore (verde/rosso).

**AC-39.3 — Happy Path: DSO e DPO**
DATO che ho fatture emesse e ricevute con date di pagamento,
QUANDO il sistema calcola,
ALLORA mostra DSO (tempo medio incasso) e DPO (tempo medio pagamento) con trend trimestrale.

**AC-39.4 — Error: Dati insufficienti**
DATO che ho meno di 1 mese di dati,
QUANDO accedo al cruscotto,
ALLORA mostra i dati disponibili con nota "Cruscotto completo dopo 3 mesi di utilizzo — attualmente [N] giorni di dati".

**AC-39.5 — Edge Case: Concentrazione clienti**
DATO che i top 3 clienti rappresentano >60% del fatturato,
QUANDO il cruscotto calcola,
ALLORA mostra alert "Rischio concentrazione: Top 3 clienti = [X]% del fatturato".

---

#### US-40: Dashboard CEO — KPI e budget vs consuntivo
**Come** CEO, **voglio** definire un budget annuale e confrontarlo mensilmente con il consuntivo, **in modo da** sapere se l'azienda e in linea con le previsioni.

**Story Points:** 8 | **MoSCoW:** Could | **Versione:** v0.4 | **Deps:** US-39 | **Req. PRD:** C1, C3

**Acceptance Criteria:**

**AC-40.1 — Happy Path: Inserimento budget**
DATO che inizio un nuovo anno,
QUANDO accedo a "Budget",
ALLORA posso inserire previsioni mensili per: ricavi, costi per categoria (personale, consulenze, affitti, marketing...), e il sistema calcola margine previsto.

**AC-40.2 — Happy Path: Confronto mensile**
DATO che e fine marzo e ho il budget,
QUANDO accedo al cruscotto budget,
ALLORA vedo per ogni voce: budget, consuntivo, delta (€ e %), con evidenziazione degli scostamenti significativi (>10%).

**AC-40.3 — Happy Path: Trend e proiezione**
DATO che ho 6 mesi di dati budget vs consuntivo,
QUANDO il sistema analizza il trend,
ALLORA mostra proiezione a fine anno: "Se il trend continua, fatturato annuo stimato €[X] vs budget €[Y] — delta [Z]%".

**AC-40.4 — Error: Budget non inserito**
DATO che non ho ancora definito il budget,
QUANDO accedo alla sezione,
ALLORA mostra wizard guidato: "Inserisci il budget in 5 minuti" con suggerimenti basati sui dati storici.

**AC-40.5 — Edge Case: Voce di costo non prevista a budget**
DATO che una nuova categoria di costo appare a consuntivo (es. "Penali"),
QUANDO il confronto non trova la voce nel budget,
ALLORA la evidenzia come "Non prevista" e suggerisce di aggiornare il budget.

---

## Riepilogo per Versione

### v0.1 — Must Have (12 stories, 69 SP)
US-01, US-02, US-03, US-04, US-05, US-10, US-11, US-12, US-13, US-14, US-15, US-16

### v0.2 — Should Have (7 stories, 32 SP)
US-06, US-07, US-08, US-09, US-17, US-18, US-19

### v0.3 — Could Have (14 stories, 79 SP)
US-20, US-21, US-22, US-23, US-24, US-25, US-26, US-29, US-30, US-31, US-32, US-33, US-35, US-36

### v0.4 — Could Have (7 stories, 44 SP)
US-27, US-28, US-34, US-37, US-38, US-39, US-40

---
_Aggiornato con analisi gap CEO — 2026-03-22_
