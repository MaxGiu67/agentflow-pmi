# Ticket 05 — Open Banking: webhook sicurezza e affidabilità

**Area:** Open Banking / Security
**Priorità:** P1
**Oggetto:** [NexaData] Webhook Open Banking — firma HMAC, retry policy, IP allow-list

---

## Contesto

Stiamo per implementare gli endpoint di ricezione dei webhook Open Banking (Connect, Reconnect, Payment) nella nostra piattaforma AgentFlow PMI.

Accedendo alla dashboard (`https://dashboard.acubeapi.com/openbanking/webhooks`) vediamo il form di creazione webhook con campi `Authentication type`, `Authentication key`, `Authentication token`, ma senza spiegazione.

La documentazione pubblica (`/open-banking/api-orchestration`) dice *"A signature is included in each call"* ma non dettaglia come verificarla.

Per un servizio finanziario **questi dettagli sono bloccanti** per andare in produzione in modo sicuro.

---

## Richieste

### 1. Authentication type — valori supportati

Nel form di creazione webhook in dashboard, il dropdown `Authentication type` quali valori accetta?

- `None`
- `Basic`
- `Bearer`
- `HMAC`
- `Custom header`
- Altri?

### 2. Firma — specifica tecnica

Per ogni `Authentication type`:

- **Algoritmo** usato (HMAC-SHA256? SHA512? altro?)
- **Nome header HTTP** che contiene la firma (`X-Acube-Signature`? `X-Signature`? altro?)
- **Payload canonico** usato per il calcolo:
  - Body raw?
  - Body + timestamp?
  - Body + URL?
  - Format esatto della stringa da firmare
- **Chiave segreta**:
  - La generiamo noi lato nostro e la inseriamo nel form?
  - La generate voi e la esponete nella dashboard?
  - Dove la recuperiamo?

### 3. Esempio verificato

Potete fornire un **esempio concreto**:

- Payload body (JSON)
- Valore firma inclusa nell'header
- Snippet codice (Python / Node) che riproduce il calcolo della firma a partire dal body + chiave

Questo ci permette di implementare e testare la verifica al primo colpo.

### 4. Retry policy

Quando il nostro endpoint risponde con codice non-2xx (o timeout):

- Quanti tentativi di retry?
- Intervallo backoff (lineare? esponenziale? quali valori?)
- Dopo quanti fallimenti consecutivi il webhook viene **disabilitato automaticamente**?
- Riceviamo notifica email/dashboard della disabilitazione?

### 5. Timeout lato vostro

Qual è il timeout HTTP con cui chiamate il nostro endpoint?
Ci serve per dimensionare il nostro processing: rispondere 200 OK velocemente e processare asincrono (code Celery), oppure processing sincrono possibile?

### 6. IP allow-list

Da quali IP / subnet partono le vostre chiamate webhook?

- Lista statica fissa?
- Cambia periodicamente?
- Ci potete fornire per whitelistare firewall-side?

### 7. Test webhook dalla dashboard

È possibile **triggerare manualmente un evento di test** dalla dashboard verso il nostro endpoint, per validare la firma in fase di sviluppo?

Se sì, come si fa? Ogni evento (Connect/Reconnect/Payment) è testabile?

### 8. Ordine di delivery

In caso di eventi multipli rapidi (es. Connect + transazione immediata), i webhook arrivano in ordine cronologico garantito o possono arrivare disordinati?

### 9. Idempotency

Esiste un **event ID univoco** nel payload webhook per permetterci di implementare idempotency (evitare doppio processing in caso di retry)? Oppure dobbiamo ricavarlo da `fiscalId + timestamp + type`?

---

## Riferimenti

- Documentazione consultata: https://docs.acubeapi.com/documentation/open-banking/api-orchestration
- Screenshot form dashboard webhook (disponibile su richiesta)

Grazie,
Massimiliano Giurtelli — CTO Nexa Data
mgiurelli@taal.it
