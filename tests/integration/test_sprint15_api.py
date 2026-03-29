"""Integration tests for Sprint 15: US-68, US-53, US-59, US-66."""

import uuid
from datetime import date, timedelta

import pytest
from httpx import AsyncClient

from tests.conftest import get_auth_token


# ── Fixtures ──

@pytest.fixture
async def sprint15_data(db_session, tenant):
    """Create data needed for Sprint 15 tests."""
    from api.db.models import (
        Invoice, BankAccount, BankTransaction, Budget,
        ImportException, FiscalDeadline,
    )

    # Bank account
    ba = BankAccount(
        tenant_id=tenant.id,
        iban="IT60X0542811101000000123456",
        bank_name="Banca Test",
        provider="cbi_globe",
        balance=30000.00,
        status="connected",
    )
    db_session.add(ba)
    await db_session.flush()

    # Invoices with categories that match immobilizzazioni
    db_session.add(Invoice(
        tenant_id=tenant.id, type="passiva", source="cassetto_fiscale",
        numero_fattura="FP-HW-001", emittente_piva="11223344556",
        emittente_nome="TechShop SRL", data_fattura=date(2026, 2, 15),
        importo_netto=2500.0, importo_iva=550.0, importo_totale=3050.0,
        category="hardware", processing_status="registered",
    ))
    db_session.add(Invoice(
        tenant_id=tenant.id, type="passiva", source="cassetto_fiscale",
        numero_fattura="FP-MOB-001", emittente_piva="11223344557",
        emittente_nome="Mobili Ufficio SRL", data_fattura=date(2026, 2, 20),
        importo_netto=400.0, importo_iva=88.0, importo_totale=488.0,
        category="mobili", processing_status="registered",
    ))
    db_session.add(Invoice(
        tenant_id=tenant.id, type="passiva", source="cassetto_fiscale",
        numero_fattura="FP-SW-001", emittente_piva="11223344558",
        emittente_nome="Software House", data_fattura=date(2026, 1, 10),
        importo_netto=800.0, importo_iva=176.0, importo_totale=976.0,
        category="software", processing_status="registered",
    ))

    # Active invoices for ricavi
    db_session.add(Invoice(
        tenant_id=tenant.id, type="attiva", source="cassetto_fiscale",
        numero_fattura="FA15/1", emittente_piva="12345678901",
        emittente_nome="Cliente A", data_fattura=date(2026, 3, 1),
        importo_netto=5000.0, importo_iva=1100.0, importo_totale=6100.0,
        processing_status="registered",
    ))

    # Overdue passive invoices (for alert agent)
    db_session.add(Invoice(
        tenant_id=tenant.id, type="passiva", source="cassetto_fiscale",
        numero_fattura="FP-OLD-001", emittente_piva="99887766554",
        emittente_nome="Fornitore Vecchio", data_fattura=date.today() - timedelta(days=45),
        importo_netto=2000.0, importo_iva=440.0, importo_totale=2440.0,
        processing_status="pending",
    ))

    # Old active invoices (missing payment)
    db_session.add(Invoice(
        tenant_id=tenant.id, type="attiva", source="cassetto_fiscale",
        numero_fattura="FA-OLD-001", emittente_piva="12345678901",
        emittente_nome="Cliente Lento", data_fattura=date.today() - timedelta(days=90),
        importo_netto=3000.0, importo_iva=660.0, importo_totale=3660.0,
        processing_status="registered",
    ))

    # Bank transactions (for unusual amounts)
    for i in range(10):
        db_session.add(BankTransaction(
            bank_account_id=ba.id, transaction_id=f"TX-15-{i:03d}",
            date=date(2026, 2, 1 + i), amount=-500.0, direction="debit",
            counterpart="Fornitore Regolare", reconciled=True, source="open_banking",
        ))
    # One outlier
    db_session.add(BankTransaction(
        bank_account_id=ba.id, transaction_id="TX-15-OUTLIER",
        date=date(2026, 2, 20), amount=-15000.0, direction="debit",
        counterpart="Acquisto Anomalo", reconciled=True, source="open_banking",
    ))

    # Budget
    db_session.add(Budget(
        tenant_id=tenant.id, year=2026, month=3, category="ricavi", budget_amount=6000.0,
    ))

    # Import exceptions (pending actions)
    db_session.add(ImportException(
        tenant_id=tenant.id, source_type="fatture", severity="warning",
        title="Fattura duplicata", action_label="Verifica",
    ))
    db_session.add(ImportException(
        tenant_id=tenant.id, source_type="banca", severity="error",
        title="Movimento non categorizzato", action_label="Categorizza",
    ))

    # Fiscal deadlines for home
    db_session.add(FiscalDeadline(
        tenant_id=tenant.id, code="1040", description="Ritenute",
        amount=600.0, due_date=date.today() + timedelta(days=10), status="pending",
    ))

    await db_session.flush()
    return {"bank_account": ba}


# ═══════════════════════════════════════════════
# US-68: Home conversazionale
# ═══════════════════════════════════════════════

@pytest.mark.asyncio
async def test_us68_home_summary(client: AsyncClient, verified_user, sprint15_data):
    """US-68: Home summary returns greeting, ricavi, saldo, uscite, azioni."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")

    resp = await client.get(
        "/api/v1/home/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "greeting" in data
    assert "Mario" in data["greeting"]
    assert "ricavi_mese" in data
    assert "saldo_banca" in data
    assert data["saldo_banca"] == 30000.0
    assert "prossime_uscite" in data
    assert "azioni_pendenti" in data
    assert data["azioni_pendenti_count"] <= 3


# ═══════════════════════════════════════════════
# US-53: Import saldi bilancio XBRL
# ═══════════════════════════════════════════════

@pytest.mark.asyncio
async def test_us53_import_xbrl(client: AsyncClient, verified_user, sprint15_data):
    """US-53: Import bilancio from XBRL file."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")

    # Simple XBRL-like XML
    xbrl_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance"
            xmlns:itcc-ci="http://www.infocamere.it/itcc-ci">
  <itcc-ci:A_III_ImmobilizzazioniMateriali>50000.00</itcc-ci:A_III_ImmobilizzazioniMateriali>
  <itcc-ci:B_II_Crediti>25000.00</itcc-ci:B_II_Crediti>
  <itcc-ci:C_I_DisponibilitaLiquide>15000.00</itcc-ci:C_I_DisponibilitaLiquide>
</xbrli:xbrl>"""

    resp = await client.post(
        "/api/v1/accounting/import-bilancio",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("bilancio.xbrl", xbrl_content, "application/xml")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["extraction_method"] == "xbrl"
    assert data["lines_count"] >= 1
    assert data["totale_dare"] >= 0


@pytest.mark.asyncio
async def test_us53_import_xml_extension(client: AsyncClient, verified_user, sprint15_data):
    """US-53: Import bilancio from .xml file triggers XBRL parser."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")

    xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<root><item>test</item></root>"""

    resp = await client.post(
        "/api/v1/accounting/import-bilancio",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("bilancio.xml", xml_content, "application/xml")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["extraction_method"] == "xbrl"


# ═══════════════════════════════════════════════
# US-59: Ammortamenti auto da fatture
# ═══════════════════════════════════════════════

@pytest.mark.asyncio
async def test_us59_auto_detect_assets(client: AsyncClient, verified_user, sprint15_data):
    """US-59: Auto-detect immobilizzazioni from invoices."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")

    resp = await client.post(
        "/api/v1/assets/auto-detect",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_count"] >= 2  # hardware + mobili + software
    assert data["total_amount"] > 0

    # Check specific proposals
    proposals = data["proposals"]
    hw_proposals = [p for p in proposals if "hardware" in p["category"].lower()]
    if hw_proposals:
        assert hw_proposals[0]["depreciation_rate"] == 20.0

    # Check full deduction threshold (mobili at 400 EUR < 516.46)
    small_proposals = [p for p in proposals if p["purchase_amount"] <= 516.46]
    for sp in small_proposals:
        assert sp["full_deduction"] is True


@pytest.mark.asyncio
async def test_us59_confirm_asset(client: AsyncClient, verified_user, sprint15_data, db_session, tenant):
    """US-59: Confirm an invoice as fixed asset."""
    from api.db.models import Invoice
    from sqlalchemy import select

    # Get a hardware invoice
    result = await db_session.execute(
        select(Invoice).where(
            Invoice.tenant_id == tenant.id,
            Invoice.category == "hardware",
        )
    )
    inv = result.scalar_one()

    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")

    resp = await client.post(
        "/api/v1/assets/confirm",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "invoice_id": str(inv.id),
            "depreciation_rate": 20.0,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "asset_id" in data
    assert data["purchase_amount"] == 2500.0


# ═══════════════════════════════════════════════
# US-66: Alert Agent
# ═══════════════════════════════════════════════

@pytest.mark.asyncio
async def test_us66_alert_scan(client: AsyncClient, verified_user, sprint15_data):
    """US-66: Alert scan returns anomalies."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")

    resp = await client.get(
        "/api/v1/alerts/scan",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "alerts" in data
    assert "total" in data
    assert "critical_count" in data
    assert "warning_count" in data

    # Should find overdue invoices and/or unusual amounts
    assert data["total"] >= 1

    # Check alert structure
    if data["alerts"]:
        alert = data["alerts"][0]
        assert "type" in alert
        assert "severity" in alert
        assert "title" in alert
