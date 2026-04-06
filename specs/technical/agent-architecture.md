# Agent Architecture — AgentFlow PMI v3.0

**Tipo sistema: B — Coordinator snello**
**Data: 2026-04-06**
**Revisione: 2 — semplificata dopo feedback**

---

## Principio fondamentale

> L'agente **aiuta il commerciale**, non lo sostituisce. Chiede le info giuste al momento giusto, suggerisce la prossima azione, prepara bozze. Non impone passi obbligatori. Il commerciale puo sempre saltare stati.

> Il **prodotto scelto** determina la pipeline. Il **commerciale** vende tutto: T&M, corpo, Elevia. L'agente si adatta.

---

## 1. Architettura

### Tre agenti, tre domini separati

```
                    ┌─────────────────────┐
                    │    ORCHESTRATOR     │
                    │   "Cosa vuoi fare?" │
                    │   Intent → Agent    │
                    └──────────┬──────────┘
                               │
           ┌───────────────────┼───────────────────┐
           │                   │                   │
    ┌──────▼──────┐    ┌───────▼───────┐   ┌──────▼──────┐
    │ SALES AGENT │    │  CONTROLLER   │   │  ANALYTICS  │
    │             │    │    AGENT      │   │    AGENT    │
    │ Vende.      │    │ Gestisce.     │   │ Analizza.   │
    │ Qualsiasi   │    │ Fatture,      │   │ KPI, trend, │
    │ prodotto,   │    │ scadenze,     │   │ cashflow,   │
    │ qualsiasi   │    │ fisco,        │   │ previsioni  │
    │ pipeline.   │    │ budget        │   │             │
    │             │    │               │   │             │
    │ Tool si     │    │ 17 tool       │   │ 6 tool      │
    │ attivano    │    │ (esistenti)   │   │             │
    │ per prodotto│    │               │   │             │
    └─────────────┘    └───────────────┘   └─────────────┘
```

**Perche un Sales Agent unico:**
- Il commerciale Nexa Data vende T&M, corpo, E Elevia. Non cambia "agente" quando cambia prodotto.
- L'agente carica la pipeline corretta dal DB in base al prodotto sul deal.
- I tool specifici (matching risorse, ATECO scoring, LinkedIn) si attivano solo quando servono per quel prodotto.
- Snello: un prompt, un contesto, un flusso.

---

## 2. Sales Agent — "Il tuo assistente commerciale"

### Come funziona

1. Il commerciale crea un deal e sceglie un prodotto dal catalogo
2. Il prodotto determina la pipeline (T&M, Corpo, Elevia, custom)
3. L'agente carica la FSM di quella pipeline dal DB
4. A ogni interazione, l'agente:
   - Sa in che stato e il deal
   - Chiede le info mancanti per quello stato
   - Suggerisce la prossima azione
   - Prepara bozze (email, offerta, messaggio LinkedIn)
   - NON blocca mai — il commerciale puo saltare stati

### Pipeline templates (precaricate, personalizzabili)

**Pipeline T&M (consulenza/staff augmentation)**
```
Lead → Qualifica → Match risorse → Offerta → Negoziazione → Won/Lost → Delivery
```
Snella, 6 stati. Il commerciale la conosce a memoria perche la vive ogni giorno. Arriva un referral, qualifica, verifica se ha le risorse, manda offerta. Non servono 9 stati.

**Pipeline Progetto a Corpo**
```
Lead → Analisi requisiti → Specifiche → [Demo] → Offerta → Negoziazione → Won/Lost → Delivery
```
Simile ma con fase Specifiche obbligatoria (si definisce cosa costruire). Demo opzionale.

**Pipeline Elevia (prodotto AI via LinkedIn)**
```
Prospect → Connessione → Engagement → Discovery Call → [Demo] → Offerta → Won/Lost → Onboarding
```
Piu lunga perche il top-of-funnel e digitale (LinkedIn). Ma anche qui: il commerciale puo saltare engagement e andare dritto alla call se ha gia il contatto.

**Pipeline Custom (futuro)**
Qualsiasi tenant puo creare la propria pipeline nell'admin. L'agente la carica dal DB e si adatta.

### Tool del Sales Agent

I tool si dividono in **sempre disponibili** e **attivati per prodotto/pipeline**.

#### Tool sempre disponibili (core vendita)

| # | Tool | Cosa fa |
|---|------|---------|
| 1 | `ask_missing_info` | Data lo stato corrente e i required_fields dalla FSM, chiede al commerciale le info mancanti in modo conversazionale. "Per andare avanti con l'offerta mi servono: budget stimato, timeline, referente tecnico." |
| 2 | `suggest_next_action` | Basandosi su stato, SLA, ultimo contatto, suggerisce cosa fare. "Il cliente non risponde da 5 giorni — vuoi che prepari un follow-up?" |
| 3 | `generate_email_draft` | Genera bozza email per la fase corrente (primo contatto, follow-up, invio offerta, reminder). |
| 4 | `move_deal_stage` | Sposta il deal allo stato successivo. Verifica i required_fields. Se mancano info, le chiede prima. |
| 5 | `log_activity` | Registra attivita (call, meeting, email, nota). Chiede: tipo, soggetto, note. |
| 6 | `get_deal_summary` | Riepilogo deal: stato, prodotto, azienda, contatto, attivita recenti, info mancanti. |
| 7 | `classify_loss` | Quando deal va in Lost: chiede motivo (prezzo, timing, competitor, no-fit, altro). Salva per analytics. |
| 8 | `detect_cross_sell` | Analizza note/conversazioni del deal. Se rileva keyword (documentazione, processi, sviluppo custom, knowledge base) → suggerisce prodotto complementare. |

#### Tool attivati per prodotto T&M

| # | Tool | Quando | Cosa fa |
|---|------|--------|---------|
| 9 | `match_resources` | Qualifica, Match risorse | Incrocia richiesta (stack, seniority, durata) con DB risorse interne. Top 5 profili con match_score. Se zero match → "Non abbiamo risorse disponibili, vuoi procedere con recruiting?" |
| 10 | `calc_margin` | Offerta | Margine = (tariffa - costo) / tariffa. Se < 15%: "Attenzione, margine sotto soglia. Vuoi procedere comunque o rivedere la tariffa?" |
| 11 | `generate_tm_offer` | Offerta | Offerta da template: tariffa per seniority, CV anonimi, condizioni. |
| 12 | `check_bench` | Delivery, sempre | Risorse disponibili o in scadenza contratto. "Marco si libera tra 30gg, vuoi proporlo a un nuovo cliente?" |

#### Tool attivati per prodotto Corpo

| # | Tool | Quando | Cosa fa |
|---|------|--------|---------|
| 13 | `prefill_specs` | Analisi requisiti, Specifiche | Pre-compila scheda specifiche da note call: scope, deliverable, milestone, team necessario. |
| 14 | `estimate_effort` | Specifiche, Offerta | Stima effort (giornate) per scope definito. Calcola costo e prezzo. |
| 15 | `generate_fixed_offer` | Offerta | Offerta a corpo: scope, milestone, prezzo, condizioni di pagamento. |

#### Tool attivati per prodotto Elevia

| # | Tool | Quando | Cosa fa |
|---|------|--------|---------|
| 16 | `score_prospect` | Prospect | Fit score: ATECO (30%) + dimensione (15%) + use case applicabili (25%) + engagement (20%) + decision maker (10%). |
| 17 | `suggest_use_case_bundle` | Prospect, Discovery | Bundle per settore. Metallurgia: UC02+UC04+UC13+UC14. Commercio: UC01+UC03+UC05+UC06+UC15. Chimica: UC02+UC04+UC07+UC09. |
| 18 | `generate_linkedin_message` | Connessione, Engagement | Messaggio personalizzato per fase e settore. Connection request < 200 char, DM < 300 char. Mai pitchare al primo contatto. |
| 19 | `suggest_content` | Engagement | Case study, whitepaper, post per settore. "Per questo prospect metallurgico, condividi il caso Fonderia XYZ." |
| 20 | `calc_warmth_score` | Engagement | Score interazione: connessione accettata +20, risposta +30, like +15, commento +25. Se >60: "E caldo, prenota la call." |
| 21 | `prefill_discovery_brief` | Discovery Call | Brief con pain point probabili per ATECO, use case candidati, domande discovery. |
| 22 | `prepare_demo` | Demo | Config demo per use case identificati, materiale settoriale. |
| 23 | `calc_roi` | Offerta | ROI = ore risparmiate x costo orario medio x 12 mesi - costo Elevia. |
| 24 | `plan_onboarding` | Won, Onboarding | Piano: training per use case, timeline, KPI adozione. |
| 25 | `monitor_adoption` | Onboarding | Login frequency, feature usage, churn alert se adoption < threshold. |
| 26 | `check_linkedin_cadence` | Tutti (Elevia) | "Warm-up fatto? Quanti touchpoint? Prossima azione nella sequenza?" |

### Come l'agente sceglie quali tool usare

```python
# L'agente riceve dal contesto:
deal.product.pipeline_type  # "tm_consulting", "fixed_project", "elevia_product"
deal.current_stage          # "qualifica", "offerta", etc.

# Il tool registry filtra:
available_tools = CORE_TOOLS + PRODUCT_TOOLS[deal.product.pipeline_type]

# Il prompt dell'agente contiene SOLO i tool rilevanti
# → meno confusione per il LLM, risposte migliori
```

### Prompt del Sales Agent

```
Sei l'assistente commerciale di {user_name} per {tenant_name}.

DEAL CORRENTE:
- Azienda: {company_name} ({ateco_code} - {sector})
- Prodotto: {product_name} (pipeline: {pipeline_type})
- Stato: {current_stage} ({stage_description})
- Ultimo contatto: {last_contact} ({days_ago} giorni fa)
- Info mancanti: {missing_fields}

PIPELINE ({pipeline_type}):
{stages_list con stato corrente evidenziato}

TOOL DISPONIBILI:
{solo i tool per questo prodotto/stato}

REGOLE:
1. Sei un assistente, non un controllore. Suggerisci, non imponi.
2. Se mancano info, chiedile in modo naturale: "Per l'offerta mi servirebbe sapere..."
3. Se il deal e fermo da troppo tempo, suggerisci un follow-up.
4. Prepara bozze (email, offerta, messaggio) ma chiedi sempre conferma.
5. Se rilevi opportunita per altri prodotti, segnalalo discretamente.
6. Risposte brevi e pratiche. Il commerciale ha fretta.
```

---

## 3. Controller Agent — "Il ragioniere" (invariato)

Eredita i 17 tool attuali. Nessuna modifica. Gestisce: fatture, prima nota, bilancio, scadenze, F24, CU, budget, SPID, spese, cespiti.

**Estensioni future** (si aggiungono tool, non si cambia l'agente):
- `generate_invoice` → Fatturazione attiva SDI
- `manage_order` → Gestione ordini cliente
- `reconcile_payment` → Riconciliazione incassi Open Banking

---

## 4. Analytics Agent — "L'analista"

| # | Tool | Cosa fa |
|---|------|---------|
| 1 | `predict_cashflow` | Previsione 30/60/90gg |
| 2 | `alert_threshold` | Alert soglie cashflow |
| 3 | `scenario_analysis` | What-if su deal/clienti |
| 4 | `pipeline_analytics` | Weighted pipeline, conversion, velocity per pipeline |
| 5 | `crm_stats` | Win rate, avg deal, attivita per commerciale |
| 6 | `cross_sell_report` | Segnali cross-sell rilevati, suggerimenti |

---

## 5. Orchestratore — Routing semplice

L'orchestratore non ragiona su dominio. Fa tre cose:

1. **Capisce l'intento** (vendita? gestione? analisi?)
2. **Carica il contesto** (deal corrente, prodotto, pipeline, stato)
3. **Passa all'agente giusto** con contesto iniettato

| Segnale | Agente |
|---------|--------|
| Deal attivo / cliente / offerta / LinkedIn / risorsa / margine | Sales Agent |
| Fattura / IVA / F24 / scadenza / bilancio / budget / SPID | Controller Agent |
| Cashflow / trend / KPI / previsione / analytics | Analytics Agent |
| Ambiguo | Chiede: "Vuoi info su un deal o sulla contabilita?" |

### Se non c'e deal attivo

Il Sales Agent funziona anche senza deal context — puo:
- Cercare contatti/aziende
- Mostrare pipeline summary
- Suggerire follow-up su deal fermi
- Mostrare bench risorse disponibili

---

## 6. Context injection

Quando l'orchestratore attiva il Sales Agent:

```python
{
    "tenant_id": "...",
    "user": {"name": "Marco Rossi", "role": "commerciale"},

    # Solo se c'e deal attivo
    "deal": {
        "id": "...",
        "company": "ACME SRL",
        "ateco": "25.11",
        "product": "Consulenza T&M",
        "pipeline_type": "tm_consulting",
        "current_stage": "qualifica",
        "days_in_stage": 3,
        "sla_days": 7,
        "last_contact": "2026-04-04",
        "missing_fields": ["budget", "timeline"],
    },

    # FSM caricata da DB per questo prodotto
    "pipeline_stages": [
        {"code": "lead", "name": "Lead", "required_fields": ["company", "contact"]},
        {"code": "qualifica", "name": "Qualifica", "required_fields": ["budget", "timeline", "match_score"]},
        ...
    ],

    # Tool filtrati per prodotto
    "available_tools": ["ask_missing_info", "suggest_next_action", ..., "match_resources", "calc_margin"],
}
```

---

## 7. Security

| Rischio | Tool | Regola |
|---------|------|--------|
| LOW | score_prospect, calc_warmth, get_deal_summary, suggest_content | Read-only |
| MEDIUM | generate_email_draft, generate_tm_offer, generate_linkedin_message | L'agente prepara la bozza, il commerciale la rivede e conferma |
| HIGH | move_deal_stage, assign_resource, log_activity | Richiede conferma esplicita |
| BLOCKED | Delete deal, modifica pipeline, cambi permessi | Solo admin via UI |

> **Regola d'oro: l'agente PREPARA, il commerciale CONFERMA.**

---

## 8. Estensibilita

Per aggiungere un nuovo prodotto (es. "Formazione"):

1. Admin crea prodotto nel catalogo con `pipeline_type = "training"`
2. Admin crea pipeline "Training": Lead → Analisi bisogni → Programma → Offerta → Won/Lost
3. Opzionalmente: aggiungere tool specifici (es. `generate_training_program`)
4. Il Sales Agent carica automaticamente la nuova pipeline dal DB

Per aggiungere un nuovo agente (es. OrderAgent, HRAgent):

1. Crea file agente con tool specifici
2. Registra nel registry
3. Aggiungi routing keyword nell'orchestratore

**Zero modifiche** agli agenti esistenti.

---

## 9. Checklist implementazione

### Fase 1 — Foundation (2 settimane)

- [ ] Refactor orchestratore: da tool-dispatch a agent-dispatch
- [ ] Agent registry con pattern plugin
- [ ] Sales Agent con 8 tool core
- [ ] Controller Agent: migra 17 tool attuali (zero regressione)
- [ ] Analytics Agent: migra + nuovi tool
- [ ] Context injection: tenant + user + deal + pipeline
- [ ] DB: tabelle pipeline_templates con seed T&M + Corpo + Elevia
- [ ] Test: 809+ test esistenti passano

### Fase 2 — Product Tools (2 settimane)

- [ ] DB: Resource, ResourceSkill (per T&M)
- [ ] DB: EleviaUseCase, AtecoUseCaseMatrix (per Elevia)
- [ ] Tool T&M: match_resources, calc_margin, generate_tm_offer, check_bench
- [ ] Tool Corpo: prefill_specs, estimate_effort, generate_fixed_offer
- [ ] Tool Elevia: score_prospect, linkedin_message, use_case_bundle, warmth_score, roi, adoption
- [ ] Tool filtering per product.pipeline_type
- [ ] Test: 30+ test nuovi

### Fase 3 — Intelligence (2 settimane)

- [ ] Cross-sell detection (keyword analysis su note deal)
- [ ] SLA monitoring + alert
- [ ] LinkedIn cadence tracker (per Elevia)
- [ ] Proactive suggestions basate su stato + tempo
- [ ] Bench alert (per T&M)

### Fase 4 — Future

- [ ] OrderAgent, InvoiceAgent
- [ ] Lead scoring predittivo (ML)
- [ ] Editor visuale FSM
- [ ] WhatsApp Business API
- [ ] LinkedIn API diretta

---

## ADR-010: Coordinator con Sales Agent unico product-aware

**Contesto:** Il commerciale Nexa Data vende T&M, corpo ed Elevia. Non ha senso agenti separati per pipeline — il commerciale e uno, l'agente che lo aiuta deve essere uno.

**Decisione:** Un Sales Agent unico che carica la pipeline dal DB in base al prodotto. I tool specifici si attivano per pipeline_type. L'orchestratore smista tra Sales/Controller/Analytics.

**Motivazione:**
- Snello: un solo prompt per il commerciale, non 3 agenti da gestire
- Flessibile: nuovo prodotto = nuova pipeline nel DB, zero codice
- Pratico: il commerciale parla con "il suo assistente", non sceglie tra agenti
- Il prodotto determina il processo, non il venditore ne il canale (principio v3.0)

**Conseguenze:**
- Il Sales Agent ha piu tool (~26) ma ne vede solo quelli del prodotto corrente (~8-12)
- Prompt dinamico: cambia per ogni deal/prodotto
- Testabilita: ogni set di tool per prodotto testabile separatamente
