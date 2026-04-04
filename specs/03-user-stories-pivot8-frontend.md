# User Stories — Pivot 8: Frontend Completo + Integrazioni

> Riferimento: pagine frontend mancanti per backend Pivot 6+7
> Data: 2026-04-03
> Aggiornamento: 2026-04-04

---

## Epic 1: Frontend Scadenzario — COMPLETATO

### US-100: Pagina scadenzario con tab attivo/passivo ✅
Implementata con tab Attivo/Passivo/Cash Flow, filtri, chiusura, insoluti.

### US-101: Cash flow previsionale da scadenzario ✅
Toggle 30/60/90gg, card KPI, breakdown settimanale, cash flow per banca.

---

## Epic 2: Frontend Email Marketing — COMPLETATO + AI

### US-102: Pagina gestione email template ✅
Lista template, filtro categorie, preview. **Aggiunto**: creazione template con AI (generazione da prompt naturale) + editor visuale GrapesJS con MJML.

### US-103: Invio email da dettaglio contatto/deal ⚠️ PARZIALE
SendEmailModal creato ma non ancora collegato al dettaglio deal/contatto. Manca il pulsante "Invia email" nelle pagine CRM.

### US-104: Dashboard email analytics ✅
KPI (open/click/bounce rate), breakdown per template, top contatti, email invalide.

---

## Epic 3: Frontend Email Sequenze — COMPLETATO BASE

### US-105: Pagina gestione sequenze email ✅
Lista sequenze, creazione con trigger. **Manca**: vista timeline step, aggiunta step da UI, attivazione/pausa.

---

## Epic 4: Frontend Fidi e Anticipi — COMPLETATO BASE

### US-106: Pagina configurazione fidi bancari ✅
Lista fidi con barra plafond, form creazione.

### US-107: Anticipo fatture nell'scadenzario ⚠️ NON IMPLEMENTATO
Mancano: pulsante "Anticipa" nello scadenzario, modale confronto banche, badge "Anticipata".

---

## Epic 5: Config Brevo — COMPLETATO

### US-108: Configurazione in impostazioni ✅
Pagina Integrazioni con settings encrypted, email quota, LLM quota.

---

## NUOVE STORIES (aggiunte 2026-04-04)

### US-117: AI Email Generator ✅ COMPLETATO
**Come** commerciale
**Voglio** descrivere l'email in linguaggio naturale e l'AI la genera
**Per** creare email professionali senza scrivere HTML

**AC-117.1**: Campo prompt "Descrivi l'email" con selezione tono ✅
**AC-117.2**: Bottone "Genera con AI" chiama OpenAI gpt-4o-mini ✅
**AC-117.3**: Preview reale con HTML originale (stili preservati) ✅
**AC-117.4**: Editor blocchi GrapesJS con MJML per modifiche strutturali ✅
**AC-117.5**: Modifica iterativa via chat AI ("Aggiungi un paragrafo su...") ✅
**AC-117.6**: Toolbar variabili {{nome}}, {{azienda}}, etc. ✅
**AC-117.7**: Salva come template con nome e categoria ✅
**AC-117.8**: Sanitizzazione HTML (no script, no event handlers) ✅

**SP**: 8 | Completata

---

### US-118: Landing page pubblica ✅ COMPLETATO
**Come** visitatore
**Voglio** capire cosa fa AgentFlow in 5 secondi e registrarmi
**Per** provare il prodotto

**AC-118.1**: Landing su / con hero "Sai sempre come sta la tua azienda" ✅
**AC-118.2**: 4 card problema → soluzione ✅
**AC-118.3**: Trust badges (Automatico, Sicuro, Italiano) ✅
**AC-118.4**: CTA "Provalo gratis" → /register ✅
**AC-118.5**: Footer Nexa Data ✅

**SP**: 3 | Completata

---

### US-119: Registrazione con creazione tenant ✅ COMPLETATO
**Come** nuovo utente
**Voglio** registrarmi e creare la mia azienda in un unico flusso
**Per** iniziare subito senza configurazioni manuali

**AC-119.1**: Step 1: nome, email, password ✅
**AC-119.2**: Step 2: ragione sociale, tipo azienda, P.IVA, regime fiscale ✅
**AC-119.3**: Creazione automatica Tenant + User owner ✅
**AC-119.4**: Registrazione senza azienda (completa dopo) ✅

**SP**: 3 | Completata

---

### US-120: Pagina nuovo deal CRM ✅ COMPLETATO
**Come** commerciale
**Voglio** creare un nuovo deal dalla pipeline
**Per** tracciare nuove opportunita

**AC-120.1**: Step 1: seleziona/crea cliente con ricerca ✅
**AC-120.2**: Step 2: nome deal, tipo (T&M/fixed/spot/hardware), valore, tariffa, tecnologia ✅
**AC-120.3**: Auto-calcolo valore per T&M (tariffa x giorni) ✅
**AC-120.4**: Skip cliente opzionale ✅

**SP**: 5 | Completata

---

### US-121: Reset password con email Brevo ✅ COMPLETATO
**Come** utente
**Voglio** recuperare la password via email
**Per** rientrare nel mio account

**AC-121.1**: /forgot-password → messaggio vago (anti-enumeration) ✅
**AC-121.2**: Email da noreply@iridia.tech con link reset ✅
**AC-121.3**: /reset-password?token=xxx → nuova password ✅
**AC-121.4**: Login con messaggio generico su errore ✅

**SP**: 3 | Completata

---

## Riepilogo aggiornato

| Story | SP | Status |
|-------|-----|--------|
| US-100 Scadenzario | 8 | ✅ Completata |
| US-101 Cash Flow | 5 | ✅ Completata |
| US-102 Email Templates + AI | 5 | ✅ Completata |
| US-103 Invio da deal/contatto | 5 | ⚠️ Parziale |
| US-104 Email Analytics | 3 | ✅ Completata |
| US-105 Sequenze | 5 | ✅ Base |
| US-106 Fidi Bancari | 3 | ✅ Completata |
| US-107 Anticipo da scadenzario | 5 | ❌ Non implementata |
| US-108 Config Integrazioni | 3 | ✅ Completata |
| US-117 AI Email Generator | 8 | ✅ Completata |
| US-118 Landing Page | 3 | ✅ Completata |
| US-119 Registrazione + Tenant | 3 | ✅ Completata |
| US-120 Nuovo Deal CRM | 5 | ✅ Completata |
| US-121 Reset Password | 3 | ✅ Completata |
| **TOTALE** | **64** | **12/14 completate** |

## Cosa manca

| Story | Cosa serve | Effort |
|-------|-----------|--------|
| **US-103** | Collegare SendEmailModal al dettaglio deal e contatto CRM | 1 ora |
| **US-107** | Pulsante "Anticipa" nello scadenzario + modale confronto banche | 3 ore |
| US-105 | Vista timeline step, aggiunta step da UI | 2 ore |
