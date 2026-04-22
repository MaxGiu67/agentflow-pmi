# Ticket 02 — Cassetto Fiscale: scarico massivo fatture attive e passive

**Area:** Cassetto Fiscale / Scarico Massivo
**Priorità:** P0
**Oggetto:** [NexaData] Scarico Massivo Cassetto Fiscale — richiesta documentazione e info tecniche

---

## Contesto

Contratto firmato il **10/04/2026** include il servizio **Scarico Massivo Fatture** (€600/anno, 5 P.IVA + 5.000 fatture/anno).

Stiamo implementando il modulo in AgentFlow PMI e, non essendo disponibile il sandbox per questo servizio, vorremmo ricevere per iscritto tutte le informazioni tecniche necessarie per scrivere il codice al primo colpo. Rispondete via ticket quando avete tempo — non serve organizzare call o meeting sincroni.

---

## Richieste

### 1. Documentazione tecnica completa

Potete condividerci:
- Specifica OpenAPI / Swagger del servizio scarico massivo
- Esempi di request/response reali (array URL XML? base64 embedded? link firmati temporanei?)
- SDK (Python / Node) se disponibile
- Esempi di codice client per i casi d'uso principali

### 2. Onboarding cliente — quale modalità raccomandate?

La documentazione pubblica (`/documentation/italy/gov-it/cassettofiscale`) descrive 3 modalità:

1. **Credenziali dirette Fisconline** (`PUT /business-registry-configurations/{id}/credentials/fisconline`)
2. **Con incaricato** (`PUT /ade-appointees/{id}/credentials/fisconline`)
3. **A-Cube come proxy** (delega unificata a P.IVA 10442360961 sul portale AdE)

Per un SaaS multi-cliente come il nostro (AgentFlow PMI, attualmente 4 clienti finali attivi), quale modalità raccomandate? Immaginiamo la **proxy A-Cube** per evitare ogni gestione di credenziali Fisconline nostre, corretto?

### 3. Fatture attive e passive — ambedue scaricabili?

Confermate che il servizio scarica:
- ✅ Fatture elettroniche **passive** (ricevute dal cliente)
- ✅ Fatture elettroniche **attive** (emesse dal cliente tramite altri provider SDI)
- ✅ Note di credito e debito
- ✅ Autofatture (reverse charge, TD17-27)

### 4. Backfill iniziale

Al primo scarico per un nuovo cliente, quanti mesi indietro è possibile recuperare lo storico fatture? È limitato dal servizio AdE o da A-Cube?

### 5. Polling o webhook?

- Frequenza di polling consigliata (oraria? giornaliera?)
- Esiste un **webhook** per notifica "nuova fattura disponibile"? Payload di esempio?

### 6. Deduplica e progressivo SDI

A-Cube filtra internamente i duplicati o dobbiamo gestirli noi tramite `codiceUnivocoDocumento` SDI?

### 7. Rate limit

Esiste un rate limit specifico sul servizio scarico massivo (req/minuto, req/giorno)?

### 8. Gestione errori

In caso di:
- Delega scaduta (durata 4 anni)
- Credenziali Fisconline invalide (modalità dirette/incaricato)
- Portale AdE irraggiungibile

Come veniamo notificati? Webhook dedicato o polling endpoint di stato?

### 9. Corrispettivi 2026

Nel contratto: *"Non appena l'Agenzia delle Entrate pubblicherà il nuovo canale Corrispettivi 2026, lo scarico sarà attivato e incluso nel canone concordato."*

Avete una stima della timeline AdE? Possiamo già implementare la parte lato nostro a feature flag?

### 10. Monitor consumi

Dato il nostro limite contrattuale (5 P.IVA + 5.000 fatture/anno), esiste un endpoint API per leggere in tempo reale:
- N P.IVA attivate nel nostro contratto
- N fatture scaricate anno corrente

Ci serve per alertare internamente al 80% delle soglie.

---

## Riferimenti

- Contratto firmato 10/04/2026
- PDF ricevuti: "Procedura manuale per delega" v1.0, "Procedura manuale per incarico (2)"
- Documentazione consultata: https://docs.acubeapi.com/documentation/italy/gov-it/cassettofiscale

Grazie,
Massimiliano Giurtelli — CTO Nexa Data
mgiurelli@taal.it
