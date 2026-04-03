"""
Tests for GET /dashboard/yearly-stats endpoint.
"""

import json
from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import Invoice, Tenant, User
from tests.conftest import get_auth_token


def _make_invoice(
    tenant_id,
    tipo: str = "attiva",
    numero: str = "FT-001",
    data_fattura: date | None = None,
    importo_netto: float = 1000.0,
    importo_iva: float = 220.0,
    importo_totale: float = 1220.0,
    emittente_nome: str = "Emittente SRL",
    emittente_piva: str = "IT11111111111",
    structured_data: dict | None = None,
) -> Invoice:
    return Invoice(
        tenant_id=tenant_id,
        type=tipo,
        document_type="TD01",
        source="cassetto_fiscale",
        numero_fattura=numero,
        emittente_piva=emittente_piva,
        emittente_nome=emittente_nome,
        data_fattura=data_fattura or date(2024, 3, 15),
        importo_netto=importo_netto,
        importo_iva=importo_iva,
        importo_totale=importo_totale,
        structured_data=structured_data,
        processing_status="pending",
    )


class TestYearlyStatsReturnsData:
    """Test that yearly-stats returns correct aggregated data."""

    async def test_yearly_stats_returns_data(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        tenant: Tenant,
    ):
        """Given invoices in 2024, when requesting yearly-stats for 2024,
        then counts, totals, monthly breakdown, and top entities are returned."""
        # Create attiva invoices (emesse)
        for i in range(3):
            inv = _make_invoice(
                tenant_id=tenant.id,
                tipo="attiva",
                numero=f"FA-2024-{i:03d}",
                data_fattura=date(2024, i + 1, 15),
                importo_netto=1000.0 * (i + 1),
                importo_iva=220.0 * (i + 1),
                importo_totale=1220.0 * (i + 1),
                emittente_nome="MIA AZIENDA SRL",
                emittente_piva="IT99999999999",
                structured_data={
                    "destinatario_nome": f"Cliente {chr(65 + i)} SPA",
                    "destinatario_piva": f"IT{10000000000 + i}",
                },
            )
            db_session.add(inv)

        # Create passiva invoices (ricevute)
        for i in range(2):
            inv = _make_invoice(
                tenant_id=tenant.id,
                tipo="passiva",
                numero=f"FP-2024-{i:03d}",
                data_fattura=date(2024, i + 1, 20),
                importo_netto=500.0 * (i + 1),
                importo_iva=110.0 * (i + 1),
                importo_totale=610.0 * (i + 1),
                emittente_nome=f"Fornitore {chr(65 + i)} SRL",
                emittente_piva=f"IT{20000000000 + i}",
            )
            db_session.add(inv)

        await db_session.flush()

        response = await client.get(
            "/api/v1/dashboard/yearly-stats?year=2024",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        # Year
        assert data["year"] == 2024

        # Fatture attive
        fa = data["fatture_attive"]
        assert fa["count"] == 3
        # totale = 1220 + 2440 + 3660 = 7320 (lordo, still available)
        assert fa["totale"] == 7320.0
        # imponibile (netto) = 1000 + 2000 + 3000 = 6000
        assert fa["imponibile"] == 6000.0

        # Fatture passive
        fp = data["fatture_passive"]
        assert fp["count"] == 2
        # totale = 610 + 1220 = 1830 (lordo)
        assert fp["totale"] == 1830.0
        # imponibile (netto) = 500 + 1000 = 1500
        assert fp["imponibile"] == 1500.0

        # Margine lordo (US-70: uses netto, not totale)
        # ricavi_totali = imponibile attive = 6000
        # costi_totali = imponibile passive = 1500
        assert data["ricavi_totali"] == 6000.0
        assert data["costi_totali"] == 1500.0
        assert data["margine_lordo"] == 6000.0 - 1500.0

        # IVA netta (US-70 AC-70.5)
        assert "iva_netta" in data
        # IVA debito = 220 + 440 + 660 = 1320
        assert data["iva_netta"]["iva_debito"] == 1320.0
        # IVA credito = 110 + 220 = 330
        assert data["iva_netta"]["iva_credito"] == 330.0
        assert data["iva_netta"]["saldo"] == 990.0

        # Fatture per mese (12 months, now netto amounts)
        assert len(data["fatture_per_mese"]) == 12
        jan = data["fatture_per_mese"][0]
        assert jan["mese"] == 1
        assert jan["attive_count"] == 1
        assert jan["passive_count"] == 1

        # Top clienti (from structured_data of attiva invoices, now netto)
        assert len(data["top_clienti"]) == 3
        # Sorted by totale desc: Cliente C (3000 netto), B (2000), A (1000)
        assert data["top_clienti"][0]["totale"] == 3000.0

        # Top fornitori (from passiva invoices, now netto)
        assert len(data["top_fornitori"]) == 2
        # Sorted by totale desc: Fornitore B (1000 netto), Fornitore A (500 netto)
        assert data["top_fornitori"][0]["totale"] == 1000.0


class TestYearlyStatsAvailableYears:
    """Test that available_years is populated correctly."""

    async def test_yearly_stats_available_years(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        tenant: Tenant,
    ):
        """Given invoices in 2023 and 2024, available_years contains both."""
        inv1 = _make_invoice(
            tenant_id=tenant.id,
            tipo="attiva",
            numero="FA-2023-001",
            data_fattura=date(2023, 6, 1),
            structured_data={"destinatario_nome": "Cliente X", "destinatario_piva": "IT00000000001"},
        )
        inv2 = _make_invoice(
            tenant_id=tenant.id,
            tipo="passiva",
            numero="FP-2024-001",
            data_fattura=date(2024, 9, 1),
        )
        db_session.add_all([inv1, inv2])
        await db_session.flush()

        response = await client.get(
            "/api/v1/dashboard/yearly-stats?year=2024",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert 2023 in data["available_years"]
        assert 2024 in data["available_years"]


class TestYearlyStatsEmptyYear:
    """Test behavior for a year with no invoices."""

    async def test_yearly_stats_empty_year(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Given no invoices for 2020, all aggregates are zero."""
        response = await client.get(
            "/api/v1/dashboard/yearly-stats?year=2020",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()

        assert data["year"] == 2020
        assert data["fatture_attive"]["count"] == 0
        assert data["fatture_attive"]["totale"] == 0.0
        assert data["fatture_passive"]["count"] == 0
        assert data["fatture_passive"]["totale"] == 0.0
        assert data["margine_lordo"] == 0.0
        assert data["top_clienti"] == []
        assert data["top_fornitori"] == []
        assert len(data["fatture_per_mese"]) == 12
        for m in data["fatture_per_mese"]:
            assert m["attive_count"] == 0
            assert m["passive_count"] == 0
