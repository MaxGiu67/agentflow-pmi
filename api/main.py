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

from contextlib import asynccontextmanager

from api.db.models import Base
from api.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
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
