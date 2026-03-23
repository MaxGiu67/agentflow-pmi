# Review Report — Fase 3: User Stories

**Data:** 2026-03-22
**Target:** specs/03-user-stories.md
**Cross-reference:** specs/02-prd.md, specs/01-vision.md

---

## Risultato: FAIL

---

## Pass 1: Completeness Check

| # | Check | Risultato | Dettaglio |
|---|-------|-----------|-----------|
| 1 | Ogni Feature (F-XXX) del PRD ha almeno 1 User Story | **FAIL** | 5 requisiti PRD non coperti (vedi sotto) |
| 2 | Ogni Story ha ID (US-XXX) e formato "Come [utente], voglio [azione], in modo da [beneficio]" | **PASS** | Tutte le 23 stories hanno formato corretto |
| 3 | Ogni Story ha almeno 4 AC in formato DATO-QUANDO-ALLORA | **PASS** | Tutte le 23 stories hanno esattamente 4 AC in formato corretto |
| 4 | Almeno 1 happy path AC per story | **PASS** | Tutte le stories hanno almeno 1 happy path (molte ne hanno 2) |
| 5 | Almeno 2 error path AC per story | **PASS** | Tutte le stories hanno almeno 2 error/failure AC |
| 6 | Almeno 1 edge case AC per story | **PASS** | Tutte le stories hanno almeno 1 edge case AC |
| 7 | Ogni Story ha Story Points (scala Fibonacci 1-13) | **PASS** | Tutti SP in scala Fibonacci (2, 3, 5, 8) |
| 8 | Ogni Story ha tag MoSCoW | **PASS** | Must/Should/Could assegnati a tutte le stories |
| 9 | Tabella riepilogativa con totali SP | **PASS** | Tabella presente con totali per versione. 141 SP totali |

### Dettaglio Feature PRD non coperte

| Feature PRD | Epic | Priorità | Story mancante |
|-------------|------|----------|---------------|
| F8: Bilancio CEE via Odoo OCA | E5: Fisco | v0.3 | Nessuna US copre la generazione del bilancio CEE |
| F9: Monitor aggiornamenti normativi | E7: Normativo | v0.4 | Epic 7 completamente assente dalle stories |
| F11: Riconciliazione completa (end-to-end) | E6: Banca/Cash | v0.4 | US-22 copre riconciliazione parziale, ma F11 (fattura→pagamento→chiusura partita Odoo) non è esplicitamente coperta come storia separata |
| P1-P6: Piattaforma Multi-Tenant | E8: Piattaforma | v1.0 | 6 requisiti piattaforma (multi-tenant, API Gateway, white-label, marketplace, billing, onboarding self-service) non hanno stories |
| M4 (duplicate): UI verifica/correzione | E1: Cattura | Must | M4 appare in Epic 1 E in Epic 2 nel PRD — ambiguità sorgente |

**Score: 7/9 check passati (78%)**

---

## Pass 2: Adversarial Review

### Assunzioni non documentate

1. **[FINDING-A1]** Le stories assumono che l'utente abbia un solo regime fiscale attivo alla volta, ma non gestiscono aziende con regimi misti (es. SRL con attività soggette a regimi IVA diversi — ordinario + agricolo).

2. **[FINDING-A2]** US-01 assume che Gmail sia il provider email prevalente tra le PMI italiane. Nessun dato di mercato lo supporta — molte PMI italiane usano PEC/Aruba/Libero. La dipendenza da Gmail per v0.1 potrebbe limitare l'activation rate (H1).

3. **[FINDING-A3]** US-06 assume che 30 fatture siano sufficienti per il learning. Non c'è giustificazione statistica per questa soglia — potrebbe essere troppo bassa per pattern robusti o troppo alta per utenti con poche fatture/mese.

4. **[FINDING-A4]** US-08/US-09 assumono che l'API Odoo sia abbastanza veloce da gestire la registrazione in tempo reale. Non ci sono performance target definiti per le operazioni Odoo.

5. **[FINDING-A5]** US-20 assume che A-Cube AISP sia immediatamente disponibile e funzionante con tutte le banche CBI Globe. L'assunzione è che CBI Globe = 400+ banche = copertura totale, ma potrebbe non essere così per banche minori o conti specifici (es. conti deposito).

### Contraddizioni

6. **[FINDING-C1]** **PRD vs Stories — Numerazione requisiti incoerente.** Il PRD usa una doppia numerazione: M1-M6, S1-S5, F1-F11, P1-P6 (non sequenziale F-XXX). Le stories usano US-01 a US-23. Non esiste una matrice di mapping esplicita tra M/S/F/P e US. Questo rende impossibile la tracciabilità automatica.

7. **[FINDING-C2]** **PRD dice 8 Epic, Stories ne coprono 6.** Il PRD definisce 8 Epic (E1-E8), ma le user stories coprono solo E1-E6. Epic 7 (Normativo) e Epic 8 (Piattaforma Multi-Tenant) non hanno nessuna story.

8. **[FINDING-C3]** **M4 duplicato nel PRD.** Il requisito M4 "UI di verifica/correzione categorizzazione" appare sia in Epic 1 che in Epic 2 con la stessa sigla, creando ambiguità sulla copertura. US-07 lo copre ma è assegnata a E2.

9. **[FINDING-C4]** **SP v0.3 nel riepilogo.** La tabella dice "v0.3-v0.4 (Could Have): 8 stories, 61 SP" ma il dettaglio mostra v0.3 = 7 stories (53 SP) + v0.4 = 1 story (8 SP) = 61 SP totale. Il riepilogo è corretto ma la distinzione è nascosta — potrebbe confondere nello sprint planning.

10. **[FINDING-C5]** **US-13 deps su US-12 discutibile.** US-13 (Notifiche WhatsApp/Telegram) dipende da US-12 (Scadenzario fiscale). Ma le notifiche dovrebbero essere un canale generico — anche le fatture da verificare (US-07) beneficerebbero di notifiche. La dipendenza è troppo stretta.

### Linguaggio vago

11. **[FINDING-V1]** US-15 AC-15.2: "la vedo nella dashboard entro 60 secondi" → **Accettabile** (quantificato). Ma manca il target di latenza per il processing OCR (US-03) — "l'OCR estrae" senza dire in quanto tempo.

12. **[FINDING-V2]** US-06 AC-06.2: "acceptance rate ≥80%" → **Accettabile**. Ma "30+ fatture" come soglia senza definire finestra temporale (30 fatture totali? negli ultimi 3 mesi?).

13. **[FINDING-V3]** US-10 AC-10.4: "caricamento non supera 2 secondi" → **Accettabile**. Ma il target è solo per 1000+ fatture — manca il target per la latenza standard (<100 fatture).

14. **[FINDING-V4]** US-09 AC-09.1: "registrazione fattura passiva" → descrizione precisa con conti contabili specifici. **Positivo**, ma manca un target temporale per la registrazione (sincrono? <5s?).

15. **[FINDING-V5]** US-21 AC-21.2: soglia "€5.000" è hardcoded — dovrebbe essere configurabile per tenant (una PMI con fatturato €10M ha soglie diverse da un freelance).

### Error path mancanti

16. **[FINDING-E1]** **US-01: Manca error path per quota API Gmail.** Se il volume di email supera la quota gratuita Gmail API (250 unità/secondo/utente), cosa succede? Nessun AC copre throttling/rate limiting.

17. **[FINDING-E2]** **US-09: Manca error path per scrittura contabile rifiutata da Odoo per sbilanciamento.** AC-09.3 copre "conto mancante" ma non il caso in cui l'importo DARE ≠ AVERE per errore di calcolo IVA.

18. **[FINDING-E3]** **US-18: Manca error path per fattura duplicata SDI.** Se l'utente emette per errore due fatture con stesso numero, come reagisce A-Cube/SDI?

19. **[FINDING-E4]** **US-20: Manca error path per revoca consent da parte dell'utente direttamente sulla banca.** L'utente potrebbe revocare il consent PSD2 dal portale bancario — il sistema dovrebbe rilevarlo e reagire.

20. **[FINDING-E5]** **US-22: Manca error path per movimenti in valuta estera.** Se il conto ha movimenti in USD/GBP, come gestisce la riconciliazione con fatture in EUR?

### Coerenza ID — PRD Features vs User Stories

| Feature PRD | Priorità | User Story | Coperta? |
|-------------|----------|------------|----------|
| M1 (Gmail) | Must | US-01 | ✅ |
| M2 (OCR+XML) | Must | US-02, US-03 | ✅ |
| M3 (Learning) | Must | US-06 | ✅ |
| M4 (UI verifica) | Must | US-07 | ✅ |
| M5 (Odoo+piano conti+scritture) | Must | US-08, US-09 | ✅ |
| M6 (Dashboard) | Must | US-10, US-11 | ✅ |
| S1 (Outlook/IMAP/PEC) | Should | US-05 | ✅ |
| S2 (Notifiche) | Should | US-13 | ✅ |
| S3 (Report commercialista) | Should | US-14 | ✅ |
| S4 (Upload manuale) | Should | US-04 | ✅ |
| S5 (Scadenzario) | Should | US-12 | ✅ |
| F1 (Cash flow 90gg) | v0.3 | US-21 | ✅ |
| F2 (FiscoAPI cassetto) | v0.3 | US-16 | ✅ |
| F3 (Alert scadenze personalizzate) | v0.3 | US-17 | ✅ |
| F4 (Open Banking AISP) | v0.3 | US-20 | ✅ |
| F5 (Riconciliazione) | v0.3 | US-22 | ✅ |
| F6 (Fatturazione SDI) | v0.3 | US-18 | ✅ |
| F7 (Liquidazione IVA) | v0.3 | US-19 | ✅ |
| **F8 (Bilancio CEE)** | **v0.3** | **—** | **❌ MANCANTE** |
| **F9 (Monitor normativo)** | **v0.4** | **—** | **❌ MANCANTE** |
| F10 (PISP pagamenti) | v0.4 | US-23 | ✅ |
| **F11 (Riconciliazione completa)** | **v0.4** | **—** | **❌ MANCANTE** (US-22 copre solo parzialmente) |
| **P1-P6 (Multi-tenant)** | **v1.0** | **—** | **❌ MANCANTI** (atteso: fuori scope stories v0.x) |

**Finding totali: 20**

---

## Pass 3: Edge Case Hunter

### Concurrent Access

21. **[EDGE-CA1]** **US-07: Verifica concorrente della stessa fattura.** Se l'utente verifica una fattura da mobile e desktop contemporaneamente, quale feedback vince? Nessun AC copre il conflitto di aggiornamento.

22. **[EDGE-CA2]** **US-09: Registrazione concorrente.** Se due eventi "invoice.categorized" arrivano quasi simultaneamente per la stessa fattura (es. doppio click dell'utente su "conferma"), il ContaAgent potrebbe creare due scritture duplicate su Odoo.

23. **[EDGE-CA3]** **US-20: Sync bancario concorrente.** Se il sync giornaliero è in corso e l'utente richiede un refresh manuale, cosa succede? Race condition su insert movimenti bancari.

### Empty State

24. **[EDGE-ES1]** **US-11: Dashboard scritture vuota.** AC-10.3 copre empty state per fatture, ma US-11 non ha un AC per dashboard scritture vuota (utente che ha fatture ma non ancora scritture contabili).

25. **[EDGE-ES2]** **US-14: Report senza categorie.** L'AC-14.3 copre "periodo senza fatture", ma non il caso in cui ci siano fatture tutte non categorizzate — il report sarebbe incompleto.

26. **[EDGE-ES3]** **US-21: Cash flow senza scadenze fiscali.** Se l'utente non ha configurato il profilo fiscale, il cash flow previsionale esclude le scadenze fiscali senza avvisare.

### Max-Length / Limiti

27. **[EDGE-ML1]** **US-02: Fattura XML con molte righe.** Nessun limite definito per righe fattura. Una fattura SDI con 500+ righe potrebbe causare timeout nel parsing e nella registrazione contabile (500 righe = 500 linee journal entry su Odoo).

28. **[EDGE-ML2]** **US-04: Dimensione file upload.** AC-04.3 definisce 10MB come limite — ma non specifica cosa succede con immagini ad alta risoluzione (es. foto 4000x3000) che superano i limiti dell'OCR Google Cloud Vision.

29. **[EDGE-ML3]** **US-01: Numero massimo di email monitorate.** Se la casella ha 50.000 email, il primo sync deve scansionarle tutte? Manca una policy di lookback (es. solo ultimi 30 giorni).

30. **[EDGE-ML4]** **US-22: Movimenti bancari massimi per sync.** Se il conto ha 3 anni di movimenti, il primo sync li importa tutti? Nessun limite o finestra temporale definita.

### Network Failure

31. **[EDGE-NF1]** **US-06: Learning Agent offline.** Se Redis è down, l'evento "invoice.parsed" non raggiunge il Learning Agent. Nessun AC specifica retry o dead letter queue per eventi persi.

32. **[EDGE-NF2]** **US-15: Onboarding con Gmail API down.** Se durante l'onboarding la connessione a Google fallisce, l'utente rimane bloccato al passo 3. Serve un skip con retry asincrono.

33. **[EDGE-NF3]** **US-21: Cash flow con dati bancari stale.** Se il sync bancario è fallito per 5 giorni, il cash flow mostra dati vecchi senza warning — potrebbe indurre decisioni errate.

### Permessi

34. **[EDGE-P1]** **Nessuna story copre l'autenticazione e i ruoli utente.** Manca completamente una US per signup/login/password reset. Tutte le AC assumono "sono autenticato" ma non c'è una story che definisca come.

35. **[EDGE-P2]** **US-08-09: Chi può modificare il piano dei conti dopo il setup?** Nessun AC definisce i permessi per operazioni contabili critiche (cancellare un conto, modificare una scrittura già registrata).

36. **[EDGE-P3]** **US-23: Autorizzazione pagamenti.** Per un'azienda con più utenti, chi è autorizzato a fare pagamenti? Serve un workflow di approvazione? Nessun AC lo copre.

### Dati Invalidi

37. **[EDGE-DI1]** **US-02: P.IVA con formato errato nell'XML.** L'AC copre XML malformato ma non il caso specifico in cui il file è un XML valido ma con P.IVA non esistente nel registro (verifica VIES/AdE).

38. **[EDGE-DI2]** **US-08: Codice ATECO inesistente.** AC-15.4 menziona il codice ATECO nell'onboarding, ma non valida che il codice sia reale — un typo creerebbe un piano conti inadeguato.

39. **[EDGE-DI3]** **US-18: Importo fattura negativo o zero.** Nessun AC verifica che l'utente non possa emettere una fattura con importo ≤0 (dovrebbe usare nota di credito per rettifiche).

40. **[EDGE-DI4]** **US-20: IBAN del conto con formato non italiano.** Se l'azienda ha un conto estero (es. Wise, Revolut con IBAN lituano), A-Cube AISP lo supporta? Nessun AC copre conti non-IT.

**Edge case totali: 20**

---

## Riepilogo

| Metrica | Valore | Soglia |
|---------|--------|--------|
| Completeness | 7/9 (78%) | ≥80% |
| Finding critici (Pass 2) | 20 | 0 per PASS |
| Edge case (Pass 3) | 20 | — |
| Contraddizioni trovate | 5 | 0 per PASS |
| AC senza error path adeguato | 5 stories | 0 per PASS |

**Raccomandazione: CORREGGI E RIPETI**

Motivi del FAIL:
1. **Completeness < 80%** (78%) — Feature F8, F9, F11 non coperte
2. **5 contraddizioni** trovate tra PRD e Stories (numerazione ID, epic mancanti, M4 duplicato)
3. **5 stories con error path incompleti** (US-01 quota API, US-09 sbilanciamento, US-18 duplicato SDI, US-20 revoca consent, US-22 valuta estera)
4. **US critica mancante**: autenticazione/signup/login (EDGE-P1)

---

## Azioni Consigliate

### Priorità 1 — Bloccanti (da risolvere prima di procedere)

1. **Aggiungere US per autenticazione/registrazione.** Tutte le stories assumono un utente autenticato ma non esiste la story che definisce signup, login, password reset, e profilo utente.

2. **Aggiungere US per Bilancio CEE (F8).** Il PRD lo richiede in v0.3 — serve almeno 1 story con AC per generazione bilancio via Odoo OCA.

3. **Creare matrice di tracciabilità PRD→Stories.** La doppia numerazione (M/S/F/P vs US-XXX) rende impossibile la tracciabilità. Aggiungere un campo "Req. PRD" a ogni story nella tabella riepilogativa.

### Priorità 2 — Importanti (da risolvere prima dello sprint planning)

4. **Aggiungere error path mancanti** a US-01 (quota API Gmail), US-09 (sbilanciamento Odoo), US-18 (fattura duplicata SDI), US-20 (revoca consent da portale bancario), US-22 (movimenti in valuta estera).

5. **Chiarire soglia learning US-06.** Definire se "30 fatture" è totale o in finestra mobile, e giustificare con dati o ipotesi esplicita.

6. **Aggiungere limiti di lookback** a US-01 (email) e US-20 (movimenti bancari) per il primo sync — es. "ultimi 90 giorni".

7. **Rendere soglia cash flow US-21 configurabile** per tenant anziché hardcoded a €5.000.

### Priorità 3 — Miglioramenti (raccomandati)

8. **Aggiungere US per F9 (Monitor normativo)** e F11 (Riconciliazione completa end-to-end). Le stories P1-P6 (piattaforma) possono restare fuori scope per ora.

9. **Aggiungere AC per concurrent access** dove critico: US-07 (verifica simultanea), US-09 (registrazione doppia), US-20 (sync concorrente).

10. **Documentare performance target** per operazioni Odoo (registrazione <Xs), OCR (processing <Xs), sync bancario (<Xs per N movimenti).

---
_Review Report generato — 2026-03-22_
