# Impact Analysis — Pivot: Integrazione Analisi Gap CEO

**Data:** 2026-03-22
**Tipo:** Espansione scope roadmap (non modifica v0.1)
**Trigger:** Analisi gap tra PRD attuale e esigenze reali di un CEO di PMI italiana
**Fonte:** specs/technical/analisi-gap-ceo.md

---

## Causa del Pivot

L'analisi gap ha evidenziato che il PRD copre bene il **ciclo della fattura** (v0.1-v0.4) ma manca di 7 aree critiche per un CEO:

1. **Controllo di Gestione** — 0% coperto, impatto CRITICO
2. **Gestione Personale (HR)** — 0% coperto, impatto CRITICO
3. **Gestione Commerciale (CRM)** — 0% coperto, impatto ALTO
4. **Gestione Progetti/Commesse** — 0% coperto, impatto ALTO
5. **Gap contabili minori** — note spese, cespiti, ritenute, ratei, bollo — impatto MEDIO
6. **Gap fisco** — F24 compilazione, CU, conservazione digitale — impatto ALTO
7. **Dashboard CEO** — dashboard attuale è tecnica, non direzionale — impatto CRITICO

**Decisione:** Integrare queste aree nella roadmap v0.3→v2.0 SENZA modificare v0.1 (già validato con review PASS al 95%).

---

## Scope del Cambiamento

| Aspetto | Dettaglio |
|---------|-----------|
| v0.1 (Must Have) | **INVARIATO** — 13 stories, 77 SP, review PASS |
| v0.2 (Should Have) | **INVARIATO** — 7 stories, 32 SP |
| v0.3-v0.4 | **AGGIORNARE** — aggiungere gap contabili e fisco |
| v1.0 | **AGGIORNARE** — aggiungere ControllerAgent, HRAgent, CommAgent |
| v1.5-v2.0 | **NUOVO** — ProjectAgent, DocAgent, ComplianceAgent |
| Vision | **AGGIORNARE** — espandere strategia evolutiva |
| PRD | **AGGIORNARE** — aggiungere Epic 9-13, milestones, budget |
| Stories | **AGGIORNARE** — aggiungere ~15 stories per gap v0.3-v0.4 |
| Tech Spec | **AGGIORNARE** — aggiungere nuovi agenti nella roadmap |

---

## RIFARE (rigenerare completamente)

| File | Motivo |
|------|--------|
| Nessuno | Il pivot non invalida nessun file esistente — è un'espansione, non una sostituzione |

## AGGIORNARE (modifica parziale)

| File | Cosa Cambiare |
|------|--------------|
| **specs/01-vision.md** | Espandere Strategia Evolutiva con Fase 4 (v1.5) e Fase 5 (v2.0). Aggiungere nuovi agenti nella visione. Aggiungere Persona 4 (CEO/Direttore). |
| **specs/02-prd.md** | Aggiungere Epic 9 (Controllo di Gestione), Epic 10 (HR Base), Epic 11 (CRM Base), Epic 12 (Progetti/Commesse), Epic 13 (Documentale/Compliance). Aggiornare MoSCoW (Could v1.0, Won't→v1.5+). Aggiornare Milestones (v1.0, v1.5, v2.0). Aggiornare Budget anno 2. Aggiornare Pricing con tier aggiuntivi. |
| **specs/03-user-stories.md** | Aggiungere ~12 stories per gap contabili v0.3-v0.4: note spese (2 stories), cespiti/ammortamenti (2), ritenute d'acconto (2), imposta di bollo (1), ratei/risconti (1), conservazione digitale (1), F24 compilazione (1), Dashboard CEO (2). NON aggiungere stories v1.0+ (troppo presto). |
| **specs/04-tech-spec.md** | Aggiornare Agent Roadmap con nuovi agenti v1.0+. Aggiungere sezione "Architettura v1.0: Nuovi Agenti" con ControllerAgent, HRAgent, CommAgent. Aggiornare schema DB con tabelle future. |
| **specs/technical/flusso-informazioni.md** | Aggiornare sezione 9 (Riepilogo versioni) con v1.0, v1.5, v2.0. |

## INVARIATO

| File | Motivo |
|------|--------|
| **specs/technical/review-report.md** | Review storica pre-pivot |
| **specs/technical/review-report-v2.md** | Review post-pivot, ancora valida per v0.1-v0.4 |
| **specs/technical/pivot-impact-analysis.md** | Primo pivot (cassetto fiscale), documento storico |

---

## Ordine di Esecuzione

```
1. specs/01-vision.md          — Aggiornare strategia + Persona CEO
2. specs/02-prd.md             — Aggiungere Epic 9-13, MoSCoW, Milestones, Budget
3. specs/03-user-stories.md    — Aggiungere ~12 stories gap contabili v0.3-v0.4
4. specs/04-tech-spec.md       — Aggiornare agent roadmap e schema DB
5. specs/technical/flusso-informazioni.md — Aggiornare riepilogo versioni
6. specs/_changelog.md         — Entry pivot v2
7. specs/_status.md            — Aggiornare conteggi e prossimi passi
```

---

## Dettaglio Modifiche per File

### 1. specs/01-vision.md
- **Sezione "Target Users"**: Aggiungere **Persona 4: CEO/Direttore PMI** con JTBD sul controllo di gestione
- **Sezione "Mappa del Dolore"**: Aggiungere 4° frustrazione "DECISIONI AL BUIO"
- **Sezione "Strategia Evolutiva"**: Espandere a 5 fasi (v0.1→v2.0)
- **Sezione "Success Metrics"**: Aggiungere metriche per dashboard CEO

### 2. specs/02-prd.md
- **Aggiungere 5 nuove Epic** (9-13) con requisiti dettagliati
- **Aggiornare MoSCoW**: Could v1.0 per ControllerAgent, HRAgent, CommAgent
- **Aggiornare Won't Have**: Spostare HR/Commerciale/Legale da "Won't" a "Could v1.0"
- **Aggiornare Milestones**: v1.0 (sett. 36-48), v1.5 (mesi 14-18), v2.0 (mesi 18-24)
- **Aggiornare Budget**: Anno 2 (v1.0-v2.0)
- **Aggiornare Pricing**: Tier Executive con dashboard CEO

### 3. specs/03-user-stories.md
- **Aggiungere 12 nuove stories** in Epic 3 e 5 esistenti + nuova Epic 8 (Gap Contabili):
  - US-29: Note spese — upload e categorizzazione
  - US-30: Note spese — approvazione e rimborso
  - US-31: Cespiti — scheda cespite e ammortamento
  - US-32: Cespiti — registro e dismissione
  - US-33: Ritenute d'acconto — riconoscimento e calcolo
  - US-34: Ritenute d'acconto — CU annuale
  - US-35: Imposta di bollo automatica
  - US-36: Ratei e risconti di fine esercizio
  - US-37: Conservazione digitale a norma
  - US-38: F24 compilazione e generazione
  - US-39: Dashboard CEO — cruscotto direzionale
  - US-40: Dashboard CEO — KPI e budget vs consuntivo
- **Aggiornare tabella riassuntiva** e conteggi

### 4. specs/04-tech-spec.md
- **Aggiornare Agent Roadmap** con v1.0-v2.0
- **Aggiungere sezione** "Nuovi Agenti (v1.0+)"
- **Aggiornare schema DB** con tabelle future (expenses, assets, hr_employees, projects, etc.)

---

_Impact Analysis v2 — 2026-03-22_
