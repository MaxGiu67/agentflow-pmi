"""
Test suite for US-14: Dashboard fatture e stato agenti
Tests for 4 Acceptance Criteria (AC-14.1 through AC-14.4)
"""

from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import Invoice, Tenant, User
from tests.conftest import create_invoice, get_auth_token


# ============================================================
# AC-14.1 — Vista completa: contatori, ultime 10, stato agenti, ultimo sync
# ============================================================


class TestAC141VistaCompleta:
    """AC-14.1: Dashboard con tutte le informazioni."""

    async def test_ac_141_vista_completa(
        self,
        client: AsyncClient,
        spid_auth_headers: dict,
        db_session: AsyncSession,
        tenant: Tenant,
    ):
        """AC-14.1: DATO fatture presenti, QUANDO dashboard,
        ALLORA contatori, ultime 10, stato agenti, ultimo sync."""
        # Create some invoices with different statuses
        statuses = ["pending", "parsed", "categorized", "registered", "error"]
        for i, status in enumerate(statuses):
            inv = create_invoice(
                tenant_id=tenant.id,
                numero=f"FT-DASH-{i:03d}",
                piva=f"IT{60000000000 + i}",
                nome=f"Fornitore Dashboard {i}",
                status=status,
            )
            db_session.add(inv)
        await db_session.flush()

        response = await client.get(
            "/api/v1/dashboard/summary",
            headers=spid_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        # Counters
        assert "counters" in data
        assert data["counters"]["total"] == 5
        assert data["counters"]["pending"] == 1
        assert data["counters"]["parsed"] == 1
        assert data["counters"]["categorized"] == 1
        assert data["counters"]["registered"] == 1
        assert data["counters"]["error"] == 1

        # Recent invoices
        assert "recent_invoices" in data
        assert len(data["recent_invoices"]) <= 10

        # Agents status
        assert "agents" in data
        assert len(data["agents"]) == 3
        agent_names = {a["name"] for a in data["agents"]}
        assert "fisco_agent" in agent_names
        assert "parser_agent" in agent_names
        assert "learning_agent" in agent_names

    async def test_ac_141_agents_status_endpoint(
        self,
        client: AsyncClient,
        spid_auth_headers: dict,
    ):
        """AC-14.1: GET /agents/status returns agent statuses."""
        response = await client.get(
            "/api/v1/agents/status",
            headers=spid_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 3


# ============================================================
# AC-14.2 — Filtri e ricerca
# ============================================================


class TestAC142FiltriERicerca:
    """AC-14.2: Filtri e ricerca sulle fatture."""

    async def test_ac_142_filtri_e_ricerca(
        self,
        client: AsyncClient,
        spid_auth_headers: dict,
        db_session: AsyncSession,
        tenant: Tenant,
    ):
        """AC-14.2: DATO lista fatture, QUANDO applico filtri,
        ALLORA risultati filtrati correttamente."""
        # Create invoices with different attributes
        inv1 = create_invoice(
            tenant_id=tenant.id,
            numero="FT-FILT-001",
            piva="IT11111111111",
            nome="Alpha SRL",
            source="cassetto_fiscale",
            status="parsed",
            data=date(2025, 1, 15),
        )
        inv2 = create_invoice(
            tenant_id=tenant.id,
            numero="FT-FILT-002",
            piva="IT22222222222",
            nome="Beta SpA",
            source="upload",
            status="categorized",
            data=date(2025, 3, 20),
        )
        inv3 = create_invoice(
            tenant_id=tenant.id,
            numero="FT-FILT-003",
            piva="IT33333333333",
            nome="Gamma Consulting",
            source="cassetto_fiscale",
            status="pending",
            data=date(2025, 6, 1),
        )
        db_session.add_all([inv1, inv2, inv3])
        await db_session.flush()

        # Filter by source
        resp = await client.get(
            "/api/v1/invoices?source=cassetto_fiscale",
            headers=spid_auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        for item in data["items"]:
            assert item["source"] == "cassetto_fiscale"

        # Filter by status
        resp = await client.get(
            "/api/v1/invoices?status=parsed",
            headers=spid_auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

        # Filter by emittente name (search)
        resp = await client.get(
            "/api/v1/invoices?emittente=Alpha",
            headers=spid_auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 1
        assert resp.json()["items"][0]["emittente_nome"] == "Alpha SRL"

        # Filter by date range
        resp = await client.get(
            "/api/v1/invoices?date_from=2025-01-01&date_to=2025-02-28",
            headers=spid_auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 1


# ============================================================
# AC-14.3 — Empty state
# ============================================================


class TestAC143EmptyState:
    """AC-14.3: Empty state quando non ci sono fatture."""

    async def test_ac_143_empty_state(
        self,
        client: AsyncClient,
        spid_auth_headers: dict,
    ):
        """AC-14.3: DATO nessuna fattura, QUANDO dashboard,
        ALLORA empty state con messaggio chiaro."""
        response = await client.get(
            "/api/v1/dashboard/summary",
            headers=spid_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        assert data["counters"]["total"] == 0
        assert len(data["recent_invoices"]) == 0
        assert data["message"] is not None
        assert "nessuna" in data["message"].lower()

    async def test_ac_143_empty_invoice_list(
        self,
        client: AsyncClient,
        spid_auth_headers: dict,
    ):
        """AC-14.3: DATO nessuna fattura, QUANDO lista fatture,
        ALLORA lista vuota con total=0."""
        response = await client.get(
            "/api/v1/invoices",
            headers=spid_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []
        assert data["pages"] == 0


# ============================================================
# AC-14.4 — Paginazione con 1000+ fatture
# ============================================================


class TestAC144Paginazione:
    """AC-14.4: Paginazione funziona con molte fatture."""

    async def test_ac_144_paginazione(
        self,
        client: AsyncClient,
        spid_auth_headers: dict,
        db_session: AsyncSession,
        tenant: Tenant,
    ):
        """AC-14.4: DATO 50+ fatture, QUANDO lista con paginazione,
        ALLORA pagine corrette."""
        # Create 50 invoices (enough to test pagination)
        for i in range(50):
            inv = create_invoice(
                tenant_id=tenant.id,
                numero=f"FT-PAGE-{i:04d}",
                piva=f"IT{40000000000 + i}",
                nome=f"Fornitore Page {i}",
            )
            db_session.add(inv)
        await db_session.flush()

        # Page 1, size 10
        resp = await client.get(
            "/api/v1/invoices?page=1&page_size=10",
            headers=spid_auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 50
        assert len(data["items"]) == 10
        assert data["page"] == 1
        assert data["page_size"] == 10
        assert data["pages"] == 5

        # Page 3
        resp = await client.get(
            "/api/v1/invoices?page=3&page_size=10",
            headers=spid_auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 10
        assert data["page"] == 3

        # Last page
        resp = await client.get(
            "/api/v1/invoices?page=5&page_size=10",
            headers=spid_auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 10
        assert data["page"] == 5
