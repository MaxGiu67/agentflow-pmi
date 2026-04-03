---
tipo: concept
progetto: agentflow-pmi
data: 2026-04-03
stack: brevo, python, fastapi, webhook
confidenza: alta
tags: brevo, sendinblue, email, api, webhook, tracking, open, click, bounce
---

# Brevo API — Email invio e tracking via webhook

## API Base
- Endpoint: `https://api.brevo.com/v3/`
- Auth: header `api-key: xkeysib-xxxxx`
- Documentazione: https://developers.brevo.com/reference

## Invio email transazionale

```python
POST /v3/smtp/email
{
    "sender": {"name": "NExadata", "email": "commerciale@nexadata.it"},
    "to": [{"email": "cliente@example.com", "name": "Mario Rossi"}],
    "subject": "Proposta progetto {{deal_name}}",
    "htmlContent": "<html><body>Gentile {{nome}},...</body></html>",
    "params": {"nome": "Mario", "deal_name": "SAP Migration"},
    "tags": ["proposal", "deal-123"]
}
```

Response: `{"messageId": "<202604031234.abc123@smtp-relay.brevo.com>"}`

## Webhook eventi

Configurazione: Dashboard Brevo → Transactional → Webhooks → Add URL

| Evento | Payload chiave |
|--------|---------------|
| delivered | {event: "delivered", messageId, date, email} |
| opened | {event: "opened", messageId, date, email, ip, tag} |
| click | {event: "click", messageId, date, email, link, ip, tag} |
| hardBounce | {event: "hard_bounce", messageId, date, email, reason} |
| softBounce | {event: "soft_bounce", messageId, date, email, reason} |
| unsubscribed | {event: "unsubscribed", messageId, date, email} |
| complaint | {event: "spam", messageId, date, email} |

## Sicurezza webhook
- Brevo non supporta HMAC nativamente sugli SMTP webhook
- Soluzione: verifica IP sorgente (range Brevo) + secret nel URL path
- Es: `POST /api/v1/email/webhook/{secret}`

## Rate limits
- Piano Starter (25 EUR/mese): 20.000 email/mese, 400/ora
- Piano Business: 100.000 email/mese, nessun rate limit orario
- API: 400 req/min per default

## Template con variabili
- Variabili in doppia graffa: `{{nome}}`, `{{azienda}}`
- Passate nel campo `params` dell'API call
- Brevo sostituisce lato server prima dell'invio

## Python adapter pattern

```python
import httpx

class BrevoClient:
    def __init__(self, api_key: str):
        self.client = httpx.AsyncClient(
            base_url="https://api.brevo.com/v3",
            headers={"api-key": api_key, "Content-Type": "application/json"},
        )

    async def send_email(self, to_email, to_name, subject, html, params=None, tags=None):
        resp = await self.client.post("/smtp/email", json={
            "sender": {"name": "NExadata", "email": "commerciale@nexadata.it"},
            "to": [{"email": to_email, "name": to_name}],
            "subject": subject,
            "htmlContent": html,
            "params": params or {},
            "tags": tags or [],
        })
        resp.raise_for_status()
        return resp.json()["messageId"]
```

## Applicazione
ADR-009: Brevo usato per email marketing in AgentFlow PMI. Adapter: api/adapters/brevo.py
