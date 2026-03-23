"""
Test suite for US-02: Profilo utente e configurazione azienda
Tests for 4 Acceptance Criteria (AC-02.1 through AC-02.4)
"""

import pytest
from httpx import AsyncClient

from api.db.models import Tenant, User
from tests.conftest import get_auth_token


# ============================================================
# AC-02.1 — Happy Path: Configurazione completa
# ============================================================


class TestAC021ConfigurazioneCompleta:
    """AC-02.1: Configurazione profilo azienda completa."""

    async def test_ac_021_get_profilo_autenticato(
        self, client: AsyncClient, auth_headers: dict
    ):
        """AC-02.1: DATO autenticato, QUANDO accedo al profilo, ALLORA vedo i dati."""
        response = await client.get("/api/v1/profile", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "mario.rossi@example.com"
        assert data["tipo_azienda"] == "srl"
        assert data["regime_fiscale"] == "ordinario"
        assert data["piva"] == "12345678901"

    async def test_ac_021_aggiorna_profilo_completo(
        self, client: AsyncClient, auth_headers: dict
    ):
        """AC-02.1: QUANDO inserisco tipo azienda, regime, P.IVA, ATECO,
        ALLORA il profilo e salvato."""
        response = await client.patch(
            "/api/v1/profile",
            headers=auth_headers,
            json={
                "azienda_nome": "Rossi Consulting SRL",
                "codice_ateco": "62.01.00",
                "name": "Mario Rossi",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["azienda_nome"] == "Rossi Consulting SRL"
        assert data["codice_ateco"] == "62.01.00"

    async def test_ac_021_setup_profilo_nuovo_utente(
        self, client: AsyncClient, verified_user_no_tenant: User
    ):
        """AC-02.1: nuovo utente senza tenant, crea profilo azienda."""
        token = await get_auth_token(client, "nuova.utente@example.com", "Password1")
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.patch(
            "/api/v1/profile",
            headers=headers,
            json={
                "tipo_azienda": "piva",
                "regime_fiscale": "forfettario",
                "piva": "04532710755",
                "azienda_nome": "Studio Nuova Utente",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["tipo_azienda"] == "piva"
        assert data["regime_fiscale"] == "forfettario"
        assert data["piva"] == "04532710755"

    async def test_ac_021_accesso_non_autenticato_rifiutato(self, client: AsyncClient):
        """AC-02.1: senza JWT, accesso negato."""
        response = await client.get("/api/v1/profile")
        assert response.status_code in (401, 403)


# ============================================================
# AC-02.2 — Error: P.IVA formato invalido
# ============================================================


class TestAC022PIVAInvalida:
    """AC-02.2: Validazione P.IVA."""

    async def test_ac_022_piva_non_11_cifre(
        self, client: AsyncClient, auth_headers: dict
    ):
        """AC-02.2: DATO P.IVA con formato errato (non 11 cifre),
        ALLORA errore di validazione."""
        response = await client.patch(
            "/api/v1/profile",
            headers=auth_headers,
            json={"piva": "12345"},
        )
        assert response.status_code == 422

    async def test_ac_022_piva_con_lettere(
        self, client: AsyncClient, auth_headers: dict
    ):
        """AC-02.2: P.IVA con lettere rifiutata."""
        response = await client.patch(
            "/api/v1/profile",
            headers=auth_headers,
            json={"piva": "1234567890A"},
        )
        assert response.status_code == 422

    async def test_ac_022_piva_checksum_invalido(
        self, client: AsyncClient, auth_headers: dict
    ):
        """AC-02.2: P.IVA con checksum errato rifiutata."""
        response = await client.patch(
            "/api/v1/profile",
            headers=auth_headers,
            json={"piva": "12345678900"},  # Invalid checksum
        )
        assert response.status_code == 422


# ============================================================
# AC-02.3 — Error: Codice ATECO inesistente
# ============================================================


class TestAC023ATECOInesistente:
    """AC-02.3: Validazione codice ATECO."""

    async def test_ac_023_ateco_formato_errato(
        self, client: AsyncClient, auth_headers: dict
    ):
        """AC-02.3: DATO codice ATECO non valido, ALLORA errore."""
        response = await client.patch(
            "/api/v1/profile",
            headers=auth_headers,
            json={"codice_ateco": "ABC"},
        )
        assert response.status_code == 422

    async def test_ac_023_ateco_sezione_inesistente(
        self, client: AsyncClient, auth_headers: dict
    ):
        """AC-02.3: DATO sezione ATECO inesistente, ALLORA errore con suggerimenti."""
        response = await client.patch(
            "/api/v1/profile",
            headers=auth_headers,
            json={"codice_ateco": "00.01.00"},
        )
        assert response.status_code == 422

    async def test_ac_023_ateco_valido_accettato(
        self, client: AsyncClient, auth_headers: dict
    ):
        """AC-02.3: codice ATECO valido accettato."""
        response = await client.patch(
            "/api/v1/profile",
            headers=auth_headers,
            json={"codice_ateco": "62.01.00"},
        )
        assert response.status_code == 200


# ============================================================
# AC-02.4 — Edge Case: Modifica profilo dopo setup piano conti
# ============================================================


class TestAC024ModificaProfiloDopoPiano:
    """AC-02.4: Avviso ricreazione piano conti al cambio tipo azienda."""

    async def test_ac_024_cambio_tipo_azienda_con_piano_conti(
        self, client: AsyncClient, user_with_odoo: User
    ):
        """AC-02.4: DATO piano conti gia creato, QUANDO cambio tipo azienda,
        ALLORA il sistema avvisa che il piano dovra essere ricreato."""
        token = await get_auth_token(client, "paolo.conti@example.com", "Password1")
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.patch(
            "/api/v1/profile",
            headers=headers,
            json={"tipo_azienda": "piva", "regime_fiscale": "forfettario"},
        )
        assert response.status_code == 409
        detail = response.json()["detail"]
        assert detail["requires_confirmation"] is True
        assert "piano_dei_conti" in detail["affected_areas"]

    async def test_ac_024_cambio_confermato_accettato(
        self, client: AsyncClient, user_with_odoo: User
    ):
        """AC-02.4: con conferma esplicita, la modifica procede."""
        token = await get_auth_token(client, "paolo.conti@example.com", "Password1")
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.patch(
            "/api/v1/profile?confirm=true",
            headers=headers,
            json={"tipo_azienda": "piva", "regime_fiscale": "forfettario"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["tipo_azienda"] == "piva"
        assert data["regime_fiscale"] == "forfettario"
