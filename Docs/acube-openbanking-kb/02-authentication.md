# 02 — Autenticazione

**Fonte:** https://docs.acubeapi.com/documentation/common/authentication
**Ultimo aggiornamento docs:** 21 ottobre 2025

---

## Endpoint di Login

| Ambiente | URL |
|---|---|
| Produzione | `https://common.api.acubeapi.com/login` |
| Sandbox | `https://common-sandbox.api.acubeapi.com/login` |

## Payload richiesto

```json
{
  "email": "your@email.com",
  "password": "your password"
}
```

## Esempio cURL

```bash
curl -X POST https://common-sandbox.api.acubeapi.com/login \
  -H 'Accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{"email": "your@email.com", "password": "your password"}'
```

## Risposta

```json
{
  "token": "a very long encrypted token"
}
```

---

## Caratteristiche del Token JWT

- **Durata:** 24 ore
- **Struttura:** 3 parti separate da `.` (header.payload.signature)
- **Pratica consigliata:** "richiedere solo un token JWT ogni 24 ore"

## Decodifica JWT (parte 2 in base64)

```json
{
  "iat": <issue timestamp>,
  "exp": <expire timestamp>,
  "roles": {
    "<project name>": ["ROLE_WRITER", ...]
  },
  "username": <your email>,
  "uid": <your identifier>
}
```

## Utilizzo del Token

Header `Authorization` con prefisso `Bearer`:

```bash
curl -X GET https://common-sandbox.api.acubeapi.com/users/me \
  -H 'Accept: application/json' \
  -H 'Authorization: Bearer <token>'
```

⚠️ **Gotcha FAQ:** Il prefisso deve essere `bearer` (lowercase nelle FAQ, `Bearer` nel tutorial — capitalizzazione non chiara, probabilmente tollerante).

Formato esatto richiesto nelle FAQ:
```
Authorization: bearer JWT_TOKEN_HERE
```

---

## Implementazione AgentFlow — note

- **Cache token:** Redis con TTL 23h (margine sicurezza 1h rispetto alla scadenza 24h)
- **Key redis:** `acube:jwt:{environment}` (es. `acube:jwt:sandbox`, `acube:jwt:prod`)
- **Refresh:** background task che rinnova prima della scadenza
- **Fallback:** al primo errore 401, forzare refresh e retry una volta

## Domande aperte ❓

Queste informazioni NON sono presenti nei docs (vedi `99-open-questions.md`):
- Esiste un endpoint di refresh token o bisogna sempre rifare login?
- C'è rate limit sul `/login`?
- Esiste autenticazione alternativa (OAuth2 client_credentials / API key statica)?
- Come si gestisce rotazione password? Service account dedicati?
