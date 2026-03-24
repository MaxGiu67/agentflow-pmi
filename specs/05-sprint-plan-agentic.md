# Sprint Plan — Sistema Agentico Conversazionale

**Progetto:** AgentFlow PMI
**Data:** 2026-03-24
**Fase:** 5 — Sprint Planning (Pivot 3)
**Fonte:** specs/03-user-stories-agentic.md, specs/technical/04-tech-spec-agentic.md

---

## Overview

- **Velocity**: 20 SP/sprint
- **Durata Sprint**: 1 settimana (accelerato, team singolo)
- **Sprint Totali**: 3
- **SP Totali**: 57
- **Must Have SP**: 39 (Sprint 11-12) | **Should Have SP**: 15 (Sprint 13) | **Could Have SP**: 3 (Sprint 13)

---

## Sprint 11: Orchestratore + Chat Backend

### Objective
Costruire il cuore del sistema agentico: orchestratore LangGraph, tool registry, chat API, conversazioni persistenti. Al termine, un utente puo inviare un messaggio via API e ricevere una risposta dall'agente corretto.

### Stories

| ID | Titolo | SP | Priority | Dependencies |
|----|--------|:--:|----------|-------------|
| US-A01 | Chat con orchestratore | 8 | Must | — |
| US-A04 | Tool system per agenti | 8 | Must | US-A01 |
| US-A02 | Conversazioni persistenti | 5 | Must | US-A01 |

**SP Totali Sprint**: 21 / 20 (leggero overflow accettabile)

### Task Breakdown

#### US-A01: Chat con orchestratore
| Task | Stima |
|------|-------|
| Installare langgraph, langchain-core, langchain-anthropic | 1h |
| Creare `api/orchestrator/state.py` — State schema Pydantic | 1h |
| Creare `api/orchestrator/graph.py` — LangGraph StateGraph (router → agent → tool → response) | 4h |
| Creare `api/orchestrator/router_node.py` — Analisi messaggio + routing agente | 3h |
| Creare `api/orchestrator/agent_node.py` — Esecuzione agente con Claude + tools | 3h |
| Creare `api/orchestrator/response_node.py` — Formattazione risposta | 1h |
| Creare `api/orchestrator/prompts.py` — System prompts orchestratore e agenti | 2h |
| Creare `api/modules/chat/router.py` — POST /chat/send | 2h |
| Creare `api/modules/chat/service.py` — ChatService | 2h |
| Test orchestratore (routing corretto, errori, multi-turno) | 3h |

#### US-A04: Tool system
| Task | Stima |
|------|-------|
| Creare `api/orchestrator/tool_registry.py` — Registry con 25+ tools | 4h |
| Creare `api/orchestrator/tool_node.py` — Esecuzione tool | 2h |
| Wrappare 9 agenti esistenti come tools (count, list, sync, verify, predict, etc.) | 4h |
| Test tool execution (parametri, errori, risultati grandi) | 2h |

#### US-A02: Conversazioni persistenti
| Task | Stima |
|------|-------|
| Aggiungere modelli DB: Conversation, Message | 1h |
| Creare `api/modules/chat/service.py` — CRUD conversazioni | 2h |
| Endpoint GET /conversations, GET /conversations/{id}, DELETE, POST /new | 2h |
| Integrazione persistenza nel grafo LangGraph (salva messaggi dopo ogni turno) | 2h |
| Test persistenza (storico, ripresa, eliminazione) | 2h |

### Completion Criteria
- [ ] POST /chat/send funziona: messaggio → routing → tool call → risposta
- [ ] Almeno 5 tools funzionanti (count_invoices, list_invoices, get_deadlines, get_dashboard, predict_cashflow)
- [ ] Conversazioni salvate in DB e recuperabili
- [ ] Test copertura ≥ 80% su orchestratore

### Risks
- **LangGraph learning curve**: Mitigazione: iniziare con grafo semplice (3 nodi), aggiungere complessita dopo.
- **Claude API latenza**: Mitigazione: timeout 10s, retry 1x, fallback a risposta generica.

---

## Sprint 12: Frontend Chat + Agent Config + Onboarding

### Objective
L'utente puo dialogare con AgentFlow da un'interfaccia chat nel browser. Puo personalizzare i nomi degli agenti. L'onboarding avviene via conversazione.

### Stories

| ID | Titolo | SP | Priority | Dependencies |
|----|--------|:--:|----------|-------------|
| US-A09 | Frontend chat UI | 8 | Must | US-A01, US-A05 |
| US-A03 | Configurazione agenti | 5 | Must | US-A01 |
| US-A06 | Onboarding conversazionale | 5 | Must | US-A01, US-A04 |
| US-A05 | WebSocket streaming | 5 | Should | US-A01 |

**SP Totali Sprint**: 23 / 20 (overflow gestibile, WS e riducibile)

### Task Breakdown

#### US-A09: Frontend chat UI
| Task | Stima |
|------|-------|
| Creare `ChatPage.tsx` — layout full-screen (sidebar + chat + input) | 3h |
| Creare `ChatMessage.tsx` — messaggio con markdown, tabelle, badge agente | 2h |
| Creare `ChatInput.tsx` — input con invio (Enter) e suggerimenti | 1h |
| Creare `AgentBadge.tsx` — badge con nome e icona agente | 1h |
| Creare `ChatSidebar.tsx` — lista conversazioni con "Nuova chat" | 2h |
| Creare `SuggestionChips.tsx` — bottoni azione rapida | 1h |
| Aggiornare `App.tsx` — route /chat come homepage | 1h |
| Creare `useChat.ts` — hook per invio messaggi e storico | 2h |
| Test responsive (mobile, tablet) | 1h |

#### US-A05: WebSocket streaming
| Task | Stima |
|------|-------|
| Creare `api/modules/chat/websocket.py` — WS handler FastAPI | 3h |
| Creare `useWebSocket.ts` — hook frontend per streaming | 2h |
| Integrare streaming nel ChatMessage (token progressivi) | 2h |
| Fallback HTTP polling se WS fallisce | 1h |
| Test WebSocket (connessione, disconnessione, retry) | 1h |

#### US-A03: Configurazione agenti
| Task | Stima |
|------|-------|
| Aggiungere modello DB: AgentConfig | 1h |
| Creare `api/modules/agent_config/` — router, service, schemas | 2h |
| Creare `defaults.py` — nomi e prompt default per 9 agenti | 1h |
| Seed default agent configs al primo login | 1h |
| Creare `AgentConfigPage.tsx` — lista agenti con toggle e rename | 2h |
| Test config (rename, disable, reset) | 1h |

#### US-A06: Onboarding conversazionale
| Task | Stima |
|------|-------|
| Integrare ContoEconomicoAgent nel flusso chat | 2h |
| Routing: se utente nuovo → avvia onboarding automaticamente | 1h |
| Gestione ripresa onboarding abbandonato | 1h |
| Test onboarding via chat (completo, abbandonato, gia fatto) | 2h |

### Completion Criteria
- [ ] Chat UI funzionante: l'utente digita, vede risposta con streaming
- [ ] Agenti rinominabili dalle impostazioni
- [ ] Onboarding avviene in chat (domande ATECO → piano conti)
- [ ] WebSocket streaming attivo (o fallback HTTP)
- [ ] Mobile responsive

### Risks
- **WebSocket su Railway**: Railway supporta WS, ma proxy potrebbe causare timeout. Mitigazione: heartbeat ogni 30s + fallback HTTP.
- **Frontend complessita**: Chat UI con streaming, markdown, tabelle. Mitigazione: usare libreria react-markdown per rendering.

---

## Sprint 13: Multi-agent + Memoria + Polish

### Objective
Completare il sistema agentico: risposte multi-agente, memoria a lungo termine, discovery skills. Al termine, il sistema agentico e completo e pronto per produzione.

### Stories

| ID | Titolo | SP | Priority | Dependencies |
|----|--------|:--:|----------|-------------|
| US-A07 | Multi-agent response | 5 | Should | US-A01, US-A04 |
| US-A08 | Memoria conversazione | 5 | Should | US-A02 |
| US-A10 | Agent skill discovery | 3 | Could | US-A01 |

**SP Totali Sprint**: 13 / 20 (buffer per bug fix e polish)

### Task Breakdown

#### US-A07: Multi-agent response
| Task | Stima |
|------|-------|
| Aggiornare router_node per riconoscere domande multi-agente | 2h |
| Esecuzione parallela di piu agenti nel grafo | 3h |
| Composizione risposta unica con badge per sezione | 2h |
| Test multi-agent (successo, fallimento parziale, timeout) | 2h |

#### US-A08: Memoria conversazione
| Task | Stima |
|------|-------|
| Aggiungere modello DB: ConversationMemory | 1h |
| Creare `api/orchestrator/memory_node.py` — salva/leggi preferenze | 2h |
| Integrare memoria nel contesto del grafo (carica all'inizio di ogni conversazione) | 2h |
| Gestione scadenza e pulizia memoria | 1h |
| Test memoria (salva, leggi, reset, cross-conversazione) | 2h |

#### US-A10: Agent skill discovery
| Task | Stima |
|------|-------|
| Aggiungere comando "cosa sai fare?" nel router | 1h |
| Generare lista capacita dagli agenti abilitati | 1h |
| Suggerimenti proattivi (chip nella chat vuota) | 1h |
| Suggerimenti contestuali (dopo azione completata) | 1h |
| Test discovery (lista, suggerimenti, agente disabilitato) | 1h |

### Completion Criteria
- [ ] "Come sta la mia azienda?" → risposta da 3+ agenti con badge
- [ ] Memoria ricorda preferenze cross-conversazione
- [ ] "Cosa sai fare?" elenca capacita
- [ ] Suggerimenti chip nella chat
- [ ] Tutti i test PASS, deploy su Railway funzionante

### Risks
- **Latenza multi-agente**: 3 agenti in parallelo = 3 chiamate Claude. Mitigazione: cache risultati recenti, timeout 8s per agente.

---

## Riepilogo Sprint

| Sprint | Obiettivo | SP | Stories |
|:------:|-----------|:--:|:-------:|
| 11 | Orchestratore + Chat Backend | 21 | US-A01, US-A04, US-A02 |
| 12 | Frontend Chat + Config + Onboarding | 23 | US-A09, US-A05, US-A03, US-A06 |
| 13 | Multi-agent + Memoria + Polish | 13 | US-A07, US-A08, US-A10 |
| **Totale** | | **57** | **10 stories** |

---

## Rischi del Piano

| Rischio | Sprint | Mitigazione |
|---------|--------|-------------|
| LangGraph complessita | 11 | Iniziare con grafo minimo, iterare |
| Claude API costi | 11-13 | Cache risposte, batch tools, max_tokens limitato |
| WebSocket su Railway | 12 | Heartbeat + fallback HTTP |
| Latenza multi-agente | 13 | Esecuzione parallela + timeout per agente |
| Context window overflow | 11-13 | Summarization storico, max 20 messaggi nel contesto |

---
_Sprint Plan Sistema Agentico — 2026-03-24_
