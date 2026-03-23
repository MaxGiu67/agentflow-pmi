"""
Test suite for US-03: Autenticazione SPID/CIE per cassetto fiscale
Tests for 5 Acceptance Criteria (AC-03.1 through AC-03.5)
"""

import pytest
from httpx import AsyncClient

from api.db.models import User
from tests.conftest import get_auth_token


# ============================================================
# AC-03.1 — Happy Path: Autenticazione SPID riuscita
# ============================================================


class TestAC031SpidRiuscita:
    """AC-03.1: Autenticazione SPID completata con successo."""

    async def test_ac_031_init_spid_auth(
        self, client: AsyncClient, auth_headers: dict
    ):
        """AC-03.1: DATO autenticato, QUANDO clicco 'Collega cassetto fiscale',
        ALLORA ottengo redirect URL per SPID."""
        response = await client.post(
            "/api/v1/auth/spid/init",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "redirect_url" in data
        assert "spid" in data["redirect_url"].lower()

    async def test_ac_031_spid_callback_successo(
        self, client: AsyncClient, auth_headers: dict
    ):
        """AC-03.1: QUANDO completo flusso SPID, ALLORA token salvato e cassetto collegato."""
        response = await client.get(
            "/api/v1/auth/spid/callback",
            params={"code": "valid-auth-code", "state": "session-state"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["cassetto_connected"] is True
        assert "collegato" in data["message"].lower()

    async def test_ac_031_cassetto_status_dopo_collegamento(
        self, client: AsyncClient, auth_headers: dict
    ):
        """AC-03.1: dopo collegamento, status mostra connesso."""
        # First connect
        await client.get(
            "/api/v1/auth/spid/callback",
            params={"code": "valid-code", "state": ""},
            headers=auth_headers,
        )

        # Check status
        response = await client.get(
            "/api/v1/cassetto/status",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["connected"] is True
        assert data["token_valid"] is True


# ============================================================
# AC-03.2 — Error: Autenticazione SPID annullata
# ============================================================


class TestAC032SpidAnnullata:
    """AC-03.2: SPID annullata o fallita."""

    async def test_ac_032_spid_annullata(
        self, client: AsyncClient, auth_headers: dict
    ):
        """AC-03.2: QUANDO annullo autenticazione SPID,
        ALLORA messaggio 'Autenticazione annullata' e posso riprovare."""
        response = await client.get(
            "/api/v1/auth/spid/callback",
            params={"code": "cancelled", "state": ""},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["cassetto_connected"] is False
        assert "annullata" in data["message"].lower()

    async def test_ac_032_spid_errore(
        self, client: AsyncClient, auth_headers: dict
    ):
        """AC-03.2: errore SPID mostra messaggio e permette retry."""
        response = await client.get(
            "/api/v1/auth/spid/callback",
            params={"code": "error", "state": ""},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["cassetto_connected"] is False


# ============================================================
# AC-03.3 — Error: Token SPID scaduto
# ============================================================


class TestAC033TokenScaduto:
    """AC-03.3: Token FiscoAPI scaduto."""

    async def test_ac_033_token_scaduto_status(
        self, client: AsyncClient, verified_user: User, db_session, auth_headers: dict
    ):
        """AC-03.3: DATO token scaduto, ALLORA status mostra 'scaduta'."""
        from datetime import UTC, datetime, timedelta

        # Set expired token directly on user
        verified_user.spid_token = "expired-token"
        verified_user.spid_token_expires_at = datetime.now(UTC) - timedelta(hours=1)
        await db_session.flush()

        response = await client.get(
            "/api/v1/cassetto/status",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["connected"] is True
        assert data["token_valid"] is False
        assert "scaduta" in data["message"].lower()


# ============================================================
# AC-03.4 — Edge Case: Utente senza SPID/CIE
# ============================================================


class TestAC034SenzaSpid:
    """AC-03.4: Utente senza SPID/CIE."""

    async def test_ac_034_info_senza_spid(
        self, client: AsyncClient, auth_headers: dict
    ):
        """AC-03.4: DATO utente senza SPID, ALLORA info su come ottenerlo + alternative."""
        response = await client.get(
            "/api/v1/cassetto/no-spid",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "spid" in data["message"].lower()
        assert len(data["alternatives"]) >= 1
        assert data["can_retry"] is False

    async def test_ac_034_status_non_collegato(
        self, client: AsyncClient, auth_headers: dict
    ):
        """AC-03.4: status mostra non collegato per utente senza SPID."""
        response = await client.get(
            "/api/v1/cassetto/status",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["connected"] is False


# ============================================================
# AC-03.5 — Edge Case: Delega a terzi (commercialista)
# ============================================================


class TestAC035Delega:
    """AC-03.5: Flusso di delega per commercialista."""

    async def test_ac_035_init_delega(
        self, client: AsyncClient, auth_headers: dict
    ):
        """AC-03.5: DATO commercialista con delega, QUANDO configura accesso,
        ALLORA flusso di delega FiscoAPI supportato."""
        response = await client.post(
            "/api/v1/auth/spid/delegate",
            headers=auth_headers,
            json={"delegante_cf": "RSSMRA80A01H501U"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "redirect_url" in data
        assert "delegate" in data["redirect_url"].lower()
