# 04 — Webhooks (API Orchestration)

**Fonte:** https://docs.acubeapi.com/documentation/open-banking/api-orchestration

---

## Configurazione

I webhook possono essere gestiti tramite:
- **API** (endpoint non documentato pubblicamente)
- **Dashboard** → `https://dashboard.acubeapi.com/openbanking/webhooks`

Form dashboard chiede:
- `Evento` (Connect / Reconnect / Payment)
- `Target URL`
- `Authentication type` ❓ (valori supportati non documentati)
- `Authentication key` ❓
- `Authentication token` ❓

## Firma digitale

> "Una firma è inclusa in ogni chiamata" per verificare l'autenticità.

⚠️ **Non documentato pubblicamente:**
- Algoritmo (probabilmente HMAC-SHA256, ma da confermare)
- Nome dell'header che contiene la firma
- Payload canonico usato per il calcolo
- Come generare la chiave condivisa

---

## Evento 1 — Connect

Triggerato quando il consenso è stabilito o fallisce.

### Payload success

```json
{
  "fiscalId": "some_fiscal_id",
  "success": true,
  "updatedAccounts": [
    "aSampleAccountID-001",
    "aSampleAccountID-002",
    "aSampleAccountID-003"
  ]
}
```

### Payload error

```json
{
  "fiscalId": "some_fiscal_id",
  "success": false,
  "errorClass": "Timeout",
  "errorMessage": "Some error message"
}
```

### errorClass — valori possibili

- `Timeout`
- `InvalidCredentials`
- `AccessDenied`
- `ProviderError`
- `GenericError`

---

## Evento 2 — Reconnect

Invocato quando un Business Registry deve rinnovare il consenso in scadenza.

### Payload

```json
{
  "fiscalId": "some_fiscal_id",
  "connectUrl": "The URL to invoke to start the reconnection process",
  "providerName": "The name of the financial institution to renew consent for",
  "consentExpiresAt": "2031-01-01T00:00:00+00:00",
  "noticeLevel": 0
}
```

### noticeLevel — valori

| Valore | Significato |
|---|---|
| `0` | Scade tra 20 giorni |
| `1` | Scade tra 10 giorni |
| `2` | Scade in 0 giorni (oggi) |

⚠️ **Non documentato:** TTL del `connectUrl` — è valido una sola volta? Per N ore?

---

## Evento 3 — Payment

Progresso del processo di pagamento.

### Payload success

```json
{
  "fiscalId": "ABCD",
  "success": true,
  "payment": {
    "uuid": "11ce6377-ff28-4c7c-842f-ba500fb94759",
    "direction": "inbound",
    "status": "accepted",
    "system": "sepa",
    "amount": "345.67",
    "currencyCode": "EUR",
    "description": "Order nr. 12345",
    "endToEndId": "A+C000001",
    "createdAt": "2023-03-30T07:51:34Z",
    "debtorProviderName": "Mario Rossi",
    "account": {
      "uuid": "c83ea9a5-78aa-4bd8-9e9a-fe46827603f9",
      "name": "ABCD123",
      "nature": "account",
      "providerName": "Commercial Bank Institute"
    }
  }
}
```

### Payload error

```json
{
  "fiscalId": "ABCD",
  "success": false,
  "errorClass": "PaymentFailed",
  "errorMessage": "Payment cancelled",
  "payment": {
    "uuid": "11ce6377-ff28-4c7c-842f-ba500fb94759",
    "direction": "inbound",
    "status": "failed",
    "system": "sepa",
    "amount": "345.67",
    "currencyCode": "EUR",
    "description": "Order nr. 12345",
    "endToEndId": "A+C000001",
    "createdAt": "2023-03-30T07:51:34Z",
    "debtorProviderName": "Mario Rossi",
    "account": {
      "uuid": "c83ea9a5-78aa-4bd8-9e9a-fe46827603f9",
      "name": "ABCD123",
      "nature": "account",
      "providerName": "Commercial Bank Institute"
    }
  }
}
```

### Payment errorClass — valori

- `Timeout`
- `InvalidCredentials`
- `AccessDenied`
- `ProviderError`
- `PaymentFailed` ← nuovo rispetto a Connect
- `GenericError`

### Payment status — valori osservati

- `accepted` (success)
- `failed` (error)
- ❓ altri: `pending`? `processing`? non documentati

### Payment direction

- `inbound` (richiesta pagamento ricevuta / Request to Pay)
- `outbound` (bonifico uscita / Outbound Payment)

### Payment system

- `sepa` (SEPA credit transfer)
- ❓ altri sistemi non documentati (F24? MAV? RAV?)

---

## Obbligatorietà

Dalle FAQ: **"Webhooks can be really useful to receive notifications in an async way, but they are not mandatory in order to use Open Banking APIs."**

AgentFlow può lavorare solo con **polling** finché non abbiamo i webhook in produzione.

---

## Implementazione AgentFlow — consigli

| Webhook | Endpoint AgentFlow | Azione |
|---|---|---|
| Connect success | `POST /api/v1/webhooks/acube/connect` | Avvia sync accounts + sync transactions iniziale |
| Connect error | stesso | Notifica utente + log errore |
| Reconnect | `POST /api/v1/webhooks/acube/reconnect` | Invia email Brevo + banner app con `connectUrl` |
| Payment | `POST /api/v1/webhooks/acube/payment` | Aggiorna stato pagamento in DB + notifica utente |

## Domande aperte ❓

- Algoritmo firma (HMAC-SHA256? altro?)
- Nome header firma (`X-Acube-Signature`? altro?)
- Payload canonico (raw body? body+timestamp?)
- Retry policy in caso di 5xx dal nostro endpoint
- Disabilitazione automatica dopo N fallimenti
- IP da whitelistare
- Testing: possibile triggerare webhook fittizi dalla dashboard?
