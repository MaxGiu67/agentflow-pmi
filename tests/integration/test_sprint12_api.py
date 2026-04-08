"""Integration tests for Sprint 12: Saldi Bilancio + CRUD (US-46, US-48, US-51, US-52, US-54)."""

import io
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from tests.conftest import get_auth_token


@pytest.fixture
async def bank_account(db_session, tenant):
    from api.db.models import BankAccount
    ba = BankAccount(tenant_id=tenant.id, iban="IT1234", bank_name="Test", provider="manual", status="connected")
    db_session.add(ba)
    await db_session.flush()
    return ba


# ═══════════════════════════════════════════════
# US-46: CRUD manuale movimenti bancari
# ═══════════════════════════════════════════════

@pytest.mark.asyncio
async def test_ac_46_1_create_manual_transaction(client: AsyncClient, verified_user, bank_account):
    """AC-46.1: Creare un movimento manuale."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")
    resp = await client.post(
        "/api/v1/bank-accounts/transactions",
        headers={"Authorization": f"Bearer {token}"},
        json={"bank_account_id": str(bank_account.id), "date": "2024-04-01", "description": "Pagamento manuale", "amount": 500.0, "direction": "debit"},
    )
    assert resp.status_code == 201
    assert resp.json()["source"] == "manual"


@pytest.mark.asyncio
async def test_ac_46_2_update_transaction(client: AsyncClient, verified_user, bank_account, db_session):
    """AC-46.2: Modificare un movimento esistente."""
    from api.db.models import BankTransaction
    tx = BankTransaction(bank_account_id=bank_account.id, transaction_id="MAN-test", date=date(2024, 4, 1), amount=100, direction="debit", description="Originale", source="manual")
    db_session.add(tx)
    await db_session.flush()

    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")
    resp = await client.put(
        f"/api/v1/bank-accounts/transactions/{tx.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"description": "Modificato", "amount": 200},
    )
    assert resp.status_code == 200
    assert resp.json()["updated"] is True


@pytest.mark.asyncio
async def test_ac_46_3_delete_transaction(client: AsyncClient, verified_user, bank_account, db_session):
    """AC-46.3: Eliminare un movimento."""
    from api.db.models import BankTransaction
    tx = BankTransaction(bank_account_id=bank_account.id, transaction_id="MAN-del", date=date(2024, 4, 1), amount=50, direction="credit", description="Da eliminare", source="manual")
    db_session.add(tx)
    await db_session.flush()

    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")
    resp = await client.delete(
        f"/api/v1/bank-accounts/transactions/{tx.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True


# ═══════════════════════════════════════════════
# US-48: CRUD manuale corrispettivi
# ═══════════════════════════════════════════════

@pytest.mark.asyncio
async def test_ac_48_1_create_manual_corrispettivo(client: AsyncClient, verified_user):
    """AC-48.1: Creare un corrispettivo manuale."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")
    resp = await client.post(
        "/api/v1/corrispettivi",
        headers={"Authorization": f"Bearer {token}"},
        json={"data": "2024-03-15", "imponibile": 1000, "imposta": 220, "totale_contanti": 500, "totale_elettronico": 720, "num_documenti": 15},
    )
    assert resp.status_code == 201
    assert resp.json()["source"] == "manual"


@pytest.mark.asyncio
async def test_ac_48_2_update_corrispettivo(client: AsyncClient, verified_user, db_session, tenant):
    """AC-48.2: Modificare un corrispettivo."""
    from api.db.models import Corrispettivo
    c = Corrispettivo(tenant_id=tenant.id, data=date(2024, 3, 15), imponibile=1000, imposta=220, totale_contanti=500, totale_elettronico=720, num_documenti=10, source="manual")
    db_session.add(c)
    await db_session.flush()

    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")
    resp = await client.put(
        f"/api/v1/corrispettivi/{c.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"imponibile": 1500, "num_documenti": 20},
    )
    assert resp.status_code == 200
    assert resp.json()["updated"] is True


@pytest.mark.asyncio
async def test_ac_48_2_delete_corrispettivo(client: AsyncClient, verified_user, db_session, tenant):
    """AC-48.2: Eliminare un corrispettivo."""
    from api.db.models import Corrispettivo
    c = Corrispettivo(tenant_id=tenant.id, data=date(2024, 3, 16), imponibile=500, imposta=110, totale_contanti=200, totale_elettronico=410, num_documenti=5, source="manual")
    db_session.add(c)
    await db_session.flush()

    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")
    resp = await client.delete(
        f"/api/v1/corrispettivi/{c.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True


# ═══════════════════════════════════════════════
# US-51: Import saldi bilancio (Excel/CSV)
# ═══════════════════════════════════════════════

BILANCIO_CSV = """\
Codice;Descrizione;Dare;Avere
15150000;Banca c/c;23.450,00;
15040000;Crediti vs clienti;45.000,00;
37030000;Debiti vs fornitori;;32.000,00
31000000;Capitale sociale;;10.000,00
31030030;Utili precedenti;;26.450,00
"""


@pytest.mark.asyncio
async def test_ac_51_1_csv_auto_detect_columns(client: AsyncClient, verified_user):
    """AC-51.1: Upload CSV → auto-detect colonne (codice, descrizione, dare, avere)."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")
    csv_file = io.BytesIO(BILANCIO_CSV.encode("utf-8"))
    resp = await client.post(
        "/api/v1/accounting/import-bilancio",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("bilancio.csv", csv_file, "text/csv")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["lines_count"] == 5
    assert data["extraction_method"] == "csv"
    assert data["columns_detected"]["codice"] == "Codice"
    assert data["columns_detected"]["dare"] == "Dare"


@pytest.mark.asyncio
async def test_ac_51_3_csv_balanced(client: AsyncClient, verified_user):
    """AC-51.3: Import bilanciato → dare == avere."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")
    csv_file = io.BytesIO(BILANCIO_CSV.encode("utf-8"))
    resp = await client.post(
        "/api/v1/accounting/import-bilancio",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("bilancio.csv", csv_file, "text/csv")},
    )
    data = resp.json()
    assert data["bilanciato"] is True
    assert data["totale_dare"] == data["totale_avere"]


@pytest.mark.asyncio
async def test_ac_51_4_confirm_creates_journal_entry(client: AsyncClient, verified_user, db_session):
    """AC-51.3+: Conferma import → crea scrittura di apertura."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")

    lines = [
        {"codice_conto": "15150000", "descrizione": "Banca c/c", "dare": 23450, "avere": 0},
        {"codice_conto": "31000000", "descrizione": "Capitale sociale", "dare": 0, "avere": 23450},
    ]
    resp = await client.post(
        "/api/v1/accounting/confirm-bilancio",
        headers={"Authorization": f"Bearer {token}"},
        json={"lines": lines, "description": "Saldi iniziali test"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["bilanciato"] is True
    assert data["lines_saved"] == 2
    assert data["journal_entry_id"]


# ═══════════════════════════════════════════════
# US-52: Import saldi bilancio (PDF + LLM)
# ═══════════════════════════════════════════════

MOCK_LLM_BILANCIO = [
    {"codice_conto": "15150000", "descrizione": "Depositi bancari", "dare": 73556.21, "avere": 0},
    {"codice_conto": "15040000", "descrizione": "Crediti vs clienti", "dare": 1819019.96, "avere": 0},
    {"codice_conto": "37030000", "descrizione": "Debiti vs fornitori", "dare": 0, "avere": 1726985.81},
    {"codice_conto": "31000000", "descrizione": "Capitale sociale", "dare": 0, "avere": 350000.00},
]


@pytest.mark.asyncio
async def test_ac_52_1_pdf_llm_extraction(client: AsyncClient, verified_user):
    """AC-52.1: Upload PDF bilancio → async processing returns job_id."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")

    with (
        patch("api.modules.banking.import_service.extract_text_from_pdf", return_value="SITUAZIONE CONTABILE TAAL SRL Esercizio 2023 " * 10),
        patch("api.modules.bilancio_import.service._extract_bilancio_llm", new_callable=AsyncMock, return_value=MOCK_LLM_BILANCIO),
    ):
        fake_pdf = io.BytesIO(b"%PDF-1.4 bilancio test content")
        resp = await client.post(
            "/api/v1/accounting/import-bilancio",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("bilancio.pdf", fake_pdf, "application/pdf")},
        )

    assert resp.status_code == 200
    data = resp.json()
    # PDF imports are now async — returns job_id for polling
    assert "job_id" in data
    assert data["status"] == "processing"


# ═══════════════════════════════════════════════
# US-54: CRUD manuale saldi bilancio (wizard)
# ═══════════════════════════════════════════════

@pytest.mark.asyncio
async def test_ac_54_1_wizard_creates_balanced_entry(client: AsyncClient, verified_user):
    """AC-54.1: Wizard saldi principali → crea scrittura bilanciata con auto-quadratura."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")
    resp = await client.post(
        "/api/v1/accounting/initial-balances/wizard",
        headers={"Authorization": f"Bearer {token}"},
        json={"banca": 23450, "crediti_clienti": 45000, "debiti_fornitori": 32000, "capitale_sociale": 10000},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["bilanciato"] is True
    assert data["journal_entry_id"]
    assert data["lines_saved"] >= 4  # 4 conti + 1 quadratura


@pytest.mark.asyncio
async def test_ac_54_2_wizard_auto_balances(client: AsyncClient, verified_user):
    """AC-54.2: Se dare != avere, la quadratura viene aggiunta automaticamente."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")
    # Solo banca (dare) e capitale (avere) — non bilanciano
    resp = await client.post(
        "/api/v1/accounting/initial-balances/wizard",
        headers={"Authorization": f"Bearer {token}"},
        json={"banca": 50000, "capitale_sociale": 10000},
    )
    assert resp.status_code == 200
    data = resp.json()
    # Auto-balanced with "utili esercizi precedenti"
    assert data["bilanciato"] is True
    assert data["totale_dare"] == data["totale_avere"]
