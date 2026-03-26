"""AgentFlow MCP Server — AUTO-GENERATED from codebase.

DO NOT EDIT MANUALLY. Regenerate with:
    python3 mcp-server/generate_mcp.py

Generated from:
- 36 SQLAlchemy models (36 tables)
- 111 FastAPI endpoints across 29 modules
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
TABLES = ["tenants", "users", "invoices", "agent_events", "categorization_feedback", "journal_entries", "journal_lines", "onboarding_states", "fiscal_rules", "chart_accounts", "notification_configs", "notification_logs", "email_connections", "active_invoices", "bank_accounts", "bank_transactions", "vat_settlements", "fiscal_deadlines", "withholding_taxes", "reconciliations", "stamp_duties", "expenses", "expense_policies", "assets", "accruals", "certificazioni_uniche", "digital_preservations", "payments", "normative_alerts", "f24_documents", "budgets", "dashboard_layouts", "conversations", "messages", "agent_configs", "conversation_memories"]

ENDPOINTS = [
    {"module": "accounting", "method": "GET", "path": "/api/v1/accounting/chart", "description": "Get existing chart of accounts for the tenant."},
    {"module": "accounting", "method": "GET", "path": "/api/v1/accounting/balance-sheet", "description": "Generate Bilancio CEE for a given year (US-23)."},
    {"module": "accounting", "method": "POST", "path": "/api/v1/accounting/chart", "description": "Create chart of accounts on Odoo for the tenant."},
    {"module": "active_invoices", "method": "POST", "path": "/api/v1/invoices/active", "description": "Create a new active invoice (fattura attiva)."},
    {"module": "active_invoices", "method": "POST", "path": "/api/v1/invoices/active/{invoice_id}/send", "description": "Send an active invoice to SDI via A-Cube."},
    {"module": "active_invoices", "method": "GET", "path": "/api/v1/invoices/active/{invoice_id}/status", "description": "Get SDI delivery status for an active invoice."},
    {"module": "active_invoices", "method": "GET", "path": "/api/v1/invoices/active", "description": "List all active invoices for the tenant."},
    {"module": "agent_config", "method": "GET", "path": "/api/v1/agents/config", "description": "List all agent configurations for current tenant."},
    {"module": "agent_config", "method": "PATCH", "path": "/api/v1/agents/config/{agent_type}", "description": "Update a specific agent configuration."},
    {"module": "agent_config", "method": "POST", "path": "/api/v1/agents/config/reset", "description": "Reset all agent configurations to defaults."},
    {"module": "agent_config", "method": "GET", "path": "/api/v1/agents/llm-settings", "description": "Get current LLM provider/model and available options."},
    {"module": "agent_config", "method": "PATCH", "path": "/api/v1/agents/llm-settings", "description": "Update LLM provider and model preference."},
    {"module": "assets", "method": "POST", "path": "/api/v1/assets", "description": "Create a fixed asset."},
    {"module": "assets", "method": "GET", "path": "/api/v1/assets", "description": "AC-32.1: List all assets (registro cespiti)."},
    {"module": "assets", "method": "GET", "path": "/api/v1/assets/{asset_id}", "description": "Get single asset detail."},
    {"module": "assets", "method": "POST", "path": "/api/v1/assets/{asset_id}/dispose", "description": "Dispose of an asset."},
    {"module": "assets", "method": "POST", "path": "/api/v1/assets/depreciation/run", "description": "AC-31.2: Run annual depreciation for all active assets."},
    {"module": "auth", "method": "POST", "path": "/api/v1/auth/register", "description": ""},
    {"module": "auth", "method": "POST", "path": "/api/v1/auth/login", "description": ""},
    {"module": "auth", "method": "POST", "path": "/api/v1/auth/token", "description": ""},
    {"module": "auth", "method": "POST", "path": "/api/v1/auth/verify-email", "description": ""},
    {"module": "auth", "method": "POST", "path": "/api/v1/auth/password-reset", "description": ""},
    {"module": "auth", "method": "POST", "path": "/api/v1/auth/password-reset/confirm", "description": ""},
    {"module": "banking", "method": "POST", "path": "/api/v1/bank-accounts/connect-session", "description": "Create a Salt Edge connect session — returns URL to authenticate with bank."},
    {"module": "banking", "method": "POST", "path": "/api/v1/bank-accounts/connect", "description": "Connect a bank account via Open Banking SCA flow."},
    {"module": "banking", "method": "GET", "path": "/api/v1/bank-accounts", "description": "List all connected bank accounts."},
    {"module": "banking", "method": "GET", "path": "/api/v1/bank-accounts/{account_id}/balance", "description": "Get balance for a connected bank account."},
    {"module": "banking", "method": "GET", "path": "/api/v1/bank-accounts/{account_id}/transactions", "description": "Get transactions for a connected bank account."},
    {"module": "banking", "method": "POST", "path": "/api/v1/bank-accounts/{account_id}/sync", "description": "Sync transactions for a connected bank account."},
    {"module": "banking", "method": "POST", "path": "/api/v1/bank-accounts/{account_id}/revoke", "description": "Revoke PSD2 consent for a connected bank account."},
    {"module": "cashflow", "method": "GET", "path": "/api/v1/cashflow/prediction", "description": "Get cash flow prediction for the next N days."},
    {"module": "cashflow", "method": "GET", "path": "/api/v1/cashflow/alerts", "description": ""},
    {"module": "ceo", "method": "GET", "path": "/api/v1/ceo/dashboard", "description": "Get CEO Dashboard KPIs."},
    {"module": "ceo", "method": "GET", "path": "/api/v1/ceo/dashboard/yoy", "description": "Year-over-year comparison."},
    {"module": "ceo", "method": "GET", "path": "/api/v1/ceo/alerts", "description": "Get CEO alerts."},
    {"module": "ceo", "method": "GET", "path": "/api/v1/ceo/budget", "description": "Get budget vs consuntivo for a year."},
    {"module": "ceo", "method": "POST", "path": "/api/v1/ceo/budget", "description": "Create/update budget entries."},
    {"module": "ceo", "method": "GET", "path": "/api/v1/ceo/budget/projection", "description": "Get end-of-year projection with moving average."},
    {"module": "chat", "method": "POST", "path": "/api/v1/chat/send", "description": "Send a message and get an AI response."},
    {"module": "chat", "method": "GET", "path": "/api/v1/chat/conversations", "description": "List user's conversations."},
    {"module": "chat", "method": "GET", "path": "/api/v1/chat/conversations/{conversation_id}", "description": "Get conversation detail with all messages."},
    {"module": "chat", "method": "DELETE", "path": "/api/v1/chat/conversations/{conversation_id}", "description": "Soft delete a conversation."},
    {"module": "chat", "method": "POST", "path": "/api/v1/chat/conversations/new", "description": "Create a new empty conversation."},
    {"module": "chat", "method": "GET", "path": "/api/v1/chat/memory", "description": "Get user's conversation memories."},
    {"module": "chat", "method": "DELETE", "path": "/api/v1/chat/memory", "description": "Clear all conversation memories for the current user."},
    {"module": "cu", "method": "GET", "path": "/api/v1/cu", "description": "List all CU records for a given year."},
    {"module": "cu", "method": "POST", "path": "/api/v1/cu/generate/{year}", "description": "Generate CU for all professionals paid in the given year."},
    {"module": "cu", "method": "GET", "path": "/api/v1/cu/{cu_id}/export", "description": "Export a CU record in CSV or telematico format."},
    {"module": "dashboard", "method": "GET", "path": "/api/v1/dashboard/dashboard/summary", "description": "Get complete dashboard summary with counters, recent invoices, and agent status."},
    {"module": "dashboard", "method": "GET", "path": "/api/v1/dashboard/dashboard/yearly-stats", "description": "Get yearly statistics: totals, monthly breakdown, top clients/suppliers."},
    {"module": "dashboard", "method": "GET", "path": "/api/v1/dashboard/agents/status", "description": "Get status of all agents."},
    {"module": "deadlines", "method": "GET", "path": "/api/v1/deadlines/deadlines", "description": "Get fiscal deadlines based on tenant regime."},
    {"module": "deadlines", "method": "GET", "path": "/api/v1/deadlines/deadlines/alerts", "description": "Get personalized fiscal alerts with estimated amounts (US-20)."},
    {"module": "email_connector", "method": "POST", "path": "/api/v1/email_connector/email/connect/gmail", "description": "Initiate Gmail OAuth connection flow."},
    {"module": "email_connector", "method": "POST", "path": "/api/v1/email_connector/email/connect/imap", "description": "Connect PEC/IMAP email account."},
    {"module": "email_connector", "method": "GET", "path": "/api/v1/email_connector/email/status", "description": "Get email connection status."},
    {"module": "expenses", "method": "POST", "path": "/api/v1/expenses", "description": "Create an expense entry."},
    {"module": "expenses", "method": "GET", "path": "/api/v1/expenses", "description": "List all expenses for tenant."},
    {"module": "expenses", "method": "PATCH", "path": "/api/v1/expenses/{expense_id}/approve", "description": "Approve an expense."},
    {"module": "expenses", "method": "PATCH", "path": "/api/v1/expenses/{expense_id}/reject", "description": "Reject an expense with motivation."},
    {"module": "expenses", "method": "POST", "path": "/api/v1/expenses/{expense_id}/reimburse", "description": "Reimburse an approved expense."},
    {"module": "f24", "method": "POST", "path": "/api/v1/f24/generate", "description": "Generate F24 for a period — aggregates IVA + ritenute + bollo."},
    {"module": "f24", "method": "GET", "path": "/api/v1/f24", "description": "List all F24 documents."},
    {"module": "f24", "method": "GET", "path": "/api/v1/f24/{f24_id}", "description": "Get F24 detail with sections."},
    {"module": "f24", "method": "GET", "path": "/api/v1/f24/{f24_id}/export", "description": "Export F24 in PDF or telematico format."},
    {"module": "f24", "method": "PATCH", "path": "/api/v1/f24/{f24_id}/mark-paid", "description": "Mark F24 as paid."},
    {"module": "fiscal", "method": "GET", "path": "/api/v1/fiscal/rules", "description": "List all fiscal rules, optionally filtered by key pattern."},
    {"module": "fiscal", "method": "GET", "path": "/api/v1/fiscal/vat-settlement", "description": "Get existing VAT settlement for a given quarter."},
    {"module": "fiscal", "method": "POST", "path": "/api/v1/fiscal/vat-settlement/compute", "description": "Compute (or recompute) quarterly VAT settlement."},
    {"module": "fiscal", "method": "POST", "path": "/api/v1/fiscal/stamp-duties/check", "description": "Check if an invoice requires stamp duty."},
    {"module": "fiscal", "method": "GET", "path": "/api/v1/fiscal/stamp-duties", "description": "Get quarterly stamp duty summary."},
    {"module": "fiscal", "method": "POST", "path": "/api/v1/fiscal/accruals/propose", "description": "Propose an accrual/deferral."},
    {"module": "fiscal", "method": "GET", "path": "/api/v1/fiscal/accruals", "description": "List accruals for tenant."},
    {"module": "fiscal", "method": "PATCH", "path": "/api/v1/fiscal/accruals/{accrual_id}/confirm", "description": "AC-36.2: Confirm accrual -> generate adjustment and reversal entries."},
    {"module": "invoices", "method": "POST", "path": "/api/v1/invoices/cassetto/sync", "description": "Force sync invoices from cassetto fiscale."},
    {"module": "invoices", "method": "GET", "path": "/api/v1/invoices/cassetto/sync/status", "description": "Get sync status information."},
    {"module": "invoices", "method": "GET", "path": "/api/v1/invoices/invoices", "description": "List invoices with filters and pagination."},
    {"module": "invoices", "method": "GET", "path": "/api/v1/invoices/invoices/pending-review", "description": "List invoices that need category review (categorized but not verified)."},
    {"module": "invoices", "method": "PATCH", "path": "/api/v1/invoices/invoices/{invoice_id}/verify", "description": "Verify or correct an invoice category."},
    {"module": "invoices", "method": "GET", "path": "/api/v1/invoices/invoices/{invoice_id}/suggest-categories", "description": "Suggest similar categories when the category is not in the piano conti."},
    {"module": "invoices", "method": "GET", "path": "/api/v1/invoices/invoices/{invoice_id}", "description": "Get a single invoice by ID."},
    {"module": "journal", "method": "GET", "path": "/api/v1/accounting/journal-entries", "description": "List journal entries with filters and pagination."},
    {"module": "journal", "method": "GET", "path": "/api/v1/accounting/journal-entries/{entry_id}", "description": "Get a single journal entry with its lines."},
    {"module": "normativo", "method": "GET", "path": "/api/v1/normativo/alerts", "description": "List all normative alerts."},
    {"module": "normativo", "method": "POST", "path": "/api/v1/normativo/check", "description": "Force check RSS feed for normative updates."},
    {"module": "notifications", "method": "POST", "path": "/api/v1/notifications/config", "description": "Create or update a notification channel configuration."},
    {"module": "notifications", "method": "GET", "path": "/api/v1/notifications/config", "description": "Get all notification configurations for the current user."},
    {"module": "notifications", "method": "POST", "path": "/api/v1/notifications/test", "description": "Send a test notification to verify channel configuration."},
    {"module": "onboarding", "method": "GET", "path": "/api/v1/onboarding/status", "description": "Get current onboarding status (step, what's done, what's next)."},
    {"module": "onboarding", "method": "POST", "path": "/api/v1/onboarding/step/{step_number}", "description": "Complete an onboarding step."},
    {"module": "payments", "method": "POST", "path": "/api/v1/payments/execute", "description": "Execute a single supplier payment via PISP."},
    {"module": "payments", "method": "POST", "path": "/api/v1/payments/batch", "description": "Execute a batch payment for multiple invoices."},
    {"module": "preservation", "method": "GET", "path": "/api/v1/preservation", "description": "List all preservation records with status summary."},
    {"module": "preservation", "method": "POST", "path": "/api/v1/preservation/batch", "description": "Send batch of documents to preservation provider."},
    {"module": "preservation", "method": "POST", "path": "/api/v1/preservation/check-status", "description": "Check preservation status for all sent documents."},
    {"module": "preservation", "method": "POST", "path": "/api/v1/preservation/credit-note/{credit_note_id}", "description": "Send credit note linked to preserved invoice."},
    {"module": "profile", "method": "GET", "path": "/api/v1/profile", "description": ""},
    {"module": "profile", "method": "PATCH", "path": "/api/v1/profile", "description": ""},
    {"module": "reconciliation", "method": "GET", "path": "/api/v1/reconciliation/pending", "description": "Get unreconciled bank transactions with match suggestions."},
    {"module": "reconciliation", "method": "POST", "path": "/api/v1/reconciliation/{tx_id}/match", "description": "Match a bank transaction to an invoice."},
    {"module": "reports", "method": "GET", "path": "/api/v1/reports/reports/commercialista", "description": "Generate commercialista report for the given period."},
    {"module": "sdi", "method": "POST", "path": "/api/v1/sdi/webhooks/sdi", "description": "Receive invoice from A-Cube SDI webhook."},
    {"module": "spid", "method": "POST", "path": "/api/v1/spid/auth/spid/init", "description": "Start SPID/CIE authentication for cassetto fiscale."},
    {"module": "spid", "method": "GET", "path": "/api/v1/spid/auth/spid/callback", "description": "Handle SPID callback after user authenticates."},
    {"module": "spid", "method": "GET", "path": "/api/v1/spid/cassetto/status", "description": "Get cassetto fiscale connection status."},
    {"module": "spid", "method": "GET", "path": "/api/v1/spid/cassetto/no-spid", "description": "Info for users without SPID/CIE — how to get it + alternatives."},
    {"module": "spid", "method": "GET", "path": "/api/v1/spid/auth/spid/session/{session_id}", "description": "Check FiscoAPI session status (SPID auth progress)."},
    {"module": "spid", "method": "POST", "path": "/api/v1/spid/auth/spid/session/{session_id}/otp", "description": "Send OTP code for SPID authentication."},
    {"module": "spid", "method": "POST", "path": "/api/v1/spid/auth/spid/delegate", "description": "Start delegated SPID auth (commercialista accessing client's cassetto)."},
    {"module": "withholding", "method": "POST", "path": "/api/v1/withholding-taxes/detect", "description": "Detect withholding tax from invoice XML."},
    {"module": "withholding", "method": "GET", "path": "/api/v1/withholding-taxes", "description": "List all withholding taxes for tenant."},
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
            cur.execute(sql, params or {})
            rows = cur.fetchmany(limit)
            return [dict(r) for r in rows]
    finally:
        conn.close()


def _scalar(sql: str, params: dict | None = None):
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or {})
            row = cur.fetchone()
            return row[0] if row else None
    finally:
        conn.close()


# ============================================================
# Database exploration
# ============================================================


@mcp.tool()
def list_tables() -> str:
    """List all 36 tables in AgentFlow DB with row counts."""
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
    """Show columns, types, and constraints for a table. Tables: tenants, users, invoices, agent_events, categorization_feedback, journal_entries, journal_lines, onboarding_states, fiscal_rules, chart_accounts..."""
    if table_name not in TABLES:
        return f"Table '{table_name}' not found. Available: {', '.join(sorted(TABLES))}"
    rows = _query(
        """
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %(t)s
        ORDER BY ordinal_position
        """,
        {"t": table_name},
    )
    return json.dumps(rows, default=str, indent=2)


@mcp.tool()
def run_query(sql: str, limit: int = 50) -> str:
    """Execute a READ-ONLY SQL query (SELECT/WITH only). Max {limit} rows."""
    sql_stripped = sql.strip().upper()
    if not sql_stripped.startswith("SELECT") and not sql_stripped.startswith("WITH"):
        return "ERROR: Only SELECT/WITH queries allowed."
    rows = _query(sql, limit=limit)
    return json.dumps(rows, default=str, indent=2)


@mcp.tool()
def sample_rows(table_name: str, limit: int = 5) -> str:
    """Get sample rows from any table. Useful for understanding data structure."""
    if table_name not in TABLES:
        return f"Table '{table_name}' not found."
    rows = _query(f"SELECT * FROM {table_name} ORDER BY created_at DESC NULLS LAST LIMIT %(lim)s", {"lim": limit}, limit=limit)
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
    params: dict = {}
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
        params["q"] = f"%{search}%"
    where = " AND ".join(conditions)
    rows = _query(
        f"SELECT type, COUNT(*) AS num, COALESCE(SUM(importo_totale), 0) AS totale "
        f"FROM invoices WHERE {where} GROUP BY type ORDER BY type",
        params,
    )
    total = sum(int(r["num"]) for r in rows)
    return json.dumps({"count": total, "by_type": rows}, default=str, indent=2)


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
    params: dict = {"lim": limit}
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
        params["q"] = f"%{search}%"
    where = " AND ".join(conditions)
    rows = _query(
        f"SELECT numero_fattura, emittente_nome, "
        f"structured_data->>'destinatario_nome' AS destinatario, "
        f"data_fattura, importo_totale, type, processing_status "
        f"FROM invoices WHERE {where} ORDER BY data_fattura DESC NULLS LAST LIMIT %(lim)s",
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
        {"yr": year}, limit=50,
    )
    return json.dumps(rows, default=str, indent=2)


@mcp.tool()
def kpi_summary(year: int = 2024) -> str:
    """KPI: fatturato, costi, EBITDA, counts for a year."""
    rows = _query(
        "SELECT type, COUNT(*) AS num_fatture, COALESCE(SUM(importo_totale), 0) AS totale "
        "FROM invoices WHERE EXTRACT(YEAR FROM data_fattura) = %(yr)s GROUP BY type",
        {"yr": year},
    )
    result = {"year": year, "fatturato": 0, "costi": 0, "fatture_emesse": 0, "fatture_ricevute": 0}
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
        {"yr": year, "ms": ms, "me": me}, limit=50,
    )
    te = sum(float(r["totale"]) for r in rows if r["type"] == "attiva")
    tr = sum(float(r["totale"]) for r in rows if r["type"] == "passiva")
    return json.dumps({
        "year": year, "quarter": quarter, "months": f"{ms}-{me}",
        "fatturato": round(te, 2), "costi": round(tr, 2), "ebitda": round(te - tr, 2),
        "detail": rows,
    }, default=str, indent=2)


@mcp.tool()
def top_clients(year: int = 2024, limit: int = 10) -> str:
    """Top clients by revenue (fatture emesse)."""
    rows = _query(
        "SELECT structured_data->>'destinatario_nome' AS cliente, "
        "COUNT(*) AS num_fatture, COALESCE(SUM(importo_totale), 0) AS totale "
        "FROM invoices WHERE type = 'attiva' AND EXTRACT(YEAR FROM data_fattura) = %(yr)s "
        "AND structured_data->>'destinatario_nome' IS NOT NULL "
        "GROUP BY structured_data->>'destinatario_nome' ORDER BY totale DESC LIMIT %(lim)s",
        {"yr": year, "lim": limit}, limit=limit,
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
        {"yr": year, "lim": limit}, limit=limit,
    )
    return json.dumps(rows, default=str, indent=2)


# ============================================================
# API endpoint catalog
# ============================================================


@mcp.tool()
def list_endpoints(module: str | None = None) -> str:
    """List all 111 API endpoints. Filter by module name optionally."""
    filtered = ENDPOINTS
    if module:
        filtered = [e for e in ENDPOINTS if e["module"] == module]
    return json.dumps(filtered, indent=2)


@mcp.tool()
def list_modules() -> str:
    """List all 29 API modules with endpoint count."""
    mods = {}
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
    headers = {"Authorization": f"Bearer {API_TOKEN}", "Content-Type": "application/json"}
    payload = {"message": prompt, "conversation_id": None, "context": {"page": page, "year": year}}
    try:
        resp = httpx.post(f"{API_URL}/api/v1/chat/send", json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        d = resp.json()
        return json.dumps({
            "content": d.get("content", "")[:500],
            "agent_name": d.get("agent_name"),
            "tool_calls": d.get("tool_calls"),
            "response_meta": d.get("response_meta"),
        }, default=str, indent=2, ensure_ascii=False)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def get_api_token(email: str = "mgiurelli@taal.it", password: str = "TestPass1") -> str:
    """Login and store JWT token for chatbot testing."""
    global API_TOKEN
    try:
        resp = httpx.post(f"{API_URL}/api/v1/auth/login", json={"email": email, "password": password}, timeout=15)
        resp.raise_for_status()
        API_TOKEN = resp.json().get("access_token", "")
        return f"Token obtained ({len(API_TOKEN)} chars). Ready for test_chatbot()."
    except Exception as e:
        return f"Login failed: {e}"


# ============================================================
# Data validation
# ============================================================


@mcp.tool()
def validate_data() -> str:
    """Check data integrity: counts by year/type, nulls, status distribution."""
    checks = {}
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
