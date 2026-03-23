# Review Report — Fase 5 (Sprint Plan)
Data: 2026-03-22

## Risultato: PASS

---

## Pass 1: Completeness Check

Checklist Fase 5 da `phase-checklists.md`:

| # | Item | Esito | Dettaglio |
|---|------|-------|-----------|
| 1 | Velocity definita (SP/sprint) | ✅ PASS | 20-24 SP/sprint, 2 settimane |
| 2 | Tutte le stories Must Have nei primi sprint | ✅ PASS | 12 Must Have (69 SP) tutte in Sprint 1-3 |
| 3 | Ogni sprint ha objective chiaro | ✅ PASS | Tutti e 10 gli sprint hanno objective 1 frase + descrizione |
| 4 | Task breakdown per ogni story (3-8 task) | ✅ PASS | 40 stories con 3-7 task ciascuna, range rispettato |
| 5 | Owner ruolo per ogni task | ✅ PASS | Ogni task ha Backend, Frontend, o Test |
| 6 | SP totali per sprint coerenti con velocity | ✅ PASS | Range 20-24 SP: Sprint 1 (24), S2 (24), S3 (21), S4 (22), S5 (20), S6 (24), S7 (24), S8 (21), S9 (23), S10 (21) |
| 7 | SP totali progetto = somma SP tutte le stories | ✅ PASS | 24+24+21+22+20+24+24+21+23+21 = 224 SP = somma 40 stories |
| 8 | Rischi del piano documentati | ✅ PASS | 6 rischi globali + 1-2 rischi per sprint (totale 16) |
| 9 | Completion criteria per ogni sprint | ✅ PASS | Tutti e 10 gli sprint hanno 4-5 criteri con checkbox |

**Score: 9/9 (100%)**

---

## Pass 2: Adversarial Review

### Dipendenze tra sprint

Tutte le 40 stories sono state verificate: **nessuna dipendenza violata**. Ogni story è pianificata in un sprint successivo a quello delle sue dipendenze (o nello stesso sprint con ordinamento interno corretto).

Dipendenze critiche verificate:
- US-04 (Sprint 2) → US-03 (Sprint 1) ✅
- US-10 (Sprint 2) → US-05 (Sprint 2, ordinato dopo US-04) ✅
- US-13 (Sprint 3) → US-10 (Sprint 2) + US-12 (Sprint 1) ✅
- US-29 (Sprint 8) → US-09 (Sprint 5) + US-02 (Sprint 1) + US-10 (Sprint 2) ✅
- US-38 (Sprint 10) → US-22 (Sprint 6) + US-33 (Sprint 7) ✅
- US-40 (Sprint 10) → US-39 (Sprint 10, ordinato prima) ✅

### Assunzioni non documentate

**[FINDING-01] Team size non specificato**
Il piano assegna task a ruoli (Backend, Frontend, Test) ma non definisce quanti sviluppatori per ruolo. Le ore totali per sprint (58-62h) implicano 1-2 sviluppatori full-time, ma non è esplicitato.
**Raccomandazione:** Aggiungere sezione "Team" con composizione minima (es. "1 senior backend, 1 frontend, 0.5 QA").

**[FINDING-02] Nessun buffer esplicito per imprevisti**
I rischi citano "Buffer 3 SP/sprint" ma nessuno sprint ha effettivamente SP liberi (tutti usano 20-24 su velocity 20-24). Il buffer è implicito nella differenza tra SP allocati e velocity max (es. Sprint 3 ha 21/24 = 3 SP liberi).
**Raccomandazione:** Esplicitare il buffer come differenza: "Sprint 3: 21 SP allocati + 3 SP buffer".

**[FINDING-03] Frontend setup mancante**
Nessun task per il setup del progetto React (create-react-app/Vite, Tailwind config, CI build frontend). Il primo task frontend è in Sprint 2 ("Frontend: pagina Dashboard.tsx"), ma non c'è un task "Setup frontend project" in Sprint 1 o 2.
**Raccomandazione:** Aggiungere task "Setup React + TypeScript + Tailwind + Vite" in Sprint 1 o inizio Sprint 2 (2-3h).

### Contraddizioni

Nessuna contraddizione trovata. I numeri (SP, stories, dependencies) sono coerenti tra sprint plan, user stories e tech spec.

### Linguaggio vago

**[FINDING-04] Accuracy targets senza metodo di misurazione**
- "Categorizzazione automatica con accuracy ≥ 70%" (Sprint 2) — misurata su quale test set? Holdout? Cross-validation?
- "Riconciliazione automatica con match ≥ 70%" (Sprint 7) — stessa ambiguità
**Raccomandazione:** Specificare: "accuracy ≥ 70% misurata su holdout set di 50 fatture etichettate manualmente".

**[FINDING-05] Stime ore senza incertezza**
Tutte le stime sono puntuali (es. "4h", "6h") senza range di incertezza. Per un progetto con molte integrazioni esterne (Odoo, FiscoAPI, A-Cube), le stime puntuali sono ottimistiche.
**Raccomandazione:** Non bloccante — le stime puntuali sono accettabili per sprint planning iniziale, verranno raffinate con la velocity reale.

### Error path nello sprint plan

Non applicabile direttamente alla Fase 5 (gli error path sono nelle user stories, già validati in review v3).

---

## Pass 3: Edge Case Hunter

### Carico e capacità

**[EDGE-01] Sprint 1 al limite superiore (24 SP)**
Sprint 1 è il più rischioso: include SPID/CIE (US-03, 8 SP) e Odoo setup (US-12, 8 SP), entrambe integrazioni esterne complesse. Se US-03 si blocca, US-04 (Sprint 2) non può partire.
**Suggerimento:** Il piano lo documenta come rischio ("US-12 può slittare a Sprint 2"). Accettabile.

**[EDGE-02] Sprint 2 ha catena sequenziale obbligatoria**
US-04 → US-05 → US-10 → US-14. Nessun parallelismo possibile all'interno dello sprint. Se US-04 ritarda di 2 giorni, tutto slitta.
**Suggerimento:** US-14 (Dashboard) non dipende da US-10, solo da US-05. Potrebbe essere implementata in parallelo con US-10.

**[EDGE-03] Nessuna regression testing budget**
Sprint 4-10 non includono tempo per testare che le feature di sprint precedenti continuino a funzionare. Con 40 stories incrementali, il debito di regression test cresce.
**Suggerimento:** Aggiungere 2-3h/sprint per "regression test suite maintenance" a partire da Sprint 4.

### Infrastruttura

**[EDGE-04] Docker setup sottostimato**
"Setup FastAPI project, Docker, PostgreSQL, Redis" = 4h. Odoo in Docker aggiunge complessità significativa (networking, volumi, healthchecks). 4h potrebbe essere insufficiente.
**Suggerimento:** Separare: "Setup Docker base" (3h) + "Setup Odoo Docker con networking" (3h).

**[EDGE-05] CI/CD non pianificato come task**
GitHub Actions CI/CD è nello stack (tech spec) ma nessun task lo implementa. Chi configura i workflow `.github/workflows/ci.yml`?
**Suggerimento:** Aggiungere task "Setup CI/CD (lint + test + coverage gate)" in Sprint 1 (3h).

### Sprint finale

**[EDGE-06] Sprint 10 catena di dipendenze lunga**
US-39 dipende da US-13 (Sprint 3), US-14 (Sprint 2), US-24 (Sprint 6). Se qualsiasi sprint tra 2 e 6 ritarda una di queste stories, Sprint 10 è impattato. La catena più lunga è: US-01 → US-03 → US-04 → US-05 → US-10 → US-13 → US-39 → US-40 (8 stories attraverso 7 sprint).
**Suggerimento:** Non bloccante — la catena è intrinseca alla logica di business. Il piano identifica correttamente il rischio.

---

## Riepilogo

| Categoria | Conteggio | Dettaglio |
|-----------|-----------|-----------|
| **Completeness** | 9/9 (100%) | Tutti i gate passati |
| **Contraddizioni** | 0 | Nessuna contraddizione — SP, dependencies, stories coerenti |
| **Finding** | 5 | Team size (1), buffer (1), frontend setup (1), accuracy target (1), stime (1) |
| **Edge case** | 6 | Carico sprint 1-2 (2), regression (1), infra setup (2), catena dipendenze (1) |

**Criterio PASS:**
- Completeness ≥ 80%: ✅ (100%)
- Nessuna contraddizione: ✅ (0 trovate)
- Nessun AC senza error path: ✅ (non applicabile a Fase 5)

---

## Azioni Consigliate

### Non-blocking (miglioramenti per prima implementazione)

1. **[FINDING-03] Aggiungere task frontend setup** — 2-3h in Sprint 1 per React + Vite + Tailwind + configurazione base.

2. **[EDGE-05] Aggiungere task CI/CD** — 3h in Sprint 1 per GitHub Actions (lint, test, coverage gate).

3. **[FINDING-01] Documentare team size** — Aggiungere sezione "Team" nel sprint plan con composizione minima.

4. **[EDGE-03] Budget regression testing** — 2-3h/sprint a partire da Sprint 4 per manutenzione test suite.

### Nice-to-have

5. **[FINDING-02] Esplicitare buffer** — Annotare SP liberi per sprint.
6. **[FINDING-04] Definire metodo misurazione accuracy** — Holdout set di 50 fatture per categorizzazione.
7. **[EDGE-04] Separare task Docker setup** — Docker base + Odoo Docker separati.

---
_Review Fase 5 — 2026-03-22_
