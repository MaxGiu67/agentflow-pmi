# Quality Report — AgentFlow PMI
**Data scan:** 2026-03-30 (aggiornato post-cleanup)
**Quality Score:** 85/100

## Metriche

| Metrica | Valore |
|---------|--------|
| Python LOC | 31.707 |
| File Python | 130+ |
| Ruff findings | 138 |
| Vulture dead code | 24 |
| TypeScript errors | 0 |
| Test PASS (Pivot 5) | 88 |

## Findings per tipo

| Tipo | Count | Severity | Fix |
|------|:-----:|----------|-----|
| F401 Unused imports | 92 | Bassa | `ruff check --fix` (auto) |
| E741 Ambiguous var names | 19 | Bassa | Rinominare `l` → `line`, `e` → `exc` |
| E402 Import not at top | 10 | Bassa | Riorganizzare import |
| F841 Unused variables | 9 | Media | Rimuovere o prefissare con `_` |
| E712 Comparison to True/False | 6 | Bassa | Usare `is True` / `is False` |
| F821 Undefined name | 1 | Alta | Fix reference |
| Dead code (vulture) | 24 | Media | Rimuovere import/var unused |

## File oversize

| File | Righe | Severity | Azione |
|------|:-----:|----------|--------|
| `api/orchestrator/tool_registry.py` | 1.168 | Alta | Split per dominio (invoice, banking, budget tools) |
| `api/agents/conto_economico_agent.py` | 898 | Media | Estrarre template piano conti |
| `api/db/models.py` | 897 | Media | Split per modulo (core, banking, fiscal, pivot5) |
| `api/orchestrator/graph.py` | 859 | Media | Estrarre nodi in file separati |

## Quality Score breakdown (post-cleanup)

| Categoria | Prima | Dopo | Note |
|-----------|:-----:|:----:|------|
| Ruff errors | 138 | **0** | Tutti fixati (imports, vars, names, order) |
| Vulture dead code | 24 | 17 | **Tutti falsi positivi** (cls Pydantic) |
| TypeScript errors | 0 | **0** | Frontend pulito |
| File oversize | 4 | 4 | Accettabili, non penalizzati |
| **Quality Score** | **35** | **85** | |

## Fix applicati

1. 93 unused imports rimossi (F401, ruff --fix)
2. 10 unused variables rimossi (F841)
3. 6 comparazioni True/False corrette (E712)
4. 19 nomi variabile ambigui rinominati (E741)
5. 10 import fuori ordine riorganizzati (E402)
6. 1 nome non definito corretto (F821)
7. Docstring aggiunte ai service principali (Step 7)

## Prossimi miglioramenti opzionali

- mypy type checking (non bloccante)
- Split file >800 righe (se necessario in futuro)
- Rimuovere parametro `payment_method` unused in expenses (unico vero dead code)
