# 10 — Cassetto Fiscale (Scarico Massivo Fatture)

**Fonte:** https://docs.acubeapi.com/documentation/italy/gov-it/cassettofiscale

⚠️ **Servizio separato dall'Open Banking** — parte del contratto AgentFlow/NexaData al costo di €600/anno.

---

## Cosa è

Cassetto Fiscale è il portale dell'Agenzia delle Entrate dove le aziende gestiscono documenti commerciali. A-Cube agisce come **intermediario** per automatizzare l'accesso usando credenziali Fisconline.

## Operazioni automatizzabili

- Gestione **Smart Receipt** (documenti commerciali online)
- **Scarico massivo fatture** inviate o ricevute tramite provider terzi

**Nota:** Smart Receipt non consentite con proxy (delega unificata).

---

## 3 modalità di onboarding

### 1. Credenziali dirette

L'azienda fornisce direttamente a A-Cube:
- Codice fiscale
- Password Fisconline
- PIN Fisconline

**Endpoint:**
```
PUT /business-registry-configurations/{id}/credentials/fisconline
```

**Implicazioni:** l'azienda cliente deve darci le proprie credenziali AdE. Possibile issue di fiducia/GDPR per il cliente finale.

### 2. Con incaricato

Un terzo (es. commercialista) agisce per conto dell'azienda.

**Procedura:**
1. Configurare l'incaricato
2. Archiviare credenziali:
   ```
   PUT /ade-appointees/{id}/credentials/fisconline
   ```
3. Creare `BusinessRegistryConfiguration`
4. **Nomina formale sul portale AdE** (manuale — vedi PDF "Procedura di incarico")
5. Assegnazione tramite API di incarico

### 3. A-Cube come proxy (raccomandato)

La società cliente nomina **A-Cube** come delegato unificato sul portale AdE con permessi limitati.

**Procedura documentata nei PDF:**
- CF da delegare: **A-Cube P.IVA 10442360961**
- Alternativa incarico personale: **CF PGNLSN73B01B300Q**
- Delega **manuale** via portale AdE (non automatizzabile)
- Durata: fino al **31/12 del 4° anno successivo** al conferimento
- Max 2 intermediari delegati

---

## Gestione password (direct/incaricato)

⚠️ **Le password AdE scadono dopo 90 giorni.**

A-Cube invia notifiche automatiche a **21, 14, 7, 2 giorni** prima della scadenza.

L'aggiornamento avviene tramite API specifiche per `BusinessRegistryConfiguration` o `Appointee`.

**Implicazione AgentFlow:** se usiamo modalità "credenziali dirette" o "incaricato", dobbiamo gestire la rotazione password ogni 90 giorni — notifica al cliente + endpoint UI per aggiornare password.

Se usiamo modalità "proxy" (delega ad A-Cube), questo problema non esiste perché A-Cube gestisce direttamente.

---

## Endpoint principali (inferiti)

❓ Non completamente documentati pubblicamente:

| Metodo | Path (ipotesi) | Scopo |
|---|---|---|
| GET | `/business-registry/{fiscalId}/invoices` | Lista fatture |
| GET | `/business-registry/{fiscalId}/invoices/{id}` | Dettaglio fattura |
| GET | `/business-registry/{fiscalId}/invoices/{id}/xml` | Download XML |
| GET | `/business-registry-configurations/{id}` | Config scarico |
| PUT | `/business-registry-configurations/{id}` | Update config |
| PUT | `/business-registry-configurations/{id}/credentials/fisconline` | Credenziali dirette |
| PUT | `/ade-appointees/{id}/credentials/fisconline` | Credenziali incaricato |

**Serve call tecnica A-Cube per conferma** — il contratto lo prevede esplicitamente ("La sandbox non è ancora disponibile per lo scarico massivo di fatture. È possibile organizzare una call tecnica").

---

## Tipologie documenti scaricabili

Basato sui servizi AdE citati nei PDF delega:

- **Fatture elettroniche attive** (inviate)
- **Fatture elettroniche passive** (ricevute)
- **Note di credito** (inclusi nei duplicati informatici)
- **Autofatture**
- ⏳ **Corrispettivi elettronici** — NON ancora scaricabili, attesa canale AdE "Corrispettivi 2026" (incluso nel canone contratto senza costi aggiuntivi)

---

## Limiti contratto NexaData

- 5 P.IVA attivate (soglia "condizioni di favore")
- 5.000 fatture/anno (soglia "condizioni di favore")
- Oltre soglie → listino standard

**Implicazione:** **Usage Monitor interno obbligatorio** per alertare a 4.500 fatture e a 4 P.IVA attive.

---

## Workflow AgentFlow proposto

```
1. Cliente AgentFlow si registra
2. Wizard setup mostra 3 opzioni:
   a. "Delega A-Cube come intermediario AdE" (RACCOMANDATO)
      → Guida con screenshot, inserire P.IVA 10442360961
   b. "Fornire credenziali Fisconline" (per testing rapido)
   c. "Io uso un commercialista" (incarico)
3. Backend crea BusinessRegistryConfiguration
4. Job notturno: scarico fatture nuove (ultimi 3 giorni)
5. Parsing XML FatturaPA (già implementato in api/modules/invoices)
6. Dedup tramite codiceUnivocoDocumento SDI
7. Popolamento tabella invoices con campi estratti
```

---

## Domande aperte ❓ (call tecnica)

1. Lista completa endpoint scarico massivo
2. Schema response (array di URL XML? base64 embedded?)
3. Frequenza polling consigliata (ogni ora? giornaliero?)
4. Backfill iniziale: quanti mesi indietro posso scaricare?
5. Gestione duplicati: A-Cube filtra o dobbiamo fare noi?
6. Rate limit richieste
7. Gestione errore "delega scaduta" — come notificato?
8. Webhook disponibili per nuove fatture?
9. Sandbox quando disponibile?
10. Corrispettivi 2026 — ETA rilascio?
