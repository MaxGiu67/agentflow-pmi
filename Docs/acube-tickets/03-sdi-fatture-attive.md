# Ticket 03 — Fatturazione elettronica: attivazione operativa

**Area:** e-Invoicing / SDI + Cassetto Fiscale
**Priorità:** P0
**Oggetto:** [NexaData] Attivazione Scarico Massivo + Emissione SDI — checklist operativo

---

Buongiorno,

sono Massimiliano Giurtelli, CTO di **NexaData S.r.l.** Abbiamo firmato il contratto il **10/04/2026** che include Open Banking AISP + Scarico Massivo Fatture + servizio SDI (il contesto "SDI - Italy" è visibile nella nostra dashboard sandbox).

Per andare in produzione con il primo cliente ci serve il **checklist operativo** di entrambi i servizi fatturazione. Cosa deve fare il cliente, cosa dobbiamo fare noi.

---

## A. Scarico Massivo Fatture (Cassetto Fiscale)

1. Tra le 3 modalità di onboarding (proxy A-Cube / credenziali Fisconline dirette / incaricato), quale raccomandate per un SaaS multi-cliente come il nostro?
2. **Lato cliente finale (PMI):** oltre ai 2 PDF che ci avete fornito (delega/incarico), servono altri passaggi?
3. **Lato NexaData:** dobbiamo creare `BusinessRegistry` + `BusinessRegistryConfiguration` via API per ciascun cliente? Altre configurazioni?
4. Endpoint principali per scaricare le fatture + esempio payload risposta.
5. Tempo tipico dall'attivazione della delega al primo download possibile?
6. Webhook disponibile per "nuova fattura" o solo polling?

## B. Emissione fatture SDI

1. **Lato cliente finale:** serve registrare un codice destinatario A-Cube nel suo portale AdE? Altri passaggi?
2. **Lato NexaData:** quali configurazioni dobbiamo fare sul nostro account per abilitare l'invio?
3. Endpoint di trasmissione fattura XML + esempio cURL (payload + risposta).
4. Firma digitale: gestita da voi server-side o dobbiamo firmare noi?
5. Notifiche SDI (RC / NS / MC / NE / EC / DT): webhook dedicati? Payload?
6. Sandbox SDI è attivo sul nostro stesso account sandbox?

---

Grazie,
Massimiliano Giurtelli
CTO — NexaData S.r.l.
mgiurelli@taal.it
