# Review Report — Fase 5: Sprint Plan Pivot 8

**Data:** 2026-04-04
**Target:** `specs/05-sprint-plan.md` sezione Pivot 8 (Sprint 100-105)
**Cross-ref:** `specs/03-user-stories-pivot8-social.md`, `specs/04-tech-spec-pivot8.md`, `specs/database/schema-pivot8.md`

---

## Risultato: PASS

---

## Pass 1: Completeness Check

| Check | Stato | Dettaglio |
|-------|-------|-----------|
| Tutte le 21 stories assegnate a sprint | PASS | US-100→US-120 tutte presenti nei 6 sprint |
| SP per sprint nel range 15-25 | PASS | 21, 21, 21, 18, 18, 21 — tutti nel range |
| Dependency chain rispettata | PASS | Vedi analisi sotto |
| Must Have stories nei primi sprint | PASS | Sprint 100-102 contengono tutti i Must Have |
| Obiettivo per ogni sprint | PASS | 6/6 sprint con objective chiaro |
| Task breakdown per ogni story | PASS | 21/21 stories con task breakdown (3-8 task ciascuna) |
| Completion criteria per ogni sprint | PASS | 6/6 sprint con completion criteria |
| Risk analysis per ogni sprint | PASS | 6/6 sprint con 2 rischi + mitigazione |
| Milestone intermedie definite | PASS | 3 milestone (settimana 4, 8, 12) |
| Timeline stimata | PASS | 12 settimane (6 × 2 settimane) |
| Riepilogo tabellare | PASS | Tabella riepilogativa presente |

**Score: 11/11 (100%)**

### Dependency Chain Verification

```
Sprint 100: US-100 (no dep) ✅, US-101 (←US-100, same sprint) ✅,
            US-102 (←US-100,101, same sprint) ✅, US-104 (no dep) ✅

Sprint 101: US-108 (no dep) ✅, US-109 (←US-108, same sprint) ✅,
            US-103 (←US-100,102 from Sprint 100) ✅

Sprint 102: US-106 (no dep) ✅, US-105 (←US-104 from Sprint 100) ✅,
            US-107 (←US-104 from Sprint 100) ✅,
            US-111 (←US-108,109 from Sprint 101) ✅

Sprint 103: US-112 (no dep) ✅, US-113 (←US-112, same sprint) ✅,
            US-114 (←US-112, same sprint) ✅,
            US-110 (←US-109 from Sprint 101) ✅

Sprint 104: US-116 (←US-112,114 from Sprint 103) ✅,
            US-117 (←US-114 from Sprint 103) ✅,
            US-115 (←US-114 from Sprint 103) ✅

Sprint 105: US-118 (←US-117 from Sprint 104) ✅,
            US-119 (←US-118, same sprint) ✅,
            US-120 (←US-119, same sprint) ✅
```

**Tutte le dipendenze rispettate: 21/21 ✅**

---

## Pass 2: Adversarial Review

### Finding 1: Sprint 100 ha dependency intra-sprint rischiosa (BASSO)
**Problema:** US-102 (migration, 8 SP) dipende da US-100 e US-101 nello stesso sprint. Se US-100 ritarda, US-102 non può partire.
**Mitigazione già presente:** US-100 e US-101 sono 5+3=8 SP, completabili nella prima settimana. US-102 nella seconda. Rischio accettabile.

### Finding 2: Sprint 105 ha 3 stories sequenziali (BASSO)
**Problema:** US-118→US-119→US-120 sono in cascata nello stesso sprint (21 SP). Se US-118 (compensi rules, 8 SP) ritarda, US-119 e US-120 slittano.
**Suggerimento:** Considerare di spostare US-120 (5 SP) in uno Sprint 106 di buffer se necessario.

### Finding 3: Nessun buffer sprint (MEDIO)
**Problema:** 120 SP in 6 sprint senza sprint di buffer per imprevisti, tech debt, o bug fix.
**Suggerimento:** Aggiungere Sprint 106 come "buffer + tech debt + bug fix + integration testing" (0 nuove features, solo stabilizzazione).

### Finding 4: Coerenza naming campo US-110
**Problema:** Task breakdown US-110 dice `default_channel` ma schema DB usa `default_origin_id`. Naming inconsistente.
**Fix:** Allineare al naming DB: `default_origin_id`.

### Finding totali: 4 (0 critici, 1 medio, 3 bassi)

---

## Pass 3: Edge Case Hunter

### Edge 1: Sprint 100 — Migration rollback scenario
La migration US-102 è nel primo sprint. Se fallisce in produzione, serve rollback immediato. Il task breakdown include "test migration up/down" ma non specifica un runbook di emergenza.
**Raccomandazione:** Aggiungere task "Scrivere runbook rollback migration" (0.5h).

### Edge 2: Sprint 101 — RBAC middleware + seed race condition
Il middleware RBAC e il seed ruoli vengono creati nello stesso sprint. Se il middleware è deployato prima che i ruoli siano seedati, tutti gli endpoint ritornano 403.
**Raccomandazione:** Task "Seed ruoli" deve eseguire PRIMA di "Deploy middleware RBAC" — specificare ordine nel task breakdown.

### Edge 3: Sprint 102 — Audit log volume in dev/test
L'audit log registra ogni azione. In fase di sviluppo e test, il volume può crescere rapidamente. Nessun task per cleanup/truncate in ambiente dev.
**Raccomandazione:** Aggiungere fixture di cleanup audit log per test environment.

### Edge 4: Sprint 103 — Row-level security test penetration
US-110 implementa row-level security per utenti esterni. Il task breakdown ha "test data segregation, 403 su accesso cross-canale" ma non specifica test di penetrazione via API diretta (bypass UI).
**Raccomandazione:** Aggiungere task "Test penetrazione: accesso diretto API con token utente esterno a risorse fuori canale".

### Edge 5: Sprint 104 — Dashboard con 0 deal
US-116 (dashboard KPI) non specifica nel task breakdown come gestire un tenant nuovo senza deal. Widget che dividono per 0 (win_rate) crasherebbero.
**Raccomandazione:** Aggiungere test "widget con 0 deal → mostra 'Nessun dato' e non errore divisione".

### Edge case totali: 5

---

## Riepilogo

| Dimensione | Score | Note |
|------------|-------|------|
| Completeness | 11/11 (100%) | Tutti i check passati |
| Dependencies | 21/21 (100%) | Tutte le catene rispettate |
| Finding critici | 0 | Nessuno |
| Finding medi | 1 | Manca sprint buffer |
| Finding bassi | 3 | Intra-sprint deps, naming |
| Edge case | 5 | Migration rollback, RBAC seed order, div/0 |

**Raccomandazione: PROCEDI**

Le 5 edge case sono miglioramenti incrementali che possono essere incorporati durante l'implementazione, non bloccano il planning.

---

## Azioni Consigliate (opzionali, non bloccanti)

1. **Considerare Sprint 106 buffer** — 1 sprint di stabilizzazione post-feature (integration test, bug fix, performance tuning)
2. **Fix naming US-110** — `default_channel` → `default_origin_id` nel task breakdown
3. **Aggiungere test div/0** — Widget dashboard con tenant vuoto
4. **Runbook migration** — Documento rollback per US-102

---

*Review completata il 2026-04-04*
*Risultato: PASS — Procedi con implementazione Sprint 100*
