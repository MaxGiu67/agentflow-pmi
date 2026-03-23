"""
Test suite for US-22: Liquidazione IVA automatica
Tests for 4 Acceptance Criteria (AC-22.1 through AC-22.4)
"""

import uuid
from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import ActiveInvoice, Invoice, Tenant, VatSettlement


# ============================================================
# AC-22.1 — Calcolo trimestrale: prospetto IVA
# ============================================================


class TestAC221CalcoloTrimestrale:
    """AC-22.1: Calcolo trimestrale -> prospetto IVA vendite/acquisti/debito/
    credito/saldo."""

    async def test_ac_221_compute_vat_settlement(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        tenant: Tenant,
    ):
        """AC-22.1: DATO fatture nel trimestre, QUANDO calcolo liquidazione,
        ALLORA prospetto con IVA vendite, acquisti, saldo."""
        # Create active invoice (vendita) in Q1 2026
        active = ActiveInvoice(
            tenant_id=tenant.id,
            numero_fattura="FTA-2026-0001",
            document_type="TD01",
            cliente_piva="IT11111111111",
            cliente_nome="Cliente A",
            data_fattura=date(2026, 2, 15),
            importo_netto=1000.0,
            aliquota_iva=22.0,
            importo_iva=220.0,
            importo_totale=1220.0,
            sdi_status="delivered",
        )
        db_session.add(active)

        # Create passive invoice (acquisto) in Q1 2026
        passive = Invoice(
            tenant_id=tenant.id,
            type="passiva",
            document_type="TD01",
            source="cassetto_fiscale",
            numero_fattura="FT-PASS-001",
            emittente_piva="IT22222222222",
            emittente_nome="Fornitore B",
            data_fattura=date(2026, 1, 20),
            importo_netto=500.0,
            importo_iva=110.0,
            importo_totale=610.0,
            processing_status="categorized",
        )
        db_session.add(passive)
        await db_session.flush()

        # Compute
        resp = await client.post(
            "/api/v1/fiscal/vat-settlement/compute",
            json={"year": 2026, "quarter": 1},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["year"] == 2026
        assert data["quarter"] == 1
        assert data["period"] == "Q1 2026"
        assert data["iva_vendite"] == 220.0
        assert data["iva_acquisti"] == 110.0
        assert data["saldo"] > 0  # 220 - 110 + interessi
        assert data["saldo_tipo"] == "debito"
        assert "iva_debito_totale" in data
        assert "iva_credito_totale" in data

    async def test_ac_221_get_existing_settlement(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        tenant: Tenant,
    ):
        """AC-22.1: DATO liquidazione gia calcolata, QUANDO richiedo per GET,
        ALLORA ottengo prospetto."""
        settlement = VatSettlement(
            tenant_id=tenant.id,
            year=2026,
            quarter=2,
            iva_vendite=500.0,
            iva_acquisti=200.0,
            saldo=303.0,
            status="computed",
        )
        db_session.add(settlement)
        await db_session.flush()

        resp = await client.get(
            "/api/v1/fiscal/vat-settlement?year=2026&quarter=2",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["iva_vendite"] == 500.0
        assert data["iva_acquisti"] == 200.0

    async def test_ac_221_settlement_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """AC-22.1: DATO liquidazione non calcolata, QUANDO richiedo per GET,
        ALLORA 404."""
        resp = await client.get(
            "/api/v1/fiscal/vat-settlement?year=2099&quarter=4",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_ac_221_credito_iva(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        tenant: Tenant,
    ):
        """AC-22.1: DATO acquisti > vendite, QUANDO calcolo,
        ALLORA saldo negativo (credito IVA)."""
        # Only passive invoice (no active) => credito
        passive = Invoice(
            tenant_id=tenant.id,
            type="passiva",
            document_type="TD01",
            source="cassetto_fiscale",
            numero_fattura="FT-CRED-001",
            emittente_piva="IT33333333333",
            emittente_nome="Fornitore Credito",
            data_fattura=date(2026, 7, 15),
            importo_netto=2000.0,
            importo_iva=440.0,
            importo_totale=2440.0,
            processing_status="registered",
        )
        db_session.add(passive)
        await db_session.flush()

        resp = await client.post(
            "/api/v1/fiscal/vat-settlement/compute",
            json={"year": 2026, "quarter": 3},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["saldo"] < 0
        assert data["saldo_tipo"] == "credito"


# ============================================================
# AC-22.2 — Reverse charge: IVA computata a debito e credito
# ============================================================


class TestAC222ReverseCharge:
    """AC-22.2: Reverse charge -> IVA computata a debito e credito."""

    async def test_ac_222_reverse_charge_computation(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        tenant: Tenant,
    ):
        """AC-22.2: DATO fattura reverse charge, QUANDO calcolo liquidazione,
        ALLORA IVA appare sia a debito che a credito."""
        # Create reverse charge invoice (TD17)
        rc_invoice = Invoice(
            tenant_id=tenant.id,
            type="passiva",
            document_type="TD17",
            source="sdi_realtime",
            numero_fattura="FT-RC-001",
            emittente_piva="IT44444444444",
            emittente_nome="Fornitore EU",
            data_fattura=date(2026, 5, 10),
            importo_netto=3000.0,
            importo_iva=660.0,
            importo_totale=3660.0,
            processing_status="categorized",
        )
        db_session.add(rc_invoice)
        await db_session.flush()

        resp = await client.post(
            "/api/v1/fiscal/vat-settlement/compute",
            json={"year": 2026, "quarter": 2},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        # Reverse charge appears in both debit and credit
        assert data["iva_reverse_charge_debito"] == 660.0
        assert data["iva_reverse_charge_credito"] == 660.0
        # They cancel each other out in the saldo
        assert data["iva_reverse_charge_debito"] == data["iva_reverse_charge_credito"]


# ============================================================
# AC-22.3 — Fatture non registrate: warning
# ============================================================


class TestAC223FattureNonRegistrate:
    """AC-22.3: Fatture non registrate -> warning 'N fatture non incluse'."""

    async def test_ac_223_unregistered_warning(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        tenant: Tenant,
    ):
        """AC-22.3: DATO fatture in stato pending nel periodo, QUANDO calcolo,
        ALLORA warning con conteggio fatture non incluse."""
        # Create pending invoices
        for i in range(3):
            inv = Invoice(
                tenant_id=tenant.id,
                type="passiva",
                document_type="TD01",
                source="upload",
                numero_fattura=f"FT-PENDING-{i}",
                emittente_piva=f"IT5555555555{i}",
                emittente_nome=f"Pending Fornitore {i}",
                data_fattura=date(2026, 10, 10 + i),
                importo_netto=100.0,
                importo_iva=22.0,
                importo_totale=122.0,
                processing_status="pending",
            )
            db_session.add(inv)
        await db_session.flush()

        resp = await client.post(
            "/api/v1/fiscal/vat-settlement/compute",
            json={"year": 2026, "quarter": 4},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["unregistered_count"] == 3
        assert len(data["warnings"]) > 0
        assert "3 fatture non registrate" in data["warnings"][0]


# ============================================================
# AC-22.4 — Credito IVA precedente: riportato e sottratto
# ============================================================


class TestAC224CreditoPrecedente:
    """AC-22.4: Credito IVA precedente -> riportato e sottratto."""

    async def test_ac_224_credit_carry_forward(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        tenant: Tenant,
    ):
        """AC-22.4: DATO credito IVA nel trimestre precedente,
        QUANDO calcolo trimestre successivo, ALLORA credito riportato e sottratto."""
        # Create previous quarter settlement with credit (negative saldo)
        prev_settlement = VatSettlement(
            tenant_id=tenant.id,
            year=2025,
            quarter=4,
            iva_vendite=100.0,
            iva_acquisti=300.0,
            saldo=-200.0,  # credito
            status="computed",
        )
        db_session.add(prev_settlement)

        # Create active invoice in Q1 2026
        active = ActiveInvoice(
            tenant_id=tenant.id,
            numero_fattura="FTA-2026-CARRY",
            document_type="TD01",
            cliente_piva="IT66666666666",
            cliente_nome="Cliente Carry",
            data_fattura=date(2026, 2, 1),
            importo_netto=2000.0,
            aliquota_iva=22.0,
            importo_iva=440.0,
            importo_totale=2440.0,
            sdi_status="delivered",
        )
        db_session.add(active)
        await db_session.flush()

        # Compute Q1 2026
        resp = await client.post(
            "/api/v1/fiscal/vat-settlement/compute",
            json={"year": 2026, "quarter": 1},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        # Previous credit should be carried forward
        assert data["credito_periodo_precedente"] == 200.0
        # Saldo should have credit subtracted: 440 - 0 - 200 + interessi
        expected_pre = 440.0 - 0.0 - 200.0
        expected_interessi = round(expected_pre * 0.01, 2)
        expected_saldo = round(expected_pre + expected_interessi, 2)
        assert data["saldo"] == expected_saldo

    async def test_ac_224_no_carry_forward_when_debito(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        tenant: Tenant,
    ):
        """AC-22.4: DATO saldo a debito nel trimestre precedente,
        QUANDO calcolo successivo, ALLORA nessun credito riportato."""
        prev_settlement = VatSettlement(
            tenant_id=tenant.id,
            year=2025,
            quarter=3,
            iva_vendite=500.0,
            iva_acquisti=100.0,
            saldo=400.0,  # debito, non credito
            status="computed",
        )
        db_session.add(prev_settlement)
        await db_session.flush()

        resp = await client.post(
            "/api/v1/fiscal/vat-settlement/compute",
            json={"year": 2025, "quarter": 4},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["credito_periodo_precedente"] == 0.0
