# User Stories — Pivot 7: CRM Interno + Email Marketing (Brevo)

> Riferimento: brainstorm/12-crm-interno-brevo-email.md, ADR-009
> Data: 2026-04-03

---

## Epic 1: CRM Interno — Modello Dati e CRUD

### US-87: Modello contatti CRM
**Come** sviluppatore
**Devo** creare il modello crm_contacts nel database
**Per** gestire contatti aziendali interni senza dipendenza Odoo

**Campi**: id, tenant_id, name, type (lead/prospect/cliente/ex_cliente), piva, codice_fiscale, email, phone, website, address, city, province, sector, source, assigned_to, notes, email_opt_in, last_contact_at, created_at, updated_at

**AC-87.1**: CRUD completo su crm_contacts (create, read, update, delete)
**AC-87.2**: Ricerca per nome, P.IVA, email (ILIKE)
**AC-87.3**: Filtro per tipo (lead, prospect, cliente, ex_cliente)
**AC-87.4**: Assegnazione contatto a un commerciale (assigned_to)
**AC-87.5**: Campo email_opt_in per consenso GDPR

**SP**: 3 | **Priorita**: Must Have

---

### US-88: Modello deal CRM con pipeline stages
**Come** sviluppatore
**Devo** creare i modelli crm_deals e crm_pipeline_stages
**Per** gestire la pipeline commerciale internamente

**AC-88.1**: CRUD deal con tutti i campi (contact_id, stage_id, deal_type, revenue, daily_rate, estimated_days, technology, probability)
**AC-88.2**: Pipeline stages configurabili per tenant (nome, sequenza, probabilita default, colore, is_won, is_lost)
**AC-88.3**: Quando un deal cambia stage, la probabilita si aggiorna al default dello stage
**AC-88.4**: Deal type: T&M, fixed, spot, hardware
**AC-88.5**: Ordine cliente: order_type (po, email, firma_word, portale), order_reference, order_date, order_notes
**AC-88.6**: Stages default creati automaticamente al primo accesso tenant (6 stadi)

**SP**: 5 | **Priorita**: Must Have

---

### US-89: Modello attivita CRM
**Come** commerciale
**Voglio** registrare chiamate, email, meeting e note su un deal o contatto
**Per** avere lo storico delle interazioni

**AC-89.1**: CRUD attivita con campi: deal_id, contact_id, user_id, type (call/email/meeting/note/task), subject, description, scheduled_at, completed_at, status
**AC-89.2**: Lista attivita per deal, ordinate per data
**AC-89.3**: Lista attivita per contatto, ordinate per data
**AC-89.4**: Filtro per tipo attivita e status (planned/completed/cancelled)
**AC-89.5**: Aggiorna last_contact_at del contatto quando si completa un'attivita

**SP**: 3 | **Priorita**: Should Have

---

## Epic 2: Vista Kanban Pipeline (stile Trello)

### US-90: Pipeline Kanban con drag-and-drop
**Come** commerciale
**Voglio** vedere i deal come card in colonne (una per stage) e spostarli trascinandoli
**Per** gestire la pipeline in modo visuale e veloce

**AC-90.1**: Vista Kanban con colonne = stages, card = deal
**AC-90.2**: Card mostra: nome deal, cliente, tipo, valore EUR, probabilita, commerciale assegnato
**AC-90.3**: Header colonna mostra: nome stage, conteggio deal, totale valore EUR
**AC-90.4**: Drag-and-drop card tra colonne → PATCH stage via API → aggiorna probabilita
**AC-90.5**: Ottimistic UI: la card si sposta subito, rollback se API fallisce
**AC-90.6**: Toggle Kanban / Tabella (lista)
**AC-90.7**: Su mobile, dropdown per cambiare stage invece di drag-and-drop
**AC-90.8**: Filtri: per commerciale assegnato, tipo deal, valore minimo/massimo

**SP**: 8 | **Priorita**: Must Have

---

### US-91: Pipeline summary e analytics
**Come** direttore commerciale
**Voglio** vedere il riepilogo pipeline con valore per stage e previsioni
**Per** capire l'andamento commerciale

**AC-91.1**: Endpoint GET /crm/pipeline/summary con: total_deals, total_value, by_stage (count + value)
**AC-91.2**: Weighted pipeline value: somma(valore_deal x probabilita) per previsione
**AC-91.3**: Conversion rate tra stages: quanti deal passano da stage N a stage N+1
**AC-91.4**: Average days in stage: tempo medio permanenza per stage
**AC-91.5**: Won/Lost ratio: deal vinti vs persi nel periodo

**SP**: 5 | **Priorita**: Should Have

---

## Epic 3: Email Marketing con Brevo

### US-92: Adapter Brevo per invio email
**Come** sistema
**Devo** integrare Brevo API per inviare email transazionali e marketing
**Per** avere email tracking professionale

**AC-92.1**: Adapter `api/adapters/brevo.py` con metodi: send_email, send_template, get_stats
**AC-92.2**: Invio email con HTML body + variabili sostituite ({{nome}}, {{azienda}}, etc.)
**AC-92.3**: Risposta include brevo_message_id per tracking
**AC-92.4**: Gestione errori: Brevo down → retry con backoff, log errore
**AC-92.5**: Rate limiting rispettato (400/ora piano Starter)

**SP**: 3 | **Priorita**: Must Have

---

### US-93: Webhook email tracking (open, click, bounce)
**Come** sistema
**Quando** Brevo notifica un evento (apertura, click, bounce, unsubscribe)
**Allora** salvo l'evento nel DB e aggiorno lo stato dell'invio

**AC-93.1**: Endpoint POST /email/webhook riceve eventi Brevo
**AC-93.2**: Verifica HMAC signature del webhook (sicurezza)
**AC-93.3**: Evento "opened" → salva in email_events, aggiorna email_sends.opened_at e open_count
**AC-93.4**: Evento "click" → salva con url_clicked, aggiorna email_sends.clicked_at e click_count
**AC-93.5**: Evento "hard_bounce" → segna contatto come email invalida
**AC-93.6**: Evento "unsubscribed" → aggiorna crm_contacts.email_opt_in = false
**AC-93.7**: Evento "spam" → aggiorna crm_contacts.email_opt_in = false + log warning

**SP**: 5 | **Priorita**: Must Have

---

### US-94: Template email con variabili
**Come** commerciale
**Voglio** creare template email con variabili (nome cliente, deal, azienda)
**Per** personalizzare le comunicazioni senza riscrivere ogni volta

**AC-94.1**: CRUD email_templates con: name, subject, html_body, text_body, variables, category
**AC-94.2**: Editor HTML semplice (textarea con preview) — no drag-and-drop builder (Fase 2)
**AC-94.3**: Variabili supportate: {{nome}}, {{azienda}}, {{email}}, {{deal_name}}, {{deal_value}}, {{commerciale}}
**AC-94.4**: Preview template con dati di esempio prima dell'invio
**AC-94.5**: Categorie: welcome, followup, proposal, reminder, nurture
**AC-94.6**: Template default pre-caricati al primo accesso (3-5 template base italiano)

**SP**: 5 | **Priorita**: Must Have

---

### US-95: Invio email singola a contatto
**Come** commerciale
**Voglio** inviare un'email a un contatto usando un template
**Per** comunicare con il cliente con tracking automatico

**AC-95.1**: Da dettaglio contatto o deal, pulsante "Invia email"
**AC-95.2**: Seleziona template, preview con variabili sostituite
**AC-95.3**: Modifica subject/body prima dell'invio (override template)
**AC-95.4**: Invio via Brevo API, salva in email_sends con brevo_message_id
**AC-95.5**: Stato email visibile: inviata → consegnata → letta → cliccata
**AC-95.6**: Storico email inviate visibile nel dettaglio contatto

**SP**: 5 | **Priorita**: Must Have

---

### US-96: Dashboard email analytics
**Come** direttore commerciale
**Voglio** vedere le statistiche delle email inviate
**Per** capire l'efficacia delle comunicazioni

**AC-96.1**: Dashboard con: totale inviate, open rate %, click rate %, bounce rate %
**AC-96.2**: Breakdown per campagna/template
**AC-96.3**: Top contatti che aprono/cliccano
**AC-96.4**: Trend temporale (ultimi 7/30/90 giorni)
**AC-96.5**: Lista contatti con email invalida (bounced)

**SP**: 3 | **Priorita**: Should Have

---

## Epic 4: Sequenze Email Automatiche

### US-97: Sequenze email multi-step
**Come** commerciale
**Voglio** creare sequenze email automatiche (es. follow-up dopo 3 giorni se non risponde)
**Per** automatizzare il nurturing senza intervento manuale

**AC-97.1**: Creazione sequenza: nome, tipo trigger (manual, deal_stage_changed, contact_created)
**AC-97.2**: Step con: template, delay (giorni/ore), condizione (none, if_opened, if_not_opened, if_clicked)
**AC-97.3**: Condizione "if_not_opened": se il contatto NON ha aperto l'email precedente, manda questo step
**AC-97.4**: Condizione "if_opened": se ha aperto, manda step diverso (es. proposta)
**AC-97.5**: Skip step se il contatto ha risposto (reply detection via Brevo)
**AC-97.6**: Workflow engine che processa le sequenze ogni ora (cron/celery)

**SP**: 8 | **Priorita**: Should Have

---

### US-98: Trigger automatici su eventi CRM
**Come** sistema
**Quando** un deal cambia stage o un contatto viene creato
**Allora** avvia automaticamente la sequenza email configurata

**AC-98.1**: Trigger "deal_stage_changed": quando deal entra in uno stage specifico → avvia sequenza
**AC-98.2**: Trigger "contact_created": quando nuovo contatto tipo "lead" → avvia welcome sequence
**AC-98.3**: Trigger configurabile: quale stage, quale sequenza, filtri opzionali
**AC-98.4**: Un contatto non puo essere in due sequenze contemporaneamente dello stesso tipo
**AC-98.5**: Log attivita automatica sul deal quando email viene inviata dalla sequenza

**SP**: 5 | **Priorita**: Should Have

---

## Epic 5: Migrazione da Odoo a CRM Interno

### US-99: Migrazione endpoint CRM da Odoo a DB interno
**Come** sviluppatore
**Devo** migrare i 12 endpoint /crm/* dall'adapter Odoo al service interno
**Per** eliminare la dipendenza Odoo

**AC-99.1**: GET /crm/contacts → query crm_contacts (non piu Odoo)
**AC-99.2**: GET /crm/deals → query crm_deals con JOIN stage (non piu Odoo)
**AC-99.3**: GET /crm/pipeline/summary → aggregazione da crm_deals
**AC-99.4**: POST/PATCH deal → scrive su crm_deals (non piu Odoo)
**AC-99.5**: I 5 tool CRM del chatbot funzionano con il nuovo service
**AC-99.6**: L'adapter odoo_crm.py resta nel codice come integrazione opzionale (non viene eliminato)
**AC-99.7**: Le 3 pagine frontend CRM (Pipeline, DealDetail, Contacts) funzionano senza modifiche (stessi endpoint)

**SP**: 5 | **Priorita**: Must Have

---

## Riepilogo

| Epic | Stories | SP Totali | Priorita |
|------|---------|-----------|----------|
| 1. CRM Modello Dati | US-87, US-88, US-89 | 11 | Must/Should |
| 2. Kanban Pipeline | US-90, US-91 | 13 | Must/Should |
| 3. Email Marketing Brevo | US-92, US-93, US-94, US-95, US-96 | 21 | Must/Should |
| 4. Sequenze Automatiche | US-97, US-98 | 13 | Should |
| 5. Migrazione Odoo→Interno | US-99 | 5 | Must |
| **TOTALE** | **13 stories** | **63 SP** | |

## Sprint suggeriti

| Sprint | Stories | SP | Focus |
|--------|---------|-----|-------|
| Sprint 23 | US-87, US-88, US-89, US-99 | 16 | Modelli DB + migrazione endpoint |
| Sprint 24 | US-90, US-91 | 13 | Kanban drag-and-drop + analytics |
| Sprint 25 | US-92, US-93, US-94 | 13 | Adapter Brevo + webhook + template |
| Sprint 26 | US-95, US-96 | 8 | Invio email + dashboard analytics |
| Sprint 27 | US-97, US-98 | 13 | Sequenze automatiche + trigger |
