# Guida CRM — AgentFlow PMI

> Come usare il CRM integrato per gestire clienti, opportunita e comunicazioni commerciali.

---

## 1. Panoramica

Il CRM di AgentFlow e pensato per il **commerciale di una PMI italiana** che gestisce trattative B2B. Non e un CRM generico: e costruito per chi vende consulenza, progetti, servizi T&M e hardware.

**Cosa puoi fare:**
- Gestire contatti aziendali (clienti, lead, prospect)
- Tracciare le opportunita in una pipeline visuale Kanban
- Registrare attivita (chiamate, email, meeting, note)
- Inviare email con tracking (sai se il cliente ha letto)
- Registrare ordini cliente e confermarli
- Vedere analytics: pipeline pesata, win rate, conversione

---

## 2. Contatti

### Dove si trova
Sidebar → **Commerciale → Contatti** (`/crm/contatti`)

### Cos'e un contatto
Un contatto e un'azienda (non una persona fisica). Ogni contatto ha:

| Campo | Esempio | Note |
|-------|---------|------|
| Ragione sociale | Acme Italia SPA | Obbligatorio |
| Tipo | lead, prospect, cliente, ex_cliente | Indica lo stato della relazione |
| P.IVA | 12345678901 | Per fatturazione |
| Email | info@acme.it | Per comunicazioni |
| Telefono | +39 02 1234567 | |
| Settore | IT, manifattura, commercio... | Per segmentazione |
| Origine | web, referral, evento, cold | Come e arrivato il contatto |
| Assegnato a | Mario Rossi | Il commerciale responsabile |
| Consenso email | Si/No | GDPR: puo ricevere email marketing? |

### Come creare un contatto
1. Vai su **Contatti**
2. Clicca **"+ Nuovo Contatto"**
3. Compila almeno la ragione sociale
4. Il contatto viene creato come **lead** (puoi cambiare il tipo dopo)

### Tipi di contatto

| Tipo | Significato | Quando usarlo |
|------|------------|---------------|
| **Lead** | Contatto appena acquisito, non ancora qualificato | Primo contatto, form dal sito, evento |
| **Prospect** | Interessato, in fase di valutazione | Dopo la prima chiamata/meeting |
| **Cliente** | Ha comprato almeno una volta | Dopo il primo ordine confermato |
| **Ex cliente** | Non compra piu | Contratto terminato, perso |

### Ricerca e filtri
- Cerca per **nome**, **P.IVA** o **email** nella barra di ricerca
- I contatti sono ordinati alfabeticamente

---

## 3. Pipeline e Deal (Opportunita)

### Dove si trova
Sidebar → **Commerciale → Pipeline CRM** (`/crm`)

### Cos'e un deal
Un deal (opportunita) e una potenziale vendita. Ogni deal ha:

| Campo | Esempio | Note |
|-------|---------|------|
| Nome | Migrazione SAP per Acme SPA | Descrizione breve della trattativa |
| Cliente | Acme Italia SPA | Collegato a un contatto |
| Tipo | T&M, fixed, spot, hardware | Come viene venduto |
| Valore atteso | 45.000 EUR | Quanto vale se si chiude |
| Tariffa giornaliera | 500 EUR/gg | Solo per T&M |
| Giorni stimati | 90 gg | Solo per T&M |
| Tecnologia | SAP S/4HANA | Stack tecnologico |
| Probabilita | 50% | Si aggiorna automaticamente con lo stage |
| Assegnato a | Mario Rossi | Il commerciale responsabile |

### Tipi di deal

| Tipo | Come funziona | Calcolo valore |
|------|--------------|----------------|
| **T&M** (Time & Material) | Tariffa giornaliera x giorni | daily_rate x estimated_days |
| **Fixed** (Progetto fisso) | Importo a corpo | Inserisci il valore totale |
| **Spot** | Consulenza breve (3-150gg) | Inserisci il valore totale |
| **Hardware** | Vendita prodotti/licenze | Inserisci il valore totale |

### Come creare un deal
1. Dalla Pipeline, clicca **"+ Nuovo Deal"**
2. **Step 1**: Seleziona un cliente esistente, creane uno nuovo, o salta
3. **Step 2**: Compila nome, tipo, valore, tecnologia
4. Per T&M: inserisci tariffa e giorni → il valore si calcola automaticamente
5. Il deal viene creato nello stage "Nuovo Lead" con probabilita 10%

### La vista Kanban

La pipeline e una board Kanban con **6 colonne** (stadi):

```
| Nuovo Lead | Qualificato | Proposta Inviata | Ordine Ricevuto | Confermato | Perso |
|    10%     |     30%     |       50%        |       80%       |    100%    |   0%  |
```

Ogni colonna mostra:
- **Header**: nome stage, numero deal, valore totale
- **Card deal**: nome, cliente, tipo, valore, probabilita
- **Colore badge**: per tipo deal (T&M, Fixed, Spot, HW)

### Come spostare un deal
- **Desktop**: trascina la card da una colonna all'altra (drag-and-drop)
- **Mobile**: usa il dropdown sotto la card per cambiare stage
- La **probabilita si aggiorna automaticamente** quando sposti il deal

### Vista Tabella
Clicca **"Tabella"** per vedere i deal in formato lista con colonne ordinabili.

---

## 4. Stadi della Pipeline

| Stage | Probabilita | Significato | Cosa fare |
|-------|------------|-------------|-----------|
| **Nuovo Lead** | 10% | Contatto appena inserito | Qualifica: ha budget? ha bisogno? decide lui? |
| **Qualificato** | 30% | Il cliente ha un bisogno reale e budget | Prepara la proposta |
| **Proposta Inviata** | 50% | La proposta e stata consegnata | Follow-up, negoziazione |
| **Ordine Ricevuto** | 80% | Il cliente ha accettato (PO, email, firma) | Registra l'ordine, attendi conferma interna |
| **Confermato** | 100% | Ordine confermato, si parte | Crea la commessa nel sistema |
| **Perso** | 0% | Il cliente ha scelto un altro | Registra il motivo della perdita |

---

## 5. Ordini Cliente

Quando il cliente accetta la proposta, devi registrare l'ordine.

### Come registrare un ordine
1. Apri il dettaglio del deal
2. Nella sezione **"Ordine Cliente"**, clicca **"Registra ordine cliente"**
3. Seleziona il tipo di accettazione:

| Tipo ordine | Quando |
|------------|--------|
| **Purchase Order (PO)** | Il cliente manda un ordine formale con numero PO |
| **Conferma via Email** | Il cliente accetta via email |
| **Firma su documento Word** | Il cliente firma la proposta/contratto |
| **Accettazione da portale** | Il cliente accetta da un portale online |

4. Inserisci il **riferimento ordine** (numero PO, email reference, etc.)
5. Aggiungi eventuali **note**
6. Il deal passa automaticamente a "Ordine Ricevuto"

### Come confermare un ordine
1. Dopo aver verificato l'ordine internamente, clicca **"Conferma Ordine"**
2. Il deal passa a **"Confermato"** con probabilita 100%
3. Prossimo passo: crea la commessa nel sistema gestionale

---

## 6. Attivita

### Cosa sono
Le attivita sono le interazioni che hai con il cliente: chiamate, email, meeting, note.

### Tipi di attivita

| Tipo | Quando usarlo |
|------|--------------|
| **Call** | Hai fatto o ricevuto una telefonata |
| **Email** | Hai inviato o ricevuto un'email importante |
| **Meeting** | Riunione (di persona, Teams, Zoom) |
| **Note** | Annotazione libera (info apprese, decisioni) |
| **Task** | Attivita da fare (follow-up, preparare documento) |

### Come registrare un'attivita
Le attivita si registrano dal dettaglio deal o dalla API. Ogni attivita ha:
- Tipo (call, email, meeting, note, task)
- Oggetto (titolo breve)
- Descrizione (dettagli)
- Stato: pianificata → completata

Quando completi un'attivita su un contatto, la data di **ultimo contatto** si aggiorna automaticamente.

---

## 7. Email Marketing

### Dove si trova
Sidebar → **Commerciale → Email Template** / **Email Stats**

### Template email
I template sono modelli pre-compilati con variabili:

| Variabile | Viene sostituita con |
|-----------|---------------------|
| `{{nome}}` | Nome del contatto |
| `{{azienda}}` | Ragione sociale |
| `{{deal_name}}` | Nome dell'opportunita |
| `{{deal_value}}` | Valore del deal |
| `{{commerciale}}` | Nome del commerciale |

**Template predefiniti:**
- **Benvenuto** — prima email dopo il contatto
- **Follow-up proposta** — dopo aver inviato la proposta
- **Reminder scadenza** — proposta in scadenza

Puoi creare i tuoi template personalizzati.

### Inviare un'email
1. Dal dettaglio di un contatto o deal
2. Clicca **"Invia email"**
3. Seleziona un template (o scrivi da zero)
4. Anteprima con le variabili sostituite
5. Invia

### Email tracking
Dopo l'invio, puoi vedere:

| Stato | Icona | Significato |
|-------|-------|------------|
| Inviata | → | L'email e partita |
| Consegnata | ✓ | Il server del destinatario l'ha accettata |
| Letta | ✓✓ | Il destinatario ha aperto l'email |
| Cliccata | 🔗 | Ha cliccato un link nell'email |
| Rimbalzata | ✗ | L'indirizzo non esiste (bounce) |

### Analytics
Vai su **Email Stats** per vedere:
- **Open rate**: % di email aperte
- **Click rate**: % di email con click
- **Bounce rate**: % di email non consegnate
- **Top contatti**: chi apre di piu
- **Breakdown per template**: quale template funziona meglio
- **Email invalide**: contatti con email che rimbalzano

---

## 8. Sequenze Email Automatiche

### Cos'e una sequenza
Una sequenza e una serie di email che partono automaticamente, con regole:

**Esempio — "Follow-up dopo proposta":**
1. Giorno 0: Invia email "Proposta inviata"
2. Giorno 3: Se NON ha aperto → invia "Reminder: hai visto la proposta?"
3. Giorno 7: Se ha aperto → invia "Quando possiamo parlarne?"

### Trigger
Le sequenze partono quando:
- **Manuale**: le avvii tu su un contatto
- **Deal cambia stage**: quando sposti un deal a uno stage specifico (es. "Proposta Inviata")
- **Nuovo contatto**: quando crei un nuovo lead

### Condizioni sugli step

| Condizione | Significato |
|-----------|------------|
| Nessuna | Invia sempre |
| Se ha aperto | Invia solo se ha aperto l'email precedente |
| Se NON ha aperto | Invia solo se NON ha aperto |
| Se ha cliccato | Invia solo se ha cliccato un link |

---

## 9. Ruoli e Permessi

### Chi vede cosa

| Ruolo | Vede deal/contatti | Gestisce utenti | Invia email | Configura integrazioni |
|-------|-------------------|-----------------|-------------|----------------------|
| **Owner** | Tutti | Si | Si | Si |
| **Admin** | Tutti | Si | Si | Si |
| **Commerciale** | Solo i propri | No | Si (suoi contatti) | No |
| **Viewer** | Tutti (sola lettura) | No | No | No |

### Gestione utenti
Sidebar → **Sistema → Utenti** (`/impostazioni/utenti`)

L'owner puo:
- **Invitare** nuovi utenti (email + ruolo → password temporanea)
- **Cambiare ruolo** a un utente
- **Disattivare** un utente (non puo piu accedere)

---

## 10. Pipeline Analytics

Nella barra in alto della Pipeline vedi:

| KPI | Cosa mostra |
|-----|------------|
| **Pipeline pesata** | Somma di (valore deal x probabilita) — il valore realistico |
| **Vinti** | Numero deal confermati |
| **Persi** | Numero deal persi |
| **Win rate** | % deal vinti su totale chiusi |

### Come leggere la pipeline pesata
Se hai:
- Deal A: 50.000 EUR al 50% = 25.000 pesato
- Deal B: 20.000 EUR all'80% = 16.000 pesato
- **Pipeline pesata = 41.000 EUR** — e il valore che realisticamente chiuderai

---

## 11. Flusso quotidiano consigliato

### Mattina (5 minuti)
1. Apri **Pipeline CRM** → guarda le colonne
2. Ci sono deal fermi da troppo tempo? Spostali o registra un'attivita
3. Controlla **Email Stats** → qualcuno ha aperto la proposta ieri?

### Durante la giornata
4. Ricevi una chiamata → apri il deal → registra attivita "call"
5. Vuoi mandare la proposta → "Invia email" con template "Proposta"
6. Il cliente accetta → registra ordine → conferma

### Fine settimana
7. Rivedi il win rate e la pipeline pesata
8. Contatti non contattati da >30gg? Richiamali
9. Sequenze email: stanno funzionando? Controlla gli analytics

---

## 12. Glossario

| Termine | Significato |
|---------|------------|
| **Deal** | Un'opportunita di vendita in pipeline |
| **Lead** | Un contatto nuovo, non ancora qualificato |
| **Prospect** | Un contatto qualificato, con potenziale |
| **Stage** | Fase della pipeline (Nuovo Lead → Confermato) |
| **Pipeline pesata** | Valore realistico = somma(valore x probabilita) |
| **Win rate** | Percentuale di deal vinti su totale chiusi |
| **T&M** | Time & Material — vendita a tariffa giornaliera |
| **PO** | Purchase Order — ordine formale del cliente |
| **Bounce** | Email non consegnata (indirizzo invalido) |
| **Sequenza** | Serie di email automatiche con condizioni |
| **BYOK** | Bring Your Own Key — usa la tua API key |

---

_Guida generata: 2026-04-04_
_AgentFlow PMI — Controller aziendale AI per PMI italiane_
