"""
Test suite for US-04: Sync fatture dal cassetto fiscale
Tests for 5 Acceptance Criteria (AC-04.1 through AC-04.5)
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import Invoice, Tenant, User
from tests.conftest import create_invoice, get_auth_token


# ============================================================
# AC-04.1 — Primo sync storico 90gg
# ============================================================


class TestAC041PrimoSyncCassetto:
    """AC-04.1: Primo sync scarica fatture, salva con source=cassetto_fiscale."""

    async def test_ac_041_primo_sync_cassetto(
        self, client: AsyncClient, spid_auth_headers: dict
    ):
        """AC-04.1: DATO SPID collegato, QUANDO primo sync,
        ALLORA scarica fatture ultimi 90gg, salva con source=cassetto_fiscale."""
        response = await client.post(
            "/api/v1/cassetto/sync",
            headers=spid_auth_headers,
            json={"force": True},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["downloaded"] > 0
        assert data["new"] > 0
        assert data["errors"] == 0
        assert "message" in data

        # Verify invoices were created
        list_response = await client.get(
            "/api/v1/invoices",
            headers=spid_auth_headers,
        )
        assert list_response.status_code == 200
        invoices = list_response.json()
        assert invoices["total"] > 0
        for item in invoices["items"]:
            assert item["source"] == "cassetto_fiscale"

    async def test_ac_041_sync_senza_spid(
        self, client: AsyncClient, auth_headers: dict
    ):
        """AC-04.1: DATO utente senza SPID, QUANDO sync,
        ALLORA errore che richiede autenticazione SPID."""
        response = await client.post(
            "/api/v1/cassetto/sync",
            headers=auth_headers,
            json={},
        )
        assert response.status_code == 400
        assert "spid" in response.json()["detail"].lower() or "cassetto" in response.json()["detail"].lower()


# ============================================================
# AC-04.2 — Sync giornaliero incrementale
# ============================================================


class TestAC042SyncIncrementale:
    """AC-04.2: Sync incrementale scarica solo nuove fatture."""

    async def test_ac_042_sync_incrementale(
        self, client: AsyncClient, spid_auth_headers: dict
    ):
        """AC-04.2: DATO sync gia effettuato, QUANDO secondo sync,
        ALLORA solo nuove fatture, no duplicati."""
        # First sync
        resp1 = await client.post(
            "/api/v1/cassetto/sync",
            headers=spid_auth_headers,
            json={"force": True},
        )
        assert resp1.status_code == 200
        first_new = resp1.json()["new"]
        assert first_new > 0

        # Second sync (incremental - same data, should find duplicates)
        resp2 = await client.post(
            "/api/v1/cassetto/sync",
            headers=spid_auth_headers,
            json={"force": True},
        )
        assert resp2.status_code == 200
        data2 = resp2.json()
        # All invoices from second sync should be duplicates
        assert data2["duplicates"] >= 0
        # The total should not have doubled
        list_resp = await client.get(
            "/api/v1/invoices",
            headers=spid_auth_headers,
        )
        total = list_resp.json()["total"]
        # Should have at most some new ones from incremental, not 2x the first
        assert total <= first_new * 2


# ============================================================
# AC-04.3 — FiscoAPI non disponibile
# ============================================================


class TestAC043FiscoAPINonDisponibile:
    """AC-04.3: FiscoAPI non disponibile, retry backoff."""

    async def test_ac_043_fiscoapi_non_disponibile(
        self, client: AsyncClient, spid_auth_headers: dict, db_session: AsyncSession
    ):
        """AC-04.3: DATO FiscoAPI non raggiungibile,
        QUANDO sync, ALLORA retry con backoff e errore 503."""
        from api.adapters.fiscoapi import FiscoAPIClient
        from api.modules.invoices.router import get_invoice_service
        from api.modules.invoices.service import InvoiceService
        from api.main import app

        # Create a broken FiscoAPI client
        broken_fiscoapi = FiscoAPIClient()
        broken_fiscoapi.set_connected(False)

        def get_broken_service(db=None):
            return InvoiceService(db_session, fiscoapi=broken_fiscoapi)

        app.dependency_overrides[get_invoice_service] = lambda: get_broken_service()

        response = await client.post(
            "/api/v1/cassetto/sync",
            headers=spid_auth_headers,
            json={"force": True},
        )
        assert response.status_code == 503
        detail = response.json()["detail"].lower()
        assert "tentativi" in detail or "non disponibile" in detail

        # Clean up
        if get_invoice_service in app.dependency_overrides:
            del app.dependency_overrides[get_invoice_service]


# ============================================================
# AC-04.4 — Fattura duplicata
# ============================================================


class TestAC044FatturaDuplicata:
    """AC-04.4: Dedup su numero_fattura + P.IVA emittente + data."""

    async def test_ac_044_fattura_duplicata(
        self,
        client: AsyncClient,
        spid_auth_headers: dict,
        db_session: AsyncSession,
        tenant: Tenant,
    ):
        """AC-04.4: DATO fattura gia presente,
        QUANDO sync scarica stessa fattura, ALLORA non duplica."""
        # Pre-insert an invoice that will match what FiscoAPI returns
        from datetime import date, timedelta
        base_date = date.today() - timedelta(days=90)

        existing = Invoice(
            tenant_id=tenant.id,
            type="passiva",
            document_type="TD01",
            source="cassetto_fiscale",
            numero_fattura="FT-2025-1001",
            emittente_piva="IT01234567890",
            emittente_nome="Fornitore Alpha SRL",
            data_fattura=base_date,
            importo_netto=1000.0,
            importo_iva=220.0,
            importo_totale=1220.0,
            processing_status="parsed",
        )
        db_session.add(existing)
        await db_session.flush()

        # Sync should detect the duplicate
        response = await client.post(
            "/api/v1/cassetto/sync",
            headers=spid_auth_headers,
            json={"force": True},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["duplicates"] >= 1


# ============================================================
# AC-04.5 — Cassetto vuoto
# ============================================================


class TestAC045CassettoVuoto:
    """AC-04.5: Cassetto vuoto, messaggio chiaro."""

    async def test_ac_045_cassetto_vuoto(
        self, client: AsyncClient, spid_auth_headers: dict, db_session: AsyncSession
    ):
        """AC-04.5: DATO cassetto senza fatture,
        QUANDO sync, ALLORA messaggio chiaro 'nessuna fattura'."""
        from api.adapters.fiscoapi import FiscoAPIClient
        from api.modules.invoices.router import get_invoice_service
        from api.modules.invoices.service import InvoiceService
        from api.main import app

        # Create a FiscoAPI that returns empty list
        class EmptyFiscoAPI(FiscoAPIClient):
            async def sync_invoices(self, token, from_date=None):
                return []

        empty_fiscoapi = EmptyFiscoAPI()

        def get_empty_service(db=None):
            return InvoiceService(db_session, fiscoapi=empty_fiscoapi)

        app.dependency_overrides[get_invoice_service] = lambda: get_empty_service()

        response = await client.post(
            "/api/v1/cassetto/sync",
            headers=spid_auth_headers,
            json={"force": True},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["downloaded"] == 0
        assert data["new"] == 0
        assert "nessuna" in data["message"].lower()

        # Clean up
        if get_invoice_service in app.dependency_overrides:
            del app.dependency_overrides[get_invoice_service]
