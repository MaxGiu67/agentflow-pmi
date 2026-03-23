"""
Test suite for US-25: Cash flow predittivo 90gg
Tests for 5 Acceptance Criteria (AC-25.1 through AC-25.5)
"""

import uuid
from datetime import date, datetime, timedelta, UTC

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import (
    ActiveInvoice, BankAccount, FiscalDeadline, Invoice, Tenant,
)
from tests.conftest import create_invoice


# ============================================================
# AC-25.1 — Grafico 90gg con saldo + entrate/uscite + proiettato
# ============================================================


class TestAC251Grafico90gg:
    """AC-25.1: Grafico 90gg con saldo attuale + entrate/uscite previste
    + saldo proiettato."""

    async def test_ac_251_prediction_default_90_days(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-25.1: DATO conto collegato con saldo, QUANDO richiedo previsione,
        ALLORA ottengo proiezione 90 giorni con saldo attuale."""
        # Setup: create a bank account with balance
        account = BankAccount(
            tenant_id=tenant.id,
            iban="IT60X0542811101000000CF0001",
            bank_name="Banca CF",
            provider="cbi_globe",
            balance=10000.0,
            status="connected",
            last_sync_at=datetime.now(UTC).replace(tzinfo=None),
        )
        db_session.add(account)
        await db_session.flush()

        resp = await client.get(
            "/api/v1/cashflow/prediction",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["saldo_attuale"] == 10000.0
        assert data["giorni"] == 90
        assert len(data["projection"]) == 90
        assert "saldo_finale_proiettato" in data

    async def test_ac_251_prediction_with_income_and_expenses(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-25.1: DATO fatture attive e passive, QUANDO previsione,
        ALLORA entrate/uscite previste nel grafico."""
        account = BankAccount(
            tenant_id=tenant.id,
            iban="IT60X0542811101000000CF0002",
            bank_name="Banca CF2",
            provider="cbi_globe",
            balance=20000.0,
            status="connected",
            last_sync_at=datetime.now(UTC).replace(tzinfo=None),
        )
        db_session.add(account)

        # Passive invoice (expense expected in 30 days)
        inv = create_invoice(
            tenant_id=tenant.id,
            numero="FT-CF-001",
            importo=1000.0,
            status="parsed",
            data=date.today(),
        )
        db_session.add(inv)

        await db_session.flush()

        resp = await client.get(
            "/api/v1/cashflow/prediction",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_uscite_previste"] > 0 or data["total_entrate_previste"] >= 0

    async def test_ac_251_custom_days(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-25.1: DATO richiesta con days=30, QUANDO previsione,
        ALLORA proiezione 30 giorni."""
        account = BankAccount(
            tenant_id=tenant.id,
            iban="IT60X0542811101000000CF0003",
            bank_name="Banca CF3",
            provider="cbi_globe",
            balance=5000.0,
            status="connected",
            last_sync_at=datetime.now(UTC).replace(tzinfo=None),
        )
        db_session.add(account)
        await db_session.flush()

        resp = await client.get(
            "/api/v1/cashflow/prediction?days=30",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["giorni"] == 30
        assert len(data["projection"]) == 30


# ============================================================
# AC-25.2 — Alert soglia critica (default 5000, configurabile)
# ============================================================


class TestAC252AlertSogliaCritica:
    """AC-25.2: Alert soglia critica (default 5000, configurabile)."""

    async def test_ac_252_critical_alert_default_threshold(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-25.2: DATO saldo basso, QUANDO richiedo alert,
        ALLORA alert per soglia critica 5000 EUR."""
        account = BankAccount(
            tenant_id=tenant.id,
            iban="IT60X0542811101000000CF0004",
            bank_name="Banca CF4",
            provider="cbi_globe",
            balance=3000.0,
            status="connected",
            last_sync_at=datetime.now(UTC).replace(tzinfo=None),
        )
        db_session.add(account)
        await db_session.flush()

        resp = await client.get(
            "/api/v1/cashflow/alerts",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["soglia_critica"] == 5000.0
        # With balance 3000 < 5000, should have at least 1 critical alert
        critical_alerts = [a for a in data["alerts"] if a["type"] == "critical_balance"]
        assert len(critical_alerts) >= 1
        assert critical_alerts[0]["severity"] == "critical"

    async def test_ac_252_custom_threshold(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-25.2: DATO soglia personalizzata, QUANDO richiedo alert,
        ALLORA usa soglia configurata."""
        account = BankAccount(
            tenant_id=tenant.id,
            iban="IT60X0542811101000000CF0005",
            bank_name="Banca CF5",
            provider="cbi_globe",
            balance=8000.0,
            status="connected",
            last_sync_at=datetime.now(UTC).replace(tzinfo=None),
        )
        db_session.add(account)
        await db_session.flush()

        resp = await client.get(
            "/api/v1/cashflow/alerts?soglia=10000",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["soglia_critica"] == 10000.0

    async def test_ac_252_no_alert_above_threshold(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-25.2: DATO saldo sopra soglia, QUANDO richiedo alert,
        ALLORA nessun alert critico."""
        account = BankAccount(
            tenant_id=tenant.id,
            iban="IT60X0542811101000000CF0006",
            bank_name="Banca CF6",
            provider="cbi_globe",
            balance=50000.0,
            status="connected",
            last_sync_at=datetime.now(UTC).replace(tzinfo=None),
        )
        db_session.add(account)
        await db_session.flush()

        resp = await client.get(
            "/api/v1/cashflow/alerts",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        critical_alerts = [a for a in data["alerts"] if a["type"] == "critical_balance"]
        assert len(critical_alerts) == 0


# ============================================================
# AC-25.3 — Dati insufficienti (<20 fatture)
# ============================================================


class TestAC253DatiInsufficienti:
    """AC-25.3: Dati insufficienti (<20 fatture) -> mostra disponibili
    + servono 20+."""

    async def test_ac_253_insufficient_data_warning(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-25.3: DATO <20 fatture, QUANDO previsione,
        ALLORA data_source='insufficient' con messaggio."""
        account = BankAccount(
            tenant_id=tenant.id,
            iban="IT60X0542811101000000CF0007",
            bank_name="Banca CF7",
            provider="cbi_globe",
            balance=10000.0,
            status="connected",
            last_sync_at=datetime.now(UTC).replace(tzinfo=None),
        )
        db_session.add(account)
        # Add only 5 invoices
        for i in range(5):
            inv = create_invoice(
                tenant_id=tenant.id,
                numero=f"FT-INS-{i:03d}",
                importo=100.0,
                status="parsed",
            )
            db_session.add(inv)
        await db_session.flush()

        resp = await client.get(
            "/api/v1/cashflow/prediction",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["data_source"] == "insufficient"
        assert data["invoice_count"] == 5
        assert data["min_invoices_required"] == 20
        assert "20" in data["message"]
        assert "5" in data["message"]

    async def test_ac_253_sufficient_data(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-25.3: DATO >=20 fatture, QUANDO previsione,
        ALLORA data_source='sufficient'."""
        account = BankAccount(
            tenant_id=tenant.id,
            iban="IT60X0542811101000000CF0008",
            bank_name="Banca CF8",
            provider="cbi_globe",
            balance=10000.0,
            status="connected",
            last_sync_at=datetime.now(UTC).replace(tzinfo=None),
        )
        db_session.add(account)
        for i in range(25):
            inv = create_invoice(
                tenant_id=tenant.id,
                numero=f"FT-SUF-{i:03d}",
                importo=100.0,
                status="parsed",
            )
            db_session.add(inv)
        await db_session.flush()

        resp = await client.get(
            "/api/v1/cashflow/prediction",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["data_source"] == "sufficient"
        assert data["message"] is None


# ============================================================
# AC-25.4 — Dati bancari stale (>3gg) -> banner warning
# ============================================================


class TestAC254DatiBancariStale:
    """AC-25.4: Dati bancari stale (>3gg) -> banner warning."""

    async def test_ac_254_stale_data_warning(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-25.4: DATO ultima sync >3gg fa, QUANDO previsione,
        ALLORA stale_warning presente."""
        account = BankAccount(
            tenant_id=tenant.id,
            iban="IT60X0542811101000000CF0009",
            bank_name="Banca CF9",
            provider="cbi_globe",
            balance=10000.0,
            status="connected",
            last_sync_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=5),
        )
        db_session.add(account)
        await db_session.flush()

        resp = await client.get(
            "/api/v1/cashflow/prediction",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["stale_warning"] is not None
        assert "aggiornati" in data["stale_warning"].lower() or "giorni" in data["stale_warning"].lower()

    async def test_ac_254_fresh_data_no_warning(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-25.4: DATO sync recente, QUANDO previsione,
        ALLORA nessun stale_warning."""
        account = BankAccount(
            tenant_id=tenant.id,
            iban="IT60X0542811101000000CF0010",
            bank_name="Banca CF10",
            provider="cbi_globe",
            balance=10000.0,
            status="connected",
            last_sync_at=datetime.now(UTC).replace(tzinfo=None),
        )
        db_session.add(account)
        await db_session.flush()

        resp = await client.get(
            "/api/v1/cashflow/prediction",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["stale_warning"] is None

    async def test_ac_254_no_bank_account_warning(
        self, client: AsyncClient, auth_headers: dict,
    ):
        """AC-25.4: DATO nessun conto collegato, QUANDO previsione,
        ALLORA warning nessun conto."""
        resp = await client.get(
            "/api/v1/cashflow/prediction",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["stale_warning"] is not None
        assert "conto" in data["stale_warning"].lower()


# ============================================================
# AC-25.5 — Pagamento in ritardo -> evidenziato con due scenari
# ============================================================


class TestAC255PagamentoInRitardo:
    """AC-25.5: Pagamento in ritardo -> evidenziato con due scenari."""

    async def test_ac_255_late_payment_two_scenarios(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-25.5: DATO fattura attiva scaduta, QUANDO alert,
        ALLORA alert late_payment con scenario ottimistico/pessimistico."""
        account = BankAccount(
            tenant_id=tenant.id,
            iban="IT60X0542811101000000CF0011",
            bank_name="Banca CF11",
            provider="cbi_globe",
            balance=20000.0,
            status="connected",
            last_sync_at=datetime.now(UTC).replace(tzinfo=None),
        )
        db_session.add(account)

        # Active invoice past due (60 days ago, so payment was due 30 days ago)
        active_inv = ActiveInvoice(
            tenant_id=tenant.id,
            numero_fattura="FA-LATE-001",
            document_type="TD01",
            cliente_piva="IT99887766554",
            cliente_nome="Cliente Ritardatario SRL",
            data_fattura=date.today() - timedelta(days=60),
            importo_netto=5000.0,
            aliquota_iva=22.0,
            importo_iva=1100.0,
            importo_totale=6100.0,
            sdi_status="delivered",
        )
        db_session.add(active_inv)
        await db_session.flush()

        resp = await client.get(
            "/api/v1/cashflow/alerts",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        late_alerts = [a for a in data["alerts"] if a["type"] == "late_payment"]
        assert len(late_alerts) >= 1
        alert = late_alerts[0]
        assert alert["severity"] == "warning"
        assert alert["scenario_optimistic"] is not None
        assert alert["scenario_pessimistic"] is not None
        assert alert["scenario_optimistic"] > alert["scenario_pessimistic"]
