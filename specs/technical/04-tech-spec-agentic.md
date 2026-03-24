# Technical Specification — Sistema Agentico Conversazionale

**Progetto:** AgentFlow PMI
**Data:** 2026-03-24
**Stato:** Pivot 3 — Spec architettura agentica
**Fonte:** specs/03-user-stories-agentic.md, specs/technical/pivot-3-agentic-system.md

---

## Technology Stack (additivo)

| Layer | Tecnologia | Motivazione |
|-------|-----------|-------------|
| Orchestratore | **LangGraph** (langgraph>=0.3) | Grafo stateful per routing agenti, checkpointing, human-in-the-loop |
| LLM | **Claude API** (anthropic SDK o httpx) | Reasoning orchestratore + interpretazione richieste utente |
| Streaming | **FastAPI WebSocket** | Risposte token-by-token real-time |
| State Store | **PostgreSQL** (tabelle conversations, messages) | Persistenza conversazioni e memoria |
| Frontend Chat | **React + TanStack Query + WebSocket** | Chat UI con streaming |

---

## Architecture

### Flusso Conversazione

```
┌──────────────┐     ┌──────────────────────────────────────────────┐
│  Frontend    │     │                  FastAPI                      │
│  Chat UI     │     │                                              │
│              │ WS  │  ┌──────────────────────────────────┐        │
│  ChatInput   ├────►│  │         Orchestrator              │        │
│  ChatMessage │◄────┤  │      (LangGraph StateGraph)       │        │
│  AgentBadge  │     │  │                                   │        │
│              │     │  │  ┌─────────┐   ┌─────────┐       │        │
└──────────────┘     │  │  │ Router  │──►│ Agent   │       │        │
                     │  │  │  Node   │   │  Node   │       │        │
                     │  │  └─────────┘   └────┬────┘       │        │
                     │  │                     │             │        │
                     │  │              ┌──────▼──────┐      │        │
                     │  │              │ Tool Exec   │      │        │
                     │  │              │    Node     │      │        │
                     │  │              └──────┬──────┘      │        │
                     │  │                     │             │        │
                     │  │              ┌──────▼──────┐      │        │
                     │  │              │  Response   │      │        │
                     │  │              │   Node      │      │        │
                     │  └──────────────┴─────────────┘      │        │
                     │                                      │        │
                     │  ┌──────────────────────────────┐    │        │
                     │  │        Tool Registry          │    │        │
                     │  │                               │    │        │
                     │  │  count_invoices()             │    │        │
                     │  │  list_invoices()              │    │        │
                     │  │  sync_cassetto()              │    │        │
                     │  │  get_cashflow()               │    │        │
                     │  │  get_deadlines()              │    │        │
                     │  │  verify_invoice()             │    │        │
                     │  │  get_balance_sheet()          │    │        │
                     │  │  create_piano_conti()         │    │        │
                     │  │  ... (30+ tools)              │    │        │
                     │  └──────────────────────────────┘    │        │
                     │                                      │        │
                     │  ┌──────────────────────────────┐    │        │
                     │  │     Conversation Store        │    │        │
                     │  │     (PostgreSQL)              │    │        │
                     │  │                               │    │        │
                     │  │  conversations                │    │        │
                     │  │  messages                     │    │        │
                     │  │  agent_configs                │    │        │
                     │  │  conversation_memories        │    │        │
                     │  └──────────────────────────────┘    │        │
                     └──────────────────────────────────────┘        │
```

### LangGraph StateGraph

```python
# Grafo dell'orchestratore
StateGraph:
  Nodes:
    - router        → Analizza messaggio, decide quale agente(i) chiamare
    - agent_exec    → Chiama Claude con tools dell'agente selezionato
    - tool_exec     → Esegue il tool e restituisce risultato
    - response      → Formatta risposta finale per l'utente
    - memory_save   → Salva contesto nella memoria conversazione

  Edges:
    START → router
    router → agent_exec (con agent_name e tools)
    agent_exec → tool_exec (se serve tool call)
    tool_exec → agent_exec (risultato tool → agente ragiona)
    agent_exec → response (risposta pronta)
    response → memory_save
    memory_save → END

  State:
    - messages: list[Message]       # Storico conversazione
    - current_agent: str            # Agente attivo
    - tool_calls: list[ToolCall]    # Tools da eseguire
    - tool_results: list[ToolResult] # Risultati tools
    - tenant_id: UUID               # Tenant corrente
    - user_id: UUID                  # Utente corrente
```

---

## Database Schema (additive)

```sql
-- Conversazioni
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    user_id UUID NOT NULL,
    title VARCHAR(255),                    -- Auto-generato dal primo messaggio
    status VARCHAR(20) DEFAULT 'active',   -- active, archived, deleted
    metadata JSONB DEFAULT '{}',           -- Dati aggiuntivi
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Messaggi
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,             -- user, assistant, system, tool
    content TEXT,                           -- Testo del messaggio
    agent_name VARCHAR(100),               -- Quale agente ha risposto (NULL per user)
    tool_calls JSONB,                      -- Tool calls richiesti dall'agente
    tool_results JSONB,                    -- Risultati dei tool calls
    tokens_used INTEGER DEFAULT 0,         -- Token usati per questa risposta
    created_at TIMESTAMP DEFAULT NOW()
);

-- Configurazione agenti per tenant
CREATE TABLE agent_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    agent_type VARCHAR(50) NOT NULL,        -- fisco, conta, cashflow, parser, learning, ocr, normativo, conto_economico, orchestrator
    display_name VARCHAR(100) NOT NULL,     -- Nome personalizzabile dall'utente
    personality TEXT,                        -- Prompt personalita (opzionale)
    system_prompt TEXT,                      -- System prompt override (opzionale)
    enabled BOOLEAN DEFAULT TRUE,
    icon VARCHAR(50),                       -- Emoji o icona
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(tenant_id, agent_type)
);

-- Tools disponibili per agente
CREATE TABLE agent_tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_type VARCHAR(50) NOT NULL,        -- A quale tipo di agente appartiene
    tool_name VARCHAR(100) NOT NULL UNIQUE, -- Nome univoco del tool
    tool_description TEXT NOT NULL,          -- Descrizione per il LLM
    tool_parameters JSONB NOT NULL,         -- JSON Schema dei parametri
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Memoria conversazione (preferenze, contesto a lungo termine)
CREATE TABLE conversation_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    user_id UUID NOT NULL,
    key VARCHAR(255) NOT NULL,              -- es. "preferred_format", "known_supplier_rossi"
    value TEXT NOT NULL,
    memory_type VARCHAR(30) DEFAULT 'preference', -- preference, fact, context
    expires_at TIMESTAMP,                   -- NULL = permanente
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indici
CREATE INDEX idx_conversations_tenant ON conversations(tenant_id, status, created_at DESC);
CREATE INDEX idx_messages_conversation ON messages(conversation_id, created_at);
CREATE INDEX idx_agent_configs_tenant ON agent_configs(tenant_id);
CREATE INDEX idx_memories_tenant ON conversation_memories(tenant_id, user_id, key);
```

---

## API Endpoints (additivi)

### Chat

| # | Endpoint | Method | Auth | Descrizione |
|---|----------|--------|------|-------------|
| C1 | `/chat/send` | POST | JWT | Invia messaggio, ottiene risposta (sync) |
| C2 | `/chat/ws` | WS | JWT (query param) | WebSocket per streaming risposte |
| C3 | `/chat/conversations` | GET | JWT | Lista conversazioni utente |
| C4 | `/chat/conversations/{id}` | GET | JWT | Storico messaggi conversazione |
| C5 | `/chat/conversations/{id}` | DELETE | JWT | Elimina conversazione (soft delete) |
| C6 | `/chat/conversations/new` | POST | JWT | Crea nuova conversazione vuota |

### Agent Config

| # | Endpoint | Method | Auth | Descrizione |
|---|----------|--------|------|-------------|
| C7 | `/agents/config` | GET | JWT | Lista configurazione agenti del tenant |
| C8 | `/agents/config/{agent_type}` | PATCH | JWT | Modifica nome/personalita/enabled |
| C9 | `/agents/config/reset` | POST | JWT | Reset a nomi default |
| C10 | `/agents/tools` | GET | JWT | Lista tools disponibili |

### Dettaglio endpoint principali

#### POST /chat/send

```json
// Request
{
    "conversation_id": "uuid-or-null",  // null = nuova conversazione
    "message": "Quante fatture ho ricevuto questo mese?"
}

// Response
{
    "conversation_id": "uuid",
    "message_id": "uuid",
    "role": "assistant",
    "content": "Hai ricevuto 12 fatture passive questo mese per un totale di €15.430,00.",
    "agent_name": "Agente Fisco",
    "agent_type": "fisco",
    "tool_calls": [
        {
            "tool": "count_invoices",
            "args": {"month": "2026-03", "type": "passiva"},
            "result": {"count": 12, "total": 15430.00}
        }
    ],
    "suggestions": ["Mostra dettaglio", "Fatture da verificare", "Scadenze imminenti"]
}
```

#### WS /chat/ws

```
// Client → Server (JSON)
{"type": "message", "conversation_id": "uuid", "content": "Come sta il cash flow?"}

// Server → Client (streaming JSON chunks)
{"type": "agent_start", "agent_name": "Agente Cash Flow", "agent_type": "cashflow"}
{"type": "token", "content": "Il "}
{"type": "token", "content": "cash flow "}
{"type": "token", "content": "previsto "}
{"type": "token", "content": "a 90 giorni "}
...
{"type": "tool_call", "tool": "predict_cashflow", "status": "executing"}
{"type": "tool_result", "tool": "predict_cashflow", "data": {...}}
{"type": "token", "content": "mostra un saldo di €45.200."}
{"type": "message_end", "message_id": "uuid", "suggestions": [...]}
```

---

## Tool Registry

### Tools wrapping agenti esistenti

| Tool Name | Agent Source | Descrizione (per LLM) | Parametri |
|-----------|------------|----------------------|-----------|
| `count_invoices` | InvoiceService | Conta fatture per periodo e tipo | month?, type?, status? |
| `list_invoices` | InvoiceService | Lista fatture con filtri | date_from?, date_to?, type?, emittente?, limit? |
| `sync_cassetto` | FiscoAgent | Sincronizza fatture dal cassetto fiscale | force? |
| `verify_invoice` | InvoiceService | Conferma o correggi categoria fattura | invoice_id, category, confirmed |
| `get_pending_review` | InvoiceService | Fatture in attesa di verifica | limit? |
| `predict_cashflow` | CashFlowAgent | Previsione cash flow | days? (default 90) |
| `get_deadlines` | DeadlinesService | Scadenze fiscali | year? |
| `get_fiscal_alerts` | DeadlinesService | Alert fiscali personalizzati | year? |
| `get_journal_entries` | JournalService | Scritture contabili | date_from?, date_to?, status? |
| `get_balance_sheet` | BalanceSheetService | Bilancio CEE | year |
| `get_vat_settlement` | VatSettlementService | Liquidazione IVA | year, quarter |
| `get_dashboard` | DashboardService | Dashboard summary | — |
| `get_ceo_kpi` | CEOService | KPI cruscotto CEO | year? |
| `get_budget` | CEOService | Budget vs consuntivo | year? |
| `list_expenses` | ExpenseService | Note spese | status?, date_from? |
| `list_assets` | AssetService | Registro cespiti | status? |
| `get_withholding` | WithholdingService | Ritenute d'acconto | — |
| `get_f24` | F24Service | Lista F24 | year?, status? |
| `get_stamp_duties` | StampDutyService | Bollo trimestrale | year?, quarter? |
| `create_piano_conti` | ContoEconomicoAgent | Crea piano conti personalizzato | answers[] |
| `search_invoices` | InvoiceService | Cerca fatture per emittente | query |
| `get_bank_balance` | BankingService | Saldo conto corrente | account_id? |
| `get_bank_transactions` | BankingService | Movimenti bancari | account_id?, date_from? |
| `reconcile` | ReconciliationService | Riconcilia fattura con movimento | tx_id, invoice_id |
| `get_preservation_status` | PreservationService | Stato conservazione digitale | — |
| `get_normative_alerts` | NormativoService | Alert normativi | — |

**Totale: 25+ tools** — tutti wrappano servizi/agenti gia esistenti.

---

## File Structure (additiva)

```
api/
  orchestrator/
    __init__.py
    graph.py                    # LangGraph StateGraph definition
    router_node.py              # Analizza messaggio, decide agente
    agent_node.py               # Esegue agente con Claude + tools
    tool_node.py                # Esegue tool e restituisce risultato
    response_node.py            # Formatta risposta finale
    memory_node.py              # Gestione memoria conversazione
    state.py                    # State schema (Pydantic)
    tool_registry.py            # Registry di tutti i tools
    prompts.py                  # System prompts per orchestratore e agenti

  modules/
    chat/
      __init__.py
      router.py                 # POST /chat/send, WS /chat/ws, GET conversations
      service.py                # ChatService: invio messaggio, storico, gestione conversazioni
      schemas.py                # ChatMessage, Conversation, ToolCall schemas
      websocket.py              # WebSocket handler per streaming

    agent_config/
      __init__.py
      router.py                 # GET/PATCH /agents/config
      service.py                # AgentConfigService: CRUD configurazione
      schemas.py                # AgentConfigResponse, AgentConfigUpdate
      defaults.py               # Nomi e prompt default per ogni agente

frontend/
  src/
    pages/
      chat/
        ChatPage.tsx            # Layout chat full-screen
        ChatSidebar.tsx         # Lista conversazioni
      impostazioni/
        AgentConfigPage.tsx     # Configurazione nomi/personalita agenti
    components/
      chat/
        ChatMessage.tsx         # Singolo messaggio (user/agent)
        ChatInput.tsx           # Input con invio + suggerimenti
        AgentBadge.tsx          # Badge agente (nome + icona)
        ToolCallDisplay.tsx     # Mostra tool call in-progress
        SuggestionChips.tsx     # Bottoni azione rapida
    hooks/
      useWebSocket.ts           # Hook WebSocket per streaming
      useChat.ts                # Hook chat (invio, storico, conversazioni)
```

---

## Default Agent Configuration

| agent_type | display_name (default) | icon | Descrizione |
|-----------|----------------------|------|-------------|
| orchestrator | AgentFlow | 🤖 | Orchestratore principale — non visibile all'utente |
| fisco | Agente Fisco | 📋 | Fatture, SPID, cassetto fiscale, scadenze |
| conta | Agente Contabilita | 📒 | Scritture, piano conti, registrazioni |
| cashflow | Agente Cash Flow | 💰 | Previsioni, riconciliazione, saldi |
| conto_economico | Agente Setup | 🏗️ | Onboarding, piano conti personalizzato |
| parser | Agente Parser | 📄 | Parsing XML FatturaPA (interno, non visibile) |
| learning | Agente Learning | 🧠 | Categorizzazione (interno, non visibile) |
| ocr | Agente OCR | 📷 | Lettura PDF/immagini (interno, non visibile) |
| normativo | Agente Normativo | ⚖️ | Monitor cambi normativi |

**Agenti visibili all'utente:** fisco, conta, cashflow, conto_economico, normativo (5)
**Agenti interni:** parser, learning, ocr, orchestrator (4)

---

## Performance Targets

| Metrica | Target |
|---------|--------|
| Tempo risposta semplice (count, list) | <3 secondi |
| Tempo risposta multi-agente | <8 secondi |
| Streaming first token | <1 secondo |
| WebSocket latency | <100ms |
| Conversazioni per utente | Illimitate |
| Messaggi per conversazione | Fino a 1000 |
| Memoria entries per utente | Max 100 |

---

## Security

- **WebSocket auth**: JWT passato come query parameter (`/chat/ws?token=xxx`)
- **Tool execution**: ogni tool verifica `tenant_id` prima di eseguire query
- **Rate limiting**: max 30 messaggi/minuto per utente
- **Content filtering**: nessun dato sensibile (password, token) nei messaggi salvati
- **Conversation isolation**: un utente vede solo le sue conversazioni

---

## Story → Endpoint Mapping

| Story | Endpoints |
|-------|----------|
| US-A01 | POST /chat/send, WS /chat/ws |
| US-A02 | GET /chat/conversations, GET /chat/conversations/{id}, DELETE /chat/conversations/{id}, POST /chat/conversations/new |
| US-A03 | GET /agents/config, PATCH /agents/config/{type}, POST /agents/config/reset |
| US-A04 | GET /agents/tools (+ tool_registry.py interno) |
| US-A05 | WS /chat/ws |
| US-A06 | POST /chat/send (routing a conto_economico agent) |
| US-A07 | POST /chat/send (multi-agent routing nel grafo) |
| US-A08 | Interno: memory_node.py + conversation_memories table |
| US-A09 | Frontend: ChatPage, ChatMessage, ChatInput, AgentBadge |
| US-A10 | POST /chat/send ("cosa sai fare?") + SuggestionChips |

---

## Dipendenze Python (da aggiungere)

```
langgraph>=0.3.0
langchain-core>=0.3.0
langchain-anthropic>=0.3.0
websockets>=13.0
```

---
_Tech Spec Sistema Agentico — 2026-03-24_
