# Piano Prossima Sessione — 2 priorita

## Priorita 1: Fix agente — risposte guidate, non generiche

### Problema
Quando l'utente chiede "Aiutami a importare i saldi del bilancio", l'agente risponde con consigli generici ("contatta il supporto") invece di guidare con domande e azioni concrete.

### Soluzione
L'agente deve avere **tools specifici** per ogni pezzo del puzzle:

```
Tool: apertura_conti
  1. Chiede: "Hai il bilancio dell'anno precedente? In che formato? (PDF/Excel/a voce)"
  2. Se PDF → chiama API /accounting/import-bilancio → mostra preview
  3. Se a voce → chiede i saldi principali uno per uno (banca, crediti, debiti, capitale)
  4. Conferma → chiama API /accounting/confirm-bilancio
  5. Segna il pezzo "Bilancio" come attivo nel puzzle

Tool: crea_budget
  1. Carica knowledge base (01-05 da api/knowledge/budget/)
  2. Sceglie tecnica per ATECO (incremental/zero-based)
  3. Fa domande per settore (da 04-domande-per-settore.md)
  4. Calcola CE previsionale fino a EBITDA
  5. Conferma → salva budget
  6. Segna il pezzo "Budget" come attivo nel puzzle
```

### File da modificare
- `api/orchestrator/graph.py` — aggiungere tools per apertura_conti e crea_budget
- `api/orchestrator/tool_registry.py` — registrare i nuovi tools
- Il system prompt dell'orchestratore deve istruire l'agente a usare i tools

---

## Priorita 2: Chatbot flottante (stile Stitch/Google)

### Problema attuale
La pagina /chat e' una pagina dedicata — l'utente esce dal contesto. Il chatbot dovrebbe essere **flottante** su ogni pagina, come Google Stitch.

### Design
```
┌─────────────────────────────────────────────┐
│  PAGINA CORRENTE (Dashboard, Import, etc.)  │
│                                             │
│  [Contenuto normale della pagina]           │
│  [Risultati dei tools mostrati qui]         │
│                                             │
│                                             │
│                    ┌──────────────────────┐  │
│                    │ 💬 Chatbot flottante │  │
│                    │ ┌──────────────────┐ │  │
│                    │ │ Messaggi...      │ │  │
│                    │ │                  │ │  │
│                    │ └──────────────────┘ │  │
│                    │ [Input messaggio...] │  │
│                    └──────────────────────┘  │
└─────────────────────────────────────────────┘
```

### Comportamento
- Chatbot e' un pannello flottante bottom-right (o laterale destro)
- Collassibile con un click (mostra solo l'icona)
- I tools dell'agente agiscono sulla pagina sotto:
  - "Mostra il fatturato" → la pagina sotto naviga a /dashboard
  - "Importa il bilancio" → la pagina sotto mostra il form import
  - "Crea il budget" → la pagina sotto mostra il wizard budget
- Il chatbot riceve il contesto della pagina corrente (quale pagina, quali dati)

### File da modificare
- Creare `components/chat/FloatingChatbot.tsx` — pannello flottante
- Modificare `components/layout/AppLayout.tsx` — includere FloatingChatbot in tutte le pagine
- Il chatbot gia esiste come `ChatbotFloating` — verificare se e' gia implementato
- Rimuovere la pagina /chat dedicata (o mantenerla come fallback)

### Riferimento
- Google Stitch: chatbox flottante + contenuto sotto
- Il chatbot AgentFlow gia ha un componente ChatbotFloating — potrebbe essere gia parzialmente implementato

---

## Ordine di esecuzione

1. **Fix prompt agente** — aggiungere tools apertura_conti e crea_budget all'orchestratore
2. **Chatbot flottante** — redesign layout con chatbot su tutte le pagine
3. **Test E2E** — verificare flusso puzzle → chat → tool → risultato
