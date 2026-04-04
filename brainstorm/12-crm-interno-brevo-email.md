# Brainstorm 12: CRM Interno + Brevo Email Marketing

> Data: 2026-04-03
> Decisione: ADR-009
> Partecipanti brainstorm: Alessandro (orchestratore), Andrea (MVP scoper), Davide (architect), Nicola (devil's advocate)

---

## 1. Problema

Nexa Data ha 3 commerciali che gestiscono ~100 progetti/anno. Servono:
1. **Pipeline visuale** (Kanban) per tracciare lead → qualificato → proposta → ordine → confermato
2. **Gestione contatti** aziendali con P.IVA, email, telefono
3. **Email tracking** — sapere se il cliente ha letto l'email, cliccato i link
4. **Sequenze email** automatiche — follow-up dopo X giorni, nurture campaign
5. **Registrazione ordine** cliente (PO, email, firma Word, portale)

## 2. Opzioni valutate

### Odoo 18 CRM (ADR-008 — implementata, ora declassata)
- **Pro**: gia implementato (adapter + 12 endpoint + 3 pagine FE)
- **Contro**: dipendenza esterna, latenza API, il CRM interno fa le stesse cose
- **Costo**: 0-93 EUR/mese
- **Verdetto**: non necessario — resta opzionale per bundle clienti

### Keap (ex Infusionsoft) — riesaminato e scartato
- **Pro**: email automation eccellente
- **Contro**: $400+/mese, no italiano, no EUR, acquisita Thryv, API immatura
- **Scorecard aggiornata**: 3/12 (migliorato da 2/12 per pipeline multi)
- **Verdetto**: troppo costoso per troppo poco CRM

### CRM interno + Brevo — SCELTO
- **CRM**: 3 tabelle PostgreSQL (contacts, deals, activities)
- **Email**: Brevo (ex Sendinblue) 25 EUR/mese — invio + tracking via webhook
- **Vista**: Kanban drag-and-drop + tabella (toggle)
- **Costo**: 300 EUR/anno
- **Verdetto**: massimo controllo, minimo costo

## 3. Architettura email tracking (pattern copiato da Keap)

### Cosa copia da Keap:
1. **Open tracking** — Brevo inserisce pixel 1x1, webhook `opened` al nostro server
2. **Click tracking** — Brevo wrappa i link, webhook `clicked` con URL originale
3. **Sequenze** — workflow engine interno: step con delay, condizioni (if opened → step B)
4. **Template con variabili** — {{nome}}, {{azienda}}, {{deal_name}} sostituiti al send
5. **Dashboard email** — open rate, click rate, bounce rate per campagna
6. **Bounce management** — webhook `hard_bounce` → contact marcato invalido
7. **Unsubscribe** — Brevo gestisce il link, webhook `unsubscribed` → contact opt-out

### Cosa NON copia (troppo complesso / non serve):
- Landing page builder (facciamo tutto nel frontend)
- SMS automation (non serve per IT consulting B2B)
- AI content generation (usiamo il nostro chatbot)
- Appointment scheduling (non serve — i meeting li fanno su Teams/Google Meet)

## 4. Modello dati CRM

### crm_contacts
| Campo | Tipo | Note |
|-------|------|------|
| id | UUID | PK |
| tenant_id | UUID | FK Tenant |
| name | String(255) | Ragione sociale |
| type | String(20) | lead, prospect, cliente, ex_cliente |
| piva | String(11) | P.IVA |
| codice_fiscale | String(16) | CF |
| email | String(255) | Email principale |
| phone | String(20) | Telefono |
| website | String(255) | Sito web |
| address | String(500) | Indirizzo completo |
| city | String(100) | Citta |
| province | String(2) | Provincia |
| sector | String(50) | Settore (IT, manifattura, etc.) |
| source | String(50) | Origine (web, referral, evento, cold) |
| assigned_to | UUID | FK User — commerciale assegnato |
| notes | Text | Note libere |
| email_opt_in | Boolean | Consenso email marketing (GDPR) |
| last_contact_at | DateTime | Ultimo contatto |
| created_at | DateTime | |
| updated_at | DateTime | |

### crm_pipeline_stages
| Campo | Tipo | Note |
|-------|------|------|
| id | UUID | PK |
| tenant_id | UUID | FK Tenant |
| name | String(100) | Nome stage (Nuovo Lead, Qualificato, ...) |
| sequence | Integer | Ordine visualizzazione |
| probability_default | Float | Probabilita default (10%, 30%, 50%, 80%, 100%) |
| color | String(7) | Colore hex (#3B82F6) |
| is_won | Boolean | Stage "vinto" (confermato) |
| is_lost | Boolean | Stage "perso" |
| created_at | DateTime | |

### crm_deals
| Campo | Tipo | Note |
|-------|------|------|
| id | UUID | PK |
| tenant_id | UUID | FK Tenant |
| contact_id | UUID | FK crm_contacts |
| stage_id | UUID | FK crm_pipeline_stages |
| name | String(300) | Nome opportunita |
| deal_type | String(20) | T&M, fixed, spot, hardware |
| expected_revenue | Float | Valore atteso EUR |
| daily_rate | Float | Tariffa giornaliera (per T&M) |
| estimated_days | Float | Giorni stimati |
| technology | String(255) | Stack tecnologico |
| probability | Float | Probabilita % |
| assigned_to | UUID | FK User — commerciale |
| expected_close_date | Date | Data chiusura prevista |
| order_type | String(20) | po, email, firma_word, portale |
| order_reference | String(100) | Numero PO / ODA |
| order_date | Date | Data ricezione ordine |
| order_notes | Text | Note ordine |
| lost_reason | String(255) | Motivo perdita (se perso) |
| created_at | DateTime | |
| updated_at | DateTime | |

### crm_activities
| Campo | Tipo | Note |
|-------|------|------|
| id | UUID | PK |
| tenant_id | UUID | FK Tenant |
| deal_id | UUID | FK crm_deals (nullable per attivita su contatto) |
| contact_id | UUID | FK crm_contacts |
| user_id | UUID | FK User — chi ha fatto l'attivita |
| type | String(20) | call, email, meeting, note, task |
| subject | String(255) | Titolo |
| description | Text | Dettaglio |
| scheduled_at | DateTime | Data/ora pianificata |
| completed_at | DateTime | Data/ora completamento |
| status | String(20) | planned, completed, cancelled |
| created_at | DateTime | |

### email_templates
| Campo | Tipo | Note |
|-------|------|------|
| id | UUID | PK |
| tenant_id | UUID | FK Tenant |
| name | String(100) | Nome template |
| subject | String(255) | Oggetto email (con variabili {{...}}) |
| html_body | Text | Corpo HTML (con variabili) |
| text_body | Text | Corpo testo plain (fallback) |
| variables | JSON | Lista variabili disponibili |
| category | String(50) | welcome, followup, proposal, reminder, nurture |
| active | Boolean | Attivo/disattivo |
| created_at | DateTime | |
| updated_at | DateTime | |

### email_campaigns
| Campo | Tipo | Note |
|-------|------|------|
| id | UUID | PK |
| tenant_id | UUID | FK Tenant |
| name | String(200) | Nome campagna |
| type | String(20) | single (broadcast), sequence (drip), trigger (evento) |
| trigger_event | String(50) | deal_stage_changed, contact_created, manual |
| trigger_config | JSON | Condizioni trigger ({stage: "Proposta Inviata"}) |
| status | String(20) | draft, active, paused, completed |
| stats_sent | Integer | Totale inviate |
| stats_opened | Integer | Totale aperte |
| stats_clicked | Integer | Totale click |
| stats_bounced | Integer | Totale bounce |
| created_at | DateTime | |
| updated_at | DateTime | |

### email_sequence_steps
| Campo | Tipo | Note |
|-------|------|------|
| id | UUID | PK |
| campaign_id | UUID | FK email_campaigns |
| step_order | Integer | Ordine step (1, 2, 3...) |
| template_id | UUID | FK email_templates |
| delay_days | Integer | Giorni di attesa dopo step precedente |
| delay_hours | Integer | Ore di attesa (per sequenze rapide) |
| condition_type | String(30) | none, if_opened, if_not_opened, if_clicked |
| condition_link | String(500) | URL specifico per condizione if_clicked |
| skip_if_replied | Boolean | Salta step se il contatto ha risposto |
| created_at | DateTime | |

### email_sends
| Campo | Tipo | Note |
|-------|------|------|
| id | UUID | PK |
| tenant_id | UUID | FK Tenant |
| campaign_id | UUID | FK email_campaigns (nullable per singole) |
| step_id | UUID | FK email_sequence_steps (nullable) |
| contact_id | UUID | FK crm_contacts |
| template_id | UUID | FK email_templates |
| brevo_message_id | String(100) | ID messaggio Brevo (per tracking) |
| subject_sent | String(255) | Subject effettivamente inviato |
| sent_at | DateTime | |
| status | String(20) | queued, sent, delivered, opened, clicked, bounced, failed |
| opened_at | DateTime | Prima apertura |
| clicked_at | DateTime | Primo click |
| open_count | Integer | Numero aperture totali |
| click_count | Integer | Numero click totali |

### email_events
| Campo | Tipo | Note |
|-------|------|------|
| id | UUID | PK |
| send_id | UUID | FK email_sends |
| event_type | String(20) | delivered, opened, clicked, hard_bounce, soft_bounce, unsubscribed, spam |
| url_clicked | String(500) | URL cliccato (per evento clicked) |
| ip_address | String(45) | IP destinatario |
| user_agent | String(500) | Browser/client email |
| timestamp | DateTime | Timestamp evento Brevo |
| raw_payload | JSON | Payload webhook completo (debug) |
| created_at | DateTime | |

## 5. Pipeline stages default

| Seq | Nome | Probabilita | Colore | Won/Lost |
|-----|------|-------------|--------|----------|
| 1 | Nuovo Lead | 10% | #6B7280 (gray) | - |
| 2 | Qualificato | 30% | #3B82F6 (blue) | - |
| 3 | Proposta Inviata | 50% | #F59E0B (amber) | - |
| 4 | Ordine Ricevuto | 80% | #F97316 (orange) | - |
| 5 | Confermato | 100% | #10B981 (green) | won |
| 6 | Perso | 0% | #EF4444 (red) | lost |

## 6. Flusso email tracking (Brevo webhook)

```
1. AgentFlow invia email via Brevo API (POST /v3/smtp/email)
   → Brevo risponde con messageId
   → Salva in email_sends.brevo_message_id

2. Brevo traccia apertura (pixel 1x1)
   → Webhook POST /api/v1/email/webhook
   → Payload: {event: "opened", messageId: "xxx", date: "..."}
   → Salva in email_events, aggiorna email_sends.opened_at

3. Brevo traccia click (link redirect)
   → Webhook POST /api/v1/email/webhook
   → Payload: {event: "click", messageId: "xxx", link: "https://...", date: "..."}
   → Salva in email_events, aggiorna email_sends.clicked_at

4. Workflow engine controlla condizioni sequenza
   → Se step successivo ha condition_type = "if_opened"
   → Verifica email_sends.opened_at IS NOT NULL
   → Se si → schedula prossimo step
   → Se no → salta o attende
```

## 7. Vista Kanban (stile Trello)

### Layout
- Colonne orizzontali, una per stage (scrollabile)
- Card deal con: logo/iniziali cliente, nome deal, tipo, valore EUR, assegnato a
- Drag-and-drop tra colonne → PATCH stage
- Header colonna: nome stage, count deal, totale EUR
- Footer: "+ Nuovo deal" per creare inline

### Interazioni
- Click card → apre dettaglio deal (slide-over o pagina)
- Drag card → aggiorna stage + probabilita (ottimistic UI)
- Filtri: per commerciale, tipo deal, valore min/max
- Toggle: Kanban / Tabella
- Mobile: select dropdown invece di drag-and-drop

### Libreria
- `@dnd-kit/core` + `@dnd-kit/sortable` (React, leggero, accessibile)
- Alternativa: `@hello-pangea/dnd` (fork di react-beautiful-dnd)

## 8. Brevo configurazione

### API
- Endpoint: `https://api.brevo.com/v3/`
- Auth: `api-key` header
- Invio email: `POST /v3/smtp/email`
- Template: possiamo usare i template Brevo OPPURE inviare HTML diretto
- Webhook: configurabile da dashboard Brevo → URL nostro
- Rate limit: 400 email/ora (piano Starter), scalabile

### Variabili .env
```env
BREVO_API_KEY=xkeysib-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
BREVO_WEBHOOK_SECRET=random-32-bytes-hex
BREVO_SENDER_EMAIL=commerciale@nexadata.it
BREVO_SENDER_NAME=Nexa Data
```

### Webhook URL da configurare in Brevo
`https://api.agentflow.nexadata.it/api/v1/email/webhook`

### Eventi webhook da attivare
- delivered, opened, click, hard_bounce, soft_bounce, unsubscribed, spam
