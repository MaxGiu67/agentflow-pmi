"""
Test suite for US-01: Registrazione e login utente
Tests for all 5 Acceptance Criteria (AC-01.1 through AC-01.5)
"""

import pytest
from httpx import AsyncClient

from api.db.models import User


# ============================================================
# AC-01.1 — Happy Path: Registrazione con email e password
# ============================================================


class TestAC011Registration:
    """AC-01.1: Registrazione con email valida e password sicura."""

    async def test_ac_011_registrazione_con_dati_validi(self, client: AsyncClient):
        """AC-01.1: DATO pagina registrazione,
        QUANDO inserisco email valida + password (min 8, 1 maiuscola, 1 numero),
        ALLORA account creato + email di verifica inviata."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "anna.colombo@example.com",
                "password": "SecurePass1",
                "name": "Anna Colombo",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "anna.colombo@example.com"
        assert "id" in data
        assert "Controlla la tua email" in data["message"]

    async def test_ac_011_verifica_email_e_accesso_dashboard(
        self, client: AsyncClient, db_session
    ):
        """AC-01.1: dopo conferma email, posso accedere alla dashboard."""
        # Register
        await client.post(
            "/api/v1/auth/register",
            json={"email": "marco.ferrari@example.com", "password": "SecurePass1"},
        )

        # Get verification token from DB
        from sqlalchemy import select

        result = await db_session.execute(
            select(User).where(User.email == "marco.ferrari@example.com")
        )
        user = result.scalar_one()
        assert user.verification_token is not None
        assert user.email_verified is False

        # Verify email
        verify_response = await client.post(
            "/api/v1/auth/verify-email",
            json={"token": user.verification_token},
        )
        assert verify_response.status_code == 200

        # Now login should work
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": "marco.ferrari@example.com", "password": "SecurePass1"},
        )
        assert login_response.status_code == 200
        tokens = login_response.json()
        assert "access_token" in tokens

    async def test_ac_011_password_troppo_corta(self, client: AsyncClient):
        """AC-01.1: password < 8 caratteri rifiutata."""
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": "test@example.com", "password": "Short1"},
        )
        assert response.status_code == 422

    async def test_ac_011_password_senza_maiuscola(self, client: AsyncClient):
        """AC-01.1: password senza maiuscola rifiutata."""
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": "test@example.com", "password": "password1"},
        )
        assert response.status_code == 422

    async def test_ac_011_password_senza_numero(self, client: AsyncClient):
        """AC-01.1: password senza numero rifiutata."""
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": "test@example.com", "password": "Password"},
        )
        assert response.status_code == 422


# ============================================================
# AC-01.2 — Happy Path: Login e logout
# ============================================================


class TestAC012LoginLogout:
    """AC-01.2: Login con JWT 24h + refresh token 7gg, logout."""

    async def test_ac_012_login_con_credenziali_valide(
        self, client: AsyncClient, verified_user: User
    ):
        """AC-01.2: DATO account verificato,
        QUANDO inserisco email e password corretti,
        ALLORA ottengo JWT valido per 24h con refresh token (7gg)."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "mario.rossi@example.com", "password": "Password1"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["access_token"]
        assert data["refresh_token"]
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == 1440 * 60  # 24h in seconds

    async def test_ac_012_refresh_token(
        self, client: AsyncClient, verified_user: User
    ):
        """AC-01.2: refresh token genera nuovo access token."""
        # Login
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "mario.rossi@example.com", "password": "Password1"},
        )
        refresh_token = login_resp.json()["refresh_token"]

        # Refresh
        refresh_resp = await client.post(
            "/api/v1/auth/token",
            json={"refresh_token": refresh_token},
        )
        assert refresh_resp.status_code == 200
        data = refresh_resp.json()
        assert data["access_token"]
        assert data["refresh_token"]

    async def test_ac_012_login_email_non_verificata(
        self, client: AsyncClient, unverified_user: User
    ):
        """AC-01.2: login rifiutato se email non verificata."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "luigi.bianchi@example.com", "password": "Password1"},
        )
        assert response.status_code == 401
        assert "non verificata" in response.json()["detail"].lower()


# ============================================================
# AC-01.3 — Error: Email gia registrata
# ============================================================


class TestAC013EmailDuplicata:
    """AC-01.3: Registrazione con email gia in uso."""

    async def test_ac_013_email_gia_registrata(
        self, client: AsyncClient, verified_user: User
    ):
        """AC-01.3: DATO email gia in uso,
        QUANDO invio il form,
        ALLORA errore 'Email gia registrata' senza rivelare se l'account esiste."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "mario.rossi@example.com",
                "password": "AltroPass1",
            },
        )
        assert response.status_code == 409
        assert "gia registrata" in response.json()["detail"].lower()

    async def test_ac_013_email_diversa_accettata(self, client: AsyncClient, verified_user: User):
        """AC-01.3: email diversa viene accettata normalmente."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "nuovo.utente@example.com",
                "password": "SecurePass1",
            },
        )
        assert response.status_code == 201


# ============================================================
# AC-01.4 — Error: Password reset
# ============================================================


class TestAC014PasswordReset:
    """AC-01.4: Flusso password dimenticata."""

    async def test_ac_014_richiesta_reset_password(
        self, client: AsyncClient, verified_user: User
    ):
        """AC-01.4: DATO password dimenticata,
        QUANDO clicco 'Password dimenticata' e inserisco email,
        ALLORA ricevo link di reset valido per 1 ora."""
        response = await client.post(
            "/api/v1/auth/password-reset",
            json={"email": "mario.rossi@example.com"},
        )
        assert response.status_code == 200
        # Always returns success (anti-enumeration)
        assert "riceverai" in response.json()["message"].lower()

    async def test_ac_014_reset_password_email_inesistente(self, client: AsyncClient):
        """AC-01.4: richiesta reset con email inesistente non rivela informazioni."""
        response = await client.post(
            "/api/v1/auth/password-reset",
            json={"email": "nonexistent@example.com"},
        )
        assert response.status_code == 200  # Same response to avoid enumeration

    async def test_ac_014_conferma_reset_password(
        self, client: AsyncClient, verified_user: User, db_session
    ):
        """AC-01.4: con token valido, posso impostare nuova password."""
        # Request reset
        await client.post(
            "/api/v1/auth/password-reset",
            json={"email": "mario.rossi@example.com"},
        )

        # Get token from DB
        from sqlalchemy import select

        result = await db_session.execute(
            select(User).where(User.email == "mario.rossi@example.com")
        )
        user = result.scalar_one()
        assert user.password_reset_token is not None

        # Confirm reset
        confirm_resp = await client.post(
            "/api/v1/auth/password-reset/confirm",
            json={
                "token": user.password_reset_token,
                "new_password": "NewSecure1",
            },
        )
        assert confirm_resp.status_code == 200

        # Login with new password
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "mario.rossi@example.com", "password": "NewSecure1"},
        )
        assert login_resp.status_code == 200

    async def test_ac_014_reset_token_invalido(self, client: AsyncClient):
        """AC-01.4: token di reset invalido rifiutato."""
        response = await client.post(
            "/api/v1/auth/password-reset/confirm",
            json={
                "token": "invalid-token",
                "new_password": "NewSecure1",
            },
        )
        assert response.status_code == 400


# ============================================================
# AC-01.5 — Edge Case: Brute force protection
# ============================================================


class TestAC015BruteForce:
    """AC-01.5: Protezione brute force con lockout."""

    async def test_ac_015_lockout_dopo_5_tentativi(
        self, client: AsyncClient, verified_user: User
    ):
        """AC-01.5: DATO 5 login falliti consecutivi,
        QUANDO il sistema rileva il pattern,
        ALLORA blocca i tentativi per 15 minuti."""
        # 5 failed attempts
        for i in range(5):
            response = await client.post(
                "/api/v1/auth/login",
                json={"email": "mario.rossi@example.com", "password": f"Wrong{i}Pwd"},
            )
            if i < 4:
                assert response.status_code == 401
            else:
                # 5th attempt triggers lockout
                assert response.status_code == 429
                assert "bloccato" in response.json()["detail"].lower()

    async def test_ac_015_dopo_lockout_tentativi_bloccati(
        self, client: AsyncClient, verified_user: User
    ):
        """AC-01.5: dopo lockout, anche password corretta viene rifiutata."""
        # Trigger lockout
        for i in range(5):
            await client.post(
                "/api/v1/auth/login",
                json={"email": "mario.rossi@example.com", "password": f"Wrong{i}Pwd"},
            )

        # Even correct password is blocked
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "mario.rossi@example.com", "password": "Password1"},
        )
        assert response.status_code == 429
        assert "bloccato" in response.json()["detail"].lower()

    async def test_ac_015_login_corretto_resetta_contatore(
        self, client: AsyncClient, verified_user: User
    ):
        """AC-01.5: login corretto resetta il contatore tentativi falliti."""
        # 3 failed attempts (under threshold)
        for i in range(3):
            await client.post(
                "/api/v1/auth/login",
                json={"email": "mario.rossi@example.com", "password": f"Wrong{i}Pwd"},
            )

        # Successful login
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "mario.rossi@example.com", "password": "Password1"},
        )
        assert response.status_code == 200

        # Counter should be reset - 3 more failures shouldn't lock
        for i in range(3):
            await client.post(
                "/api/v1/auth/login",
                json={"email": "mario.rossi@example.com", "password": f"Wrong{i}Pwd"},
            )

        # Still not locked (only 3 failures since reset)
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "mario.rossi@example.com", "password": "Password1"},
        )
        assert response.status_code == 200
