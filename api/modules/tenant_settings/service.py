"""Service for tenant settings — encrypted key-value store with platform fallback."""

import base64
import hashlib
import logging
import os
import uuid

from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import TenantSetting, Tenant

logger = logging.getLogger(__name__)

# Known setting keys with descriptions
KNOWN_KEYS = {
    # A-Cube — fatturazione SDI + Open Banking (unico provider)
    "acube_api_key": "API Key A-Cube (se custom, altrimenti usa piattaforma)",
    "acube_company_id": "ID azienda in A-Cube per fatturazione SDI",
    "acube_connection_id": "Connection ID A-Cube per Open Banking (PSD2)",
    # Email — Brevo
    "brevo_api_key": "API Key Brevo (se custom, altrimenti usa piattaforma)",
    # LLM — OpenAI
    "openai_api_key": "API Key OpenAI (se custom)",
}

# Provider attivi — Salt Edge e FiscoAPI disabilitati, A-Cube unico provider
ACTIVE_PROVIDERS = {
    "fatturazione": "acube",      # SDI invio/ricezione
    "open_banking": "acube",      # Conti correnti PSD2
    "email": "brevo",             # Email marketing + tracking
    "llm": "openai",              # Chatbot + PDF extraction
}

# Provider disabilitati (codice resta, non usato)
DISABLED_PROVIDERS = ["saltedge", "fiscoapi"]


def _get_fernet() -> Fernet:
    """Get Fernet encryption instance from AES_KEY env var."""
    aes_key = os.getenv("AES_KEY", "change-me-32-bytes-hex-encoded-key")
    # Derive a 32-byte key from AES_KEY using SHA256, then base64 encode for Fernet
    key_bytes = hashlib.sha256(aes_key.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key)


def encrypt_value(value: str) -> str:
    """Encrypt a setting value."""
    f = _get_fernet()
    return f.encrypt(value.encode()).decode()


def decrypt_value(encrypted: str) -> str:
    """Decrypt a setting value."""
    f = _get_fernet()
    return f.decrypt(encrypted.encode()).decode()


class TenantSettingsService:
    """Manages encrypted per-tenant settings with platform fallback."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_setting(self, tenant_id: uuid.UUID, key: str) -> str | None:
        """Get a setting value — tenant custom first, then platform env fallback.

        Priority:
        1. Custom tenant setting (encrypted in DB)
        2. Platform env var (e.g. BREVO_API_KEY)
        """
        result = await self.db.execute(
            select(TenantSetting).where(
                TenantSetting.tenant_id == tenant_id,
                TenantSetting.key == key,
            )
        )
        setting = result.scalar_one_or_none()
        if setting:
            try:
                return decrypt_value(setting.value_encrypted)
            except Exception:
                logger.error("Failed to decrypt setting %s for tenant %s", key, tenant_id)
                return None

        # Fallback to platform env var
        env_key = key.upper()
        return os.getenv(env_key)

    async def set_setting(
        self, tenant_id: uuid.UUID, key: str, value: str, source: str = "custom",
    ) -> dict:
        """Set or update an encrypted tenant setting."""
        encrypted = encrypt_value(value)

        result = await self.db.execute(
            select(TenantSetting).where(
                TenantSetting.tenant_id == tenant_id,
                TenantSetting.key == key,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.value_encrypted = encrypted
            existing.source = source
        else:
            self.db.add(TenantSetting(
                tenant_id=tenant_id,
                key=key,
                value_encrypted=encrypted,
                source=source,
            ))

        await self.db.flush()
        return {"key": key, "source": source, "status": "saved"}

    async def delete_setting(self, tenant_id: uuid.UUID, key: str) -> bool:
        """Delete a tenant setting (falls back to platform)."""
        result = await self.db.execute(
            select(TenantSetting).where(
                TenantSetting.tenant_id == tenant_id,
                TenantSetting.key == key,
            )
        )
        setting = result.scalar_one_or_none()
        if not setting:
            return False
        await self.db.delete(setting)
        await self.db.flush()
        return True

    async def list_settings(self, tenant_id: uuid.UUID) -> list[dict]:
        """List all settings for a tenant (values masked)."""
        result = await self.db.execute(
            select(TenantSetting).where(TenantSetting.tenant_id == tenant_id)
        )
        settings = result.scalars().all()

        items = []
        for s in settings:
            try:
                raw = decrypt_value(s.value_encrypted)
                masked = raw[:4] + "****" + raw[-4:] if len(raw) > 8 else "****"
            except Exception:
                masked = "****"

            items.append({
                "key": s.key,
                "value_masked": masked,
                "source": s.source,
                "description": KNOWN_KEYS.get(s.key, ""),
            })

        # Add platform defaults not overridden
        existing_keys = {s.key for s in settings}
        for key, desc in KNOWN_KEYS.items():
            if key not in existing_keys:
                env_val = os.getenv(key.upper())
                items.append({
                    "key": key,
                    "value_masked": "piattaforma" if env_val else "non configurato",
                    "source": "platform" if env_val else "none",
                    "description": desc,
                })

        return items

    async def get_sender_for_tenant(self, tenant_id: uuid.UUID) -> tuple[str, str]:
        """Get email sender for a tenant — tenant config first, then platform default."""
        result = await self.db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()
        if tenant and tenant.sender_email:
            return tenant.sender_email, tenant.sender_name or tenant.name
        return (
            os.getenv("BREVO_SENDER_EMAIL", "noreply@agentflow.it"),
            os.getenv("BREVO_SENDER_NAME", "AgentFlow"),
        )

    async def check_email_quota(self, tenant_id: uuid.UUID) -> dict:
        """Check email quota for tenant."""
        from datetime import datetime
        current_month = datetime.utcnow().strftime("%Y-%m")

        result = await self.db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()
        if not tenant:
            return {"allowed": False, "reason": "tenant not found"}

        # Reset counter if new month
        if getattr(tenant, "email_month_reset", None) != current_month:
            tenant.email_sent_month = 0
            tenant.email_month_reset = current_month
            await self.db.flush()

        quota = getattr(tenant, "email_quota_monthly", 5000) or 5000
        sent = getattr(tenant, "email_sent_month", 0) or 0

        return {
            "allowed": sent < quota,
            "sent": sent,
            "quota": quota,
            "remaining": max(0, quota - sent),
        }

    async def increment_email_count(self, tenant_id: uuid.UUID) -> None:
        """Increment email sent counter for tenant."""
        result = await self.db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()
        if tenant:
            tenant.email_sent_month = (getattr(tenant, "email_sent_month", 0) or 0) + 1
            await self.db.flush()
