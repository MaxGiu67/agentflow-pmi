"""Test unitari per ACubeOpenBankingClient (Sprint 48 US-OB-01 + US-OB-02).

Mockiamo httpx con MockTransport: nessuna chiamata di rete reale.
Le credenziali sono iniettate via monkeypatch su api.config.settings.
"""

from __future__ import annotations

import pytest
import httpx

from api.adapters import acube_ob
from api.adapters.acube_ob import (
    ACubeAPIError,
    ACubeAuthError,
    ACubeOpenBankingClient,
)


def _make_client(monkeypatch, *, env="sandbox", email="test@nexa.it", password="secret"):
    monkeypatch.setattr(acube_ob.settings, "acube_ob_env", env)
    monkeypatch.setattr(acube_ob.settings, "acube_ob_login_email", email)
    monkeypatch.setattr(acube_ob.settings, "acube_ob_login_password", password)
    return ACubeOpenBankingClient()


def _mock_transport(handler):
    """Wrap httpx MockTransport into an AsyncClient patch."""
    transport = httpx.MockTransport(handler)

    class _PatchedAsyncClient(httpx.AsyncClient):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = transport
            super().__init__(*args, **kwargs)

    return _PatchedAsyncClient


# ── AC-OB-01.1: client disabled when credentials missing ────

@pytest.mark.asyncio
async def test_client_disabled_without_credentials(monkeypatch):
    monkeypatch.setattr(acube_ob.settings, "acube_ob_login_email", "")
    monkeypatch.setattr(acube_ob.settings, "acube_ob_login_password", "")
    client = ACubeOpenBankingClient()
    assert client.enabled is False

    # call che non chiama login perché disabled
    result = await client.list_business_registries()
    assert result == []


# ── AC-OB-01.2: env selection sandbox vs production ────────

def test_env_sandbox_urls(monkeypatch):
    client = _make_client(monkeypatch, env="sandbox")
    assert "sandbox" in client.login_url
    assert "sandbox" in client.base_url


def test_env_production_urls(monkeypatch):
    client = _make_client(monkeypatch, env="production")
    assert "sandbox" not in client.login_url
    assert "sandbox" not in client.base_url
    assert client.login_url == "https://common.api.acubeapi.com/login"
    assert client.base_url == "https://ob.api.acubeapi.com"


# ── AC-OB-02.1: login returns JWT ──────────────────────────

@pytest.mark.asyncio
async def test_login_returns_jwt(monkeypatch):
    client = _make_client(monkeypatch)

    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["method"] = request.method
        captured["body"] = request.content.decode()
        return httpx.Response(200, json={"token": "fake-jwt-token"})

    monkeypatch.setattr(acube_ob.httpx, "AsyncClient", _mock_transport(handler))

    token = await client._login()
    assert token == "fake-jwt-token"
    assert captured["method"] == "POST"
    assert "login" in captured["url"]
    assert '"email"' in captured["body"]


# ── AC-OB-02.2: login failure raises ACubeAuthError ─────────

@pytest.mark.asyncio
async def test_login_failure_raises(monkeypatch):
    client = _make_client(monkeypatch)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "invalid credentials"})

    monkeypatch.setattr(acube_ob.httpx, "AsyncClient", _mock_transport(handler))

    with pytest.raises(ACubeAuthError):
        await client._login()


# ── AC-OB-02.3: token caching avoids repeat login ──────────

@pytest.mark.asyncio
async def test_token_cached_across_calls(monkeypatch):
    client = _make_client(monkeypatch)

    call_counter = {"logins": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if "login" in str(request.url):
            call_counter["logins"] += 1
            return httpx.Response(200, json={"token": "cached-jwt"})
        return httpx.Response(200, json={"hydra:member": [], "hydra:view": {}})

    monkeypatch.setattr(acube_ob.httpx, "AsyncClient", _mock_transport(handler))

    # chiamate multiple: deve fare login 1 sola volta
    await client.list_business_registries()
    await client.list_business_registries()
    await client.list_categories()

    assert call_counter["logins"] == 1


# ── AC-OB-02.4: 401 triggers token refresh + retry ─────────

@pytest.mark.asyncio
async def test_401_triggers_refresh_and_retry(monkeypatch):
    client = _make_client(monkeypatch)

    state = {"first_api_call": True, "logins": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "login" in url:
            state["logins"] += 1
            return httpx.Response(200, json={"token": f"jwt-{state['logins']}"})
        if "business-registry" in url and state["first_api_call"]:
            state["first_api_call"] = False
            return httpx.Response(401, json={"error": "expired"})
        return httpx.Response(200, json={"hydra:member": [], "hydra:view": {}})

    monkeypatch.setattr(acube_ob.httpx, "AsyncClient", _mock_transport(handler))

    result = await client.list_business_registries()
    assert result == []
    assert state["logins"] == 2  # initial + after 401


# ── AC-OB-01.3: headers include Bearer + Hydra accept ──────

@pytest.mark.asyncio
async def test_request_headers_contain_bearer_and_hydra(monkeypatch):
    client = _make_client(monkeypatch)
    captured_headers: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_headers.append(dict(request.headers))
        if "login" in str(request.url):
            return httpx.Response(200, json={"token": "xyz"})
        return httpx.Response(200, json={"hydra:member": [], "hydra:view": {}})

    monkeypatch.setattr(acube_ob.httpx, "AsyncClient", _mock_transport(handler))

    await client.list_business_registries()

    api_headers = captured_headers[-1]
    assert api_headers.get("authorization") == "Bearer xyz"
    assert "ld+json" in api_headers.get("accept", "")


# ── AC-OB-01.4: HTTP 5xx raises ACubeAPIError ──────────────

@pytest.mark.asyncio
async def test_5xx_raises_api_error(monkeypatch):
    client = _make_client(monkeypatch)

    def handler(request: httpx.Request) -> httpx.Response:
        if "login" in str(request.url):
            return httpx.Response(200, json={"token": "xyz"})
        return httpx.Response(503, text="Service Unavailable")

    monkeypatch.setattr(acube_ob.httpx, "AsyncClient", _mock_transport(handler))

    with pytest.raises(ACubeAPIError) as exc_info:
        await client.list_business_registries()
    assert exc_info.value.status_code == 503


# ── AC-OB-01.5: pagination loop walks all Hydra pages ──────

@pytest.mark.asyncio
async def test_pagination_walks_all_pages(monkeypatch):
    client = _make_client(monkeypatch)

    pages = {
        1: {
            "hydra:member": [{"id": 1}, {"id": 2}],
            "hydra:view": {"hydra:next": "/?page=2"},
        },
        2: {
            "hydra:member": [{"id": 3}, {"id": 4}],
            "hydra:view": {"hydra:next": "/?page=3"},
        },
        3: {
            "hydra:member": [{"id": 5}],
            "hydra:view": {},  # no next
        },
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if "login" in str(request.url):
            return httpx.Response(200, json={"token": "xyz"})
        page = int(request.url.params.get("page", "1"))
        return httpx.Response(200, json=pages.get(page, pages[1]))

    monkeypatch.setattr(acube_ob.httpx, "AsyncClient", _mock_transport(handler))

    results = await client.list_business_registries()
    assert len(results) == 5
    assert [r["id"] for r in results] == [1, 2, 3, 4, 5]


# ── AC-OB-01.6: transactions requires made_on_after to backfill ──

@pytest.mark.asyncio
async def test_list_transactions_passes_made_on_after(monkeypatch):
    client = _make_client(monkeypatch)
    captured_params: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if "login" in str(request.url):
            return httpx.Response(200, json={"token": "xyz"})
        captured_params.append(dict(request.url.params))
        return httpx.Response(200, json={"hydra:member": [], "hydra:view": {}})

    monkeypatch.setattr(acube_ob.httpx, "AsyncClient", _mock_transport(handler))

    await client.list_transactions(
        fiscal_id="IT12345678901",
        account_uuid="abc-123",
        made_on_after="2024-01-01",
    )

    params = captured_params[0]
    assert params.get("account.uuid") == "abc-123"
    assert params.get("madeOn[strictly_after]") == "2024-01-01"
    assert params.get("itemsPerPage") == "100"


# ── AC-OB-02.5: invalidate_token clears cache ──────────────

def test_invalidate_token_clears_state(monkeypatch):
    client = _make_client(monkeypatch)
    client._token = "stale"
    client._token_expires_at = 9999999999
    client.invalidate_token()
    assert client._token is None
    assert client._token_expires_at == 0
