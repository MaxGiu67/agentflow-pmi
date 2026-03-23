# Impact Analysis — Pivot: Cassetto Fiscale come fonte primaria

**Data:** 2026-03-22
**Causa:** Le fatture elettroniche si leggono dal cassetto fiscale (Agenzia delle Entrate via FiscoAPI). L'email Gmail va inserita come MCP server in un secondo momento.
**Scope:** Architettura — cambia la gerarchia delle fonti dati e le priorità di tutto il progetto.

---

## Causa del Pivot

Dal 1 gennaio 2024, la fatturazione elettronica è obbligatoria per quasi tutti i soggetti IVA in Italia. Il **cassetto fiscale dell'Agenzia delle Entrate** è la fonte autoritativa che contiene il 95%+ delle fatture in formato XML strutturato (FatturaPA).

Partire dall'email per cercare fatture è un approccio indiretto: il dato strutturato esiste già nel cassetto fiscale. L'email è utile solo per documenti non-SDI (proforma, fatture estero, ricevute).

### Nuova gerarchia fonti dati

| Priorità | Fonte | Cosa fornisce | Quando |
|----------|-------|---------------|--------|
| **1 (primaria)** | Cassetto Fiscale (FiscoAPI) | Fatture XML SDI, F24, dichiarazioni | v0.1 |
| **2 (real-time)** | A-Cube SDI diretto | Ricezione fatture in tempo reale via webhook | v0.1 |
| **3 (secondaria)** | Email/PEC via MCP server | Documenti non-SDI, proforma, estero | v0.2+ |
| **4 (fallback)** | Upload manuale | Fatture cartacee, foto | v0.2 |

---

## RIFARE (rigenerare completamente)

| File | Motivo |
|------|--------|
| `specs/03-user-stories.md` | Riordinamento completo priorità: US-16 (cassetto) diventa Must v0.1, US-01/02/03 (Gmail/XML email/OCR) scendono. Aggiunta stories mancanti (autenticazione, bilancio CEE, monitor normativo). Fix 40 finding della review. |

## AGGIORNARE (modifica parziale)

| File | Cosa Cambiare |
|------|--------------|
| `specs/01-vision.md` | H1 riformulata: "Cattura automatica dal cassetto fiscale" anziché "da email". Aggiornare pain cycle: non è "cercare fatture nell'email" ma "scaricare dal cassetto manualmente". Success metrics: rimuovere "OCR accuracy" come metrica primaria (XML SDI non serve OCR). |
| `specs/02-prd.md` | Epic 1 riscritta: fonte primaria = cassetto fiscale, non email. MoSCoW aggiornato: FiscoAPI → Must v0.1, Gmail → Should v0.2. Riorganizzare Epic 5 (Fisco): cassetto fiscale si sposta in Epic 1. Aggiungere Epic per autenticazione/SPID. Milestones v0.1-v0.2 aggiornate. |
| `specs/04-tech-spec.md` | Agent Roadmap: v0.1 include FiscoAgent (cassetto) + A-Cube SDI, non Gmail. Agent flow: step 1 non è più "email arriva" ma "sync cassetto fiscale". API esterne: FiscoAPI diventa giornaliera v0.1, Gmail API passa a v0.2. Aggiungere autenticazione SPID/CIE come requisito v0.1 (necessario per FiscoAPI). |
| `specs/technical/review-report.md` | Aggiornare con nota "review pre-pivot, vedi pivot-impact-analysis.md" |

## INVARIATO

| File | Motivo |
|------|--------|
| `specs/04-tech-spec.md` (sezioni DB, Security, Infra) | Schema DB, security model, infra costs non cambiano — FiscoAPI e A-Cube erano già nello stack |

---

## Impatto Dettagliato per File

### 01-vision.md — AGGIORNARE

1. **Vision Statement:** "cattura fatture" → "scarica fatture dal cassetto fiscale e le riceve in real-time da SDI"
2. **Persona 1 (P.IVA) JTBD:** "Quando ricevo fatture via email" → "Quando devo scaricare fatture dal cassetto fiscale dell'AdE"
3. **H1 riformulata:** "Se ContaBot sincronizza automaticamente le fatture dal cassetto fiscale e le categorizza" (non "da email")
4. **Success metrics:** Rimuovere "OCR accuracy ≥85%" come metrica primaria. Le fatture da cassetto sono XML strutturato → accuracy 100%. OCR diventa metrica secondaria per fatture non-SDI.
5. **Time-to-value:** Da "connetti email, parti in 5 minuti" a "autentica con SPID, parti in 5 minuti"

### 02-prd.md — AGGIORNARE

1. **Epic 1 riscritta:** "Cattura Fatture" → "Acquisizione Fatture da Cassetto Fiscale"
   - M1: ~~Connessione email Gmail~~ → **Connessione cassetto fiscale via FiscoAPI (SPID/CIE)**
   - M2: ~~OCR+Parser XML SDI~~ → **Parser XML FatturaPA da cassetto** (OCR diventa S-class per non-SDI)
   - M3: Resta (categorizzazione con learning)
   - M4: Resta (UI verifica/correzione)
   - S1: ~~Outlook/IMAP/PEC~~ → **Ricezione real-time fatture da A-Cube SDI (webhook)**
   - NUOVA S6: **Connessione email (Gmail/PEC) via MCP server** — canale secondario
   - S4: Resta (upload manuale)

2. **Epic 5 ridotta:** Il cassetto fiscale si sposta in Epic 1. Epic 5 diventa solo: liquidazione IVA, bilancio CEE, alert avanzati.

3. **MoSCoW aggiornato:**
   - Must v0.1: Cassetto fiscale + SPID, Parser XML SDI, Categorizzazione, Odoo+piano conti, Dashboard, Onboarding
   - Should v0.2: Email via MCP, OCR per non-SDI, Notifiche, Report, Scadenzario, Upload manuale
   - Could v0.3: Open Banking, Cash flow, Riconciliazione, Fatturazione attiva, Liquidazione IVA, Bilancio CEE

4. **NUOVA Epic 0: Autenticazione** — Signup, Login, Profilo, SPID/CIE (necessario per FiscoAPI)

5. **Milestones:** v0.1 timeline invariata (10 settimane), ma contenuto cambia

### 03-user-stories.md — RIFARE

Cambiamenti strutturali:

| ID attuale | Story attuale | Cambio |
|------------|--------------|--------|
| NUOVA US-00 | — | **Registrazione e autenticazione utente** (Must v0.1) |
| NUOVA US-00b | — | **Autenticazione SPID/CIE** per FiscoAPI (Must v0.1) |
| US-16 → US-01 | Cassetto fiscale FiscoAPI | **Diventa Must v0.1, ID rinumerato** — prima story del flusso |
| US-02 | XML SDI da email | **Riscritta**: parser XML FatturaPA da cassetto (non da email) |
| US-03 | OCR PDF/immagine | **Scende a Should v0.2** — utile solo per fatture non-SDI |
| US-01 (ex) | Connessione Gmail | **Scende a Should v0.2** — canale secondario via MCP |
| US-05 | Outlook/IMAP/PEC | **Scende a v0.2** — stesso pacchetto di Gmail |
| NUOVA | Ricezione real-time SDI via A-Cube | **Should v0.1 o Must** — webhook per fatture appena transitate |
| NUOVA | Bilancio CEE via Odoo OCA (F8) | **Could v0.3** |
| NUOVA | Monitor normativo (F9) | **Could v0.4** |
| US-18 | Fatturazione attiva SDI | Resta Could v0.3 |
| US-06-15, US-17, US-19-23 | Varie | **Aggiornare dipendenze** (molte non dipendono più da Gmail) |

Fix dalla review (40 finding):
- Aggiungere US autenticazione (EDGE-P1)
- Aggiungere US bilancio CEE F8 (FINDING-C2)
- Aggiungere US monitor normativo F9 (FINDING-C2)
- Aggiungere error path: sbilanciamento Odoo, fattura SDI duplicata, revoca consent, valuta estera
- Aggiungere matrice tracciabilità PRD → Stories
- Soglia learning 30 fatture → specificare finestra temporale
- Soglia cash flow €5.000 → configurabile per tenant
- Aggiungere limiti lookback per primo sync cassetto e banca
- Aggiungere AC concurrent access dove critico
- Aggiungere performance target per operazioni Odoo/OCR

### 04-tech-spec.md — AGGIORNARE

1. **Agent Roadmap v0.1:** Aggiungere FiscoAgent (cassetto), rimuovere Email Agent
2. **Agent Flow (step 1-14):** Riscrivere:
   - Step 1: FiscoAgent sync giornaliero → scarica fatture da cassetto
   - Step 2: A-Cube webhook → ricezione fatture real-time
   - Step 3: OCR Agent → solo per fatture non-XML (v0.2+)
   - Resto della catena invariato
3. **API Esterne:** FiscoAPI frequenza "Giornaliero" in v0.1 (non v0.3)
4. **Gmail API:** Frequenza da "Real-time (Pub/Sub)" a "v0.2+ via MCP server"
5. **Auth:** Aggiungere SPID/CIE come provider OAuth (necessario per FiscoAPI)
6. **API Pubblica:** Aggiungere endpoints per cassetto fiscale sync status

---

## Ordine di Riesecuzione Consigliato

```
1. Aggiornare manualmente specs/01-vision.md (5 modifiche puntuali)
2. Aggiornare manualmente specs/02-prd.md (Epic 1, MoSCoW, milestones)
3. Aggiornare manualmente specs/04-tech-spec.md (agent flow, roadmap, API)
4. /dev-stories → RIGENERARE specs/03-user-stories.md (completo, con fix review)
5. /dev-review phase 3 → Verificare coerenza post-pivot
6. /dev-sprint → Pianificazione sprint (Fase 5)
```

---
_Impact Analysis generata — 2026-03-22_
