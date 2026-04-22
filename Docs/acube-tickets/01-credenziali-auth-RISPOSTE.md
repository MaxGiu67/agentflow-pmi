# Ticket 01 — Risposte A-Cube

**Ricevute:** 2026-04-20
**Canale:** Helpdesk dashboard
**Status:** ✅ CHIUSO

---

## Sintesi risposte

### 1. Credenziali sandbox Open Banking
❌ **Nessun account sandbox esistente** associato a nexadata.
➡️ **Azione:** auto-registrazione tramite form pubblico → https://www.acubeapi.com/#form-onboarding

### 2. Credenziali produzione
✅ **Account produzione già esistente** (probabilmente legacy da ADR-004/adapter SDI stub).
A-Cube chiarisce che "credenziali" = **JWT token** ottenuto via `POST /login`, non chiavi statiche.
Rif: https://docs.acubeapi.com/documentation/common/authentication

### 3. Metodo auth server-to-server
❌ **Nessuna alternativa disponibile**.
L'**unico metodo supportato** è JWT via `POST /login` con email + password.
Niente OAuth2 client_credentials, niente API key statica, niente service account.

➡️ **Implicazione architetturale:** dobbiamo trattare email+password come "credenziali di massima sensibilità" → vault criptato AES256, rotazione password manuale, zero logging.

### 4. Refresh token
❌ **Nessun endpoint di refresh**.
Per rinnovare il JWT occorre **rifare `POST /login`** ogni 24h.

### 5. Rotazione password + rate limit
- **Rotazione password**: scelta nostra (nessuna policy A-Cube imposta).
- **Frequenza token**: **"1 JWT token every 24 hours"** (best practice citata da A-Cube stessa dalla docs).
- **Rate limit su /login**: non indicato → assumiamo conservativo (max 10 req/min per sicurezza).

---

## Decisioni architetturali conseguenti

| Punto | Decisione |
|---|---|
| Storage credenziali | Env var `ACUBE_LOGIN_EMAIL` + `ACUBE_LOGIN_PASSWORD_ENCRYPTED` (criptata AES256 con `AES_KEY` già presente) |
| Token caching | Redis key `acube:jwt:{env}` TTL 23h |
| Refresh strategy | Background task Celery `refresh_acube_token` ogni 23h |
| Fallback 401 | Invalidate cache + 1 retry login + se fallisce → alert admin |
| Rotazione password | Manuale via env var update + restart — no schedule automatico |
| Rate limit lock | Redis distributed lock su `/login` (max 1 concorrente) |

**Queste decisioni sono coerenti con quanto già scritto in US-OB-01 e US-OB-02** del Pivot 11 sprint plan — no modifiche necessarie.
