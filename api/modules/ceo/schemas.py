"""Pydantic schemas for CEO Dashboard module (US-39, US-40)."""

from pydantic import BaseModel


# ============================================================
# US-39: Dashboard CEO — KPI
# ============================================================


class TopEntity(BaseModel):
    """Top client/supplier entry."""
    name: str
    piva: str
    total: float


class KPIDashboard(BaseModel):
    """Main KPI dashboard data."""
    fatturato_mese: float = 0.0
    fatturato_ytd: float = 0.0
    ebitda_amount: float = 0.0
    ebitda_percent: float = 0.0
    cash_flow: float = 0.0
    scadenze_prossime: int = 0
    top_clienti: list[TopEntity] = []
    top_fornitori: list[TopEntity] = []
    data_note: str | None = None  # AC-39.4


class YoYComparison(BaseModel):
    """Year-over-year comparison."""
    metric: str
    current_value: float
    previous_value: float
    variation_percent: float | None = None
    direction: str = "stable"  # up, down, stable


class DSODPOEntry(BaseModel):
    """DSO/DPO quarterly entry."""
    quarter: int
    value: float


class DSODPOTrend(BaseModel):
    """DSO/DPO trend data."""
    dso_current: float = 0.0
    dpo_current: float = 0.0
    dso_trend: list[DSODPOEntry] = []
    dpo_trend: list[DSODPOEntry] = []


class ConcentrationAlert(BaseModel):
    """Client concentration alert."""
    alert_type: str  # concentration
    message: str
    top3_percent: float
    top3_clients: list[TopEntity]


class CEODashboardResponse(BaseModel):
    """Full dashboard response."""
    kpi: KPIDashboard
    dso_dpo: DSODPOTrend


class YoYResponse(BaseModel):
    """Year-over-year comparison response."""
    year_current: int
    year_previous: int
    comparisons: list[YoYComparison]


class AlertsResponse(BaseModel):
    """Alerts response."""
    alerts: list[ConcentrationAlert]


# ============================================================
# US-40: Budget vs Consuntivo
# ============================================================


class BudgetMonthValue(BaseModel):
    """Single month budget/actual pair."""
    month: int
    label: str
    budget: float = 0.0
    actual: float = 0.0


class BudgetEntry(BaseModel):
    """Budget category with monthly grid (Pivot 5 format)."""
    category: str
    label: str = ""
    monthly: list[BudgetMonthValue] = []
    total_budget: float = 0.0
    total_actual: float = 0.0
    variance: float = 0.0
    variance_pct: float = 0.0

    model_config = {"from_attributes": True}


class BudgetCreateRequest(BaseModel):
    """Request to create/update budget entries."""
    year: int
    month: int
    entries: list[dict]  # [{category: str, amount: float}]


class BudgetListResponse(BaseModel):
    """Budget vs consuntivo response (monthly grid)."""
    year: int
    entries: list[BudgetEntry] = []
    month_labels: list[str] = []
    total_budget: float = 0.0
    total_actual: float = 0.0
    total_delta: float = 0.0
    # Wizard fallback fields (when no budget exists)
    has_budget: bool | None = None
    message: str | None = None
    suggested_categories: list[str] | None = None
    suggestions: list[dict] | None = None


class BudgetProjection(BaseModel):
    """End-of-year projection entry."""
    category: str
    budget_annual: float
    actual_ytd: float
    projected_annual: float
    moving_average: float


class BudgetProjectionResponse(BaseModel):
    """Projection response."""
    year: int
    months_with_data: int
    projections: list[BudgetProjection]
    total_budget_annual: float = 0.0
    total_projected_annual: float = 0.0


class BudgetWizardResponse(BaseModel):
    """AC-40.4: Wizard response when no budget is set."""
    has_budget: bool = False
    message: str = "Budget non ancora inserito"
    suggested_categories: list[str] = []
    suggestions: list[dict] = []


class BudgetCreateResponse(BaseModel):
    """Response from budget creation."""
    created: int
    year: int
    month: int
