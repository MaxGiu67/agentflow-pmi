"""Integration tests for Sprint 16: US-55, US-56, US-57, US-58, US-63, US-70."""

import uuid
from datetime import date, timedelta

import pytest
from httpx import AsyncClient

from tests.conftest import get_auth_token


# ── Fixtures ──

@pytest.fixture
async def sprint16_data(db_session, tenant):
    """Create data needed for Sprint 16 tests."""
    from api.db.models import Invoice, PayrollCost, Budget

    # Invoices for cost analysis
    for i in range(1, 4):
        db_session.add(Invoice(
            tenant_id=tenant.id, type="attiva", source="cassetto_fiscale",
            numero_fattura=f"FA16/{i}", emittente_piva="12345678901",
            emittente_nome="Cliente", data_fattura=date(2026, 3, i * 5),
            importo_netto=4000.0, importo_iva=880.0, importo_totale=4880.0,
            processing_status="registered",
        ))
        db_session.add(Invoice(
            tenant_id=tenant.id, type="passiva", source="cassetto_fiscale",
            numero_fattura=f"FP16/{i}", emittente_piva="98765432109",
            emittente_nome="Fornitore", data_fattura=date(2026, 3, i * 5),
            importo_netto=2000.0, importo_iva=440.0, importo_totale=2440.0,
            processing_status="registered",
        ))

    # Previous month data (Feb)
    for i in range(1, 3):
        db_session.add(Invoice(
            tenant_id=tenant.id, type="attiva", source="cassetto_fiscale",
            numero_fattura=f"FA16-FEB/{i}", emittente_piva="12345678901",
            emittente_nome="Cliente", data_fattura=date(2026, 2, i * 10),
            importo_netto=3500.0, importo_iva=770.0, importo_totale=4270.0,
            processing_status="registered",
        ))
        db_session.add(Invoice(
            tenant_id=tenant.id, type="passiva", source="cassetto_fiscale",
            numero_fattura=f"FP16-FEB/{i}", emittente_piva="98765432109",
            emittente_nome="Fornitore", data_fattura=date(2026, 2, i * 10),
            importo_netto=1500.0, importo_iva=330.0, importo_totale=1830.0,
            processing_status="registered",
        ))

    # Payroll
    db_session.add(PayrollCost(
        tenant_id=tenant.id, mese=date(2026, 3, 1),
        dipendente_nome="Riepilogo", importo_lordo=3000, costo_totale_azienda=4200,
    ))
    db_session.add(PayrollCost(
        tenant_id=tenant.id, mese=date(2026, 2, 1),
        dipendente_nome="Riepilogo", importo_lordo=3000, costo_totale_azienda=4200,
    ))

    await db_session.flush()


# ═══════════════════════════════════════════════
# US-55+56: Contratti ricorrenti import + CRUD
# ═══════════════════════════════════════════════

@pytest.mark.asyncio
async def test_us55_import_contracts_pdf(client: AsyncClient, verified_user, sprint16_data):
    """US-55: Import recurring contracts from PDF."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")

    resp = await client.post(
        "/api/v1/recurring-contracts/import-pdf",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("contratti.pdf", b"fake-pdf", "application/pdf")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["contracts_count"] >= 1
    assert len(data["contracts"]) >= 1


@pytest.mark.asyncio
async def test_us56_create_contract(client: AsyncClient, verified_user, sprint16_data):
    """US-56: Create recurring contract."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")

    resp = await client.post(
        "/api/v1/recurring-contracts",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "description": "Canone hosting",
            "counterpart": "AWS",
            "amount": 200.0,
            "frequency": "monthly",
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "category": "infrastruttura",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["description"] == "Canone hosting"
    assert data["amount"] == 200.0
    assert data["status"] == "active"
    return data["id"]


@pytest.mark.asyncio
async def test_us56_list_contracts(client: AsyncClient, verified_user, sprint16_data):
    """US-56: List recurring contracts."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")

    # Create one first
    await client.post(
        "/api/v1/recurring-contracts",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "description": "Test contract",
            "amount": 100.0,
            "start_date": "2026-01-01",
        },
    )

    resp = await client.get(
        "/api/v1/recurring-contracts",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert len(data["contracts"]) >= 1


@pytest.mark.asyncio
async def test_us56_update_contract(client: AsyncClient, verified_user, sprint16_data):
    """US-56: Update recurring contract."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")

    # Create
    create_resp = await client.post(
        "/api/v1/recurring-contracts",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "description": "Original",
            "amount": 100.0,
            "start_date": "2026-01-01",
        },
    )
    contract_id = create_resp.json()["id"]

    # Update
    resp = await client.put(
        f"/api/v1/recurring-contracts/{contract_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"description": "Updated", "amount": 150.0},
    )
    assert resp.status_code == 200
    assert resp.json()["description"] == "Updated"
    assert resp.json()["amount"] == 150.0


@pytest.mark.asyncio
async def test_us56_delete_contract(client: AsyncClient, verified_user, sprint16_data):
    """US-56: Delete recurring contract."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")

    # Create
    create_resp = await client.post(
        "/api/v1/recurring-contracts",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "description": "To delete",
            "amount": 50.0,
            "start_date": "2026-01-01",
        },
    )
    contract_id = create_resp.json()["id"]

    resp = await client.delete(
        f"/api/v1/recurring-contracts/{contract_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True


# ═══════════════════════════════════════════════
# US-57+58: Finanziamenti/mutui import + CRUD
# ═══════════════════════════════════════════════

@pytest.mark.asyncio
async def test_us57_import_loans_pdf(client: AsyncClient, verified_user, sprint16_data):
    """US-57: Import loans from PDF."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")

    resp = await client.post(
        "/api/v1/loans/import-pdf",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("mutuo.pdf", b"fake-pdf", "application/pdf")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["loans_count"] >= 1
    assert len(data["loans"]) >= 1


@pytest.mark.asyncio
async def test_us58_create_loan(client: AsyncClient, verified_user, sprint16_data):
    """US-58: Create loan."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")

    resp = await client.post(
        "/api/v1/loans",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "description": "Mutuo ufficio",
            "lender": "UniCredit",
            "principal": 80000.0,
            "interest_rate": 2.5,
            "installment_amount": 800.0,
            "frequency": "monthly",
            "start_date": "2025-06-01",
            "end_date": "2035-06-01",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["description"] == "Mutuo ufficio"
    assert data["principal"] == 80000.0
    assert data["remaining_principal"] == 80000.0
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_us58_list_loans(client: AsyncClient, verified_user, sprint16_data):
    """US-58: List loans."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")

    # Create one
    await client.post(
        "/api/v1/loans",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "description": "Test loan",
            "principal": 10000.0,
            "interest_rate": 3.0,
            "installment_amount": 200.0,
            "start_date": "2026-01-01",
        },
    )

    resp = await client.get(
        "/api/v1/loans",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_us58_update_loan(client: AsyncClient, verified_user, sprint16_data):
    """US-58: Update loan."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")

    # Create
    create_resp = await client.post(
        "/api/v1/loans",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "description": "Original loan",
            "principal": 50000.0,
            "interest_rate": 3.0,
            "installment_amount": 500.0,
            "start_date": "2026-01-01",
        },
    )
    loan_id = create_resp.json()["id"]

    # Update
    resp = await client.put(
        f"/api/v1/loans/{loan_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"description": "Updated loan", "remaining_principal": 45000.0},
    )
    assert resp.status_code == 200
    assert resp.json()["description"] == "Updated loan"
    assert resp.json()["remaining_principal"] == 45000.0


@pytest.mark.asyncio
async def test_us58_delete_loan(client: AsyncClient, verified_user, sprint16_data):
    """US-58: Delete loan."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")

    # Create
    create_resp = await client.post(
        "/api/v1/loans",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "description": "To delete",
            "principal": 5000.0,
            "interest_rate": 2.0,
            "installment_amount": 100.0,
            "start_date": "2026-01-01",
        },
    )
    loan_id = create_resp.json()["id"]

    resp = await client.delete(
        f"/api/v1/loans/{loan_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True


# ═══════════════════════════════════════════════
# US-63: Controller "Dove perdo soldi?"
# ═══════════════════════════════════════════════

@pytest.mark.asyncio
async def test_us63_cost_analysis(client: AsyncClient, verified_user, sprint16_data):
    """US-63: Cost analysis returns top 5 categories with comparison."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")

    resp = await client.get(
        "/api/v1/controller/cost-analysis?year=2026&month=3",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "top_costs" in data
    assert "total_costs" in data
    assert "ricavi" in data
    assert "incidenza_costi_pct" in data
    assert "anomalies" in data
    assert data["total_costs"] > 0


@pytest.mark.asyncio
async def test_us63_cost_analysis_previous_comparison(client: AsyncClient, verified_user, sprint16_data):
    """US-63: Cost analysis compares with previous period."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")

    resp = await client.get(
        "/api/v1/controller/cost-analysis?year=2026&month=3",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()

    # Should have comparison data
    if data["top_costs"]:
        cost = data["top_costs"][0]
        assert "current" in cost
        assert "previous" in cost
        assert "change_pct" in cost
        assert "direction" in cost


# ═══════════════════════════════════════════════
# US-70: Email per commercialista
# ═══════════════════════════════════════════════

@pytest.mark.asyncio
async def test_us70_generate_email_bilancio(client: AsyncClient, verified_user, sprint16_data):
    """US-70: Generate bilancio request email template."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")

    resp = await client.post(
        "/api/v1/communications/generate-email",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "template_type": "bilancio_request",
            "year": 2025,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["template_type"] == "bilancio_request"
    assert "subject" in data
    assert "body" in data
    assert "bilancio" in data["body"].lower()
    assert "2025" in data["body"]


@pytest.mark.asyncio
async def test_us70_generate_email_f24(client: AsyncClient, verified_user, sprint16_data):
    """US-70: Generate F24 request email template."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")

    resp = await client.post(
        "/api/v1/communications/generate-email",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "template_type": "f24_request",
            "year": 2025,
            "notes": "Urgente, serve entro venerdi",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["template_type"] == "f24_request"
    assert "F24" in data["subject"]
    assert "Urgente" in data["body"]


@pytest.mark.asyncio
async def test_us70_generate_email_document_request(client: AsyncClient, verified_user, sprint16_data):
    """US-70: Generate document request email template."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")

    resp = await client.post(
        "/api/v1/communications/generate-email",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "template_type": "document_request",
            "year": 2025,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["template_type"] == "document_request"
    assert "subject" in data
    assert "body" in data
