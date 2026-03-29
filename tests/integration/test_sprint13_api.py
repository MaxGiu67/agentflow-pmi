"""Integration tests for Sprint 13: Budget Agent + Controller (US-60, US-61, US-62)."""

from datetime import date

import pytest
from httpx import AsyncClient

from tests.conftest import get_auth_token


@pytest.fixture
async def sample_data(db_session, tenant):
    """Create invoices and payroll for testing budget/controller."""
    from api.db.models import Invoice, PayrollCost, Budget

    # Invoices 2024 — ricavi (attiva)
    for m in range(1, 7):
        db_session.add(Invoice(
            tenant_id=tenant.id, type="attiva", source="cassetto_fiscale",
            numero_fattura=f"FA/{m}", emittente_piva="12345678901", emittente_nome="Test",
            data_fattura=date(2024, m, 15), importo_netto=5000 + m * 100,
            importo_iva=1100, importo_totale=6100 + m * 100, processing_status="registered",
        ))

    # Invoices 2024 — costi (passiva)
    for m in range(1, 7):
        db_session.add(Invoice(
            tenant_id=tenant.id, type="passiva", source="cassetto_fiscale",
            numero_fattura=f"FP/{m}", emittente_piva="98765432109", emittente_nome="Fornitore",
            data_fattura=date(2024, m, 20), importo_netto=2000 + m * 50,
            importo_iva=440, importo_totale=2440 + m * 50, processing_status="registered",
        ))

    # Payroll 2024
    for m in range(1, 7):
        db_session.add(PayrollCost(
            tenant_id=tenant.id, mese=date(2024, m, 1),
            dipendente_nome="Riepilogo", importo_lordo=3000,
            costo_totale_azienda=4200,
        ))

    # Budget 2025 (for comparison)
    for m in range(1, 13):
        db_session.add(Budget(tenant_id=tenant.id, year=2025, month=m, category="ricavi", budget_amount=6000))
        db_session.add(Budget(tenant_id=tenant.id, year=2025, month=m, category="fornitori", budget_amount=2500))
        db_session.add(Budget(tenant_id=tenant.id, year=2025, month=m, category="personale", budget_amount=4200))

    # Some 2025 actuals (Jan)
    db_session.add(Invoice(
        tenant_id=tenant.id, type="attiva", source="cassetto_fiscale",
        numero_fattura="FA25/1", emittente_piva="12345678901", emittente_nome="Test",
        data_fattura=date(2025, 1, 15), importo_netto=5500,
        importo_iva=1210, importo_totale=6710, processing_status="registered",
    ))
    db_session.add(Invoice(
        tenant_id=tenant.id, type="passiva", source="cassetto_fiscale",
        numero_fattura="FP25/1", emittente_piva="98765432109", emittente_nome="Fornitore",
        data_fattura=date(2025, 1, 20), importo_netto=3200,
        importo_iva=704, importo_totale=3904, processing_status="registered",
    ))

    await db_session.flush()


# ═══════════════════════════════════════════════
# US-60: Budget Agent — generazione conversazionale
# ═══════════════════════════════════════════════

@pytest.mark.asyncio
async def test_ac_60_1_generate_from_historical(client: AsyncClient, verified_user, sample_data):
    """AC-60.1: Con dati storici → propone budget basato su anno precedente."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")
    resp = await client.post(
        "/api/v1/controller/budget/generate?year=2025&growth_rate=0.05",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["year"] == 2025
    assert data["has_historical_data"] is True
    assert data["totale_ricavi"] > 0
    assert len(data["proposal"]) >= 3  # ricavi, fornitori, personale


@pytest.mark.asyncio
async def test_ac_60_3_save_budget(client: AsyncClient, verified_user, sample_data):
    """AC-60.3: Budget confermato → salvato per mese e categoria."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")
    resp = await client.post(
        "/api/v1/controller/budget/save",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "year": 2026,
            "lines": [
                {"category": "ricavi", "monthly_proposed": 6000},
                {"category": "personale", "monthly_proposed": 4500},
            ],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["lines_saved"] == 24  # 2 categories × 12 months
    assert data["categories"] == 2


@pytest.mark.asyncio
async def test_ac_60_4_no_history_still_works(client: AsyncClient, verified_user):
    """AC-60.4: Senza storico → propone budget vuoto."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")
    resp = await client.post(
        "/api/v1/controller/budget/generate?year=2030",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["has_historical_data"] is False


# ═══════════════════════════════════════════════
# US-61: Budget vs Consuntivo mensile
# ═══════════════════════════════════════════════

@pytest.mark.asyncio
async def test_ac_61_1_vs_actual_with_budget(client: AsyncClient, verified_user, sample_data):
    """AC-61.1: Budget vs actual con dati → confronto corretto."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")
    resp = await client.get(
        "/api/v1/controller/budget/vs-actual?year=2025&month=1",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["has_budget"] is True
    assert len(data["comparisons"]) > 0

    # Check ricavi comparison
    ricavi = next((c for c in data["comparisons"] if c["category"] == "ricavi"), None)
    assert ricavi is not None
    assert ricavi["budget"] == 6000
    assert ricavi["actual"] == 5500  # from sample_data


@pytest.mark.asyncio
async def test_ac_61_2_scostamento_severity(client: AsyncClient, verified_user, sample_data):
    """AC-61.2: Scostamento > 20% → severity critical."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")
    resp = await client.get(
        "/api/v1/controller/budget/vs-actual?year=2025&month=1",
        headers={"Authorization": f"Bearer {token}"},
    )
    data = resp.json()
    # fornitori: budget 2500, actual 3200 → +28% → critical
    fornitori = next((c for c in data["comparisons"] if c["category"] == "fornitori"), None)
    assert fornitori is not None
    assert fornitori["severity"] == "critical"


# ═══════════════════════════════════════════════
# US-62: Controller "Come sto andando?"
# ═══════════════════════════════════════════════

@pytest.mark.asyncio
async def test_ac_62_1_summary_returns_kpis(client: AsyncClient, verified_user, sample_data):
    """AC-62.1: Summary restituisce ricavi, costi, margine, trend."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")
    resp = await client.get(
        "/api/v1/controller/summary?year=2025&month=1",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ricavi"] == 5500
    assert data["costi"] > 0
    assert "margine" in data
    assert "margine_pct" in data
    assert "top_costs" in data


@pytest.mark.asyncio
async def test_ac_62_2_includes_anomalies(client: AsyncClient, verified_user, sample_data):
    """AC-62.2: Il summary include le anomalie budget."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")
    resp = await client.get(
        "/api/v1/controller/summary?year=2025&month=1",
        headers={"Authorization": f"Bearer {token}"},
    )
    data = resp.json()
    assert "anomalies" in data
