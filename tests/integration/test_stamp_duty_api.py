"""
Test suite for US-35: Imposta di bollo
Tests for 5 Acceptance Criteria (AC-35.1 through AC-35.5)
"""

import uuid
from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import Invoice, StampDuty, Tenant


FATTURA_ESENTE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<p:FatturaElettronica xmlns:p="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2"
  versione="FPR12">
  <FatturaElettronicaHeader>
    <CedentePrestatore>
      <DatiAnagrafici>
        <IdFiscaleIVA>
          <IdPaese>IT</IdPaese>
          <IdCodice>12345678901</IdCodice>
        </IdFiscaleIVA>
        <Anagrafica>
          <Denominazione>Fornitore Esente SRL</Denominazione>
        </Anagrafica>
      </DatiAnagrafici>
    </CedentePrestatore>
  </FatturaElettronicaHeader>
  <FatturaElettronicaBody>
    <DatiGenerali>
      <DatiGeneraliDocumento>
        <TipoDocumento>TD01</TipoDocumento>
        <Data>2026-02-15</Data>
        <Numero>FT-ES-001</Numero>
        <ImportoTotaleDocumento>100.00</ImportoTotaleDocumento>
      </DatiGeneraliDocumento>
    </DatiGenerali>
    <DatiBeniServizi>
      <DatiRiepilogo>
        <AliquotaIVA>0.00</AliquotaIVA>
        <ImponibileImporto>100.00</ImponibileImporto>
        <Imposta>0.00</Imposta>
      </DatiRiepilogo>
    </DatiBeniServizi>
  </FatturaElettronicaBody>
</p:FatturaElettronica>"""


FATTURA_MISTA_XML = """<?xml version="1.0" encoding="UTF-8"?>
<p:FatturaElettronica xmlns:p="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2"
  versione="FPR12">
  <FatturaElettronicaHeader>
    <CedentePrestatore>
      <DatiAnagrafici>
        <IdFiscaleIVA>
          <IdPaese>IT</IdPaese>
          <IdCodice>12345678901</IdCodice>
        </IdFiscaleIVA>
        <Anagrafica>
          <Denominazione>Fornitore Misto SRL</Denominazione>
        </Anagrafica>
      </DatiAnagrafici>
    </CedentePrestatore>
  </FatturaElettronicaHeader>
  <FatturaElettronicaBody>
    <DatiGenerali>
      <DatiGeneraliDocumento>
        <TipoDocumento>TD01</TipoDocumento>
        <Data>2026-03-10</Data>
        <Numero>FT-MIX-001</Numero>
        <ImportoTotaleDocumento>200.00</ImportoTotaleDocumento>
      </DatiGeneraliDocumento>
    </DatiGenerali>
    <DatiBeniServizi>
      <DatiRiepilogo>
        <AliquotaIVA>22.00</AliquotaIVA>
        <ImponibileImporto>50.00</ImponibileImporto>
        <Imposta>11.00</Imposta>
      </DatiRiepilogo>
      <DatiRiepilogo>
        <AliquotaIVA>0.00</AliquotaIVA>
        <ImponibileImporto>100.00</ImponibileImporto>
        <Imposta>0.00</Imposta>
      </DatiRiepilogo>
    </DatiBeniServizi>
  </FatturaElettronicaBody>
</p:FatturaElettronica>"""


FATTURA_PASSIVA_SENZA_BOLLO_XML = """<?xml version="1.0" encoding="UTF-8"?>
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
          <Denominazione>Fornitore Passivo SRL</Denominazione>
        </Anagrafica>
      </DatiAnagrafici>
    </CedentePrestatore>
  </FatturaElettronicaHeader>
  <FatturaElettronicaBody>
    <DatiGenerali>
      <DatiGeneraliDocumento>
        <TipoDocumento>TD01</TipoDocumento>
        <Data>2026-01-20</Data>
        <Numero>FT-PAS-001</Numero>
        <ImportoTotaleDocumento>150.00</ImportoTotaleDocumento>
      </DatiGeneraliDocumento>
    </DatiGenerali>
    <DatiBeniServizi>
      <DatiRiepilogo>
        <AliquotaIVA>0.00</AliquotaIVA>
        <ImponibileImporto>150.00</ImponibileImporto>
        <Imposta>0.00</Imposta>
      </DatiRiepilogo>
    </DatiBeniServizi>
  </FatturaElettronicaBody>
</p:FatturaElettronica>"""


# ============================================================
# AC-35.1 — Rilevamento obbligo bollo su fatture esenti >77.47
# ============================================================


class TestAC351RilevamentoBollo:
    """AC-35.1: Rilevamento obbligo bollo su fatture esenti >77.47 EUR
    -> tag <BolloVirtuale>."""

    async def test_ac_351_exempt_invoice_above_threshold(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-35.1: DATO fattura esente >77.47 EUR, QUANDO check,
        ALLORA bollo_required=True, bollo_virtuale=True, importo 2 EUR."""
        inv = Invoice(
            tenant_id=tenant.id,
            type="attiva",
            document_type="TD01",
            source="upload",
            numero_fattura="FT-ES-001",
            emittente_piva="IT12345678901",
            emittente_nome="Fornitore Esente SRL",
            data_fattura=date(2026, 2, 15),
            importo_netto=100.0,
            importo_iva=0.0,
            importo_totale=100.0,
            raw_xml=FATTURA_ESENTE_XML,
            structured_data={
                "riepilogo": [
                    {"aliquota_iva": 0.0, "imponibile": 100.0, "imposta": 0.0},
                ],
            },
            processing_status="parsed",
        )
        db_session.add(inv)
        await db_session.flush()

        resp = await client.post(
            "/api/v1/fiscal/stamp-duties/check",
            json={"invoice_id": str(inv.id)},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["bollo_required"] is True
        assert data["bollo_virtuale"] is True
        assert data["importo_bollo"] == 2.0
        assert data["importo_esente"] == 100.0


# ============================================================
# AC-35.2 — Conteggio trimestrale (N fatture x 2, scadenza, cod. 2501)
# ============================================================


class TestAC352ConteggioTrimestrale:
    """AC-35.2: Conteggio trimestrale (N fatture x 2 EUR, scadenza, cod. 2501)."""

    async def test_ac_352_quarterly_summary(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-35.2: DATO fatture con bollo nel Q1, QUANDO summary,
        ALLORA conteggio, importo totale, codice 2501, scadenza."""
        # Create stamp duty records directly
        for i in range(3):
            sd = StampDuty(
                tenant_id=tenant.id,
                invoice_id=uuid.uuid4(),
                importo_bollo=2.0,
                importo_esente=100.0,
                bollo_virtuale=True,
                year=2026,
                quarter=1,
            )
            db_session.add(sd)
        await db_session.flush()

        resp = await client.get(
            "/api/v1/fiscal/stamp-duties?year=2026&quarter=1",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["invoice_count"] == 3
        assert data["importo_unitario"] == 2.0
        assert data["importo_totale"] == 6.0
        assert data["f24_code"] == "2501"
        assert data["due_date"] == "2026-05-31"
        assert "2501" in data["message"]

    async def test_ac_352_empty_quarter(
        self, client: AsyncClient, auth_headers: dict,
    ):
        """AC-35.2: DATO nessun bollo nel trimestre, QUANDO summary,
        ALLORA conteggio zero."""
        resp = await client.get(
            "/api/v1/fiscal/stamp-duties?year=2026&quarter=3",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["invoice_count"] == 0
        assert data["importo_totale"] == 0.0


# ============================================================
# AC-35.3 — Sotto soglia 77.47 -> NON applica bollo
# ============================================================


class TestAC353SottoSoglia:
    """AC-35.3: Sotto soglia 77.47 EUR -> NON applica bollo."""

    async def test_ac_353_below_threshold_no_stamp(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-35.3: DATO fattura esente <=77.47 EUR, QUANDO check,
        ALLORA bollo_required=False."""
        inv = Invoice(
            tenant_id=tenant.id,
            type="attiva",
            document_type="TD01",
            source="upload",
            numero_fattura="FT-UNDER-001",
            emittente_piva="IT12345678901",
            emittente_nome="Fornitore Sotto Soglia",
            data_fattura=date(2026, 2, 15),
            importo_netto=50.0,
            importo_iva=0.0,
            importo_totale=50.0,
            structured_data={
                "riepilogo": [
                    {"aliquota_iva": 0.0, "imponibile": 50.0, "imposta": 0.0},
                ],
            },
            processing_status="parsed",
        )
        db_session.add(inv)
        await db_session.flush()

        resp = await client.post(
            "/api/v1/fiscal/stamp-duties/check",
            json={"invoice_id": str(inv.id)},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["bollo_required"] is False
        assert data["importo_bollo"] == 0.0
        assert "sotto soglia" in data["message"].lower() or "non dovuto" in data["message"].lower()

    async def test_ac_353_exactly_at_threshold(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-35.3: DATO fattura esente esattamente 77.47 EUR, QUANDO check,
        ALLORA bollo_required=False (soglia non superata)."""
        inv = Invoice(
            tenant_id=tenant.id,
            type="attiva",
            document_type="TD01",
            source="upload",
            numero_fattura="FT-EXACT-001",
            emittente_piva="IT12345678901",
            emittente_nome="Fornitore Soglia Esatta",
            data_fattura=date(2026, 2, 15),
            importo_netto=77.47,
            importo_iva=0.0,
            importo_totale=77.47,
            structured_data={
                "riepilogo": [
                    {"aliquota_iva": 0.0, "imponibile": 77.47, "imposta": 0.0},
                ],
            },
            processing_status="parsed",
        )
        db_session.add(inv)
        await db_session.flush()

        resp = await client.post(
            "/api/v1/fiscal/stamp-duties/check",
            json={"invoice_id": str(inv.id)},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["bollo_required"] is False


# ============================================================
# AC-35.4 — Fattura mista (esente+imponibile) -> bollo solo se esenti >77.47
# ============================================================


class TestAC354FatturaMista:
    """AC-35.4: Fattura mista (parte esente+imponibile)
    -> bollo solo se esenti >77.47."""

    async def test_ac_354_mixed_invoice_exempt_above_threshold(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-35.4: DATO fattura mista con esente >77.47, QUANDO check,
        ALLORA bollo richiesto."""
        inv = Invoice(
            tenant_id=tenant.id,
            type="attiva",
            document_type="TD01",
            source="upload",
            numero_fattura="FT-MIX-001",
            emittente_piva="IT12345678901",
            emittente_nome="Fornitore Misto SRL",
            data_fattura=date(2026, 3, 10),
            importo_netto=150.0,
            importo_iva=11.0,
            importo_totale=161.0,
            raw_xml=FATTURA_MISTA_XML,
            structured_data={
                "riepilogo": [
                    {"aliquota_iva": 22.0, "imponibile": 50.0, "imposta": 11.0},
                    {"aliquota_iva": 0.0, "imponibile": 100.0, "imposta": 0.0},
                ],
            },
            processing_status="parsed",
        )
        db_session.add(inv)
        await db_session.flush()

        resp = await client.post(
            "/api/v1/fiscal/stamp-duties/check",
            json={"invoice_id": str(inv.id)},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["bollo_required"] is True
        assert data["importo_esente"] == 100.0
        assert data["importo_bollo"] == 2.0

    async def test_ac_354_mixed_invoice_exempt_below_threshold(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-35.4: DATO fattura mista con esente <=77.47, QUANDO check,
        ALLORA bollo NON richiesto."""
        inv = Invoice(
            tenant_id=tenant.id,
            type="attiva",
            document_type="TD01",
            source="upload",
            numero_fattura="FT-MIX-LOW-001",
            emittente_piva="IT12345678901",
            emittente_nome="Fornitore Misto Low",
            data_fattura=date(2026, 3, 10),
            importo_netto=120.0,
            importo_iva=15.40,
            importo_totale=135.40,
            structured_data={
                "riepilogo": [
                    {"aliquota_iva": 22.0, "imponibile": 70.0, "imposta": 15.40},
                    {"aliquota_iva": 0.0, "imponibile": 50.0, "imposta": 0.0},
                ],
            },
            processing_status="parsed",
        )
        db_session.add(inv)
        await db_session.flush()

        resp = await client.post(
            "/api/v1/fiscal/stamp-duties/check",
            json={"invoice_id": str(inv.id)},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["bollo_required"] is False


# ============================================================
# AC-35.5 — Fattura passiva ricevuta senza bollo -> warning
# ============================================================


class TestAC355PassivaSenzaBollo:
    """AC-35.5: Fattura passiva ricevuta senza bollo -> warning."""

    async def test_ac_355_passive_without_bollo_warning(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-35.5: DATO fattura passiva esente >77.47 senza bollo,
        QUANDO check, ALLORA warning presente."""
        inv = Invoice(
            tenant_id=tenant.id,
            type="passiva",
            document_type="TD01",
            source="upload",
            numero_fattura="FT-PAS-001",
            emittente_piva="IT99887766554",
            emittente_nome="Fornitore Passivo SRL",
            data_fattura=date(2026, 1, 20),
            importo_netto=150.0,
            importo_iva=0.0,
            importo_totale=150.0,
            raw_xml=FATTURA_PASSIVA_SENZA_BOLLO_XML,
            structured_data={
                "riepilogo": [
                    {"aliquota_iva": 0.0, "imponibile": 150.0, "imposta": 0.0},
                ],
            },
            processing_status="parsed",
        )
        db_session.add(inv)
        await db_session.flush()

        resp = await client.post(
            "/api/v1/fiscal/stamp-duties/check",
            json={"invoice_id": str(inv.id)},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["bollo_required"] is True
        assert data["warning"] is not None
        assert "fornitore" in data["warning"].lower() or "passiva" in data["warning"].lower()

    async def test_ac_355_active_invoice_no_warning(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-35.5: DATO fattura attiva esente >77.47, QUANDO check,
        ALLORA nessun warning (non e passiva)."""
        inv = Invoice(
            tenant_id=tenant.id,
            type="attiva",
            document_type="TD01",
            source="upload",
            numero_fattura="FT-ATT-NOWAR-001",
            emittente_piva="IT12345678901",
            emittente_nome="Fornitore Attiva",
            data_fattura=date(2026, 2, 15),
            importo_netto=100.0,
            importo_iva=0.0,
            importo_totale=100.0,
            structured_data={
                "riepilogo": [
                    {"aliquota_iva": 0.0, "imponibile": 100.0, "imposta": 0.0},
                ],
            },
            processing_status="parsed",
        )
        db_session.add(inv)
        await db_session.flush()

        resp = await client.post(
            "/api/v1/fiscal/stamp-duties/check",
            json={"invoice_id": str(inv.id)},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["bollo_required"] is True
        assert data["warning"] is None
