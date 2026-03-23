"""
Test suite for US-12: Setup piano dei conti personalizzato
Tests for 4 Acceptance Criteria (AC-12.1 through AC-12.4)

Updated for ADR-007: AccountingEngine replaces Odoo CE 18.
"""

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient

from api.db.models import Tenant, User
from tests.conftest import get_auth_token


# ============================================================
# AC-12.1 — Happy Path: Piano conti per SRL in regime ordinario
# ============================================================


class TestAC121PianoContiSRL:
    """AC-12.1: Piano conti CEE per SRL ordinario."""

    async def test_ac_121_crea_piano_conti_srl_ordinario(
        self, client: AsyncClient, auth_headers: dict
    ):
        """AC-12.1: DATO profilo SRL ordinario, QUANDO ContaAgent configura,
        ALLORA piano conti CEE con conti SP e CE, registri IVA, journal banca/cassa."""
        response = await client.post(
            "/api/v1/accounting/chart",
            headers=auth_headers,
            json={},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["tipo_azienda"] == "srl"
        assert data["regime_fiscale"] == "ordinario"
        assert len(data["accounts"]) > 10  # SRL has many accounts
        assert "Vendite" in data["journals"]
        assert "Acquisti" in data["journals"]
        assert "Banca" in data["journals"]
        assert "22%" in data["tax_codes"]  # IVA ordinaria

        # Check specific CEE accounts
        codes = {a["code"] for a in data["accounts"]}
        assert "1010" in codes  # Cassa
        assert "2010" in codes  # Fornitori
        assert "3010" in codes  # Capitale sociale
        assert "4010" in codes  # Ricavi

    async def test_ac_121_get_piano_conti_dopo_creazione(
        self, client: AsyncClient, auth_headers: dict
    ):
        """AC-12.1: dopo creazione, GET /accounting/chart ritorna il piano."""
        # Create
        await client.post(
            "/api/v1/accounting/chart",
            headers=auth_headers,
            json={},
        )

        # Get
        response = await client.get(
            "/api/v1/accounting/chart",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["accounts"]) > 10


# ============================================================
# AC-12.2 — Happy Path: Piano conti per P.IVA forfettaria
# ============================================================


class TestAC122PianoContiForfettario:
    """AC-12.2: Piano conti semplificato per forfettario."""

    async def test_ac_122_crea_piano_conti_forfettario(
        self, client: AsyncClient, verified_user_no_tenant: User
    ):
        """AC-12.2: DATO P.IVA forfettario, ALLORA piano semplificato senza IVA."""
        # Setup: create user with forfettario profile
        token = await get_auth_token(client, "nuova.utente@example.com", "Password1")
        headers = {"Authorization": f"Bearer {token}"}

        # Set profile as forfettario
        await client.patch(
            "/api/v1/profile",
            headers=headers,
            json={
                "tipo_azienda": "piva",
                "regime_fiscale": "forfettario",
                "piva": "04532710755",
            },
        )

        # Create piano conti
        response = await client.post(
            "/api/v1/accounting/chart",
            headers=headers,
            json={},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["regime_fiscale"] == "forfettario"
        assert len(data["accounts"]) < 15  # Simplified
        assert data["tax_codes"] == []  # No IVA for forfettario

        # Check for forfettario-specific accounts
        account_names = {a["name"] for a in data["accounts"]}
        assert "Imposta sostitutiva" in account_names or "Costi deducibili" in account_names


# ============================================================
# AC-12.3 — Error: DB operation failed (ADR-007: replaces Odoo test)
# ============================================================


class TestAC123DBFallita:
    """AC-12.3: Database operation failure with retry."""

    async def test_ac_123_db_operation_fails(
        self, client: AsyncClient, auth_headers: dict, db_session
    ):
        """AC-12.3: DATO operazione DB fallita, ALLORA retry e errore 503."""
        from api.modules.fiscal.accounting_engine import AccountingEngine
        from api.modules.accounting.service import AccountingService

        # Create an engine that raises ConnectionError (simulating DB failure)
        broken_engine = AccountingEngine(db_session)
        original_create = broken_engine.create_piano_conti

        async def failing_create(*args, **kwargs):
            raise ConnectionError("Impossibile connettersi al database")

        broken_engine.create_piano_conti = failing_create

        def get_broken_service(db=None):
            return AccountingService(db_session, engine=broken_engine)

        from api.modules.accounting.router import get_accounting_service
        from api.main import app

        app.dependency_overrides[get_accounting_service] = lambda: get_broken_service()

        response = await client.post(
            "/api/v1/accounting/chart",
            headers=auth_headers,
            json={},
        )
        assert response.status_code == 503
        assert "tentativi" in response.json()["detail"].lower()

        # Clean up override
        if get_accounting_service in app.dependency_overrides:
            del app.dependency_overrides[get_accounting_service]


# ============================================================
# AC-12.4 — Edge Case: Tipo azienda non standard
# ============================================================


class TestAC124TipoNonStandard:
    """AC-12.4: Tipo azienda 'altro' con piano generico."""

    async def test_ac_124_piano_generico_con_nota(
        self, client: AsyncClient, verified_user_no_tenant: User
    ):
        """AC-12.4: DATO tipo 'Altro', ALLORA piano generico CEE con nota commercialista."""
        token = await get_auth_token(client, "nuova.utente@example.com", "Password1")
        headers = {"Authorization": f"Bearer {token}"}

        # Set profile as 'altro'
        await client.patch(
            "/api/v1/profile",
            headers=headers,
            json={
                "tipo_azienda": "altro",
                "regime_fiscale": "ordinario",
                "piva": "04532710755",
                "codice_ateco": "62.01.00",
            },
        )

        # Create piano conti
        response = await client.post(
            "/api/v1/accounting/chart",
            headers=headers,
            json={},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["note"] is not None
        assert "generico" in data["note"].lower()
        assert "commercialista" in data["note"].lower()

    async def test_ac_124_piano_non_duplicato(
        self, client: AsyncClient, user_with_odoo: User
    ):
        """AC-12.4: se piano conti gia esiste, errore senza force."""
        token = await get_auth_token(client, "paolo.conti@example.com", "Password1")
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.post(
            "/api/v1/accounting/chart",
            headers=headers,
            json={},
        )
        assert response.status_code == 400
        assert "gia esistente" in response.json()["detail"].lower()

    async def test_ac_124_piano_ricreato_con_force(
        self, client: AsyncClient, user_with_odoo: User
    ):
        """AC-12.4: con force=true, il piano viene ricreato."""
        token = await get_auth_token(client, "paolo.conti@example.com", "Password1")
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.post(
            "/api/v1/accounting/chart",
            headers=headers,
            json={"force": True},
        )
        assert response.status_code == 201

    async def test_ac_124_profilo_non_configurato(
        self, client: AsyncClient, verified_user_no_tenant: User
    ):
        """AC-12.4: senza profilo azienda, errore chiaro."""
        token = await get_auth_token(client, "nuova.utente@example.com", "Password1")
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.post(
            "/api/v1/accounting/chart",
            headers=headers,
            json={},
        )
        assert response.status_code == 400
        assert "profilo" in response.json()["detail"].lower()
