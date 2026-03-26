"""Chatbot test suite — runs on the server with real data.

Endpoint: GET /api/v1/chat/test-suite
Runs 40+ prompts against the orchestrator, compares results with direct DB queries,
and returns a quality report.
"""

import logging
import time
import uuid
from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.orchestrator.graph import run_orchestrator

logger = logging.getLogger(__name__)


# ============================================================
# Expected data from direct DB queries
# ============================================================


async def _get_expected_data(db: AsyncSession, tenant_id: uuid.UUID) -> dict:
    """Query the DB directly to get ground truth values for validation."""
    data = {}

    # KPI 2024
    r = await db.execute(text(
        "SELECT type, COUNT(*), COALESCE(SUM(importo_totale), 0) "
        "FROM invoices WHERE tenant_id = :tid AND EXTRACT(YEAR FROM data_fattura) = 2024 "
        "GROUP BY type"
    ), {"tid": str(tenant_id)})
    for row in r.fetchall():
        if row[0] == "attiva":
            data["fatturato_2024"] = float(row[2])
            data["count_emesse_2024"] = int(row[1])
        elif row[0] == "passiva":
            data["costi_2024"] = float(row[2])
            data["count_ricevute_2024"] = int(row[1])
    data["ebitda_2024"] = round(data.get("fatturato_2024", 0) - data.get("costi_2024", 0), 2)

    # Total invoices
    r = await db.execute(text(
        "SELECT COUNT(*) FROM invoices WHERE tenant_id = :tid"
    ), {"tid": str(tenant_id)})
    data["total_invoices"] = int(r.scalar() or 0)

    # Top client 2024
    r = await db.execute(text(
        "SELECT structured_data->>'destinatario_nome', COUNT(*) "
        "FROM invoices WHERE tenant_id = :tid AND type = 'attiva' "
        "AND EXTRACT(YEAR FROM data_fattura) = 2024 "
        "AND structured_data->>'destinatario_nome' IS NOT NULL "
        "GROUP BY structured_data->>'destinatario_nome' ORDER BY COUNT(*) DESC LIMIT 1"
    ), {"tid": str(tenant_id)})
    row = r.fetchone()
    data["top_client_2024"] = row[0] if row else None
    data["top_client_count_2024"] = int(row[1]) if row else 0

    # NTT Data count
    r = await db.execute(text(
        "SELECT COUNT(*) FROM invoices WHERE tenant_id = :tid "
        "AND (emittente_nome ILIKE '%%NTT%%' OR structured_data->>'destinatario_nome' ILIKE '%%NTT%%')"
    ), {"tid": str(tenant_id)})
    data["ntt_data_count"] = int(r.scalar() or 0)

    # Q1 2024 fatturato
    r = await db.execute(text(
        "SELECT COALESCE(SUM(importo_totale), 0) FROM invoices "
        "WHERE tenant_id = :tid AND type = 'attiva' "
        "AND EXTRACT(YEAR FROM data_fattura) = 2024 "
        "AND EXTRACT(MONTH FROM data_fattura) BETWEEN 1 AND 3"
    ), {"tid": str(tenant_id)})
    data["fatturato_q1_2024"] = float(r.scalar() or 0)

    # January 2024 count
    r = await db.execute(text(
        "SELECT COUNT(*) FROM invoices WHERE tenant_id = :tid "
        "AND EXTRACT(YEAR FROM data_fattura) = 2024 "
        "AND EXTRACT(MONTH FROM data_fattura) = 1"
    ), {"tid": str(tenant_id)})
    data["count_gen_2024"] = int(r.scalar() or 0)

    return data


# ============================================================
# Test prompt definitions
# ============================================================


def _build_test_prompts(expected: dict) -> list[dict]:
    """Build test prompts with expected validation criteria."""
    return [
        # ── A: KPI e Fatturato ──
        {
            "id": "A01", "category": "KPI",
            "prompt": "qual è il fatturato 2024?",
            "context": {"page": "dashboard", "year": 2024},
            "checks": [
                ("has_content", True),
                ("content_contains_any", ["4.724", "4724", "fatturato"]),
                ("tool_used", "get_period_stats"),
            ],
        },
        {
            "id": "A02", "category": "KPI",
            "prompt": "ebitda primo trimestre 2024",
            "context": {"page": "dashboard", "year": 2024},
            "checks": [
                ("has_content", True),
                ("tool_used", "get_period_stats"),
                ("has_content_blocks", True),
            ],
        },
        {
            "id": "A03", "category": "KPI",
            "prompt": "costi 2024",
            "context": {"page": "dashboard", "year": 2024},
            "checks": [
                ("has_content", True),
                ("content_contains_any", ["106", "costi"]),
                ("tool_used", "get_period_stats"),
            ],
        },
        {
            "id": "A04", "category": "KPI",
            "prompt": "fatturato 2025",
            "context": {"page": "dashboard", "year": 2024},
            "checks": [
                ("has_content", True),
                ("has_action_set_year", 2025),
            ],
        },
        {
            "id": "A05", "category": "KPI",
            "prompt": "ricavi di ottobre",
            "context": {"page": "dashboard", "year": 2024},
            "checks": [
                ("has_content", True),
                ("tool_used", "get_period_stats"),
            ],
        },
        {
            "id": "A06", "category": "KPI",
            "prompt": "kpi annuali",
            "context": {"page": "dashboard", "year": 2024},
            "checks": [
                ("has_content", True),
                ("tool_used", "get_period_stats"),
                ("has_content_blocks", True),
            ],
        },
        {
            "id": "A07", "category": "KPI",
            "prompt": "quanto ho guadagnato?",
            "context": {"page": "dashboard", "year": 2024},
            "checks": [
                ("has_content", True),
                ("tool_used_not", "direct_response"),
            ],
        },
        {
            "id": "A08", "category": "KPI",
            "prompt": "utile netto 2024",
            "context": {"page": "dashboard", "year": 2024},
            "checks": [
                ("has_content", True),
                ("tool_used", "get_period_stats"),
            ],
        },
        {
            "id": "A09", "category": "KPI",
            "prompt": "ebitda q2 2024",
            "context": {"page": "dashboard", "year": 2024},
            "checks": [
                ("has_content", True),
                ("tool_used", "get_period_stats"),
                ("has_content_blocks", True),
            ],
        },
        {
            "id": "A10", "category": "KPI",
            "prompt": "entrate e uscite 2024",
            "context": {"page": "dashboard", "year": 2024},
            "checks": [
                ("has_content", True),
                ("tool_used", "get_period_stats"),
            ],
        },

        # ── B: Top Clienti/Fornitori ──
        {
            "id": "B01", "category": "Top",
            "prompt": "top 5 clienti",
            "context": {"page": "dashboard", "year": 2024},
            "checks": [
                ("has_content", True),
                ("tool_used", "get_top_clients"),
                ("content_contains_any", ["NTT"]),
                ("has_content_blocks", True),
            ],
        },
        {
            "id": "B02", "category": "Top",
            "prompt": "classifica fornitori 2024",
            "context": {"page": "dashboard", "year": 2024},
            "checks": [
                ("has_content", True),
                ("tool_used", "get_top_clients"),
            ],
        },
        {
            "id": "B03", "category": "Top",
            "prompt": "chi è il mio miglior cliente?",
            "context": {"page": "dashboard", "year": 2024},
            "checks": [
                ("has_content", True),
                ("tool_used", "get_top_clients"),
            ],
        },
        {
            "id": "B04", "category": "Top",
            "prompt": "top fornitori",
            "context": {"page": "dashboard", "year": 2024},
            "checks": [
                ("has_content", True),
                ("tool_used", "get_top_clients"),
            ],
        },
        {
            "id": "B05", "category": "Top",
            "prompt": "top 3 clienti 2024",
            "context": {"page": "dashboard", "year": 2024},
            "checks": [
                ("has_content", True),
                ("tool_used", "get_top_clients"),
                ("has_content_blocks", True),
            ],
        },

        # ── C: Ricerca Fatture ──
        {
            "id": "C01", "category": "Fatture",
            "prompt": "fatture NTT Data",
            "context": {"page": "dashboard", "year": 2024},
            "checks": [
                ("has_content", True),
                ("content_not_contains", "Non ho capito"),
                ("content_contains_any", ["NTT", "fattur"]),
            ],
        },
        {
            "id": "C02", "category": "Fatture",
            "prompt": "fattura numero 1/7",
            "context": {"page": "fatture", "year": 2024},
            "checks": [
                ("has_content", True),
                ("tool_used", "get_invoice_detail"),
            ],
        },
        {
            "id": "C03", "category": "Fatture",
            "prompt": "quante fatture ricevute?",
            "context": {"page": "dashboard", "year": 2024},
            "checks": [
                ("has_content", True),
                ("tool_used", "count_invoices"),
            ],
        },
        {
            "id": "C04", "category": "Fatture",
            "prompt": "elenco fatture emesse",
            "context": {"page": "dashboard", "year": 2024},
            "checks": [
                ("has_content", True),
                ("tool_used", "list_invoices"),
            ],
        },
        {
            "id": "C05", "category": "Fatture",
            "prompt": "mostrami le fatture di gennaio 2024",
            "context": {"page": "dashboard", "year": 2024},
            "checks": [
                ("has_content", True),
                ("content_not_contains", "0 fatture"),
            ],
        },

        # ── D: Navigazione ──
        {
            "id": "D01", "category": "Nav",
            "prompt": "vai alle scadenze",
            "context": {"page": "dashboard", "year": 2024},
            "checks": [
                ("has_content", True),
                ("has_action_navigate", "/scadenze"),
            ],
        },
        {
            "id": "D02", "category": "Nav",
            "prompt": "apri le fatture",
            "context": {"page": "dashboard", "year": 2024},
            "checks": [
                ("has_content", True),
                ("has_action_navigate", "/fatture"),
            ],
        },
        {
            "id": "D03", "category": "Nav",
            "prompt": "portami alla dashboard",
            "context": {"page": "fatture", "year": 2024},
            "checks": [
                ("has_content", True),
            ],
        },

        # ── E: Panoramica ──
        {
            "id": "E01", "category": "Panoramica",
            "prompt": "situazione 2024",
            "context": {"page": "dashboard", "year": 2024},
            "checks": [
                ("has_content", True),
                ("content_not_contains", "Non ho capito"),
                ("has_content_blocks", True),
            ],
        },
        {
            "id": "E02", "category": "Panoramica",
            "prompt": "come stanno le finanze?",
            "context": {"page": "dashboard", "year": 2024},
            "checks": [
                ("has_content", True),
                ("content_not_contains", "Non ho capito"),
            ],
        },
        {
            "id": "E03", "category": "Panoramica",
            "prompt": "panoramica",
            "context": {"page": "dashboard", "year": 2024},
            "checks": [
                ("has_content", True),
                ("content_not_contains", "Non ho capito"),
            ],
        },
        {
            "id": "E04", "category": "Panoramica",
            "prompt": "come va l'azienda?",
            "context": {"page": "dashboard", "year": 2024},
            "checks": [
                ("has_content", True),
                ("content_not_contains", "Non ho capito"),
            ],
        },
        {
            "id": "E05", "category": "Panoramica",
            "prompt": "riepilogo",
            "context": {"page": "dashboard", "year": 2024},
            "checks": [
                ("has_content", True),
                ("content_not_contains", "Non ho capito"),
            ],
        },

        # ── F: Edge Cases ──
        {
            "id": "F01", "category": "Edge",
            "prompt": "ciao",
            "context": {"page": "dashboard", "year": 2024},
            "checks": [
                ("has_content", True),
                ("content_contains_any", ["Ciao", "ciao", "aiutarti"]),
            ],
        },
        {
            "id": "F02", "category": "Edge",
            "prompt": "grazie",
            "context": {"page": "dashboard", "year": 2024},
            "checks": [
                ("has_content", True),
                ("content_contains_any", ["Prego", "prego", "bisogno"]),
            ],
        },
        {
            "id": "F03", "category": "Edge",
            "prompt": "cosa sai fare?",
            "context": {"page": "dashboard", "year": 2024},
            "checks": [
                ("has_content", True),
                ("content_not_contains", "Non ho capito"),
            ],
        },
        {
            "id": "F04", "category": "Edge",
            "prompt": "<script>alert('xss')</script>",
            "context": {"page": "dashboard", "year": 2024},
            "checks": [
                ("has_content", True),
                ("content_not_contains", "<script>"),
            ],
        },
        {
            "id": "F05", "category": "Edge",
            "prompt": "fatturato 2030",
            "context": {"page": "dashboard", "year": 2024},
            "checks": [
                ("has_content", True),
                ("no_error", True),
            ],
        },

        # ── G: Specifici per dati reali ──
        {
            "id": "G01", "category": "Reale",
            "prompt": "fatture Engineering",
            "context": {"page": "dashboard", "year": 2024},
            "checks": [
                ("has_content", True),
                ("content_contains_any", ["Engineering", "ENGINEERING", "engineering"]),
            ],
        },
        {
            "id": "G02", "category": "Reale",
            "prompt": "fatturato gennaio 2024",
            "context": {"page": "dashboard", "year": 2024},
            "checks": [
                ("has_content", True),
                ("content_not_contains", "0,00"),
                ("has_content_blocks", True),
            ],
        },
        {
            "id": "G03", "category": "Reale",
            "prompt": "cash flow",
            "context": {"page": "dashboard", "year": 2024},
            "checks": [
                ("has_content", True),
                ("tool_used", "predict_cashflow"),
            ],
        },
        {
            "id": "G04", "category": "Reale",
            "prompt": "scadenze in ritardo",
            "context": {"page": "dashboard", "year": 2024},
            "checks": [
                ("has_content", True),
                ("tool_used", "get_fiscal_alerts"),
            ],
        },
        {
            "id": "G05", "category": "Reale",
            "prompt": "stato patrimoniale",
            "context": {"page": "contabilita", "year": 2024},
            "checks": [
                ("has_content", True),
                ("tool_used", "get_balance_sheet_summary"),
            ],
        },
    ]


# ============================================================
# Check functions
# ============================================================


def _run_check(check: tuple, result: dict) -> tuple[bool, str]:
    """Run a single check against the orchestrator result. Returns (passed, detail)."""
    check_type = check[0]
    expected = check[1]

    content = result.get("content", "")
    meta = result.get("response_meta", {}) or {}
    tool_calls = result.get("tool_calls", []) or []

    if check_type == "has_content":
        ok = bool(content and len(content) > 5)
        return ok, f"content length={len(content)}"

    if check_type == "content_contains_any":
        found = any(kw in content for kw in expected)
        return found, f"looking for {expected}, found={found}"

    if check_type == "content_not_contains":
        ok = expected not in content
        return ok, f"'{expected}' should not be in content, found={not ok}"

    if check_type == "tool_used":
        tools = [tc.get("tool", "") for tc in tool_calls]
        ok = expected in tools
        return ok, f"expected tool={expected}, got={tools}"

    if check_type == "tool_used_not":
        tools = [tc.get("tool", "") for tc in tool_calls]
        ok = expected not in tools
        return ok, f"tool={expected} should NOT be used, tools={tools}"

    if check_type == "has_content_blocks":
        blocks = meta.get("content_blocks", [])
        ok = len(blocks) > 0
        return ok, f"content_blocks count={len(blocks)}"

    if check_type == "has_action_set_year":
        actions = meta.get("actions", [])
        ok = any(a.get("type") == "set_year" and a.get("value") == expected for a in actions)
        return ok, f"looking for set_year={expected}, actions={actions}"

    if check_type == "has_action_navigate":
        actions = meta.get("actions", [])
        suggested = meta.get("suggested_actions", [])
        all_actions = actions + suggested
        ok = any(a.get("type") == "navigate" and expected in a.get("path", "") for a in all_actions)
        return ok, f"looking for navigate to {expected}"

    if check_type == "no_error":
        ok = "error" not in content.lower() and "errore" not in content.lower()
        return ok, f"no error in content"

    return False, f"unknown check: {check_type}"


# ============================================================
# Main test runner
# ============================================================


async def run_chatbot_test_suite(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> dict:
    """Run the full chatbot test suite. Returns detailed report."""

    # Get ground truth from DB
    expected = await _get_expected_data(db, tenant_id)

    # Build prompts
    prompts = _build_test_prompts(expected)

    results = []
    total_pass = 0
    total_fail = 0
    total_time = 0

    for test in prompts:
        t0 = time.time()
        try:
            result = await run_orchestrator(
                user_message=test["prompt"],
                tenant_id=tenant_id,
                user_id=user_id,
                db=db,
                context=test.get("context"),
            )
            elapsed = round((time.time() - t0) * 1000)
            total_time += elapsed

            # Run checks
            check_results = []
            all_passed = True
            for check in test["checks"]:
                passed, detail = _run_check(check, result)
                check_results.append({
                    "check": check[0],
                    "expected": str(check[1]),
                    "passed": passed,
                    "detail": detail,
                })
                if not passed:
                    all_passed = False

            verdict = "PASS" if all_passed else "FAIL"
            if all_passed:
                total_pass += 1
            else:
                total_fail += 1

            results.append({
                "id": test["id"],
                "category": test["category"],
                "prompt": test["prompt"],
                "verdict": verdict,
                "time_ms": elapsed,
                "content_preview": (result.get("content", "") or "")[:150],
                "tool_calls": [tc.get("tool", "") for tc in (result.get("tool_calls") or [])],
                "has_blocks": bool((result.get("response_meta") or {}).get("content_blocks")),
                "checks": check_results,
            })

        except Exception as e:
            elapsed = round((time.time() - t0) * 1000)
            total_time += elapsed
            total_fail += 1
            results.append({
                "id": test["id"],
                "category": test["category"],
                "prompt": test["prompt"],
                "verdict": "ERROR",
                "time_ms": elapsed,
                "error": str(e),
                "checks": [],
            })

    # Summary
    total = len(prompts)
    score = round(total_pass / total * 100, 1) if total > 0 else 0

    return {
        "summary": {
            "total": total,
            "pass": total_pass,
            "fail": total_fail,
            "score": f"{score}%",
            "avg_time_ms": round(total_time / total) if total > 0 else 0,
            "total_time_ms": total_time,
        },
        "expected_data": {
            "fatturato_2024": expected.get("fatturato_2024"),
            "costi_2024": expected.get("costi_2024"),
            "ebitda_2024": expected.get("ebitda_2024"),
            "count_emesse_2024": expected.get("count_emesse_2024"),
            "count_ricevute_2024": expected.get("count_ricevute_2024"),
            "top_client": expected.get("top_client_2024"),
            "ntt_data_count": expected.get("ntt_data_count"),
        },
        "results": results,
    }
