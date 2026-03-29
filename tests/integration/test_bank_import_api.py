"""Integration tests for bank statement import (US-44).

Tests the PDF import endpoint with LLM extraction mock.
"""

import io
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from tests.conftest import get_auth_token


@pytest.fixture
async def bank_account(db_session, tenant):
    """Create a test bank account."""
    from api.db.models import BankAccount
    account = BankAccount(
        tenant_id=tenant.id,
        iban="IT29H0200805239000104371230",
        bank_name="UniCredit",
        provider="manual",
        status="connected",
    )
    db_session.add(account)
    await db_session.flush()
    return account


MOCK_LLM_RESPONSE = [
    {
        "data_operazione": "2024-04-02",
        "data_valuta": "2024-04-01",
        "descrizione": "IMPRENDO ONE: COSTO FISSO MESE DI MARZO 2024",
        "dare": 8.78,
        "avere": 0,
    },
    {
        "data_operazione": "2024-04-12",
        "data_valuta": "2024-04-12",
        "descrizione": "BONIFICO SEPA DA: TAAL - S.R.L.",
        "dare": 0,
        "avere": 2318.00,
    },
    {
        "data_operazione": "2024-04-16",
        "data_valuta": "2024-04-16",
        "descrizione": "DISPOSIZIONE PAGAMENTO STIPENDI",
        "dare": 905.00,
        "avere": 0,
    },
]


# --- AC-44.1: Upload PDF → LLM extraction → structured movements ---

@pytest.mark.asyncio
async def test_ac_44_1_import_pdf_extracts_movements(client: AsyncClient, verified_user, bank_account):
    """AC-44.1: DATO un PDF estratto conto, QUANDO lo carico, ALLORA il sistema estrae i movimenti con LLM."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")

    # Mock pdftotext output and LLM extraction
    mock_text = "Estratto conto al 30.06.2024\nData Valuta Descrizione Uscite Entrate\n..."

    with (
        patch("api.modules.banking.import_service.extract_text_from_pdf", return_value=mock_text),
        patch("api.modules.banking.import_service.extract_movements_llm", new_callable=AsyncMock, return_value=MOCK_LLM_RESPONSE),
    ):
        # Create a fake PDF file
        fake_pdf = io.BytesIO(b"%PDF-1.4 fake content for testing")
        fake_pdf.name = "estratto_conto_test.pdf"

        resp = await client.post(
            f"/api/v1/bank-accounts/{bank_account.id}/import-statement",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("estratto_conto_test.pdf", fake_pdf, "application/pdf")},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["movements_count"] == 3
    assert data["extraction_method"] == "llm"
    assert data["status"] == "processed"
    assert len(data["movements"]) == 3

    # Check first movement (debit)
    m0 = data["movements"][0]
    assert m0["data_operazione"] == "2024-04-02"
    assert m0["dare"] == 8.78
    assert m0["direzione"] == "debit"

    # Check second movement (credit)
    m1 = data["movements"][1]
    assert m1["avere"] == 2318.00
    assert m1["direzione"] == "credit"


# --- AC-44.2: Preview → user can confirm or modify ---

@pytest.mark.asyncio
async def test_ac_44_2_preview_returns_modifiable_data(client: AsyncClient, verified_user, bank_account):
    """AC-44.2: DATO un estratto conto parsato, QUANDO viene mostrata la preview, ALLORA posso confermare o modificare."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")

    with (
        patch("api.modules.banking.import_service.extract_text_from_pdf", return_value="Estratto conto al 30.06.2024 - ELENCO MOVIMENTI con dati sufficienti per il parsing"),
        patch("api.modules.banking.import_service.extract_movements_llm", new_callable=AsyncMock, return_value=MOCK_LLM_RESPONSE),
    ):
        fake_pdf = io.BytesIO(b"%PDF-1.4 fake")
        resp = await client.post(
            f"/api/v1/bank-accounts/{bank_account.id}/import-statement",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("test.pdf", fake_pdf, "application/pdf")},
        )

    assert resp.status_code == 200
    data = resp.json()

    # Preview data contains all fields needed for modification
    for m in data["movements"]:
        assert "data_operazione" in m
        assert "descrizione" in m
        assert "dare" in m
        assert "avere" in m
        assert "direzione" in m

    # User can modify and send back via confirm-import
    modified_movements = data["movements"]
    modified_movements[0]["descrizione"] = "MODIFICATO: costo fisso"

    resp2 = await client.post(
        f"/api/v1/bank-accounts/{bank_account.id}/confirm-import",
        headers={"Authorization": f"Bearer {token}"},
        json={"movements": modified_movements},
    )
    assert resp2.status_code == 200
    assert resp2.json()["saved"] == 3


# --- AC-44.3: Confirmed import → source=import_pdf + reconciliation ---

@pytest.mark.asyncio
async def test_ac_44_3_confirm_saves_with_source_import_pdf(client: AsyncClient, verified_user, bank_account, db_session):
    """AC-44.3: DATO un import confermato, QUANDO i movimenti vengono salvati, ALLORA source=import_pdf."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")

    movements = [
        {
            "data_operazione": "2024-04-02",
            "data_valuta": "2024-04-01",
            "descrizione": "COSTO FISSO MARZO",
            "dare": 8.78,
            "avere": 0,
            "importo": -8.78,
            "direzione": "debit",
        },
        {
            "data_operazione": "2024-04-12",
            "data_valuta": "2024-04-12",
            "descrizione": "BONIFICO TAAL",
            "dare": 0,
            "avere": 2318.00,
            "importo": 2318.00,
            "direzione": "credit",
        },
    ]

    resp = await client.post(
        f"/api/v1/bank-accounts/{bank_account.id}/confirm-import",
        headers={"Authorization": f"Bearer {token}"},
        json={"movements": movements},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["saved"] == 2
    assert data["source"] == "import_pdf"

    # Verify in DB
    from sqlalchemy import select
    from api.db.models import BankTransaction
    result = await db_session.execute(
        select(BankTransaction).where(BankTransaction.bank_account_id == bank_account.id)
    )
    txs = result.scalars().all()
    assert len(txs) == 2
    assert all(tx.source == "import_pdf" for tx in txs)


# --- AC-44.4: Unreadable PDF → clear error + CSV suggestion ---

@pytest.mark.asyncio
async def test_ac_44_4_unreadable_pdf_returns_error_with_csv_suggestion(client: AsyncClient, verified_user, bank_account):
    """AC-44.4: DATO un PDF non leggibile, QUANDO il LLM fallisce, ALLORA errore chiaro con suggerimento CSV."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")

    with (
        patch("api.modules.banking.import_service.extract_text_from_pdf", return_value="testo troppo corto"),
    ):
        fake_pdf = io.BytesIO(b"%PDF-1.4 corrupted")
        resp = await client.post(
            f"/api/v1/bank-accounts/{bank_account.id}/import-statement",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("broken.pdf", fake_pdf, "application/pdf")},
        )

    assert resp.status_code == 422
    assert "estrarre testo" in resp.json()["detail"].lower() or "CSV" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_ac_44_4_llm_failure_suggests_csv(client: AsyncClient, verified_user, bank_account):
    """AC-44.4: LLM extraction fails → error suggests CSV fallback."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")

    with (
        patch("api.modules.banking.import_service.extract_text_from_pdf", return_value="Estratto conto lungo abbastanza " * 10),
        patch("api.modules.banking.import_service.extract_movements_llm", new_callable=AsyncMock, side_effect=ValueError("API error")),
    ):
        fake_pdf = io.BytesIO(b"%PDF-1.4 fake")
        resp = await client.post(
            f"/api/v1/bank-accounts/{bank_account.id}/import-statement",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("test.pdf", fake_pdf, "application/pdf")},
        )

    assert resp.status_code == 422
    assert "csv" in resp.json()["detail"].lower()


# --- Edge cases ---

@pytest.mark.asyncio
async def test_non_pdf_file_rejected(client: AsyncClient, verified_user, bank_account):
    """Non-PDF files are rejected with 400."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")

    fake_csv = io.BytesIO(b"data,importo\n2024-01-01,100")
    resp = await client.post(
        f"/api/v1/bank-accounts/{bank_account.id}/import-statement",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("movimenti.csv", fake_csv, "text/csv")},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_wrong_account_returns_404(client: AsyncClient, verified_user):
    """Import on non-existent account returns error."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")

    fake_pdf = io.BytesIO(b"%PDF-1.4 fake")
    resp = await client.post(
        f"/api/v1/bank-accounts/{uuid.uuid4()}/import-statement",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("test.pdf", fake_pdf, "application/pdf")},
    )
    assert resp.status_code == 422  # ValueError from service
