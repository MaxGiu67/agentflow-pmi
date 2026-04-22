# Spec di Prodotto — Modulo Social Selling per CRM B2B PMI

> Specifica funzionale per estendere un CRM classico B2B (AgentFlow) con un modulo di social selling configurabile, progettato come piattaforma generica adattabile a qualsiasi PMI, personalizzabile sulle esigenze specifiche di ogni azienda.

**Data:** 4 aprile 2026
**Versione:** 2.0
**Approccio architetturale:** Prodotto configurabile (core engine generico + configuration layer per PMI)

---

## 1. Vision del prodotto

Costruire un **modulo CRM per social selling** che qualsiasi PMI B2B possa attivare e configurare per gestire un canale di vendita su piattaforme social (LinkedIn come caso primario), tipicamente affidato a un collaboratore esterno (fractional account manager).

Il modulo non è un prodotto a sé: è un'estensione di AgentFlow che si integra con la pipeline, i contatti e le analytics esistenti, aggiungendo ciò che manca per governare il canale social.

**Principio di design:** Tutto ciò che è specifico di una singola PMI (nomi, template, regole, prodotti, KPI) è **configurabile dall'admin**. Il codice non contiene mai riferimenti a clienti, prodotti o settori specifici.

---

## 2. Architettura: Core Engine + Configuration Layer

### 2.1 Core Engine (codice, uguale per tutti)

Il motore generico gestisce:

- **Pipeline configurabile** — stadi custom con probabilità, colori e regole di transizione definibili dall'admin
- **Pre-funnel social** — stadi di warm-up prima del "Nuovo Lead", attivabili/disattivabili, rinominabili
- **Sistema ruoli RBAC** — ruoli custom con permessi granulari (read, write, delete, export per ogni entità)
- **Activity tracking multi-tipo** — tipi di attività definibili dall'admin, con campi custom
- **Sequenze multi-canale** — engine per sequenze con trigger, condizioni, pause/resume, timezone-aware
- **Analytics engine** — KPI calcolati dinamicamente su qualsiasi campo/entità, dashboard componibili
- **Attribution engine** — modello first-touch/last-touch/split, configurabile per canale
- **Audit trail** — log immutabile di ogni azione, per ogni utente, con timestamp

### 2.2 Configuration Layer (dati, diverso per ogni PMI)

Ogni PMI configura:

| Cosa si configura | Esempio Nexa Data | Esempio PMI manifatturiera |
|-------------------|------------------|---------------------------|
| Origini contatto | linkedin_organico, linkedin_dm, linkedin_inmail | fiera_mecspe, linkedin_dm, sito_web |
| Tipi di attività | social_connection, social_dm, social_engagement | visita_stabilimento, social_dm, call_tecnica |
| Stadi pre-funnel | Profilo identificato → Connesso → In conversazione → Interesse | Contatto fiera → Campione inviato → Feedback → Interesse |
| Stadi pipeline | Standard 6 stadi | Custom: Richiesta preventivo → Sopralluogo → Offerta → Ordine |
| Catalogo prodotti | elevia (SaaS), Consulenza AI, Assessment | Linea CNC, Ricambi, Manutenzione programmata |
| Template messaggi | Intro elevia, Post-demo, Case study AI | Intro catalogo, Post-visita, Scheda tecnica |
| Sequenze | LinkedIn → Demo elevia → Proposta | Fiera → Campione → Preventivo → Ordine |
| Ruoli custom | Fractional LinkedIn, Commerciale interno | Agente di zona, Distributore esterno |
| KPI dashboard | Lead LinkedIn, Win rate elevia, ROI fractional | Lead fiere, Conversion rate ricambi, Fatturato agente |
| Regole commissioni | 5% su deal originati e chiusi dal fractional | 3% su ordini del distributore, 1% su riordini |

---

## 3. I 5 moduli da costruire

---

### MODULO 1 — Origini e canali configurabili

**Problema:** Il CRM ha origini hardcoded (web, referral, evento, cold). Non copre il canale social.

**Soluzione generica:**

L'admin definisce una **lista di origini custom** con:

| Campo | Tipo | Esempio |
|-------|------|---------|
| Codice | stringa unica | `linkedin_dm` |
| Etichetta | stringa display | "LinkedIn - Messaggio diretto" |
| Canale padre | enum configurabile | Social, Diretto, Evento, Web, Referral |
| Icona | opzionale | icona LinkedIn, icona telefono, etc. |
| Attivo | boolean | sì/no |

**Regole di business:**
- Ogni contatto ha un'origine obbligatoria alla creazione
- L'origine è filtrabile in pipeline, analytics e export
- Il "canale padre" permette analytics aggregate (tutti i social, tutti gli eventi)
- L'admin può aggiungere, rinominare, disattivare origini — mai cancellare (integrità dati storici)

**Configurazione Nexa Data:** linkedin_organico, linkedin_dm, linkedin_inmail, linkedin_evento, linkedin_ads, linkedin_referral, web, referral, evento, cold

---

### MODULO 2 — Attività e pre-funnel configurabili

**Problema:** Le attività sono fisse (call, email, meeting, note, task). La pipeline parte dal "Nuovo Lead" senza pre-funnel.

**Soluzione generica — Attività:**

L'admin definisce **tipi di attività custom**:

| Campo | Tipo | Esempio |
|-------|------|---------|
| Codice | stringa unica | `social_dm` |
| Etichetta | stringa display | "Messaggio social diretto" |
| Categoria | enum configurabile | Social, Telefono, Email, Presenza, Interno |
| Campi aggiuntivi | schema custom | URL post, numero partecipanti, durata |
| Conta come "ultimo contatto" | boolean | sì → aggiorna data ultimo contatto del lead |

**Soluzione generica — Pre-funnel:**

Pipeline estesa con **stadi pre-funnel opzionali**, attivabili dall'admin:

```
[Pre-funnel: stadi configurabili] → [Pipeline classica: stadi configurabili]
```

Ogni stadio (pre-funnel o pipeline) ha:

| Campo | Tipo |
|-------|------|
| Nome | stringa |
| Ordine | intero |
| Probabilità | 0-100% |
| Tipo | pre-funnel / pipeline / chiuso-vinto / chiuso-perso |
| Colore | hex |
| Regole transizione | da quali stadi si può arrivare |

L'admin decide quanti stadi avere, come chiamarli e quali regole di transizione applicare.

---

### MODULO 3 — Ruoli, permessi e collaboratori esterni

**Problema:** I ruoli sono fissi (Owner, Admin, Commerciale, Viewer). Non esiste il concetto di collaboratore esterno con accesso limitato e scadenza.

**Soluzione generica:**

L'admin definisce **ruoli custom** con matrice permessi granulare:

| Permesso | Granularità |
|----------|-------------|
| Contatti | Crea / Leggi tutti / Leggi solo assegnati / Modifica / Elimina |
| Deal | Crea / Leggi tutti / Leggi solo assegnati / Modifica stage / Chiudi |
| Ordini | Leggi / Crea / Conferma |
| Email/Messaggi | Invia a tutti / Invia solo a propri contatti / Solo template approvati |
| Analytics | Dashboard completa / Solo propria / Nessuna |
| Export | Tutto / Solo assegnati (max N/mese) / Bloccato |
| Configurazione | Sì / No |
| Gestione utenti | Sì / No |

Ogni utente ha inoltre:

| Campo | Tipo | Scopo |
|-------|------|-------|
| Tipo | interno / esterno | Distingue dipendenti da collaboratori |
| Data scadenza accesso | data | Auto-disable dopo scadenza contratto |
| Canale di default | riferimento a origine | Contatti creati da lui hanno questa origine di default |
| Prodotto di default | riferimento a prodotto | Deal creati da lui sono associati a questo prodotto |
| Modello compenso | riferimento a regola | Per calcolo automatico commissioni |

**Sicurezza obbligatoria per esterni:**
- Audit trail immutabile (ogni azione loggatà con user, timestamp, campo, vecchio/nuovo valore)
- Export bloccato o limitato (configurabile per ruolo)
- Revoca accesso mantiene storico (disable login, keep history)
- Segregazione dati row-level (vede solo contatti/deal assegnati)

---

### MODULO 4 — Catalogo prodotti/servizi

**Problema:** Il CRM ragiona per tipo deal (T&M, fixed, spot, hardware). Non ha il concetto di prodotto.

**Soluzione generica:**

Nuova entità **Prodotto/Servizio** configurabile:

| Campo | Tipo | Obbligatorio |
|-------|------|-------------|
| Nome | stringa | Sì |
| Codice | stringa unica | Sì |
| Categoria | enum custom dall'admin | Sì |
| Modello pricing | enum: subscription, one-time, T&M, mixed | Sì |
| Prezzo base | numero | No |
| Unità | mese, giorno, licenza, pezzo | No |
| Margine target % | numero | No |
| Attivo | boolean | Sì |
| Campi custom | schema estendibile | No |

**Relazione con deal:**
- Ogni deal può essere associato a 1 o più prodotti
- Il tipo deal si estende con nuovi modelli: `subscription` (canone x mesi), `mixed` (setup + canone)
- La pipeline è filtrabile per prodotto
- Le analytics sono aggregabili per prodotto

**Categorie di esempio (configurabili):**
- SaaS, Consulenza, Hardware, Managed Service, Formazione, Licenza...
- L'admin aggiunge le proprie

---

### MODULO 5 — Analytics configurabili e compensi

**Problema:** Le analytics sono fisse (pipeline pesata, win rate, email stats). Mancano KPI social, per canale, per collaboratore, per prodotto.

**Soluzione generica — Dashboard componibili:**

L'admin compone la dashboard scegliendo da un catalogo di **widget KPI**:

| Widget | Configurazione |
|--------|---------------|
| Funnel conversione | Scegli gli stadi da visualizzare, filtra per canale/prodotto/utente |
| Pipeline pesata | Filtra per prodotto, canale, utente, periodo |
| Win rate | Per canale, prodotto, utente o combinazione |
| Scorecard utente | Seleziona KPI da mostrare (messaggi, reply rate, meeting, pipeline, deal) |
| Channel mix | Confronto canali su revenue, volume, conversion |
| Costo per lead/deal | Inserisci costo fisso del collaboratore, calcolo automatico |
| ROI collaboratore | (Valore deal chiusi attribuiti) / (costo collaboratore nel periodo) |
| Top contenuti | Contenuti con più lead generati (richiede attribution) |
| Tempo medio a deal | Da prima interazione a deal chiuso, per canale |

Ogni widget è filtrabile per: periodo, canale, prodotto, utente, stadio, origine.

**Soluzione generica — Modello compensi:**

L'admin definisce **regole di compenso** per ruolo/utente:

| Campo regola | Tipo |
|-------------|------|
| Nome regola | stringa ("Commissione fractional LinkedIn") |
| Applica a | ruolo o utente specifico |
| Trigger | deal chiuso / deal originato / deal originato E chiuso |
| Base calcolo | valore deal / margine deal / importo fisso |
| Percentuale o importo | numero |
| Condizioni | solo se canale = X, solo se prodotto = Y, solo se valore > Z |

Il sistema calcola automaticamente il compenso e genera report mensile/trimestrale.

---

## 4. Matrice di priorità (per lo sviluppo)

| Modulo | Impatto | Effort | Sprint | Priorità |
|--------|---------|--------|--------|----------|
| M1 — Origini configurabili | Alto | Basso | Sprint 1 | **P1** |
| M2 — Attività e pre-funnel | Alto | Medio | Sprint 1-2 | **P1** |
| M3 — Ruoli e collaboratori esterni | Alto | Alto | Sprint 1-2 | **P1** |
| M4 — Catalogo prodotti | Alto | Medio | Sprint 2-3 | **P1** |
| M5 — Analytics e compensi | Alto | Alto | Sprint 3-4 | **P2** |

---

## 5. Anti-scope (cosa NON costruire)

| Escluso | Motivo |
|---------|--------|
| ML/NLP (sentiment, prediction) | PMI non ha dati né data scientist |
| Social listening enterprise | Costo e complessità sproporzionati |
| Sync real-time con LinkedIn | API non lo permettono, sync on-demand è sufficiente |
| Multi-touch attribution complessa | Serve first-touch semplice, il resto è over-engineering per PMI |
| Scraping social | Violazione ToS, rischio ban account |
| Competitor tracking automatico | API social non lo espongono |
| Video recording in-app | Esistono tool dedicati (Loom), link esterno è sufficiente |
| Sync bidirezionale con altri CRM | Fuori scope, ogni PMI sceglie un CRM |

---

## 6. Configurazione di esempio: Nexa Data

Per validare che l'architettura regge, ecco come Nexa Data configurerebbe il sistema:

**Origini:** linkedin_organico, linkedin_dm, linkedin_inmail, web, referral, evento
**Attività social:** social_connection, social_dm, social_engagement, social_content
**Pre-funnel:** Profilo identificato → Connesso → In conversazione → Interesse mostrato
**Prodotti:** elevia (SaaS/subscription), Consulenza AI (T&M), Assessment (fixed)
**Ruolo fractional:** Accesso solo contatti propri, solo template approvati, export bloccato, scadenza 6 mesi
**Sequenze:** "LinkedIn → Demo elevia → Proposta" con 7 step multi-canale
**KPI dashboard:** Lead LinkedIn, Win rate elevia, ROI fractional, Channel mix, Top contenuti
**Commissioni:** 5% su deal originati dal fractional e chiusi, solo prodotto elevia, solo valore > 5.000 EUR

---

## 7. Configurazione di esempio: PMI manifatturiera

**Origini:** fiera_mecspe, fiera_bimu, linkedin_dm, sito_web, agente_zona, distributore
**Attività social:** social_dm, visita_stabilimento, demo_macchina, invio_campione
**Pre-funnel:** Contatto fiera → Campione inviato → Feedback ricevuto → Interesse confermato
**Prodotti:** Linea CNC Alpha (hardware), Ricambi (spot), Manutenzione programmata (subscription)
**Ruolo agente:** Accesso solo contatti zona Nord-Est, export max 50/mese, scadenza annuale
**Sequenze:** "Fiera → Campione → Preventivo → Ordine" con 5 step email
**KPI dashboard:** Lead per fiera, Conversion rate ricambi, Fatturato agente, Tempo medio a ordine
**Commissioni:** 3% su ordini originati dall'agente, 1% su riordini entro 12 mesi

---

## 8. Note metodologiche

Questo documento nasce da un processo strutturato:

- **Guida CRM AgentFlow** — analisi dello stato attuale del sistema
- **Gap Analysis v1** — 8 gap specifici per Nexa Data/elevia
- **Brainstorming strutturato** — 85 idee (divergenza), analisi critica (sfida), 3 concept (sintesi)
- **Spec di prodotto v2 (questo documento)** — riscrittura come piattaforma configurabile generica

I documenti di lavoro sono nella cartella `brainstorm/` (divergenza.md, sfida.md, sintesi.md).

---

*Documento generato il 4 aprile 2026*
*AgentFlow — Modulo Social Selling per CRM B2B PMI*
