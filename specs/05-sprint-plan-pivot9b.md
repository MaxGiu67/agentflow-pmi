# Sprint Plan — Pivot 9b: Framework CRM ElevIA

**Data:** 9 aprile 2026
**Stories:** 7 (US-222→US-228), 47 SP
**Sprint:** 46→47 (~4 settimane, dopo Pivot 10)
**Prerequisito:** Pivot 9 completato (pipeline templates, Sales Agent, Elevia Engine base)
**Principio:** AgentFlow orchestra, Brevo esegue. L'agente suggerisce, l'umano approva. Zero regressione sui 1029+ test esistenti.

---

## Sprint 46: ElevIA Awareness Foundation (2 settimane)

**Goal:** Tag system multi-dimensione funzionante. Lead Magnet come entita CRM. 9 sequenze seeded in Brevo/DB. Base dati pronta per orchestrazione.

| Story | Titolo | SP | Prio |
|-------|--------|:--:|:----:|
| US-222 | Sistema tag contatto multi-dimensione | 8 | Must |
| US-223 | Lead Magnet come entita CRM | 5 | Must |
| US-226 | Seed 9 sequenze ElevIA in Brevo | 8 | Must |

**SP totale:** 21

**Task breakdown:**

### 1. Modello CrmContactTag + Migration (US-222)

- **Tabella `crm_contact_tags`**: id (UUID), tenant_id, contact_id (FK), tag_category (ENUM: awareness/lm/funnel/evento/sequenza), tag_key (VARCHAR 100), tag_value (VARCHAR 255), applied_at (TIMESTAMP), removed_at (TIMESTAMP nullable), applied_by (VARCHAR — user_id o "system"), reason_code (VARCHAR 100 nullable)
- **Index composto**: (tenant_id, contact_id, tag_category, tag_key) per query veloci
- **Index secondario**: (tenant_id, tag_category, tag_value) per analytics aggregati
- **Unique constraint**: (contact_id, tag_category, tag_key, removed_at IS NULL) per impedire tag duplicati attivi
- **Service** `CrmContactTagService`: add_tag(), remove_tag() (soft-delete con removed_at), get_tags(contact_id, category?), get_tag_history(contact_id)
- **Test:** 8+ test (CRUD tag, unicita, soft-delete, storico, index performance con N=100)

### 2. Awareness 1-5 come tag gestito (US-222)

- **Auto-assign**: al create di CrmContact, se non esiste tag awareness → add_tag(category=awareness, key=level, value="1", applied_by="system", reason_code="contact_created")
- **Regole livelli**: 1=Unaware, 2=Problem Aware, 3=Solution Aware, 4=Product Aware, 5=Most Aware
- **Cambio awareness**: remove_tag vecchio (soft-delete) + add_tag nuovo con reason_code obbligatorio
- **Validazione**: awareness accetta solo valori 1-5, salto > 2 livelli genera warning (non blocco)
- **Badge frontend**: nella scheda contatto, badge colorato "Aw1 — Unaware" (colori: grigio/azzurro/verde/arancio/rosso)
- **Regola fondamentale**: download LM → tag LM si aggiunge, awareness NON cambia
- **Test:** 6+ test (auto-assign, cambio con audit, validazione range, regola LM)

### 3. Tag LM, Funnel, Evento, Sequenza (US-222)

- **Tag LM** (cumulativi): category=lm, key=LM_{FORMAT}_{CODE} (es. LM_EB_AI-PMI), value=downloaded
- **Tag Funnel**: category=funnel, key=CM/LTN/Offerta_Chiusa/Ordine_Firmato — ogni transizione con reason_code
- **Tag Evento**: category=evento, key=INTRO_Go_invitato / INTRO_Go_partecipato / INSIGHT_Go_invitato etc.
- **Tag Sequenza**: category=sequenza, key=Welcome_Started / Welcome_Finished / Educational_Started etc.
- **API**:
  - GET /crm/contacts/{id}/tags → raggruppato per category
  - POST /crm/contacts/{id}/tags → add tag (con validazione category)
  - DELETE /crm/contacts/{id}/tags/{tag_id} → soft-delete
  - GET /crm/contacts/{id}/tags/history → storico completo con removed_at
- **Audit log viewer**: tab "Tag" nella scheda contatto con timeline: "2→4 il 15/04 da Pietro (INTRO Go partecipato)"
- **Test:** 8+ test (LM cumulativi, funnel transizione, evento, sequenza, API, audit)

### 4. Modello CrmLeadMagnet + Tracking (US-223)

- **Tabella `crm_lead_magnets`**: id (UUID), tenant_id, code (VARCHAR 50, unique per tenant), name, format (ENUM: ebook/personal_video/eec/microcourse/chatbot), description, landing_page_url, thank_you_page_url, welcome_sequence_id (FK nullable), is_active, created_at
- **Seed**: Ebook "AI per PMI" (code=LM_EB_AI-PMI, format=ebook)
- **Webhook handler** `/webhooks/lm-download`: riceve form submission (Brevo o custom):
  1. Crea/aggiorna CrmContact (upsert su email)
  2. Assegna tag LM (LM_EB_AI-PMI)
  3. Assegna tag funnel=CM (se primo download)
  4. Triggera Welcome sequence (se non gia attiva)
  5. NON aggiorna awareness
- **Multi-download**: secondo LM aggiunge nuovo tag, non interferisce con sequenza in corso
- **CRUD admin** (Impostazioni > Lead Magnet):
  - Lista con colonne: nome, formato, download count, % awareness 2+
  - Form crea/modifica con dropdown formato e URL
  - Toggle attivo/disattivo
- **Endpoint API**:
  - GET/POST/PATCH /crm/lead-magnets
  - GET /crm/lead-magnets/{id}/stats (download, conversion)
  - POST /webhooks/lm-download (webhook esterno)
- **Test:** 8+ test (CRUD, webhook, upsert contact, tag assignment, multi-download, stats)

### 5. Seed 9 sequenze ElevIA (US-226)

- **Dove**: nel DB sequenze interno (tabella `email_sequences` + `email_sequence_steps` gia esistente da Pivot 7) + creazione corrispondente in Brevo via API
- **Sequenze da creare**:

| Sequenza | Email | Timing | Trigger |
|----------|:-----:|--------|---------|
| Welcome | 3 | W1: +0, W2: +2gg, W3: +5gg | tag CM assegnato |
| Educational | 5 | E1: +3gg da W3, poi +7gg ciascuna | Welcome completata + engagement |
| LTN | 13 | Settimanale (ciclico) | Welcome senza engagement O Educational senza INTRO |
| INTRO_Invita | 3 | I1: +0, +3gg, +5gg | tag INTRO_invitato |
| INTRO_Calendar | 3 | -3gg, -1gg, -1h dall'evento | tag INTRO_registrato |
| INTRO_Followup | 3 | +1gg, +4gg, +9gg post-evento | tag INTRO_partecipato |
| INSIGHT_Invita | 3 | +0, +3gg, +5gg | tag INSIGHT_invitato |
| INSIGHT_Calendar | 3 | -3gg, -1gg, -1h dall'evento | tag INSIGHT_registrato |
| INSIGHT_Followup | 4 | +1gg, +4gg, +9gg, +17gg post-evento | tag INSIGHT_partecipato |

- **Template email**: subject + body placeholder con variabili {{nome}}, {{azienda}}, {{settore}}, CTA con link LP — tutti editabili da admin
- **Brevo sync**: service `BrevSequenceSync` che crea/aggiorna le sequenze su Brevo via API (idempotente)
- **Tag automatici**: al start di ogni sequenza → tag sequenza (Welcome_Started), al finish → (Welcome_Finished)
- **Seed script** nel lifespan o migration, idempotente (skip se gia esistono per tenant)
- **Test:** 10+ test (seed idempotente, 9 sequenze create, timing corretto, template con variabili, Brevo sync mock)

### 6. Gate di uscita Sprint 46

- `python3 -m pytest tests/` → tutti i test PASS (esistenti + 40+ nuovi)
- Ruff 0 errori
- TypeScript 0 errori
- Tag system funzionante con API e UI
- Lead Magnet CRUD + webhook operativo
- 9 sequenze seeded nel DB e (mock) su Brevo

---

## Sprint 47: ElevIA Orchestration + Events + KPI (2 settimane)

**Goal:** Eventi INTRO/INSIGHT gestiti. Orchestratore sequenze awareness-driven attivo. Tool ElevIA nel Sales Agent. Dashboard KPI funnel.

| Story | Titolo | SP | Prio |
|-------|--------|:--:|:----:|
| US-224 | Eventi INTRO e INSIGHT | 8 | Must |
| US-227 | Orchestratore sequenze awareness-driven | 8 | Must |
| US-228 | Tool Sales Agent per framework ElevIA | 5 | Must |
| US-225 | KPI Funnel ElevIA | 5 | Should |

**SP totale:** 26

**Task breakdown:**

### 1. Modello CrmEvent + CrmEventAttendee (US-224)

- **Tabella `crm_events`**: id (UUID), tenant_id, event_type (ENUM: intro/insight), service_code (VARCHAR — "Go", "Exec", custom), title, date (TIMESTAMP), location_type (ENUM: online/in_person), location_detail (TEXT — link o indirizzo), capacity (INT nullable), description, is_active, created_at
- **Tabella `crm_event_attendees`**: id (UUID), event_id (FK), contact_id (FK), status (ENUM: invited/registered/attended/no_show), invited_at, registered_at, attended_at, created_at
- **Unique constraint**: (event_id, contact_id) — un contatto non puo essere invitato 2 volte allo stesso evento
- **FullCalendar integration**: eventi INTRO/INSIGHT visibili nel calendario (colore distinto: INTRO=verde, INSIGHT=blu)
- **Test:** 6+ test (CRUD event, attendee status, unique constraint, calendar integration)

### 2. Flusso iscrizione + partecipazione + no-show (US-224)

- **Invito**: POST /crm/events/{id}/invite con body {contact_ids: []}
  - Crea record attendee (status=invited)
  - Assegna tag evento (INTRO_Go_invitato)
  - Attiva sequenza INTRO_Invita (tramite orchestratore)
- **Registrazione**: PATCH /crm/event-attendees/{id} → status=registered
  - Attiva INTRO_Calendar (3 email pre-evento)
- **Partecipazione confermata**: PATCH /crm/event-attendees/{id} → status=attended
  - Tag: INTRO_Go_partecipato
  - Awareness → 4 (con reason_code, applied_by=user — MAI automatico)
  - Attiva INTRO_Followup
- **No-show**: PATCH /crm/event-attendees/{id} → status=no_show
  - Awareness NON avanza
  - INTRO_Followup NON si avvia
  - Commerciale decide se re-invitare
- **Bulk update**: POST /crm/events/{id}/mark-attendance con body {attended: [id1,id2], no_show: [id3]}
- **INSIGHT**: stessa logica ma awareness → 5, Followup ha 4 email, dopo Followup senza risposta → lista manuale (NO LTN)
- **Vista eventi** (Commerciale > Eventi): lista + dettaglio con attendees + azioni bulk
- **Test:** 10+ test (invite, registrazione, partecipazione, no-show, bulk, INSIGHT vs INTRO)

### 3. Orchestratore sequenze (US-227)

- **Service `EleviaSequenceOrchestrator`**: classe central che governa il routing tra sequenze
- **Campo CrmContact**: `active_sequence_id` (FK nullable) — la sequenza attualmente attiva
- **Regola #1 — Una sola sequenza attiva**:
  - Prima di attivare nuova sequenza: pausa quella corrente (tag Paused + punto di pausa salvato)
  - Se la nuova sequenza fallisce/finisce senza progresso → riprende la precedente dal punto di pausa
- **Regola #2 — Stop su risposta** (Brevo webhook `reply`):
  - Pausa immediata sequenza attiva
  - Tag: manual_takeover + timestamp
  - Notifica commerciale (in-app + Slack opzionale)
  - Riprende SOLO su azione esplicita del commerciale
- **Regola #3 — Routing Welcome→Educational/LTN**:
  - Post-W3: check engagement (2+ open O 1 click) → Educational
  - Post-W3 + 30gg senza engagement → LTN
  - Reply → stop + manuale
- **Regola #4 — Routing Educational→INTRO/LTN**:
  - Post-E5: check prenotazione INTRO entro 14gg → INTRO_Invita
  - Post-E5 + 14gg senza prenotazione → LTN
  - Reply → stop + manuale
- **Regola #5 — Awareness 5 = manuale**:
  - Solo INSIGHT_Followup (4 email), poi lista manuale
  - Mai LTN per awareness 5 — e una decisione, non un problema di awareness
- **Regola #6 — Abort on manual outreach**:
  - Se commerciale crea attivita manuale (call/email/meeting) → pausa 7gg
  - Dopo 7gg senza nuova attivita → ripresa automatica
  - Nuova attivita entro 7gg → rinnova pausa
- **Regola #7 — Risveglio da LTN**:
  - Click settimane 5-11 → tag ltn_risvegliato, awareness → 3, LTN pausa, rientra Educational da E3
  - Notifica commerciale
- **Implementazione**: Celery task periodico (ogni 15 min) che valuta i contatti con sequenze attive e applica le regole. Oppure event-driven via Brevo webhook per reattivita immediata su reply/click.
- **Test:** 12+ test (una sola attiva, stop reply, routing W→E, routing E→INTRO, awareness 5, abort, risveglio LTN)

### 4. Tool Sales Agent ElevIA (US-228)

- **5 nuovi tool** nel Sales Agent (filtrati solo per deal Elevia — `pipeline_template.code == "elevia_product"`):

| Tool | Input | Output |
|------|-------|--------|
| `update_awareness` | contact_id, new_level, reason | Conferma con audit trail. Warning se salto > 2 |
| `suggest_sequence` | contact_id | Analisi awareness + tag + engagement → suggerimento azione |
| `event_invite` | contact_id, event_id | Crea attendee + tag + attiva sequenza invito |
| `mark_attendance` | contact_ids[], event_id, status | Bulk update + awareness + followup |
| `funnel_status` | (nessuno) | Distribuzione awareness, LTN count, prossimo evento, conversion |

- **Guardrail**: tutti i tool che modificano dati richiedono conferma umana ("Confermi X? [Si/No]")
- **Context injection**: quando Sales Agent gestisce deal Elevia, il context include: awareness attuale, sequenza attiva, ultimi tag, prossimi eventi
- **Test:** 8+ test (update_awareness con conferma, suggest_sequence, event_invite, mark_attendance bulk, funnel_status, guardrail)

### 5. KPI Funnel ElevIA (US-225)

- **Endpoint** GET /elevia/analytics/funnel?period=30d:
  - `awareness_distribution`: {1: N, 2: N, 3: N, 4: N, 5: N} con percentuali
  - `conversion_rates`: {aw3_to_intro: X%, intro_to_insight: Y%, insight_to_offerta: Z%, offerta_to_ordine: W%}
  - `lm_performance`: per ogni LM → {downloads, pct_aw2_plus, pct_aw3_plus}
  - `ltn_status`: {count, avg_days_in_ltn, awakened_last_quarter}
  - `avg_cycle_days`: {total, cm_to_aw3, aw3_to_intro, intro_to_insight, insight_to_ordine}
- **Widget frontend** (pagina Elevia Analytics o sezione in dashboard commerciale):
  - Funnel visuale awareness 1→5 con barre
  - Card conversion rate per step
  - Tabella LM performance (ordinata per conversion, non volume)
  - Badge "In LTN" con count
- **Calcolo**: query aggregate su crm_contact_tags con GROUP BY tag_value + JOIN su crm_event_attendees per conversion
- **Test:** 6+ test (distribuzione, conversion, LM stats, LTN, ciclo medio, edge case 0 contatti)

### 6. Gate di uscita Sprint 47

- `python3 -m pytest tests/` → tutti i test PASS (esistenti + 42+ nuovi)
- Ruff 0 errori
- TypeScript 0 errori
- Eventi INTRO/INSIGHT gestibili con flusso completo (invito → registrazione → partecipazione/no-show)
- Orchestratore sequenze funzionante (7 regole attive)
- Sales Agent con 5 tool ElevIA operativi
- Dashboard KPI funnel con dati reali

---

## Riepilogo Sprint

| Sprint | Settimane | Stories | SP | Focus |
|--------|:---------:|:-------:|:--:|-------|
| 46 | 2 | US-222, US-223, US-226 | 21 | Tag System + Lead Magnet + Seed Sequenze |
| 47 | 2 | US-224, US-227, US-228, US-225 | 26 | Eventi + Orchestratore + Agent Tool + KPI |
| **TOTALE** | **~4** | **7** | **47** | |

### Verifica copertura tool ElevIA

| Tool | Story | Sprint |
|------|:-----:|:------:|
| update_awareness | US-228 | 47 |
| suggest_sequence | US-228 | 47 |
| event_invite | US-228 | 47 |
| mark_attendance | US-228 | 47 |
| funnel_status | US-228 | 47 |

### Modelli DB nuovi (6 tabelle)

| Tabella | Story | Note |
|---------|:-----:|------|
| crm_contact_tags | US-222 | Tag multi-dimensione con storico |
| crm_lead_magnets | US-223 | Catalogo LM con tracking |
| crm_events | US-224 | Eventi INTRO/INSIGHT |
| crm_event_attendees | US-224 | Iscritti con status workflow |
| *(modifica)* crm_contacts | US-227 | +active_sequence_id FK |
| *(modifica)* email_sequences | US-226 | 9 record seed ElevIA |

### Endpoint API nuovi (~15)

| Endpoint | Story | Metodo |
|----------|:-----:|--------|
| /crm/contacts/{id}/tags | US-222 | GET, POST, DELETE |
| /crm/contacts/{id}/tags/history | US-222 | GET |
| /crm/lead-magnets | US-223 | GET, POST, PATCH |
| /crm/lead-magnets/{id}/stats | US-223 | GET |
| /webhooks/lm-download | US-223 | POST |
| /crm/events | US-224 | GET, POST, PATCH |
| /crm/events/{id}/invite | US-224 | POST |
| /crm/events/{id}/mark-attendance | US-224 | POST |
| /crm/event-attendees/{id} | US-224 | PATCH |
| /elevia/analytics/funnel | US-225 | GET |

---

## Rischi e mitigazioni

| Rischio | Probabilita | Mitigazione |
|---------|:-----------:|-------------|
| Tag system query lente con N>5000 contatti | Media | Index composti + query aggregate con cache (TTL 5min per KPI) |
| Brevo API rate limit su seed 9 sequenze | Bassa | Seed idempotente con retry + backoff, mock in test |
| Orchestratore troppo complesso (7 regole) | Media | Regole come JSON config, non hardcoded. Unit test per ogni regola isolata |
| Conflitto sequenza attiva con azioni manuali | Media | Abort on manual outreach (pausa 7gg) risolve il conflitto |
| Webhook LM download inaffidabile | Bassa | Retry queue + idempotenza (upsert su email), log webhook per debug |
| Sprint 47 sovraccarico (26 SP) | Media | US-225 (KPI) e Should Have — se necessario, slitta a Sprint 48 |

---

## Nota su Sprint numbering

Il Pivot 9b e posizionato su Sprint 46-47 perche:
- Sprint 34-41: Pivot 9 (in spec, da implementare)
- Sprint 42-45: Pivot 10 Portal Integration (COMPLETATO 2026-04-07)
- **Sprint 46-47: Pivot 9b Framework ElevIA**

Il Pivot 9b dipende dal Pivot 9 (pipeline templates + Sales Agent base). L'ordine di implementazione sara: Pivot 9 → Pivot 9b. Il Pivot 10 e gia completato e non interferisce.

---

*Sprint Plan Pivot 9b — Framework CRM ElevIA — 9 aprile 2026*
*Gate di qualita: tutti i test PASS + Ruff 0 + TypeScript 0 + build OK*
