# Flusso delle Informazioni — AgentFlow PMI (ContaBot)

---

## 1. Il Quadro Generale (Big Picture)

```
FONTI DATI                    AGENTI                      DESTINAZIONI
(da dove entrano i dati)      (chi li processa)           (dove finiscono)

┌─────────────────────┐
│  1. CASSETTO FISCALE │──┐
│     (AdE via FiscoAPI)│  │    ┌──────────────┐     ┌──────────────────┐
│     [v0.1 PRIMARIA]  │  ├───>│  FiscoAgent   │────>│  PostgreSQL      │
└─────────────────────┘  │    │  (scarica XML) │     │  (tabella        │
                          │    └──────┬───────┘     │   invoices)      │
┌─────────────────────┐  │           │              └────────┬─────────┘
│  2. A-CUBE SDI       │──┤           ▼                      │
│     (webhook real-time)│  │    ┌──────────────┐            │
│     [v0.2]           │  ├───>│  Parser Agent │            │
└─────────────────────┘  │    │  (lxml → dati  │            │
                          │    │   strutturati) │            │
┌─────────────────────┐  │    └──────┬───────┘            │
│  3. EMAIL (MCP)      │──┤           │                      │
│     Gmail/PEC/Outlook │  │           ▼                      │
│     [v0.2]           │──┤    ┌──────────────┐            │
└─────────────────────┘  │    │ Learning Agent│            │
                          │    │ (categorizza  │            │
┌─────────────────────┐  │    │  con rules +  │            │
│  4. UPLOAD MANUALE   │──┘    │  similarity)  │            │
│     PDF/foto/XML      │       └──────┬───────┘            │
│     [v0.2]           │              │                      │
└─────────────────────┘              ▼                      │
                               ┌──────────────┐            │
                               │   UTENTE      │            │
                               │ (verifica/    │            │
                               │  corregge     │            │
                               │  categoria)   │            │
                               └──────┬───────┘            │
                                      │                      │
                                      ▼                      │
                               ┌──────────────┐            │
                               │  ContaAgent   │            │
                               │ (registra in  │──────────>│
                               │  partita      │     ┌──────┴──────────┐
                               │  doppia)      │────>│  ODOO CE 18     │
                               └──────────────┘     │  (partita doppia │
                                                     │   piano conti,   │
                                                     │   registri IVA,  │
                                                     │   bilancio CEE)  │
                                                     └─────────────────┘
```

---

## 2. Il Flusso Passo per Passo (v0.1 — MVP)

Ecco cosa succede dall'inizio alla fine, in ordine:

### Fase A: L'utente si registra (US-01, US-02, US-03)

```
Utente
  │
  ├─1─> Si registra (email + password)        → PostgreSQL: tabella users
  │
  ├─2─> Compila profilo (tipo azienda,        → PostgreSQL: tabella tenants
  │     regime fiscale, P.IVA, ATECO)
  │
  └─3─> Si autentica con SPID/CIE             → FiscoAPI riceve il token
        (redirect a FiscoAPI)                  → PostgreSQL: token encrypted
```

### Fase B: Le fatture entrano nel sistema (US-04, US-05)

```
FiscoAgent (automatico, ogni giorno alle 06:00)
  │
  ├─1─> Chiama FiscoAPI con token SPID
  │     "Dammi le fatture nuove dal cassetto"
  │
  ├─2─> FiscoAPI risponde con N file XML
  │     (fatture in formato FatturaPA)
  │
  ├─3─> Per ogni XML:
  │     └─> Pubblica evento "invoice.downloaded" su Redis
  │
  │     ┌─────── REDIS EVENT BUS ──────────┐
  │     │  invoice.downloaded               │
  │     └────────────┬─────────────────────┘
  │                  │
  │                  ▼
  │     Parser Agent (sottoscritto a Redis)
  │     │
  │     ├─> Apre il file XML con lxml
  │     ├─> Estrae: emittente, P.IVA, importo,
  │     │   IVA (per aliquota), data, numero,
  │     │   tipo documento, righe dettaglio
  │     │
  │     └─> Pubblica "invoice.parsed" su Redis
  │
  │     ┌─────── REDIS EVENT BUS ──────────┐
  │     │  invoice.parsed                   │
  │     │  {emittente, piva, importo, ...}  │
  │     └────────────┬─────────────────────┘
  │                  │
  └─> Salva in PostgreSQL (tabella invoices, source="cassetto_fiscale")
```

### Fase C: La fattura viene categorizzata (US-10, US-11)

```
Learning Agent (sottoscritto a "invoice.parsed")
  │
  ├─1─> Riceve i dati strutturati della fattura
  │
  ├─2─> Cerca match nelle regole:
  │     "P.IVA 01234567890 = Studio Rossi = categoria Consulenze"
  │     │
  │     ├─ SE match con confidence >70%:
  │     │  └─> Propone categoria + confidence score
  │     │
  │     ├─ SE match con confidence 40-70%:
  │     │  └─> Propone categoria con flag "verifica consigliata"
  │     │
  │     └─ SE nessun match (<40%):
  │        └─> Marca come "categoria: nessuna, richiede verifica"
  │
  ├─3─> Pubblica "invoice.categorized" su Redis
  │
  │     ┌─────── REDIS EVENT BUS ──────────┐
  │     │  invoice.categorized              │
  │     │  {fattura_id, categoria, conf.}   │
  │     └──────────────────────────────────┘
  │
  └─4─> L'utente vede la fattura nella dashboard:
        │
        ├─ Conferma (click) → feedback positivo al modello
        │
        └─ Corregge (seleziona altra categoria) → feedback negativo
           └─> Il Learning Agent impara per la prossima volta
```

### Fase D: La fattura viene registrata in contabilita (US-12, US-13)

```
ContaAgent (sottoscritto a "invoice.categorized")
  │
  ├─1─> Riceve fattura categorizzata e verificata
  │
  ├─2─> Determina i conti contabili:
  │     Esempio fattura passiva "Consulenze" da E1.220 (E1.000 + E220 IVA):
  │
  │     DARE: 6110 Consulenze       E1.000,00
  │     DARE: 2212 IVA a credito      E220,00
  │     AVERE: 4010 Fornitori       E1.220,00
  │
  ├─3─> Chiama Odoo API (XML-RPC/JSON-2):
  │     "Crea account.move con queste righe"
  │
  │     ┌─────────────────────────────────┐
  │     │          ODOO CE 18             │
  │     │  (headless — l'utente non lo    │
  │     │   vede mai direttamente)        │
  │     │                                 │
  │     │  Moduli attivi:                 │
  │     │  • l10n_it_account              │
  │     │  • l10n_it_vat_registries       │
  │     │  • l10n_it_financial_statements │
  │     │  • ...80+ moduli OCA            │
  │     │                                 │
  │     │  Cosa fa:                       │
  │     │  • Valida DARE = AVERE          │
  │     │  • Registra nel registro IVA    │
  │     │  • Aggiorna bilancio            │
  │     │  • Tiene lo storico             │
  │     └─────────────────────────────────┘
  │
  └─4─> Pubblica "journal.entry.created" su Redis
        └─> La dashboard si aggiorna in real-time
```

### Fase E: L'utente vede tutto nella dashboard (US-14, US-15, US-16)

```
┌────────────────────────────────────────────────────────┐
│                   REACT DASHBOARD                       │
│                                                        │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐  │
│  │ FATTURE      │  │ CONTABILITA │  │ AGENTI       │  │
│  │              │  │             │  │              │  │
│  │ Totali: 47   │  │ Scritture:  │  │ FiscoAgent ✅│  │
│  │ Da verificare│  │ 38          │  │ Parser    ✅ │  │
│  │   : 9        │  │             │  │ Learning  ✅ │  │
│  │ Registrate   │  │ DARE=AVERE  │  │ ContaAgent ✅│  │
│  │   : 38       │  │ sempre ✓    │  │              │  │
│  └─────────────┘  └─────────────┘  └──────────────┘  │
│                                                        │
│  ┌─────────────────────────────────────────────────┐  │
│  │ ULTIMO SYNC CASSETTO: oggi 06:12 — 3 nuove     │  │
│  └─────────────────────────────────────────────────┘  │
│                                                        │
│  Dati letti da: PostgreSQL (fatture, agenti)           │
│                  Odoo API (scritture, bilancio)        │
└────────────────────────────────────────────────────────┘
```

---

## 3. Come comunicano i componenti (Event Bus)

Tutti gli agenti parlano tra loro tramite Redis Pub/Sub. Non si chiamano direttamente — pubblicano eventi e chi e interessato li ascolta:

```
EVENTO                     CHI LO PUBBLICA      CHI LO ASCOLTA
─────────────────────────────────────────────────────────────
invoice.downloaded         FiscoAgent            Parser Agent
invoice.parsed             Parser Agent          Learning Agent, Dashboard
invoice.categorized        Learning Agent        ContaAgent, Dashboard
journal.entry.created      ContaAgent            Dashboard
deadline.approaching       FiscoAgent (v0.2)     Notification Agent
payment.matched            CashFlowAgent (v0.3)  Dashboard
```

Se Redis e down, gli eventi vanno in una **dead letter queue** locale e vengono reinviati quando Redis torna su.

---

## 4. Dove vivono i dati

```
┌─────────────────────────────────────────────────────────────┐
│                    POSTGRESQL (FastAPI)                       │
│                                                             │
│  users            → chi e registrato, token OAuth           │
│  tenants          → tipo azienda, regime, subscription      │
│  invoices         → cache fatture + metadati                │
│  fiscal_deadlines → scadenze fiscali calcolate              │
│  agent_events     → log di tutto (event sourcing)           │
│  categorization_feedback → feedback utente per learning     │
│  bank_accounts    → conti collegati PSD2 (v0.3)             │
│  bank_transactions → movimenti bancari sync (v0.3)          │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    ODOO CE 18 (separato)                     │
│                                                             │
│  account.account     → piano dei conti (CEE)                │
│  account.move        → registrazioni contabili              │
│  account.move.line   → righe dare/avere                     │
│  account.journal     → registri (vendite, acquisti, banca)  │
│  account.tax         → aliquote IVA                         │
│  + moduli OCA l10n-italy per tutto il resto                 │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    REDIS                                     │
│                                                             │
│  Pub/Sub events    → comunicazione tra agenti               │
│  Cache             → dati frequenti (dashboard summary)     │
│  Sessions          → JWT sessions utente                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. Flusso per Versione

### v0.1 — Il cuore (13 stories, 77 SP)

```
SPID → Cassetto Fiscale → XML → Parsing → Categorizzazione → Partita Doppia → Dashboard
```

Tutto il valore e qui. L'utente si autentica con SPID, le fatture arrivano dal cassetto, vengono parsate, categorizzate, e registrate in contabilita. La dashboard mostra tutto.

### v0.2 — Canali secondari (7 stories, 32 SP)

```
+ Email MCP ─────┐
+ Upload manuale ─┼──> OCR (per non-XML) ──> stesso flusso di v0.1
+ A-Cube webhook ─┘
+ Scadenzario
+ Notifiche WhatsApp/Telegram
+ Report per commercialista
```

Si aggiungono altri modi per far entrare le fatture, e si aggiungono output (notifiche, report).

### v0.3 — Banca e fisco avanzato (7 stories, 50 SP)

```
+ Open Banking ──> Movimenti bancari ──> Riconciliazione fatture<->pagamenti
                                      ──> Cash flow predittivo 90gg
+ Fatturazione attiva SDI (emissione fatture)
+ Liquidazione IVA automatica
+ Bilancio CEE
```

Il sistema diventa bidirezionale: non solo riceve fatture, ma le emette. E con i dati bancari, puo prevedere il futuro.

### v0.4 — Automazione (2 stories, 13 SP)

```
+ Pagamenti fornitori (PISP) ──> ciclo completo fattura→pagamento→registrazione
+ Monitor normativo ──> aggiornamenti automatici delle regole
```

---

## 6. Servizi Esterni — Chi fa cosa

```
SERVIZIO          COSA FA                           QUANDO
──────────────────────────────────────────────────────────
FiscoAPI          Accede al cassetto fiscale AdE     v0.1 (giornaliero)
                  via SPID/CIE. Scarica fatture,
                  F24, dichiarazioni.

A-Cube SDI        Riceve fatture in real-time         v0.2 (webhook)
                  dal Sistema di Interscambio.
                  Invia fatture attive (v0.3).

A-Cube AISP       Legge saldi e movimenti del         v0.3 (giornaliero)
                  conto corrente via Open Banking.

A-Cube PISP       Dispone pagamenti fornitori          v0.4 (on-demand)
                  dal conto corrente.

CBI Globe         Infrastruttura bancaria che          v0.3 (trasparente)
                  collega 400+ banche italiane.
                  Usato da A-Cube sotto il cofano.

Google Vision     OCR su PDF/immagini di fatture       v0.2 (on-demand)
                  non elettroniche.

Odoo CE 18        Engine contabile headless.            v0.1 (sempre)
                  Partita doppia, piano conti,
                  IVA, bilancio. L'utente non
                  lo vede mai.
```

---

## 7. Domanda chiave: perche il cassetto fiscale e la fonte primaria?

```
PRIMA (pre-pivot):                    DOPO (post-pivot):

Email → cerca fatture tra             Cassetto Fiscale → ha GIA tutte
       migliaia di email                    le fatture in XML strutturato
     → OCR su PDF (errori)                → accuracy ~100% (dati nativi)
     → parsing XML (se trova)             → nessun OCR necessario
     → dipende da Gmail API              → via FiscoAPI + SPID
                                          → 95%+ delle fatture italiane

Email diventa SECONDARIA              Email aggiunta dopo come MCP
(v0.2+) per documenti                server per catturare proforma,
non-SDI                               ricevute, fatture estere
```

La fatturazione elettronica e obbligatoria dal 2024. Il cassetto fiscale e la fonte di verita.

---

## 8. Il Flusso Conto Corrente (v0.3-v0.4)

Il conto corrente e la **seconda gamba** del sistema. La prima (fatturazione) registra cosa si deve e a chi. La seconda (banca) registra cosa si paga e quando. Insieme, chiudono il cerchio.

### 8.1 Big Picture — Flusso Banca

```
BANCA DELL'UTENTE                   CONTABOT                         DESTINAZIONI
(400+ banche italiane)

┌─────────────────────┐
│  Conto Corrente     │
│  (IBAN: IT...)      │
│                     │     ┌────────────────────────────────────────────────┐
│  Movimenti:         │     │                                                │
│  - Bonifici in/out  │     │  CBI GLOBE (infrastruttura interbancaria)     │
│  - RiBa             │     │  400+ banche italiane collegate               │
│  - SDD              │     │                                                │
│  - POS/carte        │     └────────────────┬───────────────────────────────┘
│  - F24              │                      │
└─────────────────────┘                      │
                                             ▼
                              ┌──────────────────────────┐
                              │  A-CUBE API              │
                              │                          │
                              │  AISP (lettura v0.3)     │
                              │  → saldi e movimenti     │
                              │                          │
                              │  PISP (pagamenti v0.4)   │
                              │  → dispone bonifici      │
                              └──────────┬───────────────┘
                                         │
                                         ▼
                              ┌──────────────────────────┐
                              │  BankingAdapter          │
                              │  (nostro componente)     │
                              │                          │
                              │  - Gestisce consent PSD2 │
                              │  - Normalizza movimenti  │
                              │  - Dedup su              │
                              │    transaction_id        │
                              └──────────┬───────────────┘
                                         │
                        ┌────────────────┼────────────────┐
                        │                │                │
                        ▼                ▼                ▼
                 ┌────────────┐  ┌────────────┐  ┌────────────────┐
                 │ PostgreSQL │  │ CashFlow   │  │ Riconciliazione│
                 │ bank_      │  │ Agent      │  │ Agent          │
                 │ transactions│  │ (previsione│  │ (abbina fatture│
                 │            │  │  90gg)     │  │  a movimenti)  │
                 └────────────┘  └──────┬─────┘  └───────┬────────┘
                                        │                │
                                        ▼                ▼
                                 ┌────────────┐  ┌────────────────┐
                                 │ Dashboard  │  │ ODOO CE 18     │
                                 │ Cash Flow  │  │ (chiude partite│
                                 │ grafico    │  │  dare/avere)   │
                                 └────────────┘  └────────────────┘
```

### 8.2 Passo per Passo: Collegamento Conto (US-24)

```
Utente
  │
  ├─1─> Clicca "Collega conto corrente"
  │
  ├─2─> Seleziona banca dalla lista CBI Globe (400+)
  │     └─ Se non in lista → upload manuale CSV/XLS
  │     └─ Se IBAN non IT (Wise, Revolut) → verifica supporto A-Cube
  │
  ├─3─> Redirect alla banca → SCA (Strong Customer Authentication)
  │     (la banca chiede conferma con app, SMS, o token)
  │
  ├─4─> Consent PSD2 confermato → validita 90 giorni
  │     └─ Notifica 7gg prima della scadenza
  │     └─ Se revocato da portale bancario → stato "revocato" + notifica
  │
  └─5─> Primo sync: importa movimenti ultimi 90gg
        Sync successivi: solo incrementali (giornaliero)
```

### 8.3 Passo per Passo: Sync Giornaliero Movimenti

```
BankingAdapter (automatico, giornaliero)
  │
  ├─1─> Verifica consent PSD2 ancora attivo
  │     └─ Se scaduto → notifica utente, stop sync
  │
  ├─2─> Chiama A-Cube AISP:
  │     "Dammi saldi e movimenti dal last_sync_date"
  │
  ├─3─> Per ogni movimento ricevuto:
  │     │
  │     ├─ Dedup su transaction_id (evita duplicati)
  │     ├─ Normalizza: data valuta, importo, causale, controparte
  │     └─ Salva in PostgreSQL (tabella bank_transactions)
  │
  ├─4─> Pubblica "bank.transactions.synced" su Redis
  │
  │     ┌─────── REDIS EVENT BUS ──────────────┐
  │     │  bank.transactions.synced             │
  │     │  {account_id, count: 12, date_range}  │
  │     └───────────┬──────────────────────────┘
  │                 │
  │                 ├───> CashFlowAgent (ascolta)
  │                 └───> RiconciliazioneAgent (ascolta)
  │
  └─5─> Lock per tenant_id + bank_account_id
        (se sync manuale concorrente → il secondo attende)
```

### 8.4 Passo per Passo: Riconciliazione (US-26)

```
RiconciliazioneAgent (sottoscritto a "bank.transactions.synced")
  │
  ├─1─> Per ogni movimento, cerca match nelle fatture registrate:
  │
  │     CRITERI DI MATCH:
  │     ┌─────────────────────────────────────────────────────┐
  │     │  1. Importo esatto (E1.220 = fattura E1.220)       │
  │     │  2. Controparte ≈ fornitore/cliente (fuzzy match)  │
  │     │  3. Data vicina alla scadenza fattura               │
  │     │  4. Causale contiene numero fattura                 │
  │     └─────────────────────────────────────────────────────┘
  │
  ├─2─> Risultato del match:
  │     │
  │     ├─ MATCH ESATTO (tutti i criteri):
  │     │  └─> Abbina automaticamente
  │     │      └─> Marca fattura "pagata"
  │     │      └─> Pubblica "payment.matched" su Redis
  │     │      └─> Odoo: chiude la partita dare/avere
  │     │
  │     ├─ MATCH PARZIALE (importo diverso):
  │     │  └─> E3.000 fatturati, E1.500 pagati?
  │     │      └─> "Parzialmente pagata (E1.500/E3.000)"
  │     │      └─> Residuo E1.500 resta nel cash flow
  │     │
  │     ├─ MATCH SUGGERITO (non sicuro):
  │     │  └─> Propone le 3 fatture piu probabili con confidence %
  │     │      └─> L'utente conferma o abbina manualmente
  │     │
  │     └─ NESSUN MATCH:
  │        └─> Appare in "non riconciliati"
  │        └─> Opzioni: abbinare a fattura, creare fattura, o "non-fattura"
  │            (es: prelievo bancomat, commissione bancaria)
  │
  ├─3─> Movimento in VALUTA ESTERA (USD, GBP)?
  │     └─> Converte al cambio BCE del giorno
  │     └─> Abbina in EUR, logga tasso applicato
  │
  └─4─> Aggiorna dashboard riconciliazione
```

### 8.5 Passo per Passo: Cash Flow Predittivo (US-25)

```
CashFlowAgent (sottoscritto a "bank.transactions.synced" + "journal.entry.created")
  │
  ├─1─> Raccoglie dati da 3 fonti:
  │     │
  │     ├─ Saldo attuale → A-Cube AISP (via PostgreSQL cache)
  │     ├─ Fatture passive da pagare → Odoo (partite aperte dare)
  │     └─ Fatture attive da incassare → Odoo (partite aperte avere)
  │
  ├─2─> Per ogni giorno dei prossimi 90gg, proietta:
  │
  │     Giorno 1:  E23.400 (saldo attuale)
  │     Giorno 5:  E23.400 - E1.220 (fattura Studio Rossi) = E22.180
  │     Giorno 12: E22.180 + E4.800 (incasso cliente X) = E26.980
  │     Giorno 15: E26.980 - E2.440 (fattura fornitore Y) = E24.540
  │     ...
  │     Giorno 90: E18.200 (proiezione finale)
  │
  ├─3─> Controlla soglia critica:
  │     │
  │     ├─ Soglia configurabile per utente (default E5.000)
  │     │
  │     ├─ SE il saldo proiettato scende sotto soglia:
  │     │  └─> Alert: "Il [data], il saldo previsto e EX.XXX"
  │     │  └─> Dettaglio uscite critiche di quel periodo
  │     │
  │     └─ SE una fattura emessa e scaduta da 15+ giorni:
  │        └─> Due scenari: "con incasso" vs "senza incasso"
  │        └─> Evidenziata come "incasso in ritardo"
  │
  ├─4─> Controlla freschezza dati:
  │     └─ SE sync fallito da 3+ giorni:
  │        └─> Banner "Dati aggiornati al [data]"
  │
  └─5─> Genera grafico per dashboard:
        Saldo attuale → curve entrate/uscite → saldo proiettato
        (aggiornato in real-time via Redis)
```

### 8.6 Passo per Passo: Pagamento Fornitori PISP (US-27, v0.4)

```
Utente
  │
  ├─1─> Dalla fattura passiva, clicca "Paga"
  │     └─ Vede: fornitore, IBAN, importo, scadenza
  │     └─ Opzione batch: seleziona piu fatture stesso fornitore
  │        → bonifico cumulativo con causale che elenca i numeri
  │
  ├─2─> Conferma con SCA (redirect alla banca)
  │     │
  │     ├─ SE fondi insufficienti:
  │     │  └─> "Saldo: EX.XXX — suggerisco pagamento il [data]"
  │     │
  │     └─ SE IBAN non valido:
  │        └─> Errore validazione, permette correzione
  │
  ├─3─> A-Cube PISP dispone il bonifico
  │
  ├─4─> ContaBot registra automaticamente:
  │     │
  │     │  DARE: 4010 Fornitori       E1.220,00
  │     │  AVERE: 1110 Banca c/c      E1.220,00
  │     │
  │     └─> Odoo: chiude la partita fornitore
  │
  └─5─> Ciclo completo chiuso:
        fattura ricevuta → categorizzata → registrata → pagata → riconciliata
```

### 8.7 Event Bus — Eventi Banca

```
EVENTO                        CHI LO PUBBLICA          CHI LO ASCOLTA
────────────────────────────────────────────────────────────────────
bank.consent.granted          BankingAdapter            Dashboard
bank.consent.expiring         BankingAdapter (cron)     NotificationAgent
bank.consent.revoked          BankingAdapter            Dashboard, NotificationAgent
bank.transactions.synced      BankingAdapter            CashFlowAgent, RiconciliazioneAgent
payment.matched               RiconciliazioneAgent      Dashboard, CashFlowAgent
payment.partial               RiconciliazioneAgent      Dashboard, CashFlowAgent
payment.dispatched            PaymentAgent (PISP)       ContaAgent, RiconciliazioneAgent
cashflow.alert                CashFlowAgent             NotificationAgent, Dashboard
```

### 8.8 Come si integrano Fatturazione e Banca

```
IL CICLO COMPLETO DI UNA FATTURA PASSIVA (fornitore):

                    FLUSSO FATTURAZIONE (v0.1)
    ┌─────────────────────────────────────────────┐
    │                                             │
    │  Cassetto ──> Parse ──> Categorizza ──> Registra in Odoo
    │  Fiscale      XML       (Learning)      (partita doppia)
    │                                             │
    └─────────────────────────────┬───────────────┘
                                  │
                          PARTITA APERTA
                       "devo E1.220 a Studio Rossi"
                                  │
                    FLUSSO BANCA (v0.3-v0.4)
    ┌─────────────────────────────┼───────────────┐
    │                             │               │
    │  v0.3: Il pagamento arriva dalla banca      │
    │        (sync AISP) ──> Riconcilia ──> Chiude partita
    │                                             │
    │  v0.4: L'utente paga da ContaBot            │
    │        (PISP) ──> Registra uscita ──> Chiude partita
    │                                             │
    └─────────────────────────────────────────────┘
                                  │
                          PARTITA CHIUSA
                       "pagato il 15/03 — OK"
                                  │
                                  ▼
                       CASH FLOW AGGIORNATO
                       (previsione ricalcolata)
```

Il ciclo e identico per le **fatture attive** (emesse a clienti), ma al contrario: emetti fattura → aspetti incasso → riconcili quando arriva il bonifico.

---

## 9. Il Flusso Adempimenti Fiscali (v0.2-v0.4)

Gli adempimenti sono la **terza gamba**: la fatturazione dice "quanto devo/mi devono", la banca dice "cosa ho pagato/incassato", gli adempimenti dicono "cosa devo fare per lo Stato e quando". E la parte che tiene svegli i titolari di PMI.

### 9.1 Big Picture — Flusso Adempimenti

```
FONTI DATI                         AGENTI                        OUTPUT
(da dove vengono i numeri)         (chi calcola)                 (cosa produce)

┌──────────────────────┐
│  FATTURE REGISTRATE  │──┐
│  (Odoo: account.move) │  │
│  IVA credito/debito   │  │    ┌───────────────────┐     ┌──────────────────┐
└──────────────────────┘  ├───>│  FiscoAgent        │────>│ SCADENZARIO      │
                           │    │                     │     │ IVA, F24, INPS   │
┌──────────────────────┐  │    │  - Calcola scadenze │     │ con countdown    │
│  PROFILO AZIENDA     │──┤    │  - Stima importi    │     │ e semaforo       │
│  (PostgreSQL: tenants)│  │    │  - Monitora         │     └──────────────────┘
│  regime, ATECO, tipo  │  │    │    cambi normativi  │
└──────────────────────┘  │    └────────┬──────────┘     ┌──────────────────┐
                           │             │           ├───>│ ALERT & NOTIFICHE│
┌──────────────────────┐  │             │                 │ WhatsApp/Telegram│
│  CASSETTO FISCALE    │──┤             │                 │ con importo      │
│  (FiscoAPI: F24,      │  │             │                 │ stimato/ufficiale│
│   dichiarazioni)      │  │             │                 └──────────────────┘
└──────────────────────┘  │             │
                           │             ▼                ┌──────────────────┐
┌──────────────────────┐  │    ┌───────────────────┐     │ LIQUIDAZIONE IVA │
│  DATI BANCARI        │──┘    │  Odoo OCA         │────>│ Prospetto con    │
│  (bank_transactions)  │      │  l10n-italy        │     │ debito/credito   │
│  saldi, movimenti     │      │                     │     │ e drill-down     │
└──────────────────────┘       │  - Liquidazione IVA│     └──────────────────┘
                                │  - Bilancio CEE    │
                                │  - Registri IVA    │     ┌──────────────────┐
                                └───────────────────┘────>│ BILANCIO CEE     │
                                                           │ SP + CE formato  │
                                                           │ codice civile    │
                                                           │ PDF + XBRL       │
                                                           └──────────────────┘

                                                           ┌──────────────────┐
                                                      ────>│ REPORT COMMERC.  │
                                                           │ PDF trimestrale  │
                                                           │ CSV per studio   │
                                                           └──────────────────┘
```

### 9.2 Le Scadenze: Come le calcola il sistema

```
IL CALENDARIO FISCALE DI UNA PMI ITALIANA (esempio SRL regime ordinario)

MESE      SCADENZA                            CHI LA CALCOLA         VERSIONE
──────────────────────────────────────────────────────────────────────────
Gen 16    Versamento IVA dicembre              FiscoAgent + Odoo      v0.2
Feb 16    Versamento IVA gennaio               FiscoAgent + Odoo      v0.2
Feb 28    Comunicazione LIPE Q4                FiscoAgent             v0.3
Mar 16    Versamento IVA febbraio              FiscoAgent + Odoo      v0.2
Apr 16    Versamento IVA marzo / IVA Q1        FiscoAgent + Odoo      v0.2
...
Giu 16    Versamento IVA maggio                FiscoAgent + Odoo      v0.2
Giu 30    IMU 1° acconto                       FiscoAgent             v0.3
Giu 30    Dichiarazione redditi (saldo + 1°)   FiscoAgent + FiscoAPI  v0.3
...
Nov 30    Dichiarazione redditi (2° acconto)   FiscoAgent + FiscoAPI  v0.3
Dic 27    Acconto IVA                          FiscoAgent + Odoo      v0.3
──────────────────────────────────────────────────────────────────────────

REGOLA: se la scadenza cade di sabato/domenica/festivo
        → slitta al primo giorno lavorativo successivo
```

### 9.3 Passo per Passo: Scadenzario Base (US-17, v0.2)

```
FiscoAgent (al login o in background)
  │
  ├─1─> Legge il profilo azienda da PostgreSQL:
  │     - Tipo: SRL
  │     - Regime: Ordinario
  │     - ATECO: 62.01.00
  │     - Periodicita IVA: Mensile (fatturato >400K) o Trimestrale
  │
  ├─2─> Genera calendario scadenze:
  │     │
  │     │  Tabella regole interna:
  │     │  ┌──────────────────────────────────────────────┐
  │     │  │ regime=ordinario, IVA=mensile → 16 di ogni  │
  │     │  │ regime=ordinario, IVA=trimestrale → 16/5,   │
  │     │  │   16/8, 16/11, 16/2                          │
  │     │  │ regime=forfettario → nessun versamento IVA  │
  │     │  │ tipo=SRL → bilancio entro 120gg da chiusura │
  │     │  │ F24 → secondo calendario AdE per cod.tributo│
  │     │  │ INPS → trimestrale (fissi) + saldo/acconto  │
  │     │  └──────────────────────────────────────────────┘
  │     │
  │     └─> Applica regola weekend/festivi → data effettiva
  │
  ├─3─> Mostra nella dashboard:
  │
  │     ┌──────────────────────────────────────────┐
  │     │  SCADENZE IMMINENTI                      │
  │     │                                          │
  │     │  🔴 IVA mensile         16 apr (3 gg)   │
  │     │     Importo stimato: E2.340              │
  │     │                                          │
  │     │  🟡 F24 contributi      16 apr (3 gg)   │
  │     │     Importo: da verificare               │
  │     │                                          │
  │     │  🟢 INPS trimestrale   16 mag (33 gg)   │
  │     │     Importo fisso: E1.032                │
  │     └──────────────────────────────────────────┘
  │
  │     Semaforo: 🔴 <7gg | 🟡 7-15gg | 🟢 >15gg
  │
  └─4─> Pubblica "deadline.approaching" su Redis
        └─> NotificationAgent invia su WhatsApp/Telegram (v0.2)
```

### 9.4 Passo per Passo: Alert con Importo (US-20, v0.3)

```
FiscoAgent (sottoscritto a "journal.entry.created" + FiscoAPI polling)
  │
  ├─1─> Per scadenze IVA, calcola importo stimato:
  │     │
  │     │  FONTE 1 (stima interna):
  │     │  ├─ Prende da Odoo: IVA a debito (vendite) del periodo
  │     │  ├─ Prende da Odoo: IVA a credito (acquisti) del periodo
  │     │  └─ Saldo = Debito - Credito
  │     │     Esempio: E4.200 - E1.860 = E2.340 da versare
  │     │
  │     │  FONTE 2 (importo ufficiale da FiscoAPI):
  │     │  ├─ FiscoAPI fornisce F24 precompilato con codice tributo
  │     │  └─ Se disponibile, usa questo al posto della stima
  │     │
  │     └─ SE ci sono fatture non registrate:
  │        └─ "Stima provvisoria — 3 fatture in attesa di registrazione"
  │
  ├─2─> Invia alert arricchito:
  │
  │     ┌──────────────────────────────────────────────┐
  │     │  ⚠️ SCADENZA IVA TRA 10 GIORNI              │
  │     │                                              │
  │     │  Periodo: Q1 2026 (gen-mar)                  │
  │     │  IVA debito:   E4.200                        │
  │     │  IVA credito: -E1.860                        │
  │     │  ──────────────────────────                  │
  │     │  DA VERSARE:    E2.340                       │
  │     │                                              │
  │     │  Codice tributo: 6001 (versamento IVA gen)   │
  │     │  Scadenza: 16 aprile 2026                    │
  │     │                                              │
  │     │  ⚠️ 3 fatture non ancora registrate          │
  │     │  [Vedi dettaglio] [Registra ora]             │
  │     └──────────────────────────────────────────────┘
  │
  └─3─> Caso speciale: CAMBIO REGIME in corso d'anno
        DATO che l'utente passa da forfettario a ordinario
        → ricalcola TUTTE le scadenze dalla data di cambio
        → il periodo pre-cambio segue regole forfettario
        → il periodo post-cambio segue regole ordinario
```

### 9.5 Passo per Passo: Liquidazione IVA (US-22, v0.3)

```
FiscoAgent + Odoo OCA (automatico, al 10° giorno dopo fine trimestre)
  │
  ├─1─> Chiama Odoo OCA modulo l10n_it_vat_registries:
  │     "Calcola liquidazione IVA per Q1 2026"
  │
  ├─2─> Odoo esegue il calcolo:
  │
  │     REGISTRO VENDITE (IVA a debito):
  │     ┌──────────────────────────────────────────────┐
  │     │  Fattura 2026/001  IVA 22%  E220,00          │
  │     │  Fattura 2026/002  IVA 22%  E440,00          │
  │     │  Fattura 2026/003  IVA 10%  E150,00          │
  │     │  Fattura 2026/004  IVA 22%  E660,00          │
  │     │  ──────────────────────────────              │
  │     │  Totale IVA debito:       E1.470,00          │
  │     └──────────────────────────────────────────────┘
  │
  │     REGISTRO ACQUISTI (IVA a credito):
  │     ┌──────────────────────────────────────────────┐
  │     │  Fattura ACQ/001   IVA 22%  E264,00          │
  │     │  Fattura ACQ/002   IVA 22%  E176,00          │
  │     │  Fattura ACQ/003   IVA 22%  E132,00          │
  │     │  ──────────────────────────────              │
  │     │  Totale IVA credito:        E572,00          │
  │     └──────────────────────────────────────────────┘
  │
  ├─3─> Calcola saldo:
  │     │
  │     │  IVA debito:    E1.470,00
  │     │  IVA credito:  -E572,00
  │     │  Credito Q4:   -E0,00    ← riporto trimestre precedente
  │     │  ────────────────────
  │     │  DA VERSARE:    E898,00
  │     │
  │     │  Casi speciali gestiti:
  │     │  • Reverse charge → computato sia a debito che a credito
  │     │  • Credito precedente → sottratto dal debito corrente
  │     │  • Fatture non registrate → warning con lista
  │
  ├─4─> Mostra prospetto nella dashboard:
  │
  │     ┌──────────────────────────────────────────────┐
  │     │  LIQUIDAZIONE IVA — Q1 2026                  │
  │     │                                              │
  │     │  IVA debito (vendite):    E1.470,00          │
  │     │    di cui al 22%: E1.320   al 10%: E150     │
  │     │                                              │
  │     │  IVA credito (acquisti): -E572,00            │
  │     │    di cui al 22%: E572                       │
  │     │                                              │
  │     │  Credito precedente:      E0,00              │
  │     │  ─────────────────────────────               │
  │     │  SALDO DA VERSARE:        E898,00            │
  │     │                                              │
  │     │  Scadenza versamento: 16 maggio 2026         │
  │     │  Cod. tributo: 6031 (IVA Q1)                │
  │     │                                              │
  │     │  [Drill-down vendite] [Drill-down acquisti]  │
  │     │  [Genera F24] [Scarica prospetto PDF]        │
  │     └──────────────────────────────────────────────┘
  │
  └─5─> Pubblica "vat.settlement.computed" su Redis
        └─> Dashboard aggiornata
        └─> Alert se importo > soglia utente
```

### 9.6 Passo per Passo: Bilancio CEE (US-23, v0.3)

```
Utente (di solito a fine esercizio o su richiesta)
  │
  ├─1─> Clicca "Genera bilancio CEE"
  │
  ├─2─> Verifica prerequisiti:
  │     │
  │     ├─ SE ci sono scritture provvisorie:
  │     │  └─ "N scritture da chiudere prima" + lista + azione
  │     │
  │     └─ SE OK:
  │        └─ Chiama Odoo OCA modulo l10n_it_financial_statements
  │
  ├─3─> Odoo genera il bilancio:
  │
  │     STATO PATRIMONIALE (schema CEE art. 2424 c.c.)
  │     ┌───────────────────────────────────────────────┐
  │     │  ATTIVO                      2026     2025    │
  │     │  A) Crediti verso soci        —        —     │
  │     │  B) Immobilizzazioni                         │
  │     │     I. Immateriali          E5.000   E3.000  │
  │     │     II. Materiali          E12.000  E10.000  │
  │     │  C) Attivo circolante                        │
  │     │     I. Rimanenze                  ...        │
  │     │     II. Crediti            E34.000  E28.000  │
  │     │     IV. Disponibilita      E23.400  E18.000  │
  │     │  ────────────────────────────────────        │
  │     │  TOTALE ATTIVO            E74.400  E59.000  │
  │     │                                              │
  │     │  PASSIVO                                     │
  │     │  A) Patrimonio netto      E45.000  E38.000  │
  │     │  B) Fondi rischi                    ...      │
  │     │  D) Debiti                E29.400  E21.000  │
  │     │  ────────────────────────────────────        │
  │     │  TOTALE PASSIVO           E74.400  E59.000  │
  │     └───────────────────────────────────────────────┘
  │
  │     CONTO ECONOMICO (schema CEE art. 2425 c.c.)
  │     ┌───────────────────────────────────────────────┐
  │     │  A) Valore della produzione        E120.000  │
  │     │  B) Costi della produzione        -E105.000  │
  │     │  ────────────────────────────────────        │
  │     │  Differenza (A-B)                   E15.000  │
  │     │  C) Proventi/oneri finanziari         -E200  │
  │     │  ────────────────────────────────────        │
  │     │  Risultato prima imposte            E14.800  │
  │     │  Imposte                            -E4.200  │
  │     │  ────────────────────────────────────        │
  │     │  UTILE D'ESERCIZIO                 E10.600  │
  │     └───────────────────────────────────────────────┘
  │
  ├─4─> Adatta al tipo di impresa:
  │     │
  │     ├─ SRL/SPA ordinaria → bilancio completo CEE
  │     ├─ Micro-impresa (art. 2435-ter) → formato abbreviato
  │     └─ Primo esercizio → colonna "anno precedente" vuota
  │
  └─5─> Esporta:
        ├─ PDF (per consultazione)
        └─ XBRL (per deposito CCIAA — obbligo legale)
```

### 9.7 Passo per Passo: Report per Commercialista (US-19, v0.2)

```
Utente
  │
  ├─1─> Clicca "Genera report" + seleziona periodo (es. Q1 2026)
  │
  ├─2─> Sceglie formato:
  │     │
  │     ├─ PDF → per consultazione/stampa
  │     │  Contenuto:
  │     │  ├─ Riepilogo fatture (attive e passive)
  │     │  ├─ Registri IVA (vendite + acquisti)
  │     │  ├─ Prima nota (tutte le scritture)
  │     │  ├─ Totali per categoria
  │     │  └─ Avviso se ci sono fatture non registrate
  │     │
  │     └─ CSV → per importazione nel software di studio
  │        Formato: data | numero | importo | IVA | conto
  │        Compatibile con Zucchetti, TeamSystem, Profis, Wolters Kluwer
  │
  ├─3─> SE periodo senza fatture:
  │     └─ "Nessuna fattura nel periodo" (non genera PDF vuoto)
  │
  └─4─> SE ci sono fatture non categorizzate:
        └─ "5 fatture in attesa — includi o escludi?"
```

### 9.8 Passo per Passo: Fatturazione Attiva SDI (US-21, v0.3)

```
Utente (vuole emettere fattura a un cliente)
  │
  ├─1─> Compila la fattura:
  │     Cliente, P.IVA, importo, aliquota IVA, descrizione
  │     │
  │     ├─ Validazione in tempo reale:
  │     │  - P.IVA cliente → formato valido?
  │     │  - Numero fattura → non duplicato?
  │     │  - Importo → positivo?
  │     │
  │     └─ Se nota di credito:
  │        → tipo documento TD04 + riferimento fattura originale
  │
  ├─2─> Clicca "Invia via SDI"
  │
  ├─3─> Il sistema:
  │     │
  │     ├─ Crea account.move su Odoo (registrazione contabile)
  │     │
  │     │  DARE: 3010 Crediti vs clienti    E1.220,00
  │     │  AVERE: 4110 Ricavi              E1.000,00
  │     │  AVERE: 2211 IVA a debito          E220,00
  │     │
  │     ├─ Genera XML FatturaPA
  │     │  (formato standard italiano, namespace 1.2.2)
  │     │
  │     └─ Invia ad A-Cube SDI API
  │
  ├─4─> Monitora stato in real-time:
  │     │
  │     │  Inviata → Consegnata → Accettata ✅
  │     │                       → Rifiutata ❌ (motivo SDI)
  │     │                          └─> L'utente corregge e reinvia
  │     │
  │     └─ Webhook A-Cube aggiorna lo stato
  │
  └─5─> Pubblica "invoice.sent" su Redis
        └─> Dashboard aggiornata
        └─> CashFlowAgent aggiunge l'incasso atteso
```

### 9.9 Passo per Passo: Monitor Normativo (US-28, v0.4)

```
NormativoAgent (polling periodico)
  │
  ├─1─> Monitora fonti:
  │     ├─ Feed RSS Gazzetta Ufficiale
  │     ├─ API Agenzia delle Entrate (circolari, risoluzioni)
  │     └─ Feed ANC/CNDCEC (ordine commercialisti)
  │
  ├─2─> Filtra per rilevanza:
  │     "Questa norma riguarda il regime/tipo azienda del mio utente?"
  │
  ├─3─> SE norma rilevante trovata:
  │     │
  │     ├─ Genera riepilogo semplificato:
  │     │  "Dal 1/7/2026, l'aliquota IVA per servizi digitali
  │     │   passa dal 22% al 20% (DL 45/2026)"
  │     │
  │     ├─ Calcola impatto:
  │     │  "Per te: -E440/anno sulle fatture attive"
  │     │
  │     ├─ Azioni suggerite:
  │     │  "Aggiornare aliquota IVA nel piano conti dal 1/7"
  │     │
  │     └─ SE decorrenza futura (>30gg):
  │        └─ Schedula per la data giusta
  │        └─ Non modifica regole correnti
  │
  ├─4─> SE feed non disponibili:
  │     └─ Riprova con backoff esponenziale
  │     └─ Continua con regole attuali
  │
  └─5─> Propone aggiornamento regole:
        └─ Preview impatto → conferma utente → applica
        (MAI applica automaticamente senza conferma)
```

### 9.10 Event Bus — Eventi Adempimenti

```
EVENTO                         CHI LO PUBBLICA       CHI LO ASCOLTA
─────────────────────────────────────────────────────────────────────
deadline.approaching           FiscoAgent             NotificationAgent, Dashboard
deadline.computed              FiscoAgent             Dashboard
vat.settlement.computed        FiscoAgent/Odoo        Dashboard, NotificationAgent
balance.sheet.generated        Odoo OCA               Dashboard
report.generated               ReportAgent            Dashboard
invoice.sent                   SDI Agent (A-Cube)     ContaAgent, CashFlowAgent
invoice.delivery.status        SDI Agent (webhook)    Dashboard, NotificationAgent
regulation.detected            NormativoAgent         Dashboard, NotificationAgent
regulation.applied             NormativoAgent         FiscoAgent, ContaAgent
```

### 9.11 Come si integrano i Tre Flussi

```
┌─────────────────────────────────────────────────────────────────┐
│                   IL QUADRO COMPLETO                             │
│                                                                 │
│   FLUSSO 1: FATTURAZIONE                                       │
│   "Quanto devo e a chi?"                                        │
│   Cassetto → Parse → Categorizza → Registra                    │
│   (ricezione fatture passive, emissione fatture attive)         │
│        │                                                        │
│        ├──> DATI per Flusso 2 (fatture da pagare/incassare)    │
│        └──> DATI per Flusso 3 (IVA, scadenze, bilancio)       │
│                                                                 │
│   FLUSSO 2: BANCA                                              │
│   "Cosa ho pagato e incassato?"                                 │
│   Open Banking → Sync → Riconcilia → Cash Flow                 │
│   (movimenti bancari, match con fatture)                        │
│        │                                                        │
│        ├──> DATI per Flusso 1 (chiude partite aperte)          │
│        └──> DATI per Flusso 3 (saldi per F24, liquidita)       │
│                                                                 │
│   FLUSSO 3: ADEMPIMENTI                                        │
│   "Cosa devo fare per lo Stato e quando?"                       │
│   Scadenze → Alert → Liquidazione IVA → Bilancio → Report      │
│   (obblighi fiscali, compliance, export commercialista)         │
│        │                                                        │
│        └──> DATI per Flusso 1 (aliquote aggiornate)            │
│                                                                 │
│   ═══════════════════════════════════════════                   │
│   I TRE FLUSSI SI ALIMENTANO A VICENDA:                        │
│   le fatture generano dati per banca e fisco,                   │
│   la banca conferma i pagamenti delle fatture,                  │
│   il fisco aggiorna le regole per fatture e banca.              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 10. Riepilogo: Cosa entra in ogni versione

```
v0.1  FATTURAZIONE BASE
      SPID → Cassetto → Parse → Categorizza → Registra → Dashboard
      ────────────────────────────────────────────────────────────

v0.2  + CANALI SECONDARI + OUTPUT
      + Email MCP, Upload, A-Cube SDI, OCR
      + Scadenzario, Notifiche, Report
      ────────────────────────────────────────────────────────────

v0.3  + BANCA (LETTURA) + FISCO AVANZATO + GAP CONTABILI
      + Open Banking AISP (saldi, movimenti)
      + Riconciliazione (fatture ↔ pagamenti)
      + Cash Flow predittivo 90gg
      + Fatturazione attiva SDI
      + Liquidazione IVA, Bilancio CEE
      + Note spese, Cespiti, Ritenute, Imposta bollo, Ratei/risconti
      ────────────────────────────────────────────────────────────

v0.4  + BANCA (SCRITTURA) + NORMATIVO + CRUSCOTTO CEO
      + Pagamenti PISP (disponi bonifici)
      + Monitor normativo (GU + AdE)
      + Dashboard CEO (fatturato, margini, KPI, budget vs consuntivo)
      + F24 compilazione, CU annuale, Conservazione digitale
      → CICLO FATTURA COMPLETAMENTE CHIUSO
      ────────────────────────────────────────────────────────────

v1.0  + COPILOTA DEL CEO
      + ControllerAgent (centri di costo, budget, analisi scostamenti)
      + HRAgent base (costo personale, budget HR, scadenzario contratti)
      + CommAgent base (CRM, pipeline, preventivi)
      + Multi-tenant + white-label commercialisti
      ────────────────────────────────────────────────────────────

v1.5  + GESTIONE OPERATIVA COMPLETA
      + ProjectAgent (commesse, timesheet, margine, SAL)
      + DocAgent (repository, contratti, scadenzario rinnovi)
      + FornitureAgent (ordini acquisto, albo fornitori)
      ────────────────────────────────────────────────────────────

v2.0  + ENTERPRISE
      + ComplianceAgent (81/08, GDPR, antiriciclaggio)
      + Marketplace agenti third-party + API pubblica
      → L'AZIENDA INTERA GESTITA DA AGENTI AI
```
