"""
Test suite for US-38: F24 compilazione e generazione
Tests for 4 Acceptance Criteria (AC-38.1 through AC-38.4)
"""

import uuid
from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import (
    ActiveInvoice,
    Invoice,
    StampDuty,
    Tenant,
    VatSettlement,
    WithholdingTax,
)


# ============================================================
# AC-38.1 — F24 da liquidazione IVA
# ============================================================


class TestAC381F24DaIVA:
    """AC-38.1: F24 da liquidazione IVA → sezione Erario, codice tributo, export."""

    async def test_ac_381_generate_f24_from_iva_settlement(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-38.1: DATO liquidazione IVA Q1 con saldo a debito,
        QUANDO POST /f24/generate con quarter=1,
        ALLORA F24 con sezione Erario, codice 6031, periodo T1."""
        # Create VAT settlement for Q1
        settlement = VatSettlement(
            tenant_id=tenant.id,
            year=2026,
            quarter=1,
            iva_vendite=5000.0,
            iva_acquisti=2000.0,
            saldo=3000.0,  # positive = debito
            status="confirmed",
        )
        db_session.add(settlement)
        await db_session.flush()

        resp = await client.post(
            "/api/v1/f24/generate",
            json={"year": 2026, "quarter": 1},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()

        f24 = data["f24"]
        assert f24["year"] == 2026
        assert f24["period_quarter"] == 1
        assert f24["total_debit"] == 3000.0
        assert f24["net_amount"] == 3000.0
        assert f24["status"] == "generated"

        # Check sezione erario with correct tribute code
        sections = f24["sections"]
        assert len(sections) >= 1
        iva_section = sections[0]
        assert iva_section["codice_tributo"] == "6031"
        assert iva_section["periodo_riferimento"] == "T1"
        assert iva_section["importo_debito"] == 3000.0
        assert iva_section["section_type"] == "erario"

    async def test_ac_381_quarterly_tribute_codes(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-38.1: Codici tributo trimestrali: 6031 Q1, 6032 Q2, 6033 Q3, 6034 Q4."""
        for quarter, code in [(1, "6031"), (2, "6032"), (3, "6033"), (4, "6034")]:
            settlement = VatSettlement(
                tenant_id=tenant.id,
                year=2026,
                quarter=quarter,
                iva_vendite=1000.0 * quarter,
                iva_acquisti=500.0,
                saldo=1000.0 * quarter - 500.0,
                status="confirmed",
            )
            db_session.add(settlement)
            await db_session.flush()

            resp = await client.post(
                "/api/v1/f24/generate",
                json={"year": 2026, "quarter": quarter},
                headers=auth_headers,
            )
            assert resp.status_code == 200
            sections = resp.json()["f24"]["sections"]
            iva_sec = [s for s in sections if s["codice_tributo"] == code]
            assert len(iva_sec) == 1, f"Missing code {code} for Q{quarter}"

    async def test_ac_381_export_pdf(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-38.1: DATO F24 generato, QUANDO export PDF,
        ALLORA contenuto PDF con sezioni e importi."""
        settlement = VatSettlement(
            tenant_id=tenant.id,
            year=2026,
            quarter=2,
            iva_vendite=4000.0,
            iva_acquisti=1500.0,
            saldo=2500.0,
            status="confirmed",
        )
        db_session.add(settlement)
        await db_session.flush()

        gen_resp = await client.post(
            "/api/v1/f24/generate",
            json={"year": 2026, "quarter": 2},
            headers=auth_headers,
        )
        f24_id = gen_resp.json()["f24"]["id"]

        resp = await client.get(
            f"/api/v1/f24/{f24_id}/export?format=pdf",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["format"] == "pdf"
        assert "MODELLO F24" in data["content"]
        assert "6032" in data["content"]
        assert data["filename"].endswith(".pdf")

    async def test_ac_381_export_telematico(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-38.1: DATO F24 generato, QUANDO export telematico,
        ALLORA formato ministeriale."""
        settlement = VatSettlement(
            tenant_id=tenant.id,
            year=2026,
            quarter=3,
            iva_vendite=6000.0,
            iva_acquisti=2000.0,
            saldo=4000.0,
            status="confirmed",
        )
        db_session.add(settlement)
        await db_session.flush()

        gen_resp = await client.post(
            "/api/v1/f24/generate",
            json={"year": 2026, "quarter": 3},
            headers=auth_headers,
        )
        f24_id = gen_resp.json()["f24"]["id"]

        resp = await client.get(
            f"/api/v1/f24/{f24_id}/export?format=telematico",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["format"] == "telematico"
        assert "F24|2026" in data["content"]
        assert "SEZ|erario|6033" in data["content"]
        assert data["filename"].endswith(".txt")


# ============================================================
# AC-38.2 — F24 da ritenute
# ============================================================


class TestAC382F24DaRitenute:
    """AC-38.2: F24 da ritenute → codice 1040, mese/anno, importo totale."""

    async def test_ac_382_generate_f24_from_withholding(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-38.2: DATO ritenute per mese 3/2026,
        QUANDO POST /f24/generate con month=3,
        ALLORA F24 con codice 1040 e importo totale ritenute."""
        # Create invoice for March 2026
        inv = Invoice(
            tenant_id=tenant.id,
            type="passiva",
            document_type="TD06",
            source="upload",
            numero_fattura="PARC-F24-001",
            emittente_piva="IT99887766554",
            emittente_nome="Studio Legale Rossi",
            data_fattura=date(2026, 3, 15),
            importo_netto=2000.0,
            importo_iva=440.0,
            importo_totale=2440.0,
            processing_status="parsed",
        )
        db_session.add(inv)
        await db_session.flush()

        wt = WithholdingTax(
            tenant_id=tenant.id,
            invoice_id=inv.id,
            tipo_ritenuta="RT01",
            aliquota=20.0,
            importo_ritenuta=400.0,
            imponibile_ritenuta=2000.0,
            importo_netto=2040.0,
            f24_code="1040",
            status="detected",
        )
        db_session.add(wt)
        await db_session.flush()

        resp = await client.post(
            "/api/v1/f24/generate",
            json={"year": 2026, "month": 3},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()

        f24 = data["f24"]
        assert f24["period_month"] == 3
        assert f24["total_debit"] == 400.0

        # Check ritenuta section
        sections = f24["sections"]
        wt_section = [s for s in sections if s["codice_tributo"] == "1040"]
        assert len(wt_section) == 1
        assert wt_section[0]["importo_debito"] == 400.0
        assert wt_section[0]["periodo_riferimento"] == "03"

    async def test_ac_382_multiple_withholdings_aggregated(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-38.2: DATO multiple ritenute nello stesso mese,
        QUANDO genera F24, ALLORA importo totale aggregato."""
        for i, amount in enumerate([1000.0, 2000.0], 1):
            inv = Invoice(
                tenant_id=tenant.id,
                type="passiva",
                document_type="TD06",
                source="upload",
                numero_fattura=f"PARC-AGG-{i:03d}",
                emittente_piva=f"IT{i:011d}",
                emittente_nome=f"Studio {i}",
                data_fattura=date(2026, 6, 10 + i),
                importo_netto=amount,
                importo_iva=amount * 0.22,
                importo_totale=amount * 1.22,
                processing_status="parsed",
            )
            db_session.add(inv)
            await db_session.flush()

            wt = WithholdingTax(
                tenant_id=tenant.id,
                invoice_id=inv.id,
                tipo_ritenuta="RT01",
                aliquota=20.0,
                importo_ritenuta=amount * 0.2,
                imponibile_ritenuta=amount,
                importo_netto=amount * 1.02,
                f24_code="1040",
                status="detected",
            )
            db_session.add(wt)
            await db_session.flush()

        resp = await client.post(
            "/api/v1/f24/generate",
            json={"year": 2026, "month": 6},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        f24 = resp.json()["f24"]
        # 1000*0.2 + 2000*0.2 = 200 + 400 = 600
        assert f24["total_debit"] == 600.0


# ============================================================
# AC-38.3 — Importo FiscoAPI diverso da stima
# ============================================================


class TestAC383FiscoAPIComparison:
    """AC-38.3: FiscoAPI amount differs from estimate → show both with difference."""

    async def test_ac_383_fisco_api_different_amount(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-38.3: DATO F24 stimato 3000, FiscoAPI dice 3100,
        QUANDO genera F24, ALLORA mostra entrambi con differenza 100."""
        settlement = VatSettlement(
            tenant_id=tenant.id,
            year=2026,
            quarter=1,
            iva_vendite=5000.0,
            iva_acquisti=2000.0,
            saldo=3000.0,
            status="confirmed",
        )
        db_session.add(settlement)
        await db_session.flush()

        resp = await client.post(
            "/api/v1/f24/generate",
            json={
                "year": 2026,
                "quarter": 1,
                "fisco_api_amount": 3100.0,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()

        f24 = data["f24"]
        assert f24["net_amount"] == 3000.0
        assert f24["fisco_api_amount"] == 3100.0
        assert f24["amount_difference"] == 100.0

        # Warning present
        assert len(data["warnings"]) > 0
        assert "FiscoAPI" in data["warnings"][0]
        assert "3100" in data["warnings"][0]
        assert "3000" in data["warnings"][0]

    async def test_ac_383_fisco_api_matching_amount(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-38.3: DATO FiscoAPI uguale a stima,
        QUANDO genera F24, ALLORA nessun warning."""
        settlement = VatSettlement(
            tenant_id=tenant.id,
            year=2026,
            quarter=2,
            iva_vendite=3000.0,
            iva_acquisti=1000.0,
            saldo=2000.0,
            status="confirmed",
        )
        db_session.add(settlement)
        await db_session.flush()

        resp = await client.post(
            "/api/v1/f24/generate",
            json={"year": 2026, "quarter": 2, "fisco_api_amount": 2000.0},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()["warnings"]) == 0


# ============================================================
# AC-38.4 — Compensazione crediti IVA
# ============================================================


class TestAC384CompensazioneCrediti:
    """AC-38.4: Compensazione crediti IVA → sezione credito + debito, netto."""

    async def test_ac_384_iva_credit_compensation(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-38.4: DATO IVA a credito (saldo negativo),
        QUANDO genera F24, ALLORA sezione credito e netto ridotto."""
        # Q1: IVA a credito
        settlement = VatSettlement(
            tenant_id=tenant.id,
            year=2026,
            quarter=1,
            iva_vendite=1000.0,
            iva_acquisti=3000.0,
            saldo=-2000.0,  # credito
            status="confirmed",
        )
        db_session.add(settlement)
        await db_session.flush()

        resp = await client.post(
            "/api/v1/f24/generate",
            json={"year": 2026, "quarter": 1},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        f24 = resp.json()["f24"]

        assert f24["total_credit"] == 2000.0
        assert f24["total_debit"] == 0.0
        assert f24["net_amount"] == -2000.0  # credit

        # Check credit section
        credit_sections = [
            s for s in f24["sections"] if s["section_type"] == "credito"
        ]
        assert len(credit_sections) == 1
        assert credit_sections[0]["importo_credito"] == 2000.0
        assert "compensazione" in credit_sections[0]["description"].lower()

    async def test_ac_384_mixed_debit_credit_netto(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-38.4: DATO IVA credito + ritenute debito,
        QUANDO genera F24, ALLORA netto da versare corretto."""
        # IVA Q1: credito 500
        settlement = VatSettlement(
            tenant_id=tenant.id,
            year=2026,
            quarter=1,
            iva_vendite=1000.0,
            iva_acquisti=1500.0,
            saldo=-500.0,  # credito
            status="confirmed",
        )
        db_session.add(settlement)
        await db_session.flush()

        # Ritenute: debito 300 in month 1 (within Q1)
        inv = Invoice(
            tenant_id=tenant.id,
            type="passiva",
            document_type="TD06",
            source="upload",
            numero_fattura="PARC-COMP-001",
            emittente_piva="IT99887766554",
            emittente_nome="Studio Legale",
            data_fattura=date(2026, 1, 15),
            importo_netto=1500.0,
            importo_iva=330.0,
            importo_totale=1830.0,
            processing_status="parsed",
        )
        db_session.add(inv)
        await db_session.flush()

        wt = WithholdingTax(
            tenant_id=tenant.id,
            invoice_id=inv.id,
            tipo_ritenuta="RT01",
            aliquota=20.0,
            importo_ritenuta=300.0,
            imponibile_ritenuta=1500.0,
            importo_netto=1530.0,
            f24_code="1040",
            status="detected",
        )
        db_session.add(wt)
        await db_session.flush()

        # Generate with both quarter and month
        resp = await client.post(
            "/api/v1/f24/generate",
            json={"year": 2026, "quarter": 1, "month": 1},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        f24 = resp.json()["f24"]

        # Debito (ritenute) = 300, Credito (IVA) = 500
        assert f24["total_debit"] == 300.0
        assert f24["total_credit"] == 500.0
        # Net = 300 - 500 = -200 (still credit)
        assert f24["net_amount"] == -200.0


# ============================================================
# Additional F24 tests (list, detail, mark paid)
# ============================================================


class TestF24Operations:
    """Additional operations: list, detail, mark-paid."""

    async def test_list_f24(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """DATO F24 generati, QUANDO GET /f24, ALLORA lista."""
        settlement = VatSettlement(
            tenant_id=tenant.id,
            year=2026,
            quarter=1,
            iva_vendite=2000.0,
            iva_acquisti=1000.0,
            saldo=1000.0,
            status="confirmed",
        )
        db_session.add(settlement)
        await db_session.flush()

        await client.post(
            "/api/v1/f24/generate",
            json={"year": 2026, "quarter": 1},
            headers=auth_headers,
        )

        resp = await client.get(
            "/api/v1/f24?year=2026",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    async def test_get_f24_detail(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """DATO F24 generato, QUANDO GET /f24/{id}, ALLORA dettaglio con sezioni."""
        settlement = VatSettlement(
            tenant_id=tenant.id,
            year=2026,
            quarter=2,
            iva_vendite=3000.0,
            iva_acquisti=1000.0,
            saldo=2000.0,
            status="confirmed",
        )
        db_session.add(settlement)
        await db_session.flush()

        gen_resp = await client.post(
            "/api/v1/f24/generate",
            json={"year": 2026, "quarter": 2},
            headers=auth_headers,
        )
        f24_id = gen_resp.json()["f24"]["id"]

        resp = await client.get(
            f"/api/v1/f24/{f24_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == f24_id
        assert data["sections"] is not None

    async def test_mark_f24_paid(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """DATO F24 generato, QUANDO PATCH mark-paid, ALLORA status=paid."""
        settlement = VatSettlement(
            tenant_id=tenant.id,
            year=2026,
            quarter=4,
            iva_vendite=5000.0,
            iva_acquisti=2000.0,
            saldo=3000.0,
            status="confirmed",
        )
        db_session.add(settlement)
        await db_session.flush()

        gen_resp = await client.post(
            "/api/v1/f24/generate",
            json={"year": 2026, "quarter": 4},
            headers=auth_headers,
        )
        f24_id = gen_resp.json()["f24"]["id"]

        resp = await client.patch(
            f"/api/v1/f24/{f24_id}/mark-paid",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "paid"
        assert data["net_amount"] == 3000.0

    async def test_f24_not_found(
        self, client: AsyncClient, auth_headers: dict,
    ):
        """DATO F24 inesistente, QUANDO GET, ALLORA 404."""
        fake_id = str(uuid.uuid4())
        resp = await client.get(
            f"/api/v1/f24/{fake_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 404
