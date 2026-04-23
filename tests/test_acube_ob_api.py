"""Test integrazione endpoint A-Cube Open Banking (Sprint 48 US-OB-04).

Mocka ACubeOpenBankingClient iniettando un fake service.
Verifica:
- POST /banking/connections/init — crea BR + avvia connect → restituisce URL SCA
- GET /banking/connections — lista
- GET /banking/connections/{id} — dettaglio + 404
- POST /banking/connections/{id}/sync-now — bloccato se status != active
- 400 se tenant senza P.IVA
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from httpx import AsyncClient

from api.db.models import BankConnection, User
from api.modules.banking import acube_ob_router, acube_ob_service


class _FakeClient:
    """Fake ACubeOpenBankingClient per test integrazione (no rete)."""

    def __init__(self) -> None:
        self.enabled = True
        self.env = "sandbox"
        self.created_brs: list[dict] = []
        self.started_connects: list[dict] = []
        self.accounts_to_return: list[dict] = []
        self.tx_by_account: dict[str, list[dict]] = {}
        self.list_tx_calls: list[dict] = []

    async def create_business_registry(
        self, fiscal_id: str, email: str, business_name: str, enabled: bool = False
    ) -> dict[str, Any]:
        br = {
            "uuid": f"br-fake-{fiscal_id[-4:]}",
            "fiscalId": fiscal_id,
            "email": email,
            "businessName": business_name,
            "enabled": enabled,
        }
        self.created_brs.append(br)
        return br

    async def start_connect(
        self, fiscal_id: str, redirect_url: str, locale: str = "it"
    ) -> dict[str, Any]:
        self.started_connects.append(
            {"fiscal_id": fiscal_id, "redirect_url": redirect_url, "locale": locale}
        )
        return {
            "uuid": f"connect-req-{fiscal_id[-4:]}",
            "redirectUrl": f"https://ob-sandbox.api.acubeapi.com/sca/{fiscal_id}?token=xyz",
            "state": "pending",
        }

    async def list_accounts(self, fiscal_id: str, enabled: bool | None = None) -> list[dict[str, Any]]:
        return self.accounts_to_return

    async def reconnect_account(self, account_uuid: str) -> dict[str, Any]:
        return {
            "uuid": f"reconnect-{account_uuid}",
            "redirectUrl": f"https://ob-sandbox.api.acubeapi.com/reconnect/sca/{account_uuid}",
            "state": "pending",
        }

    async def list_transactions(
        self,
        fiscal_id: str,
        *,
        account_uuid: str | None = None,
        made_on_after: str | None = None,
        made_on_before: str | None = None,
        status: str | list[str] | None = None,
    ) -> list[dict[str, Any]]:
        self.list_tx_calls.append(
            {
                "fiscal_id": fiscal_id,
                "account_uuid": account_uuid,
                "made_on_after": made_on_after,
                "made_on_before": made_on_before,
                "status": status,
            }
        )
        return self.tx_by_account.get(account_uuid or "", [])


@pytest.fixture
def fake_client() -> _FakeClient:
    return _FakeClient()


@pytest.fixture(autouse=True)
def inject_fake_client(fake_client, db_session):
    """Override FastAPI dependency per iniettare il fake client A-Cube OB."""
    from api.main import app

    def _factory_override():
        # db_session già iniettato dal conftest tramite override get_db
        return acube_ob_service.ACubeOpenBankingService(db_session, client=fake_client)

    app.dependency_overrides[acube_ob_router.get_service] = _factory_override
    yield
    app.dependency_overrides.pop(acube_ob_router.get_service, None)


# ── AC-OB-04.1: init connection — happy path ──────────────

@pytest.mark.asyncio
async def test_init_connection_happy_path(client: AsyncClient, auth_headers, fake_client):
    resp = await client.post(
        "/api/v1/banking/connections/init",
        headers=auth_headers,
        json={"return_url": "https://agentflow.up.railway.app/banca/callback"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "connection_id" in data
    assert data["connect_url"].startswith("https://ob-sandbox.api.acubeapi.com/sca/")
    assert data["status"] == "pending"
    assert data["acube_br_uuid"].startswith("br-fake-")

    # Verifica side effects
    assert len(fake_client.created_brs) == 1
    assert len(fake_client.started_connects) == 1
    assert fake_client.started_connects[0]["locale"] == "it"


# ── AC-OB-04.2: init idempotent — BR non ri-creato ────────

@pytest.mark.asyncio
async def test_init_connection_idempotent_on_existing_br(
    client: AsyncClient, auth_headers, fake_client
):
    # Prima init
    r1 = await client.post(
        "/api/v1/banking/connections/init",
        headers=auth_headers,
        json={"return_url": "https://example.com/cb"},
    )
    assert r1.status_code == 200

    # Seconda init: stesso tenant → non dovrebbe ricreare BR
    r2 = await client.post(
        "/api/v1/banking/connections/init",
        headers=auth_headers,
        json={"return_url": "https://example.com/cb"},
    )
    assert r2.status_code == 200

    assert len(fake_client.created_brs) == 1, "BR deve essere creato UNA sola volta"
    assert len(fake_client.started_connects) == 2, "Connect deve essere chiamato ogni volta"
    # Stesso connection_id
    assert r1.json()["connection_id"] == r2.json()["connection_id"]


# ── AC-OB-04.3: 400 se tenant senza P.IVA ─────────────────

@pytest.mark.asyncio
async def test_init_connection_400_if_no_piva(
    client: AsyncClient, db_session, verified_user_no_tenant: User
):
    # Login come utente senza tenant
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "nuova.utente@example.com", "password": "Password1"},
    )
    token = resp.json().get("access_token")
    assert token, resp.text
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.post(
        "/api/v1/banking/connections/init",
        headers=headers,
        json={"return_url": "https://example.com/cb"},
    )
    assert r.status_code == 400
    assert "azienda" in r.json()["detail"].lower() or "tenant" in r.json()["detail"].lower()


# ── AC-OB-04.4: lista connessioni per tenant ──────────────

@pytest.mark.asyncio
async def test_list_connections(client: AsyncClient, auth_headers, fake_client):
    # Crea almeno 1 connessione
    await client.post(
        "/api/v1/banking/connections/init",
        headers=auth_headers,
        json={"return_url": "https://example.com/cb"},
    )

    r = await client.get("/api/v1/banking/connections", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 1
    assert data["items"][0]["status"] == "pending"
    assert data["items"][0]["environment"] == "sandbox"


# ── AC-OB-04.5: detail connection + 404 ───────────────────

@pytest.mark.asyncio
async def test_get_connection_detail(client: AsyncClient, auth_headers, fake_client):
    init_resp = await client.post(
        "/api/v1/banking/connections/init",
        headers=auth_headers,
        json={"return_url": "https://example.com/cb"},
    )
    conn_id = init_resp.json()["connection_id"]

    r = await client.get(f"/api/v1/banking/connections/{conn_id}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["id"] == conn_id


@pytest.mark.asyncio
async def test_get_connection_404(client: AsyncClient, auth_headers):
    fake_id = uuid.uuid4()
    r = await client.get(f"/api/v1/banking/connections/{fake_id}", headers=auth_headers)
    assert r.status_code == 404


# ── AC-OB-04.6: sync-now bloccato se status != active ─────

@pytest.mark.asyncio
async def test_sync_now_blocked_if_pending(client: AsyncClient, auth_headers, fake_client):
    init_resp = await client.post(
        "/api/v1/banking/connections/init",
        headers=auth_headers,
        json={"return_url": "https://example.com/cb"},
    )
    conn_id = init_resp.json()["connection_id"]

    r = await client.post(
        f"/api/v1/banking/connections/{conn_id}/sync-now",
        headers=auth_headers,
    )
    assert r.status_code == 409
    assert "non attiva" in r.json()["detail"].lower()


# ── AC-OB-04.7: sync-now ok quando status=active ──────────

@pytest.mark.asyncio
async def test_sync_now_ok_when_active(
    client: AsyncClient, auth_headers, db_session, verified_user, fake_client
):
    # Simula connect webhook già ricevuto: conn=active + 1 account a-cube da importare
    init_resp = await client.post(
        "/api/v1/banking/connections/init",
        headers=auth_headers,
        json={"return_url": "https://example.com/cb"},
    )
    conn_id = uuid.UUID(init_resp.json()["connection_id"])

    # Mark as active directly in DB
    conn = (await db_session.get(BankConnection, conn_id))
    conn.status = "active"
    conn.acube_enabled = True
    await db_session.commit()

    # Configure fake accounts
    fake_client.accounts_to_return = [
        {
            "uuid": "acc-fake-1",
            "iban": "IT60X0542811101000000123456",
            "providerName": "Intesa Sanpaolo",
            "nature": "account",
            "balance": "10000.00",
            "enabled": True,
            "extra": {"bic": "BCITITMM"},
        }
    ]

    r = await client.post(
        f"/api/v1/banking/connections/{conn_id}/sync-now",
        headers=auth_headers,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["accounts_created"] == 1
    assert data["accounts_updated"] == 0
    assert data["accounts_synced"] == 1  # back-compat: created + updated
    assert data["tx_created"] == 0  # fake_client.tx_by_account vuoto


# ── AC-OB-06.1: sync-accounts idempotente (created → updated) ──

@pytest.mark.asyncio
async def test_sync_accounts_idempotent_second_call_updates(
    client: AsyncClient, auth_headers, db_session, fake_client
):
    init_resp = await client.post(
        "/api/v1/banking/connections/init",
        headers=auth_headers,
        json={"return_url": "https://example.com/cb"},
    )
    conn_id = uuid.UUID(init_resp.json()["connection_id"])
    conn = await db_session.get(BankConnection, conn_id)
    conn.status = "active"
    await db_session.commit()

    fake_client.accounts_to_return = [
        {"uuid": "acc-a", "iban": "IT01", "providerName": "Intesa", "balance": "100.00", "enabled": True},
        {"uuid": "acc-b", "iban": "IT02", "providerName": "Unicredit", "balance": "200.00", "enabled": True},
    ]

    r1 = await client.post(
        f"/api/v1/banking/connections/{conn_id}/sync-accounts",
        headers=auth_headers,
    )
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["accounts_created"] == 2
    assert d1["accounts_updated"] == 0

    # Seconda chiamata: stessi UUID → tutti updated, 0 created
    fake_client.accounts_to_return[0]["balance"] = "150.00"
    r2 = await client.post(
        f"/api/v1/banking/connections/{conn_id}/sync-accounts",
        headers=auth_headers,
    )
    d2 = r2.json()
    assert d2["accounts_created"] == 0
    assert d2["accounts_updated"] == 2
    assert d2["accounts_revoked"] == 0


# ── AC-OB-06.2: account orfano (non più su A-Cube) → revoked ──

@pytest.mark.asyncio
async def test_sync_accounts_marks_orphan_as_revoked(
    client: AsyncClient, auth_headers, db_session, fake_client
):
    init_resp = await client.post(
        "/api/v1/banking/connections/init",
        headers=auth_headers,
        json={"return_url": "https://example.com/cb"},
    )
    conn_id = uuid.UUID(init_resp.json()["connection_id"])
    conn = await db_session.get(BankConnection, conn_id)
    conn.status = "active"
    await db_session.commit()

    # 2 account creati
    fake_client.accounts_to_return = [
        {"uuid": "acc-keep", "iban": "IT-K", "providerName": "X", "balance": "10", "enabled": True},
        {"uuid": "acc-drop", "iban": "IT-D", "providerName": "Y", "balance": "20", "enabled": True},
    ]
    await client.post(f"/api/v1/banking/connections/{conn_id}/sync-accounts", headers=auth_headers)

    # Ora A-Cube ne restituisce solo 1 → l'altro diventa orphan
    fake_client.accounts_to_return = [
        {"uuid": "acc-keep", "iban": "IT-K", "providerName": "X", "balance": "10", "enabled": True},
    ]
    r = await client.post(
        f"/api/v1/banking/connections/{conn_id}/sync-accounts", headers=auth_headers
    )
    d = r.json()
    assert d["accounts_updated"] == 1
    assert d["accounts_revoked"] == 1


# ── AC-OB-07.1: sync-transactions default since = 30gg fa ──

@pytest.mark.asyncio
async def test_sync_transactions_default_backfill_30_days(
    client: AsyncClient, auth_headers, db_session, fake_client
):
    from datetime import date, timedelta

    init_resp = await client.post(
        "/api/v1/banking/connections/init",
        headers=auth_headers,
        json={"return_url": "https://example.com/cb"},
    )
    conn_id = uuid.UUID(init_resp.json()["connection_id"])
    conn = await db_session.get(BankConnection, conn_id)
    conn.status = "active"
    await db_session.commit()

    # Setup account + transazioni fake
    fake_client.accounts_to_return = [
        {"uuid": "acc-1", "iban": "IT99", "providerName": "Intesa", "balance": "500", "enabled": True},
    ]
    await client.post(f"/api/v1/banking/connections/{conn_id}/sync-accounts", headers=auth_headers)

    fake_client.tx_by_account["acc-1"] = [
        {
            "id": "tx-1",
            "amount": "-45.50",
            "madeOn": "2026-04-10",
            "description": "Bonifico fornitore X",
            "status": "booked",
            "counterparty": "Fornitore X SRL",
        },
        {
            "id": "tx-2",
            "amount": "1200.00",
            "madeOn": "2026-04-15",
            "description": "Incasso fattura 42",
            "status": "booked",
            "category": "Sales",
        },
    ]

    r = await client.post(
        f"/api/v1/banking/connections/{conn_id}/sync-transactions",
        headers=auth_headers,
    )
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["accounts_processed"] == 1
    assert d["tx_created"] == 2
    assert d["tx_updated"] == 0

    # Verifica che made_on_after sia stato passato (default ~30gg; tolleranza UTC±1)
    assert fake_client.list_tx_calls[0]["made_on_after"] is not None
    made_on_after = date.fromisoformat(fake_client.list_tx_calls[0]["made_on_after"])
    delta_days = (date.today() - made_on_after).days
    assert 29 <= delta_days <= 31


# ── AC-OB-07.2: sync-transactions idempotente ──

@pytest.mark.asyncio
async def test_sync_transactions_idempotent(
    client: AsyncClient, auth_headers, db_session, fake_client
):
    init_resp = await client.post(
        "/api/v1/banking/connections/init",
        headers=auth_headers,
        json={"return_url": "https://example.com/cb"},
    )
    conn_id = uuid.UUID(init_resp.json()["connection_id"])
    conn = await db_session.get(BankConnection, conn_id)
    conn.status = "active"
    await db_session.commit()

    fake_client.accounts_to_return = [
        {"uuid": "acc-1", "iban": "IT11", "providerName": "X", "balance": "0", "enabled": True},
    ]
    await client.post(f"/api/v1/banking/connections/{conn_id}/sync-accounts", headers=auth_headers)

    fake_client.tx_by_account["acc-1"] = [
        {"id": "tx-same", "amount": "10", "madeOn": "2026-04-20", "status": "booked"},
    ]
    r1 = await client.post(
        f"/api/v1/banking/connections/{conn_id}/sync-transactions", headers=auth_headers
    )
    assert r1.json()["tx_created"] == 1

    # Stessa chiamata → 0 create, 1 update
    # Cambio amount per simulare aggiornamento (pending → booked scenario)
    fake_client.tx_by_account["acc-1"][0]["amount"] = "15"
    r2 = await client.post(
        f"/api/v1/banking/connections/{conn_id}/sync-transactions", headers=auth_headers
    )
    assert r2.json()["tx_created"] == 0
    assert r2.json()["tx_updated"] == 1


# ── AC-OB-07.3: sync-transactions con body `since` esplicito ──

@pytest.mark.asyncio
async def test_sync_transactions_since_param_forwarded(
    client: AsyncClient, auth_headers, db_session, fake_client
):
    init_resp = await client.post(
        "/api/v1/banking/connections/init",
        headers=auth_headers,
        json={"return_url": "https://example.com/cb"},
    )
    conn_id = uuid.UUID(init_resp.json()["connection_id"])
    conn = await db_session.get(BankConnection, conn_id)
    conn.status = "active"
    await db_session.commit()

    fake_client.accounts_to_return = [
        {"uuid": "acc-1", "iban": "IT22", "providerName": "X", "balance": "0", "enabled": True},
    ]
    await client.post(f"/api/v1/banking/connections/{conn_id}/sync-accounts", headers=auth_headers)

    r = await client.post(
        f"/api/v1/banking/connections/{conn_id}/sync-transactions",
        headers=auth_headers,
        json={"since": "2026-01-01"},
    )
    assert r.status_code == 200
    assert r.json()["since"] == "2026-01-01"
    # Il client deve aver ricevuto il param
    assert fake_client.list_tx_calls[0]["made_on_after"] == "2026-01-01"


# ── AC-OB-07.4: sync-transactions 409 se connection non attiva ──

@pytest.mark.asyncio
async def test_sync_transactions_enriches_cro_and_invoice_ref(
    client: AsyncClient, auth_headers, db_session, fake_client
):
    """US-OB-09: enriched_cro + enriched_invoice_ref popolati al sync."""
    from sqlalchemy import select

    from api.db.models import BankTransaction

    init_resp = await client.post(
        "/api/v1/banking/connections/init",
        headers=auth_headers,
        json={"return_url": "https://example.com/cb"},
    )
    conn_id = uuid.UUID(init_resp.json()["connection_id"])
    conn = await db_session.get(BankConnection, conn_id)
    conn.status = "active"
    await db_session.commit()

    fake_client.accounts_to_return = [
        {"uuid": "acc-enr", "iban": "IT33", "providerName": "Intesa", "balance": "0", "enabled": True},
    ]
    await client.post(f"/api/v1/banking/connections/{conn_id}/sync-accounts", headers=auth_headers)

    fake_client.tx_by_account["acc-enr"] = [
        {
            "id": "tx-rich",
            "amount": "500.00",
            "madeOn": "2026-04-18",
            "description": "BONIFICO SEPA CRO: 12345678901 FATT. N. 42/2026 ACME SPA",
            "status": "booked",
        }
    ]
    r = await client.post(
        f"/api/v1/banking/connections/{conn_id}/sync-transactions",
        headers=auth_headers,
    )
    assert r.status_code == 200

    tx = (
        await db_session.execute(
            select(BankTransaction).where(BankTransaction.acube_transaction_id == "tx-rich")
        )
    ).scalar_one()
    assert tx.enriched_cro == "12345678901"
    assert tx.enriched_invoice_ref == "42/2026"


# ── AC-OB-11.1: reconnect con URL da webhook cache ──

@pytest.mark.asyncio
async def test_reconnect_returns_cached_url_from_webhook(
    client: AsyncClient, auth_headers, db_session, fake_client
):
    init_resp = await client.post(
        "/api/v1/banking/connections/init",
        headers=auth_headers,
        json={"return_url": "https://example.com/cb"},
    )
    conn_id = uuid.UUID(init_resp.json()["connection_id"])

    # Simula che un webhook Reconnect ha già salvato l'url
    conn = await db_session.get(BankConnection, conn_id)
    conn.reconnect_url = "https://ob-sandbox.api.acubeapi.com/reconnect/cached-xyz"
    conn.notice_level = 1
    await db_session.commit()

    r = await client.post(
        f"/api/v1/banking/connections/{conn_id}/reconnect", headers=auth_headers
    )
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["source"] == "webhook_cached"
    assert d["reconnect_url"].endswith("cached-xyz")
    assert d["notice_level"] == 1


# ── AC-OB-11.2: reconnect on-demand se nessun url cached ──

@pytest.mark.asyncio
async def test_reconnect_on_demand_when_no_cached_url(
    client: AsyncClient, auth_headers, db_session, fake_client
):
    init_resp = await client.post(
        "/api/v1/banking/connections/init",
        headers=auth_headers,
        json={"return_url": "https://example.com/cb"},
    )
    conn_id = uuid.UUID(init_resp.json()["connection_id"])
    conn = await db_session.get(BankConnection, conn_id)
    conn.status = "active"
    await db_session.commit()

    # Sync un account per avere qualcosa da cui chiedere reconnect
    fake_client.accounts_to_return = [
        {"uuid": "acc-xyz", "iban": "IT44", "providerName": "Intesa", "balance": "0", "enabled": True},
    ]
    await client.post(f"/api/v1/banking/connections/{conn_id}/sync-accounts", headers=auth_headers)

    r = await client.post(
        f"/api/v1/banking/connections/{conn_id}/reconnect", headers=auth_headers
    )
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["source"] == "on_demand"
    assert "acc-xyz" in d["reconnect_url"]


# ── AC-OB-11.3: reconnect 409 se nessun account ──

@pytest.mark.asyncio
async def test_reconnect_409_when_no_account(
    client: AsyncClient, auth_headers, fake_client
):
    init_resp = await client.post(
        "/api/v1/banking/connections/init",
        headers=auth_headers,
        json={"return_url": "https://example.com/cb"},
    )
    conn_id = init_resp.json()["connection_id"]
    r = await client.post(
        f"/api/v1/banking/connections/{conn_id}/reconnect", headers=auth_headers
    )
    assert r.status_code == 409
    assert "account" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_sync_transactions_blocked_if_pending(
    client: AsyncClient, auth_headers, fake_client
):
    init_resp = await client.post(
        "/api/v1/banking/connections/init",
        headers=auth_headers,
        json={"return_url": "https://example.com/cb"},
    )
    conn_id = init_resp.json()["connection_id"]
    r = await client.post(
        f"/api/v1/banking/connections/{conn_id}/sync-transactions",
        headers=auth_headers,
    )
    assert r.status_code == 409
