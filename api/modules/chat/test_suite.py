"""Chatbot test suite — 100+ prompts tested on server with real data.

Endpoint: GET /api/v1/chat/test-suite
Runs prompts against the orchestrator, compares with direct DB queries,
returns quality + efficiency report.
"""

import logging
import time
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.orchestrator.graph import run_orchestrator

logger = logging.getLogger(__name__)


async def _get_expected_data(db: AsyncSession, tenant_id: uuid.UUID) -> dict:
    """Query DB directly for ground truth validation."""
    data = {}

    r = await db.execute(text(
        "SELECT type, COUNT(*), COALESCE(SUM(importo_totale), 0) "
        "FROM invoices WHERE tenant_id = :tid AND EXTRACT(YEAR FROM data_fattura) = 2024 GROUP BY type"
    ), {"tid": str(tenant_id)})
    for row in r.fetchall():
        if row[0] == "attiva":
            data["fatturato_2024"] = float(row[2])
            data["count_emesse_2024"] = int(row[1])
        elif row[0] == "passiva":
            data["costi_2024"] = float(row[2])
            data["count_ricevute_2024"] = int(row[1])
    data["ebitda_2024"] = round(data.get("fatturato_2024", 0) - data.get("costi_2024", 0), 2)

    r = await db.execute(text("SELECT COUNT(*) FROM invoices WHERE tenant_id = :tid"), {"tid": str(tenant_id)})
    data["total_invoices"] = int(r.scalar() or 0)

    r = await db.execute(text(
        "SELECT structured_data->>'destinatario_nome', COUNT(*) FROM invoices "
        "WHERE tenant_id = :tid AND type = 'attiva' AND EXTRACT(YEAR FROM data_fattura) = 2024 "
        "AND structured_data->>'destinatario_nome' IS NOT NULL "
        "GROUP BY 1 ORDER BY COUNT(*) DESC LIMIT 1"
    ), {"tid": str(tenant_id)})
    row = r.fetchone()
    data["top_client"] = row[0] if row else None

    r = await db.execute(text(
        "SELECT COUNT(*) FROM invoices WHERE tenant_id = :tid "
        "AND (emittente_nome ILIKE '%%NTT%%' OR structured_data->>'destinatario_nome' ILIKE '%%NTT%%')"
    ), {"tid": str(tenant_id)})
    data["ntt_count"] = int(r.scalar() or 0)

    # Monthly counts
    for m in range(1, 13):
        r = await db.execute(text(
            "SELECT COUNT(*) FROM invoices WHERE tenant_id = :tid "
            "AND EXTRACT(YEAR FROM data_fattura) = 2024 AND EXTRACT(MONTH FROM data_fattura) = :m"
        ), {"tid": str(tenant_id), "m": m})
        data[f"count_month_{m}"] = int(r.scalar() or 0)

    return data


def _build_prompts() -> list[dict]:
    """Build 100+ test prompts covering all DB query combinations."""
    prompts = []

    def add(id, cat, prompt, ctx_year, checks, page="dashboard"):
        prompts.append({
            "id": id, "category": cat, "prompt": prompt,
            "context": {"page": page, "year": ctx_year}, "checks": checks,
        })

    # ══════════════════════════════════════════════════════════
    # A: KPI / Fatturato (20 prompt)
    # ══════════════════════════════════════════════════════════
    add("A01", "KPI", "qual è il fatturato 2024?", 2024, [
        ("has_content", True), ("content_contains_any", ["4.724", "4724", "4,724"]), ("tool_used", "get_period_stats"), ("has_content_blocks", True)])
    add("A02", "KPI", "ebitda primo trimestre 2024", 2024, [
        ("has_content", True), ("tool_used", "get_period_stats"), ("has_content_blocks", True)])
    add("A03", "KPI", "costi 2024", 2024, [
        ("has_content", True), ("content_contains_any", ["106", "costi"]), ("tool_used", "get_period_stats")])
    add("A04", "KPI", "fatturato 2025", 2024, [
        ("has_content", True), ("has_action_set_year", 2025)])
    add("A05", "KPI", "ricavi di ottobre", 2024, [
        ("has_content", True), ("tool_used", "get_period_stats")])
    add("A06", "KPI", "kpi annuali", 2024, [
        ("has_content", True), ("tool_used", "get_period_stats"), ("has_content_blocks", True)])
    add("A07", "KPI", "quanto ho guadagnato?", 2024, [
        ("has_content", True), ("tool_used_not", "direct_response")])
    add("A08", "KPI", "utile netto 2024", 2024, [
        ("has_content", True), ("tool_used", "get_period_stats")])
    add("A09", "KPI", "ebitda q2 2024", 2024, [
        ("has_content", True), ("tool_used", "get_period_stats"), ("has_content_blocks", True)])
    add("A10", "KPI", "entrate e uscite 2024", 2024, [
        ("has_content", True), ("tool_used", "get_period_stats")])
    add("A11", "KPI", "margine lordo 2024", 2024, [
        ("has_content", True), ("tool_used", "get_period_stats")])
    add("A12", "KPI", "fatturato q3 2024", 2024, [
        ("has_content", True), ("tool_used", "get_period_stats"), ("has_content_blocks", True)])
    add("A13", "KPI", "fatturato q4 2024", 2024, [
        ("has_content", True), ("tool_used", "get_period_stats")])
    add("A14", "KPI", "costi primo trimestre", 2024, [
        ("has_content", True), ("tool_used", "get_period_stats")])
    add("A15", "KPI", "ricavi febbraio 2024", 2024, [
        ("has_content", True), ("tool_used", "get_period_stats")])
    add("A16", "KPI", "fatturato dicembre 2024", 2024, [
        ("has_content", True), ("tool_used", "get_period_stats")])
    add("A17", "KPI", "profitto 2024", 2024, [
        ("has_content", True), ("tool_used", "get_period_stats")])
    add("A18", "KPI", "costi secondo trimestre 2024", 2024, [
        ("has_content", True), ("tool_used", "get_period_stats")])
    add("A19", "KPI", "guadagno di marzo", 2024, [
        ("has_content", True), ("tool_used", "get_period_stats")])
    add("A20", "KPI", "ebitda annuale", 2024, [
        ("has_content", True), ("tool_used", "get_period_stats"), ("has_content_blocks", True)])

    # ══════════════════════════════════════════════════════════
    # B: Top Clienti/Fornitori (15 prompt)
    # ══════════════════════════════════════════════════════════
    add("B01", "Top", "top 5 clienti", 2024, [
        ("has_content", True), ("tool_used", "get_top_clients"), ("content_contains_any", ["NTT"]), ("has_content_blocks", True)])
    add("B02", "Top", "classifica fornitori 2024", 2024, [
        ("has_content", True), ("tool_used", "get_top_clients")])
    add("B03", "Top", "chi è il mio miglior cliente?", 2024, [
        ("has_content", True), ("tool_used", "get_top_clients")])
    add("B04", "Top", "top fornitori", 2024, [
        ("has_content", True), ("tool_used", "get_top_clients")])
    add("B05", "Top", "top 3 clienti 2024", 2024, [
        ("has_content", True), ("tool_used", "get_top_clients"), ("has_content_blocks", True)])
    add("B06", "Top", "top 10 clienti", 2024, [
        ("has_content", True), ("tool_used", "get_top_clients")])
    add("B07", "Top", "migliore cliente", 2024, [
        ("has_content", True), ("tool_used", "get_top_clients")])
    add("B08", "Top", "principale fornitore", 2024, [
        ("has_content", True), ("tool_used", "get_top_clients")])
    add("B09", "Top", "classifica clienti per fatturato", 2024, [
        ("has_content", True), ("tool_used", "get_top_clients")])
    add("B10", "Top", "top clienti 2023", 2024, [
        ("has_content", True), ("tool_used", "get_top_clients")])
    add("B11", "Top", "miglior cliente 2024", 2024, [
        ("has_content", True), ("tool_used", "get_top_clients")])
    add("B12", "Top", "top 5 fornitori 2024", 2024, [
        ("has_content", True), ("tool_used", "get_top_clients")])
    add("B13", "Top", "principali clienti", 2024, [
        ("has_content", True), ("tool_used", "get_top_clients")])
    add("B14", "Top", "migliori fornitori", 2024, [
        ("has_content", True), ("tool_used", "get_top_clients")])
    add("B15", "Top", "top clienti", 2024, [
        ("has_content", True), ("tool_used", "get_top_clients")])

    # ══════════════════════════════════════════════════════════
    # C: Ricerca Fatture (20 prompt)
    # ══════════════════════════════════════════════════════════
    add("C01", "Fatture", "fatture NTT Data", 2024, [
        ("has_content", True), ("content_not_contains", "Non ho capito"), ("content_contains_any", ["NTT", "199", "fattur"])])
    add("C02", "Fatture", "fattura numero 1/7", 2024, [
        ("has_content", True), ("tool_used", "get_invoice_detail")], page="fatture")
    add("C03", "Fatture", "quante fatture ricevute?", 2024, [
        ("has_content", True), ("tool_used", "count_invoices")])
    add("C04", "Fatture", "elenco fatture emesse", 2024, [
        ("has_content", True), ("tool_used", "list_invoices")])
    add("C05", "Fatture", "mostrami le fatture di gennaio 2024", 2024, [
        ("has_content", True), ("content_not_contains", "0 fatture")])
    add("C06", "Fatture", "quante fatture emesse nel 2024?", 2024, [
        ("has_content", True), ("tool_used", "count_invoices")])
    add("C07", "Fatture", "fatture Engineering", 2024, [
        ("has_content", True), ("content_contains_any", ["Engineering", "ENGINEERING"])])
    add("C08", "Fatture", "fatture Xister Reply", 2024, [
        ("has_content", True), ("content_contains_any", ["Xister", "XISTER"])])
    add("C09", "Fatture", "fatture Deloitte", 2024, [
        ("has_content", True), ("content_contains_any", ["Deloitte", "DELOITTE"])])
    add("C10", "Fatture", "fatture Nexa Data", 2024, [
        ("has_content", True), ("content_contains_any", ["Nexa", "NEXA"])])
    add("C11", "Fatture", "lista fatture marzo 2024", 2024, [
        ("has_content", True), ("tool_used", "list_invoices")])
    add("C12", "Fatture", "quante fatture ho?", 2024, [
        ("has_content", True), ("tool_used", "count_invoices")])
    add("C13", "Fatture", "fatture ricevute febbraio", 2024, [
        ("has_content", True)])
    add("C14", "Fatture", "numero fatture per mese", 2024, [
        ("has_content", True), ("tool_used_not", "direct_response")])
    add("C15", "Fatture", "fatture emesse a luglio", 2024, [
        ("has_content", True)])
    add("C16", "Fatture", "conta fatture passive", 2024, [
        ("has_content", True), ("tool_used", "count_invoices")])
    add("C17", "Fatture", "mostra fatture attive", 2024, [
        ("has_content", True), ("tool_used", "list_invoices")])
    add("C18", "Fatture", "fattura n. AQ01809969", 2024, [
        ("has_content", True), ("tool_used", "get_invoice_detail")])
    add("C19", "Fatture", "cerca fatture settembre 2024", 2024, [
        ("has_content", True)])
    add("C20", "Fatture", "quante fatture ci sono in totale?", 2024, [
        ("has_content", True), ("tool_used", "count_invoices")])

    # ══════════════════════════════════════════════════════════
    # D: Navigazione e Azioni (10 prompt)
    # ══════════════════════════════════════════════════════════
    add("D01", "Nav", "vai alle scadenze", 2024, [
        ("has_content", True), ("has_action_navigate", "/scadenze")])
    add("D02", "Nav", "apri le fatture", 2024, [
        ("has_content", True), ("has_action_navigate", "/fatture")])
    add("D03", "Nav", "portami alla dashboard", 2024, [
        ("has_content", True)], page="fatture")
    add("D04", "Nav", "vai alla contabilità", 2024, [
        ("has_content", True), ("has_action_navigate", "/contabilita")])
    add("D05", "Nav", "apri il cruscotto CEO", 2024, [
        ("has_content", True)])
    add("D06", "Nav", "mostrami il 2023", 2024, [
        ("has_content", True)])
    add("D07", "Nav", "vai alle spese", 2024, [
        ("has_content", True)])
    add("D08", "Nav", "apri i cespiti", 2024, [
        ("has_content", True)])
    add("D09", "Nav", "vai alle impostazioni", 2024, [
        ("has_content", True)])
    add("D10", "Nav", "apri la banca", 2024, [
        ("has_content", True)])

    # ══════════════════════════════════════════════════════════
    # E: Panoramica e Stato (10 prompt)
    # ══════════════════════════════════════════════════════════
    add("E01", "Panoramica", "situazione 2024", 2024, [
        ("has_content", True), ("content_not_contains", "Non ho capito"), ("has_content_blocks", True)])
    add("E02", "Panoramica", "come stanno le finanze?", 2024, [
        ("has_content", True), ("content_not_contains", "Non ho capito")])
    add("E03", "Panoramica", "panoramica", 2024, [
        ("has_content", True), ("content_not_contains", "Non ho capito")])
    add("E04", "Panoramica", "come va l'azienda?", 2024, [
        ("has_content", True), ("content_not_contains", "Non ho capito")])
    add("E05", "Panoramica", "riepilogo", 2024, [
        ("has_content", True), ("content_not_contains", "Non ho capito")])
    add("E06", "Panoramica", "come stiamo?", 2024, [
        ("has_content", True), ("content_not_contains", "Non ho capito")])
    add("E07", "Panoramica", "stato dell'azienda", 2024, [
        ("has_content", True), ("content_not_contains", "Non ho capito")])
    add("E08", "Panoramica", "situazione finanziaria", 2024, [
        ("has_content", True), ("content_not_contains", "Non ho capito")])
    add("E09", "Panoramica", "dammi un riepilogo del 2024", 2024, [
        ("has_content", True), ("content_not_contains", "Non ho capito")])
    add("E10", "Panoramica", "com'è la situazione?", 2024, [
        ("has_content", True), ("content_not_contains", "Non ho capito")])

    # ══════════════════════════════════════════════════════════
    # F: Contabilità e Registrazioni (10 prompt)
    # ══════════════════════════════════════════════════════════
    add("F01", "Contabilità", "prima nota", 2024, [
        ("has_content", True), ("tool_used", "get_journal_entries")])
    add("F02", "Contabilità", "ultime registrazioni contabili", 2024, [
        ("has_content", True), ("tool_used", "get_journal_entries")])
    add("F03", "Contabilità", "stato patrimoniale", 2024, [
        ("has_content", True), ("tool_used", "get_balance_sheet_summary")], page="contabilita")
    add("F04", "Contabilità", "bilancio", 2024, [
        ("has_content", True), ("tool_used", "get_balance_sheet_summary")])
    add("F05", "Contabilità", "cash flow", 2024, [
        ("has_content", True), ("tool_used", "predict_cashflow")])
    add("F06", "Contabilità", "flusso di cassa", 2024, [
        ("has_content", True), ("tool_used", "predict_cashflow")])
    add("F07", "Contabilità", "previsione cash flow", 2024, [
        ("has_content", True), ("tool_used", "predict_cashflow")])
    add("F08", "Contabilità", "note spese", 2024, [
        ("has_content", True), ("tool_used", "list_expenses")])
    add("F09", "Contabilità", "cespiti", 2024, [
        ("has_content", True), ("tool_used", "list_assets")])
    add("F10", "Contabilità", "beni strumentali", 2024, [
        ("has_content", True), ("tool_used", "list_assets")])

    # ══════════════════════════════════════════════════════════
    # G: Scadenze e Fisco (10 prompt)
    # ══════════════════════════════════════════════════════════
    add("G01", "Fisco", "prossime scadenze", 2024, [
        ("has_content", True), ("tool_used", "get_deadlines")])
    add("G02", "Fisco", "scadenze fiscali", 2024, [
        ("has_content", True), ("tool_used", "get_deadlines")])
    add("G03", "Fisco", "scadenze in ritardo", 2024, [
        ("has_content", True), ("tool_used", "get_fiscal_alerts")])
    add("G04", "Fisco", "alert fiscali", 2024, [
        ("has_content", True), ("tool_used", "get_fiscal_alerts")])
    add("G05", "Fisco", "ci sono scadenze scadute?", 2024, [
        ("has_content", True), ("tool_used", "get_fiscal_alerts")])
    add("G06", "Fisco", "fatture da verificare", 2024, [
        ("has_content", True), ("tool_used", "get_pending_review")])
    add("G07", "Fisco", "fatture in attesa di revisione", 2024, [
        ("has_content", True), ("tool_used", "get_pending_review")])
    add("G08", "Fisco", "stato cassetto fiscale", 2024, [
        ("has_content", True), ("tool_used", "sync_cassetto")])
    add("G09", "Fisco", "sincronizzazione cassetto", 2024, [
        ("has_content", True), ("tool_used", "sync_cassetto")])
    add("G10", "Fisco", "dashboard fatture", 2024, [
        ("has_content", True), ("tool_used", "get_dashboard_summary")])

    # ══════════════════════════════════════════════════════════
    # H: Edge Cases e Sicurezza (15 prompt)
    # ══════════════════════════════════════════════════════════
    add("H01", "Edge", "ciao", 2024, [
        ("has_content", True), ("content_contains_any", ["Ciao", "ciao", "aiutarti"])])
    add("H02", "Edge", "grazie", 2024, [
        ("has_content", True), ("content_contains_any", ["Prego", "prego"])])
    add("H03", "Edge", "cosa sai fare?", 2024, [
        ("has_content", True), ("content_not_contains", "Non ho capito")])
    add("H04", "Edge", "buongiorno", 2024, [
        ("has_content", True), ("content_contains_any", ["Ciao", "ciao", "aiutarti"])])
    add("H05", "Edge", "buonasera", 2024, [
        ("has_content", True), ("content_contains_any", ["Ciao", "ciao", "aiutarti"])])
    add("H06", "Edge", "<script>alert('xss')</script>", 2024, [
        ("has_content", True), ("content_not_contains", "<script>")])
    add("H07", "Edge", "fatturato 2030", 2024, [
        ("has_content", True), ("no_error", True)])
    add("H08", "Edge", "help", 2024, [
        ("has_content", True), ("content_not_contains", "Non ho capito")])
    add("H09", "Edge", "aiuto", 2024, [
        ("has_content", True), ("content_not_contains", "Non ho capito")])
    add("H10", "Edge", "come funziona?", 2024, [
        ("has_content", True), ("content_not_contains", "Non ho capito")])
    add("H11", "Edge", "' OR 1=1 --", 2024, [
        ("has_content", True), ("no_error", True)])
    add("H12", "Edge", "fatturato 2020", 2024, [
        ("has_content", True), ("no_error", True)])
    add("H13", "Edge", "a", 2024, [
        ("has_content", True)])
    add("H14", "Edge", "!@#$%^&*()", 2024, [
        ("has_content", True), ("no_error", True)])
    add("H15", "Edge", "fammi un caffè", 2024, [
        ("has_content", True)])

    # ══════════════════════════════════════════════════════════
    # I: Context-Aware / Pagine diverse (10 prompt)
    # ══════════════════════════════════════════════════════════
    add("I01", "Context", "fatturato", 2024, [
        ("has_content", True), ("tool_used", "get_period_stats")])
    add("I02", "Context", "fatturato", 2023, [
        ("has_content", True), ("tool_used", "get_period_stats")])
    add("I03", "Context", "quante fatture?", 2024, [
        ("has_content", True), ("tool_used", "count_invoices")], page="fatture")
    add("I04", "Context", "quante fatture?", 2024, [
        ("has_content", True), ("tool_used", "count_invoices")], page="dashboard")
    add("I05", "Context", "ebitda", 2024, [
        ("has_content", True), ("tool_used", "get_period_stats")], page="ceo")
    add("I06", "Context", "stato patrimoniale", 2024, [
        ("has_content", True), ("tool_used", "get_balance_sheet_summary")], page="contabilita")
    add("I07", "Context", "top clienti", 2024, [
        ("has_content", True), ("tool_used", "get_top_clients")])
    add("I08", "Context", "top clienti", 2023, [
        ("has_content", True), ("tool_used", "get_top_clients")])
    add("I09", "Context", "fatturato gennaio", 2024, [
        ("has_content", True), ("tool_used", "get_period_stats")])
    add("I10", "Context", "fatturato gennaio", 2023, [
        ("has_content", True), ("tool_used", "get_period_stats")])

    return prompts


def _run_check(check: tuple, result: dict) -> tuple[bool, str]:
    """Run a single check. Returns (passed, detail)."""
    check_type, expected = check[0], check[1]
    content = result.get("content", "")
    meta = result.get("response_meta", {}) or {}
    tool_calls = result.get("tool_calls", []) or []

    if check_type == "has_content":
        ok = bool(content and len(content) > 5)
        return ok, f"len={len(content)}"
    if check_type == "content_contains_any":
        found = any(kw in content for kw in expected)
        return found, f"keywords={expected}"
    if check_type == "content_not_contains":
        ok = expected not in content
        return ok, f"'{expected}' in content={not ok}"
    if check_type == "tool_used":
        tools = [tc.get("tool", "") for tc in tool_calls]
        ok = expected in tools
        return ok, f"want={expected}, got={tools}"
    if check_type == "tool_used_not":
        tools = [tc.get("tool", "") for tc in tool_calls]
        ok = expected not in tools
        return ok, f"should_not={expected}, got={tools}"
    if check_type == "has_content_blocks":
        blocks = meta.get("content_blocks", [])
        ok = len(blocks) > 0
        return ok, f"blocks={len(blocks)}"
    if check_type == "has_action_set_year":
        actions = meta.get("actions", [])
        ok = any(a.get("type") == "set_year" and a.get("value") == expected for a in actions)
        return ok, f"set_year={expected}"
    if check_type == "has_action_navigate":
        all_actions = meta.get("actions", []) + meta.get("suggested_actions", [])
        ok = any(a.get("type") == "navigate" and expected in a.get("path", "") for a in all_actions)
        return ok, f"navigate to {expected}"
    if check_type == "no_error":
        ok = "error" not in content.lower() and "errore" not in content.lower() and "traceback" not in content.lower()
        return ok, "no errors"
    return False, f"unknown: {check_type}"


async def run_chatbot_test_suite(
    db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID,
) -> dict:
    """Run full test suite. Returns report with scores, timing, failures."""

    expected = await _get_expected_data(db, tenant_id)
    prompts = _build_prompts()

    results = []
    total_pass = total_fail = total_time = 0
    category_stats: dict[str, dict] = {}

    for test in prompts:
        cat = test["category"]
        if cat not in category_stats:
            category_stats[cat] = {"pass": 0, "fail": 0, "time": 0}

        t0 = time.time()
        try:
            result = await run_orchestrator(
                user_message=test["prompt"],
                tenant_id=tenant_id, user_id=user_id, db=db,
                context=test.get("context"),
            )
            elapsed = round((time.time() - t0) * 1000)
            total_time += elapsed
            category_stats[cat]["time"] += elapsed

            check_results = []
            all_passed = True
            for check in test["checks"]:
                passed, detail = _run_check(check, result)
                check_results.append({"check": check[0], "expected": str(check[1]), "passed": passed, "detail": detail})
                if not passed:
                    all_passed = False

            verdict = "PASS" if all_passed else "FAIL"
            if all_passed:
                total_pass += 1
                category_stats[cat]["pass"] += 1
            else:
                total_fail += 1
                category_stats[cat]["fail"] += 1

            results.append({
                "id": test["id"], "category": cat, "prompt": test["prompt"],
                "verdict": verdict, "time_ms": elapsed,
                "content_preview": (result.get("content", "") or "")[:200],
                "tool_calls": [tc.get("tool", "") for tc in (result.get("tool_calls") or [])],
                "has_blocks": bool((result.get("response_meta") or {}).get("content_blocks")),
                "checks": check_results,
            })

        except Exception as e:
            elapsed = round((time.time() - t0) * 1000)
            total_time += elapsed
            total_fail += 1
            category_stats[cat]["fail"] += 1
            results.append({
                "id": test["id"], "category": cat, "prompt": test["prompt"],
                "verdict": "ERROR", "time_ms": elapsed, "error": str(e)[:300], "checks": [],
            })

    total = len(prompts)
    score = round(total_pass / total * 100, 1) if total > 0 else 0

    # Category summary
    cat_summary = {}
    for cat, stats in category_stats.items():
        t = stats["pass"] + stats["fail"]
        cat_summary[cat] = {
            "total": t, "pass": stats["pass"], "fail": stats["fail"],
            "score": f"{round(stats['pass']/t*100, 1)}%" if t > 0 else "0%",
            "avg_ms": round(stats["time"] / t) if t > 0 else 0,
        }

    return {
        "summary": {
            "total": total, "pass": total_pass, "fail": total_fail,
            "score": f"{score}%",
            "avg_time_ms": round(total_time / total) if total > 0 else 0,
            "total_time_ms": total_time,
        },
        "categories": cat_summary,
        "expected_data": {
            "fatturato_2024": expected.get("fatturato_2024"),
            "costi_2024": expected.get("costi_2024"),
            "ebitda_2024": expected.get("ebitda_2024"),
            "count_emesse_2024": expected.get("count_emesse_2024"),
            "count_ricevute_2024": expected.get("count_ricevute_2024"),
            "top_client": expected.get("top_client"),
            "ntt_count": expected.get("ntt_count"),
        },
        "results": results,
    }
