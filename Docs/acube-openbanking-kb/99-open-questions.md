# 99 — Open Questions (domande non coperte dai docs)

Punti **non documentati** pubblicamente o documentati in modo incompleto.
Da chiarire con A-Cube **prima di iniziare lo sviluppo** (vedi `Docs/Email_A-Cube_Kickoff_Tecnico.md`).

---

## 🔑 Autenticazione e credenziali — ✅ CHIUSO 2026-04-20

- [x] ~~Credenziali sandbox già emesse~~ → **No**, auto-registrazione via https://www.acubeapi.com/#form-onboarding
- [x] ~~Credenziali produzione~~ → **Già disponibili** (account legacy)
- [x] ~~Auth alternativa~~ → **Solo JWT via email+password**, nessuna alternativa
- [x] ~~Refresh token~~ → **No endpoint dedicato**, rifare `POST /login`
- [x] ~~Rotazione password~~ → **Up to us**, nessuna policy A-Cube
- [x] ~~Service account~~ → **Non disponibile**
- [ ] Rate limit su `/login`? (non indicato — assumiamo 10 req/min conservativo)
- [ ] Ambienti intermedi (staging/pre-prod)? (non chiesto nel ticket)

## 🛡️ Webhook — sicurezza

- [ ] Quali valori supportati per **"Authentication type"** nel form dashboard (Bearer / Basic / HMAC / Custom / None)?
- [ ] Se HMAC: **algoritmo** usato (SHA256? SHA512?)
- [ ] Nome **header** contenente la firma (`X-Acube-Signature`? altro?)
- [ ] **Payload canonico** per calcolo firma (body raw? body+timestamp? altro?)
- [ ] Chiave segreta: la generiamo noi o A-Cube?
- [ ] **Retry policy** in caso di risposta non-2xx (quanti tentativi, backoff)
- [ ] Dopo quanti fallimenti webhook disabilitato automaticamente?
- [ ] **IP allow-list** da cui partono le chiamate webhook
- [ ] Possibile **trigger manuale** da dashboard per test firma?

## 🏢 Business Registry — multi-cliente

- [ ] Conferma creazione programmatica di **N BR** via `POST /business-registry` (fino a 50 per fascia base contrattuale)
- [ ] Passaggio fascia 51-100 **automatico** o contrattuale?
- [ ] Endpoint API per conoscere **consumo corrente** (N BR creati, fascia attiva, fatture scaricate anno corrente)?
- [ ] Sub-account utente — scopo esatto: dashboard access o altro?
- [ ] **Fee creazione BR** in sandbox è gratuita o no?

## 🔗 Consenso PSD2

- [ ] Durata consenso — confermato 90 giorni? Varia per banca?
- [ ] **TTL del `connectUrl`** di Reconnect (valido una volta? N ore?)
- [ ] **Storico transazioni** al primo consent: quanti mesi indietro max?
- [ ] **Lista banche italiane** supportate aggiornata (Intesa, Unicredit, BNL, Fineco, BPM, Credem, MPS, BCC)?

## 💸 Transazioni pratiche

- [ ] **Normalizzazione `extra`**: guida ufficiale per banca o parser custom?
- [ ] Frequenza aggiornamento **sync banca → A-Cube** (minuti? ore?)
- [ ] Esiste webhook per **nuovo movimento** (oltre a Connect/Reconnect/Payment)?
- [ ] **CRO / TRN / reference pagamento** — dove esposto (in `extra`? `description`?)?
- [ ] **Categorizzazione `/categories`** — tassonomia MCC standard o proprietaria?

## 💳 Pagamenti (PISP)

- [ ] Contratto AISP attuale include **PISP** o richiede addendum?
- [ ] Costi PISP aggiuntivi
- [ ] Endpoint esatto **Outbound Payment** (path, body completo)
- [ ] Endpoint **Request to Pay**
- [ ] Supportati **F24 / MAV / RAV** oltre a SEPA?
- [ ] **SEPA Instant** (SCT Inst) supportato?
- [ ] Flusso SCA embedded o solo redirect?
- [ ] Stati Payment non documentati (`pending`, `processing`)?

## 📄 Scarico Massivo Cassetto Fiscale

- [ ] **Call tecnica** — date disponibili?
- [ ] Lista endpoint completa e formato response
- [ ] Sandbox ETA
- [ ] Frequenza polling consigliata
- [ ] Profondità backfill iniziale
- [ ] Gestione duplicati lato A-Cube
- [ ] Rate limit specifico
- [ ] Webhook per nuove fatture disponibili?
- [ ] **Corrispettivi 2026** — timeline rilascio AdE

## 📊 Observability e monitoring

- [ ] **Rate limit** generali OB API
- [ ] **Status page pubblica** con incidents?
- [ ] Endpoint **health check** pubblico?

---

## ⚠️ Ambiguità da risolvere leggendo più in dettaglio

Elementi che potrebbero essere documentati ma non ho trovato:
- Endpoint `POST /business-registry/{fiscalId}/payments` per outbound
- Schema completo ConnectRequest body (redirectUrl obbligatorio?)
- Campo `counterparty` quando popolato
- Relazione Transaction ↔ Category (category `name` o `id`?)
