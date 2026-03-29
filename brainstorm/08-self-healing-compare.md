# Confronto Multi-LLM — Self-Healing Import System
**Data:** 2026-03-30

## Modelli utilizzati
| Ruolo | Provider | Modello | Tipo |
|-------|----------|---------|------|
| Analista 1 | Anthropic | claude-opus-4-6 | locale |
| Analista 2 | OpenAI | gpt-4o | via API |

## Domanda
Come implementare un sistema che si auto-corregge quando un import PDF fallisce, usando Claude API per generare fix automatiche?

---

## Prospettiva claude-opus-4-6 (Anthropic)

### Insight chiave: non serve generare codice

3 livelli di complessita crescente:

1. **Self-healing del prompt LLM (1-2 giorni)** — retry con prompt adattato. Il LLM e' gia un parser universale, basta migliorare il prompt. Zero codice generato.

2. **Auto-tuning del prompt (1 settimana)** — meta-prompt che analizza l'errore e produce un prompt migliore. Salvato in DB per riuso futuro (per-tenant, per-formato).

3. **Code generation via Agent SDK (2-3 settimane)** — genera PR su GitHub con migration + codice + test. L'utente approva, mai deploy diretto.

### Architettura: Error → Retry → Adapt → Escalate
```
PDF fallisce
  → Retry con prompt adattato (Livello 1)
  → Se fallisce ancora → meta-prompt per migliorare (Livello 2)
  → Se fallisce ancora → crea eccezione per l'utente (Livello 3)
  → Opzionale: genera PR con fix strutturale
```

### Costi: ~€0.30-€3/mese per 100 errori con Haiku

### Sicurezza: mai generare codice eseguibile in produzione. Solo prompt (Livello 1-2) o PR per review (Livello 3).

---

## Prospettiva gpt-4o (OpenAI)

### Approccio piu tradizionale
- Error Detector → Chatbot/Hook → Claude API → Fix Applicator → Test → Deploy/Approva
- Sandboxing per testare fix
- Code review manuale per fix critiche
- 5.000-10.000 token per fix media

### Alternative proposte
- Ampliare pattern di parsing con esempi
- ML specifico per formati PDF comuni
- Feedback manuale dall'utente

### Limiti identificati
- Codice molto complesso confonde il modello
- Dati PDF eterogenei problematici
- Intervento umano necessario per errori specifici

---

## Meta-analisi (claude-opus-4-6)

### Convergenze
1. **Il sistema e' fattibile** — entrambi concordano
2. **Sandbox/testing obbligatorio** — non deployare fix senza test
3. **Gradualita** — partire dal monitoring, poi integrare
4. **L'intervento umano resta necessario** per casi limite

### Divergenze

| Tema | Claude | GPT |
|------|--------|-----|
| **Approccio** | NON generare codice, migliorare i prompt | Generare codice + sandbox |
| **Complessita** | "Piu semplice di quanto pensi" — 3 livelli | "Complesso ma fattibile" — generico |
| **Sicurezza** | Mai codice in produzione, solo prompt o PR | Sandboxing + permessi minimi |
| **Costi** | €0.003-€0.30 per fix (quantificato) | "Migliaia di token" (vago) |
| **Primo passo** | Prompt retry automatico (1-2 giorni) | Logging/monitoring (setup) |

### Insight unici claude-opus-4-6
- **Il LLM E' gia il self-healing** — il parser LLM e' generalista, la maggior parte dei "fix" sono miglioramenti del prompt, non del codice
- **Meta-prompt pattern** — un LLM che migliora il prompt di un altro LLM, salvato per riuso
- **Prompt per-tenant in DB** — ogni commercialista ha il suo formato, il sistema impara
- **Agent SDK per PR** — genera PR su GitHub, non deploya

### Insight unici gpt-4o
- **ML specifico per formati** — alternativa interessante per formati ad alto volume
- **Feedback loop manuale** — segnalazione errori dall'utente come training data

### Raccomandazione

**Partire dal Livello 1 (prompt retry) — e' gia quasi gratis.**

Il sistema attuale (pdftotext → LLM → JSON) e' gia self-healing per natura — il LLM generalizza su formati diversi. L'unica cosa da aggiungere subito e' il **retry con prompt adattato** quando il primo tentativo fallisce.

Il Livello 2 (meta-prompt + salvataggio) e' il vero differenziante competitivo: il sistema **impara** dal commercialista di ogni utente.

Il Livello 3 (code generation) e' un "nice to have" per casi strutturali (campo DB mancante, endpoint nuovo) — ma per il 90% dei casi, migliorare il prompt basta.

**Percorso consigliato:**
1. Implementare retry con prompt adattato (1-2 giorni)
2. Aggiungere meta-prompt con salvataggio per-tenant (1 settimana)
3. Valutare Agent SDK per PR automatiche dopo il lancio

---

_Confronto generato: 2026-03-30 | claude-opus-4-6 + gpt-4o_
