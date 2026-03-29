"""Integration tests for completeness score (US-69)."""

import pytest
from httpx import AsyncClient

from tests.conftest import get_auth_token


# --- AC-69.1: Shows connected sources + unlocked features + next suggestion ---

@pytest.mark.asyncio
async def test_ac_69_1_empty_tenant_shows_all_not_configured(client: AsyncClient, verified_user):
    """AC-69.1: Nessuna fonte collegata → mostra tutto non configurato con primo suggerimento."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")

    resp = await client.get(
        "/api/v1/completeness-score",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    data = resp.json()

    assert data["connected_count"] == 0
    assert data["total_sources"] == 6
    assert len(data["unlocked_features"]) == 0

    # All sources should be not_configured
    for src in data["sources"]:
        assert src["status"] in ("not_configured", "pending")
        assert "label" in src
        assert "unlocks" in src
        assert len(src["unlocks"]) > 0  # each source has unlockable features

    # Should suggest first source (fatture)
    assert data["next_suggestion"] is not None
    assert data["next_suggestion"]["source_type"] == "fatture"
    assert data["next_suggestion"]["benefit"]


@pytest.mark.asyncio
async def test_ac_69_1_with_invoices_shows_fatture_connected(client: AsyncClient, verified_user, tenant, db_session):
    """AC-69.1: Con fatture importate → fatture appare come connessa."""
    from api.db.models import Invoice
    from datetime import date

    inv = Invoice(
        tenant_id=tenant.id,
        type="passiva",
        source="cassetto_fiscale",
        numero_fattura="FAT/2024/001",
        emittente_piva="12345678901",
        emittente_nome="Fornitore Test",
        data_fattura=date(2024, 3, 1),
        importo_netto=1000.0,
        importo_iva=220.0,
        importo_totale=1220.0,
        processing_status="parsed",
    )
    db_session.add(inv)
    await db_session.flush()

    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")
    resp = await client.get(
        "/api/v1/completeness-score",
        headers={"Authorization": f"Bearer {token}"},
    )

    data = resp.json()
    assert data["connected_count"] == 1

    fatture_src = next(s for s in data["sources"] if s["source_type"] == "fatture")
    assert fatture_src["status"] == "connected"

    assert "Fatturato in tempo reale" in data["unlocked_features"]

    # Next suggestion should be banca (second in list)
    assert data["next_suggestion"]["source_type"] == "banca"


# --- AC-69.2: Connecting a new source → new features appear as unlocked ---

@pytest.mark.asyncio
async def test_ac_69_2_adding_bank_unlocks_cashflow(client: AsyncClient, verified_user, tenant, db_session):
    """AC-69.2: Collegando la banca → Cash Flow e Riconciliazione appaiono come sbloccati."""
    from api.db.models import Invoice, BankAccount, BankTransaction
    from datetime import date

    # Add invoice (fatture connected)
    inv = Invoice(
        tenant_id=tenant.id, type="passiva", source="cassetto_fiscale",
        numero_fattura="FAT/001", emittente_piva="12345678901", emittente_nome="Test",
        data_fattura=date(2024, 1, 1), importo_netto=100, importo_iva=22, importo_totale=122,
        processing_status="parsed",
    )
    db_session.add(inv)

    # Add bank account + transaction (banca connected)
    ba = BankAccount(
        tenant_id=tenant.id, iban="IT1234", bank_name="Test Bank",
        provider="manual", status="connected",
    )
    db_session.add(ba)
    await db_session.flush()

    tx = BankTransaction(
        bank_account_id=ba.id, transaction_id="TX-001", date=date(2024, 1, 5),
        amount=122.0, direction="debit", description="Pagamento", source="import_pdf",
    )
    db_session.add(tx)
    await db_session.flush()

    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")
    resp = await client.get(
        "/api/v1/completeness-score",
        headers={"Authorization": f"Bearer {token}"},
    )

    data = resp.json()
    assert data["connected_count"] == 2

    banca_src = next(s for s in data["sources"] if s["source_type"] == "banca")
    assert banca_src["status"] == "connected"

    assert "Cash Flow predittivo" in data["unlocked_features"]
    assert "Riconciliazione automatica" in data["unlocked_features"]


# --- AC-69.3: Positive framing ---

@pytest.mark.asyncio
async def test_ac_69_3_positive_framing_message(client: AsyncClient, verified_user, tenant, db_session):
    """AC-69.3: Il messaggio usa 'Hai sbloccato X', non percentuali negative."""
    from api.db.models import Invoice
    from datetime import date

    inv = Invoice(
        tenant_id=tenant.id, type="passiva", source="cassetto_fiscale",
        numero_fattura="FAT/001", emittente_piva="12345678901", emittente_nome="Test",
        data_fattura=date(2024, 1, 1), importo_netto=100, importo_iva=22, importo_totale=122,
        processing_status="parsed",
    )
    db_session.add(inv)
    await db_session.flush()

    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")
    resp = await client.get(
        "/api/v1/completeness-score",
        headers={"Authorization": f"Bearer {token}"},
    )

    data = resp.json()
    msg = data["message"]

    # Positive framing
    assert "Hai sbloccato" in msg
    assert "%" not in msg  # no percentages
    assert "manca" not in msg.lower()  # no "ti manca"

    # Should mention next step
    assert "Prossimo passo" in msg


@pytest.mark.asyncio
async def test_ac_69_3_empty_message_is_encouraging(client: AsyncClient, verified_user):
    """AC-69.3: Senza fonti collegate il messaggio e' incoraggiante, non negativo."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")

    resp = await client.get(
        "/api/v1/completeness-score",
        headers={"Authorization": f"Bearer {token}"},
    )

    data = resp.json()
    msg = data["message"]

    assert "%" not in msg
    assert "manca" not in msg.lower()
    assert "cassetto" in msg.lower() or "fatture" in msg.lower()
