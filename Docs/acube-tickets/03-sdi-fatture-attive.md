# Ticket 03 — Fatturazione SDI: emissione fatture attive

**Area:** e-Invoicing Italia / SDI
**Priorità:** P0
**Oggetto:** [NexaData] Fatturazione elettronica SDI — emissione fatture attive via API

---

## Contesto

AgentFlow PMI integra A-Cube per la gestione fiscale dei clienti. Abbiamo già un adapter stub (`ACubeSDIAdapter`) nel codice, pronto per essere cablato con le vostre API SDI in produzione.

Il contratto firmato il 10/04/2026 copre **AISP + Scarico Massivo**. Vorremmo chiarire il perimetro commerciale/tecnico per la **fatturazione SDI in uscita** (emissione fatture attive).

---

## Richieste

### 1. Stato commerciale

Il servizio di **emissione fatture SDI** è:

- **a)** già attivo nel contratto esistente? (non lo vediamo esplicitamente menzionato nell'offerta firmata)
- **b)** un contratto separato già presente da un'attivazione precedente?
- **c)** un servizio da attivare con offerta/addendum aggiuntivo?

Ci potete confermare lo stato? In caso **(c)**, potete inviarci offerta commerciale con:
- Costo setup
- Canone annuo
- Pricing per volume (fatture/mese)

### 2. Perimetro servizio

Il servizio copre:
- ✅ Trasmissione fattura XML FatturaPA a SDI
- ✅ Ricezione notifiche SDI (RC, NS, MC, NE, EC, DT)
- ✅ Firma digitale qualificata (inclusa o separata?)
- ✅ Conservazione digitale a norma (inclusa?)
- ✅ Supporto TD01-TD28 (inclusi reverse charge, autofatture)

### 3. Endpoint principali

Dove si trova la documentazione dettagliata per:
- `POST` trasmissione fattura (payload XML o JSON?)
- `GET` stato trasmissione (notifiche SDI)
- Webhook notifiche SDI real-time

URL documentazione: https://docs.acubeapi.com/documentation/italy/gov-it/invoices/composing-invoice è quello corretto?

### 4. Sandbox

Lo sandbox è disponibile? Ambiente di test per:
- Inviare fatture con P.IVA test
- Simulare esiti SDI (accettato / scartato)

### 5. Flusso operativo

Modello di invio: **síncrono** (call API → aspetta risposta SDI) o **asíncrono** (call API → risposta immediata con ID → webhook stato)?

### 6. Firma digitale

Se non inclusa, quale modalità raccomandate:
- Firma automatica server-side con certificato condiviso?
- Firma client-side pre-upload?
- Firma remota OTP?

### 7. Conservazione digitale

Separata o inclusa? Se separata, prezzo?
Durata legale (10 anni) rispettata a norma?

### 8. Relazione con Scarico Massivo

Se emettiamo fatture attive via A-Cube SDI, vengono poi automaticamente visibili anche nello scarico massivo dal cassetto fiscale? O c'è doppio contatore?

### 9. Notifica eventi SDI

Webhook disponibili per:
- `RC` (Ricevuta Consegna)
- `NS` (Notifica Scarto)
- `MC` (Mancata Consegna)
- `NE` (Notifica Esito — accettazione/rifiuto cliente PA)
- `EC` (Esito Cessionario)
- `DT` (Decorrenza Termini)

### 10. Limiti contrattuali

Esiste un limite massimo fatture/anno incluso nel canone base? Pricing per excedente?

---

## Riferimenti

- Contratto firmato 10/04/2026 (non menziona SDI emissione esplicitamente)
- Adapter AgentFlow esistente: `api/adapters/acube.py` (stub attivo, da cablare)
- Documentazione consultata: https://docs.acubeapi.com/documentation/italy

Grazie,
Massimiliano Giurtelli — CTO Nexa Data
mgiurelli@taal.it
