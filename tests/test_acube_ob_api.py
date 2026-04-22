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

    async def list_accounts(self, fiscal_id: str) -> list[dict[str, Any]]:
        return self.accounts_to_return


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
    assert data["accounts_synced"] == 1
