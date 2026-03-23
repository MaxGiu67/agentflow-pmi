"""
Test suite for US-34: Certificazione Unica (CU) annuale
Tests for 4 Acceptance Criteria (AC-34.1 through AC-34.4)
"""

import uuid
from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import Invoice, Tenant, WithholdingTax


FATTURA_PROFESSIONISTA_XML = """<?xml version="1.0" encoding="UTF-8"?>
<p:FatturaElettronica xmlns:p="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2"
  versione="FPR12">
  <FatturaElettronicaHeader>
    <CedentePrestatore>
      <DatiAnagrafici>
        <IdFiscaleIVA>
          <IdPaese>IT</IdPaese>
          <IdCodice>99887766554</IdCodice>
        </IdFiscaleIVA>
        <Anagrafica>
          <Denominazione>Studio Legale Rossi</Denominazione>
        </Anagrafica>
      </DatiAnagrafici>
    </CedentePrestatore>
  </FatturaElettronicaHeader>
  <FatturaElettronicaBody>
    <DatiGenerali>
      <DatiGeneraliDocumento>
        <TipoDocumento>TD06</TipoDocumento>
        <Data>2025-06-15</Data>
        <Numero>PARC-2025-001</Numero>
        <ImportoTotaleDocumento>1220.00</ImportoTotaleDocumento>
      </DatiGeneraliDocumento>
    </DatiGenerali>
  </FatturaElettronicaBody>
</p:FatturaElettronica>"""


# ============================================================
# AC-34.1 — Genera CU per ogni professionista pagato
# ============================================================


class TestAC341GeneraCU:
    """AC-34.1: Genera CU per ogni professionista pagato (compensi lordi, ritenute, netto)."""

    async def test_ac_341_generate_cu_for_professionals(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-34.1: DATO ritenute registrate per anno 2025,
        QUANDO POST /cu/generate/2025,
        ALLORA CU generata con compensi, ritenute, netto."""
        # Create invoice and withholding tax
        inv = Invoice(
            tenant_id=tenant.id,
            type="passiva",
            document_type="TD06",
            source="upload",
            numero_fattura="PARC-2025-001",
            emittente_piva="IT99887766554",
            emittente_nome="Studio Legale Rossi",
            data_fattura=date(2025, 6, 15),
            importo_netto=1000.0,
            importo_iva=220.0,
            importo_totale=1220.0,
            raw_xml=FATTURA_PROFESSIONISTA_XML,
            processing_status="parsed",
        )
        db_session.add(inv)
        await db_session.flush()

        wt = WithholdingTax(
            tenant_id=tenant.id,
            invoice_id=inv.id,
            tipo_ritenuta="RT01",
            aliquota=20.0,
            causale_pagamento="A",
            importo_ritenuta=200.0,
            imponibile_ritenuta=1000.0,
            importo_netto=1020.0,
            f24_code="1040",
            f24_due_date=date(2025, 7, 16),
            status="detected",
        )
        db_session.add(wt)
        await db_session.flush()

        resp = await client.post(
            "/api/v1/cu/generate/2025",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["generated"] == 1
        assert data["year"] == 2025

        cu_item = data["items"][0]
        assert cu_item["percettore_piva"] == "IT99887766554"
        assert cu_item["percettore_nome"] == "Studio Legale Rossi"
        assert cu_item["compenso_lordo"] == 1000.0
        assert cu_item["ritenute_operate"] == 200.0
        assert cu_item["netto_corrisposto"] == 1020.0

    async def test_ac_341_list_cu_by_year(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-34.1: DATO CU generate, QUANDO GET /cu?year=2025,
        ALLORA lista CU per anno."""
        # Create data and generate
        inv = Invoice(
            tenant_id=tenant.id,
            type="passiva",
            document_type="TD06",
            source="upload",
            numero_fattura="PARC-LIST-001",
            emittente_piva="IT99887766554",
            emittente_nome="Studio Legale Rossi",
            data_fattura=date(2025, 3, 10),
            importo_netto=500.0,
            importo_iva=110.0,
            importo_totale=610.0,
            raw_xml=FATTURA_PROFESSIONISTA_XML,
            processing_status="parsed",
        )
        db_session.add(inv)
        await db_session.flush()

        wt = WithholdingTax(
            tenant_id=tenant.id,
            invoice_id=inv.id,
            tipo_ritenuta="RT01",
            aliquota=20.0,
            importo_ritenuta=100.0,
            imponibile_ritenuta=500.0,
            importo_netto=510.0,
            f24_code="1040",
            status="detected",
        )
        db_session.add(wt)
        await db_session.flush()

        # Generate first
        await client.post("/api/v1/cu/generate/2025", headers=auth_headers)

        # Now list
        resp = await client.get(
            "/api/v1/cu?year=2025",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["year"] == 2025
        assert data["total"] >= 1


# ============================================================
# AC-34.2 — Export formato telematico/CSV
# ============================================================


class TestAC342ExportCU:
    """AC-34.2: Export formato telematico/CSV."""

    async def test_ac_342_export_csv(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-34.2: DATO CU generata, QUANDO GET /cu/{id}/export?format=csv,
        ALLORA file CSV con dati CU."""
        inv = Invoice(
            tenant_id=tenant.id,
            type="passiva",
            document_type="TD06",
            source="upload",
            numero_fattura="PARC-EXP-001",
            emittente_piva="IT99887766554",
            emittente_nome="Studio Legale Rossi",
            data_fattura=date(2025, 4, 10),
            importo_netto=2000.0,
            importo_iva=440.0,
            importo_totale=2440.0,
            raw_xml=FATTURA_PROFESSIONISTA_XML,
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

        # Generate CU
        gen_resp = await client.post("/api/v1/cu/generate/2025", headers=auth_headers)
        assert gen_resp.status_code == 200
        cu_id = gen_resp.json()["items"][0]["id"]

        # Export CSV
        resp = await client.get(
            f"/api/v1/cu/{cu_id}/export?format=csv",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["format"] == "csv"
        assert "Compenso_Lordo" in data["content"]
        assert data["filename"].endswith(".csv")

    async def test_ac_342_export_telematico(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-34.2: DATO CU generata, QUANDO export telematico,
        ALLORA formato ministeriale."""
        inv = Invoice(
            tenant_id=tenant.id,
            type="passiva",
            document_type="TD06",
            source="upload",
            numero_fattura="PARC-TEL-001",
            emittente_piva="IT99887766554",
            emittente_nome="Studio Legale Rossi",
            data_fattura=date(2025, 5, 10),
            importo_netto=1500.0,
            importo_iva=330.0,
            importo_totale=1830.0,
            raw_xml=FATTURA_PROFESSIONISTA_XML,
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

        gen_resp = await client.post("/api/v1/cu/generate/2025", headers=auth_headers)
        cu_id = gen_resp.json()["items"][0]["id"]

        resp = await client.get(
            f"/api/v1/cu/{cu_id}/export?format=telematico",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["format"] == "telematico"
        assert "CU2025" in data["content"]
        assert data["filename"].endswith(".txt")


# ============================================================
# AC-34.3 — Ritenute non tutte versate -> warning
# ============================================================


class TestAC343RitenuteNonVersate:
    """AC-34.3: Ritenute non tutte versate -> warning."""

    async def test_ac_343_warning_ritenute_non_versate(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-34.3: DATO ritenute detected ma non paid,
        QUANDO genera CU, ALLORA warning per ritenute non versate."""
        inv = Invoice(
            tenant_id=tenant.id,
            type="passiva",
            document_type="TD06",
            source="upload",
            numero_fattura="PARC-WARN-001",
            emittente_piva="IT99887766554",
            emittente_nome="Studio Legale Rossi",
            data_fattura=date(2025, 7, 15),
            importo_netto=1000.0,
            importo_iva=220.0,
            importo_totale=1220.0,
            raw_xml=FATTURA_PROFESSIONISTA_XML,
            processing_status="parsed",
        )
        db_session.add(inv)
        await db_session.flush()

        # Ritenuta NOT paid (status="detected")
        wt = WithholdingTax(
            tenant_id=tenant.id,
            invoice_id=inv.id,
            tipo_ritenuta="RT01",
            aliquota=20.0,
            importo_ritenuta=200.0,
            imponibile_ritenuta=1000.0,
            importo_netto=1020.0,
            f24_code="1040",
            status="detected",  # not paid!
        )
        db_session.add(wt)
        await db_session.flush()

        resp = await client.post("/api/v1/cu/generate/2025", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["warnings"]) > 0
        assert "non interamente versate" in data["warnings"][0].lower() or "versate" in data["warnings"][0].lower()

        # CU item should also have warning
        cu_item = data["items"][0]
        assert cu_item["warning"] is not None


# ============================================================
# AC-34.4 — Professionista con contributo INPS 4%
# ============================================================


class TestAC344ContributoINPS:
    """AC-34.4: Professionista con contributo INPS 4% -> indicato separatamente."""

    async def test_ac_344_inps_contribution_detected(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-34.4: DATO professionista (ingegnere/consulente),
        QUANDO genera CU, ALLORA contributo INPS 4% indicato separatamente."""
        inv = Invoice(
            tenant_id=tenant.id,
            type="passiva",
            document_type="TD06",
            source="upload",
            numero_fattura="PARC-INPS-001",
            emittente_piva="IT55443322110",
            emittente_nome="Ing. Marco Consulente Tecnico",
            data_fattura=date(2025, 8, 20),
            importo_netto=5000.0,
            importo_iva=1100.0,
            importo_totale=6100.0,
            raw_xml=FATTURA_PROFESSIONISTA_XML,
            processing_status="parsed",
        )
        db_session.add(inv)
        await db_session.flush()

        wt = WithholdingTax(
            tenant_id=tenant.id,
            invoice_id=inv.id,
            tipo_ritenuta="RT01",
            aliquota=20.0,
            importo_ritenuta=1000.0,
            imponibile_ritenuta=5000.0,
            importo_netto=5100.0,
            f24_code="1040",
            status="paid",
        )
        db_session.add(wt)
        await db_session.flush()

        resp = await client.post("/api/v1/cu/generate/2025", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["generated"] >= 1

        # Find the CU for this professional
        cu_item = None
        for item in data["items"]:
            if item["percettore_piva"] == "IT55443322110":
                cu_item = item
                break
        assert cu_item is not None
        assert cu_item["has_inps_separato"] is True
        assert cu_item["contributo_inps"] == 200.0  # 5000 * 4%

    async def test_ac_344_no_inps_for_non_professional(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-34.4: DATO fornitore non professionista,
        QUANDO genera CU, ALLORA nessun contributo INPS."""
        inv = Invoice(
            tenant_id=tenant.id,
            type="passiva",
            document_type="TD06",
            source="upload",
            numero_fattura="PARC-NOINPS-001",
            emittente_piva="IT11223344556",
            emittente_nome="Studio Legale Bianchi",
            data_fattura=date(2025, 9, 10),
            importo_netto=3000.0,
            importo_iva=660.0,
            importo_totale=3660.0,
            raw_xml=FATTURA_PROFESSIONISTA_XML,
            processing_status="parsed",
        )
        db_session.add(inv)
        await db_session.flush()

        wt = WithholdingTax(
            tenant_id=tenant.id,
            invoice_id=inv.id,
            tipo_ritenuta="RT01",
            aliquota=20.0,
            importo_ritenuta=600.0,
            imponibile_ritenuta=3000.0,
            importo_netto=3060.0,
            f24_code="1040",
            status="paid",
        )
        db_session.add(wt)
        await db_session.flush()

        resp = await client.post("/api/v1/cu/generate/2025", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()

        cu_item = None
        for item in data["items"]:
            if item["percettore_piva"] == "IT11223344556":
                cu_item = item
                break
        assert cu_item is not None
        assert cu_item["has_inps_separato"] is False
        assert cu_item["contributo_inps"] == 0.0
