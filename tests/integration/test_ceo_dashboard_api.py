"""
Test suite for US-39: Dashboard CEO — cruscotto direzionale
Tests for 5 Acceptance Criteria (AC-39.1 through AC-39.5)
Updated for US-70: all amounts use importo_netto (not importo_totale)
"""

import uuid
from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import (
    FiscalDeadline,
    Invoice,
    Tenant,
)


def _make_attiva(tenant_id, numero, cliente_piva, cliente_nome, data, netto, iva=None, totale=None, piva_emittente="IT99999999999"):
    """Helper to create an active Invoice (type=attiva) for CEO tests."""
    iva = iva or round(netto * 0.22, 2)
    totale = totale or round(netto + iva, 2)
    return Invoice(
        tenant_id=tenant_id,
        type="attiva",
        document_type="TD01",
        source="sdi",
        numero_fattura=numero,
        emittente_piva=piva_emittente,
        emittente_nome="Mia Azienda SRL",
        data_fattura=data,
        importo_netto=netto,
        importo_iva=iva,
        importo_totale=totale,
        processing_status="registered",
        structured_data={
            "destinatario_nome": cliente_nome,
            "destinatario_piva": cliente_piva,
        },
    )


# ============================================================
# AC-39.1 — KPI principali
# ============================================================


class TestAC391KPIPrincipali:
    """AC-39.1: KPI (fatturato, EBITDA, cash flow, scadenze, top 5)."""

    async def test_ac_391_dashboard_kpi_with_data(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-39.1: DATO fatture attive e passive,
        QUANDO GET /ceo/dashboard,
        ALLORA KPI con fatturato netto, EBITDA, top clienti/fornitori."""
        today = date.today()

        # Active invoices (revenue) — netto: 1000, 2000, 3000
        for i in range(3):
            db_session.add(_make_attiva(
                tenant.id, f"FA-2026-{i:03d}",
                f"IT{i:011d}", f"Cliente {i}",
                date(today.year, today.month, 1 + i),
                netto=1000.0 * (i + 1),
            ))

        # Passive invoices (costs) — netto: 500, 1000
        for i in range(2):
            db_session.add(Invoice(
                tenant_id=tenant.id, type="passiva", document_type="TD01",
                source="upload", numero_fattura=f"FP-2026-{i:03d}",
                emittente_piva=f"IT{i+10:011d}", emittente_nome=f"Fornitore {i}",
                data_fattura=date(today.year, today.month, 5 + i),
                importo_netto=500.0 * (i + 1),
                importo_iva=110.0 * (i + 1),
                importo_totale=610.0 * (i + 1),
                processing_status="registered",
            ))
        await db_session.flush()

        resp = await client.get(
            f"/api/v1/ceo/dashboard?year={today.year}&month={today.month}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        kpi = resp.json()["kpi"]

        # Fatturato mese (netto): 1000 + 2000 + 3000 = 6000
        assert kpi["fatturato_mese"] == 6000.0
        assert kpi["fatturato_ytd"] >= 6000.0
        assert kpi["ebitda_amount"] > 0
        assert "top_clienti" in kpi
        assert "top_fornitori" in kpi

    async def test_ac_391_scadenze_prossime(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-39.1: DATO scadenze fiscali pending,
        QUANDO dashboard, ALLORA conteggio scadenze."""
        today = date.today()
        for i in range(3):
            db_session.add(FiscalDeadline(
                tenant_id=tenant.id, code="1040",
                description=f"Scadenza {i}",
                amount=100.0 * (i + 1),
                due_date=today + timedelta(days=10 + i),
                status="pending",
            ))
        await db_session.flush()

        resp = await client.get(
            "/api/v1/ceo/dashboard",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["kpi"]["scadenze_prossime"] >= 3

    async def test_ac_391_top_5_clienti_sorted(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-39.1: DATO molti clienti, ALLORA top 5 ordinati per importo netto."""
        today = date.today()
        for i in range(7):
            db_session.add(_make_attiva(
                tenant.id, f"FA-TOP-{i:03d}",
                f"IT{i+20:011d}", f"BigClient {i}",
                date(today.year, 1, 10),
                netto=1000.0 * (i + 1),
            ))
        await db_session.flush()

        resp = await client.get(
            f"/api/v1/ceo/dashboard?year={today.year}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        top = resp.json()["kpi"]["top_clienti"]
        assert len(top) <= 5
        # Should be sorted descending
        totals = [c["total"] for c in top]
        assert totals == sorted(totals, reverse=True)


# ============================================================
# AC-39.2 — Confronto anno precedente
# ============================================================


class TestAC392ConfrontoYoY:
    """AC-39.2: Confronto anno precedente con variazione %."""

    async def test_ac_392_yoy_comparison_up(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-39.2: DATO fatturato netto 2025=8196, 2026=9836,
        QUANDO /ceo/dashboard/yoy, ALLORA variazione +20% direction=up."""
        # Create invoices with netto amounts that give exactly +20%
        db_session.add(_make_attiva(
            tenant.id, "FA-YOY-2025", "IT00000000001", "ClienteYoY",
            date(2025, 3, 15), netto=10000.0,
        ))
        db_session.add(_make_attiva(
            tenant.id, "FA-YOY-2026", "IT00000000001", "ClienteYoY",
            date(2026, 3, 15), netto=12000.0,
        ))
        await db_session.flush()

        resp = await client.get(
            "/api/v1/ceo/dashboard/yoy?year=2026",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["year_current"] == 2026
        assert data["year_previous"] == 2025

        fatturato_comp = [c for c in data["comparisons"] if c["metric"] == "Fatturato"]
        assert len(fatturato_comp) == 1
        assert fatturato_comp[0]["direction"] == "up"
        assert fatturato_comp[0]["variation_percent"] == 20.0

    async def test_ac_392_yoy_comparison_down(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-39.2: DATO fatturato in calo, ALLORA direction=down."""
        db_session.add(_make_attiva(
            tenant.id, "FA-YOYD-2025", "IT00000000002", "ClienteDown",
            date(2025, 2, 10), netto=20000.0,
        ))
        db_session.add(_make_attiva(
            tenant.id, "FA-YOYD-2026", "IT00000000002", "ClienteDown",
            date(2026, 2, 10), netto=15000.0,
        ))
        await db_session.flush()

        resp = await client.get(
            "/api/v1/ceo/dashboard/yoy?year=2026",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        fatturato_comp = [
            c for c in resp.json()["comparisons"] if c["metric"] == "Fatturato"
        ]
        assert fatturato_comp[0]["direction"] == "down"
        assert fatturato_comp[0]["variation_percent"] < 0


# ============================================================
# AC-39.3 — DSO e DPO con trend trimestrale
# ============================================================


class TestAC393DSODPO:
    """AC-39.3: DSO e DPO con trend trimestrale."""

    async def test_ac_393_dso_dpo_returned(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-39.3: DATO dati fatturazione,
        QUANDO dashboard, ALLORA DSO e DPO presenti con trend."""
        today = date.today()
        # Active invoice (attiva) for DSO calc
        db_session.add(_make_attiva(
            tenant.id, "FA-DSO-001", "IT00000000010", "ClienteDSO",
            date(today.year, 1, 15), netto=5000.0,
        ))
        # Passive invoice for DPO calc
        db_session.add(Invoice(
            tenant_id=tenant.id, type="passiva", document_type="TD01",
            source="upload", numero_fattura="FP-DPO-001",
            emittente_piva="IT00000000011", emittente_nome="FornitoreDPO",
            data_fattura=date(today.year, 1, 20),
            importo_netto=3000.0, importo_iva=660.0, importo_totale=3660.0,
            processing_status="pending",
        ))
        await db_session.flush()

        resp = await client.get(
            f"/api/v1/ceo/dashboard?year={today.year}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        dso_dpo = resp.json()["dso_dpo"]

        assert "dso_current" in dso_dpo
        assert "dpo_current" in dso_dpo
        assert "dso_trend" in dso_dpo
        assert "dpo_trend" in dso_dpo
        assert len(dso_dpo["dso_trend"]) == 4  # 4 quarters
        assert len(dso_dpo["dpo_trend"]) == 4


# ============================================================
# AC-39.4 — Dati insufficienti
# ============================================================


class TestAC394DatiInsufficienti:
    """AC-39.4: Dati insufficienti (<1 mese) → nota."""

    async def test_ac_394_no_data_note(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-39.4: DATO nessun dato, QUANDO dashboard,
        ALLORA nota 'completo dopo 3 mesi'."""
        resp = await client.get(
            "/api/v1/ceo/dashboard?year=2026",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        kpi = resp.json()["kpi"]
        assert kpi["data_note"] is not None
        assert "3 mesi" in kpi["data_note"]

    async def test_ac_394_partial_data_note(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-39.4: DATO 1 mese di dati, ALLORA nota 'parziali'."""
        db_session.add(_make_attiva(
            tenant.id, "FA-PART-001", "IT00000000099", "ClienteParziale",
            date(2026, 1, 15), netto=1000.0,
        ))
        await db_session.flush()

        resp = await client.get(
            "/api/v1/ceo/dashboard?year=2026",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        kpi = resp.json()["kpi"]
        assert kpi["data_note"] is not None
        assert "parzial" in kpi["data_note"].lower() or "3 mesi" in kpi["data_note"]


# ============================================================
# AC-39.5 — Concentrazione clienti
# ============================================================


class TestAC395ConcentrazioneClienti:
    """AC-39.5: Concentrazione top 3 clienti > 60% → alert."""

    async def test_ac_395_concentration_alert(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-39.5: DATO 1 grande cliente con >60% fatturato,
        QUANDO /ceo/alerts, ALLORA alert concentrazione."""
        today = date.today()
        # Big client: ~80% of revenue (netto 8000)
        db_session.add(_make_attiva(
            tenant.id, "FA-CONC-001", "IT00000000050", "MegaClient",
            date(today.year, 2, 10), netto=8000.0,
        ))
        # Small clients (netto 100 each * 5 = 500 total)
        for i in range(5):
            db_session.add(_make_attiva(
                tenant.id, f"FA-CONC-S{i}", f"IT{i+60:011d}", f"SmallClient {i}",
                date(today.year, 2, 15 + i), netto=100.0,
            ))
        await db_session.flush()

        resp = await client.get(
            f"/api/v1/ceo/alerts?year={today.year}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        alerts = resp.json()["alerts"]
        concentration = [a for a in alerts if a["alert_type"] == "concentration"]
        assert len(concentration) == 1
        assert concentration[0]["top3_percent"] > 60

    async def test_ac_395_no_concentration_alert_when_balanced(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-39.5: DATO clienti bilanciati, ALLORA nessun alert."""
        today = date.today()
        # 10 equal clients (netto 1000 each)
        for i in range(10):
            db_session.add(_make_attiva(
                tenant.id, f"FA-BAL-{i:03d}", f"IT{i+70:011d}", f"Client {i}",
                date(today.year, 3, 1 + i), netto=1000.0,
            ))
        await db_session.flush()

        resp = await client.get(
            f"/api/v1/ceo/alerts?year={today.year}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        alerts = resp.json()["alerts"]
        concentration = [a for a in alerts if a["alert_type"] == "concentration"]
        # Top 3 = 3000/10000 = 30% < 60% → no alert
        assert len(concentration) == 0
