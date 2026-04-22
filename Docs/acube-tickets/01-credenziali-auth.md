# Ticket 01 — Credenziali sandbox + auth server-to-server

**Area:** Platform / Account
**Priorità:** P0
**Oggetto:** [NexaData] Credenziali sandbox OB + auth server-to-server

---

## Contesto

Contratto firmato il **10/04/2026** per AISP + Scarico Massivo Fatture (Ref. offerta NexaData, firmata da Gennaro Vallo).

Stiamo iniziando l'integrazione tecnica della vostra API in AgentFlow PMI e abbiamo bisogno di sbloccare due punti operativi prima di scrivere codice.

---

## Richieste

### 1. Credenziali sandbox Open Banking

Potete confermare/emettere le credenziali per:
- Login su `https://common-sandbox.api.acubeapi.com/login`
- Email tecnica referente: `mgiurelli@nexadata.it`

Se già emesse, a quale indirizzo? Se no, potete emetterle?

### 2. Credenziali produzione

Procedura e tempistica per l'emissione delle credenziali prod (`https://common.api.acubeapi.com/login`).

### 3. Metodo auth server-to-server

La vostra documentazione pubblica descrive `POST /login` con **email + password** → JWT 24h.

Per un'integrazione SaaS backend-to-backend come la nostra, mantenere email+password in config non è un pattern ideale. Esistono alternative?

- OAuth2 `client_credentials` (`client_id` + `client_secret`)?
- API key statica via header?
- Service account dedicato?

### 4. Refresh token

Esiste un endpoint di refresh, o ad ogni rotazione di sicurezza occorre rifare `POST /login` ex novo?

### 5. Rotazione password + rate limit

- Frequenza raccomandata rotazione password account A-Cube
- Rate limit su `POST /login` (per dimensionare retry / lock)

---

## Riferimenti

- Contratto: Offerta NexaData firmata 10/04/2026
- Documentazione consultata: https://docs.acubeapi.com/documentation/common/authentication

Grazie,
Massimiliano Giurtelli — CTO Nexa Data
mgiurelli@taal.it
