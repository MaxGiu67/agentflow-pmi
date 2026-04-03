---
tipo: pattern
progetto: agentflow-pmi
data: 2026-04-03
stack: python, fastapi, brevo, webhook
confidenza: alta
tags: email, tracking, webhook, open-tracking, click-tracking, bounce, brevo, pattern
---

# Pattern: Email tracking via webhook (non costruire l'infrastruttura)

## Problema
Servono email tracking (apertura, click, bounce, unsubscribe) per campagne commerciali. Costruire l'infrastruttura SMTP con IP reputati, SPF/DKIM/DMARC, pixel tracking e link wrapping e un investimento di mesi e richiede manutenzione continua.

## Soluzione
Separare **logica** (tua) da **infrastruttura** (servizio esterno):

```
Tuo codice (logica)                 Servizio email (infrastruttura)
┌─────────────────────┐             ┌─────────────────────┐
│ Template engine     │             │ SMTP con IP reputati│
│ Sequenze workflow   │──── API ───▶│ Pixel tracking      │
│ Trigger su eventi   │             │ Link wrapping       │
│ Analytics dashboard │◀── Hook ────│ Bounce handling     │
│ A/B split logic     │             │ SPF/DKIM/DMARC      │
└─────────────────────┘             └─────────────────────┘
```

**Tu costruisci:** template, workflow, trigger, analytics, A/B logic
**Il servizio fa:** invio, tracking pixel, link redirect, bounce, deliverability

## Webhook eventi tipici

| Evento | Trigger | Dati utili |
|--------|---------|-----------|
| `delivered` | Email consegnata al server destinatario | message_id, timestamp |
| `opened` | Destinatario apre l'email (pixel 1x1 caricato) | message_id, timestamp, IP, user_agent |
| `clicked` | Destinatario clicca un link | message_id, url, timestamp |
| `hard_bounce` | Indirizzo non esiste | message_id, email, reason |
| `soft_bounce` | Mailbox piena / server temporaneamente down | message_id, email, reason |
| `unsubscribed` | Destinatario clicca unsubscribe | message_id, email |
| `spam` | Destinatario segna come spam | message_id, email |

## Servizi compatibili

| Servizio | Costo | Webhook | Note |
|----------|-------|---------|------|
| Brevo | 25 EUR/mo (20K) | Si, tutti gli eventi | UI italiana, GDPR EU |
| Resend | $20/mo (50K) | Si | Developer-first |
| Amazon SES | ~$1/10K | Si (via SNS) | Setup complesso |
| Postmark | $15/mo (10K) | Si | Deliverability top |

## Modello DB consigliato

```sql
-- Singoli invii tracciati
email_sends (id, campaign_id, contact_id, template_id, brevo_message_id, sent_at, status)

-- Eventi webhook
email_events (id, send_id, event_type, url_clicked, ip_address, user_agent, timestamp)
```

## Anti-pattern
- NON costruire il tuo SMTP server
- NON gestire IP reputation internamente
- NON implementare pixel tracking con immagini sul tuo server (i mail client li bloccano)
- NON fare link wrapping manuale (problemi con HTTPS, redirect, encoding)

## Applicazione in AgentFlow PMI
ADR-009: Brevo come servizio email, logica campagne interna. Costo 300 EUR/anno.
