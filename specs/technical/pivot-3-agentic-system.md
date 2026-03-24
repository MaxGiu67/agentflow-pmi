# Impact Analysis — Pivot 3: Sistema Agentico Conversazionale

**Data:** 2026-03-24
**Tipo:** Cambio architetturale maggiore
**Scope:** Architettura, DB, API, Frontend, tutti gli agenti

---

## Causa del Pivot

Da un sistema di agenti indipendenti (chiamati dai service layer) a un **sistema agentico conversazionale** ispirato a OpenClaw:
- **Orchestratore centrale** che dialoga con l'utente via chat
- **Agenti specialisti** chiamati dall'orchestratore quando necessario
- **Nomi personalizzabili** dall'utente nelle impostazioni
- **Tools e skills** utilizzabili dagli agenti
- **Conversazioni persistenti** con chat history
- **Framework**: LangGraph StateGraph + Claude API

**Motivazione:** L'utente non interagisce con un gestionale tradizionale — dialoga con un agente AI che gestisce la contabilita per lui. Questo e il differenziatore chiave di AgentFlow.

---

## RIFARE (rigenerare completamente)

| File | Motivo |
|------|--------|
| specs/04-tech-spec.md | Nuova architettura agentica: Orchestrator, Agent Registry, Tool System, Conversation Store, WebSocket, Memory. Nuovi modelli DB (Conversation, Message, AgentConfig, AgentTool). Nuovi endpoint (chat, websocket, agent config). |
| specs/05-sprint-plan.md | Sprint aggiuntivi per il sistema agentico (Sprint 11-14 stimati). Riorganizzazione priorita. |
| specs/frontend/02-prd-frontend.md | Nuova interfaccia chat come schermata principale. Pagina configurazione agenti. |

## AGGIORNARE (modifica parziale)

| File | Cosa Cambiare |
|------|--------------|
| specs/01-vision.md | Vision statement: da "agente che lavora per te" a "agente con cui parli". Aggiungere sezione "Sistema Agentico Conversazionale" |
| specs/02-prd.md | Nuova Epic "Sistema Agentico" (E10). Aggiornare MoSCoW con chat, agent config, tools. Aggiornare milestones. |
| specs/03-user-stories.md | Aggiungere 8-10 nuove stories (US-A01 a US-A10) per sistema agentico. Stories esistenti invariate. |
| specs/database/schema.md | Aggiungere tabelle: conversations, messages, agent_configs, agent_tools, agent_skills, conversation_memories |
| specs/testing/test-strategy.md | Aggiungere test strategy per chat, websocket, LLM mocking |
| specs/ux/wireframes.md | Aggiungere wireframe chat interface |
| specs/_status.md | Aggiungere Pivot 3, aggiornare fasi |
| specs/_changelog.md | Entry pivot |

## INVARIATO

| File | Motivo |
|------|--------|
| specs/07-implementation.md | Sprint 1-10 completati, non cambiano |
| specs/08-validation.md | Validazione Sprint 1-10 completata |
| specs/testing/test-map.md | 369 test esistenti restano validi |
| specs/technical/ADR-007-drop-odoo.md | Decisione Drop Odoo invariata |
| specs/sprint-reviews/ | Review passate invariate |

---

## Impatto Implementazione

### Agenti esistenti (9) — WRAP, non rifare

| Agente | Impatto | Azione |
|--------|---------|--------|
| BaseAgent | ALTO | Estendere con interfaccia LangGraph node. Aggiungere tool registry. |
| FiscoAgent | BASSO | Wrappare come tool dell'orchestratore. Nessun cambio logica. |
| ParserAgent | BASSO | Wrappare come tool. |
| LearningAgent | BASSO | Wrappare come tool. |
| ContaAgent | BASSO | Wrappare come tool. |
| CashFlowAgent | BASSO | Wrappare come tool. |
| OCRAgent | BASSO | Wrappare come tool. |
| NormativoAgent | BASSO | Wrappare come tool. |
| ContoEconomicoAgent | MEDIO | Gia usa Claude API. Integrare nel flusso conversazionale. |

**Strategia:** Gli agenti esistenti diventano **tools** dell'orchestratore, non vengono riscritti.

### Database — ADDITIVE

Nuove tabelle (nessuna tabella esistente viene modificata):

```sql
-- Conversazioni
conversations (id, tenant_id, user_id, title, agent_id, status, created_at, updated_at)
messages (id, conversation_id, role, content, agent_name, tool_calls, tool_results, tokens_used, created_at)

-- Configurazione agenti
agent_configs (id, tenant_id, agent_type, display_name, personality, system_prompt, enabled, tools_enabled, created_at)
agent_tools (id, agent_config_id, tool_name, tool_description, tool_schema, enabled, created_at)

-- Memoria
conversation_memories (id, conversation_id, tenant_id, key, value, memory_type, created_at)
```

### API — ADDITIVE

Nuovi endpoint (nessun endpoint esistente viene modificato):

```
POST   /api/v1/chat/send              — Invia messaggio all'orchestratore
GET    /api/v1/chat/conversations      — Lista conversazioni
GET    /api/v1/chat/conversations/{id} — Storico messaggi
DELETE /api/v1/chat/conversations/{id} — Elimina conversazione
WS     /api/v1/chat/ws                 — WebSocket per streaming
GET    /api/v1/agents/config           — Lista configurazione agenti
PATCH  /api/v1/agents/config/{id}      — Modifica nome/personalita agente
GET    /api/v1/agents/tools            — Lista tools disponibili
```

### Frontend — ADDITIVE

Nuove pagine (nessuna pagina esistente viene rimossa):

```
/chat                    — Chat principale con orchestratore (NUOVA, diventa home)
/chat/{conversation_id}  — Conversazione specifica
/impostazioni/agenti     — Configurazione nomi e personalita agenti
```

Componenti nuovi:
- `ChatPage.tsx` — interfaccia chat full-screen
- `ChatMessage.tsx` — singolo messaggio (user/agent)
- `ChatInput.tsx` — input con invio
- `AgentBadge.tsx` — mostra quale agente sta rispondendo
- `AgentConfigPage.tsx` — configurazione agenti

### Test — ADDITIVE

Nuovi test (369 esistenti invariati):
- test_chat_api.py — invio messaggi, conversazioni
- test_orchestrator.py — routing a agenti corretti
- test_agent_config.py — configurazione agenti
- test_tools.py — esecuzione tools
- test_websocket.py — streaming

---

## Dipendenze tecniche

| Pacchetto | Versione | Uso |
|-----------|---------|-----|
| langgraph | >=0.3 | Orchestrazione grafo agenti |
| langchain-anthropic | >=0.3 | Claude come LLM per orchestratore |
| websockets | >=13 | WebSocket FastAPI |

---

## Stima effort

| Componente | Giorni |
|-----------|:------:|
| Modelli DB + API chat | 2 |
| Orchestratore LangGraph | 3 |
| Tool system (wrap 9 agenti) | 2 |
| Agent config (nomi, personalita) | 1 |
| Conversazione persistente + memoria | 2 |
| WebSocket streaming | 1 |
| Frontend chat UI | 3 |
| Frontend agent config | 1 |
| Test | 2 |
| **Totale** | **~17 giorni** |

---

## Ordine di riesecuzione consigliato

```
1. /dev-vision    — Aggiornare vision con sistema agentico
2. /dev-prd       — Aggiornare PRD con Epic Sistema Agentico
3. /dev-stories   — Generare US-A01 a US-A10
4. /dev-spec      — Tech spec architettura agentica
5. /dev-sprint    — Sprint 11-14 planning
6. /dev-review    — Verifica coerenza post-pivot
7. /dev-implement — Implementazione story per story
```

---
_Pivot 3 Impact Analysis — 2026-03-24_
