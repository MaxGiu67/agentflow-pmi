"""Sprint 17 tests — US-70 (Dashboard IVA netto), US-71 (Budget IVA netto), US-84 (Scadenza model).

Tests verify that dashboard and budget use importo_netto instead of importo_totale,
and that the Scadenza model is created correctly.
"""

import uuid
from datetime import date, datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import (
    Base, Budget, BudgetMeta, Invoice, Scadenza, BankFacility, InvoiceAdvance,
    BankAccount, Tenant, User,
)
from tests.conftest import test_session_factory, engine, get_auth_token


# ── Helpers ──

async def _create_tenant_user_invoices(db: AsyncSession) -> tuple:
    """Create tenant, user, and sample invoices with split netto/iva/totale."""
    tenant = Tenant(
        name="Sprint17 SRL",
        type="srl",
        regime_fiscale="ordinario",
        piva="17171717171",
        codice_ateco="62.01.00",
    )
    db.add(tenant)
    await db.flush()

    from tests.conftest import _hash_pw
    user = User(
        email="sprint17@example.com",
        password_hash=_hash_pw("Password1"),
        name="Sprint17 User",
        role="owner",
        email_verified=True,
        tenant_id=tenant.id,
    )
    db.add(user)
    await db.flush()

    # Fattura attiva: netto 1000, IVA 220, totale 1220
    inv_attiva = Invoice(
        tenant_id=tenant.id,
        type="attiva",
        document_type="TD01",
        source="sdi",
        numero_fattura="FA-2026-001",
        emittente_piva="17171717171",
        emittente_nome="Sprint17 SRL",
        data_fattura=date(2026, 3, 15),
        importo_netto=1000.0,
        importo_iva=220.0,
        importo_totale=1220.0,
        processing_status="registered",
        structured_data={"destinatario_nome": "Cliente Alpha", "destinatario_piva": "99999999999"},
    )
    db.add(inv_attiva)

    # Fattura passiva: netto 500, IVA 110, totale 610
    inv_passiva = Invoice(
        tenant_id=tenant.id,
        type="passiva",
        document_type="TD01",
        source="cassetto_fiscale",
        numero_fattura="FP-2026-001",
        emittente_piva="88888888888",
        emittente_nome="Fornitore Beta SRL",
        data_fattura=date(2026, 3, 20),
        importo_netto=500.0,
        importo_iva=110.0,
        importo_totale=610.0,
        processing_status="registered",
        category="Consulenze",
    )
    db.add(inv_passiva)
    await db.flush()
    return tenant, user, inv_attiva, inv_passiva


# ============================================================
# US-70: Dashboard mostra ricavi e costi al netto IVA
# ============================================================


@pytest.mark.asyncio
async def test_ac_70_1_ricavi_totali_uses_importo_netto(db_session: AsyncSession):
    """AC-70.1: Widget Ricavi Totali mostra somma importo_netto (non importo_totale)."""
    tenant, user, inv_a, inv_p = await _create_tenant_user_invoices(db_session)

    from api.modules.dashboard.service import DashboardService
    svc = DashboardService(db_session)
    stats = await svc.get_yearly_stats(user, 2026)

    # ricavi_totali should use imponibile (netto), not totale
    assert stats["ricavi_totali"] == 1000.0, (
        f"Expected 1000.0 (netto), got {stats['ricavi_totali']}"
    )
    assert stats["fatture_attive"]["imponibile"] == 1000.0


@pytest.mark.asyncio
async def test_ac_70_2_costi_totali_uses_importo_netto(db_session: AsyncSession):
    """AC-70.2: Widget Costi Totali mostra somma importo_netto passive."""
    tenant, user, inv_a, inv_p = await _create_tenant_user_invoices(db_session)

    from api.modules.dashboard.service import DashboardService
    svc = DashboardService(db_session)
    stats = await svc.get_yearly_stats(user, 2026)

    # costi_totali should use imponibile passive (500), not totale (610)
    assert stats["costi_totali"] == 500.0, (
        f"Expected 500.0 (netto), got {stats['costi_totali']}"
    )
    assert stats["fatture_passive"]["imponibile"] == 500.0


@pytest.mark.asyncio
async def test_ac_70_3_margine_ebitda_uses_netti(db_session: AsyncSession):
    """AC-70.3: Margine EBITDA = ricavi netti - costi netti."""
    tenant, user, inv_a, inv_p = await _create_tenant_user_invoices(db_session)

    from api.modules.dashboard.service import DashboardService
    svc = DashboardService(db_session)
    stats = await svc.get_yearly_stats(user, 2026)

    expected_margin = 1000.0 - 500.0
    assert stats["margine_lordo"] == expected_margin


@pytest.mark.asyncio
async def test_ac_70_4_grafico_mensile_uses_importo_netto(db_session: AsyncSession):
    """AC-70.4: Grafico mensile mostra importi netti."""
    tenant, user, inv_a, inv_p = await _create_tenant_user_invoices(db_session)

    from api.modules.dashboard.service import DashboardService
    svc = DashboardService(db_session)
    stats = await svc.get_yearly_stats(user, 2026)

    # March (month 3) should show netto amounts
    marzo = stats["fatture_per_mese"][2]  # index 2 = month 3
    assert marzo["mese"] == 3
    assert marzo["attive_totale"] == 1000.0, f"Expected 1000 netto, got {marzo['attive_totale']}"
    assert marzo["passive_totale"] == 500.0, f"Expected 500 netto, got {marzo['passive_totale']}"


@pytest.mark.asyncio
async def test_ac_70_5_widget_iva_netta(db_session: AsyncSession):
    """AC-70.5: Widget IVA Netta mostra IVA debito - IVA credito."""
    tenant, user, inv_a, inv_p = await _create_tenant_user_invoices(db_session)

    from api.modules.dashboard.service import DashboardService
    svc = DashboardService(db_session)
    stats = await svc.get_yearly_stats(user, 2026)

    assert "iva_netta" in stats
    assert stats["iva_netta"]["iva_debito"] == 220.0
    assert stats["iva_netta"]["iva_credito"] == 110.0
    assert stats["iva_netta"]["saldo"] == 110.0  # 220 - 110


# ============================================================
# US-71: Budget consuntivo usa importi netti
# ============================================================


@pytest.mark.asyncio
async def test_ac_71_1_consuntivo_ricavi_uses_importo_netto(db_session: AsyncSession):
    """AC-71.1: Consuntivo fatture attive usa importo_netto per ricavi."""
    tenant, user, inv_a, inv_p = await _create_tenant_user_invoices(db_session)

    # Create budget with ricavi category
    for month in range(1, 13):
        db_session.add(Budget(
            tenant_id=tenant.id, year=2026, month=month,
            category="ricavi", label="Ricavi", budget_amount=2000.0,
        ))
    await db_session.flush()

    from api.modules.ceo.service import CEOService
    svc = CEOService(db_session)
    result = await svc.get_budget(tenant.id, 2026)

    ricavi_entry = next(e for e in result["entries"] if e["category"] == "ricavi")
    # March should show 1000 netto (not 1220 lordo)
    march_actual = ricavi_entry["monthly"][2]["actual"]  # index 2 = March
    assert march_actual == 1000.0, f"Expected 1000.0 (netto), got {march_actual}"


@pytest.mark.asyncio
async def test_ac_71_2_consuntivo_costi_uses_importo_netto(db_session: AsyncSession):
    """AC-71.2: Consuntivo fatture passive usa importo_netto per costi."""
    tenant, user, inv_a, inv_p = await _create_tenant_user_invoices(db_session)

    # Create budget with Consulenze category (matches invoice category)
    for month in range(1, 13):
        db_session.add(Budget(
            tenant_id=tenant.id, year=2026, month=month,
            category="Consulenze", label="Consulenze", budget_amount=1000.0,
        ))
    await db_session.flush()

    from api.modules.ceo.service import CEOService
    svc = CEOService(db_session)
    result = await svc.get_budget(tenant.id, 2026)

    consulenze_entry = next(e for e in result["entries"] if e["category"] == "Consulenze")
    march_actual = consulenze_entry["monthly"][2]["actual"]
    assert march_actual == 500.0, f"Expected 500.0 (netto), got {march_actual}"


@pytest.mark.asyncio
async def test_ac_71_3_scostamento_on_netti(db_session: AsyncSession):
    """AC-71.3: Scostamento budget/consuntivo calcolato su importi netti."""
    tenant, user, inv_a, inv_p = await _create_tenant_user_invoices(db_session)

    # Budget ricavi: 2000/month, actual ricavi in March: 1000 (netto)
    for month in range(1, 13):
        db_session.add(Budget(
            tenant_id=tenant.id, year=2026, month=month,
            category="ricavi", label="Ricavi", budget_amount=2000.0,
        ))
    await db_session.flush()

    from api.modules.ceo.service import CEOService
    svc = CEOService(db_session)
    result = await svc.get_budget(tenant.id, 2026)

    ricavi_entry = next(e for e in result["entries"] if e["category"] == "ricavi")
    # Total actual should be 1000 (only March), total budget 24000
    assert ricavi_entry["total_actual"] == 1000.0
    assert ricavi_entry["total_budget"] == 24000.0
    # Variance = actual - budget = 1000 - 24000 = -23000
    assert ricavi_entry["variance"] == -23000.0


# ============================================================
# US-84: Modello Scadenza
# ============================================================


@pytest.mark.asyncio
async def test_ac_84_scadenza_model_creation(db_session: AsyncSession):
    """US-84: Scadenza model exists with all required fields."""
    tenant = Tenant(
        name="Scadenza Test SRL", type="srl",
        regime_fiscale="ordinario", piva="84848484848",
    )
    db_session.add(tenant)
    await db_session.flush()

    scadenza = Scadenza(
        tenant_id=tenant.id,
        tipo="attivo",
        source_type="fattura",
        source_id=uuid.uuid4(),
        controparte="Cliente Test SPA",
        importo_lordo=1220.0,
        importo_netto=1000.0,
        importo_iva=220.0,
        data_scadenza=date(2026, 5, 15),
        stato="aperto",
        banca_appoggio_id=None,
        anticipata=False,
    )
    db_session.add(scadenza)
    await db_session.flush()

    assert scadenza.id is not None
    assert scadenza.tipo == "attivo"
    assert scadenza.source_type == "fattura"
    assert scadenza.importo_lordo == 1220.0
    assert scadenza.importo_netto == 1000.0
    assert scadenza.importo_iva == 220.0
    assert scadenza.stato == "aperto"
    assert scadenza.anticipata is False


@pytest.mark.asyncio
async def test_ac_84_scadenza_passiva(db_session: AsyncSession):
    """US-84: Scadenza passiva with payment tracking."""
    tenant = Tenant(
        name="Passiva Test SRL", type="srl",
        regime_fiscale="ordinario", piva="84848484849",
    )
    db_session.add(tenant)
    await db_session.flush()

    scadenza = Scadenza(
        tenant_id=tenant.id,
        tipo="passivo",
        source_type="fattura",
        controparte="Fornitore Test SRL",
        importo_lordo=610.0,
        importo_netto=500.0,
        importo_iva=110.0,
        data_scadenza=date(2026, 4, 30),
        stato="aperto",
    )
    db_session.add(scadenza)
    await db_session.flush()

    # Simulate payment
    scadenza.stato = "pagato"
    scadenza.data_pagamento = date(2026, 4, 28)
    scadenza.importo_pagato = 610.0
    await db_session.flush()

    assert scadenza.stato == "pagato"
    assert scadenza.data_pagamento == date(2026, 4, 28)


@pytest.mark.asyncio
async def test_ac_84_scadenza_parziale(db_session: AsyncSession):
    """US-84: Scadenza with partial payment."""
    tenant = Tenant(
        name="Parziale Test SRL", type="srl",
        regime_fiscale="ordinario", piva="84848484850",
    )
    db_session.add(tenant)
    await db_session.flush()

    scadenza = Scadenza(
        tenant_id=tenant.id,
        tipo="attivo",
        source_type="fattura",
        controparte="Cliente Parziale SPA",
        importo_lordo=2440.0,
        importo_netto=2000.0,
        importo_iva=440.0,
        data_scadenza=date(2026, 6, 15),
        stato="parziale",
        importo_pagato=1000.0,
    )
    db_session.add(scadenza)
    await db_session.flush()

    assert scadenza.stato == "parziale"
    assert scadenza.importo_pagato == 1000.0
    residuo = scadenza.importo_lordo - scadenza.importo_pagato
    assert residuo == 1440.0


@pytest.mark.asyncio
async def test_ac_85_bank_facility_model(db_session: AsyncSession):
    """US-85: BankFacility model exists with all required fields."""
    tenant = Tenant(
        name="Fido Test SRL", type="srl",
        regime_fiscale="ordinario", piva="85858585858",
    )
    db_session.add(tenant)
    await db_session.flush()

    bank = BankAccount(
        tenant_id=tenant.id, iban="IT60X0542811101000000123456",
        bank_name="UniCredit", provider="manual", status="connected",
    )
    db_session.add(bank)
    await db_session.flush()

    facility = BankFacility(
        tenant_id=tenant.id,
        bank_account_id=bank.id,
        tipo="anticipo_fatture",
        plafond=100000.0,
        percentuale_anticipo=80.0,
        tasso_interesse_annuo=3.5,
        commissione_presentazione_pct=0.3,
        commissione_incasso=2.50,
        commissione_insoluto=15.0,
        giorni_max=120,
    )
    db_session.add(facility)
    await db_session.flush()

    assert facility.id is not None
    assert facility.plafond == 100000.0
    assert facility.percentuale_anticipo == 80.0
    assert facility.tasso_interesse_annuo == 3.5


@pytest.mark.asyncio
async def test_ac_86_invoice_advance_model(db_session: AsyncSession):
    """US-86: InvoiceAdvance model exists with all required fields."""
    tenant = Tenant(
        name="Anticipo Test SRL", type="srl",
        regime_fiscale="ordinario", piva="86868686868",
    )
    db_session.add(tenant)
    await db_session.flush()

    advance = InvoiceAdvance(
        tenant_id=tenant.id,
        facility_id=uuid.uuid4(),
        invoice_id=uuid.uuid4(),
        importo_fattura=10000.0,
        importo_anticipato=8000.0,
        commissione=30.0,
        interessi_stimati=46.67,
        data_presentazione=date(2026, 4, 1),
        data_scadenza_prevista=date(2026, 6, 30),
        stato="attivo",
    )
    db_session.add(advance)
    await db_session.flush()

    assert advance.id is not None
    assert advance.importo_anticipato == 8000.0
    assert advance.stato == "attivo"
