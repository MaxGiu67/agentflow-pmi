"""
Test suite for US-05: Parsing XML FatturaPA
Tests for 4 Acceptance Criteria (AC-05.1 through AC-05.4)
"""

import time
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from api.agents.parser_agent import ParserAgent
from api.db.models import Invoice, Tenant
from tests.conftest import create_invoice


# ============================================================
# AC-05.1 — Parse XML estrae tutti campi, pubblica "invoice.parsed"
# ============================================================


class TestAC051ParsingXMLFatturaPA:
    """AC-05.1: Parse XML FatturaPA estraendo tutti i campi."""

    async def test_ac_051_parsing_xml_fatturapa(
        self,
        db_session: AsyncSession,
        tenant: Tenant,
        invoice_in_db: Invoice,
        sample_fattura_xml: str,
    ):
        """AC-05.1: DATO XML FatturaPA valido, QUANDO parsing,
        ALLORA estrae tutti i campi e pubblica invoice.parsed."""
        parser = ParserAgent(db_session)

        parsed = await parser.parse_invoice(invoice_in_db.id, tenant.id)

        # Verify all fields extracted
        assert parsed["tipo_documento"] == "TD01"
        assert parsed["emittente_piva"] == "IT01234567890"
        assert parsed["emittente_nome"] == "Fornitore Alpha SRL"
        assert parsed["data_fattura"] == "2025-01-15"
        assert parsed["numero_fattura"] == "FT-2025-0001"
        assert parsed["importo_totale"] == 1220.0

        # Verify line items
        assert len(parsed["linee_dettaglio"]) >= 1
        linea = parsed["linee_dettaglio"][0]
        assert linea["descrizione"] == "Consulenza informatica"
        assert linea["prezzo_totale"] == 1000.0
        assert linea["aliquota_iva"] == 22.0

        # Verify riepilogo
        assert len(parsed["riepilogo"]) >= 1
        riep = parsed["riepilogo"][0]
        assert riep["imponibile"] == 1000.0
        assert riep["imposta"] == 220.0

        # Verify invoice was updated
        await db_session.refresh(invoice_in_db)
        assert invoice_in_db.processing_status == "parsed"
        assert invoice_in_db.structured_data is not None
        assert invoice_in_db.importo_netto == 1000.0
        assert invoice_in_db.importo_iva == 220.0

        # Verify event was published
        from api.agents.base_agent import event_bus
        events = event_bus.get_events("invoice.parsed")
        assert len(events) >= 1


# ============================================================
# AC-05.2 — Nota di credito TD04
# ============================================================


class TestAC052NotaCreditoTD04:
    """AC-05.2: Identifica nota di credito TD04."""

    async def test_ac_052_nota_credito_td04(
        self,
        db_session: AsyncSession,
        tenant: Tenant,
        sample_nota_credito_xml: str,
    ):
        """AC-05.2: DATO XML con TipoDocumento=TD04,
        QUANDO parsing, ALLORA identifica come nota di credito."""
        invoice = Invoice(
            tenant_id=tenant.id,
            type="passiva",
            document_type="TD01",  # Will be updated by parser
            source="cassetto_fiscale",
            numero_fattura="NC-2025-0001",
            emittente_piva="IT01234567890",
            emittente_nome="Fornitore Alpha SRL",
            importo_totale=244.0,
            raw_xml=sample_nota_credito_xml,
            processing_status="pending",
        )
        db_session.add(invoice)
        await db_session.flush()

        parser = ParserAgent(db_session)
        parsed = await parser.parse_invoice(invoice.id, tenant.id)

        assert parsed["tipo_documento"] == "TD04"
        assert parsed["tipo_documento_desc"] == "nota_credito"

        await db_session.refresh(invoice)
        assert invoice.document_type == "TD04"


# ============================================================
# AC-05.3 — XML malformato
# ============================================================


class TestAC053XMLMalformato:
    """AC-05.3: XML malformato segnato come parsing_fallito."""

    async def test_ac_053_xml_malformato(
        self,
        db_session: AsyncSession,
        tenant: Tenant,
    ):
        """AC-05.3: DATO XML malformato, QUANDO parsing,
        ALLORA segnata come parsing_fallito."""
        invoice = Invoice(
            tenant_id=tenant.id,
            type="passiva",
            document_type="TD01",
            source="cassetto_fiscale",
            numero_fattura="FT-MALFORMED",
            emittente_piva="IT99999999999",
            raw_xml="<not valid xml<<<>>>",
            processing_status="pending",
        )
        db_session.add(invoice)
        await db_session.flush()

        parser = ParserAgent(db_session)

        with pytest.raises(ValueError, match="Parsing fallito"):
            await parser.parse_invoice(invoice.id, tenant.id)

        await db_session.refresh(invoice)
        assert invoice.processing_status == "error"
        assert invoice.structured_data is not None
        assert "parsing_fallito" in str(invoice.structured_data.get("parse_status", ""))


# ============================================================
# AC-05.4 — Fattura 200+ righe
# ============================================================


class TestAC054Fattura200Righe:
    """AC-05.4: Gestisce fattura con 200+ righe entro 5 secondi."""

    async def test_ac_054_fattura_200_righe(
        self,
        db_session: AsyncSession,
        tenant: Tenant,
    ):
        """AC-05.4: DATO fattura con 200+ linee dettaglio,
        QUANDO parsing, ALLORA gestisce entro 5 secondi."""
        # Generate XML with 200+ lines
        lines = ""
        for i in range(250):
            lines += f"""
        <DettaglioLinee>
          <NumeroLinea>{i + 1}</NumeroLinea>
          <Descrizione>Articolo {i + 1} - Servizio professionale</Descrizione>
          <Quantita>1.00</Quantita>
          <PrezzoUnitario>10.00</PrezzoUnitario>
          <PrezzoTotale>10.00</PrezzoTotale>
          <AliquotaIVA>22.00</AliquotaIVA>
        </DettaglioLinee>"""

        big_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<p:FatturaElettronica xmlns:p="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2"
  versione="FPR12">
  <FatturaElettronicaHeader>
    <CedentePrestatore>
      <DatiAnagrafici>
        <IdFiscaleIVA>
          <IdPaese>IT</IdPaese>
          <IdCodice>01234567890</IdCodice>
        </IdFiscaleIVA>
        <Anagrafica>
          <Denominazione>Big Supplier SRL</Denominazione>
        </Anagrafica>
      </DatiAnagrafici>
    </CedentePrestatore>
  </FatturaElettronicaHeader>
  <FatturaElettronicaBody>
    <DatiGenerali>
      <DatiGeneraliDocumento>
        <TipoDocumento>TD01</TipoDocumento>
        <Data>2025-03-01</Data>
        <Numero>FT-BIG-001</Numero>
        <ImportoTotaleDocumento>3050.00</ImportoTotaleDocumento>
      </DatiGeneraliDocumento>
    </DatiGenerali>
    <DatiBeniServizi>{lines}
      <DatiRiepilogo>
        <AliquotaIVA>22.00</AliquotaIVA>
        <ImponibileImporto>2500.00</ImponibileImporto>
        <Imposta>550.00</Imposta>
      </DatiRiepilogo>
    </DatiBeniServizi>
  </FatturaElettronicaBody>
</p:FatturaElettronica>"""

        invoice = Invoice(
            tenant_id=tenant.id,
            type="passiva",
            document_type="TD01",
            source="upload",
            numero_fattura="FT-BIG-001",
            emittente_piva="IT01234567890",
            raw_xml=big_xml,
            processing_status="pending",
        )
        db_session.add(invoice)
        await db_session.flush()

        parser = ParserAgent(db_session)

        start = time.time()
        parsed = await parser.parse_invoice(invoice.id, tenant.id)
        elapsed = time.time() - start

        assert elapsed < 5.0, f"Parsing took {elapsed:.2f}s, should be <5s"
        assert len(parsed["linee_dettaglio"]) == 250

        await db_session.refresh(invoice)
        assert invoice.processing_status == "parsed"
