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

from contextlib import asynccontextmanager

from api.db.models import Base
from api.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
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
        ]:
            try:
                await conn.execute(text(stmt))
            except Exception:
                pass  # Column already exists or table doesn't exist yet

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

frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(profile_router, prefix="/api/v1")
app.include_router(spid_router, prefix="/api/v1")
app.include_router(accounting_router, prefix="/api/v1")
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
app.include_router(active_invoices_router, prefix="/api/v1")
app.include_router(banking_router, prefix="/api/v1")
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
