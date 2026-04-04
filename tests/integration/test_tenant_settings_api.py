"""Tests for tenant_settings — encryption, fallback, multi-sender, email quota."""

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import Tenant
from api.modules.tenant_settings.service import (
    TenantSettingsService, encrypt_value, decrypt_value,
)


# ── Encryption ──

def test_encrypt_decrypt():
    """Values are encrypted and decryptable."""
    original = "xkeysib-abc123-secret"
    encrypted = encrypt_value(original)
    assert encrypted != original
    assert decrypt_value(encrypted) == original


def test_encrypt_different_each_time():
    """Same value encrypts differently (Fernet uses random IV)."""
    v1 = encrypt_value("test")
    v2 = encrypt_value("test")
    assert v1 != v2  # different ciphertext
    assert decrypt_value(v1) == decrypt_value(v2)  # same plaintext


# ── Service ──

@pytest.mark.asyncio
async def test_set_and_get_setting(db_session: AsyncSession, tenant: Tenant):
    """Set a setting, get it back decrypted."""
    svc = TenantSettingsService(db_session)
    await svc.set_setting(tenant.id, "brevo_api_key", "xkeysib-test-123")

    value = await svc.get_setting(tenant.id, "brevo_api_key")
    assert value == "xkeysib-test-123"


@pytest.mark.asyncio
async def test_get_setting_fallback_to_env(db_session: AsyncSession, tenant: Tenant):
    """No custom setting → falls back to platform env var."""
    import os
    os.environ["TEST_PLATFORM_KEY"] = "platform-value"
    svc = TenantSettingsService(db_session)

    value = await svc.get_setting(tenant.id, "test_platform_key")
    assert value == "platform-value"

    del os.environ["TEST_PLATFORM_KEY"]


@pytest.mark.asyncio
async def test_custom_overrides_platform(db_session: AsyncSession, tenant: Tenant):
    """Custom tenant setting overrides platform env var."""
    import os
    os.environ["MY_KEY"] = "platform"
    svc = TenantSettingsService(db_session)

    await svc.set_setting(tenant.id, "my_key", "custom-tenant-value")
    value = await svc.get_setting(tenant.id, "my_key")
    assert value == "custom-tenant-value"  # not "platform"

    del os.environ["MY_KEY"]


@pytest.mark.asyncio
async def test_delete_setting_reverts_to_platform(db_session: AsyncSession, tenant: Tenant):
    """Deleting custom setting reverts to platform default."""
    import os
    os.environ["REVERT_KEY"] = "platform-default"
    svc = TenantSettingsService(db_session)

    await svc.set_setting(tenant.id, "revert_key", "custom")
    assert await svc.get_setting(tenant.id, "revert_key") == "custom"

    await svc.delete_setting(tenant.id, "revert_key")
    assert await svc.get_setting(tenant.id, "revert_key") == "platform-default"

    del os.environ["REVERT_KEY"]


@pytest.mark.asyncio
async def test_list_settings_masked(db_session: AsyncSession, tenant: Tenant):
    """List shows masked values."""
    svc = TenantSettingsService(db_session)
    await svc.set_setting(tenant.id, "brevo_api_key", "xkeysib-very-long-secret-key-1234")

    settings = await svc.list_settings(tenant.id)
    brevo = next(s for s in settings if s["key"] == "brevo_api_key")
    assert "****" in brevo["value_masked"]
    assert "xkeysib-very-long-secret-key-1234" not in brevo["value_masked"]


# ── Multi-sender ──

@pytest.mark.asyncio
async def test_sender_from_tenant(db_session: AsyncSession):
    """Tenant with sender_email uses its own sender."""
    t = Tenant(
        name="Sender Test SRL", type="srl", regime_fiscale="ordinario",
        piva="99999999991", sender_email="info@sendertest.it", sender_name="Sender Test",
    )
    db_session.add(t)
    await db_session.flush()

    svc = TenantSettingsService(db_session)
    email, name = await svc.get_sender_for_tenant(t.id)
    assert email == "info@sendertest.it"
    assert name == "Sender Test"


@pytest.mark.asyncio
async def test_sender_fallback_to_platform(db_session: AsyncSession, tenant: Tenant):
    """Tenant without sender_email falls back to platform."""
    svc = TenantSettingsService(db_session)
    email, name = await svc.get_sender_for_tenant(tenant.id)
    assert "@" in email  # some default


# ── Email quota ──

@pytest.mark.asyncio
async def test_email_quota_check(db_session: AsyncSession):
    """Email quota check and increment."""
    t = Tenant(
        name="Quota Test SRL", type="srl", regime_fiscale="ordinario",
        piva="99999999992", email_quota_monthly=100,
    )
    db_session.add(t)
    await db_session.flush()

    svc = TenantSettingsService(db_session)

    quota = await svc.check_email_quota(t.id)
    assert quota["allowed"] is True
    assert quota["quota"] == 100
    assert quota["remaining"] == 100

    # Send some emails
    for _ in range(3):
        await svc.increment_email_count(t.id)

    quota2 = await svc.check_email_quota(t.id)
    assert quota2["sent"] == 3
    assert quota2["remaining"] == 97


# ── API endpoints ──

@pytest.mark.asyncio
async def test_api_list_settings(client: AsyncClient, auth_headers: dict):
    """API: GET /settings/integrations."""
    resp = await client.get("/api/v1/settings/integrations", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_api_set_setting(client: AsyncClient, auth_headers: dict):
    """API: POST /settings/integrations."""
    resp = await client.post(
        "/api/v1/settings/integrations",
        json={"key": "acube_company_id", "value": "comp_001"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "saved"


@pytest.mark.asyncio
async def test_api_email_quota(client: AsyncClient, auth_headers: dict):
    """API: GET /settings/email-quota."""
    resp = await client.get("/api/v1/settings/email-quota", headers=auth_headers)
    assert resp.status_code == 200
    assert "quota" in resp.json()


@pytest.mark.asyncio
async def test_api_sender(client: AsyncClient, auth_headers: dict):
    """API: GET /settings/sender."""
    resp = await client.get("/api/v1/settings/sender", headers=auth_headers)
    assert resp.status_code == 200
    assert "sender_email" in resp.json()
