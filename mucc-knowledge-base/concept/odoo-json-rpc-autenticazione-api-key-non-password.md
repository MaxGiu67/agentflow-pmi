---
tipo: concept
progetto: agentflow-pmi
data: 2026-04-02
stack: odoo, json-rpc
confidenza: alta
tags: odoo, json-rpc, api-key, autenticazione, sicurezza
---

# Odoo JSON-RPC usa API Key al posto della password per sicurezza

## Contesto
Odoo 18 supporta autenticazione via API Key (Preferenze > Sicurezza Account > Nuova API Key) al posto della password utente. Questo e il metodo raccomandato per integrazioni machine-to-machine.

## Concept

**Flusso autenticazione:**
1. `POST /jsonrpc` → service "common", method "authenticate", args [db, user, api_key, {}]
2. Ritorna `uid` (user ID numerico)
3. Chiamate successive: service "object", method "execute", args [db, uid, api_key, model, method, ...]

**JSON-RPC payload:**
```json
{
  "jsonrpc": "2.0",
  "method": "call",
  "params": {
    "service": "object",
    "method": "execute",
    "args": ["db_name", 2, "api_key", "crm.lead", "search_read", [...], [...]]
  },
  "id": 1
}
```

**Campi custom Odoo** usano prefisso `x_` (es. `x_deal_type`, `x_daily_rate`, `x_order_type`, `x_order_reference`, `x_order_date`, `x_order_notes`). Vanno creati manualmente in Impostazioni > Tecnico > Campi.

**Rate limit Odoo Online:** ~60 richieste/minuto. Per volumi alti, implementare caching locale.

## Progetto origine
agentflow-pmi — api/adapters/odoo_crm.py
