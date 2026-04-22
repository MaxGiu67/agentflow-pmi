"""Test modelli DB A-Cube Open Banking (Sprint 48 US-OB-03).

Verifica:
- BankConnection si persiste con tutti i campi
- BankAccount supporta i nuovi campi acube_*
- BankTransaction supporta i nuovi campi acube_* + enriched_*
- Indici/vincoli di unicità non documentati qui (si testano solo a DB migrato)
"""

from __future__ import annotations

import uuid
from datetime import datetime, date

import pytest
from sqlalchemy import select

from api.db.models import BankAccount, BankConnection, BankTransaction


@pytest.mark.asyncio
async def test_bank_connection_round_trip(db_session):
    tenant_id = uuid.uuid4()
    conn = BankConnection(
        tenant_id=tenant_id,
        fiscal_id="IT12345678901",
        business_name="Acme Srl",
        acube_br_uuid="br-abc-123",
        acube_email="br-acme@agentflow.taal.it",
        status="pending",
        acube_enabled=False,
        environment="sandbox",
    )
    db_session.add(conn)
    await db_session.commit()
    await db_session.refresh(conn)

    assert conn.id is not None
    assert conn.fiscal_id == "IT12345678901"
    assert conn.acube_br_uuid == "br-abc-123"
    assert conn.environment == "sandbox"
    assert conn.acube_enabled is False
    assert conn.status == "pending"
    assert conn.created_at is not None


@pytest.mark.asyncio
async def test_bank_connection_lifecycle_transition(db_session):
    """Ciclo vita: pending → active → expired."""
    conn = BankConnection(
        tenant_id=uuid.uuid4(),
        fiscal_id="IT98765432109",
        status="pending",
    )
    db_session.add(conn)
    await db_session.commit()

    # Connect webhook success → attiva
    conn.status = "active"
    conn.acube_enabled = True
    conn.consent_expires_at = datetime(2026, 7, 20, 0, 0, 0)
    await db_session.commit()

    # Reconnect webhook noticeLevel=2
    conn.notice_level = 2
    conn.reconnect_url = "https://ob-sandbox.api.acubeapi.com/reconnect/xyz"
    conn.last_reconnect_webhook_at = datetime(2026, 7, 18, 10, 0, 0)
    await db_session.commit()

    await db_session.refresh(conn)
    assert conn.status == "active"
    assert conn.notice_level == 2
    assert conn.reconnect_url is not None


@pytest.mark.asyncio
async def test_bank_account_acube_fields(db_session):
    tenant_id = uuid.uuid4()
    conn_id = uuid.uuid4()
    acc = BankAccount(
        tenant_id=tenant_id,
        iban="IT60X0542811101000000123456",
        bank_name="Intesa Sanpaolo",
        provider="acube_aisp",
        status="connected",
        acube_uuid="acc-uuid-xyz",
        acube_connection_id=conn_id,
        acube_provider_name="Intesa Sanpaolo",
        acube_nature="account",
        acube_enabled=True,
        acube_extra={"bic": "BCITITMM", "bank_branch": "Milano"},
        balance=15234.50,
    )
    db_session.add(acc)
    await db_session.commit()
    await db_session.refresh(acc)

    assert acc.acube_uuid == "acc-uuid-xyz"
    assert acc.acube_connection_id == conn_id
    assert acc.acube_provider_name == "Intesa Sanpaolo"
    assert acc.acube_nature == "account"
    assert acc.acube_enabled is True
    assert acc.acube_extra["bic"] == "BCITITMM"


@pytest.mark.asyncio
async def test_bank_transaction_acube_and_enriched_fields(db_session):
    acc_id = uuid.uuid4()
    tx = BankTransaction(
        bank_account_id=acc_id,
        transaction_id="local-id-001",
        date=date(2026, 4, 15),
        value_date=date(2026, 4, 16),
        amount=1200.00,
        direction="credit",
        counterpart="Cliente Rossi Srl",
        description="Bonifico SEPA FATTURA N. 2026/45 CRO 12345678901",
        source="open_banking",
        # A-Cube fields
        acube_transaction_id="acube-tx-abc-123",
        acube_status="booked",
        acube_duplicated=False,
        acube_category="business_revenue",
        acube_fetched_at=datetime(2026, 4, 16, 8, 30),
        acube_counterparty="Cliente Rossi Srl",
        acube_extra={"provider_txid": "INT-2026-04-15-001", "endToEndId": "A+C000123"},
        # Enriched fields (estratti dal parser extra)
        enriched_cro="12345678901",
        enriched_invoice_ref="2026/45",
    )
    db_session.add(tx)
    await db_session.commit()
    await db_session.refresh(tx)

    assert tx.acube_transaction_id == "acube-tx-abc-123"
    assert tx.acube_status == "booked"
    assert tx.acube_duplicated is False
    assert tx.acube_category == "business_revenue"
    assert tx.acube_extra["endToEndId"] == "A+C000123"
    assert tx.enriched_cro == "12345678901"
    assert tx.enriched_invoice_ref == "2026/45"


@pytest.mark.asyncio
async def test_bank_transaction_pending_status(db_session):
    """Verifica che status 'pending' sia ammesso (gotcha: vanno ri-eliminate ad ogni fetch)."""
    tx = BankTransaction(
        bank_account_id=uuid.uuid4(),
        transaction_id="tmp-001",
        date=date(2026, 4, 20),
        amount=50.00,
        direction="debit",
        acube_transaction_id="acube-pending-001",
        acube_status="pending",
    )
    db_session.add(tx)
    await db_session.commit()
    await db_session.refresh(tx)
    assert tx.acube_status == "pending"


@pytest.mark.asyncio
async def test_query_bank_connection_by_tenant(db_session):
    """La query comune è per tenant+fiscal_id — deve essere performante (index)."""
    tenant_id = uuid.uuid4()
    db_session.add_all([
        BankConnection(tenant_id=tenant_id, fiscal_id="IT11111111111", status="active"),
        BankConnection(tenant_id=tenant_id, fiscal_id="IT22222222222", status="pending"),
    ])
    await db_session.commit()

    result = await db_session.execute(
        select(BankConnection).where(
            BankConnection.tenant_id == tenant_id,
            BankConnection.status == "active",
        )
    )
    actives = result.scalars().all()
    assert len(actives) == 1
    assert actives[0].fiscal_id == "IT11111111111"
