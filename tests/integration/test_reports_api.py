"""
Test suite for US-19: Report export commercialista
Tests for 4 Acceptance Criteria (AC-19.1 through AC-19.4)
"""

from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import Invoice, Tenant, User
from tests.conftest import create_invoice, get_auth_token


# ============================================================
# AC-19.1 — Export PDF trimestrale
# ============================================================


class TestAC191ExportPDFTrimestrale:
    """AC-19.1: Export report PDF trimestrale con riepilogo fatture."""

    async def test_ac_191_export_pdf_q1(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        tenant: Tenant,
    ):
        """AC-19.1: DATO fatture nel trimestre, QUANDO export PDF Q1,
        ALLORA report con riepilogo completo."""
        # Insert invoices in Q1 2026
        inv1 = create_invoice(
            tenant_id=tenant.id,
            numero="FT-Q1-001",
            piva="IT11111111111",
            nome="Fornitore Uno",
            importo=1000.0,
            category="Consulenze",
            data=date(2026, 1, 15),
        )
        inv2 = create_invoice(
            tenant_id=tenant.id,
            numero="FT-Q1-002",
            piva="IT22222222222",
            nome="Fornitore Due",
            importo=500.0,
            category="Utenze",
            data=date(2026, 2, 20),
        )
        db_session.add(inv1)
        db_session.add(inv2)
        await db_session.flush()

        response = await client.get(
            "/api/v1/reports/commercialista?period=Q1-2026&format=pdf",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["period"] == "Q1-2026"
        assert data["format"] == "pdf"
        assert data["total_fatture_passive"] == 2
        assert data["totale_costi"] > 0
        assert data["tenant_name"] == "Test SRL"
        assert data["regime_fiscale"] == "ordinario"
        assert len(data["fatture_passive"]) == 2
        assert "generato" in data["message"].lower()

    async def test_ac_191_report_includes_iva_summary(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        tenant: Tenant,
    ):
        """AC-19.1: Report include riepilogo IVA (credito/debito/saldo)."""
        inv = create_invoice(
            tenant_id=tenant.id,
            numero="FT-IVA-001",
            piva="IT33333333333",
            importo=2000.0,
            data=date(2026, 3, 10),
        )
        db_session.add(inv)
        await db_session.flush()

        response = await client.get(
            "/api/v1/reports/commercialista?period=Q1-2026&format=pdf",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "totale_iva_credito" in data
        assert "totale_iva_debito" in data
        assert "saldo_iva" in data


# ============================================================
# AC-19.2 — Export CSV
# ============================================================


class TestAC192ExportCSV:
    """AC-19.2: Export report in formato CSV."""

    async def test_ac_192_export_csv(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        tenant: Tenant,
    ):
        """AC-19.2: DATO fatture, QUANDO export CSV,
        ALLORA report con format=csv e dati strutturati."""
        inv = create_invoice(
            tenant_id=tenant.id,
            numero="FT-CSV-001",
            piva="IT44444444444",
            importo=750.0,
            data=date(2026, 1, 5),
            category="Materie prime",
        )
        db_session.add(inv)
        await db_session.flush()

        response = await client.get(
            "/api/v1/reports/commercialista?period=Q1-2026&format=csv",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["format"] == "csv"
        assert data["total_fatture_passive"] >= 1
        assert len(data["fatture_passive"]) >= 1
        assert "costi_per_categoria" in data


# ============================================================
# AC-19.3 — Periodo senza dati
# ============================================================


class TestAC193PeriodoSenzaDati:
    """AC-19.3: Periodo senza fatture restituisce report vuoto con messaggio."""

    async def test_ac_193_periodo_vuoto(
        self, client: AsyncClient, auth_headers: dict
    ):
        """AC-19.3: DATO nessuna fattura nel periodo, QUANDO export,
        ALLORA report vuoto con messaggio appropriato."""
        response = await client.get(
            "/api/v1/reports/commercialista?period=Q4-2020&format=pdf",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_fatture_attive"] == 0
        assert data["total_fatture_passive"] == 0
        assert "nessuna" in data["message"].lower()

    async def test_ac_193_periodo_invalido(
        self, client: AsyncClient, auth_headers: dict
    ):
        """AC-19.3: DATO periodo non valido, QUANDO export,
        ALLORA errore con periodo non valido."""
        response = await client.get(
            "/api/v1/reports/commercialista?period=X9-2026&format=pdf",
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "periodo" in response.json()["detail"].lower() or "non valido" in response.json()["detail"].lower()


# ============================================================
# AC-19.4 — Fatture non categorizzate
# ============================================================


class TestAC194FattureNonCategorizzate:
    """AC-19.4: Report segnala fatture non categorizzate."""

    async def test_ac_194_fatture_non_categorizzate(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        tenant: Tenant,
    ):
        """AC-19.4: DATO fatture senza categoria, QUANDO export,
        ALLORA report le segnala come non categorizzate."""
        # Invoice without category
        inv = create_invoice(
            tenant_id=tenant.id,
            numero="FT-NOCAT-001",
            piva="IT55555555555",
            importo=300.0,
            data=date(2026, 2, 15),
            category=None,  # not categorized
        )
        db_session.add(inv)
        await db_session.flush()

        response = await client.get(
            "/api/v1/reports/commercialista?period=Q1-2026&format=pdf",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["has_uncategorized"] is True
        assert len(data["fatture_non_categorizzate"]) >= 1
        # The uncategorized invoice should be listed
        uncategorized_numeri = [f["numero_fattura"] for f in data["fatture_non_categorizzate"]]
        assert "FT-NOCAT-001" in uncategorized_numeri
