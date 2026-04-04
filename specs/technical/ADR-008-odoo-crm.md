# ADR-008: Odoo 18 come CRM Esterno (non contabile)

**Data:** 2026-04-02
**Stato:** APPROVATA
**Decisori:** Massimiliano Giurelli (Nexa Data)

---

## Contesto

Nexa Data e una societa di consulenza IT con 3 commerciali, 65 risorse e ~100 progetti/anno. Il modello di business comprende:
- **T&M** (Time & Material): tariffa giornaliera × giorni
- **Fixed price**: progetti a corpo
- **Spot consulting**: 3-150 giorni/uomo
- **Vendita hardware**

Le offerte sono tutte in Word con template. Serve un CRM per gestire il ciclo commerciale pre-vendita: pipeline → offerta → ordine cliente → conferma. Dopo la conferma dell'ordine, il commerciale crea la "commessa" nel sistema proprietario Nexa Data.

AgentFlow PMI ha gia un engine contabile interno (ADR-007) e NON serve Odoo per la contabilita. Il timesheet e il billing sono su applicativi proprietari Nexa Data con API REST — Odoo CRM NON ha accesso a questi dati (nessun write-back).

## Decisione

**Odoo 18 Online** come CRM esterno per il ciclo pre-vendita (pipeline → offerta → ordine cliente → conferma), integrato in AgentFlow PMI via adapter JSON-RPC.

### Perche Odoo e non altri

| CRM | Score | Motivo esclusione/scelta |
|-----|-------|--------------------------|
| **Odoo 18** | **10/12** | Pipeline personalizzabile, campi custom (x_), API JSON-RPC, localizzazione IT, €93/mese (3 utenti) |
| Teamleader | 8/12 | Buono per PMI, ma meno personalizzabile dei campi custom Odoo |
| Pipedrive | 6/12 | No T&M nativo, no localizzazione italiana |
| HubSpot | 3/12 | Overkill per 3 utenti, costo esplosivo con contatti |
| **Keap** | **2/12** | E-commerce/marketing automation, inadeguato per IT consulting/body rental |

### Perche NON Keap

1. Progettato per e-commerce e marketing automation, non per servizi IT
2. Nessun supporto T&M (tariffa giornaliera × giorni)
3. Nessuna gestione risorse/body rental
4. Pipeline rigida, non personalizzabile per deal type diversi
5. Localizzazione italiana assente
6. Prezzo alto per quello che offre a un'azienda di consulenza

## Architettura

```
┌─────────────────────────────────────────────────────────────┐
│                     AgentFlow PMI                            │
│                                                             │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   │
│  │ Orchestrator  │   │ CRM Module   │   │ Other Modules│   │
│  │ (7 agenti)   │──▶│ router.py    │   │ (49 moduli)  │   │
│  │              │   │ service.py   │   │              │   │
│  │ tool: crm_*  │   │ schemas.py   │   │              │   │
│  └──────────────┘   └──────┬───────┘   └──────────────┘   │
│                            │                                │
│                   ┌────────▼────────┐                      │
│                   │ odoo_crm.py     │                      │
│                   │ (adapter async) │                      │
│                   │ JSON-RPC client │                      │
│                   └────────┬────────┘                      │
└────────────────────────────┼────────────────────────────────┘
                             │ HTTPS / JSON-RPC
                    ┌────────▼────────┐
                    │   Odoo 18       │
                    │   Online CRM    │
                    │   (SaaS)        │
                    │                 │
                    │ res.partner     │
                    │ crm.lead        │
                    │ crm.stage       │
                    └─────────────────┘
```

### Flusso dati

**Odoo → AgentFlow:**
- Pipeline deal (crm.lead) con fasi, valore, probabilita
- Contatti aziendali (res.partner)
- Riepilogo pipeline per l'agente conversazionale
- Ordini ricevuti (stage=Ordine Ricevuto) per revisione

**AgentFlow → Odoo:**
- Registrazione ordine cliente: POST /deals/{id}/order salva x_order_type, x_order_reference, x_order_date, x_order_notes
- Conferma ordine: POST /deals/{id}/order/confirm porta il deal in stage Confermato

**NON è previsto (RIMOSSO):**
- Write-back ore/giorni consumati dal timesheet (Odoo non è responsabile della contabilità)
- Write-back importo fatturato dal billing (Odoo non è responsabile della contabilità)
- Sincronizzazione pagamenti/fatturazione tra Odoo e AgentFlow

**Webhook (futuro):**
- Odoo Automated Action su deal confermato → POST /webhook/deal-confirmed → crea commessa nel sistema Nexa Data

## Campi Custom Odoo (prefisso x_)

| Campo | Tipo | Uso |
|-------|------|-----|
| x_deal_type | Selection | T&M, fixed, spot, hardware |
| x_daily_rate | Float | Tariffa giornaliera (€) |
| x_estimated_days | Float | Giorni/uomo stimati |
| x_technology | Char | Stack tecnologico (Java, .NET, PHP...) |
| x_order_type | Selection | Tipo ordine: PO, email, firma_word, portale |
| x_order_reference | Char | Numero/riferimento ordine cliente |
| x_order_date | Date | Data ordine |
| x_order_notes | Text | Note aggiuntive ordine |

## Pipeline Stages (Odoo)

| Fase | Descrizione |
|------|-------------|
| Nuovo Lead | Primo contatto con potenziale cliente |
| Qualificato | Lead qualificato, merita proposta |
| Proposta Inviata | Offerta inviata al cliente |
| Ordine Ricevuto | Ordine ricevuto dal cliente (campi x_order_* compilati) |
| Confermato | Ordine confermato, passato a commessa in Nexa Data |

## Configurazione

```env
ODOO_URL=https://nexadata.odoo.com
ODOO_DB=nexadata
ODOO_USER=mgiurelli@taal.it
ODOO_API_KEY=<generata da Preferenze > Sicurezza Account > Nuova API Key>
ODOO_WEBHOOK_SECRET=<secret per validare webhook in ingresso>
```

## Conseguenze

### Positive
- CRM professionale senza sviluppo da zero
- Commerciali usano Odoo direttamente per gestire pipeline
- AgentFlow ha visibilita sulla pipeline via agente "crm"
- Gestione ordini cliente tracciata in Odoo (storia completa)
- Costo contenuto: €93/mese
- Separazione netta tra pre-vendita (Odoo) e gestione progetti/contabilità (Nexa Data + AgentFlow)

### Negative
- Dipendenza Odoo per il CRM (mitigata: adapter astratto, sostituibile)
- Rate limit ~60 req/min su Odoo Online (mitigato: caching in-memory)
- Campi custom richiedono configurazione manuale in Odoo
- Passaggio ordine da Odoo a Nexa Data richiede azione manuale del commerciale (non automatizzato)

### Rischi
- Odoo Online potrebbe cambiare API → mitigato con adapter isolato
- Latenza JSON-RPC → mitigata con caching per dati non critici
- Sincronizzazione ordine→commessa potrebbe fallire se Nexa Data non disponibile → gestito con retry/queue

## Opportunita: Odoo Partnership Program e Multi-Tenant (2026-04-02)

### Contesto

Odoo ha contattato Nexa Data (Achraf Kanice, acka@odoo.com, +32 2 616 86 72) per aderire al Partnership Program. Questo apre la possibilita per Nexa Data di rivendere licenze Odoo ai propri clienti con margine. Contemporaneamente, 4-5 clienti di Nexa Data sono gia interessati ad AgentFlow PMI con integrazione CRM Odoo.

### Implicazioni Architetturali

**Multi-Tenant Readiness:**
- Ogni cliente Nexa Data puo avere una propria istanza Odoo (SaaS separate) o un database Odoo distinto (on-prem)
- AgentFlow PMI rimane centralizzato ma supporta multi-tenancy via tenant router (EPIC 13)
- Adapter `api/adapters/odoo_crm.py` accetta `odoo_instance_url` per tenant — ogni tenant configura il suo endpoint Odoo

**Per-Client Configuration:**
- Variabili env divengono per-tenant:
  - `ODOO_URL_{tenant_id}` — indirizzo istanza Odoo del cliente
  - `ODOO_DB_{tenant_id}` — database Odoo del cliente
  - `ODOO_API_KEY_{tenant_id}` — API key del cliente in Odoo
- Endpoint CRM restano centralizzati: `GET /api/{tenant_id}/deals`, `POST /api/{tenant_id}/deals`, etc.

**Separazione Responsabilita:**
- **Odoo**: Pre-vendita (pipeline, lead, contatti, ordini) — visibile ai commerciali del cliente
- **AgentFlow**: Gestione progetti, contabilita, compliance — visibile a CEO/CFO del cliente
- Webhook Odoo → AgentFlow permette al cliente di creare una "commessa" in AgentFlow non appena l'ordine è confermato in Odoo

### Revenue Model

- Nexa Data diventa Odoo Partner e addebita Odoo (€93/mese base) al cliente + margine
- Nexa Data vende AgentFlow PMI come bundle: contabilita agentica + CRM Odoo integrato
- Per clienti IT consulting, il bundle costi ca. €200-300/mese (Odoo + AgentFlow + hosting)
- 4-5 clienti rappresentano un TAM iniziale di ~€1k-1.5k/mese in MRR

### Roadmap

1. Test interno: Nexa Data usa Odoo CRM + AgentFlow per 30 giorni (validare l'integrazione, formare commerciali)
2. Formalizzare Odoo Partnership (agreement legale, provisioning)
3. Completare EPIC 13 (multi-tenant infrastructure)
4. Commercializzare bundle ai 4-5 clienti interessati
