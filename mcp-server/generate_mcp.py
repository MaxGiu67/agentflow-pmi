#!/usr/bin/env python3
"""Auto-generate MCP server from AgentFlow SQLAlchemy models and FastAPI routers.

This script reads the codebase and generates an up-to-date MCP server.
Run it whenever you add/change endpoints or DB models:

    python3 mcp-server/generate_mcp.py

It generates: mcp-server/server.py
"""

import ast
import os
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
API_DIR = PROJECT_ROOT / "api"
MODELS_FILE = API_DIR / "db" / "models.py"
MODULES_DIR = API_DIR / "modules"
OUTPUT_FILE = Path(__file__).parent / "server.py"


def extract_models(filepath: Path) -> list[dict]:
    """Extract SQLAlchemy model names and their __tablename__ from models.py."""
    source = filepath.read_text()
    tree = ast.parse(source)
    models = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            # Check if inherits from Base
            bases = [b.id if isinstance(b, ast.Name) else "" for b in node.bases]
            if "Base" not in bases:
                continue

            tablename = None
            columns = []
            for item in node.body:
                # Find __tablename__
                if isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name) and target.id == "__tablename__":
                            if isinstance(item.value, ast.Constant):
                                tablename = item.value.value

                # Find Column() definitions
                if isinstance(item, ast.Assign) and item.targets:
                    target = item.targets[0]
                    if isinstance(target, ast.Name):
                        col_name = target.id
                        if col_name.startswith("_"):
                            continue
                        columns.append(col_name)

            if tablename:
                models.append({
                    "class_name": node.name,
                    "table_name": tablename,
                    "columns": columns,
                })

    return models


def extract_endpoints(modules_dir: Path) -> list[dict]:
    """Extract FastAPI endpoints from router files."""
    endpoints = []

    for router_file in sorted(modules_dir.glob("*/router.py")):
        module_name = router_file.parent.name
        source = router_file.read_text()

        # Find prefix
        prefix_match = re.search(r'prefix="([^"]+)"', source)
        prefix = prefix_match.group(1) if prefix_match else f"/{module_name}"

        # Find route decorators
        for match in re.finditer(
            r'@router\.(get|post|put|delete|patch)\(\s*"([^"]*)"',
            source,
        ):
            method = match.group(1).upper()
            path = match.group(2)

            # Find the function name (next def after decorator)
            pos = match.end()
            func_match = re.search(r'(?:async\s+)?def\s+(\w+)', source[pos:pos + 200])
            func_name = func_match.group(1) if func_match else "unknown"

            # Find docstring
            if func_match:
                doc_start = pos + func_match.end()
                doc_match = re.search(r'"""(.*?)"""', source[doc_start:doc_start + 500], re.DOTALL)
                docstring = doc_match.group(1).strip().split("\n")[0] if doc_match else ""
            else:
                docstring = ""

            full_path = f"/api/v1{prefix}{path}"
            endpoints.append({
                "module": module_name,
                "method": method,
                "path": full_path,
                "function": func_name,
                "description": docstring[:100],
            })

    return endpoints


def generate_server(models: list[dict], endpoints: list[dict]) -> str:
    """Generate the MCP server.py content."""

    # Group endpoints by module
    modules = {}
    for ep in endpoints:
        mod = ep["module"]
        if mod not in modules:
            modules[mod] = []
        modules[mod].append(ep)

    # Build table list for the DB tool
    table_names = [m["table_name"] for m in models]

    # Build endpoint catalog
    endpoint_lines = []
    for ep in endpoints:
        endpoint_lines.append(
            f'    {{"module": "{ep["module"]}", "method": "{ep["method"]}", '
            f'"path": "{ep["path"]}", "description": "{ep["description"]}"}},'
        )

    import json as _json
    tables_json = _json.dumps(table_names)

    return f'''"""AgentFlow MCP Server — AUTO-GENERATED from codebase.

DO NOT EDIT MANUALLY. Regenerate with:
    python3 mcp-server/generate_mcp.py

Generated from:
- {len(models)} SQLAlchemy models ({len(table_names)} tables)
- {len(endpoints)} FastAPI endpoints across {len(modules)} modules
"""

import json
import os
from datetime import date

import httpx
import psycopg2
import psycopg2.extras
from mcp.server.fastmcp import FastMCP

# ── Config ──────────────────────────────────────────
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://contabot:contabot@localhost:5432/contabot",
)
API_URL = os.environ.get("API_URL", "http://localhost:8000")
API_TOKEN = os.environ.get("API_TOKEN", "")

mcp = FastMCP("AgentFlow DB")

# ── Auto-generated metadata ─────────────────────────
TABLES = {tables_json}

ENDPOINTS = [
{chr(10).join(endpoint_lines)}
]


def _get_conn():
    url = DATABASE_URL
    if "+asyncpg" in url:
        url = url.replace("+asyncpg", "")
    return psycopg2.connect(url)


def _query(sql: str, params: dict | None = None, limit: int = 50) -> list[dict]:
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params or {{}})
            rows = cur.fetchmany(limit)
            return [dict(r) for r in rows]
    finally:
        conn.close()


def _scalar(sql: str, params: dict | None = None):
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or {{}})
            row = cur.fetchone()
            return row[0] if row else None
    finally:
        conn.close()


# ============================================================
# Database exploration
# ============================================================


@mcp.tool()
def list_tables() -> str:
    """List all {len(table_names)} tables in AgentFlow DB with row counts."""
    rows = _query(
        """
        SELECT tablename,
               (SELECT COUNT(*) FROM information_schema.columns c
                WHERE c.table_name = t.tablename AND c.table_schema = 'public') AS num_columns,
               pg_stat_get_tuples_inserted(c.oid) AS approx_rows
        FROM pg_tables t
        JOIN pg_class c ON c.relname = t.tablename
        WHERE schemaname = 'public'
        ORDER BY tablename
        """
    )
    return json.dumps(rows, default=str, indent=2)


@mcp.tool()
def describe_table(table_name: str) -> str:
    """Show columns, types, and constraints for a table. Tables: {', '.join(table_names[:10])}..."""
    if table_name not in TABLES:
        return f"Table '{{table_name}}' not found. Available: {{', '.join(sorted(TABLES))}}"
    rows = _query(
        """
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %(t)s
        ORDER BY ordinal_position
        """,
        {{"t": table_name}},
    )
    return json.dumps(rows, default=str, indent=2)


@mcp.tool()
def run_query(sql: str, limit: int = 50) -> str:
    """Execute a READ-ONLY SQL query (SELECT/WITH only). Max {{limit}} rows."""
    sql_stripped = sql.strip().upper()
    if not sql_stripped.startswith("SELECT") and not sql_stripped.startswith("WITH"):
        return "ERROR: Only SELECT/WITH queries allowed."
    rows = _query(sql, limit=limit)
    return json.dumps(rows, default=str, indent=2)


@mcp.tool()
def sample_rows(table_name: str, limit: int = 5) -> str:
    """Get sample rows from any table. Useful for understanding data structure."""
    if table_name not in TABLES:
        return f"Table '{{table_name}}' not found."
    rows = _query(f"SELECT * FROM {{table_name}} ORDER BY created_at DESC NULLS LAST LIMIT %(lim)s", {{"lim": limit}}, limit=limit)
    return json.dumps(rows, default=str, indent=2)


# ============================================================
# Invoice tools
# ============================================================


@mcp.tool()
def count_invoices(
    year: int | None = None,
    month: int | None = None,
    invoice_type: str | None = None,
    search: str | None = None,
) -> str:
    """Count invoices. type: 'attiva' (emesse) or 'passiva' (ricevute). search: name/number."""
    conditions = ["1=1"]
    params: dict = {{}}
    if year:
        conditions.append("EXTRACT(YEAR FROM data_fattura) = %(yr)s")
        params["yr"] = year
    if month and year:
        conditions.append("EXTRACT(MONTH FROM data_fattura) = %(m)s")
        params["m"] = month
    if invoice_type:
        conditions.append("type = %(tp)s")
        params["tp"] = invoice_type
    if search:
        conditions.append(
            "(emittente_nome ILIKE %(q)s OR numero_fattura ILIKE %(q)s "
            "OR structured_data->>'destinatario_nome' ILIKE %(q)s)"
        )
        params["q"] = f"%{{search}}%"
    where = " AND ".join(conditions)
    rows = _query(
        f"SELECT type, COUNT(*) AS num, COALESCE(SUM(importo_totale), 0) AS totale "
        f"FROM invoices WHERE {{where}} GROUP BY type ORDER BY type",
        params,
    )
    total = sum(int(r["num"]) for r in rows)
    return json.dumps({{"count": total, "by_type": rows}}, default=str, indent=2)


@mcp.tool()
def list_invoices(
    year: int | None = None,
    month: int | None = None,
    invoice_type: str | None = None,
    search: str | None = None,
    limit: int = 20,
) -> str:
    """List invoices with details. type: 'attiva'/'passiva'. search: name/number."""
    conditions = ["1=1"]
    params: dict = {{"lim": limit}}
    if year:
        conditions.append("EXTRACT(YEAR FROM data_fattura) = %(yr)s")
        params["yr"] = year
    if month and year:
        conditions.append("EXTRACT(MONTH FROM data_fattura) = %(m)s")
        params["m"] = month
    if invoice_type:
        conditions.append("type = %(tp)s")
        params["tp"] = invoice_type
    if search:
        conditions.append(
            "(emittente_nome ILIKE %(q)s OR numero_fattura ILIKE %(q)s "
            "OR structured_data->>'destinatario_nome' ILIKE %(q)s)"
        )
        params["q"] = f"%{{search}}%"
    where = " AND ".join(conditions)
    rows = _query(
        f"SELECT numero_fattura, emittente_nome, "
        f"structured_data->>'destinatario_nome' AS destinatario, "
        f"data_fattura, importo_totale, type, processing_status "
        f"FROM invoices WHERE {{where}} ORDER BY data_fattura DESC NULLS LAST LIMIT %(lim)s",
        params, limit=limit,
    )
    return json.dumps(rows, default=str, indent=2)


@mcp.tool()
def monthly_stats(year: int = 2024) -> str:
    """Monthly fatturato breakdown: emesse vs ricevute per month."""
    rows = _query(
        "SELECT EXTRACT(MONTH FROM data_fattura)::int AS mese, type, "
        "COUNT(*) AS num_fatture, COALESCE(SUM(importo_totale), 0) AS totale "
        "FROM invoices WHERE EXTRACT(YEAR FROM data_fattura) = %(yr)s "
        "GROUP BY mese, type ORDER BY mese, type",
        {{"yr": year}}, limit=50,
    )
    return json.dumps(rows, default=str, indent=2)


@mcp.tool()
def kpi_summary(year: int = 2024) -> str:
    """KPI: fatturato, costi, EBITDA, counts for a year."""
    rows = _query(
        "SELECT type, COUNT(*) AS num_fatture, COALESCE(SUM(importo_totale), 0) AS totale "
        "FROM invoices WHERE EXTRACT(YEAR FROM data_fattura) = %(yr)s GROUP BY type",
        {{"yr": year}},
    )
    result = {{"year": year, "fatturato": 0, "costi": 0, "fatture_emesse": 0, "fatture_ricevute": 0}}
    for r in rows:
        if r["type"] == "attiva":
            result["fatturato"] = float(r["totale"])
            result["fatture_emesse"] = int(r["num_fatture"])
        elif r["type"] == "passiva":
            result["costi"] = float(r["totale"])
            result["fatture_ricevute"] = int(r["num_fatture"])
    result["ebitda"] = round(result["fatturato"] - result["costi"], 2)
    return json.dumps(result, default=str, indent=2)


@mcp.tool()
def quarter_stats(year: int = 2024, quarter: int = 1) -> str:
    """Stats for a quarter (1-4): fatturato, costi, EBITDA with monthly detail."""
    ms = (quarter - 1) * 3 + 1
    me = ms + 2
    rows = _query(
        "SELECT EXTRACT(MONTH FROM data_fattura)::int AS mese, type, "
        "COUNT(*) AS num_fatture, COALESCE(SUM(importo_totale), 0) AS totale "
        "FROM invoices WHERE EXTRACT(YEAR FROM data_fattura) = %(yr)s "
        "AND EXTRACT(MONTH FROM data_fattura) BETWEEN %(ms)s AND %(me)s "
        "GROUP BY mese, type ORDER BY mese, type",
        {{"yr": year, "ms": ms, "me": me}}, limit=50,
    )
    te = sum(float(r["totale"]) for r in rows if r["type"] == "attiva")
    tr = sum(float(r["totale"]) for r in rows if r["type"] == "passiva")
    return json.dumps({{
        "year": year, "quarter": quarter, "months": f"{{ms}}-{{me}}",
        "fatturato": round(te, 2), "costi": round(tr, 2), "ebitda": round(te - tr, 2),
        "detail": rows,
    }}, default=str, indent=2)


@mcp.tool()
def top_clients(year: int = 2024, limit: int = 10) -> str:
    """Top clients by revenue (fatture emesse)."""
    rows = _query(
        "SELECT structured_data->>'destinatario_nome' AS cliente, "
        "COUNT(*) AS num_fatture, COALESCE(SUM(importo_totale), 0) AS totale "
        "FROM invoices WHERE type = 'attiva' AND EXTRACT(YEAR FROM data_fattura) = %(yr)s "
        "AND structured_data->>'destinatario_nome' IS NOT NULL "
        "GROUP BY structured_data->>'destinatario_nome' ORDER BY totale DESC LIMIT %(lim)s",
        {{"yr": year, "lim": limit}}, limit=limit,
    )
    return json.dumps(rows, default=str, indent=2)


@mcp.tool()
def top_suppliers(year: int = 2024, limit: int = 10) -> str:
    """Top suppliers by cost (fatture ricevute)."""
    rows = _query(
        "SELECT emittente_nome AS fornitore, COUNT(*) AS num_fatture, "
        "COALESCE(SUM(importo_totale), 0) AS totale "
        "FROM invoices WHERE type = 'passiva' AND EXTRACT(YEAR FROM data_fattura) = %(yr)s "
        "AND emittente_nome IS NOT NULL AND emittente_nome != '' "
        "GROUP BY emittente_nome ORDER BY totale DESC LIMIT %(lim)s",
        {{"yr": year, "lim": limit}}, limit=limit,
    )
    return json.dumps(rows, default=str, indent=2)


# ============================================================
# API endpoint catalog
# ============================================================


@mcp.tool()
def list_endpoints(module: str | None = None) -> str:
    """List all {len(endpoints)} API endpoints. Filter by module name optionally."""
    filtered = ENDPOINTS
    if module:
        filtered = [e for e in ENDPOINTS if e["module"] == module]
    return json.dumps(filtered, indent=2)


@mcp.tool()
def list_modules() -> str:
    """List all {len(modules)} API modules with endpoint count."""
    mods = {{}}
    for ep in ENDPOINTS:
        m = ep["module"]
        mods[m] = mods.get(m, 0) + 1
    return json.dumps(dict(sorted(mods.items())), indent=2)


# ============================================================
# Chatbot testing
# ============================================================


@mcp.tool()
def test_chatbot(prompt: str, year: int = 2024, page: str = "dashboard") -> str:
    """Send a prompt to the AgentFlow chatbot and return the full response.

    Args:
        prompt: Message (e.g. "fatturato 2024", "top 5 clienti")
        year: Simulated dashboard year
        page: Simulated current page
    """
    if not API_TOKEN:
        return "ERROR: Call get_api_token() first."
    headers = {{"Authorization": f"Bearer {{API_TOKEN}}", "Content-Type": "application/json"}}
    payload = {{"message": prompt, "conversation_id": None, "context": {{"page": page, "year": year}}}}
    try:
        resp = httpx.post(f"{{API_URL}}/api/v1/chat/send", json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        d = resp.json()
        return json.dumps({{
            "content": d.get("content", "")[:500],
            "agent_name": d.get("agent_name"),
            "tool_calls": d.get("tool_calls"),
            "response_meta": d.get("response_meta"),
        }}, default=str, indent=2, ensure_ascii=False)
    except Exception as e:
        return f"Error: {{e}}"


@mcp.tool()
def get_api_token(email: str = "mgiurelli@taal.it", password: str = "TestPass1") -> str:
    """Login and store JWT token for chatbot testing."""
    global API_TOKEN
    try:
        resp = httpx.post(f"{{API_URL}}/api/v1/auth/login", json={{"email": email, "password": password}}, timeout=15)
        resp.raise_for_status()
        API_TOKEN = resp.json().get("access_token", "")
        return f"Token obtained ({{len(API_TOKEN)}} chars). Ready for test_chatbot()."
    except Exception as e:
        return f"Login failed: {{e}}"


# ============================================================
# Data validation
# ============================================================


@mcp.tool()
def validate_data() -> str:
    """Check data integrity: counts by year/type, nulls, status distribution."""
    checks = {{}}
    checks["by_year_type"] = _query(
        "SELECT EXTRACT(YEAR FROM data_fattura)::int AS anno, type, COUNT(*) AS num, "
        "COALESCE(SUM(importo_totale), 0) AS totale FROM invoices "
        "WHERE data_fattura IS NOT NULL GROUP BY anno, type ORDER BY anno DESC, type",
        limit=50,
    )
    checks["null_dates"] = _scalar("SELECT COUNT(*) FROM invoices WHERE data_fattura IS NULL")
    checks["null_amounts"] = _scalar("SELECT COUNT(*) FROM invoices WHERE importo_totale IS NULL")
    checks["status"] = _query(
        "SELECT processing_status, COUNT(*) AS num FROM invoices GROUP BY processing_status ORDER BY num DESC",
        limit=20,
    )
    checks["tenants"] = _query("SELECT id, name, piva FROM tenants", limit=10)
    return json.dumps(checks, default=str, indent=2)


if __name__ == "__main__":
    mcp.run()
'''


def main():
    print(f"Scanning models from {MODELS_FILE}...")
    models = extract_models(MODELS_FILE)
    print(f"  Found {len(models)} models")

    print(f"Scanning endpoints from {MODULES_DIR}...")
    endpoints = extract_endpoints(MODULES_DIR)
    print(f"  Found {len(endpoints)} endpoints across {len(set(e['module'] for e in endpoints))} modules")

    print(f"Generating {OUTPUT_FILE}...")
    content = generate_server(models, endpoints)
    OUTPUT_FILE.write_text(content)
    print(f"  Written {len(content)} bytes")

    print("\nDone! MCP server regenerated.")
    print("Restart Claude Code to pick up changes.")


if __name__ == "__main__":
    main()
