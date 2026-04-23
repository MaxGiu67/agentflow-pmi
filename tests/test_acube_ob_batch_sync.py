"""Test batch sync multiple connessioni A-Cube (US-OB-08).

Verifica che ciascuna BankConnection venga processata indipendentemente
e che errori su una non blocchino le altre.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from sqlalchemy import select

from api.db.models import BankAccount, BankConnection
from api.modules.banking.acube_ob_service import (
    ACubeOBServiceError,
    ACubeOpenBankingService,
)


class _RecordingClient:
    """Client fake che registra le call e può simulare errori selettivi."""

    def __init__(self) -> None:
        self.enabled = True
        self.env = "sandbox"
        self.accounts_by_fiscal: dict[str, list[dict]] = {}
        self.tx_by_account: dict[str, list[dict]] = {}
        self.raise_for_fiscal: set[str] = set()

    async def list_accounts(self, fiscal_id: str, enabled: bool | None = None) -> list[dict]:
        if fiscal_id in self.raise_for_fiscal:
            from api.adapters.acube_ob import ACubeAPIError
            raise ACubeAPIError(502, '{"error":"upstream"}')
        return self.accounts_by_fiscal.get(fiscal_id, [])

    async def list_transactions(
        self,
        fiscal_id: str,
        *,
        account_uuid: str | None = None,
        made_on_after: str | None = None,
        made_on_before: str | None = None,
        status: Any = None,
    ) -> list[dict]:
        return self.tx_by_account.get(account_uuid or "", [])


@pytest.fixture
async def two_active_connections(db_session, verified_user) -> list[BankConnection]:
    """Crea 2 BankConnection attive per lo stesso tenant."""
    t_id = verified_user.tenant_id
    c1 = BankConnection(
        tenant_id=t_id,
        fiscal_id="IT11111111111",
        business_name="A SPA",
        acube_br_uuid="br-a",
        status="active",
        environment="sandbox",
    )
    c2 = BankConnection(
        tenant_id=t_id,
        fiscal_id="IT22222222222",
        business_name="B SRL",
        acube_br_uuid="br-b",
        status="active",
        environment="sandbox",
    )
    db_session.add_all([c1, c2])
    await db_session.commit()
    await db_session.refresh(c1)
    await db_session.refresh(c2)
    return [c1, c2]


@pytest.mark.asyncio
async def test_batch_sync_processes_each_independently(db_session, two_active_connections):
    """Errore su BR-A non impatta BR-B."""
    client = _RecordingClient()
    client.accounts_by_fiscal["IT22222222222"] = [
        {"uuid": "acc-b1", "iban": "IT-B1", "providerName": "UniCredit", "balance": "0", "enabled": True},
    ]
    client.raise_for_fiscal.add("IT11111111111")  # primo fallisce

    service = ACubeOpenBankingService(db_session, client=client)

    c1, c2 = two_active_connections
    results: list[dict] = []

    # Simula il loop dello script CLI
    for conn in two_active_connections:
        try:
            out = await service.sync_accounts(conn.id, conn.tenant_id)
            results.append({"ok": True, "conn": conn.fiscal_id, "created": out["accounts_created"]})
        except ACubeOBServiceError as exc:
            results.append({"ok": False, "conn": conn.fiscal_id, "err": str(exc)})
        except Exception as exc:  # noqa: BLE001
            results.append({"ok": False, "conn": conn.fiscal_id, "err": repr(exc)})

    # BR-A fallisce, BR-B ok
    assert results[0]["conn"] == "IT11111111111"
    assert results[0]["ok"] is False
    assert results[1]["conn"] == "IT22222222222"
    assert results[1]["ok"] is True
    assert results[1]["created"] == 1

    # Verifica DB: solo acc-b1 creato
    rows = (await db_session.execute(select(BankAccount))).scalars().all()
    assert len(rows) == 1
    assert rows[0].acube_uuid == "acc-b1"


@pytest.mark.asyncio
async def test_mark_expired_consents(db_session, verified_user):
    """BankConnection con consent_expires_at passato → status=expired."""
    from datetime import datetime, timedelta

    t_id = verified_user.tenant_id
    now = datetime.utcnow()

    c_expired = BankConnection(
        tenant_id=t_id,
        fiscal_id="IT55555555555",
        status="active",
        consent_expires_at=now - timedelta(days=1),
        environment="sandbox",
    )
    c_fresh = BankConnection(
        tenant_id=t_id,
        fiscal_id="IT66666666666",
        status="active",
        consent_expires_at=now + timedelta(days=30),
        environment="sandbox",
    )
    c_no_expiry = BankConnection(
        tenant_id=t_id,
        fiscal_id="IT77777777777",
        status="active",
        consent_expires_at=None,
        environment="sandbox",
    )
    db_session.add_all([c_expired, c_fresh, c_no_expiry])
    await db_session.commit()

    service = ACubeOpenBankingService(db_session, client=_RecordingClient())
    n = await service.mark_expired_consents()
    assert n == 1

    await db_session.refresh(c_expired)
    await db_session.refresh(c_fresh)
    await db_session.refresh(c_no_expiry)
    assert c_expired.status == "expired"
    assert c_fresh.status == "active"
    assert c_no_expiry.status == "active"


@pytest.mark.asyncio
async def test_batch_skips_inactive_connection(db_session, verified_user):
    """Connection con status!=active NON viene processata (service-level check)."""
    t_id = verified_user.tenant_id
    conn = BankConnection(
        tenant_id=t_id,
        fiscal_id="IT33333333333",
        status="pending",
        environment="sandbox",
    )
    db_session.add(conn)
    await db_session.commit()
    await db_session.refresh(conn)

    client = _RecordingClient()
    service = ACubeOpenBankingService(db_session, client=client)

    with pytest.raises(ACubeOBServiceError, match="non attiva"):
        await service.sync_accounts(conn.id, t_id)
