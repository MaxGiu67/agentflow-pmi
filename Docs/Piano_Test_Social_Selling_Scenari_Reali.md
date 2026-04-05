# Piano di Test — Social Selling: Scenari Commerciali Reali

**Obiettivo:** Simulare il lavoro quotidiano di un commerciale e di un venditore LinkedIn per validare che AgentFlow copra situazioni reali, non solo casi tecnici.

**Perche questo piano:** I test unitari verificano che il codice funzioni. Questo piano verifica che il **business** funzioni — che un commerciale possa lavorare senza blocchi, che i dati fluiscano correttamente, e che il manager abbia visibilita reale sulla pipeline.

---

## Personaggi

| Persona | Nome | Ruolo | Come lavora |
|---------|------|-------|-------------|
| **Admin** | Laura Bianchi | Owner/Admin | Configura il sistema, assegna ruoli, monitora KPI |
| **Commerciale Senior** | Marco Rossi | Sales Rep (interno) | Telefonate, visite clienti, fiere, email commerciali |
| **LinkedIn Seller** | Sara Conti | Sales Rep (esterno) | Prospecting LinkedIn, InMail, contenuti, social selling |
| **Sales Manager** | Paolo Verdi | Manager | Supervisiona pipeline, approva compensi, report |

---

## FASE 1: Setup Iniziale (Laura — Admin)

### Scenario 1.1: Laura prepara il sistema per il team

**Contesto reale:** Laura ha appena acquistato AgentFlow per Nexa Data. Ha 2 commerciali (Marco interno, Sara freelancer LinkedIn) e un manager. Deve configurare tutto prima che inizino a lavorare.

**Azioni:**

1. **Crea le origini contatto**
   - `POST /social/origins` — Crea: "Fiera", "Passaparola", "Sito Web", "LinkedIn Organic", "LinkedIn InMail", "Cold Call"
   - **Intenzione reale:** Laura sa che ogni cliente arriva da un canale diverso. Vuole capire quale canale porta piu revenue per decidere dove investire budget marketing.
   - **Verifica:** Le 6 origini + le 6 di default = 12 origini visibili

2. **Crea i tipi di attivita personalizzati**
   - `POST /social/activity-types` — Crea: "Visita Cliente", "Demo Online", "Invio Preventivo", "Follow-up Telefonico", "LinkedIn InMail", "Commento LinkedIn"
   - **Intenzione reale:** Marco fa visite fisiche, Sara fa InMail. Laura vuole tracciare TUTTO per capire quante attivita servono per chiudere un deal.
   - **Verifica:** 8 default + 6 custom = 14 tipi attivita

3. **Crea il catalogo prodotti**
   - `POST /social/products` con:
     - "Sviluppo Custom" (code: `custom_dev`, fixed, 50.000 EUR, margine 40%)
     - "Supporto SLA" (code: `sla_support`, fixed, 5.000 EUR/anno)
     - "Consulenza AI" (code: `ai_consult`, hourly, 150 EUR/h, stima 20gg)
     - "Formazione" (code: `training`, fixed, 3.000 EUR)
   - **Intenzione reale:** Marco vende sviluppo + SLA, Sara vende consulenza AI + formazione. Laura vuole report per prodotto.
   - **Verifica:** 4 prodotti attivi nel catalogo

4. **Crea i ruoli RBAC**
   - `POST /social/roles` — "Commerciale Esterno" con:
     - contacts: create, read, update (NO delete, NO view_all)
     - deals: create, read, update (NO export)
     - activities: create, read
   - **Intenzione reale:** Sara e freelancer, deve vedere SOLO i suoi contatti LinkedIn, non quelli di Marco. Laura non vuole che esporti la lista clienti.
   - **Verifica:** Ruolo creato con permessi granulari

5. **Configura Sara come utente esterno**
   - Sara ha: `user_type=external`, `access_expires_at=2026-09-30`, `default_origin_id="LinkedIn InMail"`, `default_product_id="Consulenza AI"`, `crm_role_id="Commerciale Esterno"`
   - **Intenzione reale:** Sara lavora solo fino a settembre. Quando crea un contatto, l'origine e gia "LinkedIn". Quando crea un deal, il prodotto e gia "Consulenza AI". Meno errori, meno training.
   - **Verifica:** Sara non vede contatti di Marco (row-level). Il form ha campi pre-compilati.

6. **Aggiunge stadi pre-funnel alla pipeline**
   - `POST /social/pipeline/stages`:
     - "Prospect" (sequence=1, stage_type=pre_funnel, probability=5%)
     - "Contatto Qualificato" (sequence=2, stage_type=pre_funnel, probability=15%)
   - **Intenzione reale:** Marco e Sara lavorano persone che non sono ancora "lead". Un like su LinkedIn non e un lead. Servono stadi prima del funnel classico per tracciare il nurturing.
   - **Verifica:** Pipeline mostra: Prospect > Contatto Qualificato > Nuovo Lead > Qualificato > Proposta > Ordine > Confermato

---

## FASE 2: Marco — Il Commerciale Tradizionale

### Scenario 2.1: Marco incontra un potenziale cliente a una fiera

**Contesto reale:** Marco e alla fiera "SMAU Milano". Incontra il CEO di "TechnoSteel SRL" che si lamenta del gestionale. Scambia il biglietto da visita.

**Azioni (giorno 1 — alla fiera):**

1. **Crea il contatto da mobile (PWA)**
   - `POST /crm/contacts` con: name="TechnoSteel SRL", email="info@technosteel.it", phone="+39 02 1234567", type="azienda", piva="12345678901", sector="Manifatturiero"
   - **Poi assegna origine:** `POST /social/contacts/{id}/origin?origin_id={fiera_id}`
   - **Intenzione reale:** Marco non vuole perdere il contatto. Lo inserisce subito dal telefono tra un caffe e l'altro. L'origine "Fiera" gli servira per dire a Laura "la fiera ha portato X contatti".
   - **Verifica:** Contatto creato con origine "Fiera"

2. **Logga l'attivita "Incontro Fiera"**
   - `POST /crm/activities` con: contact_id, type="meeting", activity_type_id={visita_cliente}, subject="Incontro SMAU — interesse per gestionale", status="completed"
   - **Intenzione reale:** Marco vuole ricordarsi cosa si sono detti. E il manager vuole vedere quante attivita fa Marco alla fiera.
   - **Verifica:** Attivita creata, `last_contact_at` aggiornato sul contatto

3. **Crea il deal nello stadio "Prospect"**
   - `POST /crm/deals` con: contact_id, name="TechnoSteel - Gestionale Custom", stage_id={prospect}, deal_type="fixed"
   - **Intenzione reale:** Non e ancora un lead vero — non sa nemmeno il budget. Ma vuole tracciarlo nella pipeline per non dimenticarselo.
   - **Verifica:** Deal in stadio "Prospect" (pre-funnel), probability 5%

### Scenario 2.2: Marco qualifica il prospect (settimana successiva)

**Contesto reale:** Marco chiama TechnoSteel. Scopre che hanno budget 80k, vogliono partire entro 3 mesi, il decisore e il CFO. E un lead qualificato.

**Azioni:**

4. **Logga la chiamata**
   - `POST /crm/activities` con: type="call", activity_type_id={follow_up_telefonico}, subject="Chiamata qualifica — budget 80k, decisore CFO", status="completed"
   - **Intenzione reale:** Marco annota i dettagli BANT (Budget, Authority, Need, Timeline). Servira quando prepara il preventivo.

5. **Muove il deal a "Contatto Qualificato" poi "Nuovo Lead"**
   - `PATCH /crm/deals/{id}` con stage_id cambiato prima a "Contatto Qualificato" poi a "Nuovo Lead"
   - **Intenzione reale:** Il deal entra nella pipeline "vera". Da qui il manager lo vede nei report.
   - **Verifica:** Deal ora in "Nuovo Lead", probability aggiornata a 20%

6. **Aggiunge prodotti al deal**
   - `POST /social/deals/{id}/products` — "Sviluppo Custom" qty=1 price_override=null (usa 50k base)
   - `POST /social/deals/{id}/products` — "Supporto SLA" qty=12 (12 mesi) price_override=null (5k)
   - `POST /social/deals/{id}/products` — "Formazione" qty=2 price_override=null (3k * 2)
   - **Intenzione reale:** Marco compone l'offerta: sviluppo + un anno di supporto + 2 sessioni formazione = 50k + 60k + 6k = 116k. Il deal.expected_revenue si aggiorna automaticamente.
   - **Verifica:** Revenue deal = 116.000 EUR, 3 linee prodotto visibili

### Scenario 2.3: Marco manda il preventivo e negozia

**Azioni:**

7. **Invia email con preventivo** (da deal detail)
   - Usa il sistema email: template "Preventivo", variabili {{nome}}="TechnoSteel", {{deal_value}}="116.000"
   - **Intenzione reale:** Marco vuole che l'email sia tracciata — se il cliente la apre, lo sa subito e puo richiamare.
   - **Verifica:** EmailSend creata con brevo_message_id, status "sent"

8. **Il cliente risponde: "Il budget e 80k, non 116k"**
   - Marco modifica il deal: rimuove una formazione, abbassa il prezzo SLA
   - `DELETE /social/deals/{id}/products/{formazione_2_id}` — rimuove una formazione
   - `PATCH /social/products/{sla}` — NO, il prezzo base non cambia per tutti! Marco usa `price_override` sulla linea deal.
   - **Intenzione reale:** Il cliente ha negoziato. Marco non puo cambiare il listino (vale per tutti). Cambia solo il prezzo su questo specifico deal.
   - **Verifica:** Revenue ricalcolata, prezzo listino SLA invariato per altri deal

9. **Muove a "Proposta Inviata"**
   - `PATCH /crm/deals/{id}` — stage_id = Proposta Inviata, probability = 60%
   - **Logga attivita:** "Invio Preventivo" con note "Preventivo rivisto a 80k dopo negoziazione"

### Scenario 2.4: Marco chiude il deal

**Azioni:**

10. **Il cliente accetta via email — Marco registra l'ordine**
    - `POST /crm/deals/{id}/order` con: order_type="email", order_reference="Mail CFO 15/04", order_notes="Accettazione via email dal CFO"
    - **Intenzione reale:** In Italia l'ordine puo arrivare in mille modi: PO, email, telefonata, firma su Word. Marco deve registrare COME e arrivato per compliance.
    - **Verifica:** Deal ha order_type, order_reference, order_notes

11. **Marco conferma l'ordine**
    - `POST /crm/deals/{id}/confirm-order`
    - **Verifica:** Deal probability = 100%, stage = "Confermato"

12. **Audit trail registra tutto**
    - `GET /social/audit-log?entity_type=deal&entity_id={deal_id}`
    - **Intenzione reale:** Laura puo ricostruire l'intera storia: chi ha creato il deal, chi l'ha mosso, chi ha registrato l'ordine.
    - **Verifica:** 10+ eventi nel log per questo deal

---

## FASE 3: Sara — LinkedIn Social Selling

### Scenario 3.1: Sara trova un prospect su LinkedIn

**Contesto reale:** Sara e una freelancer specializzata in vendita consulenza AI. Lavora SOLO da LinkedIn. Non fa cold call, non va alle fiere. Trova prospect commentando post e mandando InMail.

**Azioni (giorno 1):**

1. **Sara vede un post interessante del CEO di "GreenEnergy Srl"**
   - Commenta il post su LinkedIn (fuori da AgentFlow)
   - **Poi logga in AgentFlow:** Crea contatto "GreenEnergy Srl", email="ceo@greenenergy.it"
   - L'origine e gia pre-compilata: "LinkedIn InMail" (default_origin_id di Sara)
   - **Intenzione reale:** Sara traccia TUTTO. Anche un commento a un post. Perche tra 2 settimane, quando manda l'InMail, vuole sapere che il primo touchpoint era un commento.
   - **Verifica:** Contatto creato con origine "LinkedIn InMail" automatica

2. **Logga il commento come attivita**
   - `POST /crm/activities` con: activity_type_id={commento_linkedin}, subject="Commento su post AI nel manifatturiero", status="completed"
   - **Intenzione reale:** Il commento e un'attivita di nurturing. Conta come "ultimo contatto" perche il tipo ha `counts_as_last_contact=true`.
   - **Verifica:** `last_contact_at` aggiornato

3. **Crea deal in stadio "Prospect"**
   - Il prodotto e pre-compilato: "Consulenza AI"
   - `POST /social/deals/{id}/products` — Consulenza AI, hourly, stima 20gg, 150 EUR/h = 24.000 EUR stimati
   - **Intenzione reale:** Sara non sa ancora se c'e interesse. Ma lo traccia per non perderlo. Revenue stimata basata sul prodotto default.

### Scenario 3.2: Sara inizia il nurturing LinkedIn (2 settimane)

**Contesto reale:** Sara non chiama. Non manda email. Fa social selling: commenta, mette like, condivide contenuti. Dopo 2 settimane manda un InMail.

**Azioni (giorni 2-14):**

4. **Logga engagement su LinkedIn**
   - 3x `POST /crm/activities` con activity_type_id={linkedin_engagement}:
     - "Like su post GreenEnergy su sostenibilita"
     - "Commento su articolo condiviso dal CEO"
     - "Condivisione post GreenEnergy con commento personalizzato"
   - **Intenzione reale:** Sara sa che servono 5-7 touchpoint prima di un InMail. Ogni interazione scalda il prospect. Vuole dimostrare al manager che il suo lavoro non e "perdere tempo su LinkedIn" ma un processo strutturato.
   - **Verifica:** 4 attivita totali sul contatto, `last_contact_at` aggiornato ad ogni engagement

5. **Manda InMail personalizzato (giorno 14)**
   - `POST /crm/activities` con activity_type_id={linkedin_inmail}, subject="InMail: 'Ho visto il vostro progetto AI — posso aiutare?'"
   - **Poi invia email da AgentFlow** (se ha l'email): template "Primo contatto LinkedIn", variabili personalizzate
   - **Intenzione reale:** L'InMail e il momento chiave. Sara vuole tracciare il tasso di risposta per capire dopo quanti touchpoint funziona meglio.

6. **Il prospect risponde — Sara muove a "Contatto Qualificato"**
   - `PATCH /crm/deals/{id}` — stage_id = Contatto Qualificato
   - `POST /crm/activities` — "Risposta InMail positiva — interessato a demo"
   - **Intenzione reale:** Il prospect ha risposto. Non e ancora un lead (non ha chiesto un preventivo), ma e qualificato. Sara puo programmare una demo.

### Scenario 3.3: Sara fa la demo e chiude

**Azioni (settimana 3-4):**

7. **Demo online**
   - `POST /crm/activities` con activity_type_id={demo_online}, subject="Demo AI per processi produttivi — 45 min"
   - Muove deal a "Nuovo Lead" → "Qualificato"
   - **Intenzione reale:** Il deal entra nel funnel "vero" dopo la demo. Sara sa che dopo la demo il tasso di chiusura e 40%.

8. **Invio proposta**
   - Aggiunge secondo prodotto: "Formazione" qty=1 (3k)
   - Revenue = 24k + 3k = 27k
   - Muove a "Proposta Inviata"
   - **Intenzione reale:** Sara sa che aggiungere formazione aumenta la probabilita di chiusura perche il cliente si sente supportato.

9. **Chiusura via email**
   - Registra ordine: order_type="email", reference="Mail CEO 28/04"
   - Conferma ordine → probability 100%

---

## FASE 4: Paolo — Il Manager Controlla

### Scenario 4.1: Report settimanale pipeline

**Contesto reale:** E lunedi mattina. Paolo vuole sapere: quanti deal attivi? Quanto vale la pipeline? Chi sta lavorando e chi no?

**Azioni:**

1. **Dashboard KPI**
   - `POST /social/dashboards` con widget:
     - "Revenue Pipeline" (periodo: YTD)
     - "Deal per Stage" (periodo: corrente)
     - "Win Rate" (periodo: ultimo trimestre)
     - "Top Performers" (periodo: ultimo mese)
   - **Intenzione reale:** Paolo non vuole aprire Excel. Vuole una dashboard che si aggiorna da sola.
   - **Verifica:** Dashboard salvata con 4 widget, dati calcolati

2. **Scorecard di Marco**
   - `GET /social/scorecard/{marco_id}?start_date=2026-04-01&end_date=2026-04-30`
   - **Atteso:** Deal created=1, Revenue closed=80k, Win rate=100% (1/1), Activities=8+
   - **Intenzione reale:** Paolo vuole confrontare Marco con Sara. Chi porta piu revenue? Chi ha piu attivita per deal?

3. **Scorecard di Sara**
   - `GET /social/scorecard/{sara_id}?start_date=2026-04-01&end_date=2026-04-30`
   - **Atteso:** Deal created=1, Revenue closed=27k, Win rate=100% (1/1), Activities=7+
   - **Intenzione reale:** Sara ha chiuso meno revenue, ma il ciclo di vendita e piu corto e il costo di acquisizione e zero (solo tempo LinkedIn).

4. **Filtra pipeline per prodotto**
   - `GET /crm/deals?product_ids={consulenza_ai_id}`
   - **Intenzione reale:** Paolo vuole sapere quanti deal hanno "Consulenza AI" per decidere se assumere un secondo consulente.
   - **Verifica:** Solo i deal di Sara appaiono

### Scenario 4.2: Calcolo compensi mensili

**Contesto reale:** Fine mese. Laura deve calcolare quanto pagare Marco e Sara.

**Azioni:**

5. **Laura crea regole compensi**
   - Regola 1: "Base 5%" — percent_revenue, rate=5, trigger=deal_won
   - Regola 2: "Bonus LinkedIn" — fixed_amount, amount=500, condizione: origin=LinkedIn
   - Regola 3: "Tiered >50k" — tiered, tiers: [0-50k: 5%, 50k-100k: 7%, >100k: 10%]
   - **Intenzione reale:** Laura vuole incentivare il canale LinkedIn (bonus fisso) e premiare i deal grandi (tiered).

6. **Calcola compensi aprile**
   - `POST /social/compensation/calculate?month=2026-04-01`
   - **Atteso per Marco:** 80k * tiered = (50k*5%) + (30k*7%) = 2.500 + 2.100 = 4.600 EUR
   - **Atteso per Sara:** 27k * 5% = 1.350 EUR + 500 EUR (bonus LinkedIn) = 1.850 EUR
   - **Intenzione reale:** Laura vuole verificare prima di confermare. I compensi partono in stato "draft".

7. **Laura verifica e conferma**
   - `GET /social/compensation/monthly?month=2026-04-01` — vede i draft
   - `PATCH /social/compensation/monthly/{marco_entry}/confirm`
   - `PATCH /social/compensation/monthly/{sara_entry}/confirm`
   - **Intenzione reale:** Laura controlla che i numeri siano giusti prima di confermare. Una volta confermato, non si puo piu modificare.

8. **Dopo il pagamento**
   - `PATCH /social/compensation/monthly/{entry}/paid`
   - **Verifica:** Status = "paid", timestamp registrato, audit log aggiornato

### Scenario 4.3: Audit trail per compliance

9. **Laura esporta audit log del mese**
   - `GET /social/audit-log/export?start_date=2026-04-01&end_date=2026-04-30`
   - **Intenzione reale:** Il commercialista vuole sapere chi ha fatto cosa. In caso di contenzioso con Sara (freelancer), Laura ha le prove di ogni azione.
   - **Verifica:** CSV scaricato con header SHA256 per integrita

---

## FASE 5: Situazioni Critiche e Edge Case Reali

### 5.1: Sara prova a vedere i contatti di Marco

**Contesto:** Sara e curiosa. Prova ad accedere a un contatto di Marco via URL diretto.
- **Atteso:** 403 Forbidden (row-level security tramite default_origin_id)
- **Audit log:** Evento "permission_denied" registrato
- **Perche importa:** I contatti di Marco sono proprietari dell'azienda, non di Sara.

### 5.2: L'accesso di Sara scade

**Contesto:** E il 1 ottobre 2026. Sara ha `access_expires_at=2026-09-30`.
- **Atteso:** Login fallisce con "Accesso scaduto"
- **Perche importa:** Sara era una freelancer temporanea. Non deve piu accedere ai dati.

### 5.3: Marco perde un deal

**Contesto:** TechnoSteel cambia idea dopo 3 mesi. Marco deve chiudere il deal come "Perso".
- **Azioni:** `PATCH /crm/deals/{id}` — stage_id = Perso, lost_reason = "Budget riallocato a altro progetto"
- **Perche importa:** Il "perso" conta nelle analytics (win rate cala). Marco deve registrare il motivo per pattern analysis.
- **Verifica:** Win rate ricalcolato, deal non appare piu nella pipeline attiva

### 5.4: Un contatto arriva da 2 canali diversi

**Contesto:** Il CEO di "DataFlow Srl" incontra Marco a una fiera E riceve un InMail da Sara lo stesso giorno.
- **Problema:** Chi "possiede" il contatto? Chi prende la commissione?
- **Soluzione attesa:** L'admin (Laura) assegna il contatto a Marco (prima interazione) ma logga l'attivita di Sara. Se il deal chiude, entrambi possono ricevere compenso (regole con condizioni diverse).
- **Verifica:** Un contatto, 2 attivita da 2 utenti diversi, origine = "Fiera" (primo touchpoint)

### 5.5: Marco aggiunge un prodotto che non esiste piu

**Contesto:** Laura disattiva "Formazione" (non la offrono piu). Marco prova ad aggiungerlo a un deal.
- **Atteso:** Errore "Prodotto non trovato o disattivato"
- **Ma:** I deal vecchi che avevano "Formazione" mantengono il prodotto (storico immutabile)
- **Perche importa:** Il listino cambia, ma i contratti firmati no.

### 5.6: Compensi con regola tiered — verifica calcolo manuale

**Contesto:** Marco chiude 3 deal nello stesso mese: 30k + 45k + 25k = 100k totale
- **Calcolo tiered:** (50k * 5%) + (50k * 7%) = 2.500 + 3.500 = 6.000 EUR
- **Verifica:** Il sistema calcola esattamente 6.000, non 5.000 (se applicasse 5% piatto) e non 7.000 (se applicasse 7% piatto)
- **Perche importa:** I tiered sono il punto dove i bug finanziari si nascondono.

### 5.7: Sara non fa attivita per 2 settimane

**Contesto:** Paolo apre la scorecard di Sara e vede 0 attivita nelle ultime 2 settimane.
- **Atteso:** Scorecard mostra i dati vuoti senza errore (AC-147.3)
- **Perche importa:** Non deve crashare. Deve mostrare che Sara non sta lavorando, cosi Paolo puo parlarne.

### 5.8: Laura vuole capire quale canale rende di piu

**Contesto:** Dopo 3 mesi, Laura vuole sapere: investire in fiere o in LinkedIn?
- **Azioni:** Filtra deals per origin, confronta revenue e ciclo di vendita
- **Dati attesi:**
  - Fiera: 1 deal, 80k, ciclo 4 settimane, costo fiera 5k
  - LinkedIn: 1 deal, 27k, ciclo 4 settimane, costo 0 EUR
  - **ROI:** Fiera = 80k-5k = 75k netto. LinkedIn = 27k netto.
  - **Ma:** LinkedIn scala meglio (Sara puo fare 5x deal al mese, Marco no)
- **Perche importa:** Questo e il motivo per cui servono le origini configurabili. Non e un campo decorativo.

---

## Checklist Esecuzione Test

| # | Scenario | Persona | Risultato Atteso | Pass/Fail |
|---|----------|---------|------------------|-----------|
| 1.1 | Setup origini | Laura | 12 origini create | |
| 1.2 | Setup tipi attivita | Laura | 14 tipi attivita | |
| 1.3 | Setup prodotti | Laura | 4 prodotti catalogo | |
| 1.4 | Setup ruoli RBAC | Laura | Ruolo "Commerciale Esterno" | |
| 1.5 | Setup Sara (esterna) | Laura | User esterno con defaults | |
| 1.6 | Setup stadi pre-funnel | Laura | Pipeline 7 stadi | |
| 2.1 | Contatto da fiera | Marco | Contatto con origine "Fiera" | |
| 2.2 | Attivita incontro | Marco | last_contact_at aggiornato | |
| 2.3 | Deal in Prospect | Marco | Deal pre-funnel, prob 5% | |
| 2.4 | Qualifica telefonica | Marco | Deal mosso a Nuovo Lead | |
| 2.5 | Prodotti su deal | Marco | Revenue = 116k auto-calcolata | |
| 2.6 | Negoziazione prezzo | Marco | price_override su linea, listino invariato | |
| 2.7 | Registra ordine | Marco | order_type, reference salvati | |
| 2.8 | Conferma deal | Marco | probability 100% | |
| 3.1 | Contatto LinkedIn | Sara | Origine pre-compilata "LinkedIn" | |
| 3.2 | Engagement LinkedIn | Sara | 4 attivita, last_contact aggiornato | |
| 3.3 | InMail + nurturing | Sara | Deal mosso a Contatto Qualificato | |
| 3.4 | Demo + chiusura | Sara | Deal confermato, 27k | |
| 4.1 | Dashboard KPI | Paolo | 4 widget con dati | |
| 4.2 | Scorecard Marco | Paolo | 80k revenue, 1 deal | |
| 4.3 | Scorecard Sara | Paolo | 27k revenue, 1 deal | |
| 4.4 | Filtro per prodotto | Paolo | Solo deal con Consulenza AI | |
| 4.5 | Regole compensi | Laura | 3 regole create | |
| 4.6 | Calcolo compensi | Laura | Marco 4.600, Sara 1.850 | |
| 4.7 | Conferma + pagamento | Laura | Status confirmed → paid | |
| 4.8 | Export audit | Laura | CSV con SHA256 | |
| 5.1 | Row-level security | Sara | 403 su contatto Marco | |
| 5.2 | Accesso scaduto | Sara | Login rifiutato | |
| 5.3 | Deal perso | Marco | Win rate ricalcolato | |
| 5.4 | Contatto 2 canali | Laura | 1 contatto, 2 attivita | |
| 5.5 | Prodotto disattivato | Marco | Errore, storico invariato | |
| 5.6 | Tiered 100k | Sistema | Esattamente 6.000 EUR | |
| 5.7 | Scorecard vuota | Paolo | KPI a zero, no errore | |
| 5.8 | ROI per canale | Laura | Confronto Fiera vs LinkedIn | |

---

*Piano creato il 2026-04-05*
*Per: AgentFlow PMI — Social Selling Module (US-130→US-150)*
