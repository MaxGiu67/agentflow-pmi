# 06 — Payments (Outbound + Request to Pay)

**Fonti:**
- https://docs.acubeapi.com/documentation/open-banking/outbound-payment
- https://docs.acubeapi.com/documentation/open-banking/payment_require_process

---

## Payments — Lista per Business Registry

```
GET /business-registry/{fiscalId}/payments
```

**Query params:**

| Parametro | Tipo | Note |
|---|---|---|
| `page`, `itemsPerPage` | int | paginazione standard |
| `account.uuid` | string | filtro per conto |
| `account.uuid[]` | array | multipli |
| `system` | string | es. `sepa` |
| `system[]` | array | multipli |
| `createdAt[before]` | datetime | |
| `createdAt[strictly_before]` | datetime | |
| `createdAt[after]` | datetime | |
| `createdAt[strictly_after]` | datetime | |

⚠️ **Default:** se `createdAt` non impostato, restituisce solo pagamenti del **mese corrente**.

---

## Schema Payment

```typescript
{
  uuid: string (UUID)
  direction: "inbound" | "outbound"
  status: string                   // enum: accepted | failed | ...
  system: string                   // enum: sepa | ...
  amount: string (decimal)
  currencyCode: string             // es. "EUR"
  description?: string             // causale
  endToEndId?: string              // identificativo E2E
  createdAt: string (date-time)
  debtorProviderName?: string      // nome debitore (se inbound)
  account: {
    uuid: string (UUID)
    name: string
    nature: string
    providerName: string
  }
}
```

---

## Outbound Payment (Bonifico in uscita)

### Flusso 9 step

1. L'End User registrato richiede l'avvio del pagamento
2. Software Integrator invia `POST` a endpoint "Start a payment"
3. A-Cube risponde con un URL
4. Integrator comunica URL all'End User
5. End User clicca → reindirizzato alla banca
6. Processo continua sul sito banca (SCA)
7. Successo → debitore vede pagina riepilogo pagamento
8. Reindirizzato al `returnUrl` opzionale
9. A-Cube chiama webhook `Payment` con payload success

### Endpoint

❓ Non chiaramente documentato nel dettaglio, ma riferimento in docs: `/documentation/api/openbanking/post-receive-sepa-payment` (probabilmente per Request to Pay).

Per Outbound: verosimilmente `POST /business-registry/{fiscalId}/payments` con body specifico — **da verificare con A-Cube** (vedi `99-open-questions.md`).

---

## Request to Pay (Richiesta pagamento — inbound)

### Flusso 8 step

1. End User registrato avvia processo Request to Pay
2. Integrator invia `POST` a endpoint "Start Request to Pay"
3. A-Cube fornisce URL
4. **End User condivide URL con il debitore (NON registrato)**
5. Debitore accede e sceglie la propria banca
6. Processo continua sul sito banca
7. Successo → pagina riepilogo per debitore
8. A-Cube attiva webhook `Payment` con payload success

### Caratteristica chiave

Il **debitore non deve essere registrato in A-Cube** — riceve solo un URL condiviso dal creditore (End User).

### Endpoint

`POST /documentation/api/openbanking/post-receive-sepa-payment`

Schema body ❓ non documentato nel dettaglio pubblico.

---

## Contratto attuale NexaData

⚠️ Il contratto A-Cube firmato 10/04/2026 copre **solo AISP** (Account Information Service Provider).

Per PISP (Payment Initiation Service Provider) — cioè Outbound Payment e Request to Pay — probabilmente serve **contratto separato**. Da chiarire con A-Cube.

---

## Domande aperte ❓

- Endpoint esatto per Outbound Payment (POST come path?)
- Body completo Start Payment (IBAN destinatario, causale, importo, data valuta?)
- Body Request to Pay
- F24, MAV, RAV supportati oltre a SEPA?
- Flusso SCA interna (embedded vs redirect)
- Stati di payment non documentati (`pending`, `processing`?)
- Costi PISP vs AISP
- Tempi settlement SEPA Instant vs Standard
