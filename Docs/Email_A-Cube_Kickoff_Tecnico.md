# Email kick-off tecnico ad A-Cube (versione lean)

**A:** (indirizzo account manager A-Cube / apertura ticket via dashboard `https://dashboard.acubeapi.com` → Helpdesk)
**Da:** mgiurelli@taal.it
**Oggetto:** [NexaData – AgentFlow] Integrazione AISP + Scarico Massivo — quesiti tecnici residui

---

Gentile team A-Cube,

a seguito della firma del contratto del **10/04/2026** (rif. Offerta NexaData – Open Banking AISP + Scarico Massivo Fatture), stiamo avviando l'integrazione tecnica della vostra API nella nostra piattaforma SaaS **AgentFlow PMI**.

Abbiamo studiato in dettaglio la documentazione pubblica (`docs.acubeapi.com/documentation/open-banking/` + OpenAPI spec + PDF "Procedura di delega/incarico") e la maggior parte dei dubbi è stata chiarita. Ci rimangono alcune domande tecniche residue, per poter scrivere codice "al primo colpo" senza procedere per tentativi.

---

## 1. Credenziali e autenticazione

1. **Credenziali sandbox già emesse?** Se sì, a quale indirizzo? Se no, potete emetterle per `mgiurelli@nexadata.it`?
2. **Credenziali produzione**: qual è la procedura per l'emissione delle credenziali prod? Tempistica?
3. Oltre al flusso documentato `POST /login` con email+password → JWT 24h, esiste un metodo di autenticazione **alternativo pensato per integrazioni server-to-server**?
   - OAuth2 `client_credentials` con `client_id` / `client_secret`?
   - API key statica via header?
   - Service account dedicato?
   Per un SaaS come il nostro, mantenere email+password in config non è il pattern ideale.
4. Esiste un endpoint di **refresh token** o ad ogni rotazione occorre rifare `/login`?
5. **Rotazione password**: frequenza raccomandata? Esiste notifica pre-scadenza?
6. **Rate limit su `/login`**: quale valore?

## 2. Webhook — sicurezza e affidabilità

Nel dashboard `/openbanking/webhooks` il form di creazione webhook chiede `Authentication type`, `Authentication key`, `Authentication token`.

1. **Quali valori supporta il dropdown "Authentication type"**? (es. None, Basic, Bearer, HMAC, Custom header)
2. La documentazione `api-orchestration` dice "A signature is included in each call". Dettagli:
   - **Algoritmo** (HMAC-SHA256? SHA512?)
   - **Nome header** contenente la firma (`X-Acube-Signature`? altro?)
   - **Payload canonico** usato per il calcolo (body raw? body + timestamp? body + URL?)
   - **Chiave segreta**: la generiamo noi o la fornite voi? Come la otteniamo?
3. **Retry policy** in caso di risposta non-2xx dal nostro endpoint: quanti tentativi, con che backoff?
4. Dopo quanti fallimenti il webhook viene **disabilitato automaticamente**?
5. **IP allow-list**: da quali IP/subnet partono le vostre chiamate webhook? (necessario per whitelist firewall).
6. È possibile **triggerare manualmente** un evento di test verso il nostro endpoint dalla dashboard, per validare la firma in fase di sviluppo?

## 3. Gestione clienti finali

Abbiamo **4 clienti attivi** (PMI italiane) che useranno AgentFlow. Ciascuno ha la propria P.IVA. Vorremmo mappare **1 Business Registry A-Cube = 1 cliente finale**.

1. La creazione programmatica tramite `POST /business-registry` comporta "a fee will be charged" (da docs). In **sandbox** questa fee è simulata/gratuita o reale?
2. L'endpoint `POST /business-registry/{fiscalId}/user` crea un **sub-account** utente. Per il nostro caso d'uso (il cliente resta solo su AgentFlow e noi leggiamo i dati via API per suo conto) dobbiamo **evitare** di creare sub-account, giusto? Ci confermate che la modalità "trasparente" è pienamente supportata?
3. Passaggio fascia 51-100 P.IVA: cambio di pricing **automatico** o richiede modifica contrattuale preventiva (email / PEC)?
4. Esiste un **endpoint API** per conoscere in tempo reale: N Business Registry creati, fascia di pricing attiva, N fatture scaricate anno corrente (per il servizio Scarico Massivo)? Vorremmo esporlo in una dashboard interna per evitare di superare le soglie contrattuali (50 clienti + 5.000 fatture/anno).

## 4. Open Banking — dettagli pratici

1. **Limiti sandbox**: quando si scatena l'errore `402 Payment Required` citato in docs? Ci sono quote su N Business Registry / N Account / N Transactions? Possiamo avere i valori esatti?
2. **Lista banche italiane supportate** aggiornata: copriamo correttamente Intesa Sanpaolo, Unicredit, BNL, Fineco, BPM, Credem, Monte dei Paschi, BCC, BPER, Poste Italiane?
3. **Storico transazioni** al primo consenso: quanti mesi/giorni indietro è possibile scaricare? Dipende dalla banca?
4. **TTL del `connectUrl`** restituito dal webhook `Reconnect`: è valido una sola volta? Per N ore?
5. Campo `extra` delle Transaction: dai docs "varies by institution". Esiste una **guida di normalizzazione** per le principali banche italiane o ogni banca richiede un parser dedicato?
6. **CRO / TRN / reference pagamento** (fondamentale per riconciliazione automatica con fatture): in quale campo è esposto? `description`? `extra.cro`? Altro?
7. **Frequenza sync banca → A-Cube**: quando la banca contabilizza un nuovo movimento, entro quanto è disponibile via API? Esiste un **webhook per nuovo movimento** oltre agli eventi documentati (Connect/Reconnect/Payment)?
8. **Tassonomia `GET /categories`**: standard MCC o proprietaria?

## 5. Pagamenti in uscita (PISP)

Il nostro contratto attuale copre **AISP**. Vorremmo capire:

1. Per attivare **Outbound Payment** e **Request to Pay** (endpoint `/payments`) serve un contratto PISP separato? Quali costi aggiuntivi?
2. Endpoint esatto per avviare Outbound Payment e body richiesto: i docs illustrano il flusso a 9 step ma non il payload. Potete fornire esempio curl?
3. Oltre a SEPA, sono supportati **F24 / MAV / RAV** / **bollettini postali**?
4. **SEPA Instant Credit Transfer (SCT Inst)** supportato?

## 6. Scarico Massivo Fatture (Cassetto Fiscale)

Come indicato in contratto, la sandbox non è ancora disponibile e "è possibile organizzare una call tecnica".

1. Possiamo **prenotare la call tecnica**? Proponiamo alcuni slot nelle prossime 2 settimane.
2. Argomenti che vorremmo coprire:
   - Endpoint completi scarico massivo e formato response (array URL XML? base64 embedded?)
   - **Backfill iniziale**: quanti mesi indietro è possibile recuperare?
   - Frequenza polling consigliata (oraria? giornaliera?)
   - Gestione **duplicati** (filtrato lato A-Cube o dobbiamo gestire noi via progressivo SDI?)
   - **Rate limit** specifico
   - Webhook per nuove fatture disponibili? (in caso positivo: payload esempio)
   - Gestione errori "delega scaduta" / "credenziali Fisconline invalide" (modalità incarico): notifica webhook o polling errore?
   - Timeline rilascio **Corrispettivi 2026** da parte dell'AdE
   - Differenze operative tra le 3 modalità di onboarding (credenziali dirette, incaricato, proxy A-Cube) — quale raccomandate per SaaS multi-cliente come il nostro?

## 7. Supporto e operations

1. Abbiamo attivato solo il supporto base (best-effort). Qual è il **tempo medio di risposta** osservato nel supporto best-effort? Dato necessario per valutare upgrade a prioritario.
2. Esiste una **status page pubblica** con incidents / maintenance windows?
3. Esiste un **forum pubblico** o community? (menzionato nel menu dashboard)
4. In caso di issue P1 bloccante fuori dagli orari lavorativi, esiste un canale di escalation?

---

Rimaniamo a disposizione per qualsiasi chiarimento. Grazie per l'attenzione — aspettiamo il vostro riscontro per chiudere questi punti e partire con la fase implementativa.

Cordiali saluti,

**Massimiliano Giurtelli**
CTO — NexaData S.r.l.
mgiurelli@taal.it
