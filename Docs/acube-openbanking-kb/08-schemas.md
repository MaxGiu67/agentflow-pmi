# 08 — Schemi dati completi

**Fonte:** OpenAPI spec estratto da `/openapi/open-banking-api.json`

---

## Account

### Account.AccountOutput

```typescript
{
  uuid: string (UUID)              // required
  fiscalId: string
  accountId: string                // ID esterno della banca
  providerName: string             // nome ASPSP
  name: string                     // nome conto
  nature: string                   // enum: account | card | loan | investment | ...
  balance: string (decimal)
  currencyCode: string
  enabled: boolean                 // required
  consentExpiresAt?: string (date-time)
  iban?: string
  bban?: string
  swift?: string
  extra?: object                   // variabile per banca
}
```

### Account.AccountInput (PUT)

```typescript
{
  enabled: boolean                 // required — toggle
}
```

### Account.ReconnectRequestOutput

```typescript
{
  uuid: string (UUID)              // required
  redirectUrl: string              // required — URL per SCA rinnovo
  state: string                    // required
}
```

---

## BusinessRegistry

### BusinessRegistry.BusinessRegistryOutput

```typescript
{
  fiscalId: string                 // required
  email: string                    // required — UNIVOCA per tutta la piattaforma!
  businessName: string             // required
  enabled: boolean                 // required
}
```

### BusinessRegistry.BusinessRegistryInputCreate (POST)

```typescript
{
  fiscalId: string                 // required — P.IVA/CF
  email: string                    // required
  businessName: string             // required
  enabled?: boolean                // default: false
}
```

⚠️ **Email deve essere univoca tra tutti i BR** — riuso email → errore "entity already exists".

### BusinessRegistry.BusinessRegistryInputUpdate (PUT)

```typescript
{
  businessName?: string            // modificabile
  enabled?: boolean                // toggle
}
```

**Nota:** email NON è modificabile dopo la creazione.

### BusinessRegistry.BusinessRegistrySubscriptionOutput

```typescript
{
  autoRenew: boolean               // required
  nextRenewalDate?: string (date-time)
}
```

### BusinessRegistry.BusinessRegistrySubscriptionInput

```typescript
{
  autoRenew: boolean               // required
}
```

### BusinessRegistry.BusinessRegistryBrandingOutput

```typescript
{
  primaryColor?: string            // hex color
  secondaryColor?: string          // hex color
  logoUrl?: string
}
```

### BusinessRegistry.BusinessRegistryBrandingInput

```typescript
{
  primaryColor?: string
  secondaryColor?: string
}
```

### BusinessRegistry.ImageOutput

```typescript
{
  url: string                      // required — URL logo
}
```

### BusinessRegistry.ImageInput

```typescript
{
  data: string                     // required — base64 encoded
}
```

### BusinessRegistry.BusinessRegistryUserInput

```typescript
{
  password: string                 // required — per sub-account
}
```

### BusinessRegistry.BusinessRegistryBankManagerInput

```typescript
{
  uuid: string (UUID)              // required — link BM esistente
}
```

---

## BankManager

### BankManager.BankManagerOutput

```typescript
{
  uuid: string (UUID)              // required
  email?: string
  name?: string
}
```

### BankManager.BankManagerCreateInput

```typescript
{
  email: string                    // required
  name?: string
}
```

### BankManager.BusinessRegistryOutput (nested)

```typescript
{
  fiscalId: string                 // required
  businessName: string             // required
}
```

---

## ConnectRequest

### ConnectRequest.ConnectRequestOutput

```typescript
{
  uuid: string (UUID)              // required
  redirectUrl: string              // required — URL SCA
  state: string                    // required
}
```

### ConnectRequest.ConnectRequestInput

```typescript
{
  bankManagerEmail?: string
  redirectUrl?: string             // URL di ritorno dopo SCA
  // Dal tutorial anche: locale (es. "en", "it")
}
```

---

## Transaction

### Transaction.TransactionOutput

```typescript
{
  id: string                       // required
  account: {
    uuid: string (UUID)            // reference
  }
  description?: string
  amount?: string (decimal)
  currency?: string
  madeOn: string (date)            // required
  updatedAt?: string (date-time)
  fetchedAt?: string (date-time)
  status: string                   // required — enum: pending | booked | canceled
  category?: string
  duplicated?: boolean
  counterparty?: string
  extra?: object                   // variabile per banca
}
```

---

## Payment

### Payment.PaymentOutput

```typescript
{
  id: string                       // required
  account: object                  // reference
  description?: string
  amount?: string (decimal)
  currency?: string
  createdAt: string (date-time)
  system: string                   // es. "sepa"
}
```

### Payment schema in webhook (più completo)

```typescript
{
  uuid: string (UUID)
  direction: "inbound" | "outbound"
  status: string                   // "accepted" | "failed" | ...
  system: string                   // "sepa" | ...
  amount: string (decimal)
  currencyCode: string
  description?: string
  endToEndId?: string
  createdAt: string (date-time)
  debtorProviderName?: string
  account: {
    uuid: string (UUID)
    name: string
    nature: string
    providerName: string
  }
}
```

---

## Category

### Category.CategoryOutput

```typescript
{
  id: string                       // required
  name: string                     // required
  icon?: string
}
```

---

## Enums principali

### Account.nature

Valori noti:
- `account`
- `card`
- `loan`
- `investment`
- ❓ altri non documentati

### Transaction.status

- `pending` — non ancora contabilizzata, ⚠️ **attributi instabili incluso id**
- `booked` — contabilizzata, stabile
- `canceled` — annullata

### Payment.direction

- `inbound` — ricevuto (Request to Pay)
- `outbound` — inviato (Outbound Payment)

### Payment.status (webhook)

- `accepted`
- `failed`
- ❓ `pending`, `processing` non documentati

### Payment.system

- `sepa`
- ❓ F24, MAV, RAV non documentati (probabilmente non supportati in AISP base)

### Webhook errorClass

Connect/Reconnect:
- `Timeout`
- `InvalidCredentials`
- `AccessDenied`
- `ProviderError`
- `GenericError`

Payment (aggiunge):
- `PaymentFailed`

---

## HTTP status codes

| Code | Uso tipico |
|---|---|
| 200 | OK |
| 201 | Created |
| 202 | Accepted (delete async) |
| 204 | No Content |
| 400 | Invalid input |
| 401 | Unauthorized — JWT |
| 402 | **Payment Required** — limiti sandbox / fattura non pagata |
| 404 | Not Found |
| 422 | Unprocessable Entity |
