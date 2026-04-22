# 03 — Connection Process (Consenso PSD2)

**Fonte:** https://docs.acubeapi.com/documentation/open-banking/connection_process
**Ultimo aggiornamento docs:** 22 dicembre 2025

---

## Prerequisito

Prima di iniziare il processo l'End User deve essere già registrato come **Business Registry**.

---

## Flusso completo (9 step)

1. L'End User richiede i servizi Open Banking
2. Il Software Integrator invia `POST /business-registry/{fiscalId}/connect`
3. L'API A-Cube risponde con un URL
4. L'End User clicca su questo URL
5. Il link reindirizza a una pagina dove **scegliere la banca**
6. Il processo continua sul sito della banca (SCA, login, autorizzazione)
7. Se autenticazione OK, l'End User è reindirizzato a una pagina dove **selezionare gli account** da usare con OB API
8. Una pagina finale informa del completamento
9. A-Cube chiama il webhook `Connect` con payload di successo
   > Nota: il webhook **non è obbligatorio**. È a discrezione del Software Integrator se configurarlo.

---

## Tutorial step-by-step completo

Dal tutorial `/documentation/open-banking/transactions`:

### Step 1 — Login (JWT)

```bash
curl --request POST https://common-sandbox.api.acubeapi.com/login \
  -H 'Content-Type: application/json' -H 'Accept: application/json' \
  --data-raw '{"email": "my@email.test", "password": "myPassword"}'
```

### Step 2 — Creare Business Registry

```bash
curl --request POST https://ob-sandbox.api.acubeapi.com/business-registry \
  -H 'Content-Type: application/json' -H 'Accept: application/json' \
  -H "Authorization: bearer JWT_TOKEN_HERE" \
  --data-raw '{
    "fiscalId": "SOME_ID",
    "email": "some@email.test",
    "businessName": "Some Name"
  }'
```

⚠️ **Fee:** "Creates a new Business Registry (**a fee will be charged**)" — da `putBusinessRegistryItem`

### Step 3 — Avviare Connect Request

```bash
curl --request POST https://ob-sandbox.api.acubeapi.com/business-registry/SOME_ID/connect \
  -H 'Content-Type: application/json' -H 'Accept: application/json' \
  -H "Authorization: bearer JWT_TOKEN_HERE" \
  --data-raw '{"locale": "en"}'
```

**Note importanti:**
- ⚠️ Durante il processo utente deve **spuntare consenso GDPR**
- ⚠️ L'utente deve **esplicitamente abilitare ciascun account** desiderato
- Se non si abilita un account, le sue transazioni non sono leggibili

### Step 4 — Recuperare gli Accounts

```bash
curl --request GET \
  https://ob-sandbox.api.acubeapi.com/business-registry/SOME_ID/accounts \
  -H 'Content-Type: application/json' -H 'Accept: application/json' \
  -H "Authorization: bearer JWT_TOKEN_HERE"
```

### Step 5 — Recuperare le Transactions

```bash
curl --request GET \
  https://ob-sandbox.api.acubeapi.com/business-registry/SOME_ID/transactions \
  -H 'Content-Type: application/json' -H 'Accept: application/json' \
  -H "Authorization: bearer JWT_TOKEN_HERE"
```

---

## Schema ConnectRequest

### Input (body POST /business-registry/{fiscalId}/connect)

| Campo | Tipo | Obbligatorio | Note |
|---|---|---|---|
| `redirectUrl` | string URI | ⚠️ non chiaro se obbligatorio | URL di ritorno dopo SCA |
| `bankManagerEmail` | string | opzionale | Associazione Bank Manager |
| `locale` | string | opzionale | es. `en`, `it` |
| `language` | string | opzionale | alternativa a locale |

### Output (risposta 201)

| Campo | Tipo | Note |
|---|---|---|
| `uuid` | string UUID | ID della request |
| `redirectUrl` | string | URL verso cui far andare l'utente per SCA |
| `state` | string | Stato iniziale |

---

## Durata consenso

⚠️ Dai docs API Reference: **"Reconnessione necessaria dopo 90 giorni per rinnovare consenso accesso dati"**.

Questo rispetta lo standard PSD2 italiano/EU (90 giorni).

---

## Reconnect

Quando il consenso sta per scadere, A-Cube invia un webhook `Reconnect` (vedi `04-webhooks.md`) con:
- `connectUrl` — link per far rinnovare l'utente
- `noticeLevel` — 0 (20gg), 1 (10gg), 2 (0gg = oggi)

Alternativa via API: `GET /accounts/{uuid}/reconnect` → avvia processo riconnessione.

---

## Gotchas

| Problema | Causa | Soluzione |
|---|---|---|
| `"entity already exists"` su create BR | Email già usata | Ogni BR deve avere email univoca |
| Transazioni non leggibili dopo connect | GDPR non accettato o account non abilitato esplicitamente | Verificare abilitazione per ciascun account nel portale A-Cube |
| `pending` transactions cambiano ID | Comportamento normale PSD2 | Eliminarle ad ogni fetch e ricrearle |
