# User Stories — Pivot 8: Frontend Completo + Integrazioni

> Riferimento: pagine frontend mancanti per backend Pivot 6+7
> Data: 2026-04-03

---

## Epic 1: Frontend Scadenzario (Alta)

### US-100: Pagina scadenzario con tab attivo/passivo
**Come** imprenditore
**Voglio** vedere tutte le scadenze in una pagina con tab attivo (crediti) e passivo (debiti)
**Per** gestire incassi e pagamenti in un unico punto

**AC-100.1**: Tab "Attivo" mostra scadenze tipo attivo con colonne: controparte, importo lordo/netto, scadenza, giorni residui, stato, colore
**AC-100.2**: Tab "Passivo" mostra scadenze tipo passivo
**AC-100.3**: Filtri per stato (aperto/pagato/insoluto/parziale), controparte, periodo
**AC-100.4**: Totali per stato visibili in header (da incassare, scaduto, incassato)
**AC-100.5**: Pulsante "Genera scadenze" per creare scadenze mancanti da fatture
**AC-100.6**: Pulsante "Chiudi" su ogni scadenza aperta → modale importo + data pagamento
**AC-100.7**: Pulsante "Insoluto" su scadenze attive scadute
**AC-100.8**: Badge "Anticipata" su scadenze con anticipo attivo

**SP**: 8 | **Priorita**: Must Have

---

### US-101: Cash flow previsionale da scadenzario
**Come** imprenditore
**Voglio** vedere il cash flow previsto per i prossimi 30/60/90 giorni
**Per** anticipare problemi di liquidita

**AC-101.1**: Toggle 30/60/90 giorni
**AC-101.2**: Card: saldo banca, incassi previsti, pagamenti previsti, saldo previsto
**AC-101.3**: Grafico a barre settimanale con saldo progressivo
**AC-101.4**: Alert se saldo scende sotto soglia configurabile
**AC-101.5**: Tab "Per banca" mostra cash flow separato per ogni conto

**SP**: 5 | **Priorita**: Must Have

---

## Epic 2: Frontend Email Marketing (Alta)

### US-102: Pagina gestione email template
**Come** commerciale
**Voglio** creare e modificare template email con variabili
**Per** personalizzare le comunicazioni senza riscrivere ogni volta

**AC-102.1**: Lista template con nome, categoria, stato (attivo/inattivo)
**AC-102.2**: Editor: nome, oggetto, corpo HTML (textarea), variabili disponibili
**AC-102.3**: Preview con dati campione prima del salvataggio
**AC-102.4**: Categorie filtrabili: welcome, followup, proposal, reminder, nurture
**AC-102.5**: Template default pre-caricati visibili

**SP**: 5 | **Priorita**: Must Have

---

### US-103: Invio email da dettaglio contatto/deal
**Come** commerciale
**Voglio** inviare un'email a un contatto direttamente dal suo profilo o dal deal
**Per** comunicare velocemente con tracking automatico

**AC-103.1**: Pulsante "Invia email" nel dettaglio contatto CRM
**AC-103.2**: Pulsante "Invia email" nel dettaglio deal CRM
**AC-103.3**: Modale: seleziona template, preview, modifica subject/body, invia
**AC-103.4**: Storico email inviate visibile nel dettaglio contatto (lista con status)
**AC-103.5**: Status email: inviata → consegnata → letta → cliccata (icone colorate)

**SP**: 5 | **Priorita**: Must Have

---

### US-104: Dashboard email analytics
**Come** direttore commerciale
**Voglio** vedere le statistiche email in una dashboard dedicata
**Per** capire l'efficacia delle comunicazioni

**AC-104.1**: Card KPI: totale inviate, open rate %, click rate %, bounce rate %
**AC-104.2**: Breakdown per template (tabella con sent/opened/clicked per template)
**AC-104.3**: Top 10 contatti che aprono/cliccano
**AC-104.4**: Lista contatti con email invalida (bounced)

**SP**: 3 | **Priorita**: Must Have

---

## Epic 3: Frontend Email Sequenze (Media)

### US-105: Pagina gestione sequenze email
**Come** commerciale
**Voglio** creare sequenze email automatiche con step e condizioni
**Per** automatizzare il follow-up senza intervento manuale

**AC-105.1**: Lista sequenze con nome, trigger, status (draft/active/paused), stats
**AC-105.2**: Creazione sequenza: nome, trigger event (manual, deal_stage_changed, contact_created)
**AC-105.3**: Aggiunta step: seleziona template, delay giorni/ore, condizione (none, if_opened, if_not_opened)
**AC-105.4**: Vista step come timeline verticale (step 1 → delay → step 2 → ...)
**AC-105.5**: Attivazione/pausa sequenza

**SP**: 5 | **Priorita**: Should Have

---

## Epic 4: Frontend Fidi e Anticipi (Bassa)

### US-106: Pagina configurazione fidi bancari
**Come** imprenditore
**Voglio** configurare i fidi anticipo per ogni banca
**Per** sapere quanto posso anticipare e a che costo

**AC-106.1**: Lista fidi con banca, plafond, utilizzato, disponibile, tasso
**AC-106.2**: Form creazione fido: seleziona banca, plafond, %, tasso, commissioni
**AC-106.3**: Barra visuale plafond utilizzato/disponibile

**SP**: 3 | **Priorita**: Could Have

---

### US-107: Anticipo fatture nell'scadenzario
**Come** imprenditore
**Voglio** anticipare una fattura dallo scadenzario attivo
**Per** ottenere liquidita immediata

**AC-107.1**: Pulsante "Anticipa" su scadenze attive non anticipate
**AC-107.2**: Modale confronto banche: importo anticipabile, commissione, interessi, costo totale per banca
**AC-107.3**: Conferma anticipo → badge "Anticipata" sulla scadenza
**AC-107.4**: Pulsante "Incassa anticipo" quando il cliente paga

**SP**: 5 | **Priorita**: Could Have

---

## Epic 5: Account Brevo + E2E (Media)

### US-108: Configurazione Brevo in impostazioni
**Come** admin
**Voglio** configurare la connessione Brevo dalle impostazioni
**Per** attivare l'email marketing senza toccare il codice

**AC-108.1**: Sezione "Email Marketing" in pagina Impostazioni
**AC-108.2**: Campi: API Key (masked), sender email, sender name
**AC-108.3**: Pulsante "Test connessione" → invia email di test
**AC-108.4**: Status: connesso/non configurato

**SP**: 3 | **Priorita**: Should Have

---

## Riepilogo

| Epic | Stories | SP | Priorita |
|------|---------|-----|----------|
| 1. Scadenzario FE | US-100, US-101 | 13 | Alta |
| 2. Email Marketing FE | US-102, US-103, US-104 | 13 | Alta |
| 3. Email Sequenze FE | US-105 | 5 | Media |
| 4. Fidi + Anticipi FE | US-106, US-107 | 8 | Bassa |
| 5. Config Brevo | US-108 | 3 | Media |
| **TOTALE** | **9 stories** | **42 SP** | |

## Sprint Plan

| Sprint | Stories | SP | Focus |
|--------|---------|-----|-------|
| Sprint 28 | US-100, US-101 | 13 | Scadenzario FE + Cash Flow |
| Sprint 29 | US-102, US-103, US-104 | 13 | Email template + invio + analytics |
| Sprint 30 | US-105, US-108 | 8 | Sequenze FE + Config Brevo |
| Sprint 31 | US-106, US-107 | 8 | Fidi + Anticipi FE |
