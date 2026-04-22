# Ticket 04 — Open Banking: dettagli pratici (banche, storico, extra, CRO)

**Area:** Open Banking / AISP
**Priorità:** P1
**Oggetto:** [NexaData] Open Banking — domande pratiche su banche supportate, storico, extra, CRO

---

## Contesto

Stiamo implementando il modulo Finance di AgentFlow PMI che sincronizza i conti bancari dei nostri clienti tramite la vostra API Open Banking (contratto AISP firmato 10/04/2026).

La documentazione pubblica (https://docs.acubeapi.com/documentation/open-banking/) copre l'architettura generale, ma rimangono alcuni dettagli operativi necessari per scrivere il codice senza procedere per tentativi.

---

## Richieste

### 1. Banche italiane supportate

Potete fornire una **lista aggiornata degli ASPSP italiani** supportati? In particolare i nostri clienti operano con:

- Intesa Sanpaolo
- Unicredit
- BNL (BNP Paribas)
- Fineco
- BPM (Banco BPM)
- Credem
- Monte dei Paschi di Siena
- BCC / Iccrea
- BPER
- Poste Italiane

Tutte coperte? Ce ne sono altre che consigliate di testare per primi?

### 2. Storico transazioni al primo consenso

Quando un End User completa il primo consenso PSD2, quanti mesi/giorni indietro è possibile scaricare lo storico transazioni tramite `GET /business-registry/{fiscalId}/transactions?madeOn[strictly_after]=...`?

È un limite A-Cube o dipende dall'ASPSP? Per mappare aspettative degli utenti.

### 3. TTL `connectUrl` del webhook Reconnect

Nel payload dell'evento Reconnect ricevete un `connectUrl` per il rinnovo consenso. Questo URL è:

- Valido per una sola invocazione?
- Ha una scadenza (es. 24h, 7gg)?
- Rigenerato ad ogni nuovo webhook noticeLevel?

### 4. Normalizzazione campo `extra` delle Transaction

La documentazione API dice che il campo `extra` delle transazioni "varies by institution". Abbiamo due domande:

- Esiste una **guida di normalizzazione** o mapping per le principali banche italiane (Intesa, Unicredit, BNL, Fineco, BPM)?
- Oppure dobbiamo implementare un parser dedicato per ogni ASPSP?

### 5. CRO / TRN / reference pagamento

Il **CRO** (Codice Riferimento Operazione) e il **TRN** sono fondamentali per la riconciliazione automatica con fatture attive (incassi).

In quale campo sono esposti nella response Transaction?

- `description`?
- `extra.cro` / `extra.trn`?
- Un campo dedicato che non trovo in docs?

Varia per banca?

### 6. Frequenza sync banca → A-Cube

Quando una banca contabilizza un nuovo movimento, entro quanto è disponibile via API A-Cube? Minuti / ore / fine giornata?

### 7. Webhook "nuovo movimento"

Oltre agli eventi documentati (Connect, Reconnect, Payment), esiste o è in roadmap un **webhook per nuovo movimento** (new transaction)?

Attualmente dobbiamo pollare `GET /transactions` periodicamente, il che spreca chiamate.

### 8. Pending transactions

La documentazione indica: *"Pending transactions should be deleted on each call since their attributes, including id, can vary."*

Ci confermate il pattern corretto?
1. Cancelliamo da DB locale tutti i movimenti con `status=pending` per l'account
2. Re-inseriamo dal risultato del nuovo `GET /transactions`
3. I `booked` sono stabili, non li tocchiamo

### 9. Tassonomia `GET /categories`

- Categorie standard MCC (Merchant Category Code) o proprietarie A-Cube?
- Lista completa (numero totale)?

### 10. Disable/enable Business Registry

Gli endpoint `POST /business-registry/{fiscalId}/disable` e `/enable` hanno impatti commerciali (fee charged on enable). Nel caso uno dei nostri clienti metta in pausa l'abbonamento:

- I dati già scaricati vengono mantenuti lato A-Cube (per ricollegare poi) o cancellati?
- Quanto dura il "pause" massimo prima che A-Cube forzi cancellazione?

### 11. Limiti sandbox — errore 402

La documentazione menziona HTTP `402 Payment Required` quando si superano limiti sandbox. Ci potete dare i **valori esatti**?

- Max Business Registry in sandbox
- Max Account per BR
- Max Transactions / chiamate
- Quando si resetta il contatore?

---

## Riferimenti

- Contratto AISP firmato 10/04/2026
- Knowledge base interna: studio completo di tutta la documentazione pubblica
- Documentazione consultata: https://docs.acubeapi.com/documentation/open-banking/

Grazie,
Massimiliano Giurtelli — CTO Nexa Data
mgiurelli@taal.it
