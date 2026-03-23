"""
Test suite for US-33: Ritenute d'acconto
Tests for 4 Acceptance Criteria (AC-33.1 through AC-33.4)
"""

import uuid
from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import Invoice, Tenant, WithholdingTax, FiscalDeadline
from tests.conftest import create_invoice


FATTURA_CON_RITENUTA_XML = """<?xml version="1.0" encoding="UTF-8"?>
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
        <Data>2026-01-15</Data>
        <Numero>PARC-2026-001</Numero>
        <ImportoTotaleDocumento>1220.00</ImportoTotaleDocumento>
        <DatiRitenuta>
          <TipoRitenuta>RT01</TipoRitenuta>
          <ImportoRitenuta>200.00</ImportoRitenuta>
          <AliquotaRitenuta>20.00</AliquotaRitenuta>
          <CausalePagamento>A</CausalePagamento>
        </DatiRitenuta>
      </DatiGeneraliDocumento>
    </DatiGenerali>
    <DatiBeniServizi>
      <DettaglioLinee>
        <NumeroLinea>1</NumeroLinea>
        <Descrizione>Consulenza legale</Descrizione>
        <Quantita>1.00</Quantita>
        <PrezzoUnitario>1000.00</PrezzoUnitario>
        <PrezzoTotale>1000.00</PrezzoTotale>
        <AliquotaIVA>22.00</AliquotaIVA>
      </DettaglioLinee>
      <DatiRiepilogo>
        <AliquotaIVA>22.00</AliquotaIVA>
        <ImponibileImporto>1000.00</ImponibileImporto>
        <Imposta>220.00</Imposta>
      </DatiRiepilogo>
    </DatiBeniServizi>
  </FatturaElettronicaBody>
</p:FatturaElettronica>"""


FATTURA_SENZA_RITENUTA_PROFESSIONISTA_XML = """<?xml version="1.0" encoding="UTF-8"?>
<p:FatturaElettronica xmlns:p="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2"
  versione="FPR12">
  <FatturaElettronicaHeader>
    <CedentePrestatore>
      <DatiAnagrafici>
        <IdFiscaleIVA>
          <IdPaese>IT</IdPaese>
          <IdCodice>11223344556</IdCodice>
        </IdFiscaleIVA>
        <Anagrafica>
          <Denominazione>Studio Commercialista Bianchi</Denominazione>
        </Anagrafica>
      </DatiAnagrafici>
    </CedentePrestatore>
  </FatturaElettronicaHeader>
  <FatturaElettronicaBody>
    <DatiGenerali>
      <DatiGeneraliDocumento>
        <TipoDocumento>TD01</TipoDocumento>
        <Data>2026-02-10</Data>
        <Numero>FT-PROF-001</Numero>
        <ImportoTotaleDocumento>610.00</ImportoTotaleDocumento>
      </DatiGeneraliDocumento>
    </DatiGenerali>
    <DatiBeniServizi>
      <DettaglioLinee>
        <NumeroLinea>1</NumeroLinea>
        <Descrizione>Consulenza fiscale</Descrizione>
        <Quantita>1.00</Quantita>
        <PrezzoUnitario>500.00</PrezzoUnitario>
        <PrezzoTotale>500.00</PrezzoTotale>
        <AliquotaIVA>22.00</AliquotaIVA>
      </DettaglioLinee>
      <DatiRiepilogo>
        <AliquotaIVA>22.00</AliquotaIVA>
        <ImponibileImporto>500.00</ImponibileImporto>
        <Imposta>110.00</Imposta>
      </DatiRiepilogo>
    </DatiBeniServizi>
  </FatturaElettronicaBody>
</p:FatturaElettronica>"""


# ============================================================
# AC-33.1 — Riconoscimento tag <DatiRitenuta> da XML, calcolo netto
# ============================================================


class TestAC331RiconoscimentoRitenuta:
    """AC-33.1: Riconoscimento tag <DatiRitenuta> da XML, calcolo netto."""

    async def test_ac_331_detect_ritenuta_from_xml(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-33.1: DATO fattura con <DatiRitenuta>, QUANDO detect,
        ALLORA ritenuta riconosciuta con importo e netto calcolato."""
        inv = Invoice(
            tenant_id=tenant.id,
            type="passiva",
            document_type="TD06",
            source="upload",
            numero_fattura="PARC-2026-001",
            emittente_piva="IT99887766554",
            emittente_nome="Studio Legale Rossi",
            data_fattura=date(2026, 1, 15),
            importo_netto=1000.0,
            importo_iva=220.0,
            importo_totale=1220.0,
            raw_xml=FATTURA_CON_RITENUTA_XML,
            processing_status="parsed",
        )
        db_session.add(inv)
        await db_session.flush()

        resp = await client.post(
            "/api/v1/withholding-taxes/detect",
            json={"invoice_id": str(inv.id)},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["detected"] is True
        assert data["tipo_ritenuta"] == "RT01"
        assert data["aliquota"] == 20.0
        assert data["importo_ritenuta"] == 200.0
        assert data["importo_netto"] == 1020.0  # 1220 - 200
        assert data["causale_pagamento"] == "A"

    async def test_ac_331_no_ritenuta_no_warning(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
        sample_fattura_xml: str,
    ):
        """AC-33.1: DATO fattura senza <DatiRitenuta> e non professionista,
        QUANDO detect, ALLORA detected=False, no warning."""
        inv = Invoice(
            tenant_id=tenant.id,
            type="passiva",
            document_type="TD01",
            source="upload",
            numero_fattura="FT-NORT-001",
            emittente_piva="IT01234567890",
            emittente_nome="Fornitore Alpha SRL",
            data_fattura=date(2026, 1, 15),
            importo_netto=1000.0,
            importo_iva=220.0,
            importo_totale=1220.0,
            raw_xml=sample_fattura_xml,
            processing_status="parsed",
        )
        db_session.add(inv)
        await db_session.flush()

        resp = await client.post(
            "/api/v1/withholding-taxes/detect",
            json={"invoice_id": str(inv.id)},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["detected"] is False
        assert data["warning"] is None


# ============================================================
# AC-33.2 — Registrazione contabile con ritenuta
# ============================================================


class TestAC332RegistrazioneContabile:
    """AC-33.2: Registrazione contabile con ritenuta
    (DARE costo+IVA / AVERE fornitore+erario)."""

    async def test_ac_332_journal_entry_with_ritenuta(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-33.2: DATO ritenuta rilevata, QUANDO detect,
        ALLORA journal_entry con 4 righe (costo, IVA, fornitore, erario)."""
        inv = Invoice(
            tenant_id=tenant.id,
            type="passiva",
            document_type="TD06",
            source="upload",
            numero_fattura="PARC-JE-001",
            emittente_piva="IT99887766554",
            emittente_nome="Studio Legale Rossi",
            data_fattura=date(2026, 1, 15),
            importo_netto=1000.0,
            importo_iva=220.0,
            importo_totale=1220.0,
            raw_xml=FATTURA_CON_RITENUTA_XML,
            processing_status="parsed",
        )
        db_session.add(inv)
        await db_session.flush()

        resp = await client.post(
            "/api/v1/withholding-taxes/detect",
            json={"invoice_id": str(inv.id)},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        je = data["journal_entry"]
        assert je is not None
        lines = je["lines"]
        assert len(lines) == 4

        # Check DARE (debit) entries
        debit_lines = [l for l in lines if l["debit"] > 0]
        assert len(debit_lines) == 2
        codes = {l["account_code"] for l in debit_lines}
        assert "6100" in codes  # Costo per servizi
        assert "1120" in codes  # IVA a credito

        # Check AVERE (credit) entries
        credit_lines = [l for l in lines if l["credit"] > 0]
        assert len(credit_lines) == 2
        codes = {l["account_code"] for l in credit_lines}
        assert "2010" in codes  # Debiti verso fornitori
        assert "2030" in codes  # Erario c/ritenute


# ============================================================
# AC-33.3 — Scadenza F24 (cod. 1040, 16 mese dopo pagamento)
# ============================================================


class TestAC333ScadenzaF24:
    """AC-33.3: Scadenza F24 (cod. 1040, 16 mese dopo pagamento)."""

    async def test_ac_333_f24_deadline_created(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-33.3: DATO ritenuta rilevata da fattura gen 2026,
        QUANDO detect, ALLORA f24_code=1040, due_date=16/02/2026."""
        inv = Invoice(
            tenant_id=tenant.id,
            type="passiva",
            document_type="TD06",
            source="upload",
            numero_fattura="PARC-F24-001",
            emittente_piva="IT99887766554",
            emittente_nome="Studio Legale Rossi",
            data_fattura=date(2026, 1, 15),
            importo_netto=1000.0,
            importo_iva=220.0,
            importo_totale=1220.0,
            raw_xml=FATTURA_CON_RITENUTA_XML,
            processing_status="parsed",
        )
        db_session.add(inv)
        await db_session.flush()

        resp = await client.post(
            "/api/v1/withholding-taxes/detect",
            json={"invoice_id": str(inv.id)},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["f24_code"] == "1040"
        assert data["f24_due_date"] == "2026-02-16"

    async def test_ac_333_f24_december_rolls_to_next_year(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-33.3: DATO fattura dicembre 2026, QUANDO detect,
        ALLORA f24 due_date = 16/01/2027."""
        xml_dec = FATTURA_CON_RITENUTA_XML.replace(
            "2026-01-15", "2026-12-20"
        ).replace("PARC-2026-001", "PARC-DIC-001")

        inv = Invoice(
            tenant_id=tenant.id,
            type="passiva",
            document_type="TD06",
            source="upload",
            numero_fattura="PARC-DIC-001",
            emittente_piva="IT99887766554",
            emittente_nome="Studio Legale Rossi",
            data_fattura=date(2026, 12, 20),
            importo_netto=1000.0,
            importo_iva=220.0,
            importo_totale=1220.0,
            raw_xml=xml_dec,
            processing_status="parsed",
        )
        db_session.add(inv)
        await db_session.flush()

        resp = await client.post(
            "/api/v1/withholding-taxes/detect",
            json={"invoice_id": str(inv.id)},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["f24_due_date"] == "2027-01-16"


# ============================================================
# AC-33.4 — Fattura senza tag ma da professionista -> warning
# ============================================================


class TestAC334ProfessionistaWarning:
    """AC-33.4: Fattura senza tag ma da professionista -> warning."""

    async def test_ac_334_professional_supplier_warning(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-33.4: DATO fattura da 'Studio Commercialista' senza ritenuta,
        QUANDO detect, ALLORA warning professionista."""
        inv = Invoice(
            tenant_id=tenant.id,
            type="passiva",
            document_type="TD01",
            source="upload",
            numero_fattura="FT-PROF-001",
            emittente_piva="IT11223344556",
            emittente_nome="Studio Commercialista Bianchi",
            data_fattura=date(2026, 2, 10),
            importo_netto=500.0,
            importo_iva=110.0,
            importo_totale=610.0,
            raw_xml=FATTURA_SENZA_RITENUTA_PROFESSIONISTA_XML,
            processing_status="parsed",
        )
        db_session.add(inv)
        await db_session.flush()

        resp = await client.post(
            "/api/v1/withholding-taxes/detect",
            json={"invoice_id": str(inv.id)},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["detected"] is False
        assert data["warning"] is not None
        assert "commercialista" in data["warning"].lower() or "professionista" in data["warning"].lower()

    async def test_ac_334_parcella_without_ritenuta_warning(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-33.4: DATO fattura TD06 (parcella) senza DatiRitenuta,
        QUANDO detect, ALLORA warning tipo documento."""
        # Use XML without DatiRitenuta but doc type TD06
        xml_td06 = FATTURA_SENZA_RITENUTA_PROFESSIONISTA_XML.replace(
            "TD01", "TD06"
        ).replace("FT-PROF-001", "PARC-NORT-001")

        inv = Invoice(
            tenant_id=tenant.id,
            type="passiva",
            document_type="TD06",
            source="upload",
            numero_fattura="PARC-NORT-001",
            emittente_piva="IT11223344556",
            emittente_nome="Dott. Verdi",
            data_fattura=date(2026, 3, 1),
            importo_netto=500.0,
            importo_iva=110.0,
            importo_totale=610.0,
            raw_xml=xml_td06,
            processing_status="parsed",
        )
        db_session.add(inv)
        await db_session.flush()

        resp = await client.post(
            "/api/v1/withholding-taxes/detect",
            json={"invoice_id": str(inv.id)},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["detected"] is False
        assert data["warning"] is not None

    async def test_ac_334_list_withholding_taxes(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-33: DATO ritenute rilevate, QUANDO list,
        ALLORA elenco ritenute per tenant."""
        # First detect one
        inv = Invoice(
            tenant_id=tenant.id,
            type="passiva",
            document_type="TD06",
            source="upload",
            numero_fattura="PARC-LIST-001",
            emittente_piva="IT99887766554",
            emittente_nome="Studio Legale Rossi",
            data_fattura=date(2026, 1, 15),
            importo_netto=1000.0,
            importo_iva=220.0,
            importo_totale=1220.0,
            raw_xml=FATTURA_CON_RITENUTA_XML,
            processing_status="parsed",
        )
        db_session.add(inv)
        await db_session.flush()

        await client.post(
            "/api/v1/withholding-taxes/detect",
            json={"invoice_id": str(inv.id)},
            headers=auth_headers,
        )

        resp = await client.get(
            "/api/v1/withholding-taxes",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        item = data["items"][0]
        assert item["tipo_ritenuta"] == "RT01"
        assert item["f24_code"] == "1040"
