"""Integration tests for Sprint 14: US-49, US-50, US-64, US-65, US-67, US-72."""

import uuid
from datetime import date, timedelta

import pytest
from httpx import AsyncClient

from tests.conftest import get_auth_token


# ── Fixtures ──

@pytest.fixture
async def sprint14_data(db_session, tenant):
    """Create data needed for Sprint 14 tests."""
    from api.db.models import (
        Invoice, BankAccount, BankTransaction, FiscalDeadline,
        PayrollCost, NotificationConfig, WithholdingTax,
    )

    # Bank account with balance
    ba = BankAccount(
        tenant_id=tenant.id,
        iban="IT60X0542811101000000123456",
        bank_name="Banca Test",
        provider="cbi_globe",
        balance=50000.00,
        status="connected",
    )
    db_session.add(ba)
    await db_session.flush()

    # Invoices (active = income, passive = expense)
    for i in range(1, 4):
        db_session.add(Invoice(
            tenant_id=tenant.id, type="attiva", source="cassetto_fiscale",
            numero_fattura=f"FA14/{i}", emittente_piva="12345678901",
            emittente_nome="Cliente Test", data_fattura=date(2026, 3, i * 5),
            importo_netto=3000.0, importo_iva=660.0, importo_totale=3660.0,
            processing_status="registered",
        ))
        db_session.add(Invoice(
            tenant_id=tenant.id, type="passiva", source="cassetto_fiscale",
            numero_fattura=f"FP14/{i}", emittente_piva="98765432109",
            emittente_nome="Fornitore Test", data_fattura=date(2026, 3, i * 5),
            importo_netto=1500.0, importo_iva=330.0, importo_totale=1830.0,
            processing_status="registered",
        ))

    # Bank transactions (unreconciled)
    db_session.add(BankTransaction(
        bank_account_id=ba.id, transaction_id="TX-001",
        date=date(2026, 3, 5), amount=-1830.0, direction="debit",
        counterpart="Fornitore Test", description="Pagamento fattura",
        reconciled=False, source="open_banking",
    ))
    db_session.add(BankTransaction(
        bank_account_id=ba.id, transaction_id="TX-002",
        date=date(2026, 3, 10), amount=3660.0, direction="credit",
        counterpart="Cliente Test", description="Incasso fattura",
        reconciled=False, source="open_banking",
    ))

    # Fiscal deadlines
    db_session.add(FiscalDeadline(
        tenant_id=tenant.id, code="1040", description="Ritenute d'acconto",
        amount=800.0, due_date=date.today() + timedelta(days=10), status="pending",
    ))
    db_session.add(FiscalDeadline(
        tenant_id=tenant.id, code="6031", description="IVA trimestrale",
        amount=2500.0, due_date=date.today() + timedelta(days=30), status="pending",
    ))

    # Payroll
    db_session.add(PayrollCost(
        tenant_id=tenant.id, mese=date(2026, 1, 1),
        dipendente_nome="Riepilogo", importo_lordo=3000, costo_totale_azienda=4200,
    ))
    db_session.add(PayrollCost(
        tenant_id=tenant.id, mese=date(2026, 2, 1),
        dipendente_nome="Riepilogo", importo_lordo=3000, costo_totale_azienda=4200,
    ))

    # Withholding taxes
    inv_result = await db_session.execute(
        __import__("sqlalchemy").select(Invoice).where(
            Invoice.tenant_id == tenant.id, Invoice.type == "passiva"
        )
    )
    passive_inv = inv_result.scalars().first()
    if passive_inv:
        db_session.add(WithholdingTax(
            tenant_id=tenant.id, invoice_id=passive_inv.id,
            tipo_ritenuta="RT01", aliquota=20.0,
            importo_ritenuta=300.0, imponibile_ritenuta=1500.0,
            importo_netto=1200.0, status="detected",
        ))

    await db_session.flush()
    return {"bank_account": ba}


# ═══════════════════════════════════════════════
# US-49: Import F24 versamenti (PDF + LLM)
# ═══════════════════════════════════════════════

@pytest.mark.asyncio
async def test_us49_import_f24_pdf(client: AsyncClient, verified_user, sprint14_data):
    """US-49: Import F24 from PDF returns extracted versamenti."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")

    resp = await client.post(
        "/api/v1/f24/import-pdf",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("f24_test.pdf", b"fake-pdf-content", "application/pdf")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["versamenti_count"] >= 1
    assert len(data["versamenti"]) >= 1
    assert "codice_tributo" in data["versamenti"][0]
    assert "importo" in data["versamenti"][0]


# ═══════════════════════════════════════════════
# US-50: CRUD manuale F24 versamenti
# ═══════════════════════════════════════════════

@pytest.mark.asyncio
async def test_us50_create_versamento(client: AsyncClient, verified_user, sprint14_data):
    """US-50: Create manual F24 versamento."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")

    resp = await client.post(
        "/api/v1/f24/versamenti",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "codice_tributo": "1040",
            "periodo_riferimento": "03/2026",
            "importo": 750.00,
            "data_versamento": "2026-04-16",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["codice_tributo"] == "1040"
    assert data["importo"] == 750.00
    assert "journal_entry_id" in data
    return data["id"]


@pytest.mark.asyncio
async def test_us50_update_versamento(client: AsyncClient, verified_user, sprint14_data):
    """US-50: Update F24 versamento."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")

    # Create first
    create_resp = await client.post(
        "/api/v1/f24/versamenti",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "codice_tributo": "1040",
            "periodo_riferimento": "03/2026",
            "importo": 750.00,
            "data_versamento": "2026-04-16",
        },
    )
    versamento_id = create_resp.json()["id"]

    # Update
    resp = await client.put(
        f"/api/v1/f24/versamenti/{versamento_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"importo": 850.00},
    )
    assert resp.status_code == 200
    assert resp.json()["importo"] == 850.00


@pytest.mark.asyncio
async def test_us50_delete_versamento(client: AsyncClient, verified_user, sprint14_data):
    """US-50: Delete F24 versamento."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")

    # Create first
    create_resp = await client.post(
        "/api/v1/f24/versamenti",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "codice_tributo": "2501",
            "periodo_riferimento": "Q1/2026",
            "importo": 200.00,
            "data_versamento": "2026-04-30",
        },
    )
    versamento_id = create_resp.json()["id"]

    resp = await client.delete(
        f"/api/v1/f24/versamenti/{versamento_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True


# ═══════════════════════════════════════════════
# US-64: Cash Flow Agent potenziato
# ═══════════════════════════════════════════════

@pytest.mark.asyncio
async def test_us64_enhanced_cashflow(client: AsyncClient, verified_user, sprint14_data):
    """US-64: Enhanced cash flow returns comprehensive data."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")

    resp = await client.get(
        "/api/v1/cashflow/enhanced?days=90",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "bank_balance" in data
    assert "expected_income" in data
    assert "expected_expenses" in data
    assert "payroll_monthly" in data
    assert "projected_balance" in data
    assert "risk_level" in data
    assert data["bank_balance"] == 50000.00


# ═══════════════════════════════════════════════
# US-65: Adempimenti Agent proattivo
# ═══════════════════════════════════════════════

@pytest.mark.asyncio
async def test_us65_proactive_deadlines(client: AsyncClient, verified_user, sprint14_data):
    """US-65: Proactive deadlines returns upcoming with calculated amounts."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")

    resp = await client.get(
        "/api/v1/deadlines/proactive?days=60",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "deadlines" in data
    assert "estimates" in data
    assert data["total_count"] >= 1
    assert data["total_amount"] > 0
    # Should have estimates
    assert "iva_trimestrale_stima" in data["estimates"]
    assert "ritenute_mensili_stima" in data["estimates"]
    assert "costo_personale_mensile" in data["estimates"]


# ═══════════════════════════════════════════════
# US-67: Doppio canale notifiche
# ═══════════════════════════════════════════════

@pytest.mark.asyncio
async def test_us67_push_notification_fallback(client: AsyncClient, verified_user, sprint14_data):
    """US-67: Push notification falls back to email when no channel configured."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")

    resp = await client.post(
        "/api/v1/notifications/push",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "message": "Scadenza IVA in 7 giorni",
            "message_type": "scadenza",
            "channel": "telegram",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_sent"] >= 1
    assert data["channels"][0]["channel"] == "email_fallback"


@pytest.mark.asyncio
async def test_us67_push_notification_telegram(client: AsyncClient, verified_user, sprint14_data, db_session, tenant):
    """US-67: Push notification sends to configured Telegram channel."""
    from api.db.models import NotificationConfig

    # Configure Telegram
    config = NotificationConfig(
        user_id=verified_user.id,
        tenant_id=tenant.id,
        channel="telegram",
        chat_id="123456789",
        enabled=True,
    )
    db_session.add(config)
    await db_session.flush()

    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")

    resp = await client.post(
        "/api/v1/notifications/push",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "message": "F24 in scadenza",
            "channel": "telegram",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_sent"] >= 1
    assert data["channels"][0]["channel"] == "telegram"
    assert data["channels"][0]["success"] is True


# ═══════════════════════════════════════════════
# US-72: Riconciliazione Agent
# ═══════════════════════════════════════════════

@pytest.mark.asyncio
async def test_us72_auto_match(client: AsyncClient, verified_user, sprint14_data):
    """US-72: Auto-match bank transactions to invoices."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")

    resp = await client.post(
        "/api/v1/reconciliation/auto-match",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "matched" in data
    assert "unmatched" in data
    assert "matches" in data
    assert isinstance(data["matches"], list)
