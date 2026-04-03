# Product Requirements Document — AgentFlow PMI

**Progetto:** AgentFlow PMI
**MVP:** AgentFlow — "Il controller aziendale AI per PMI italiane"
**Data:** 2026-03-29
**Stato:** Aggiornato post Pivot 5 (Da Gestionale Contabile a Controller Aziendale AI)
**Fonte:** brainstorm/07-compare-llm.md, specs/technical/pivot-impact-analysis-v3.md

---

## Market Analysis

### Landscape Competitivo

Il mercato della gestione contabile per PMI italiane è saturo di soluzioni tradizionali ma privo di innovazione agentica:

**Competitor Diretti:**
- **Fatture in Cloud** (TeamSystem) — ~100k clienti, UX moderna, ma software reattivo senza AI. Da €25/mese.
- **Danea Easyfatt** — Storico, molto diffuso, ma datato e offline-first. €169/anno.
- **Aruba Fatturazione** — Prezzo aggressivo (da €1/mese), funzionalità basilari.
- **Zucchetti** — Suite completa enterprise-oriented. Custom pricing >€100/mese.
- **Reviso** — Cloud nativo multi-country, poco adattato al mercato italiano.

**Competitor Fintech Emergenti:**
- **Qonto** — Unicorno (>€1B valuation), banking-first non contabilità-first.
- **Finom** — Conto + fatturazione, focus su pagamenti.
- **Pennylane** (Francia) — Contabilità AI B2B2C, possibile competitor futuro in Italia.

**Gap confermato:** Nessun competitor offre agenticità, learning personalizzato, o cash flow predittivo. Finestra di opportunità first-mover.

**Pivot 5 — Nuovo posizionamento:** AgentFlow NON sostituisce il gestionale contabile — lo affianca come **controller aziendale AI**. Zero data entry, massima interpretazione. I dati arrivano da soli (cassetto fiscale, banca, paghe dal consulente). L'agente li interpreta e parla all'utente in linguaggio naturale. La contabilita funziona sotto il cofano, l'utente non la vede.

### Dati di Mercato
- ~60% PMI italiane delega tutto al commercialista (CGIA Mestre, Istat)
- ~40% usa Excel/Google Sheets come "gestionale"
- Keyword "fatturazione elettronica" CPC €3-8 — CAC via ads alto
- PSD2/Open Banking obbligatorio in UE — integrazione bancaria fattibile

---

## Functional Requirements by Epic

### EPIC 0: Autenticazione e Profilo (v0.1) — Must Have

| # | Requisito | Priorità | Giustificazione |
|---|-----------|----------|-----------------|
| A1 | Registrazione utente (email + password) | Must | Prerequisito per tutto |
| A2 | Login / Logout / Password reset | Must | Base auth |
| A3 | Profilo utente (tipo azienda, regime fiscale, P.IVA) | Must | Necessario per piano conti e scadenze |
| A4 | Autenticazione SPID/CIE (delegata via FiscoAPI) | Must | Necessaria per accesso cassetto fiscale |

### EPIC 1: Acquisizione Fatture da Cassetto Fiscale (v0.1) — Must Have

| # | Requisito | Priorità | Giustificazione |
|---|-----------|----------|-----------------|
| M1 | Sync fatture da cassetto fiscale AdE via FiscoAPI (SPID/CIE) | Must | H1: activation driver — fonte primaria, 95%+ fatture |
| M2 | Parser XML FatturaPA (dati strutturati da cassetto) | Must | H1: estrazione dati — accuracy ~100% |
| M4 | UI di verifica/correzione categorizzazione | Must | H1+H2: feedback loop |
| S1 | Ricezione real-time fatture via A-Cube SDI webhook | Should (v0.1-0.2) | Complemento: fatture appena transitate |
| S4 | Upload manuale PDF/foto | Should (v0.2) | Fallback per fatture non-SDI |
| S6 | Connessione email (Gmail/PEC/Outlook) via MCP server | Should (v0.2) | Canale secondario per documenti non-SDI |
| S7 | OCR su fatture PDF/immagine (non-XML) | Should (v0.2) | Per fatture estere, proforma, ricevute |

### EPIC 2: Categorizzazione Intelligente (v0.1) — Must Have

| # | Requisito | Priorità | Giustificazione |
|---|-----------|----------|-----------------|
| M3 | Categorizzazione con learning ibrido (rules + similarity) | Must | H2: differenziante core |
| M4 | Feedback loop: utente corregge → sistema impara | Must | H2: learning progressivo |

### EPIC 3: Contabilità in Partita Doppia (v0.1) — Must Have

| # | Requisito | Priorità | Giustificazione |
|---|-----------|----------|-----------------|
| M5 | AccountingEngine interno (ADR-007: Odoo rimosso) | Must | Partita doppia nativa, fiscal_rules configurabili |
| M5 | ContaAgent crea piano dei conti personalizzato via API | Must | Adattamento per tipo azienda |
| M5 | Registrazione automatica scritture dare/avere | Must | Core contabile |

### EPIC 4: Dashboard e Reporting (v0.1-v0.2)

| # | Requisito | Priorità | Giustificazione |
|---|-----------|----------|-----------------|
| M6 | Dashboard minima: fatture, scritture contabili, stato agenti | Must (v0.1) | Visibilità base |
| S3 | Report export per commercialista (da Odoo) | Should (v0.2) | Abilita B2B2C |
| S5 | Scadenzario fiscale base (alert IVA, F24, INPS) | Should (v0.2) | Prevenzione scadenze |
| S2 | Notifiche WhatsApp/Telegram | Should (v0.2) | Retention driver |

### EPIC 5: Fisco Avanzato e Compliance (v0.3)

| # | Requisito | Priorità | Giustificazione |
|---|-----------|----------|-----------------|
| F3 | Alert scadenze fiscali personalizzate per regime | v0.3 | Riduce ansia (JTBD 2) |
| F6 | Fatturazione attiva via Odoo + A-Cube SDI | v0.3 | Bidirezionalità fatture |
| F7 | Liquidazione IVA automatica | v0.3 | Compliance trimestrale |
| F8 | Bilancio CEE via Odoo OCA | v0.3 | Obbligo bilancio SRL |

**Nota:** F2 (cassetto fiscale) è stato promosso a Epic 1 (M1) come fonte primaria v0.1.

### EPIC 6: Open Banking e Cash Flow (v0.3-v0.4)

| # | Requisito | Priorità | Giustificazione |
|---|-----------|----------|-----------------|
| F4 | Open Banking AISP — lettura saldi e movimenti conto corrente via A-Cube | v0.3 | Dati bancari reali per CashFlowAgent |
| F1 | Cash flow predittivo 90gg con dati bancari reali | v0.3 | H3: retention driver (JTBD 3) |
| F5 | Riconciliazione automatica fatture ↔ movimenti bancari | v0.3 | Chiusura partite automatica |
| F10 | Open Banking PISP — pagamenti fornitori via API | v0.4 | Automazione pagamenti |
| F11 | Riconciliazione completa (fattura → pagamento → chiusura partita in Odoo) | v0.4 | End-to-end automation |

### EPIC 7: Normativo (v0.4)

| # | Requisito | Priorità | Giustificazione |
|---|-----------|----------|-----------------|
| F9 | Monitor aggiornamenti normativi (GU, circolari AdE) | v0.4 | Compliance proattiva |

### EPIC 8: Gap Contabili e Fisco Avanzato (v0.3-v0.4)

| # | Requisito | Priorità | Giustificazione |
|---|-----------|----------|-----------------|
| G1 | Note spese (upload, categorizzazione, rimborso) | v0.3 | Obbligo contabile per trasferte e spese dipendenti/titolare |
| G2 | Cespiti e ammortamenti (scheda, registro, calcolo automatico) | v0.3 | Obbligo registro cespiti, ammortamenti annuali |
| G3 | Ritenute d'acconto (riconoscimento, calcolo netto, scadenza F24) | v0.3 | Obbligo per chi paga professionisti/collaboratori |
| G4 | Certificazione Unica (CU) annuale | v0.4 | Obbligo annuale per sostituti d'imposta |
| G5 | Imposta di bollo automatica (fatture esenti >€77,16) | v0.3 | Obbligo legale, €2 per fattura esente IVA |
| G6 | Ratei e risconti di fine esercizio | v0.3 | Principio di competenza, scritture di assestamento |
| G7 | F24 compilazione e generazione | v0.4 | Versamento imposte e contributi — il CEO deve pagare |
| G8 | Conservazione digitale a norma (via provider certificato) | v0.4 | Obbligo 10 anni (art. 39 D.P.R. 633/1972) |

### EPIC 9: Cruscotto CEO e Controllo di Gestione (v0.4-v1.0)

| # | Requisito | Priorità | Giustificazione |
|---|-----------|----------|-----------------|
| C1 | Dashboard CEO (fatturato vs budget, EBITDA, top clienti, DSO/DPO) | v0.4 | H4: upgrade driver, il CEO decide guardando i dati |
| C2 | Centri di costo (allocazione automatica da fatture categorizzate) | v1.0 | Controllo di gestione base — dove spendo? |
| C3 | Budget annuale vs consuntivo (confronto mensile) | v1.0 | Il CEO deve sapere se è in linea con le previsioni |
| C4 | Analisi marginalità per cliente | v1.0 | "Quanto guadagno davvero dal cliente X?" |
| C5 | KPI personalizzabili | v1.0 | Ogni CEO ha i suoi numeri chiave |
| C6 | Simulazioni what-if ("se assumo 2 persone...") | v1.5 | Pianificazione strategica |

### EPIC 10: Gestione Personale — HR Base (v1.0)

| # | Requisito | Priorità | Giustificazione |
|---|-----------|----------|-----------------|
| H1 | Anagrafica dipendenti (contratto, livello, RAL, CCNL) | v1.0 | Base per qualsiasi calcolo HR |
| H2 | Calcolo costo azienda da RAL (contributi INPS, INAIL, TFR, 13a/14a) | v1.0 | Spesa #1 per 70% PMI — il CEO DEVE saperlo |
| H3 | Budget HR e simulazione assunzioni | v1.0 | "Quanto mi costa assumere un senior developer?" |
| H4 | Scadenzario HR (scadenza contratti, periodi di prova, visite mediche) | v1.0 | Prevenzione dimenticanze con impatto legale |
| H5 | Gestione presenze base (ferie, permessi, malattia) | v1.5 | Necessario per calcolo costi per commessa |
| H6 | Integrazione buste paga (import da Zucchetti/TeamSystem) | v1.5 | Il calcolo buste paga resta al provider specializzato |

### EPIC 11: Gestione Ordini Cliente — CRM via Odoo 18 (v1.0) ✅ INTEGRAZIONE COMPLETATA

**Strategia (ADR-008 — Aggiornato):** CRM delegato a Odoo 18 Online (€93/mese, 3 utenti) per il ciclo pre-vendita: pipeline → offerta → ordine cliente → conferma. Dopo conferma, il commerciale crea la "commessa" nel sistema proprietario NExadata. Keap scartato (e-commerce oriented, inadeguato per IT consulting/body rental/T&M).

**Pipeline CRM:** Nuovo Lead → Qualificato → Proposta Inviata → Ordine Ricevuto → Confermato

| # | Requisito | Priorità | Status | Giustificazione |
|---|-----------|----------|--------|-----------------|
| V1 | Anagrafica clienti e fornitori da Odoo (res.partner) | v1.0 | ✅ Implementato | Adapter + REST endpoint + tool orchestrator |
| V2 | Pipeline vendite da Odoo (crm.lead con fasi personalizzate) | v1.0 | ✅ Implementato | 11 endpoint REST, 4 tool agente "crm" |
| V3 | Campi custom NExadata (x_deal_type, x_daily_rate, x_technology) | v1.0 | ✅ Implementato | T&M/fixed/spot/hardware — modello business NExadata |
| V4 | Dashboard commerciale (pipeline summary, deal per fase, valore) | v1.0 | ✅ Implementato | Tool crm_pipeline_summary nell'orchestrator |
| V5 | Registrazione ordine cliente (POST /deals/{id}/order) | v1.0 | ✅ Implementato | Tipi: PO, email, firma_word, portale. Campi: x_order_type, x_order_reference, x_order_date, x_order_notes |
| V6 | Conferma ordine e passaggio a commessa NExadata (POST /deals/{id}/order/confirm) | v1.0 | ✅ Implementato | Ordini in sospeso su GET /orders/pending |
| V7 | Webhook deal vinto → creazione progetto timesheet | v1.0 | 🔜 Prossimo | Odoo Automated Actions → /webhook/deal-won |
| V8 | Contratti attivi e scadenzario rinnovi | v1.5 | — | Alert pre-scadenza 30/60/90 giorni |

**Multi-Tenant Potential (2026-04-02):**
L'integrazione CRM via Odoo non è solo interna a NExadata. AgentFlow PMI è progettato per supportare client deployments: 4-5 clienti di NExadata sono gia interessati ad usare AgentFlow PMI + Odoo CRM integrato. La soluzione è pronta per multi-tenancy: ogni cliente può avere una propria istanza Odoo (o un database separato) mentre AgentFlow rimane centralizzato con tenant routing. Questo apre un nuovo revenue stream: NExadata può offrire AgentFlow PMI + Odoo CRM come bundle ai propri clienti di consulting IT.

### EPIC 12: Gestione Progetti e Commesse (v1.5)

| # | Requisito | Priorità | Giustificazione |
|---|-----------|----------|-----------------|
| J1 | Anagrafica commesse (cliente, budget, date, stato) | v1.5 | Per PMI di servizi — core business |
| J2 | Timesheet base (ore per persona per progetto) | v1.5 | Input per margine di commessa |
| J3 | Margine di commessa (ricavi - costi personale - spese dirette) | v1.5 | "Sto guadagnando o perdendo su questo progetto?" |
| J4 | SAL e milestone tracking | v1.5 | Stato avanzamento per cliente e direzione |
| J5 | Collegamento commessa ↔ fatture | v1.5 | Tracciabilità fatturato per progetto |

### EPIC 13: Piattaforma Multi-Tenant (v1.0)

| # | Requisito | Priorità | Giustificazione |
|---|-----------|----------|-----------------|
| P1 | Infra multi-tenant (un DB Odoo per tenant, provisioning automatico) | v1.0 | Scalabilità |
| P2 | API Gateway + Tenant Router | v1.0 | Isolamento |
| P3 | Dashboard white-label per commercialisti | v1.0 | B2B2C |
| P4 | Marketplace agenti (attiva/disattiva per tenant) | v1.0 | Monetizzazione |
| P5 | Billing + subscription management (Stripe) | v1.0 | Pagamenti |
| P6 | Onboarding self-service | v1.0 | Scalabilità |

---

### EPIC A: Sistema Agentico Conversazionale (v0.5) — Must Have (Pivot 3)

| # | Requisito | Priorita | Giustificazione |
|---|-----------|----------|-----------------|
| AG1 | Orchestratore conversazionale (chat con utente, routing a agenti) | Must | H5: interfaccia primaria — l'utente parla, non naviga |
| AG2 | Chat persistente (conversazioni salvate, ripresa dal punto lasciato) | Must | Retention: l'utente torna e trova lo storico |
| AG3 | Agenti con nomi personalizzabili (display name, personalita) | Must | Personalizzazione: l'utente chiama l'agente "Mario" |
| AG4 | Tool system (tools registrabili, eseguibili dagli agenti) | Must | Modularita: agenti usano tools per azioni concrete |
| AG5 | WebSocket streaming (risposte in tempo reale) | Should | UX: l'utente vede la risposta che si scrive |
| AG6 | Memoria conversazione (contesto a lungo termine) | Should | L'agente ricorda preferenze e scelte passate |
| AG7 | Onboarding conversazionale (ContoEconomicoAgent via chat) | Must | Gia implementato, da integrare nel flusso chat |
| AG8 | Multi-agent response (orchestratore chiama piu agenti per una risposta) | Should | Es: "come sto?" → fisco + cashflow + contabilita |
| AG9 | Agent skill discovery (agente suggerisce cosa puo fare) | Could | "Posso aiutarti con fatture, scadenze, cash flow..." |
| AG10 | Configurazione agenti nelle impostazioni | Must | UI per abilitare/disabilitare e rinominare agenti |

**Tech stack aggiuntivo:**
- LangGraph StateGraph per orchestrazione
- Claude API per reasoning degli agenti
- WebSocket (FastAPI) per streaming
- PostgreSQL per conversazioni e configurazione agenti

---

### EPIC B: Agentic Dashboard (v0.6) — Must Have

| # | Requisito | Priorita | Giustificazione |
|---|-----------|----------|-----------------|
| DB1 | Dashboard JSON-driven con widget configurabili | Must | L'utente personalizza la sua vista senza codice |
| DB2 | Widget predefiniti: stat_card, bar_chart, pie_chart, table, list, alert | Must | Copertura 80% dei casi d'uso |
| DB3 | Drag & drop riposizionamento widget (react-grid-layout) | Must | L'utente organizza la dashboard come vuole |
| DB4 | Chatbot floating nella dashboard (bottom-right, collapsibile) | Must | Interfaccia conversazionale integrata nella vista principale |
| DB5 | Tool modify_dashboard nell'orchestratore (add/remove/update widget via chat) | Must | "Aggiungi grafico fatturato" → widget appare |
| DB6 | Salvataggio layout per tenant nel DB | Must | Ogni utente ha la sua dashboard personalizzata |
| DB7 | Selettore anno per tutti i widget | Must | Filtro globale anno competenza |
| DB8 | Widget KPI con trend e confronto anno precedente | Should | L'amministratore vede l'andamento |
| DB9 | Chatbot proattivo con notifiche contestuali | Should | "3 fatture da verificare, scadenza IVA tra 12gg" |
| DB10 | Template dashboard per settore (basato su ATECO) | Could | Onboarding veloce con layout pre-configurato |

### EPIC C: Import Pipeline Silenzioso + CRUD Manuale (v0.5-v0.6) — Must Have (Pivot 5)

**Principio: il CRUD e' la base, l'import e' l'acceleratore.** L'utente deve SEMPRE poter inserire/modificare/eliminare qualsiasi voce a mano. L'import automatico e' una comodita, non un obbligo. Tutti gli import funzionano in background (silenzioso) — solo le anomalie vengono segnalate.

| # | Requisito | Priorita | Giustificazione |
|---|-----------|----------|-----------------|
| IC1 | Import estratto conto bancario (PDF + LLM extraction) | Must | Cash flow reale, riconciliazione. LLM per parsing universale (no regex fragile) |
| IC2 | Import estratto conto bancario (CSV fallback) | Must | Fallback per chi preferisce export CSV da home banking |
| IC3 | Open Banking API (Fabrick/Salt Edge AISP) — sync automatico | Must | Dati bancari freschi ogni 6h, zero intervento utente |
| IC4 | CRUD manuale movimenti bancari | Must | Inserisci/modifica/elimina singolo movimento a mano |
| IC5 | Import corrispettivi telematici (XML COR10 da cassetto fiscale) | Must | Completa fatturato per PMI retail, stessa fonte di FiscoAPI |
| IC6 | CRUD manuale corrispettivi | Must | Inserimento giornaliero manuale |
| IC7 | Import F24 versamenti (PDF + LLM extraction codici tributo) | Must | Quadratura fiscale, verifica versamenti |
| IC8 | CRUD manuale F24 | Must | Inserimento versamento manuale |
| IC9 | Import saldi bilancio iniziali (Excel/CSV + mapping LLM) | Must | Punto partenza contabile — auto-detect colonne, mapping conti |
| IC10 | Import saldi bilancio (PDF + LLM extraction) | Must | Il commercialista manda PDF, noi estraiamo con LLM |
| IC11 | Import saldi bilancio (XBRL tassonomia CEE) | Should | Bilancio depositato Camera Commercio — formato standard |
| IC12 | CRUD manuale saldi bilancio (wizard guidato) | Must | Inserimento saldi principali per chi non ha file |
| IC13 | Import contratti ricorrenti (PDF + LLM) | Should | Affitto, leasing, utenze → cash flow predittivo |
| IC14 | CRUD manuale contratti ricorrenti | Should | Inserisci ricorrenza a mano |
| IC15 | Import piano ammortamento finanziamenti (PDF + LLM) | Should | Rate, debito residuo → cash flow |
| IC16 | CRUD manuale finanziamenti/mutui | Should | Inserisci rata manuale |
| IC17 | Ammortamenti cespiti auto da fatture | Should | Auto-detect immobilizzazioni dal cassetto, aliquota ministeriale, conferma |
| IC18 | Import silenzioso con segnalazione eccezioni (max 3 azioni) | Must | Background import, solo anomalie segnalate all'utente |

**File esempio disponibili:** esempi_import/ (4 PDF banca UniCredit+Credit Agricole, 1 PDF bilancio TAAL 2023, 90 XML corrispettivi, 24 PDF paghe)

---

### EPIC D: Agenti di Gestione Aziendale — Doppio Canale (v0.6-v0.7) — Must Have (Pivot 5)

**Principio: l'agente dice all'utente cosa deve sapere e cosa deve fare.** Due modalita: dashboard (sempre visibile) e conversazione (chatbot). Alert critici anche su WhatsApp/Telegram.

| # | Requisito | Priorita | Giustificazione |
|---|-----------|----------|-----------------|
| MA1 | Budget Agent — creazione conversazionale | Must | Propone budget da storico, Q&A naturale, l'utente aggiusta parlando |
| MA2 | Budget Agent — controllo consuntivo mensile | Must | Budget vs actual automatico, scostamenti, analisi cause |
| MA3 | Controller Agent — "Come sto andando?" | Must | KPI sintetici, trend, confronto periodi, linguaggio naturale |
| MA4 | Controller Agent — "Dove perdo soldi?" | Should | Analisi costi per categoria, anomalie, suggerimenti |
| MA5 | Cash Flow Agent potenziato (dati banca + contratti ricorrenti) | Must | Previsione con movimenti reali + rate fisse + scadenze |
| MA6 | Adempimenti Agent proattivo | Must | Push 10gg prima scadenza, calcolo importi da dati reali |
| MA7 | Alert Agent (anomalie, fatture scadute, sbilanciamenti) | Should | Pattern detection, P.IVA cessate, importi anomali |
| MA8 | Riconciliazione Agent (match fatture ↔ movimenti banca) | Must | Dopo ogni sync banca, propone abbinamenti |
| MA9 | Doppio canale notifiche (dashboard + WhatsApp/Telegram) | Must | Ogni alert → push su messaging per chi non apre l'app |

---

### EPIC E: UX Controller — Non Gestionale (v0.6) — Must Have (Pivot 5)

**Principio: l'app non sembra un gestionale, sembra un assistente.** La home e' una conversazione, non una tabella. Max 3 azioni visibili.

| # | Requisito | Priorita | Giustificazione |
|---|-----------|----------|-----------------|
| UX1 | Home conversazionale (saluto + situazione + azioni) | Must | "Buongiorno, fatturato a €38k su €45k target. Prossime uscite: stipendi + F24." |
| UX2 | Completeness Score con framing positivo | Must | "Hai sbloccato Fatture + Paghe. Prossimo: collega la banca → attivi Cash Flow" |
| UX3 | Max 3 azioni pendenti visibili | Must | Le altre in backlog — non sopraffare l'utente |
| UX4 | Email auto-generata per commercialista | Should | Template per richiesta bilancio/dati |
| UX5 | Budget vs Consuntivo come widget dashboard | Must | Tabella mensile con scostamenti e colori (verde/giallo/rosso) |
| UX6 | Import wizard universale (selezione file, preview, conferma) | Must | Pattern unico per tutti i tipi di import (banca, bilancio, F24, paghe) |

---

## MoSCoW Prioritization (MVP v0.1)

### Must Have
1. Registrazione utente + autenticazione SPID/CIE
2. Sync cassetto fiscale AdE via FiscoAPI (fonte primaria)
3. Parser XML FatturaPA (dati strutturati)
4. Categorizzazione con learning
5. UI di verifica/correzione
6. Odoo headless + ContaAgent (partita doppia, piano conti)
7. Dashboard minima
8. Onboarding guidato (SPID → cassetto → prima fattura)

### Should Have (v0.2)
1. Ricezione real-time fatture via A-Cube SDI webhook
2. Email (Gmail/PEC/Outlook) via MCP server — canale secondario
3. OCR per fatture non-SDI (PDF/foto)
4. Upload manuale PDF/foto
5. Notifiche WhatsApp/Telegram
6. Report per commercialista
7. Scadenzario fiscale base

### Could Have (v0.3-v0.4)
1. CashFlowAgent + Open Banking AISP
2. Riconciliazione fatture ↔ movimenti
3. Alert scadenze fiscali personalizzate
4. Fatturazione attiva SDI
5. Liquidazione IVA automatica
6. Bilancio CEE via Odoo OCA
7. Open Banking PISP (pagamenti)
8. NormativoAgent
9. Note spese, cespiti, ritenute d'acconto, imposta di bollo, ratei/risconti
10. F24 compilazione, CU annuale, conservazione digitale a norma
11. Dashboard CEO base (fatturato vs budget, margini, KPI)

### Must Have (v0.5 — Sistema Agentico)
1. Orchestratore conversazionale con routing a agenti specialisti
2. Chat persistente (conversazioni salvate in PostgreSQL)
3. Agenti con nomi personalizzabili dall'utente
4. Tool system (wrap 9 agenti esistenti come tools)
5. Configurazione agenti nelle impostazioni
6. Onboarding conversazionale (ContoEconomicoAgent integrato)
7. Frontend chat UI (diventa interfaccia principale)

### Must Have (v0.5-v0.7 — Pivot 5: Controller Aziendale AI)
1. Import banca (PDF+LLM, CSV, Open Banking) + CRUD manuale movimenti
2. Import corrispettivi XML COR10 + CRUD manuale
3. Import F24 (PDF+LLM) + CRUD manuale
4. Import saldi bilancio (Excel/CSV/PDF/XBRL) + CRUD manuale + wizard
5. Budget Agent conversazionale (creazione + consuntivo mensile)
6. Controller Agent ("Come sto andando?", budget vs actual)
7. Cash Flow Agent potenziato (dati banca reali + contratti ricorrenti)
8. Adempimenti Agent proattivo (push 10gg prima scadenza)
9. Riconciliazione Agent (match fatture ↔ banca)
10. Home conversazionale (non tabellare, max 3 azioni)
11. Completeness Score (framing positivo)
12. Import silenzioso (background, solo anomalie segnalate)
13. Doppio canale notifiche (dashboard + WhatsApp/Telegram)
14. CRUD manuale per ogni voce importata
15. Import wizard universale (pattern unico per tutti i tipi)

### Should Have (v0.7-v0.8 — Pivot 5)
1. Import contratti ricorrenti (PDF+LLM) + CRUD
2. Import finanziamenti/mutui (PDF+LLM) + CRUD
3. Ammortamenti cespiti auto da fatture
4. Alert Agent (anomalie, P.IVA cessate, importi anomali)
5. Controller Agent — "Dove perdo soldi?" (analisi costi per categoria)
6. Email auto-generata per commercialista
7. Import saldi XBRL (tassonomia CEE)

### Could Have (v1.0)
1. HRAgent base (anagrafica, costo personale, budget HR, scadenzario)
2. CommAgent base (CRM, pipeline, preventivi, dashboard commerciale)
3. Multi-tenant + white-label commercialisti
4. Marketplace agenti + billing Stripe
5. KPI personalizzabili, simulazioni what-if

### Could Have (v1.5-v2.0)
1. ProjectAgent (commesse, timesheet, margine progetto, SAL)
2. DocAgent (repository documentale, contratti, scadenzario rinnovi)
3. FornitureAgent (ordini acquisto, albo fornitori)
4. ComplianceAgent (D.Lgs 81/08, GDPR, antiriciclaggio)
5. Simulazioni what-if
6. Gestione presenze e import buste paga
7. API pubblica per integrazioni custom

### Won't Have (v0.1-v0.4)
1. App mobile nativa
2. Multi-tenant
3. Marketplace agenti
4. Gestione HR/personale (→ v1.0)
5. Gestione commerciale/offerte (→ v1.0)
6. Gestione progetti/commesse (→ v1.5)
7. Gestione legale (→ v2.0)
8. Buste paga/cedolini (sempre integrazione, mai in-house)

---

## Out of Scope (Anti-Scope Permanente)

1. **Sostituzione del gestionale contabile** — AgentFlow AFFIANCA il gestionale, non lo sostituisce. Non deve essere rigido o richiedere data entry obbligatorio. (Pivot 5)
2. **App mobile nativa** — Web responsive sufficiente. Solo se retention lo giustifica.
3. **Buste paga/cedolini in-house** — Troppo complesso (CCNL, addizionali, detrazioni). Sempre integrazione con provider (Zucchetti, TeamSystem).
4. **Diventare intermediario telematico AdE** — Cambia completamente i requisiti normativi.
5. **LLM API per categorizzazione base** — Rules + similarity engine (ADR-003). LLM usato per: orchestratore conversazionale, onboarding, PDF extraction banca/F24/bilancio (Pivot 5).
6. **ERP completo** — AgentFlow e' un controller AI, non un SAP. AccountingEngine interno (ADR-007).
7. **Gestione magazzino/inventario** — Troppo specifico per settore, fuori target PMI di servizi.

---

## Regole Anti-Scope Creep

1. **Fase 1 (v0.1-0.2):** Solo ContaBot + FiscoAgent. Nessun agente aggiuntivo finché H1 non è validata.
2. **Fase 2 (v0.3-0.4):** Gap contabili e fisco. Si sbloccano solo con richiesta diretta da almeno 10 utenti beta.
3. **Fase 3 (v1.0):** ControllerAgent, HRAgent, CommAgent SOLO se product-market fit confermato (H1+H2 GO).
4. **Fase 4-5 (v1.5-v2.0):** ProjectAgent, DocAgent, ComplianceAgent SOLO con 10+ commercialisti partner e 200+ utenti attivi.
5. Ogni nuova feature va confrontata con la fase attuale — se appartiene a una fase successiva, va nel Won't Have.

---

## Risks

### Rischi di Mercato

| Rischio | Probabilità | Impatto | Mitigazione |
|---------|:-----------:|:-------:|-------------|
| CAC alto (mercato saturo, keyword costose) | Alta | Alto | GTM via commercialisti (B2B2C) anziché ads diretti |
| Adozione lenta (PMI diffidenti verso AI) | Alta | Medio | Spiegabilità: mostra sempre il ragionamento dell'agente |
| Compliance conservazione digitale | Media | Alto | Partnership con provider certificati (Aruba, InfoCert) |
| Qualità dati storici (import da Excel caotico) | Alta | Medio | Migration wizard + "pulizia assistita" come feature |
| Competitor che copiano (TeamSystem aggiunge AI) | Media | Alto | Velocità di esecuzione + community + dati utente come moat |

### Rischi Tecnici

| Rischio | Probabilità | Impatto | Mitigazione |
|---------|:-----------:|:-------:|-------------|
| Odoo come dipendenza pesante/complessa | Alta | Alto | Containerizzare, limitare moduli, team con competenza Odoo |
| OCR accuracy <85% su fatture italiane | Media | Critico | Priorità parsing XML SDI (dati strutturati), OCR come fallback |
| FiscoAPI/A-Cube down o cambio pricing | Media | Alto | Abstraction layer, fallback CWBI/Invoicetronic |
| PSD2 consent scade ogni 90gg | Alta | Medio | Auto-rinnovo con notifica utente, graceful degradation |
| Learning non converge con pochi dati | Media | Alto | Baseline rule-based sempre attiva |

### Rischi Security & Privacy
- **Costo security anno 1:** €20-35k
- **DPIA obbligatoria** prima del lancio (trattamento dati su larga scala)
- **Conservazione fatture 10 anni** (art. 39 D.P.R. 633/1972)
- **OAuth tokens = asset più sensibile** — encryption at-rest, Secrets Manager
- **NON diventare intermediario AdE** — evita requisiti normativi aggiuntivi

---

## Milestones

| Versione | Timeline | Deliverables chiave | Kill Gate |
|----------|----------|--------------------| ----------|
| v0.1 | Sett. 1-10 | SPID/CIE, Cassetto Fiscale, Parser XML, ContaAgent+Odoo, Learning, Dashboard | Activation < 40% → pivot/kill |
| v0.2 | Sett. 11-16 | A-Cube SDI webhook, Email MCP, OCR non-SDI, notifiche, report, scadenzario | Acceptance < 60% dopo 30 fatture → rivedere learning |
| v0.3 | Sett. 17-26 | CashFlowAgent, Open Banking AISP, riconciliazione, SDI attiva, Liquidazione IVA, Bilancio CEE, note spese, cespiti, ritenute, imposta bollo, ratei/risconti | — |
| v0.4 | Sett. 27-36 | NormativoAgent, PISP pagamenti, F24 compilazione, CU annuale, conservazione digitale, Dashboard CEO base | H4 engagement < 10% → rivedere cruscotto |
| v1.0 | Mesi 10-15 | ControllerAgent, HRAgent base, CommAgent base, multi-tenant, white-label, Stripe | Upgrade rate < 5% → ridurre scope |
| v1.5 | Mesi 15-20 | ProjectAgent, DocAgent, FornitureAgent, presenze, import buste paga | — |
| v2.0 | Mesi 20-26 | ComplianceAgent, marketplace third-party, API pubblica | — |

---

## Budget

| Fase | Costo stimato | Timeline | FTE |
|------|--------------|----------|-----|
| v0.1-0.2 | €60-80k | 4 mesi | 3.5 |
| v0.3-0.4 | €100-140k | 6 mesi | 4.5 |
| v1.0 | €180-250k | 5 mesi | 7 |
| **Totale anno 1** | **€340-470k** | **~15 mesi** | — |
| v1.5 | €120-160k | 5 mesi | 6 |
| v2.0 | €100-140k | 6 mesi | 5 |
| **Totale anno 2** | **€220-300k** | **~11 mesi** | — |

**Nota:** v0.3-v0.4 aumentato per gap contabili (+note spese, cespiti, ritenute, F24, conservazione digitale, dashboard CEO).

---

## Pricing

| Tier | Agenti inclusi | Prezzo | Target |
|------|---------------|--------|--------|
| **Starter** | ContaAgent + Dashboard | €49/mese | P.IVA forfettario |
| **Business** | + FiscoAgent + CashFlow + Gap contabili | €129/mese | Micro-impresa |
| **Premium** | + Dashboard CEO + Budget vs consuntivo | €249/mese | PMI (titolare) |
| **Executive** | + ControllerAgent + HRAgent + CommAgent | €399/mese | PMI (CEO/direzione) |
| **Partner** | Multi-azienda + white-label + tutti gli agenti | €599/mese (fino 20 clienti) | Commercialisti |

**Breakeven:** ~€30k MRR → 230 clienti Starter oppure 50 Partner
**Target anno 2:** €80k MRR con upsell Executive su base utenti esistente

---

## Posizionamento (aggiornato Pivot 5)

**"Non e' un gestionale. E' il controller aziendale che ogni PMI dovrebbe avere."**

AgentFlow non sostituisce il programma di contabilita — lo affianca. Non e' rigido, e' di supporto. L'imprenditore non vuole fare il contabile, vuole capire come va la sua azienda.

| Dimensione | Gestionale classico | AgentFlow |
|------------|-------------------|-----------|
| Data entry | L'utente inserisce tutto | I dati arrivano da soli |
| Interfaccia | Tabelle, griglie, form | Conversazione naturale + insight |
| Paradigma | Software reattivo (tu agisci) | Agente proattivo (lui agisce) |
| Valore | "Registra correttamente" | "Capisci cosa sta succedendo" |
| Budget | Foglio Excel da compilare | Chiacchierata con l'agente |
| Bilancio | L'utente lo legge (se sa come) | L'agente lo spiega |
| Cash flow | Consuntivo (passato) | Predittivo (futuro 90gg) |
| Errori | "Risolvi tu" | "Ho trovato questo, vuoi che sistemi?" |
| Notifiche | Email generiche | WhatsApp/Telegram contestuali |
| Onboarding | Setup manuale, ore di configurazione | SPID + sblocchi progressivi |
| Competizione | Fatture in Cloud, TeamSystem | Nessuna diretta — nuovo posizionamento |

### Principi di design (Pivot 5)
1. **Zero data entry** — I dati arrivano da fonti automatiche
2. **Import silenzioso** — Background, solo anomalie segnalate
3. **Max 3 azioni** — Mai sopraffare l'utente
4. **CRUD come base** — L'utente puo sempre inserire/modificare a mano
5. **Framing positivo** — "Hai sbloccato X", non "Ti manca il 55%"
6. **Doppio canale** — Dashboard + messaging (l'imprenditore non apre l'app ogni giorno)
7. **Supporto, non problema** — Il sistema aiuta, non crea lavoro

---

## Go-to-Market

1. **Via commercialisti (B2B2C)** — Reclutare 10 commercialisti early-adopter che portino 100+ clienti ciascuno.
2. **Spiegabilità come feature** — Target diffidente verso AI. Mostrare SEMPRE il ragionamento dell'agente.
3. **MVP = sync cassetto fiscale** — Partire dal dolore più acuto: "devo scaricare fatture dal cassetto manualmente e registrarle a mano".
4. **Import da caos** — Migration wizard critico: l'utente viene da Excel/carta.

---

## EPIC 13: Finanza Operativa — Scadenzario e Cash Flow (Pivot 6)

| # | Requisito | Priorita |
|---|-----------|----------|
| F1 | IVA scorporata — tutti i KPI dashboard/budget usano importo_netto | Must |
| F2 | Scadenzario attivo/passivo generato automaticamente da fatture | Must |
| F3 | Cash flow previsionale 30/60/90gg (saldo + incassi - pagamenti) | Must |
| F4 | Gestione fidi bancari per banca (plafond, tasso, commissioni) | Should |
| F5 | Anticipo fatture con lifecycle completo (presentazione → incasso/insoluto) | Should |
| F6 | Confronto costi anticipo tra banche | Could |

**Modelli DB:** Scadenza, BankFacility, InvoiceAdvance
**Stories:** US-70 → US-86 (17 stories, 72 SP)

## EPIC 14: CRM Sales — Pipeline e Ordini Cliente (Pivot 7)

| # | Requisito | Priorita |
|---|-----------|----------|
| S1 | CRM interno PostgreSQL (contatti, deal, stage, attivita) — no Odoo | Must |
| S2 | Pipeline Kanban drag-and-drop con 6 stadi configurabili | Must |
| S3 | Deal type: T&M, fixed, spot, hardware (con daily_rate x days) | Must |
| S4 | Ordini cliente: 4 tipi (PO, email, firma_word, portale) | Must |
| S5 | Pipeline analytics: weighted value, conversion, won/lost ratio | Should |
| S6 | Attivita CRM: call, email, meeting, note, task con storico | Should |

**Modelli DB:** CrmContact, CrmPipelineStage, CrmDeal, CrmActivity
**Stories:** US-87 → US-91, US-99 (6 stories, 29 SP)
**ADR-009:** Keap scartato, Odoo declassato a opzionale

## EPIC 15: Email Marketing con Brevo (Pivot 7)

| # | Requisito | Priorita |
|---|-----------|----------|
| E1 | Adapter Brevo per invio email con variable substitution | Must |
| E2 | Webhook tracking: open, click, bounce, unsubscribe, spam | Must |
| E3 | Template email con variabili {{nome}}, {{azienda}}, {{deal_name}} | Must |
| E4 | Invio email singola da dettaglio contatto/deal | Must |
| E5 | Dashboard email analytics: open/click/bounce rate, breakdown, top contacts | Should |
| E6 | Sequenze email multi-step con condizioni (if_opened, if_not_opened) | Should |
| E7 | Trigger automatici su eventi CRM (deal_stage_changed, contact_created) | Should |

**Modelli DB:** EmailTemplate, EmailCampaign, EmailSend, EmailEvent, EmailSequenceStep, EmailSequenceEnrollment
**Stories:** US-92 → US-98 (7 stories, 34 SP)
**Infrastruttura:** Brevo 25 EUR/mese — pattern build logic / buy infrastructure

## EPIC 16: Frontend PWA (2026-04-03)

| # | Requisito | Priorita |
|---|-----------|----------|
| P1 | PWA installabile (manifest, service worker, icons) | Must |
| P2 | Code splitting React.lazy (riduzione bundle -66%) | Must |
| P3 | Bottom nav mobile (5 tab) + safe areas iOS | Must |
| P4 | Skeleton loading + ErrorBoundary | Must |
| P5 | Design system: DM Sans, CSS variables, dark mode prep | Should |
| P6 | useOptimistic per Kanban drag-and-drop | Should |

---
_Aggiornato: 2026-04-03 — Pivot 6+7 (EPIC 13-16)_
_Aggiornato: 2026-03-29 — Pivot 5: Controller Aziendale AI_
