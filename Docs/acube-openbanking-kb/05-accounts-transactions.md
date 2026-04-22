# 05 — Accounts + Transactions

**Fonte:** OpenAPI spec + `/documentation/open-banking/transactions`

---

## Accounts

### Lista account per Business Registry

```
GET /business-registry/{fiscalId}/accounts
```

**Query params:**
- `page` (default: 1)
- `itemsPerPage` (default: 30, max: 100)
- `enabled` (boolean) — filtra solo abilitati
- `iban` (string)
- `iban[]` (array)

### Dettaglio account

```
GET /accounts/{uuid}
```

### Enable / Disable account

```
PUT /accounts/{uuid}
Body: { "enabled": true | false }
```

⚠️ **Account disabilitato:** Cancella balance, extra data e transazioni.

### Reconnect account specifico

```
GET /accounts/{uuid}/reconnect
```

Avvia processo riconnessione (restituisce `redirectUrl` + `uuid` + `state`).

### Elimina account

```
DELETE /accounts/{uuid}
```

---

## Schema Account

```typescript
{
  uuid: string (UUID)              // required
  fiscalId: string                 // P.IVA del BR proprietario
  accountId: string                // ID esterno banca
  providerName: string             // Nome banca (es. "Intesa Sanpaolo")
  name: string                     // Nome account (spesso "Conto Corrente")
  nature: string                   // enum: account | card | loan | investment | ...
  balance: string (decimal)        // saldo corrente
  currencyCode: string             // es. "EUR"
  enabled: boolean                 // required
  consentExpiresAt?: string        // ISO datetime - scadenza consenso PSD2
  iban?: string                    // opzionale (solo conti)
  bban?: string                    // opzionale
  swift?: string                   // opzionale
  extra?: object                   // banca-specific, non normalizzato
}
```

⚠️ I campi opzionali **non compaiono** nella response se assenti.

---

## Transactions

### Lista transazioni per Business Registry

```
GET /business-registry/{fiscalId}/transactions
```

**Query params completi:**

| Parametro | Tipo | Note |
|---|---|---|
| `page` | int | default 1 |
| `itemsPerPage` | int | default 30, max 100 |
| `account.uuid` | string | filtro per conto |
| `account.uuid[]` | array | multipli conti |
| `duplicated` | bool | filtra duplicate |
| `status` | string | pending/booked/canceled |
| `status[]` | array | multipli |
| `category` | string | categoria movimento |
| `category[]` | array | multipli |
| `madeOn[before]` | date | entro data (inclusivo) |
| `madeOn[strictly_before]` | date | prima data (esclusivo) |
| `madeOn[after]` | date | da data (inclusivo) |
| `madeOn[strictly_after]` | date | dopo data (esclusivo) |
| `updatedAt[before]` | datetime | |
| `updatedAt[strictly_before]` | datetime | |
| `updatedAt[after]` | datetime | |
| `updatedAt[strictly_after]` | datetime | |
| `fetchedAt[before]` | datetime | |
| `fetchedAt[strictly_before]` | datetime | |
| `fetchedAt[after]` | datetime | |
| `fetchedAt[strictly_after]` | datetime | |

### ⚠️ Default trappola

> "Se i filtri `madeOn` o `updatedAt` non sono esplicitamente impostati, l'API restituisce solo transazioni del mese corrente"

**Implicazione:** per il backfill iniziale storico, **bisogna sempre passare `madeOn[strictly_after]=YYYY-MM-DD`** altrimenti perdiamo tutto il pregresso.

### Dettaglio singola transazione

```
GET /business-registry/{fiscalId}/transactions/{transactionId}
```

---

## Schema Transaction

```typescript
{
  id: string                       // required
  account: {
    uuid: string (UUID)            // required
  }
  description?: string             // causale movimento
  amount?: string (decimal)        // importo (positivo = entrata, negativo = uscita)
  currency?: string                // es. "EUR"
  madeOn: string (date)            // required - data operazione
  updatedAt?: string (date-time)   // quando A-Cube ha visto update
  fetchedAt?: string (date-time)   // quando A-Cube ha scaricato da banca
  status: string                   // required - pending | booked | canceled
  category?: string                // categoria (vedi /categories)
  duplicated?: boolean             // flag duplicato
  counterparty?: string            // controparte (nome)
  extra?: object                   // varia per banca, non normalizzato
}
```

---

## Gotchas Transazioni

| Problema | Dettaglio | Soluzione |
|---|---|---|
| **Pending instabili** | Le transazioni `pending` possono cambiare attributi (incluso `id`!) ad ogni chiamata | Eliminarle ad ogni fetch e ricrearle da zero |
| **Default mese corrente** | Senza filtri `madeOn` restituisce solo mese corrente | Sempre esplicitare `madeOn[after]` |
| **30 record default** | Primi 30 movimenti, il resto va paginato | Loop su `page` finché `hydra:view.next` presente |
| **Campo `extra` non normalizzato** | Dipende dall'istituto | Parser per banca (Intesa, Unicredit, Fineco, ecc.) |
| **CRO/TRN non standardizzato** | ❓ probabilmente in `extra` o `description` | Regex per estrazione |

---

## Categories

```
GET /categories
```

**Query params:**
- `page`, `itemsPerPage`

### Schema Category

```typescript
{
  id: string       // required
  name: string     // required - nome leggibile
  icon?: string    // icona associata
}
```

❓ Tassonomia proprietaria o standard MCC — non documentato.

---

## Hydra pagination (application/ld+json)

Richiedendo header `Accept: application/ld+json`, la risposta include metadati:

```json
{
  "hydra:member": [...],           // array risultati
  "hydra:totalItems": 1523,        // totale filtrato
  "hydra:view": {
    "@id": "/...?page=2",
    "hydra:first": "/...?page=1",
    "hydra:last": "/...?page=51",
    "hydra:next": "/...?page=3",
    "hydra:previous": "/...?page=1"
  },
  "hydra:search": {...}            // filtri applicati
}
```

Useful per **loop paginazione** robusto.

---

## Pattern backfill iniziale — AgentFlow

```python
# Pseudo-codice
from datetime import date, timedelta

async def backfill_account(fiscal_id: str, account_uuid: str):
    today = date.today()
    start = today - timedelta(days=730)  # 2 anni (PSD2 max 90gg ma varia)
    page = 1
    while True:
        resp = await acube.get(
            f"/business-registry/{fiscal_id}/transactions",
            params={
                "account.uuid": account_uuid,
                "madeOn[after]": start.isoformat(),
                "page": page,
                "itemsPerPage": 100,
            },
            headers={"Accept": "application/ld+json"},
        )
        data = resp.json()
        for tx in data["hydra:member"]:
            upsert_transaction(tx)
        if "hydra:next" not in data.get("hydra:view", {}):
            break
        page += 1
```
