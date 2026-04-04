# User Stories — Pivot 8: Social Selling Configurabile
**AgentFlow PMI — CRM B2B per PMI italiane**

---

## Overview

Il Pivot 8 aggiunge 5 moduli configurabili per social selling:
1. **M1 — Origini Configurabili** (Custom sources per contatti)
2. **M2 — Attività Custom e Pre-funnel** (Tipi di attività e stadi pre-pipeline)
3. **M3 — Ruoli e Collaboratori Esterni** (RBAC, utenti con scadenza, audit trail)
4. **M4 — Catalogo Prodotti** (Prodotti/servizi, pricing, deal associations)
5. **M5 — Analytics e Compensi** (Dashboard KPI, scorecard, modello compensi)

Le stories partono da **US-130** e seguono il template:
- 4+ AC per story (1 happy path, 2 error/edge, 1 boundary)
- Story Points 1-13
- Priorità MoSCoW
- Format DATO-QUANDO-ALLORA

---

## EPIC 1: Origini Configurabili

### US-130: Admin definisce origine contact custom

**Come** admin di un tenant AgentFlow
**Voglio** creare una nuova origine contact (es. "LinkedIn Sales", "Referral", "Webinar")
**Per** categorizzare i contatti secondo i canali di acquisizione specifici della mia azienda

**AC-130.1 (Happy Path)**: DATO che sono loggato come admin, QUANDO accedo a Impostazioni > Origini e clicco "Nuova origine", ALLORA:
  - La form contiene campi: Codice (univoco per tenant), Etichetta, Canale padre (select), Icona (picker), Attivo (checkbox)
  - La form valida che Codice non sia vuoto, univoco nel tenant, max 50 caratteri
  - Al submit, l'origine viene salvata in `crm_contact_origins` e appare nella lista

**AC-130.2 (Error - Codice duplicato)**: DATO che l'origine "linkedin" esiste già per il mio tenant, QUANDO creo una nuova origine con codice "linkedin", ALLORA:
  - Il sistema mostra errore "Codice origine già esistente per questo tenant"
  - La form non invia il submit e rimane in state editing

**AC-130.3 (Edge - Canale padre nullo)**: DATO che creo un'origine senza selezionare Canale padre, QUANDO salvo, ALLORA:
  - Il sistema accetta il salvataggio (canale_padre = NULL)
  - L'origine rimane valida per l'assegnazione ai contatti

**AC-130.4 (Boundary - Numero massimo)**: DATO che il tenant ha già 100 origini attive, QUANDO cerco di crearne una nuova, ALLORA:
  - Il sistema consente il salvataggio senza limite tecnico (limite business eventuale in altro momento)

**SP**: 5 | **Priorità**: Must Have | **Epic**: Origini Configurabili | **Dipendenze**: Nessuna

---

### US-131: Admin modifica/disattiva origine

**Come** admin
**Voglio** modificare o disattivare un'origine (codice immutabile, etichetta/canale/icona modificabili)
**Per** mantenere la configurazione delle origini aggiornata con la strategia commerciale

**AC-131.1 (Happy Path)**: DATO che seleziono un'origine dalla lista, QUANDO clicco "Modifica", ALLORA:
  - La form mostra i valori attuali (codice disabilitato/read-only, altri editable)
  - Al submit, salvo le modifiche e torno alla lista con toast "Origine aggiornata"

**AC-131.2 (Disattivazione)**: DATO che un'origine ha contatti associati, QUANDO la disattivo, ALLORA:
  - I contatti rimangono associati all'origine disattivata
  - L'origine disattivata NON appare nei dropdown di new contact
  - La tabella origini mostra icona/badge "Disattivata"

**AC-131.3 (Error - Codice non modificabile)**: DATO che cerco di modificare il codice di un'origine, ALLORA:
  - Il campo codice è disabilitato (read-only visibile)
  - Se invio form, il codice rimane invariato nel DB

**AC-131.4 (Boundary - Delete origin with contacts)**: DATO che un'origine ha 50 contatti associati, QUANDO cerco di cancellarla, ALLORA:
  - Il sistema NON permette il delete (mostra errore "Non puoi eliminare un'origine con contatti associati")
  - L'admin DEVE disattivare l'origine (soft delete logic)

**SP**: 3 | **Priorità**: Must Have | **Epic**: Origini Configurabili | **Dipendenze**: US-130

---

### US-132: Migrare campo source in crm_contacts a origine FK

**Come** system administrator
**Voglio** migrare il campo `source` (stringa) in crm_contacts a una FK verso la nuova tabella `crm_contact_origins`
**Per** garantire integrità referenziale e queryability sulle origini

**AC-132.1 (Migration happy path)**: DATO che il Pivot 8 viene deployato, QUANDO la migration corre, ALLORA:
  - Viene creata tabella `crm_contact_origins` con colonne: id, tenant_id, code, label, parent_channel, icon_name, is_active, created_at, updated_at
  - Viene aggiunto indice UNIQUE (tenant_id, code)
  - Viene creato campo `origin_id` (FK, nullable) in crm_contacts

**AC-132.2 (Data preservation)**: DATO che il tenant ha contatti con source = "LinkedIn", QUANDO la migration esegue la data transformation, ALLORA:
  - Viene creata automaticamente un'origine con code="LinkedIn", label="LinkedIn" per il tenant
  - Tutti i contatti con source="LinkedIn" sono riallocati a origin_id della nuova origine
  - Il campo source (vecchio) rimane per rollback temporaneo

**AC-132.3 (Null handling)**: DATO che alcuni contatti hanno source = NULL, QUANDO la migration esegue, ALLORA:
  - Il campo origin_id rimane NULL
  - La validazione al salvataggio del contatto rende origin_id obbligatorio

**AC-132.4 (Rollback safety)**: DATO che la migration deve rollare back per qualche motivo, QUANDO eseguo il down, ALLORA:
  - Il campo source viene ripopolato dai dati salvati
  - La tabella crm_contact_origins viene droppata

**SP**: 8 | **Priorità**: Must Have | **Epic**: Origini Configurabili | **Dipendenze**: US-130, US-131

---

### US-133: Assegnare origine obbligatoria al contact

**Come** user che crea/modifica un contatto
**Voglio** selezionare una origine (required field) dalla lista di origini attive
**Per** categorizzare correttamente il canale di acquisizione del contatto

**AC-133.1 (Happy Path)**: DATO che apro il form di new contact, QUANDO seleziono un'origine dal dropdown, ALLORA:
  - Il dropdown mostra solo origini attive (is_active = true) del mio tenant
  - Selezionando, il valore è salvato in origin_id del contatto
  - Nell'UI del contact detail, l'origine è visualizzata con icona e etichetta

**AC-133.2 (Validation - Required)**: DATO che cerco di salvare un contatto senza selezionare un'origine, ALLORA:
  - Il sistema mostra errore "Origine obbligatoria"
  - Il form non permette submit finché non seleziono un'origine

**AC-133.3 (Bulk action - Change origin)**: DATO che seleziono 10 contatti dalla lista, QUANDO eseguo azione bulk "Cambia origine", ALLORA:
  - Si apre dialog con dropdown origine
  - Al submit, tutti i 10 contatti sono riallocati alla nuova origine
  - Log audit registra l'azione per tenant + admin che l'ha eseguita

**AC-133.4 (Edge - Origin becomes inactive)**: DATO che un contatto ha origine="LinkedIn" (attiva), QUANDO l'admin disattiva tale origine, ALLORA:
  - Il contatto rimane associato all'origine disattivata
  - Se cerco di modificare il contatto, l'origine disattivata è visibile ma NON più selezionabile per nuovi contatti

**SP**: 5 | **Priorità**: Must Have | **Epic**: Origini Configurabili | **Dipendenze**: US-130, US-132

---

## EPIC 2: Attività Custom e Pre-funnel

### US-134: Admin definisce tipo attività custom

**Come** admin di un tenant
**Voglio** creare un tipo di attività custom (es. "Inmail LinkedIn", "Commento Post", "Story View")
**Per** tracciare tutte le interazioni social e non standard che il mio team fa

**AC-134.1 (Happy Path)**: DATO che sono in Impostazioni > Tipi attività, QUANDO clicco "Nuovo tipo", ALLORA:
  - Form contiene: Codice, Etichetta, Categoria (select: Sales Activity / Marketing / Customer Support), Conta come ultimo contatto (checkbox)
  - Codice è univoco per tenant, max 50 caratteri
  - Al submit, tipo viene salvato in `crm_activity_types` con tenant_id

**AC-134.2 (Error - Codice duplicato)**: DATO che tipo "inmail_linkedin" esiste già, QUANDO creo un nuovo tipo con lo stesso codice, ALLORA:
  - Errore "Codice tipo attività già esistente"
  - Form rimane in state edit

**AC-134.3 (Flag "Conta come ultimo contatto")**: DATO che creo tipo "Inmail LinkedIn" e attivo il flag, QUANDO un'attività di questo tipo viene loggata, ALLORA:
  - Il campo `contact.last_contact_at` viene aggiornato al timestamp dell'attività
  - Se il flag è disattivo, `last_contact_at` rimane invariato

**AC-134.4 (Boundary - Categoria e stato)**: DATO che creo un tipo con categoria "Marketing", QUANDO uso il tipo in un'attività, ALLORA:
  - L'attività eredita la categoria per analytics/filtering
  - Categoria serve solo per raggruppamento, non per logica di business

**SP**: 5 | **Priorità**: Must Have | **Epic**: Attività Custom e Pre-funnel | **Dipendenze**: Nessuna

---

### US-135: Admin modifica/disattiva tipo attività

**Come** admin
**Voglio** modificare o disattivare un tipo di attività (codice immutabile)
**Per** mantenere i tipi di attività allineati con i processi commerciali

**AC-135.1 (Happy Path)**: DATO che seleziono un tipo di attività, QUANDO clicco "Modifica", ALLORA:
  - Codice è read-only
  - Etichetta, Categoria, Flag "Conta ultimo contatto" sono editable
  - Al submit, le modifiche sono salvate

**AC-135.2 (Soft delete)**: DATO che un tipo ha 200 attività già loggati, QUANDO disattivo il tipo, ALLORA:
  - Le attività esistenti rimangono collegate al tipo disattivato (immutabile storico)
  - Il tipo disattivato NON appare nei dropdown per nuove attività
  - Admin vede badge "Disattivato" nella lista

**AC-135.3 (Error - Cannot hard delete)**: DATO che cerco di cancellare un tipo, ALLORA:
  - Il sistema NON offre opzione "Elimina" (solo Disattiva)
  - Se inviato diretto su API DELETE, il sistema ritorna 409 Conflict

**AC-135.4 (Boundary - Last active type)**: DATO che il tenant ha solo 1 tipo attività attivo, QUANDO cerco di disattivarlo, ALLORA:
  - Il sistema permette il disattivamento
  - Toast warning: "Nessun tipo attività attivo. Nessuna attività potrà essere loggata."

**SP**: 3 | **Priorità**: Should Have | **Epic**: Attività Custom e Pre-funnel | **Dipendenze**: US-134

---

### US-136: Admin definisce stadi pre-funnel nella pipeline

**Come** admin
**Voglio** aggiungere stadi pre-funnel (es. "Prospect", "Contatto Qualificato") prima di "Nuovo Lead" nella pipeline
**Per** tracciare la progressione del contatto prima che diventi un'opportunità formale

**AC-136.1 (Happy Path)**: DATO che sono in Impostazioni > Pipeline stages, QUANDO clicco "Aggiungi stadio pre-funnel", ALLORA:
  - Form contiene: Nome, Sequenza (numero), Probabilità (0-100%), Colore, Tipo stadio (select: "pre_funnel" / "pipeline"), Attivo
  - Posso inserire uno stadio prima di "Nuovo Lead" (sequence < del Nuovo Lead)
  - Al submit, stadio è salvato in `crm_pipeline_stages` con `stage_type = 'pre_funnel'`

**AC-136.2 (Sequenza e ordinamento)**: DATO che i miei stadi pre-funnel sono: Prospect (seq=1), Contatto Qualificato (seq=2), Nuovo Lead (seq=3), QUANDO visualizzo la pipeline Kanban, ALLORA:
  - Le colonne appaiono in ordine: Prospect > Contatto Qualificato > Nuovo Lead > (stadi standard)
  - Posso trascinare deal tra le colonne e cambiano stage automaticamente

**AC-136.3 (Error - Sequenza invalida)**: DATO che cerco di creare uno stadio pre-funnel con sequenza DOPO il "Nuovo Lead", ALLORA:
  - Il sistema valida e mostra errore "Stadi pre-funnel devono avere sequenza prima di 'Nuovo Lead'"
  - Form non permette submit

**AC-136.4 (Boundary - Deal creation)**: DATO che creo un deal in uno stadio pre-funnel, QUANDO il deal raggiunge "Nuovo Lead", ALLORA:
  - Il deal transita in "Nuovo Lead" (no validazione blocco)
  - Analytics conta il passaggio nel pipeline standard solo da "Nuovo Lead" in poi

**SP**: 5 | **Priorità**: Should Have | **Epic**: Attività Custom e Pre-funnel | **Dipendenze**: Nessuna

---

### US-137: User logga attività con tipo custom

**Come** sales user
**Voglio** creare una nuova attività di tipo custom (es. "Inmail LinkedIn"), associandola a un contatto o deal
**Per** tracciare tutte le interazioni che faccio con i prospect

**AC-137.1 (Happy Path)**: DATO che apro il contact detail, QUANDO clicco "Nuova attività", ALLORA:
  - Form contiene: Tipo (select di tipi attivi custom + standard), Oggetto, Descrizione, Data/Ora, Status (Completata/Pianificata)
  - Selezionando un tipo, il form mostra categoria del tipo per context
  - Al submit, attività è creata in `crm_activities` con il tipo selezionato e status default

**AC-137.2 (Type-driven behavior)**: DATO che creo un'attività con tipo "Inmail LinkedIn" (ha flag "Conta ultimo contatto"=true), QUANDO salvo, ALLORA:
  - L'attività è creata
  - Il `contact.last_contact_at` è aggiornato al timestamp dell'attività
  - Nel contact detail, la timeline mostra l'attività con label "Ultimo contatto"

**AC-137.3 (Error - Required fields)**: DATO che cerco di salvare un'attività senza Tipo o Oggetto, ALLORA:
  - Il sistema mostra errore "Tipo e Oggetto sono obbligatori"
  - Form non invia submit

**AC-137.4 (Boundary - Bulk log activity)**: DATO che seleziono 5 contatti, QUANDO eseguo "Log attività in bulk", ALLORA:
  - Si apre form con Tipo, Oggetto, Descrizione, Data (singola per tutti)
  - Al submit, per ogni contatto viene creata un'attività separata con stessa data
  - Nessun errore di duplicazione

**SP**: 5 | **Priorità**: Must Have | **Epic**: Attività Custom e Pre-funnel | **Dipendenze**: US-134

---

## EPIC 3: Ruoli e Collaboratori Esterni

### US-138: Admin definisce ruolo custom con matrice permessi RBAC

**Come** admin di un tenant
**Voglio** creare un ruolo custom (es. "Sales Manager", "Account Executive") con granular permessi su entità (Create/Read/Update/Delete, Export, View All)
**Per** gestire accesso e azioni degli utenti secondo la struttura organizzativa

**AC-138.1 (Happy Path)**: DATO che sono in Impostazioni > Ruoli, QUANDO clicco "Nuovo ruolo", ALLORA:
  - Form contiene: Nome ruolo, Descrizione, Matrice permessi per entità (crm_contacts, crm_deals, crm_activities, crm_pipelines, email_sequences, reports)
  - Per ogni entità: checkbox Create, Read, Update, Delete, Export, View All (row-level data visibility)
  - Al submit, ruolo è salvato in `crm_roles` con tenant_id

**AC-138.2 (Preset roles)**: DATO che creo un nuovo tenant, ALLORA:
  - I ruoli preset sono creati automaticamente: Admin (tutti i permessi), Sales Rep (limited CRUD), Manager (CRUD + View All), Guest (Read only)
  - Admin può basarsi su preset o crearne uno da zero

**AC-138.3 (Permission evaluation)**: DATO che un utente con ruolo "Sales Rep" che ha Update=false su crm_deals, QUANDO tenta di modificare un deal, ALLORA:
  - Il form è in read-only
  - Toast mostra "Non hai permesso di modificare deal"
  - Se invio su API, ritorna 403 Forbidden con messaggio

**AC-138.4 (Boundary - Export permesso)**: DATO che creo ruolo "Account Executive" con Export=false su crm_contacts, QUANDO l'utente tenta di esportare la lista contatti in CSV, ALLORA:
  - Il bottone "Esporta" è disabilitato (greyed out)
  - Se inviato diretto su API /export, ritorna 403 Forbidden

**SP**: 8 | **Priorità**: Must Have | **Epic**: Ruoli e Collaboratori Esterni | **Dipendenze**: Nessuna

---

### US-139: Admin crea utente esterno con scadenza accesso

**Come** admin
**Voglio** aggiungere un utente di tipo "Esterno" (freelancer, contractor, partner) con data scadenza accesso e permessi limitati
**Per** concedere accesso temporaneo a risorse esterne senza grant permanente

**AC-139.1 (Happy Path)**: DADO che sono in Utenti > Nuovo utente, QUANDO inserisco: Email, Nome, Tipo=Esterno, Data scadenza accesso, Ruolo (select custom roles), Canale/Prodotto default, ALLORA:
  - Utente è creato in `crm_users` con tipo "external", access_expiry_date settato
  - Viene inviata email di invito con link temporaneo
  - Nel user detail, è visibile badge "Accesso scade il [data]"

**AC-139.2 (Access expiry logic)**: DADO che l'utente esterno ha access_expiry_date = 2026-04-15, QUANDO accede il 2026-04-16, ALLORA:
  - Il login fallisce con messaggio "Accesso scaduto. Contatta l'administrator."
  - Nel DB, il campo `is_active` è automaticamente settato a false dalla job notturna
  - L'admin vede utente "Disattivato (accesso scaduto)" nella lista

**AC-139.3 (Error - Invalid expiry date)**: DADO che cerco di creare utente esterno con access_expiry_date nel passato, ALLORA:
  - Il sistema valida e mostra errore "Data scadenza deve essere nel futuro"
  - Form non invia

**AC-139.4 (Boundary - Extend access)**: DADO che un utente esterno ha accesso scaduto, QUANDO l'admin lo seleziona e clicca "Estendi accesso", ALLORA:
  - Si apre dialog con nuovo campo access_expiry_date
  - Al submit, la data è aggiornata e utente torna attivo
  - Nessuna email di notifica inviata

**SP**: 8 | **Priorità**: Must Have | **Epic**: Ruoli e Collaboratori Esterni | **Dipendenze**: US-138

---

### US-140: Assegnare canale/prodotto default a utente esterno

**Come** admin
**Voglio** configurare che un utente esterno abbia un canale (es. "LinkedIn Sales") e un prodotto (es. "Sviluppo Custom") di default
**Per** limitare la visibilità dei dati e forzare tracciamento corretto senza che l'utente selezioni

**AC-140.1 (Happy Path)**: DATO che creo/modifico un utente esterno, QUANDO assegno Canale default = "LinkedIn Sales" e Prodotto default = "Sviluppo", ALLORA:
  - I campi sono salvati in `crm_users.default_channel` e `default_product_id`
  - Quando l'utente crea un contact, il campo Origine è pre-compilato con il canale default
  - Quando crea un deal, il prodotto default è pre-selezionato

**AC-140.2 (Data segregation)**: DATO che utente esterno ha canale default="LinkedIn", QUANDO filtra la lista contatti, ALLORA:
  - La lista mostra SOLO contatti con origine="LinkedIn" (non è bypassabile da UI)
  - Se naviga a contatto di altra origine tramite link diretto, ritorna 403 Forbidden (row-level security)

**AC-140.3 (Error - Cannot change own defaults)**: DATO che un utente esterno tenta di modificare le sue impostazioni di canale/prodotto default, ALLORA:
  - I campi canale/prodotto default sono read-only nel profilo utente
  - Solo admin può cambiarli da Impostazioni > Utenti

**AC-140.4 (Boundary - No default product)**: DATO che creo un utente esterno SENZA assegnare un prodotto default, QUANDO crea un deal, ALLORA:
  - Il campo Prodotto rimane facoltativo (nessuna pre-selezione)
  - Se assegno il prodotto default dopo la creazione, NON si ripercuote su deal già creati

**AC-140.5 (Default product pre-selection)**: DATO che un utente esterno ha `default_product_id` = "Sviluppo Custom", QUANDO crea un nuovo deal, ALLORA:
  - Il dropdown Prodotto è pre-selezionato su "Sviluppo Custom"
  - L'utente PUÒ cambiare il prodotto selezionato (non è forzato, solo pre-compilato)
  - Il campo `default_product_id` è salvato in `users.default_product_id` (FK)

**SP**: 5 | **Priorità**: Should Have | **Epic**: Ruoli e Collaboratori Esterni | **Dipendenze**: US-139

---

### US-141: Audit trail immutabile per azioni utenti

**Come** admin o auditor
**Voglio** visualizzare un log immutabile di tutte le azioni (CRUD, login, export, permission denied) di ogni utente
**Per** garantire compliance e tracciabilità degli accessi ai dati

**AC-141.1 (Happy Path)**: DATO che sono in Impostazioni > Audit Log, QUANDO filtro per utente="Marco Rossi" e data range="Ultimi 7 giorni", ALLORA:
  - La tabella mostra: Timestamp, User, Action (create_contact / update_deal / view_report / export_csv / login / permission_denied), Entità, Dettagli, IP/User-Agent
  - Per ogni riga è visualizzato: "Marco Rossi ha creato contact #123 'ACME Corp' il 2026-04-02 alle 14:30 da IP 192.168.1.1"
  - Nessun record è modificabile (read-only visivo)

**AC-141.2 (Data immutability)**: DATO che eseguo azioni di CRUD su DB direttamente (nessuno dovrebbe farlo), QUANDO cerco di UPDATE una riga in `crm_audit_log`, ALLORA:
  - Il DB ha trigger che nega l'UPDATE (immutable)
  - Se cerco di fare DELETE, il DB nega con errore "Audit log cannot be deleted"

**AC-141.3 (Error - Permission denied event)**: DATO che un utente esterno tenta di visualizzare un contatto di canale diverso, QUANDO fa la richiesta, ALLORA:
  - La richiesta è bloccata (403)
  - Un evento "permission_denied" è registrato in audit_log con dettagli (utente, entità, motivo)

**AC-141.4 (Boundary - Export audit log)**: DATO che l'admin ha ruolo con Export=true, QUANDO esegue "Esporta audit log" con filter, ALLORA:
  - Si scarica CSV con i record filtrati
  - Il file CSV è firmato digitalmente (hash SHA256) per attestare integrità
  - Se l'admin tenta l'export senza permesso, ritorna 403

**SP**: 8 | **Priorità**: Must Have | **Epic**: Ruoli e Collaboratori Esterni | **Dipendenze**: US-138, US-139

---

## EPIC 4: Catalogo Prodotti

### US-142: Admin definisce prodotto/servizio nel catalogo

**Come** admin di un tenant
**Voglio** creare un nuovo Prodotto/Servizio (es. "Sviluppo Custom", "Supporto SLA") con dettagli pricing e categoria
**Per** tracciare quali prodotti sono venduti e calcolare metriche di performance per prodotto

**AC-142.1 (Happy Path)**: DATO che sono in Impostazioni > Catalogo prodotti, QUANDO clicco "Nuovo prodotto", ALLORA:
  - Form contiene: Nome (required), Codice (unique per tenant), Categoria (select custom category o create new), Modello pricing (Fixed / Hourly / Custom), Prezzo base (numero), Margine target (%), Descrizione, Attivo
  - Al submit, prodotto è salvato in `crm_products` con tenant_id
  - Nel catalogo, prodotto appare con icona/badge per tipo pricing

**AC-142.2 (Pricing models)**: DATO che creo prodotto con modello "Hourly", QUANDO salvo, ALLORA:
  - Il form mostra campi aggiuntivi: Prezzo orario, Stima giorni standard (default), Tipo tecnologia (es. "Frontend", "Backend", "Mobile")
  - Al creare un deal con questo prodotto, la revenue è calcolata come prezzo_orario * giorni_stima

**AC-142.3 (Error - Duplicate code)**: DATO che codice "custom_dev" esiste già, QUANDO creo nuovo prodotto con lo stesso codice, ALLORA:
  - Errore "Codice prodotto già esistente nel tenant"
  - Form rimane in edit

**AC-142.4 (Boundary - Category)**: DATO che creo un prodotto e la categoria non esiste, QUANDO inserisco una nuova categoria (inline picker), ALLORA:
  - La categoria è creata on-the-fly per il tenant
  - Il prodotto viene salvato con la nuova categoria

**SP**: 5 | **Priorità**: Must Have | **Epic**: Catalogo Prodotti | **Dipendenze**: Nessuna

---

### US-143: Admin modifica/disattiva prodotto

**Come** admin
**Voglio** modificare un prodotto (nome, pricing, margine target) o disattivarlo
**Per** mantenere il catalogo allineato con l'offerta aziendale

**AC-143.1 (Happy Path)**: DATO che seleziono un prodotto, QUANDO clicco "Modifica", ALLORA:
  - Il codice è read-only
  - Campi Nome, Categoria, Prezzo base, Margine, Descrizione sono editable
  - Al submit, le modifiche sono salvate e aggiornate nel DB

**AC-143.2 (Soft delete)**: DATO che un prodotto ha 30 deal già associati, QUANDO lo disattivo, ALLORA:
  - Il prodotto disattivato rimane associato ai deal esistenti (storico immutabile)
  - Il prodotto NON appare nel dropdown per nuovi deal
  - Admin vede badge "Disattivato" nella lista

**AC-143.3 (Error - Cannot hard delete)**: DATO che cerco di cancellare un prodotto, ALLORA:
  - Il sistema offre solo opzione "Disattiva" (no delete button)
  - Se inviato su API DELETE, ritorna 409 Conflict

**AC-143.4 (Boundary - Pricing change impact)**: DATO che cambio Prezzo base di un prodotto, QUANDO salvo, ALLORA:
  - I deal già creati con questo prodotto mantengono il prezzo originale (snapshot al momento della creazione)
  - Solo i NUOVI deal usano il nuovo prezzo

**SP**: 3 | **Priorità**: Should Have | **Epic**: Catalogo Prodotti | **Dipendenze**: US-142

---

### US-144: Associare 1+ prodotti a un deal

**Come** sales user
**Voglio** aggiungere uno o più prodotti a un deal e specificare quantità/dettagli pricing
**Per** tracciare esattamente quale/i prodotto/i è/sono in negoziazione

**AC-144.1 (Happy Path)**: DATO che apro un deal detail, QUANDO clicco "Aggiungi prodotto", ALLORA:
  - Si apre dialog con: Prodotto (select di catalogo attivi), Quantità, Prezzo override (opzionale), Note
  - Al submit, il prodotto è aggiunto in `crm_deal_products` (tabella pivot)
  - Nel deal detail, la sezione Prodotti mostra lista con riga per ogni prodotto

**AC-144.2 (Revenue calculation)**: DATO che aggiungo 2 prodotti: Sviluppo (prezzo 50k, qty=1) e Supporto SLA (prezzo 5k, qty=12 mesi), QUANDO salvo, ALLORA:
  - Revenue totale del deal è aggiornato: 50k + (5k * 12) = 110k
  - Se prezzo è overridato, usa il prezzo override nel calcolo
  - La sezione Prodotti mostra subtotale per prodotto e totale deal

**AC-144.3 (Error - Remove product)**: DATO che cerco di rimuovere l'unico prodotto di un deal, ALLORA:
  - Il sistema valida: almeno 1 prodotto deve rimanere
  - Se è l'ultimo, mostra errore "Un deal deve avere almeno 1 prodotto"
  - Button Remove è disabilitato

**AC-144.4 (Boundary - Duplicate product)**: DATO che un deal ha già prodotto "Sviluppo" aggiunto, QUANDO cerco di aggiungere lo stesso prodotto, ALLORA:
  - Il sistema consente di aggiungere la stessa linea di prodotto (potrebbe essere multiple phase)
  - Nella lista dei prodotti, appaiono come righe separate con quantità diversa

**SP**: 5 | **Priorità**: Must Have | **Epic**: Catalogo Prodotti | **Dipendenze**: US-142

---

### US-145: Filtrare pipeline e deal per prodotto

**Come** sales manager
**Voglio** filtrare la pipeline Kanban e la lista deal per prodotto (es. "Mostra solo deal con Sviluppo Custom")
**Per** focalizzarmi sui deal di una specifica linea di business

**AC-145.1 (Happy Path)**: DATO che sono nella view Pipeline, QUANDO clicco "Filtri" e seleziono Prodotto="Sviluppo Custom", ALLORA:
  - La pipeline Kanban mostra SOLO deal che hanno "Sviluppo Custom" associato
  - Il filtro è salvato in URL (#pipeline?product=sviluppo_custom)
  - Al refresh della pagina, il filtro persiste

**AC-145.2 (Multi-product filter)**: DATO che seleziono Prodotti="Sviluppo" e "Supporto SLA", ALLORA:
  - Viene applicato filtro OR: deal che hanno Sviluppo O Supporto SLA
  - La lista mostra tutti i deal matching uno dei due prodotti

**AC-145.3 (Analytics impact)**: DATO che il dashboard ha widget "Revenue by Product", QUANDO applico filtro prodotto nel dashboard, ALLORA:
  - Il widget mostra revenue SOLO per il prodotto filtrato
  - Gli altri widget (KPI, Scorecard) sono aggiornati con scope filtrato

**AC-145.4 (Boundary - No product filter)**: DATO che il filtro Prodotto è non applicato, ALLORA:
  - La pipeline mostra TUTTI i deal (default behavior, senza filtro)
  - Nel filtro UI, il select Prodotto mostra "- Tutti i prodotti -"

**SP**: 5 | **Priorità**: Should Have | **Epic**: Catalogo Prodotti | **Dipendenze**: US-144

---

## EPIC 5: Analytics e Compensi

### US-146: Admin crea dashboard KPI componibile e filtrabile

**Come** sales manager o admin
**Voglio** creare una dashboard personalizzata con widget KPI configurabili (Revenue MoM, Deal Count, Win Rate, etc.)
**Per** avere visibilità in tempo reale sullo stato della pipeline

**AC-146.1 (Happy Path)**: DATO che sono in Analitycs > Nuova Dashboard, QUANDO clicco "Aggiungi widget", ALLORA:
  - Si apre catalog con widget preset: Revenue, Deal Count, Win Rate, Average Deal Size, Pipeline by Stage, Forecast
  - Selezionando un widget, appare nella dashboard in layout grid
  - Per ogni widget, posso configurare: Periodo (Last 30 days / Last quarter / YTD / Custom), Canale (filter), Prodotto (filter), Utente (filter)
  - Al submit, dashboard è salvata in `crm_dashboards` con configurazione JSON

**AC-146.2 (Widget calculation)**: DATO che aggiungo widget "Revenue MoM", QUANDO configuroo Periodo=Last 3 months e Prodotto=Sviluppo, ALLORA:
  - Il widget calcola: Revenue per mese negli ultimi 3 mesi SOLO per deal con prodotto Sviluppo
  - Mostra in formato line chart con valori assoluti e trend % MoM
  - Legenda mostra source dei dati (deal_value da crm_deals.revenue)

**AC-146.3 (Error - Invalid config)**: DATO che creo widget senza selezionare Periodo, QUANDO cerco di salvare la dashboard, ALLORA:
  - Il sistema valida e mostra errore "Tutti i widget devono avere Periodo configurato"
  - Dashboard non è salvata

**AC-146.4 (Boundary - Widget export)**: DATO che visualizzo una dashboard con 4 widget, QUANDO clicco "Esporta dashboard", ALLORA:
  - Si scarica PDF con screenshot di tutti i widget
  - Oppure, clicco "Esporta dati" e scarico CSV con i dati sottostanti di ogni widget

**SP**: 8 | **Priorità**: Should Have | **Epic**: Analytics e Compensi | **Dipendenze**: US-142, US-144

---

### US-147: Scorecard collaboratore con metriche custom

**Come** sales manager
**Voglio** visualizzare per ogni collaboratore una scorecard con metriche: Deal count, Revenue, Win rate, Tempo medio chiusura, Last contact date
**Per** valutare performance e identificare chi ha bisogno di supporto

**AC-147.1 (Happy Path)**: DATO che sono in Analytics > Scorecard collaboratori, QUANDO seleziono un utente e periodo, ALLORA:
  - Appare scorecard con KPI: Deal created, Revenue closed, Win rate (%), Avg days to close, Last contact
  - Per ogni KPI è mostrato: valore attuale, trend vs periodo precedente (up/down %), target se configurato
  - I dati sono aggregati dai deal assegnati all'utente

**AC-147.2 (Metric aggregation)**: DATO che Marco ha 3 deal chiusi (10k, 15k, 5k) in Q1, QUANDO visualizzo la scorecard, ALLORA:
  - Deal created = 5 (deal assegnati, chiusi o no)
  - Revenue closed = 30k (somma degli win)
  - Win rate = 60% (3 chiusi su 5 totali)
  - Tutti i valori sono calcolati lato server da query su crm_deals

**AC-147.3 (Error - User has no data)**: DATO che seleziono un utente che non ha deal assegnati, QUANDO visualizzo la scorecard, ALLORA:
  - La scorecard mostra "Nessun dato disponibile per questo periodo"
  - I KPI rimangono vuoti (no errore)

**AC-147.4 (Boundary - Filter by product)**: DATO che applico filtro Prodotto="Sviluppo" alla scorecard, ALLORA:
  - Tutti i KPI sono ricalcolati per deal che contengono solo quel prodotto
  - Se l'utente non ha deal con quel prodotto, scorecard rimane vuota

**SP**: 5 | **Priorità**: Should Have | **Epic**: Analytics e Compensi | **Dipendenze**: US-144

---

### US-148: Admin configura modello compensi con regole

**Come** admin
**Voglio** definire un modello di compensi con regole trigger/base calcolo/condizioni (es. "5% su revenue chiusa + bonus se >30k")
**Per** automatizzare il calcolo delle provvigioni e incentivare performance

**AC-148.1 (Happy Path)**: DATO che sono in Impostazioni > Modello Compensi, QUANDO clicco "Nuova regola", ALLORA:
  - Form contiene: Nome regola, Trigger (Deal Won / Revenue Threshold / Quarterly), Base calcolo (% su Revenue / Fixed amount / Tiered), Condizioni (es. prodotto=Sviluppo, canale=LinkedIn)
  - Al submit, regola è salvata in `crm_compensation_rules` con tenant_id e configurazione JSON
  - La regola appare nella lista e può essere attivata/disattivata

**AC-148.2 (Tiered compensation)**: DATO che configuro regola: "5% su revenue 0-50k, 7% su 50-100k, 10% su >100k", QUANDO calcolo compensi per Marco con revenue 70k, ALLORA:
  - Compenso = (50k * 5%) + (20k * 7%) = 2.5k + 1.4k = 3.9k
  - Il sistema applica il tier matching correttamente

**AC-148.3 (Error - Circular logic)**: DATO che creo regola con condizione "IF Product=A THEN payout=X, ELSE payout=X*2", QUANDO salvo, ALLORA:
  - Il sistema valida la logica
  - Se rileva cicli (regola A rimanda a regola B che rimanda ad A), mostra errore "Logica circolare rilevata"

**AC-148.4 (Boundary - Multiple rules)**: DATO che ho 3 regole attive (Base 5%, Bonus prodotto Sviluppo +2%, Penalty No Activity -1%), QUANDO calcolo compensi, ALLORA:
  - Il sistema aggrega tutte le regole in ordine di priorità
  - Compenso finale = base + bonus - penalty
  - In UI, il dettaglio della scorecard mostra breakdown di ogni regola applicata

**SP**: 8 | **Priorità**: Could Have | **Epic**: Analytics e Compensi | **Dipendenze**: US-147

---

### US-149: Calcolo e visualizzazione compensi mensili

**Come** admin o collaboratore
**Voglio** visualizzare il compenso mensile calcolato in base alle regole configurate
**Per** verificare correttezza del calcolo e pianificare pagamenti

**AC-149.1 (Happy Path)**: DATO che sono in Analytics > Compensi Mensili, QUANDO seleziono mese e filtro per utente, ALLORA:
  - La tabella mostra per ogni collaboratore: Nome, Deal count, Revenue chiusa, Regole applicate, Compenso lordo, Status pagamento (Bozza / Confermato / Pagato)
  - Clicco su un utente e si apre dettaglio: breakdown riga per riga di quale deal ha contribuito a quale parte della provvigione

**AC-149.2 (Calculation trigger)**: DATO che il mese di marzo è terminato e è il 1 aprile, QUANDO cron job esegue nightly job "Calculate monthly compensation", ALLORA:
  - Per ogni tenant, per ogni utente attivo, il compenso di marzo è calcolato
  - Viene creato record in `crm_compensation_monthly` con user_id, month, amount_gross, rules_applied (JSON), status=Draft
  - Admin riceve notifica "Compensi marzo calcolati, attendono conferma"

**AC-149.3 (Error - Conflicting rules)**: DATO che ho regole che entrano in conflitto (es. regola A dice 5%, regola B dice 3%), QUANDO il calcolo esegue, ALLORA:
  - Il sistema non sa quale regola applicare
  - La riga di compenso è creata con status "Error - conflicting rules"
  - Admin riceve notifica e deve risolvere manualmente

**AC-149.4 (Boundary - Retroactive calculation)**: DATO che aggiungo una nuova regola di compensi, QUANDO applico la regola al mese precedente, ALLORA:
  - Posso selezionare "Recalculate previous months"
  - Il sistema ricalcola con le nuove regole e crea nuovi record (mantiene storico dei vecchi)
  - Admin deve confermare manualmente prima di sovrascrivere

**SP**: 8 | **Priorità**: Should Have | **Epic**: Analytics e Compensi | **Dipendenze**: US-148

---

### US-150: Export e management ciclo pagamento compensi

**Como** admin o finance team
**Voglio** esportare il report compensi mensile (Excel/PDF) e tracciare il ciclo pagamento (Confermato > In pagamento > Pagato)
**Per** gestire il flusso amministrativo di pagamento delle provvigioni

**AC-150.1 (Happy Path)**: DATO che sono in Analytics > Compensi Mensili con mese="Marzo 2026" e tutti i compensi in status "Bozza", QUANDO clicco "Conferma compensi", ALLORA:
  - Un dialog chiede "Confermi il calcolo per aprile 2026? Non sarà possibile modificare."
  - Al submit, tutti i record cambiano status a "Confermato"
  - Admin riceve email con report PDF allegato

**AC-150.2 (Export)**: DATO che i compensi sono "Confermati", QUANDO clicco "Esporta Excel", ALLORA:
  - Si scarica file con colonne: Cognome, Nome, Revenue, Regole applicate (string), Compenso lordo, Ritenute (calcolate da tax rules), Netto, Metodo pagamento (IBAN/Bollettino)
  - Il file è firmato (firma digitale dell'admin che l'ha esportato)

**AC-150.3 (Payment tracking)**: DATO che clicco "Segna come pagato" per un compenso "Confermato", ALLORA:
  - Status cambia a "Pagato"
  - Viene registrato timestamp e user_id di chi ha confermato
  - Nessun utente esterno può vedere report completo (solo la propria riga)

**AC-150.4 (Boundary - Bulk action)**: DATO che seleziono 5 compensi con status "Confermato", QUANDO clicco "Segna come pagato in bulk", ALLORA:
  - Tutti e 5 cambiano a status "Pagato" con singolo timestamp
  - Un record di audit log unico registra l'azione bulk

**SP**: 5 | **Priorità**: Should Have | **Epic**: Analytics e Compensi | **Dipendenze**: US-149

---

## Riepilogo Stories per Epic

| Epic | Stories | Total SP | Priorità |
|------|---------|----------|----------|
| **Epic 1: Origini Configurabili** | US-130, US-131, US-132, US-133 | 21 | Must Have |
| **Epic 2: Attività Custom e Pre-funnel** | US-134, US-135, US-136, US-137 | 18 | Must Have / Should Have |
| **Epic 3: Ruoli e Collaboratori Esterni** | US-138, US-139, US-140, US-141 | 29 | Must Have |
| **Epic 4: Catalogo Prodotti** | US-142, US-143, US-144, US-145 | 18 | Must Have / Should Have |
| **Epic 5: Analytics e Compensi** | US-146, US-147, US-148, US-149, US-150 | 34 | Should Have / Could Have |

**Total: 21 User Stories, 120 Story Points**

---

## Note di Implementazione

1. **Migrazioni DB**: Story US-132 è prerequisito per tutte le altre. Va completata in Pivot 8 Sprint 1.

2. **RBAC Engine**: La matrice permessi (US-138) deve essere implementata come middleware in FastAPI che intercetta le route `/crm/...` e valida contro i permessi dell'utente logato.

3. **Row-level security**: Le stories di Epic 3 (Ruoli/Collaboratori) richiedono filtri WHERE automatici basati su tenant_id + canale_default + permessi. Non è triviale.

4. **Audit immutabilità**: La tabella `crm_audit_log` deve avere trigger PostgreSQL ON UPDATE per prevenire modifiche (trigger RAISE EXCEPTION).

5. **Calcolo compensi**: Story US-149 richiede engine di valutazione di regole. Consiglio di usare libreria come Drools o custom Python DSL.

6. **Dashboard**: Story US-146 è complessa se si vuol fare bene. Considera di usare libreria charting (Recharts React side, o aggregazioni pre-calcolate in Redis).

---

## Dipendenze Critiche

```
US-130 → US-131, US-132, US-133
US-132 → (prerequisito per tutti Epic 1)
US-138 → US-139, US-140, US-141
US-142 → US-143, US-144, US-145
US-148 → US-149, US-150
```

---

**File generato il 2026-04-04**
**Pivot 8: Social Selling Configurabile**
**AgentFlow PMI — CRM B2B per PMI italiane**
