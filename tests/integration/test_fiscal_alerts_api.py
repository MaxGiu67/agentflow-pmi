"""
Test suite for US-20: Alert scadenze fiscali personalizzate
Tests for 4 Acceptance Criteria (AC-20.1 through AC-20.4)
"""

from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import Tenant, User, Invoice
from api.modules.deadlines.service import DeadlineService
from tests.conftest import get_auth_token, create_invoice


# ============================================================
# AC-20.1 — Alert IVA con importo stimato (10gg prima)
# ============================================================


class TestAC201AlertIVA:
    """AC-20.1: Alert IVA with estimated amount 10 days before deadline."""

    async def test_ac_201_alert_iva_con_importo(
        self, db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-20.1: DATO tenant ordinario con fatture registrate,
        QUANDO scadenza IVA entro 10gg, ALLORA alert con importo stimato."""
        # Create invoices for Q1
        for i in range(3):
            inv = create_invoice(
                tenant_id=tenant.id,
                numero=f"FT-IVA-{i}",
                importo=1000.0 + i * 500,
                data=date(2026, 2, 15),
                status="parsed",
            )
            db_session.add(inv)
        await db_session.flush()

        service = DeadlineService(db_session)
        # Set reference date to 10 days before Q1 IVA deadline (May 16)
        result = await service.get_alerts(
            tenant_id=tenant.id,
            regime="ordinario",
            year=2026,
            reference_date=date(2026, 5, 6),
            advance_days=10,
        )

        assert result["regime"] == "ordinario"
        alerts = result["alerts"]
        # Should have at least one IVA alert
        iva_alerts = [a for a in alerts if a["category"] == "iva"]
        assert len(iva_alerts) > 0

        for alert in iva_alerts:
            assert alert["importo_stimato"] is not None
            assert alert["importo_stimato"] >= 0
            assert alert["importo_source"] == "stima"

    async def test_ac_201_alert_via_api(
        self, client: AsyncClient, auth_headers: dict,
    ):
        """AC-20.1: DATO utente autenticato,
        QUANDO richiede alerts via API, ALLORA riceve risposta valida."""
        resp = await client.get(
            "/api/v1/deadlines/alerts?year=2026",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "alerts" in data
        assert "regime" in data
        assert data["year"] == 2026

    async def test_ac_201_alert_days_remaining(
        self, db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-20.1: DATO alert IVA,
        ALLORA mostra days_remaining corretto."""
        service = DeadlineService(db_session)
        ref = date(2026, 5, 10)
        result = await service.get_alerts(
            tenant_id=tenant.id,
            regime="ordinario",
            year=2026,
            reference_date=ref,
            advance_days=10,
        )

        for alert in result["alerts"]:
            scad = date.fromisoformat(alert["scadenza_date"])
            expected_days = (scad - ref).days
            assert alert["days_remaining"] == expected_days


# ============================================================
# AC-20.2 — Alert con importo da FiscoAPI
# ============================================================


class TestAC202AlertFiscoAPI:
    """AC-20.2: Alert with amount sourced from FiscoAPI."""

    async def test_ac_202_importo_da_fiscoapi(
        self, db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-20.2: DATO FiscoAPI disponibile,
        QUANDO genera alert, ALLORA importo_source = 'fiscoapi'."""
        service = DeadlineService(db_session)
        result = await service.get_alerts(
            tenant_id=tenant.id,
            regime="ordinario",
            year=2026,
            reference_date=date(2026, 5, 6),
            advance_days=10,
            fiscoapi_available=True,
        )

        for alert in result["alerts"]:
            assert alert["importo_source"] == "fiscoapi"

    async def test_ac_202_senza_fiscoapi_usa_stima(
        self, db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-20.2: DATO FiscoAPI non disponibile,
        QUANDO genera alert, ALLORA importo_source = 'stima'."""
        service = DeadlineService(db_session)
        result = await service.get_alerts(
            tenant_id=tenant.id,
            regime="ordinario",
            year=2026,
            reference_date=date(2026, 5, 6),
            advance_days=10,
            fiscoapi_available=False,
        )

        for alert in result["alerts"]:
            assert alert["importo_source"] == "stima"


# ============================================================
# AC-20.3 — Stima imprecisa -> "stima provvisoria, N fatture in attesa"
# ============================================================


class TestAC203StimaPrecisa:
    """AC-20.3: Inaccurate estimate shows provisional note."""

    async def test_ac_203_stima_provvisoria_con_fatture_pending(
        self, db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-20.3: DATO fatture in stato pending,
        QUANDO genera alert, ALLORA nota 'stima provvisoria, N fatture in attesa'."""
        # Create some parsed and some pending invoices
        inv1 = create_invoice(
            tenant_id=tenant.id, numero="FT-PARSED-1",
            importo=1000.0, data=date(2026, 2, 10), status="parsed",
        )
        inv2 = create_invoice(
            tenant_id=tenant.id, numero="FT-PEND-1",
            importo=2000.0, data=date(2026, 3, 5), status="pending",
        )
        inv3 = create_invoice(
            tenant_id=tenant.id, numero="FT-PEND-2",
            importo=1500.0, data=date(2026, 1, 20), status="pending",
        )
        db_session.add_all([inv1, inv2, inv3])
        await db_session.flush()

        service = DeadlineService(db_session)
        result = await service.get_alerts(
            tenant_id=tenant.id,
            regime="ordinario",
            year=2026,
            reference_date=date(2026, 5, 6),
            advance_days=10,
        )

        # Find IVA alert
        iva_alerts = [a for a in result["alerts"] if a["category"] == "iva"]
        assert len(iva_alerts) > 0

        # At least one should be provisional due to pending invoices
        provisional = [a for a in iva_alerts if a["is_provisional"]]
        assert len(provisional) > 0

        for p in provisional:
            assert p["provisional_note"] is not None
            assert "fatture in attesa" in p["provisional_note"]
            assert "Stima provvisoria" in p["provisional_note"]

    async def test_ac_203_tutte_registrate_non_provvisoria(
        self, db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-20.3: DATO tutte le fatture registrate,
        QUANDO genera alert, ALLORA is_provisional = False."""
        inv = create_invoice(
            tenant_id=tenant.id, numero="FT-REG-1",
            importo=3000.0, data=date(2026, 2, 15), status="registered",
        )
        db_session.add(inv)
        await db_session.flush()

        service = DeadlineService(db_session)
        result = await service.get_alerts(
            tenant_id=tenant.id,
            regime="ordinario",
            year=2026,
            reference_date=date(2026, 5, 6),
            advance_days=10,
        )

        iva_alerts = [a for a in result["alerts"] if a["category"] == "iva"]
        for a in iva_alerts:
            assert a["is_provisional"] is False


# ============================================================
# AC-20.4 — Cambio regime in corso d'anno -> ricalcolo scadenze
# ============================================================


class TestAC204CambioRegime:
    """AC-20.4: Regime change mid-year recalculates deadlines."""

    async def test_ac_204_cambio_regime_ricalcolo(
        self, db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-20.4: DATO cambio regime da forfettario a ordinario il 1 luglio,
        QUANDO genera alert, ALLORA scadenze ricalcolate."""
        service = DeadlineService(db_session)
        result = await service.get_alerts(
            tenant_id=tenant.id,
            regime="forfettario",
            year=2026,
            reference_date=date(2026, 4, 1),
            advance_days=30,
            regime_change_date=date(2026, 7, 1),
            new_regime="ordinario",
        )

        # Response should indicate regime transition
        assert "->" in result["regime"]
        assert "forfettario" in result["regime"]
        assert "ordinario" in result["regime"]

        # Alerts before July should use forfettario rules
        for alert in result["alerts"]:
            scad = date.fromisoformat(alert["scadenza_date"])
            if scad < date(2026, 7, 1):
                assert alert["regime"] == "forfettario"

    async def test_ac_204_cambio_regime_scadenze_dopo(
        self, db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-20.4: DATO cambio regime,
        ALLORA scadenze dopo la data cambio usano il nuovo regime."""
        service = DeadlineService(db_session)
        result = await service.get_alerts(
            tenant_id=tenant.id,
            regime="forfettario",
            year=2026,
            reference_date=date(2026, 8, 1),
            advance_days=60,
            regime_change_date=date(2026, 7, 1),
            new_regime="ordinario",
        )

        # Alerts after July should use ordinario rules
        for alert in result["alerts"]:
            scad = date.fromisoformat(alert["scadenza_date"])
            if scad >= date(2026, 7, 1):
                assert alert["regime"] == "ordinario"

    async def test_ac_204_senza_cambio_regime_normale(
        self, db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-20.4: DATO nessun cambio regime,
        ALLORA alert normali con regime invariato."""
        service = DeadlineService(db_session)
        result = await service.get_alerts(
            tenant_id=tenant.id,
            regime="ordinario",
            year=2026,
            reference_date=date(2026, 5, 6),
            advance_days=10,
        )

        assert result["regime"] == "ordinario"
        for alert in result["alerts"]:
            assert alert["regime"] == "ordinario"
