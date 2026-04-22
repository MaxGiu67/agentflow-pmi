# 01 — Overview + Ambienti

**Fonte:** https://docs.acubeapi.com/documentation/open-banking/
**Ultimo aggiornamento docs:** 15 gennaio 2026

---

## Cosa è

Open Banking API A-Cube fornisce un modo per connettersi alle istituzioni finanziarie tramite i canali **PSD2**. Consente di:
- interrogare conti finanziari (saldo, IBAN, movimenti)
- avviare pagamenti (outbound + request to pay)

## Attori coinvolti

| Attore | Ruolo |
|---|---|
| **End User** | Proprietario dei conti finanziari (cliente finale della PMI) |
| **Software Integrator** | Consumatore dell'API (noi, AgentFlow) |
| **A-Cube** | Fornitore dell'API |
| **Istituzione Finanziaria / Banca** | Ospita i conti dell'End User (ASPSP) |

---

## Ambienti

### Sandbox

- **Login URL:** `https://common-sandbox.api.acubeapi.com/login`
- **OB URL:** `https://ob-sandbox.api.acubeapi.com`
- **Caratteristiche:**
  - Connessioni simulate **e reali**
  - Supporta codice paese fittizio **`XF`** per connessioni simulate
  - Ha **limiti massimi** su conti e pagamenti
  - ⚠️ Superare i limiti → HTTP `402 Payment Required`

### Production

- **Login URL:** `https://common.api.acubeapi.com/login`
- **OB URL:** `https://ob.api.acubeapi.com`
- **Caratteristiche:**
  - Comunicazione **reale** con le istituzioni finanziarie
  - Richiede Business Registry reali con P.IVA valide

---

## Directory dei link principali

Dalla sidebar del portale documentazione:

| Sezione | URL |
|---|---|
| Open Banking API (home) | `/documentation/open-banking/` |
| How to retrieve Financial Transactions | `/documentation/open-banking/transactions` |
| The connection process | `/documentation/open-banking/connection_process` |
| API orchestration - Webhooks | `/documentation/open-banking/api-orchestration` |
| The Request to Pay process | `/documentation/open-banking/payment_require_process` |
| Outbound Payment process | `/documentation/open-banking/outbound-payment` |
| Frequently Asked Questions | `/documentation/open-banking/faq` |
| API Reference | `/documentation/api/openbanking/open-banking-rest-api` |
| Autenticazione (common) | `/documentation/common/authentication` |

---

## Blocchi logici del sistema

```
┌─────────────────────────────────────────────────────┐
│  Account A-Cube (email + password)                  │
│  └─ JWT 24h tramite POST /login                     │
│                                                     │
│  Business Registry (1 per P.IVA cliente finale)    │
│  ├─ email univoca                                   │
│  ├─ businessName                                    │
│  ├─ fiscalId (P.IVA)                                │
│  ├─ enabled (controlla fatturazione)                │
│  └─ autoRenew subscription                          │
│       │                                             │
│       ├─ Accounts (conti bancari PSD2)              │
│       │  ├─ uuid, IBAN, BBAN, providerName          │
│       │  ├─ balance, currency                       │
│       │  ├─ consentExpiresAt                        │
│       │  ├─ nature (account/card/loan/invest)       │
│       │  └─ enabled                                 │
│       │       │                                     │
│       │       └─ Transactions                       │
│       │          ├─ id, account.uuid                │
│       │          ├─ amount, currency, madeOn        │
│       │          ├─ status (pending/booked/cancel)  │
│       │          ├─ category, counterparty          │
│       │          ├─ duplicated flag                 │
│       │          └─ extra (banca-specific)          │
│       │                                             │
│       ├─ Payments (outbound/inbound)                │
│       ├─ BankManagers (sub-entità gestione banche)  │
│       ├─ Branding (logo + colori)                   │
│       └─ User sub-accounts (accesso dashboard)      │
└─────────────────────────────────────────────────────┘
```
