# User Stories — Pivot 10: Metering, Rate Limiting, Integrazioni UI

> Data: 2026-04-04
> Causa: Predisposizione per 3 tenant reali — serve controllo consumi

---

### US-113: Contatore LLM tokens per tenant
**Come** admin piattaforma
**Voglio** tracciare i token LLM consumati da ogni tenant
**Per** controllare i costi OpenAI e prevenire abusi

**AC-113.1**: Modello `TenantUsage` con campi: tenant_id, month, llm_tokens_in, llm_tokens_out, llm_requests, pdf_pages
**AC-113.2**: Dopo ogni chiamata OpenAI, incrementa contatori del tenant
**AC-113.3**: Quota configurabile per tenant: `llm_quota_monthly` (default 100.000 token)
**AC-113.4**: Se quota superata, chatbot risponde "Quota AI raggiunta — contatta l'amministratore"
**AC-113.5**: Reset automatico contatori a inizio mese

**SP**: 3 | **Priorita**: Must Have

---

### US-114: Rate limit API per tenant
**Come** admin piattaforma
**Voglio** limitare il numero di richieste API per tenant
**Per** proteggere l'infrastruttura da abusi

**AC-114.1**: Middleware rate limit basato su tenant_id (non IP)
**AC-114.2**: Limite default: 60 req/min per tenant
**AC-114.3**: Limite configurabile per tenant in tenant_settings (`api_rate_limit`)
**AC-114.4**: Risposta HTTP 429 con header `Retry-After` se superato
**AC-114.5**: Endpoint senza rate limit: webhook Brevo, health check

**SP**: 3 | **Priorita**: Must Have

---

### US-115: Metering dashboard (admin)
**Come** admin piattaforma (owner Nexa Data)
**Voglio** vedere i consumi di tutti i tenant in una dashboard
**Per** capire chi consuma cosa e pianificare il billing

**AC-115.1**: Endpoint GET /admin/metering con totali per tenant: email inviate, LLM tokens, PDF pages, API calls
**AC-115.2**: Filtro per mese
**AC-115.3**: Solo super-admin (owner del tenant piattaforma) puo accedere
**AC-115.4**: Pagina frontend /admin/metering con tabella tenant + consumi

**SP**: 5 | **Priorita**: Should Have

---

### US-116: Pagina Impostazioni → Integrazioni (frontend)
**Come** owner/admin tenant
**Voglio** vedere e configurare le integrazioni della mia azienda
**Per** gestire API key, sender email, quota senza toccare il codice

**AC-116.1**: Pagina /impostazioni/integrazioni con lista settings (masked)
**AC-116.2**: Sezione A-Cube: company_id, connection_id
**AC-116.3**: Sezione Email: sender_email, sender_name, sender_domain, quota usata
**AC-116.4**: Sezione AI: quota LLM tokens usati/totale
**AC-116.5**: Form per aggiungere/modificare custom API key (encrypted)
**AC-116.6**: Solo owner/admin possono accedere

**SP**: 5 | **Priorita**: Must Have

---

## Riepilogo

| Story | SP | Priorita | Focus |
|-------|-----|----------|-------|
| US-113 | 3 | Must | Contatore LLM tokens |
| US-114 | 3 | Must | Rate limit per tenant |
| US-115 | 5 | Should | Metering dashboard admin |
| US-116 | 5 | Must | Pagina Integrazioni FE |
| **TOTALE** | **16** | | |

## Sprint Plan

| Sprint | Stories | SP |
|--------|---------|-----|
| Sprint 33 | US-113, US-114 | 6 |
| Sprint 34 | US-115, US-116 | 10 |
