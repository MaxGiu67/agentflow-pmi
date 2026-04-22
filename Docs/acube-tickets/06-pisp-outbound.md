# Ticket 06 — PISP: Outbound Payment e Request to Pay

**Area:** Open Banking / PISP
**Priorità:** P2
**Oggetto:** [NexaData] PISP — attivazione Outbound Payment e Request to Pay

---

## Contesto

Il nostro contratto del 10/04/2026 copre **AISP** (Account Information Service Provider) per la lettura dei conti bancari.

Nella roadmap di AgentFlow PMI vogliamo aggiungere funzionalità di **pagamento in uscita** (bonifici SEPA, pagamento scadenze, F24) e di **Request to Pay** (richieste incasso verso clienti finali).

La documentazione pubblica (`/documentation/open-banking/outbound-payment` e `/documentation/open-banking/payment_require_process`) descrive i flussi a alto livello, ma serve chiarimento sul perimetro commerciale.

Priorità bassa — richiesta informativa per planning, non bloccante per lo sviluppo corrente.

---

## Richieste

### 1. Contratto

Per attivare **Outbound Payment** e **Request to Pay** serve:

- **a)** contratto PISP separato da stipulare?
- **b)** addendum al contratto AISP attuale?
- **c)** incluso nell'AISP attuale a un fee per transazione?

Ci potete inviare un'offerta commerciale indicativa?

### 2. Costi

Modelli di pricing PISP:

- Setup una tantum?
- Canone annuo fisso?
- Fee per transazione (€/operazione)?
- Fasce a volume?

### 3. Sistemi supportati

Confermate il supporto per:

- ✅ **Bonifico SEPA** standard (SCT)
- ❓ **SEPA Instant Credit Transfer (SCT Inst)** — molto utile per MVP B2B
- ❓ **F24** (pagamento contributi/tributi)
- ❓ **MAV / RAV**
- ❓ **Bollettini postali**
- ❓ **PagoPA**

### 4. Banche supportate

La lista ASPSP italiane supportate per PISP è la stessa di AISP o è ridotta?

### 5. Endpoint e payload

Per iniziare un Outbound Payment:

- Endpoint esatto (`POST /business-registry/{fiscalId}/payments`?)
- Body richiesto completo:
  - `debtor_account_uuid`?
  - `creditor_iban`?
  - `creditor_name`?
  - `amount`
  - `currency`
  - `reference` / `description` (causale)
  - `execution_date`?
  - `system` (`sepa` / `sepa_inst` / altro)?
- Esempio curl

Idem per Request to Pay.

### 6. Flusso SCA

La SCA è sempre **redirect-based** (URL ritornato → utente completa sulla propria banca) o esistono flussi alternativi (embedded, decoupled)?

### 7. Stati di Payment

Oltre a `accepted` e `failed` documentati, esistono stati intermedi:

- `pending`
- `processing`
- `scheduled`
- Altro?

### 8. Webhook delivery

Lo stesso webhook `Payment` documentato per AISP inbound funziona anche per outbound? Il campo `direction: "outbound"` è l'unico distintivo?

### 9. Limiti operativi

- Importo massimo singolo bonifico
- Frequenza consentita (N pagamenti/giorno)
- Cut-off orari per SEPA standard

### 10. Riconciliazione automatica

Quando un Outbound Payment viene eseguito, entra poi automaticamente come Transaction sul conto debitore (via AISP)? Con quale delay?

---

## Riferimenti

- Contratto attuale copre solo AISP
- Documentazione consultata:
  - https://docs.acubeapi.com/documentation/open-banking/outbound-payment
  - https://docs.acubeapi.com/documentation/open-banking/payment_require_process

Grazie,
Massimiliano Giurtelli — CTO Nexa Data
mgiurelli@taal.it
