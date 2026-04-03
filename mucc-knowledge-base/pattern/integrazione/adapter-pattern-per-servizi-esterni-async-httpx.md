---
tipo: pattern
progetto: agentflow-pmi
data: 2026-04-02
stack: python, fastapi, httpx
confidenza: alta
tags: adapter, integrazione, async, httpx, dependency-injection, pattern
---

# Pattern adapter async con httpx per servizi esterni in FastAPI

## Contesto
AgentFlow PMI integra 8+ servizi esterni (FiscoAPI, Salt Edge, A-Cube, OCR, Odoo CRM...). Ogni integrazione segue lo stesso pattern collaudato.

## Pattern

1. **File**: un adapter = un file in `api/adapters/nome_servizio.py`
2. **Dataclass di dominio**: `@dataclass` per input/output tipizzati (es. `OdooCRMDeal`, `SaltEdgeTransaction`)
3. **Client class**: costruttore con config da `api.config.settings`, metodi `async def`
4. **HTTP**: `httpx.AsyncClient` con timeout 30s, `raise_for_status()`
5. **Constructor injection**: `service(adapter=None)` → `self.adapter = adapter or DefaultClient()`
6. **Mock/Real branching**: `if settings.api_key:` usa reale, altrimenti mock
7. **Registrazione tool**: handler nel `tool_registry.py`, mapping agente nel `graph.py`

**Esempio firma:**
```python
class OdooCRMClient:
    def __init__(self, url=None, db=None, user=None, api_key=None):
        self.url = url or settings.odoo_url
        # ...

    async def get_deals(self, domain=None, limit=100) -> list[OdooCRMDeal]:
        # ...
```

## Progetto origine
agentflow-pmi — api/adapters/odoo_crm.py, api/adapters/saltedge.py, api/adapters/fiscoapi.py
