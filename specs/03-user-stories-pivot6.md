# User Stories — Pivot 6: IVA, Scadenzari, Cash Flow, Anticipi

> Riferimento: brainstorm/11-iva-scadenzari-anticipi.md
> Data: 2026-04-01

---

## Epic 1: Scorporo IVA — Ricavi e Costi al Netto

### US-70: Dashboard mostra ricavi e costi al netto IVA
**Come** imprenditore
**Voglio** vedere ricavi e costi al netto dell'IVA nella Dashboard
**Per** avere una visione reale del margine senza il transito IVA

**AC-70.1**: Il widget "Ricavi Totali" mostra la somma di `importo_netto` delle fatture attive (non `importo_totale`)
**AC-70.2**: Il widget "Costi Totali" mostra la somma di `importo_netto` delle fatture passive
**AC-70.3**: Il widget "Margine (EBITDA)" usa ricavi netti - costi netti
**AC-70.4**: Il grafico mensile mostra importi netti per mese
**AC-70.5**: Esiste un widget "IVA Netta" che mostra IVA debito - IVA credito = IVA da versare

**SP**: 3 | **Priorita**: Must Have

---

### US-71: Budget consuntivo usa importi netti
**Come** imprenditore
**Voglio** che il confronto budget vs consuntivo usi importi al netto IVA
**Per** confrontare dati coerenti tra previsioni e reale

**AC-71.1**: Il consuntivo delle fatture attive usa `importo_netto` per la voce "ricavi"
**AC-71.2**: Il consuntivo delle fatture passive usa `importo_netto` per le voci costo
**AC-71.3**: Lo scostamento budget/consuntivo e calcolato su importi netti

**SP**: 2 | **Priorita**: Must Have

---

## Epic 2: Scadenzario Attivo e Passivo

### US-72: Generazione automatica scadenze da fatture
**Come** sistema
**Quando** viene creata o importata una fattura
**Allora** crea automaticamente una riga nello scadenzario

**AC-72.1**: Fattura attiva → scadenza tipo "attivo" (credito da incassare) con data = data_fattura + giorni_pagamento
**AC-72.2**: Fattura passiva → scadenza tipo "passivo" (debito da pagare) con data = data_fattura + giorni_pagamento
**AC-72.3**: L'importo scadenza include: lordo, netto, IVA separati
**AC-72.4**: La banca di appoggio e l'IBAN indicato sulla fattura
**AC-72.5**: Se giorni_pagamento non specificato, default 30gg

**SP**: 5 | **Priorita**: Must Have

---

### US-73: Visualizzazione scadenzario attivo (crediti)
**Come** imprenditore
**Voglio** vedere tutte le fatture da incassare con le date di scadenza
**Per** sapere quanto denaro attendo e quando

**AC-73.1**: Lista scadenze attive ordinata per data scadenza
**AC-73.2**: Colonne: controparte, numero fattura, importo lordo, importo netto, scadenza, giorni residui, stato
**AC-73.3**: Stati possibili: da_incassare, parziale, incassato, insoluto, anticipata
**AC-73.4**: Colore rosso se scaduta, giallo se scade entro 7gg, verde se > 7gg
**AC-73.5**: Filtri per: stato, periodo, controparte
**AC-73.6**: Totale importi per stato (da incassare, scaduto, incassato)

**SP**: 5 | **Priorita**: Must Have

---

### US-74: Visualizzazione scadenzario passivo (debiti)
**Come** imprenditore
**Voglio** vedere tutti i pagamenti in scadenza
**Per** pianificare le uscite di cassa

**AC-74.1**: Lista scadenze passive da: fatture passive, stipendi, rate mutui, F24, contratti ricorrenti
**AC-74.2**: Colonne: controparte, tipo, importo, scadenza, giorni residui, stato
**AC-74.3**: Stati: da_pagare, pagato, scaduto
**AC-74.4**: Stessi colori e filtri di US-73
**AC-74.5**: Totale importi per stato

**SP**: 5 | **Priorita**: Must Have

---

### US-75: Chiusura automatica scadenze da movimenti banca
**Come** sistema
**Quando** un movimento bancario viene riconciliato con una fattura
**Allora** la scadenza corrispondente viene chiusa automaticamente

**AC-75.1**: Riconciliazione fattura attiva → scadenza passa a "incassato" con data_pagamento
**AC-75.2**: Riconciliazione fattura passiva → scadenza passa a "pagato" con data_pagamento
**AC-75.3**: Se importo parziale → stato "parziale" con importo residuo
**AC-75.4**: Se la scadenza era anticipata → scarica l'anticipo (libera plafond)

**SP**: 5 | **Priorita**: Should Have

---

### US-76: Gestione insoluti
**Come** imprenditore
**Voglio** segnare una fattura come insoluta quando il cliente non paga
**Per** tracciare i crediti problematici

**AC-76.1**: Pulsante "Segna insoluto" sulle scadenze attive scadute
**AC-76.2**: Se la fattura era anticipata: sistema avvisa che la banca riaddebitera l'anticipo
**AC-76.3**: Lo scadenzario mostra l'insoluto con badge rosso
**AC-76.4**: L'insoluto resta nello scadenzario finche non viene incassato o stornato

**SP**: 3 | **Priorita**: Should Have

---

## Epic 3: Cash Flow Previsionale

### US-77: Cash flow da scadenzario
**Come** imprenditore
**Voglio** vedere il cash flow previsto per i prossimi 30/60/90 giorni
**Per** sapere se avro liquidita sufficiente

**AC-77.1**: Calcolo: saldo banca attuale + incassi previsti (scadenzario attivo) - pagamenti previsti (scadenzario passivo)
**AC-77.2**: Vista 30/60/90 giorni selezionabile
**AC-77.3**: Grafico a barre giornaliere o settimanali con saldo progressivo
**AC-77.4**: Alert se il saldo previsto scende sotto una soglia (configurabile)
**AC-77.5**: Considera anche le scadenze delle fatture anticipate (restituzione alla banca)

**SP**: 8 | **Priorita**: Must Have

---

### US-78: Cash flow per banca
**Come** imprenditore
**Voglio** vedere il cash flow previsto per ogni conto bancario separatamente
**Per** sapere quale conto rischia di andare in rosso

**AC-78.1**: Selezione banca/conto nel filtro
**AC-78.2**: Ogni fattura ha una banca di appoggio → gli incassi vanno su quel conto
**AC-78.3**: I pagamenti vanno sul conto da cui si paga (da definire)
**AC-78.4**: Widget "Saldo previsto per banca" nella dashboard

**SP**: 5 | **Priorita**: Should Have

---

## Epic 4: Fidi Bancari e Anticipo Fatture

### US-79: Configurazione fido anticipo fatture per banca
**Come** imprenditore
**Voglio** configurare le condizioni del fido anticipo per ogni banca
**Per** avere sempre chiaro quanto posso anticipare e a che costo

**AC-79.1**: CRUD fido bancario con campi: banca (FK BankAccount), tipo (anticipo_fatture/sbf/riba), plafond, % anticipo, tasso interesse annuo, commissione presentazione %, commissione incasso EUR, commissione insoluto EUR, giorni max
**AC-79.2**: Visualizzazione: plafond totale, utilizzato (calcolato da anticipi attivi), disponibile
**AC-79.3**: La banca del fido e la stessa banca di appoggio delle fatture
**AC-79.4**: Possibilita di avere piu fidi su banche diverse

**SP**: 5 | **Priorita**: Should Have

---

### US-80: Anticipo fattura — Presentazione
**Come** imprenditore
**Voglio** anticipare una fattura attiva presso la banca di appoggio
**Per** avere liquidita immediata senza aspettare il pagamento del cliente

**AC-80.1**: Dallo scadenzario attivo, pulsante "Anticipa" su fatture non ancora anticipate
**AC-80.2**: Il sistema mostra: importo anticipabile (% del lordo), commissione, interessi stimati, costo totale
**AC-80.3**: L'anticipo avviene sulla stessa banca di appoggio della fattura (stesso IBAN)
**AC-80.4**: Verifica che il plafond disponibile sia sufficiente
**AC-80.5**: Conferma → anticipo attivo, plafond aggiornato
**AC-80.6**: La scadenza nello scadenzario mostra badge "anticipata"
**AC-80.7**: L'anticipo e opzionale e puo essere richiesto anche dopo la creazione della fattura

**SP**: 8 | **Priorita**: Should Have

---

### US-81: Anticipo fattura — Incasso e scarico
**Come** sistema
**Quando** il cliente paga una fattura anticipata
**Allora** l'anticipo viene scaricato e il plafond si libera

**AC-81.1**: Incasso fattura anticipata → anticipo passa a stato "incassato"
**AC-81.2**: Plafond liberato dell'importo anticipato → disponibilita aumenta
**AC-81.3**: Interessi effettivi calcolati sui giorni reali (data_presentazione → data_incasso)
**AC-81.4**: Interessi + commissioni registrati come costo "oneri_finanziari" nel budget
**AC-81.5**: Il plafond liberato e subito riutilizzabile per anticipare altre fatture

**SP**: 5 | **Priorita**: Should Have

---

### US-82: Anticipo fattura — Insoluto
**Come** sistema
**Quando** una fattura anticipata non viene pagata alla scadenza
**Allora** la banca riaddebita l'anticipo

**AC-82.1**: Se la fattura e insoluta → anticipo passa a stato "insoluto"
**AC-82.2**: Riaddebito: importo anticipato viene sottratto dal conto
**AC-82.3**: Commissione insoluto addebitata
**AC-82.4**: Il plafond NON si libera finche l'insoluto non e risolto
**AC-82.5**: La fattura torna nello scadenzario come "insoluta"

**SP**: 3 | **Priorita**: Should Have

---

### US-83: Confronto costi anticipo tra banche
**Come** imprenditore
**Voglio** confrontare il costo dell'anticipo tra le mie banche
**Per** scegliere dove anticipare una fattura al minor costo

**AC-83.1**: Quando seleziono una fattura da anticipare, il sistema mostra una tabella confronto
**AC-83.2**: Per ogni banca con fido disponibile: importo anticipabile, commissione, interessi stimati, costo totale, costo % annuo
**AC-83.3**: Evidenzia la banca piu conveniente
**AC-83.4**: Mostra disponibilita residua del plafond per ogni banca

**SP**: 3 | **Priorita**: Could Have

---

## Epic 5: Modello Dati

### US-84: Modello Scadenza (DB)
**Come** sviluppatore
**Devo** creare il modello Scadenza nel database
**Per** supportare scadenzario attivo/passivo

**Campi**: id, tenant_id, tipo (attivo/passivo), source_type (fattura/stipendio/f24/mutuo/contratto), source_id, controparte, importo_lordo, importo_netto, importo_iva, data_scadenza, data_pagamento, stato (aperto/pagato/insoluto/parziale), banca_appoggio_id (FK BankAccount), anticipata (bool), anticipo_id (FK InvoiceAdvance), created_at, updated_at

**SP**: 3 | **Priorita**: Must Have

---

### US-85: Modello BankFacility (DB)
**Come** sviluppatore
**Devo** creare il modello BankFacility per i fidi bancari
**Per** gestire le condizioni anticipo per ogni banca

**Campi**: id, tenant_id, bank_account_id (FK), tipo, plafond, percentuale_anticipo, tasso_interesse_annuo, commissione_presentazione_pct, commissione_incasso, commissione_insoluto, giorni_max, attivo (bool), created_at

**SP**: 2 | **Priorita**: Should Have

---

### US-86: Modello InvoiceAdvance (DB)
**Come** sviluppatore
**Devo** creare il modello InvoiceAdvance per i singoli anticipi
**Per** tracciare ogni anticipo fattura con i relativi costi

**Campi**: id, tenant_id, facility_id (FK BankFacility), invoice_id (FK Invoice), importo_fattura, importo_anticipato, commissione, interessi_stimati, interessi_effettivi, data_presentazione, data_scadenza_prevista, data_chiusura, stato (attivo/incassato/insoluto), created_at

**SP**: 2 | **Priorita**: Should Have

---

## Riepilogo

| Epic | Stories | SP Totali | Priorita |
|------|---------|-----------|----------|
| 1. Scorporo IVA | US-70, US-71 | 5 | Must Have |
| 2. Scadenzario | US-72, US-73, US-74, US-75, US-76 | 23 | Must/Should |
| 3. Cash Flow | US-77, US-78 | 13 | Must/Should |
| 4. Anticipi | US-79, US-80, US-81, US-82, US-83 | 24 | Should/Could |
| 5. Modelli DB | US-84, US-85, US-86 | 7 | Must/Should |
| **TOTALE** | **17 stories** | **72 SP** | |

## Sprint suggeriti

| Sprint | Stories | SP | Focus |
|--------|---------|-----|-------|
| Sprint 17 | US-70, US-71, US-84 | 10 | IVA netto + modello Scadenza |
| Sprint 18 | US-72, US-73, US-74 | 15 | Scadenzario attivo/passivo |
| Sprint 19 | US-75, US-76, US-77 | 16 | Chiusura scadenze + Cash flow |
| Sprint 20 | US-78, US-85, US-79 | 12 | Cash flow per banca + Fidi |
| Sprint 21 | US-86, US-80, US-81, US-82 | 18 | Anticipo fatture completo |
| Sprint 22 | US-83 | 3 | Confronto costi anticipo |
