"""
Test suite for US-18: Notifiche WhatsApp/Telegram
Tests for 4 Acceptance Criteria (AC-18.1 through AC-18.4)
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import Tenant, User, NotificationLog
from api.modules.notifications.service import NotificationService
from tests.conftest import get_auth_token


# ============================================================
# AC-18.1 — Notifica scadenza via Telegram
#            (tipo, data, importo, link)
# ============================================================


class TestAC181NotificaTelegram:
    """AC-18.1: Notifica scadenza inviata via Telegram con tutti i dati."""

    async def test_ac_181_send_scadenza_telegram(
        self, db_session: AsyncSession, tenant: Tenant, verified_user: User,
    ):
        """AC-18.1: DATO utente con Telegram configurato,
        QUANDO scadenza imminente, ALLORA notifica con tipo/data/importo/link."""
        service = NotificationService(db_session)

        # Configure Telegram
        await service.create_or_update_config(
            user_id=verified_user.id,
            tenant_id=tenant.id,
            channel="telegram",
            chat_id="123456789",
        )

        # Send scadenza notification
        results = await service.send_scadenza_notification(
            user_id=verified_user.id,
            tenant_id=tenant.id,
            scadenza_tipo="Liquidazione IVA Q1",
            scadenza_data="2026-05-16",
            importo=5200.00,
            link="https://contabot.it/scadenze/iva-q1",
        )

        assert len(results) == 1
        assert results[0]["success"] is True
        assert results[0]["channel"] == "telegram"
        assert results[0]["message_id"] is not None

        # Verify message content via adapter
        sent = service.telegram.get_sent_messages()
        assert len(sent) == 1
        msg = sent[0]["text"]
        assert "Liquidazione IVA Q1" in msg
        assert "2026-05-16" in msg
        assert "5,200.00" in msg or "5200" in msg
        assert "contabot.it" in msg

    async def test_ac_181_send_via_api(
        self, client: AsyncClient, auth_headers: dict,
    ):
        """AC-18.1: DATO utente autenticato,
        QUANDO configura Telegram e invia test,
        ALLORA riceve conferma invio."""
        # Create config
        resp = await client.post(
            "/api/v1/notifications/config",
            json={"channel": "telegram", "chat_id": "987654321"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["channel"] == "telegram"
        assert data["chat_id"] == "987654321"

        # Send test
        resp = await client.post(
            "/api/v1/notifications/test",
            json={"channel": "telegram"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        results = resp.json()
        assert len(results) == 1
        assert results[0]["success"] is True


# ============================================================
# AC-18.2 — Configurazione canale (WhatsApp o Telegram)
# ============================================================


class TestAC182ConfigurazioneCanale:
    """AC-18.2: User can configure WhatsApp or Telegram channel."""

    async def test_ac_182_config_telegram(
        self, client: AsyncClient, auth_headers: dict,
    ):
        """AC-18.2: DATO utente, QUANDO configura Telegram,
        ALLORA config salvata con chat_id."""
        resp = await client.post(
            "/api/v1/notifications/config",
            json={"channel": "telegram", "chat_id": "111222333"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["channel"] == "telegram"
        assert data["chat_id"] == "111222333"
        assert data["enabled"] is True

    async def test_ac_182_config_whatsapp(
        self, client: AsyncClient, auth_headers: dict,
    ):
        """AC-18.2: DATO utente, QUANDO configura WhatsApp,
        ALLORA config salvata con numero telefono."""
        resp = await client.post(
            "/api/v1/notifications/config",
            json={"channel": "whatsapp", "phone": "+393331234567"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["channel"] == "whatsapp"
        assert data["phone"] == "+393331234567"

    async def test_ac_182_get_configs(
        self, client: AsyncClient, auth_headers: dict,
    ):
        """AC-18.2: DATO utente con canali configurati,
        QUANDO richiede configs, ALLORA vede tutti i canali."""
        # Create both channels
        await client.post(
            "/api/v1/notifications/config",
            json={"channel": "telegram", "chat_id": "444555666"},
            headers=auth_headers,
        )
        await client.post(
            "/api/v1/notifications/config",
            json={"channel": "whatsapp", "phone": "+393339876543"},
            headers=auth_headers,
        )

        resp = await client.get(
            "/api/v1/notifications/config",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 2
        channels = [c["channel"] for c in data["configs"]]
        assert "telegram" in channels
        assert "whatsapp" in channels

    async def test_ac_182_canale_non_supportato(
        self, client: AsyncClient, auth_headers: dict,
    ):
        """AC-18.2: DATO canale non supportato,
        QUANDO configura, ALLORA errore."""
        resp = await client.post(
            "/api/v1/notifications/config",
            json={"channel": "sms", "phone": "+393331111111"},
            headers=auth_headers,
        )
        assert resp.status_code == 400
        assert "non supportato" in resp.json()["detail"]

    async def test_ac_182_telegram_senza_chat_id(
        self, client: AsyncClient, auth_headers: dict,
    ):
        """AC-18.2: DATO Telegram senza chat_id,
        QUANDO configura, ALLORA errore."""
        resp = await client.post(
            "/api/v1/notifications/config",
            json={"channel": "telegram"},
            headers=auth_headers,
        )
        assert resp.status_code == 400
        assert "chat_id" in resp.json()["detail"]


# ============================================================
# AC-18.3 — Consegna fallita -> retry 1h, max 3, fallback email
# ============================================================


class TestAC183RetryFallback:
    """AC-18.3: Failed delivery retries 3 times then falls back to email."""

    async def test_ac_183_retry_e_fallback(
        self, db_session: AsyncSession, tenant: Tenant, verified_user: User,
    ):
        """AC-18.3: DATO consegna fallita,
        QUANDO riprova 3 volte, ALLORA fallback a email."""
        service = NotificationService(db_session)

        # Configure Telegram
        await service.create_or_update_config(
            user_id=verified_user.id,
            tenant_id=tenant.id,
            channel="telegram",
            chat_id="fail_chat",
        )

        # Set adapter to fail
        service.telegram.set_fail_mode(True)

        results = await service.send_scadenza_notification(
            user_id=verified_user.id,
            tenant_id=tenant.id,
            scadenza_tipo="F24 Marzo",
            scadenza_data="2026-03-16",
            importo=1500.00,
            link="https://contabot.it/f24",
        )

        assert len(results) == 1
        result = results[0]
        assert result["success"] is False
        assert result["retry_count"] == 3
        assert result["fallback_used"] is True

    async def test_ac_183_retry_count_logged(
        self, db_session: AsyncSession, tenant: Tenant, verified_user: User,
    ):
        """AC-18.3: DATO consegna fallita dopo max retry,
        ALLORA log con status fallback_email."""
        service = NotificationService(db_session)

        await service.create_or_update_config(
            user_id=verified_user.id,
            tenant_id=tenant.id,
            channel="telegram",
            chat_id="fail_chat_2",
        )

        service.telegram.set_fail_mode(True)

        await service.send_scadenza_notification(
            user_id=verified_user.id,
            tenant_id=tenant.id,
            scadenza_tipo="Test Retry",
            scadenza_data="2026-03-16",
            importo=100.00,
            link="https://contabot.it/test",
        )

        # Check notification log
        from sqlalchemy import select
        result = await db_session.execute(
            select(NotificationLog).where(
                NotificationLog.user_id == verified_user.id,
            )
        )
        logs = result.scalars().all()
        assert len(logs) >= 1
        fallback_log = [l for l in logs if l.status == "fallback_email"]
        assert len(fallback_log) == 1
        assert fallback_log[0].retry_count == 3

    async def test_ac_183_success_no_retry(
        self, db_session: AsyncSession, tenant: Tenant, verified_user: User,
    ):
        """AC-18.3: DATO consegna riuscita al primo tentativo,
        ALLORA retry_count = 0."""
        service = NotificationService(db_session)

        await service.create_or_update_config(
            user_id=verified_user.id,
            tenant_id=tenant.id,
            channel="telegram",
            chat_id="good_chat",
        )

        results = await service.send_scadenza_notification(
            user_id=verified_user.id,
            tenant_id=tenant.id,
            scadenza_tipo="IVA Q1",
            scadenza_data="2026-05-16",
            importo=3000.00,
            link="https://contabot.it/iva",
        )

        assert results[0]["success"] is True
        assert results[0]["retry_count"] == 0
        assert results[0]["fallback_used"] is False


# ============================================================
# AC-18.4 — Troppe notifiche -> digest raggruppato
# ============================================================


class TestAC184DigestRaggruppato:
    """AC-18.4: Too many notifications trigger grouped digest."""

    async def test_ac_184_digest_dopo_soglia(
        self, db_session: AsyncSession, tenant: Tenant, verified_user: User,
    ):
        """AC-18.4: DATO >5 notifiche nello stesso giorno,
        QUANDO invia nuova notifica, ALLORA invia digest raggruppato."""
        service = NotificationService(db_session)

        # Configure channel
        await service.create_or_update_config(
            user_id=verified_user.id,
            tenant_id=tenant.id,
            channel="telegram",
            chat_id="digest_chat",
        )

        # Create 6 notification logs for today to exceed threshold
        from datetime import datetime, UTC
        for i in range(6):
            log = NotificationLog(
                user_id=verified_user.id,
                tenant_id=tenant.id,
                channel="telegram",
                message_type="scadenza",
                message_text=f"Notification {i}",
                status="sent",
            )
            db_session.add(log)
        await db_session.flush()

        # Now send another - should trigger digest
        results = await service.send_scadenza_notification(
            user_id=verified_user.id,
            tenant_id=tenant.id,
            scadenza_tipo="Another Scadenza",
            scadenza_data="2026-05-16",
            importo=1000.00,
            link="https://contabot.it/test",
        )

        # Should receive digest
        assert len(results) >= 1
        # Check that digest message was sent
        sent = service.telegram.get_sent_messages()
        assert any("Riepilogo notifiche" in m["text"] or "riepilogo" in m["text"].lower()
                    for m in sent)

    async def test_ac_184_sotto_soglia_no_digest(
        self, db_session: AsyncSession, tenant: Tenant, verified_user: User,
    ):
        """AC-18.4: DATO <= 5 notifiche,
        QUANDO invia notifica, ALLORA notifica singola (non digest)."""
        service = NotificationService(db_session)

        await service.create_or_update_config(
            user_id=verified_user.id,
            tenant_id=tenant.id,
            channel="telegram",
            chat_id="no_digest_chat",
        )

        results = await service.send_scadenza_notification(
            user_id=verified_user.id,
            tenant_id=tenant.id,
            scadenza_tipo="IVA Q2",
            scadenza_data="2026-08-20",
            importo=4000.00,
            link="https://contabot.it/iva-q2",
        )

        assert len(results) >= 1
        assert results[0]["success"] is True

        # Message should be specific, not a digest
        sent = service.telegram.get_sent_messages()
        assert len(sent) >= 1
        assert "IVA Q2" in sent[-1]["text"]
        assert "Riepilogo" not in sent[-1]["text"]
