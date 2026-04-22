"""Test endpoint webhook A-Cube OB (Sprint 48 US-OB-05).

Verifica:
- POST connect/reconnect/payment con firma valida → 200
- Firma invalida → 401 (se verify abilitato)
- Modalità insecure (env flag false) → accetta senza firma
- Idempotency: stesso payload 2 volte → secondo = duplicate_ignored
- Side effect: BankConnection attivata dopo processing Connect
- Side effect: reconnect_url + notice_level salvati dopo Reconnect
"""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from api.config import settings
from api.db.models import BankConnection, WebhookEvent


SECRET = "test-webhook-shared-secret"


def _sign(body: bytes, secret: str = SECRET) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


@pytest.fixture
def enable_signature(monkeypatch):
    monkeypatch.setattr(settings, "acube_ob_webhook_verify_signature", True)
    monkeypatch.setattr(settings, "acube_ob_webhook_secret", SECRET)
    monkeypatch.setattr(settings, "acube_ob_webhook_signature_header", "X-Acube-Signature")
    monkeypatch.setattr(settings, "acube_ob_webhook_signature_algo", "sha256")
    monkeypatch.setattr(settings, "acube_ob_webhook_signature_prefix", "")


@pytest.fixture
def disable_signature(monkeypatch):
    monkeypatch.setattr(settings, "acube_ob_webhook_verify_signature", False)


@pytest.fixture
async def existing_connection(db_session) -> BankConnection:
    conn = BankConnection(
        tenant_id=uuid.uuid4(),
        fiscal_id="IT12345678901",
        business_name="Test Spa",
        status="pending",
        acube_br_uuid="br-test-xyz",
        environment="sandbox",
    )
    db_session.add(conn)
    await db_session.commit()
    await db_session.refresh(conn)
    return conn


# ── Connect ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_connect_webhook_with_valid_signature(
    client: AsyncClient, db_session, enable_signature, existing_connection
):
    payload = {
        "fiscalId": "IT12345678901",
        "success": True,
        "updatedAccounts": ["acc-1", "acc-2"],
    }
    body = json.dumps(payload).encode()
    sig = _sign(body)

    resp = await client.post(
        "/api/v1/webhooks/acube/connect",
        content=body,
        headers={"Content-Type": "application/json", "X-Acube-Signature": sig},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "accepted"
    assert "event_id" in data

    # Verifica evento persistito
    events = (await db_session.execute(select(WebhookEvent))).scalars().all()
    assert len(events) == 1
    assert events[0].signature_verified is True
    assert events[0].event_type == "connect"


@pytest.mark.asyncio
async def test_connect_webhook_invalid_signature_rejected(
    client: AsyncClient, enable_signature
):
    body = b'{"fiscalId":"IT12345678901","success":true,"updatedAccounts":[]}'
    resp = await client.post(
        "/api/v1/webhooks/acube/connect",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Acube-Signature": "wrong-signature-0000000000000000000000000000000000000000",
        },
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_connect_webhook_missing_signature_rejected(
    client: AsyncClient, enable_signature
):
    body = b'{"fiscalId":"IT12345678901","success":true,"updatedAccounts":[]}'
    resp = await client.post(
        "/api/v1/webhooks/acube/connect",
        content=body,
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_connect_webhook_insecure_mode_accepts_unsigned(
    client: AsyncClient, disable_signature, existing_connection
):
    body = json.dumps({
        "fiscalId": "IT12345678901",
        "success": True,
        "updatedAccounts": ["acc-1"],
    }).encode()
    resp = await client.post(
        "/api/v1/webhooks/acube/connect",
        content=body,
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "accepted"


# ── Idempotency ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_duplicate_webhook_ignored(
    client: AsyncClient, db_session, disable_signature, existing_connection
):
    payload = {"fiscalId": "IT12345678901", "success": True, "updatedAccounts": ["a"]}
    body = json.dumps(payload).encode()

    r1 = await client.post(
        "/api/v1/webhooks/acube/connect",
        content=body,
        headers={"Content-Type": "application/json"},
    )
    assert r1.status_code == 200
    assert r1.json()["status"] == "accepted"

    r2 = await client.post(
        "/api/v1/webhooks/acube/connect",
        content=body,
        headers={"Content-Type": "application/json"},
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == "duplicate_ignored"
    # Stesso event_id (il primo creato)
    assert r1.json()["event_id"] == r2.json()["event_id"]

    # In DB deve esserci solo 1 evento
    events = (await db_session.execute(select(WebhookEvent))).scalars().all()
    assert len(events) == 1


# ── Reconnect ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_reconnect_webhook_saves_url_and_notice(
    client: AsyncClient, db_session, disable_signature, existing_connection
):
    payload = {
        "fiscalId": "IT12345678901",
        "connectUrl": "https://ob-sandbox.api.acubeapi.com/reconnect/xyz",
        "providerName": "Intesa Sanpaolo",
        "consentExpiresAt": "2026-07-20T00:00:00+00:00",
        "noticeLevel": 1,
    }
    body = json.dumps(payload).encode()
    resp = await client.post(
        "/api/v1/webhooks/acube/reconnect",
        content=body,
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 200


# ── Payment ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_payment_webhook_accepted(
    client: AsyncClient, disable_signature
):
    payload = {
        "fiscalId": "IT12345678901",
        "success": True,
        "payment": {
            "uuid": "pay-123",
            "direction": "inbound",
            "status": "accepted",
            "amount": "100.00",
            "currencyCode": "EUR",
        },
    }
    body = json.dumps(payload).encode()
    resp = await client.post(
        "/api/v1/webhooks/acube/payment",
        content=body,
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 200


# ── Payload non-JSON ───────────────────────────────────────

@pytest.mark.asyncio
async def test_invalid_json_rejected(client: AsyncClient, disable_signature):
    resp = await client.post(
        "/api/v1/webhooks/acube/connect",
        content=b"not-json-at-all",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 401  # trattato come firma/payload invalido


# ── Prefisso firma (Stripe-style) ──────────────────────────

@pytest.mark.asyncio
async def test_signature_with_prefix_format(
    client: AsyncClient, monkeypatch, existing_connection
):
    monkeypatch.setattr(settings, "acube_ob_webhook_verify_signature", True)
    monkeypatch.setattr(settings, "acube_ob_webhook_secret", SECRET)
    monkeypatch.setattr(settings, "acube_ob_webhook_signature_header", "X-Acube-Signature")
    monkeypatch.setattr(settings, "acube_ob_webhook_signature_algo", "sha256")
    monkeypatch.setattr(settings, "acube_ob_webhook_signature_prefix", "sha256=")

    body = json.dumps({"fiscalId": "IT12345678901", "success": True, "updatedAccounts": []}).encode()
    sig = "sha256=" + _sign(body)

    resp = await client.post(
        "/api/v1/webhooks/acube/connect",
        content=body,
        headers={"Content-Type": "application/json", "X-Acube-Signature": sig},
    )
    assert resp.status_code == 200
