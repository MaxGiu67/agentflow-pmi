"""
Test suite for US-39: Dashboard CEO — cruscotto direzionale
Tests for 5 Acceptance Criteria (AC-39.1 through AC-39.5)
"""

import uuid
from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import (
    ActiveInvoice,
    FiscalDeadline,
    Invoice,
    Tenant,
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
        ALLORA KPI con fatturato, EBITDA, top clienti/fornitori."""
        today = date.today()

        # Active invoices (revenue)
        for i in range(3):
            inv = ActiveInvoice(
                tenant_id=tenant.id,
                numero_fattura=f"FA-2026-{i:03d}",
                document_type="TD01",
                cliente_piva=f"IT{i:011d}",
                cliente_nome=f"Cliente {i}",
                data_fattura=date(today.year, today.month, 1 + i),
                importo_netto=1000.0 * (i + 1),
                aliquota_iva=22.0,
                importo_iva=220.0 * (i + 1),
                importo_totale=1220.0 * (i + 1),
                sdi_status="delivered",
            )
            db_session.add(inv)

        # Passive invoices (costs)
        for i in range(2):
            inv = Invoice(
                tenant_id=tenant.id,
                type="passiva",
                document_type="TD01",
                source="upload",
                numero_fattura=f"FP-2026-{i:03d}",
                emittente_piva=f"IT{i+10:011d}",
                emittente_nome=f"Fornitore {i}",
                data_fattura=date(today.year, today.month, 5 + i),
                importo_netto=500.0 * (i + 1),
                importo_iva=110.0 * (i + 1),
                importo_totale=610.0 * (i + 1),
                processing_status="registered",
            )
            db_session.add(inv)

        await db_session.flush()

        resp = await client.get(
            f"/api/v1/ceo/dashboard?year={today.year}&month={today.month}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()

        kpi = data["kpi"]
        # Fatturato mese: 1220 + 2440 + 3660 = 7320
        assert kpi["fatturato_mese"] == 7320.0
        assert kpi["fatturato_ytd"] >= 7320.0
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
            dl = FiscalDeadline(
                tenant_id=tenant.id,
                code="1040",
                description=f"Scadenza {i}",
                amount=100.0 * (i + 1),
                due_date=today + timedelta(days=10 + i),
                status="pending",
            )
            db_session.add(dl)
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
        """AC-39.1: DATO molti clienti, ALLORA top 5 ordinati per importo."""
        today = date.today()
        for i in range(7):
            inv = ActiveInvoice(
                tenant_id=tenant.id,
                numero_fattura=f"FA-TOP-{i:03d}",
                document_type="TD01",
                cliente_piva=f"IT{i+20:011d}",
                cliente_nome=f"BigClient {i}",
                data_fattura=date(today.year, 1, 10),
                importo_netto=1000.0 * (i + 1),
                aliquota_iva=22.0,
                importo_iva=220.0 * (i + 1),
                importo_totale=1220.0 * (i + 1),
                sdi_status="delivered",
            )
            db_session.add(inv)
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
        """AC-39.2: DATO fatturato 2025=10000, 2026=12000,
        QUANDO /ceo/dashboard/yoy, ALLORA variazione +20% direction=up."""
        # Previous year invoices
        for yr, amount in [(2025, 10000.0), (2026, 12000.0)]:
            inv = ActiveInvoice(
                tenant_id=tenant.id,
                numero_fattura=f"FA-YOY-{yr}",
                document_type="TD01",
                cliente_piva="IT00000000001",
                cliente_nome="ClienteYoY",
                data_fattura=date(yr, 3, 15),
                importo_netto=amount / 1.22,
                aliquota_iva=22.0,
                importo_iva=amount - amount / 1.22,
                importo_totale=amount,
                sdi_status="delivered",
            )
            db_session.add(inv)
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
        for yr, amount in [(2025, 20000.0), (2026, 15000.0)]:
            inv = ActiveInvoice(
                tenant_id=tenant.id,
                numero_fattura=f"FA-YOYD-{yr}",
                document_type="TD01",
                cliente_piva="IT00000000002",
                cliente_nome="ClienteYoYDown",
                data_fattura=date(yr, 2, 10),
                importo_netto=amount / 1.22,
                aliquota_iva=22.0,
                importo_iva=amount - amount / 1.22,
                importo_totale=amount,
                sdi_status="delivered",
            )
            db_session.add(inv)
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
        # Active invoice for DSO calc
        inv = ActiveInvoice(
            tenant_id=tenant.id,
            numero_fattura="FA-DSO-001",
            document_type="TD01",
            cliente_piva="IT00000000010",
            cliente_nome="ClienteDSO",
            data_fattura=date(today.year, 1, 15),
            importo_netto=5000.0,
            aliquota_iva=22.0,
            importo_iva=1100.0,
            importo_totale=6100.0,
            sdi_status="sent",  # unpaid
        )
        db_session.add(inv)

        # Passive invoice for DPO calc
        pinv = Invoice(
            tenant_id=tenant.id,
            type="passiva",
            document_type="TD01",
            source="upload",
            numero_fattura="FP-DPO-001",
            emittente_piva="IT00000000011",
            emittente_nome="FornitoreDPO",
            data_fattura=date(today.year, 1, 20),
            importo_netto=3000.0,
            importo_iva=660.0,
            importo_totale=3660.0,
            processing_status="pending",  # unpaid
        )
        db_session.add(pinv)
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
        inv = ActiveInvoice(
            tenant_id=tenant.id,
            numero_fattura="FA-PART-001",
            document_type="TD01",
            cliente_piva="IT00000000099",
            cliente_nome="ClienteParziale",
            data_fattura=date(2026, 1, 15),
            importo_netto=1000.0,
            aliquota_iva=22.0,
            importo_iva=220.0,
            importo_totale=1220.0,
            sdi_status="delivered",
        )
        db_session.add(inv)
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
        """AC-39.5: DATO 3 clienti con >60% fatturato,
        QUANDO /ceo/alerts, ALLORA alert concentrazione."""
        today = date.today()
        # Big client: 80% of revenue
        big = ActiveInvoice(
            tenant_id=tenant.id,
            numero_fattura="FA-CONC-001",
            document_type="TD01",
            cliente_piva="IT00000000050",
            cliente_nome="MegaClient",
            data_fattura=date(today.year, 2, 10),
            importo_netto=8000.0,
            aliquota_iva=22.0,
            importo_iva=1760.0,
            importo_totale=9760.0,
            sdi_status="delivered",
        )
        db_session.add(big)

        # Small clients
        for i in range(5):
            inv = ActiveInvoice(
                tenant_id=tenant.id,
                numero_fattura=f"FA-CONC-S{i}",
                document_type="TD01",
                cliente_piva=f"IT{i+60:011d}",
                cliente_nome=f"SmallClient {i}",
                data_fattura=date(today.year, 2, 15 + i),
                importo_netto=100.0,
                aliquota_iva=22.0,
                importo_iva=22.0,
                importo_totale=122.0,
                sdi_status="delivered",
            )
            db_session.add(inv)
        await db_session.flush()

        resp = await client.get(
            f"/api/v1/ceo/alerts?year={today.year}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        alerts = resp.json()["alerts"]
        assert len(alerts) >= 1

        conc_alert = alerts[0]
        assert conc_alert["alert_type"] == "concentration"
        assert conc_alert["top3_percent"] > 60
        assert "60%" in conc_alert["message"]

    async def test_ac_395_no_concentration_alert_when_balanced(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-39.5: DATO clienti bilanciati (<60%),
        QUANDO /ceo/alerts, ALLORA nessun alert."""
        today = date.today()
        # 10 clients, each with equal share
        for i in range(10):
            inv = ActiveInvoice(
                tenant_id=tenant.id,
                numero_fattura=f"FA-BAL-{i:03d}",
                document_type="TD01",
                cliente_piva=f"IT{i+70:011d}",
                cliente_nome=f"BalancedClient {i}",
                data_fattura=date(today.year, 3, 1 + i),
                importo_netto=1000.0,
                aliquota_iva=22.0,
                importo_iva=220.0,
                importo_totale=1220.0,
                sdi_status="delivered",
            )
            db_session.add(inv)
        await db_session.flush()

        resp = await client.get(
            f"/api/v1/ceo/alerts?year={today.year}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        alerts = resp.json()["alerts"]
        # top 3 = 3/10 = 30% < 60%, no alert
        conc_alerts = [a for a in alerts if a["alert_type"] == "concentration"]
        assert len(conc_alerts) == 0
