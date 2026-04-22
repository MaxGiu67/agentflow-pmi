# 09 — FAQ + Gotchas

**Fonte:** https://docs.acubeapi.com/documentation/open-banking/faq

---

## FAQ pubbliche (verbatim)

### Q: È obbligatorio configurare i webhook?

> "Webhooks can be really useful to receive notifications in an async way, but they are not mandatory in order to use Open Banking APIs."

**Implicazione AgentFlow:** possiamo partire in polling, attivare webhook dopo.

---

### Q: Ho il token dall'API di auth ma non riesco a usare l'OB API

Il prefisso `bearer` deve essere presente:

```
Authorization: bearer JWT_TOKEN_HERE
```

**Implicazione:** case-sensitivity da verificare (probabilmente tollerante).

---

### Q: Non riesco a scaricare più di 30 record

> "A common mistake is to forget that our APIs are paginated, returning 30 records by default."

**Implicazione AgentFlow:** sempre usare `itemsPerPage=100` + loop su `page` o Hydra `hydra:next`.

---

### Q: Ho passato il connect ma non riesco a leggere i dati

Due cause:
1. **Consenso GDPR non accettato** durante il processo
2. **Account non esplicitamente abilitato**

**Implicazione:** istruire l'utente a completare entrambi i passaggi nel portale durante SCA. Verificare `account.enabled == true` prima di leggere.

---

### Q: Errore "entity already exists" creando nuovo Business Registry

> "You can't use the same email for different Business Registries."

**Implicazione AgentFlow:** serve generatore email univoche per BR. Opzioni:
- Email alias del tipo `tenant-{fiscalId}@nexadata.it`
- Email cliente finale (se disponibile)
- Email generata `br-{uuid}@agentflow.taal.it`

---

## Gotchas non-FAQ (dai docs)

### Pending transactions instabili

> "Pending transactions should be deleted on each call since their attributes, including id, can vary."

**Implicazione AgentFlow:** pattern idempotente — prima del fetch `DELETE FROM transactions WHERE status='pending' AND account_uuid=?`, poi re-insert.

### Default mese corrente

Transactions e Payments ritornano solo mese corrente se `madeOn` / `createdAt` non esplicitati.

**Implicazione:** per storico o per job di sync periodico, sempre passare intervallo date.

### Account disabilitato = dati cancellati

Disabilitando un account → balance, extra e transazioni **vengono cancellate**.

**Implicazione:** se serve storico post-disable, archiviare in DB nostro prima.

### Fee su POST /business-registry

> "Creates a new Business Registry (a fee will be charged)"

**Implicazione:** NON creare BR in test senza controllo. In sandbox forse gratis (da verificare).

### Enable/disable BR impatta fatturazione

- `/enable` → "fee charged"
- `/disable` → ferma lettura

**Implicazione:** usare disable per clienti AgentFlow che disattivano abbonamento temporaneamente, senza perdere la configurazione.

### Sub-account limitato

> "Sub-account: accesso limitato a dati della Business Registry assegnata"

**Implicazione:** se mai volessimo dare accesso dashboard A-Cube al cliente finale, usare sub-account (ma preferiamo modalità trasparente).

### Bank Manager auto-creato

> "Bank Manager creato automaticamente alla prima connessione se non esiste"

**Implicazione:** in genere non dobbiamo creare BM manualmente. Se serve customizzazione branding → usare `POST /bank-managers` + link.

### Reconnect 90 giorni

> "Reconnessione necessaria dopo 90 giorni per rinnovare consenso accesso dati"

**Implicazione:** webhook Reconnect arriva a 20/10/0 giorni dalla scadenza → workflow email/banner cliente.

---

## Errori HTTP da gestire

| Code | Caso | Azione AgentFlow |
|---|---|---|
| 401 | JWT scaduto | Refresh token + retry 1 volta |
| 402 | Sandbox limiti / fattura non pagata | Alert admin + bloccare chiamate |
| 404 | BR/Account non esistente | Log + segnalazione utente |
| 422 | Validazione fallita | Log dettagliato + correzione client-side |

---

## Best practice operative

1. **Header standard AgentFlow:**
   ```
   Content-Type: application/json
   Accept: application/ld+json          # per Hydra pagination
   Authorization: Bearer <jwt>
   ```

2. **Client HTTP timeout:** 30s (SCA banche può essere lento)

3. **Retry:** exponential backoff su 5xx, NO retry su 4xx (tranne 401 con refresh)

4. **Logging:** mai loggare JWT in chiaro

5. **Rate limiting:** non documentato ❓ — precauzionalmente max 10 req/s
