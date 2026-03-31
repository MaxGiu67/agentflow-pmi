"""Schemas for the dashboard module."""

from datetime import datetime

from pydantic import BaseModel

from api.modules.invoices.schemas import InvoiceResponse


class InvoiceCounters(BaseModel):
    """Invoice counters by status."""
    total: int = 0
    pending: int = 0
    parsed: int = 0
    categorized: int = 0
    registered: int = 0
    error: int = 0


class AgentStatus(BaseModel):
    """Status of a single agent."""
    name: str
    status: str  # active, idle, error
    last_run: datetime | None = None
    events_published: int = 0
    events_failed: int = 0


class DashboardSummary(BaseModel):
    """Complete dashboard summary."""
    counters: InvoiceCounters
    recent_invoices: list[InvoiceResponse]
    agents: list[AgentStatus]
    last_sync_at: datetime | None = None
    message: str | None = None


# --- Yearly stats schemas ---

class InvoiceTypeSummary(BaseModel):
    """Aggregate summary for a type of invoice (attiva/passiva)."""
    count: int = 0
    totale: float = 0.0
    imponibile: float = 0.0
    iva: float = 0.0


class TopEntity(BaseModel):
    """A top client or supplier entry."""
    nome: str
    piva: str = ""
    totale: float = 0.0
    count: int = 0


class MonthlyBreakdown(BaseModel):
    """Monthly breakdown of invoices."""
    mese: int
    attive_count: int = 0
    attive_totale: float = 0.0
    passive_count: int = 0
    passive_totale: float = 0.0


class CostSummary(BaseModel):
    """Summary for a cost source."""
    count: int = 0
    totale: float = 0.0


class LoanSummary(BaseModel):
    """Summary for loans/financing."""
    count: int = 0
    totale_annuo: float = 0.0


class YearlyStats(BaseModel):
    """Complete yearly statistics for the dashboard."""
    year: int
    fatture_attive: InvoiceTypeSummary
    fatture_passive: InvoiceTypeSummary
    costo_personale: CostSummary = CostSummary()
    note_spese: CostSummary = CostSummary()
    corrispettivi: CostSummary = CostSummary()
    finanziamenti: LoanSummary = LoanSummary()
    ricavi_totali: float = 0.0
    costi_totali: float = 0.0
    margine_lordo: float = 0.0
    top_clienti: list[TopEntity] = []
    top_fornitori: list[TopEntity] = []
    fatture_per_mese: list[MonthlyBreakdown] = []
    available_years: list[int] = []
