# Architettura Agentica — Generatore Email AI

> Data: 2026-04-04
> Tipo sistema: **Single Agent** (tipo A) — un agente con tool specifico
> Stack: Python 3.12 + FastAPI + OpenAI + Brevo

---

## 1. Agent Loop Architecture

### Classificazione
- **Tipo**: Single Agent — un agente che genera HTML email da prompt naturale
- **Tool**: 1 (generazione HTML) + varianti (refine, translate)
- **Human-in-the-loop**: Si — il commerciale vede la preview e puo modificare/approvare
- **Sessione**: Corta (< 30 secondi per generazione)
- **Multi-LLM**: No — solo OpenAI (gpt-4o-mini per costi, gpt-4o per qualita)

### Flusso

```
Commerciale                    Backend                         OpenAI
    │                            │                               │
    │ "Crea email per proposta   │                               │
    │  servizi SAP a Acme SPA"   │                               │
    │ ──────────────────────────>│                               │
    │                            │  POST /v1/chat/completions    │
    │                            │  system: email_generator      │
    │                            │  user: prompt + contesto      │
    │                            │ ─────────────────────────────>│
    │                            │                               │
    │                            │  HTML completo + subject      │
    │                            │ <─────────────────────────────│
    │                            │                               │
    │  Preview HTML renderizzata │                               │
    │ <──────────────────────────│                               │
    │                            │                               │
    │  [Modifica testo]          │                               │
    │  [Inserisci {{nome}}]      │                               │
    │  [Salva come template]     │                               │
    │ ──────────────────────────>│                               │
    │                            │  Salva in email_templates     │
    │  Template salvato!         │                               │
    │ <──────────────────────────│                               │
```

### Nessun loop agentico necessario
Questo non e un agent loop classico con iterazioni. E una **singola chiamata LLM** con system prompt ottimizzato. Il "loop" e umano: genera → preview → modifica → rigenera (opzionale).

### Parametri operativi

| Parametro | Valore | Motivazione |
|-----------|--------|-------------|
| Modello | `gpt-4o-mini` | Sufficiente per HTML email, costo ~$0.15/1M token |
| Max tokens risposta | 2000 | Un'email HTML professionale e ~800-1500 token |
| Temperature | 0.7 | Creativita moderata — email professionali ma non robotiche |
| Timeout | 15s | Se non risponde in 15s, errore |
| Retry | 1 | Un solo retry con backoff 2s |
| Metering | Si | Track tokens per tenant (TenantUsage) |
| Quota check | Si | Controlla quota LLM prima di chiamare |

---

## 2. Context Management

### System Prompt (zona statica — cacheable)

```
Sei un esperto di email marketing B2B italiano. Generi email HTML
professionali, responsive e moderne.

REGOLE:
1. Output SOLO HTML valido — nessun testo prima o dopo
2. Layout responsive con max-width: 600px, centrato
3. Font: -apple-system, BlinkMacSystemFont, sans-serif
4. Colori brand: primario #863bff (viola), secondario #2563eb (blu)
5. Struttura: header con logo → corpo → CTA button → firma → footer
6. Bottone CTA: background #863bff, border-radius 10px, padding 14px 32px
7. Footer: "Questa email e stata inviata da {{azienda}}" + link unsubscribe
8. Usa variabili con doppia graffa: {{nome}}, {{azienda}}, {{deal_name}}, {{commerciale}}
9. Subject line: includi come commento HTML <!-- subject: ... --> nella prima riga
10. Tono: professionale ma caldo, italiano formale (Lei, non tu)
11. NO immagini esterne (no <img src="http...">)
12. NO JavaScript
13. Inline CSS (no <style> tag — molti client email li ignorano)
```

### User Prompt (zona dinamica)

```python
user_prompt = f"""
Crea un'email per: {prompt_utente}

CONTESTO:
- Azienda mittente: {tenant_name}
- Settore: {tenant_sector or "non specificato"}
- Commerciale: {user_name}
- Destinatario: {contact_name or "generico"}
- Deal: {deal_name or "non specificato"}

VARIABILI DISPONIBILI (inseriscile dove appropriato):
{{{{nome}}}}, {{{{azienda}}}}, {{{{deal_name}}}}, {{{{commerciale}}}}, {{{{deal_value}}}}
"""
```

### Context Window Budget

| Componente | Token stimati |
|------------|--------------|
| System prompt | ~300 |
| User prompt + contesto | ~200 |
| Risposta HTML | ~1200 |
| **Totale per chiamata** | **~1700 token** |
| **Costo per email** | **~$0.0003 (gpt-4o-mini)** |

Con quota 100.000 token/mese = ~58 email generate/mese per tenant. Piu che sufficiente.

---

## 3. Security & Sandboxing

### Input Validation

```python
from pydantic import BaseModel, Field

class GenerateEmailRequest(BaseModel):
    prompt: str = Field(..., min_length=10, max_length=1000)
    tone: str = Field(default="professionale", pattern="^(professionale|amichevole|formale)$")
    contact_name: str = ""
    deal_name: str = ""
    include_cta: bool = True
```

### Rischi e mitigazioni

| Rischio | Livello | Mitigazione |
|---------|---------|-------------|
| Prompt injection nell'email | MEDIO | System prompt con regole rigide, output solo HTML |
| HTML malevolo (XSS) | BASSO | Sanitizzazione output (no script, no onclick) |
| Costo eccessivo | MEDIO | Quota token per tenant, max 2000 token per risposta |
| Contenuto inappropriato | BASSO | OpenAI ha filtri built-in, contenuto e email B2B |
| Leak dati tenant | BASSO | Contesto solo del tenant corrente, no cross-tenant |

### Sanitizzazione output

```python
import re

def sanitize_email_html(html: str) -> str:
    """Remove potentially dangerous HTML from AI output."""
    # Remove script tags
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    # Remove event handlers
    html = re.sub(r'\s+on\w+="[^"]*"', '', html, flags=re.IGNORECASE)
    # Remove external images (privacy tracking risk)
    # Keep only data: URIs if any
    html = re.sub(r'<img[^>]+src="https?://[^"]*"[^>]*>', '', html, flags=re.IGNORECASE)
    return html.strip()
```

---

## 4. API Design

### Endpoint: POST /api/v1/email/generate

```python
# Request
{
    "prompt": "Crea una email per presentare i nostri servizi SAP a un nuovo prospect",
    "tone": "professionale",
    "contact_name": "Mario Rossi",
    "deal_name": "SAP Migration Acme",
    "include_cta": true
}

# Response
{
    "subject": "I nostri servizi SAP per Acme SPA",
    "html_body": "<div style='max-width:600px;margin:0 auto;...'>...</div>",
    "variables_detected": ["nome", "azienda", "deal_name", "commerciale"],
    "tokens_used": 1650,
    "model": "gpt-4o-mini"
}
```

### Endpoint: POST /api/v1/email/refine

Per modifiche iterative senza rigenerare da zero:

```python
# Request
{
    "html_body": "<div>...current HTML...</div>",
    "instruction": "Aggiungi un paragrafo sui tempi di consegna: 3-6 mesi",
    "keep_variables": true
}

# Response — same format as /generate
```

---

## 5. Frontend Architecture

### Componente: `AIEmailEditor`

```
┌─────────────────────────────────────────────────┐
│  Descrivi l'email che vuoi                      │
│  ┌─────────────────────────────────────────────┐│
│  │ Crea una email professionale per presentare ││
│  │ i nostri servizi SAP...                     ││
│  └─────────────────────────────────────────────┘│
│                                                 │
│  Tono: [Professionale ▼]    [✨ Genera con AI]  │
│                                                 │
│  ─── Preview ──────────────────────────────────│
│  ┌─────────────────────────────────────────────┐│
│  │  ┌────────────────────┐                     ││
│  │  │     AF  AgentFlow  │   ← header          ││
│  │  └────────────────────┘                     ││
│  │                                             ││
│  │  Gentile {{nome}},                          ││
│  │                                             ││
│  │  Le scrivo per presentarle i nostri...      ││
│  │                                             ││
│  │  ┌──────────────────┐                       ││
│  │  │  Scopri di piu   │  ← CTA button        ││
│  │  └──────────────────┘                       ││
│  │                                             ││
│  │  Cordiali saluti,                           ││
│  │  {{commerciale}}                            ││
│  └─────────────────────────────────────────────┘│
│                                                 │
│  ─── Variabili ────────────────────────────────│
│  [+ {{nome}}] [+ {{azienda}}] [+ {{deal_name}}]│
│                                                 │
│  ─── Azioni ───────────────────────────────────│
│  [🔄 Rigenera] [✏️ Modifica HTML] [💾 Salva]    │
│                                                 │
└─────────────────────────────────────────────────┘
```

### Stati del componente

| Stato | UI |
|-------|-----|
| **Idle** | Textarea prompt + bottone "Genera" |
| **Generating** | Spinner + "L'AI sta creando la tua email..." |
| **Preview** | HTML renderizzato + toolbar variabili + azioni |
| **Editing** | Textarea HTML (per utenti avanzati) |
| **Saving** | Form nome template + categoria → salva |

### Toolbar variabili

Bottoni cliccabili che inseriscono la variabile nel punto corrente del testo:
- `{{nome}}` — Nome contatto
- `{{azienda}}` — Ragione sociale
- `{{deal_name}}` — Nome opportunita
- `{{deal_value}}` — Valore deal
- `{{commerciale}}` — Nome commerciale

Click su un bottone → inserisce la variabile nel clipboard + evidenzia nel preview.

---

## 6. Checklist Implementazione

### Fase 1: Backend (2-3 ore)

- [ ] Endpoint `POST /email/generate` — chiama OpenAI, sanitizza, ritorna HTML
- [ ] Endpoint `POST /email/refine` — modifica iterativa
- [ ] System prompt ottimizzato per email HTML italiane
- [ ] Sanitizzazione output (no script, no event handlers)
- [ ] Metering: track token usage per tenant
- [ ] Quota check prima della generazione
- [ ] Test: 3 test (generazione, sanitizzazione, quota)

### Fase 2: Frontend (2-3 ore)

- [ ] Componente `AIEmailEditor.tsx` con stati (idle → generating → preview → saving)
- [ ] Textarea prompt con suggerimenti
- [ ] Preview HTML renderizzata (iframe o dangerouslySetInnerHTML)
- [ ] Toolbar variabili (bottoni clickabili)
- [ ] Toggle "Modifica HTML" per utenti avanzati
- [ ] Form salva template (nome, categoria)
- [ ] Hook `useGenerateEmail()` con React Query mutation

### Fase 3: Integrazione (1 ora)

- [ ] Collegare alla pagina `/email/templates` — bottone "Crea con AI"
- [ ] Collegare al `SendEmailModal` — opzione "Genera con AI"
- [ ] Aggiungere nella pagina `/crm/deals/:id` — bottone "Genera email per questo deal"

---

## 7. ADR

### ADR-010: Generazione email via OpenAI (non editor drag-and-drop)

**Contesto**: Serviva un modo per i commerciali di creare email professionali senza scrivere HTML ne uscire da AgentFlow.

**Opzioni**:
1. Editor drag-and-drop interno (Unlayer, TipTap) — 2+ sprint, complesso
2. Template Brevo con ID — bello ma richiede uscire su Brevo
3. **Generazione AI da prompt naturale** — il commerciale descrive, l'AI crea

**Decisione**: Opzione 3. Il commerciale parla in italiano, l'AI genera HTML professionale. Preview + modifica + salva come template.

**Motivazione**:
- Nessun competitor CRM per PMI ha questa feature
- Costo trascurabile (~$0.0003 per email con gpt-4o-mini)
- Implementazione veloce (1 sprint)
- Il commerciale non deve imparare ne HTML ne un editor
- Differenziazione forte rispetto a Keap/Pipedrive/HubSpot

**Rischi**:
- Qualita HTML variabile → mitigato con system prompt rigido + sanitizzazione
- Dipendenza OpenAI → mitigato con fallback a template manuali
