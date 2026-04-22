# 07 — API Reference completa

**Fonti:**
- https://docs.acubeapi.com/documentation/api/openbanking/open-banking-rest-api
- https://docs.acubeapi.com/openapi/open-banking-api.json

---

## Servers

| URL | Ambiente |
|---|---|
| `https://ob-sandbox.api.acubeapi.com` | Sandbox |
| `https://ob.api.acubeapi.com` | Production |

---

## Tags (raggruppamenti)

- **Account** — operazioni su conti bancari
- **BankManager** — gestione responsabili bancari
- **BusinessRegistry** — gestione registri aziendali
- **ConnectRequest** — richieste di connessione
- **Payment** — operazioni di pagamento
- **Transaction** — operazioni su transazioni
- **Category** — categorie di transazioni

---

## Endpoint — Account

| Metodo | Path | Operation ID | Note |
|---|---|---|---|
| GET | `/accounts/{uuid}` | `getAccountItem` | Dettaglio account |
| PUT | `/accounts/{uuid}` | `putAccountItem` | Enable/Disable — body `{"enabled": bool}` |
| DELETE | `/accounts/{uuid}` | `deleteAccountItem` | Elimina account |
| GET | `/accounts/{uuid}/reconnect` | `reconnectAccountItem` | Avvia riconnessione |
| GET | `/business-registry/{fiscalId}/accounts` | `getAccountCollection` | Lista account per BR |

**Query params su `getAccountCollection`:**
- `page`, `itemsPerPage`
- `enabled` (boolean)
- `iban` (string) / `iban[]` (array)

---

## Endpoint — Business Registry

| Metodo | Path | Operation ID | Note |
|---|---|---|---|
| GET | `/business-registry` | `getBusinessRegistryCollection` | Lista BR |
| POST | `/business-registry` | `postBusinessRegistryItem` | ⚠️ **a fee will be charged** |
| GET | `/business-registry/{fiscalId}` | `getBusinessRegistryItem` | Dettaglio |
| PUT | `/business-registry/{fiscalId}` | `putBusinessRegistryItem` | Update (excluded email) |
| DELETE | `/business-registry/{fiscalId}` | `deleteBusinessRegistryItem` | Rimozione |
| GET | `/business-registry/{fiscalId}/bank-managers` | `getBusinessRegistryBankManagersCollection` | Lista BM linkati |
| POST | `/business-registry/{fiscalId}/bank-managers` | `postBankManagerBusinessRegistryItem` | Link BM |
| GET | `/business-registry/{fiscalId}/branding` | `getBusinessRegistryBranding` | Branding colori |
| PUT | `/business-registry/{fiscalId}/branding` | `putBusinessRegistryBranding` | Update branding |
| GET | `/business-registry/{fiscalId}/branding/logo` | `getBusinessRegistryBrandingLogo` | URL logo |
| PUT | `/business-registry/{fiscalId}/branding/logo` | `putBusinessRegistryBrandingLogo` | Upload logo (base64) |
| POST | `/business-registry/{fiscalId}/connect` | `postConnectRequest` | Avvia connect PSD2 |
| POST | `/business-registry/{fiscalId}/disable` | `postBusinessRegistryDisable` | ⚠️ Disabilita lettura (impact fees) |
| POST | `/business-registry/{fiscalId}/enable` | `postBusinessRegistryEnable` | ⚠️ Abilita lettura (fee charged) |
| GET | `/business-registry/{fiscalId}/subscription` | `getBusinessRegistrySubscription` | Stato auto-renew |
| PUT | `/business-registry/{fiscalId}/subscription` | `putBusinessRegistrySubscription` | Enable/disable auto-renew |
| POST | `/business-registry/{fiscalId}/user` | `postBusinessRegistryUser` | Crea sub-account |
| DELETE | `/business-registry/{fiscalId}/user` | `deleteBusinessRegistryUser` | Rimuove sub-account |

---

## Endpoint — Bank Manager

| Metodo | Path | Operation ID | Note |
|---|---|---|---|
| GET | `/bank-managers` | `getBankManagerCollection` | Lista BM |
| POST | `/bank-managers` | `postBankManagerItem` | Crea BM |
| GET | `/bank-managers/{uuid}` | `getBankManager` | Dettaglio |
| GET | `/bank-managers/{uuid}/business-registries` | `getBankManagerBusinessRegistriesCollection` | BR linkati al BM |

Note: "Bank Manager creato automaticamente alla prima connessione se non esiste."

---

## Endpoint — Transaction

| Metodo | Path | Operation ID | Note |
|---|---|---|---|
| GET | `/business-registry/{fiscalId}/transactions` | `getTransactionCollection` | Lista movimenti |
| GET | `/business-registry/{fiscalId}/transactions/{transactionId}` | `getTransactionItem` | Dettaglio |

**Query params getTransactionCollection:** vedi `05-accounts-transactions.md`

---

## Endpoint — Payment

| Metodo | Path | Operation ID | Note |
|---|---|---|---|
| GET | `/business-registry/{fiscalId}/payments` | `getPaymentCollection` | Lista pagamenti |

❓ POST per avviare pagamenti non completamente documentato pubblicamente.

---

## Endpoint — Category

| Metodo | Path | Operation ID | Note |
|---|---|---|---|
| GET | `/categories` | `getCategoryCollection` | Lista categorie |

---

## Convenzioni globali

### Paginazione
- `page` (default: 1)
- `itemsPerPage` (default: 30, **max: 100**)
- Response con header `Accept: application/ld+json` include metadati Hydra

### Filtraggio multiplo
- `parametro[]=A&parametro[]=B` → OR logico

### Filtraggio date
- `campo[before]` — ≤
- `campo[strictly_before]` — <
- `campo[after]` — ≥
- `campo[strictly_after]` — >

### Autenticazione
- Header `Authorization: Bearer <JWT>`
- JWT ottenuto via `POST /login` su `common[-sandbox].api.acubeapi.com`

### Content-Type
- Request: `application/json`
- Response standard: `application/json`
- Response con paginazione Hydra: `application/ld+json` (opt-in)

### Codici errore comuni
- `200` — OK
- `201` — Created
- `202` — Accepted (delete account)
- `204` — No Content (delete BR)
- `400` — Invalid input
- `401` — Unauthorized (JWT mancante/scaduto)
- `402` — **Payment Required** (superati limiti sandbox o fattura non pagata)
- `404` — Not Found
- `422` — Unprocessable Entity (validazione fallita)

---

## Fee-related endpoints

Questi endpoint **generano fatturazione** (impatto costi):

| Endpoint | Quando fattura |
|---|---|
| `POST /business-registry` | Creazione nuovo registro |
| `POST /business-registry/{fiscalId}/enable` | Riabilitazione dopo disable |

Endpoint per **risparmiare costi** (mettere in pausa):

| Endpoint | Effetto |
|---|---|
| `POST /business-registry/{fiscalId}/disable` | Stop lettura dati — ferma fatturazione |
| `PUT /business-registry/{fiscalId}/subscription` | Disabilita auto-renew |
