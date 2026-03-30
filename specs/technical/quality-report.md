# Quality Report — AgentFlow PMI
**Data scan:** 2026-03-30
**Quality Score:** 35/100

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

## Quality Score breakdown

| Categoria | Deduzione | Max |
|-----------|:---------:|:---:|
| Unused imports (92) | -15 | -15 |
| Unused vars (9) | -10 | -10 |
| Ambiguous names (19) | -5 | -5 |
| File >1000 righe (1) | -10 | — |
| File 500-1000 righe (3) | -15 | -20 |
| Dead code vulture (24) | -10 | -10 |
| TypeScript errors (0) | 0 | — |
| **TOTALE** | **-65** | |
| **Score** | **35/100** | |

## Quick wins (5 minuti, +30 punti)

1. `ruff check --fix ./api` → rimuove 92 unused imports automaticamente (+15 punti)
2. Fix 9 unused vars con `_` prefix (+10 punti)
3. Fix 6 comparison `== True/False` → `is True/False` (+5 punti)

**Score stimato dopo quick wins: 65/100**

## Refactoring consigliati (1-2 ore)

1. Split `tool_registry.py` (1168 righe) → `tools/invoice_tools.py`, `tools/banking_tools.py`, etc.
2. Split `models.py` (897 righe) → `models/core.py`, `models/banking.py`, `models/fiscal.py`
3. Rimuovere dead code (vulture 24 items)
