import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.modules.auth.router import router as auth_router
from api.modules.profile.router import router as profile_router
from api.modules.spid.router import router as spid_router
from api.modules.accounting.router import router as accounting_router
from api.modules.invoices.router import router as invoices_router
from api.modules.invoices.upload_router import router as upload_router
from api.modules.dashboard.router import router as dashboard_router
from api.modules.journal.router import router as journal_router
from api.modules.onboarding.router import router as onboarding_router
from api.modules.onboarding.conto_economico_router import router as conto_economico_router
from api.modules.fiscal.router import router as fiscal_router
from api.modules.sdi.router import router as sdi_router
from api.modules.email_connector.router import router as email_router
from api.modules.deadlines.router import router as deadlines_router
from api.modules.reports.router import router as reports_router
from api.modules.notifications.router import router as notifications_router
from api.modules.active_invoices.router import router as active_invoices_router
from api.modules.banking.router import router as banking_router
from api.modules.banking.acube_ob_router import router as acube_ob_router
from api.modules.banking.acube_ob_webhooks import router as acube_ob_webhooks_router
from api.modules.cashflow.router import router as cashflow_router
from api.modules.reconciliation.router import router as reconciliation_router
from api.modules.withholding.router import router as withholding_router
from api.modules.expenses.router import router as expenses_router
from api.modules.assets.router import router as assets_router
from api.modules.cu.router import router as cu_router
from api.modules.preservation.router import router as preservation_router
from api.modules.payments.router import router as payments_router
from api.modules.normativo.router import router as normativo_router
from api.modules.f24.router import router as f24_router
from api.modules.ceo.router import router as ceo_router
from api.modules.webhooks_fiscoapi import router as fiscoapi_webhook_router
from api.modules.chat.router import router as chat_router
from api.modules.agent_config.router import router as agent_config_router
from api.modules.dashboard.layout_router import router as layout_router
from api.modules.payroll.router import router as payroll_router
from api.modules.corrispettivi.router import router as corrispettivi_router
from api.modules.completeness.router import router as completeness_router
from api.modules.bilancio_import.router import router as bilancio_import_router
from api.modules.controller.router import router as controller_router
from api.modules.f24_import.router import router as f24_import_router
from api.modules.home.router import router as home_router
from api.modules.ammortamenti.router import router as ammortamenti_router
from api.modules.alerts.router import router as alerts_router
from api.modules.recurring.router import router as recurring_router
from api.modules.loans.router import router as loans_router
from api.modules.communications.router import router as communications_router
from api.modules.scadenzario.router import router as scadenzario_router
from api.modules.crm.router import router as crm_router
from api.modules.email_marketing.router import router as email_marketing_router
from api.modules.user_management.router import router as user_management_router
from api.modules.tenant_settings.router import router as tenant_settings_router
from api.modules.metering.router import router as metering_router
from api.modules.social_selling.router import router as social_selling_router
from api.modules.calendar.router import router as calendar_router
from api.modules.portal.router import router as portal_router
from api.modules.pipeline_templates.router import router as pipeline_templates_router
from api.modules.resources.router import router as resources_router
from api.modules.elevia.router import router as elevia_router
from api.modules.pec.router import router as pec_router
from api.modules.scarico_massivo.router import router as scarico_massivo_router
from api.modules.scarico_massivo.webhooks import router as scarico_massivo_webhooks_router
from api.modules.state.banking_snapshot import router as state_banking_router
from api.modules.state.invoicing_snapshot import router as state_invoicing_router
from api.modules.state.sales_snapshot import router as state_sales_router
from api.modules.state.router import router as state_aggregator_router

from contextlib import asynccontextmanager

from api.db.models import Base
from api.db.session import engine
from monitoring.error_middleware import ErrorTrackingMiddleware
from monitoring.heartbeat_client import HeartbeatClient


@asynccontextmanager
async def lifespan(app: FastAPI):
    HeartbeatClient.start_web()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Pivot 5: add missing columns to existing tables (safe ALTER TABLE IF NOT EXISTS)
        from sqlalchemy import text
        for stmt in [
            "ALTER TABLE bank_transactions ADD COLUMN IF NOT EXISTS value_date DATE",
            "ALTER TABLE bank_transactions ADD COLUMN IF NOT EXISTS source VARCHAR(20) DEFAULT 'open_banking'",
            "ALTER TABLE f24_documents ADD COLUMN IF NOT EXISTS source VARCHAR(20) DEFAULT 'calculated'",
            "ALTER TABLE assets ADD COLUMN IF NOT EXISTS source VARCHAR(20) DEFAULT 'manual'",
            "ALTER TABLE assets ADD COLUMN IF NOT EXISTS detected_from_invoice_id UUID",
            "ALTER TABLE budgets ADD COLUMN IF NOT EXISTS label VARCHAR(200)",
            # Pivot 9: User management columns
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS active BOOLEAN DEFAULT TRUE",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS sender_email VARCHAR(255)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS sender_name VARCHAR(255)",
            # Pivot 7: Tenant email config
            "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS sender_email VARCHAR(255)",
            "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS sender_name VARCHAR(255)",
            "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS sender_domain VARCHAR(100)",
            "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS email_quota_monthly INTEGER DEFAULT 5000",
            "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS email_sent_month INTEGER DEFAULT 0",
            "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS email_month_reset VARCHAR(7)",
            # Pivot 8: Social Selling — origin_id on contacts
            "ALTER TABLE crm_contacts ADD COLUMN IF NOT EXISTS origin_id UUID",
            "ALTER TABLE crm_contacts ADD COLUMN IF NOT EXISTS contact_name VARCHAR(255)",
            "ALTER TABLE crm_contacts ADD COLUMN IF NOT EXISTS contact_role VARCHAR(100)",
            "ALTER TABLE crm_contacts ADD COLUMN IF NOT EXISTS company_id UUID",
            "ALTER TABLE crm_deals ADD COLUMN IF NOT EXISTS company_id UUID",
            # Pivot 8: Pipeline pre-funnel + activity types
            "ALTER TABLE crm_pipeline_stages ADD COLUMN IF NOT EXISTS stage_type VARCHAR(50) DEFAULT 'pipeline'",
            "ALTER TABLE crm_pipeline_stages ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE",
            "ALTER TABLE crm_activities ADD COLUMN IF NOT EXISTS activity_type_id UUID",
            # Pivot 8: US-138→US-141 — Roles, external users, audit
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS user_type VARCHAR(50) DEFAULT 'internal'",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS access_expires_at TIMESTAMP",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS crm_role_id UUID",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS default_origin_id UUID",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS default_product_id UUID",
            # Sprint 33: Calendar
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS microsoft_token TEXT",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS calendly_url VARCHAR(500)",
            "ALTER TABLE crm_activities ADD COLUMN IF NOT EXISTS outlook_event_id VARCHAR(255)",
            # Pivot 9: Pipeline Templates + Resources + Elevia
            "ALTER TABLE crm_products ADD COLUMN IF NOT EXISTS pipeline_template_id UUID",
            "ALTER TABLE crm_deals ADD COLUMN IF NOT EXISTS pipeline_template_id UUID",
            # Pivot 10: Portal integration
            "ALTER TABLE crm_deals ADD COLUMN IF NOT EXISTS portal_customer_id INTEGER",
            "ALTER TABLE crm_deals ADD COLUMN IF NOT EXISTS portal_customer_name VARCHAR(255)",
            "ALTER TABLE crm_deals ADD COLUMN IF NOT EXISTS portal_project_id INTEGER",
            "ALTER TABLE crm_deals ADD COLUMN IF NOT EXISTS portal_offer_id INTEGER",
            "ALTER TABLE crm_products ADD COLUMN IF NOT EXISTS requires_resources BOOLEAN DEFAULT FALSE",
            # Pivot 11: A-Cube Open Banking AISP (ADR-012) — Sprint 48 US-OB-03
            "ALTER TABLE bank_accounts ADD COLUMN IF NOT EXISTS acube_uuid VARCHAR(64)",
            "ALTER TABLE bank_accounts ADD COLUMN IF NOT EXISTS acube_connection_id UUID",
            "ALTER TABLE bank_accounts ADD COLUMN IF NOT EXISTS acube_provider_name VARCHAR(255)",
            "ALTER TABLE bank_accounts ADD COLUMN IF NOT EXISTS acube_nature VARCHAR(50)",
            "ALTER TABLE bank_accounts ADD COLUMN IF NOT EXISTS acube_enabled BOOLEAN DEFAULT TRUE",
            "ALTER TABLE bank_accounts ADD COLUMN IF NOT EXISTS acube_extra JSON",
            "ALTER TABLE bank_transactions ADD COLUMN IF NOT EXISTS acube_transaction_id VARCHAR(255)",
            "ALTER TABLE bank_transactions ADD COLUMN IF NOT EXISTS acube_status VARCHAR(20)",
            "ALTER TABLE bank_transactions ADD COLUMN IF NOT EXISTS acube_duplicated BOOLEAN DEFAULT FALSE",
            "ALTER TABLE bank_transactions ADD COLUMN IF NOT EXISTS acube_category VARCHAR(100)",
            "ALTER TABLE bank_transactions ADD COLUMN IF NOT EXISTS acube_fetched_at TIMESTAMP",
            "ALTER TABLE bank_transactions ADD COLUMN IF NOT EXISTS acube_counterparty VARCHAR(255)",
            "ALTER TABLE bank_transactions ADD COLUMN IF NOT EXISTS enriched_cro VARCHAR(50)",
            "ALTER TABLE bank_transactions ADD COLUMN IF NOT EXISTS enriched_invoice_ref VARCHAR(100)",
            "ALTER TABLE bank_transactions ADD COLUMN IF NOT EXISTS acube_extra JSON",
            # Sprint 50 — AI parser per movimenti bancari
            "ALTER TABLE bank_transactions ADD COLUMN IF NOT EXISTS parsed_counterparty VARCHAR(255)",
            "ALTER TABLE bank_transactions ADD COLUMN IF NOT EXISTS parsed_counterparty_iban VARCHAR(34)",
            "ALTER TABLE bank_transactions ADD COLUMN IF NOT EXISTS parsed_invoice_ref VARCHAR(100)",
            "ALTER TABLE bank_transactions ADD COLUMN IF NOT EXISTS parsed_category VARCHAR(50)",
            "ALTER TABLE bank_transactions ADD COLUMN IF NOT EXISTS parsed_subcategory VARCHAR(50)",
            "ALTER TABLE bank_transactions ADD COLUMN IF NOT EXISTS parsed_confidence REAL",
            "ALTER TABLE bank_transactions ADD COLUMN IF NOT EXISTS parsed_method VARCHAR(20)",
            "ALTER TABLE bank_transactions ADD COLUMN IF NOT EXISTS parsed_at TIMESTAMP",
            "ALTER TABLE bank_transactions ADD COLUMN IF NOT EXISTS parsed_notes TEXT",
            "ALTER TABLE bank_transactions ADD COLUMN IF NOT EXISTS user_corrected BOOLEAN DEFAULT FALSE",
            "ALTER TABLE bank_transactions ADD COLUMN IF NOT EXISTS linked_invoice_id UUID",
            # Indici utili per dedup/lookup
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_bank_accounts_acube_uuid ON bank_accounts (acube_uuid) WHERE acube_uuid IS NOT NULL",
            "CREATE INDEX IF NOT EXISTS ix_bank_accounts_acube_connection_id ON bank_accounts (acube_connection_id)",
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_bank_tx_acube_id ON bank_transactions (bank_account_id, acube_transaction_id) WHERE acube_transaction_id IS NOT NULL",
            "CREATE INDEX IF NOT EXISTS ix_bank_connections_tenant_fiscal ON bank_connections (tenant_id, fiscal_id)",
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_bank_connections_acube_br_uuid ON bank_connections (acube_br_uuid) WHERE acube_br_uuid IS NOT NULL",
            # Pivot 11 US-OB-05: webhook_events idempotency + audit
            "CREATE INDEX IF NOT EXISTS ix_webhook_events_status ON webhook_events (processing_status)",
            "CREATE INDEX IF NOT EXISTS ix_webhook_events_received_at ON webhook_events (received_at)",
            "CREATE INDEX IF NOT EXISTS ix_webhook_events_source_type ON webhook_events (source, event_type)",
        ]:
            try:
                await conn.execute(text(stmt))
            except Exception:
                pass  # Column already exists or table doesn't exist yet

    # Dedup pipeline stages (remove duplicates by name per tenant)
    async with engine.begin() as conn:
        try:
            # Reassign deals to the first stage per name
            await conn.execute(text("""
                UPDATE crm_deals SET stage_id = keeper.id
                FROM crm_pipeline_stages s,
                     (SELECT DISTINCT ON (tenant_id, name) id, tenant_id, name
                      FROM crm_pipeline_stages ORDER BY tenant_id, name, id ASC) keeper
                WHERE crm_deals.stage_id = s.id
                  AND s.name = keeper.name AND s.tenant_id = keeper.tenant_id
                  AND crm_deals.stage_id != keeper.id
            """))
            # Delete duplicate stages
            await conn.execute(text("""
                DELETE FROM crm_pipeline_stages WHERE id IN (
                    SELECT id FROM (
                        SELECT id, ROW_NUMBER() OVER (PARTITION BY tenant_id, name ORDER BY id ASC) as rn
                        FROM crm_pipeline_stages
                    ) ranked WHERE rn > 1
                )
            """))
        except Exception:
            pass

    # Seed fiscal rules if empty
    from api.modules.fiscal.seed_rules import seed_fiscal_rules
    from api.db.session import async_session_factory
    async with async_session_factory() as session:
        try:
            await seed_fiscal_rules(session)
            await session.commit()
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning("Seed rules failed: %s", e)

    yield


app = FastAPI(
    title="AgentFlow API",
    description="AgentFlow — L'agente contabile AI per PMI italiane",
    version="1.0.0",
    lifespan=lifespan,
)


# ── Manual migration endpoint (call once after deploy) ──
@app.get("/api/v1/admin/migrate")
async def admin_migrate():
    """One-time manual migration: creates missing tables and columns.
    Call this after deploy if lifespan didn't run the migrations."""
    from sqlalchemy import text
    from api.db.session import engine
    from api.db.models import Base

    results = []

    # Step 1: Create all missing tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        results.append("Tables: create_all executed")

    # Step 2: ALTER TABLE for new columns
    alter_statements = [
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS microsoft_token TEXT",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS calendly_url VARCHAR(500)",
        "ALTER TABLE crm_activities ADD COLUMN IF NOT EXISTS outlook_event_id VARCHAR(255)",
        "ALTER TABLE crm_products ADD COLUMN IF NOT EXISTS pipeline_template_id UUID",
        "ALTER TABLE crm_deals ADD COLUMN IF NOT EXISTS pipeline_template_id UUID",
        "ALTER TABLE crm_deals ADD COLUMN IF NOT EXISTS company_id UUID",
        "ALTER TABLE crm_deals ADD COLUMN IF NOT EXISTS portal_customer_id INTEGER",
        "ALTER TABLE crm_deals ADD COLUMN IF NOT EXISTS portal_customer_name VARCHAR(255)",
        "ALTER TABLE crm_deals ADD COLUMN IF NOT EXISTS portal_project_id INTEGER",
        "ALTER TABLE crm_contacts ADD COLUMN IF NOT EXISTS company_id UUID",
        "ALTER TABLE crm_contacts ADD COLUMN IF NOT EXISTS contact_name VARCHAR(255)",
        "ALTER TABLE crm_contacts ADD COLUMN IF NOT EXISTS contact_role VARCHAR(100)",
        "ALTER TABLE crm_contacts ADD COLUMN IF NOT EXISTS origin_id UUID",
        "ALTER TABLE crm_pipeline_stages ADD COLUMN IF NOT EXISTS stage_type VARCHAR(50) DEFAULT 'pipeline'",
        "ALTER TABLE crm_pipeline_stages ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE",
        "ALTER TABLE crm_activities ADD COLUMN IF NOT EXISTS activity_type_id UUID",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS user_type VARCHAR(50) DEFAULT 'internal'",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS access_expires_at TIMESTAMP",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS crm_role_id UUID",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS default_origin_id UUID",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS default_product_id UUID",
    ]

    async with engine.begin() as conn:
        for stmt in alter_statements:
            try:
                await conn.execute(text(stmt))
                col = stmt.split("ADD COLUMN IF NOT EXISTS ")[1].split(" ")[0]
                results.append(f"ALTER: {col} OK")
            except Exception as e:
                results.append(f"ALTER: {stmt[:50]}... SKIP ({e})")

    # Step 3: Dedup pipeline stages (keep first per name+tenant, reassign deals)
    dedup_sql = """
    WITH ranked AS (
        SELECT id, name, tenant_id,
               ROW_NUMBER() OVER (PARTITION BY tenant_id, name ORDER BY created_at ASC, id ASC) as rn
        FROM crm_pipeline_stages
    ),
    dupes AS (
        SELECT id FROM ranked WHERE rn > 1
    ),
    keeper AS (
        SELECT DISTINCT ON (tenant_id, name) id, tenant_id, name
        FROM crm_pipeline_stages ORDER BY tenant_id, name, created_at ASC, id ASC
    )
    UPDATE crm_deals SET stage_id = keeper.id
    FROM crm_pipeline_stages s, keeper
    WHERE crm_deals.stage_id = s.id
      AND s.name = keeper.name AND s.tenant_id = keeper.tenant_id
      AND crm_deals.stage_id != keeper.id;
    """
    dedup_delete = """
    DELETE FROM crm_pipeline_stages WHERE id IN (
        SELECT id FROM (
            SELECT id, ROW_NUMBER() OVER (PARTITION BY tenant_id, name ORDER BY created_at ASC, id ASC) as rn
            FROM crm_pipeline_stages
        ) ranked WHERE rn > 1
    );
    """
    async with engine.begin() as conn:
        try:
            await conn.execute(text(dedup_sql))
            result_del = await conn.execute(text(dedup_delete))
            results.append(f"Dedup stages: deleted {result_del.rowcount} duplicates")
        except Exception as e:
            results.append(f"Dedup stages: SKIP ({e})")

    return {"status": "migration_complete", "results": results}

frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(ErrorTrackingMiddleware)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(profile_router, prefix="/api/v1")
app.include_router(spid_router, prefix="/api/v1")
app.include_router(accounting_router, prefix="/api/v1")
app.include_router(active_invoices_router, prefix="/api/v1")  # MUST be before invoices_router (route conflict on /invoices/active)
app.include_router(invoices_router, prefix="/api/v1")
app.include_router(upload_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(journal_router, prefix="/api/v1")
app.include_router(onboarding_router, prefix="/api/v1")
app.include_router(conto_economico_router, prefix="/api/v1")
app.include_router(fiscal_router, prefix="/api/v1")
app.include_router(sdi_router, prefix="/api/v1")
app.include_router(email_router, prefix="/api/v1")
app.include_router(deadlines_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(notifications_router, prefix="/api/v1")
app.include_router(banking_router, prefix="/api/v1")
app.include_router(acube_ob_router, prefix="/api/v1")
app.include_router(acube_ob_webhooks_router, prefix="/api/v1")
app.include_router(cashflow_router, prefix="/api/v1")
app.include_router(reconciliation_router, prefix="/api/v1")
app.include_router(withholding_router, prefix="/api/v1")
app.include_router(expenses_router, prefix="/api/v1")
app.include_router(assets_router, prefix="/api/v1")
app.include_router(cu_router, prefix="/api/v1")
app.include_router(preservation_router, prefix="/api/v1")
app.include_router(payments_router, prefix="/api/v1")
app.include_router(normativo_router, prefix="/api/v1")
app.include_router(f24_router, prefix="/api/v1")
app.include_router(ceo_router, prefix="/api/v1")
app.include_router(fiscoapi_webhook_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(agent_config_router, prefix="/api/v1")
app.include_router(layout_router, prefix="/api/v1")
app.include_router(payroll_router, prefix="/api/v1")
app.include_router(corrispettivi_router, prefix="/api/v1")
app.include_router(completeness_router, prefix="/api/v1")
app.include_router(bilancio_import_router, prefix="/api/v1")
app.include_router(controller_router, prefix="/api/v1")
app.include_router(f24_import_router, prefix="/api/v1")
app.include_router(home_router, prefix="/api/v1")
app.include_router(ammortamenti_router, prefix="/api/v1")
app.include_router(alerts_router, prefix="/api/v1")
app.include_router(recurring_router, prefix="/api/v1")
app.include_router(loans_router, prefix="/api/v1")
app.include_router(communications_router, prefix="/api/v1")
app.include_router(scadenzario_router)
app.include_router(crm_router, prefix="/api/v1")
app.include_router(email_marketing_router)
app.include_router(user_management_router)
app.include_router(tenant_settings_router)
app.include_router(metering_router)
app.include_router(social_selling_router)
app.include_router(calendar_router, prefix="/api/v1")
app.include_router(pipeline_templates_router, prefix="/api/v1")
app.include_router(resources_router, prefix="/api/v1")
app.include_router(elevia_router, prefix="/api/v1")
app.include_router(portal_router, prefix="/api/v1")
app.include_router(pec_router, prefix="/api/v1")
app.include_router(scarico_massivo_router, prefix="/api/v1")
app.include_router(scarico_massivo_webhooks_router, prefix="/api/v1")
# State snapshots aggregati per agenti AI
app.include_router(state_banking_router, prefix="/api/v1")
app.include_router(state_invoicing_router, prefix="/api/v1")
app.include_router(state_sales_router, prefix="/api/v1")
app.include_router(state_aggregator_router, prefix="/api/v1")
