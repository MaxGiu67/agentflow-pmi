"""
Test suite for US-21: Fatturazione attiva SDI via A-Cube
Tests for 5 Acceptance Criteria (AC-21.1 through AC-21.5)
"""

import uuid
from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import ActiveInvoice, Tenant, User


# ============================================================
# AC-21.1 — Compila fattura, genera XML, invia a SDI, stato real-time
# ============================================================


class TestAC211CompilaFatturaInviaSDI:
    """AC-21.1: Compila fattura (cliente, importo, IVA) -> genera XML FatturaPA
    -> invia ad A-Cube -> stato real-time."""

    async def test_ac_211_create_active_invoice(
        self, client: AsyncClient, auth_headers: dict
    ):
        """AC-21.1: DATO utente autenticato, QUANDO compila fattura attiva,
        ALLORA genera XML FatturaPA e salva in bozza."""
        payload = {
            "cliente_piva": "IT09876543210",
            "cliente_nome": "Cliente Test SRL",
            "data_fattura": "2026-03-15",
            "importo_netto": 1000.0,
            "aliquota_iva": 22.0,
            "descrizione": "Consulenza informatica",
        }
        response = await client.post(
            "/api/v1/invoices/active",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["cliente_piva"] == "IT09876543210"
        assert data["importo_netto"] == 1000.0
        assert data["importo_iva"] == 220.0
        assert data["importo_totale"] == 1220.0
        assert data["sdi_status"] == "draft"
        assert data["raw_xml"] is not None
        assert "FatturaElettronica" in data["raw_xml"]
        assert data["numero_fattura"].startswith("FTA-2026-")

    async def test_ac_211_send_to_sdi(
        self, client: AsyncClient, auth_headers: dict
    ):
        """AC-21.1: DATO fattura in bozza, QUANDO invio a SDI,
        ALLORA stato cambia a 'sent' con sdi_id."""
        # Create invoice
        create_resp = await client.post(
            "/api/v1/invoices/active",
            json={
                "cliente_piva": "IT11223344556",
                "cliente_nome": "Altro Cliente SRL",
                "data_fattura": "2026-03-20",
                "importo_netto": 500.0,
            },
            headers=auth_headers,
        )
        assert create_resp.status_code == 201
        invoice_id = create_resp.json()["id"]

        # Send to SDI
        send_resp = await client.post(
            f"/api/v1/invoices/active/{invoice_id}/send",
            headers=auth_headers,
        )
        assert send_resp.status_code == 200
        data = send_resp.json()
        assert data["sdi_status"] == "sent"
        assert data["sdi_id"] is not None
        assert data["sdi_id"].startswith("SDI-")

    async def test_ac_211_status_realtime(
        self, client: AsyncClient, auth_headers: dict
    ):
        """AC-21.1: DATO fattura inviata, QUANDO controllo stato,
        ALLORA vedo stato aggiornato in real-time."""
        # Create and send
        create_resp = await client.post(
            "/api/v1/invoices/active",
            json={
                "cliente_piva": "IT55566677788",
                "cliente_nome": "Status Test SRL",
                "data_fattura": "2026-03-22",
                "importo_netto": 750.0,
            },
            headers=auth_headers,
        )
        invoice_id = create_resp.json()["id"]
        await client.post(
            f"/api/v1/invoices/active/{invoice_id}/send",
            headers=auth_headers,
        )

        # Check status
        status_resp = await client.get(
            f"/api/v1/invoices/active/{invoice_id}/status",
            headers=auth_headers,
        )
        assert status_resp.status_code == 200
        data = status_resp.json()
        assert data["sdi_status"] in ("sent", "delivered")
        assert data["sdi_id"] is not None

    async def test_ac_211_xml_contains_fatturapa_elements(
        self, client: AsyncClient, auth_headers: dict
    ):
        """AC-21.1: L'XML generato contiene gli elementi FatturaPA obbligatori."""
        resp = await client.post(
            "/api/v1/invoices/active",
            json={
                "cliente_piva": "IT99887766554",
                "cliente_nome": "XML Test SRL",
                "data_fattura": "2026-01-10",
                "importo_netto": 2000.0,
                "aliquota_iva": 22.0,
            },
            headers=auth_headers,
        )
        xml = resp.json()["raw_xml"]
        assert "<TipoDocumento>TD01</TipoDocumento>" in xml
        assert "<CedentePrestatore>" in xml
        assert "<CessionarioCommittente>" in xml
        assert "<DatiBeniServizi>" in xml
        assert "<ImponibileImporto>2000.00</ImponibileImporto>" in xml
        assert "<Imposta>440.00</Imposta>" in xml


# ============================================================
# AC-21.2 — Rifiuto SDI: mostra "Rifiutata" con motivazione
# ============================================================


class TestAC212RifiutoSDI:
    """AC-21.2: Rifiuto SDI -> mostra 'Rifiutata' con motivazione,
    permette correzione/reinvio."""

    async def test_ac_212_rifiuto_sdi_mostra_motivazione(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        tenant: Tenant,
    ):
        """AC-21.2: DATO fattura inviata, QUANDO SDI la rifiuta,
        ALLORA stato='rejected' con motivazione visibile."""
        # Create a rejected invoice directly in DB
        invoice = ActiveInvoice(
            tenant_id=tenant.id,
            numero_fattura="FTA-2026-REJECT",
            document_type="TD01",
            cliente_piva="IT11111111111",
            cliente_nome="Rifiuto Test SRL",
            data_fattura=date(2026, 3, 1),
            importo_netto=1000.0,
            aliquota_iva=22.0,
            importo_iva=220.0,
            importo_totale=1220.0,
            sdi_status="rejected",
            sdi_id="SDI-REJECTED-001",
            sdi_reject_reason="Codice destinatario non valido",
            raw_xml="<test/>",
        )
        db_session.add(invoice)
        await db_session.flush()

        # Check status
        status_resp = await client.get(
            f"/api/v1/invoices/active/{invoice.id}/status",
            headers=auth_headers,
        )
        assert status_resp.status_code == 200
        data = status_resp.json()
        assert data["sdi_status"] == "rejected"
        assert "rifiutata" in data["message"].lower() or "rejected" in data["sdi_status"].lower()
        assert data["sdi_reject_reason"] is not None

    async def test_ac_212_reinvio_dopo_rifiuto(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        tenant: Tenant,
    ):
        """AC-21.2: DATO fattura rifiutata, QUANDO reinvio,
        ALLORA stato torna a 'sent' (correzione permessa)."""
        invoice = ActiveInvoice(
            tenant_id=tenant.id,
            numero_fattura="FTA-2026-RESEND",
            document_type="TD01",
            cliente_piva="IT22222222222",
            cliente_nome="Reinvio Test SRL",
            data_fattura=date(2026, 3, 5),
            importo_netto=800.0,
            aliquota_iva=22.0,
            importo_iva=176.0,
            importo_totale=976.0,
            sdi_status="rejected",
            sdi_id="SDI-OLD",
            sdi_reject_reason="Errore formato",
            raw_xml="<test/>",
        )
        db_session.add(invoice)
        await db_session.flush()

        # Re-send
        send_resp = await client.post(
            f"/api/v1/invoices/active/{invoice.id}/send",
            headers=auth_headers,
        )
        assert send_resp.status_code == 200
        data = send_resp.json()
        assert data["sdi_status"] == "sent"
        assert data["sdi_id"].startswith("SDI-")


# ============================================================
# AC-21.3 — Numero fattura duplicato: blocca con suggerimento
# ============================================================


class TestAC213NumeroFatturaDuplicato:
    """AC-21.3: Numero fattura duplicato -> blocca con suggerimento
    prossimo disponibile."""

    async def test_ac_213_numero_progressivo_auto(
        self, client: AsyncClient, auth_headers: dict
    ):
        """AC-21.3: DATO fattura creata, QUANDO creo seconda fattura stessa anno,
        ALLORA numero progressivo incrementa automaticamente."""
        base_payload = {
            "cliente_piva": "IT33344455566",
            "cliente_nome": "Progressivo Test SRL",
            "data_fattura": "2026-06-01",
            "importo_netto": 100.0,
        }

        resp1 = await client.post(
            "/api/v1/invoices/active",
            json=base_payload,
            headers=auth_headers,
        )
        assert resp1.status_code == 201
        num1 = resp1.json()["numero_fattura"]

        resp2 = await client.post(
            "/api/v1/invoices/active",
            json={**base_payload, "importo_netto": 200.0},
            headers=auth_headers,
        )
        assert resp2.status_code == 201
        num2 = resp2.json()["numero_fattura"]

        # Both should be in 2026 series, second should be higher
        assert num1.startswith("FTA-2026-")
        assert num2.startswith("FTA-2026-")
        assert num2 > num1

    async def test_ac_213_dedup_across_invoices(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        tenant: Tenant,
    ):
        """AC-21.3: DATO fattura con certo numero, QUANDO creo nuova,
        ALLORA numero non duplica mai (auto-increment)."""
        # Pre-insert an invoice with specific number
        existing = ActiveInvoice(
            tenant_id=tenant.id,
            numero_fattura="FTA-2026-0001",
            document_type="TD01",
            cliente_piva="IT44455566677",
            cliente_nome="Existing SRL",
            data_fattura=date(2026, 1, 1),
            importo_netto=100.0,
            aliquota_iva=22.0,
            importo_iva=22.0,
            importo_totale=122.0,
            sdi_status="draft",
        )
        db_session.add(existing)
        await db_session.flush()

        # Create new invoice for same year
        resp = await client.post(
            "/api/v1/invoices/active",
            json={
                "cliente_piva": "IT55566677788",
                "cliente_nome": "New SRL",
                "data_fattura": "2026-02-01",
                "importo_netto": 300.0,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        new_num = resp.json()["numero_fattura"]
        # Should be 0002 or higher
        assert new_num != "FTA-2026-0001"
        assert "FTA-2026-" in new_num


# ============================================================
# AC-21.4 — Importo zero/negativo: errore "usa nota di credito"
# ============================================================


class TestAC214ImportoZeroNegativo:
    """AC-21.4: Importo zero/negativo -> errore 'usa nota di credito'."""

    async def test_ac_214_importo_zero_rifiutato(
        self, client: AsyncClient, auth_headers: dict
    ):
        """AC-21.4: DATO importo zero, QUANDO creo fattura,
        ALLORA errore con suggerimento nota di credito."""
        resp = await client.post(
            "/api/v1/invoices/active",
            json={
                "cliente_piva": "IT00000000001",
                "cliente_nome": "Zero Test",
                "data_fattura": "2026-01-01",
                "importo_netto": 0,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        # Check that somewhere in the error there's mention of nota di credito
        detail_str = str(detail).lower()
        assert "nota di credito" in detail_str or "positivo" in detail_str

    async def test_ac_214_importo_negativo_rifiutato(
        self, client: AsyncClient, auth_headers: dict
    ):
        """AC-21.4: DATO importo negativo, QUANDO creo fattura,
        ALLORA errore con suggerimento nota di credito."""
        resp = await client.post(
            "/api/v1/invoices/active",
            json={
                "cliente_piva": "IT00000000002",
                "cliente_nome": "Negative Test",
                "data_fattura": "2026-01-01",
                "importo_netto": -500.0,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 422
        detail_str = str(resp.json()["detail"]).lower()
        assert "nota di credito" in detail_str or "positivo" in detail_str


# ============================================================
# AC-21.5 — Nota di credito TD04 con riferimento fattura originale
# ============================================================


class TestAC215NotaDiCredito:
    """AC-21.5: Nota di credito -> genera XML TD04 con riferimento
    fattura originale."""

    async def test_ac_215_create_nota_credito(
        self, client: AsyncClient, auth_headers: dict
    ):
        """AC-21.5: DATO fattura originale, QUANDO creo nota di credito,
        ALLORA XML con TD04 e riferimento fattura originale."""
        # First create the original invoice
        orig_resp = await client.post(
            "/api/v1/invoices/active",
            json={
                "cliente_piva": "IT77788899900",
                "cliente_nome": "NC Test SRL",
                "data_fattura": "2026-02-01",
                "importo_netto": 1000.0,
            },
            headers=auth_headers,
        )
        assert orig_resp.status_code == 201
        orig_id = orig_resp.json()["id"]
        orig_numero = orig_resp.json()["numero_fattura"]

        # Create credit note referencing original
        nc_resp = await client.post(
            "/api/v1/invoices/active",
            json={
                "cliente_piva": "IT77788899900",
                "cliente_nome": "NC Test SRL",
                "data_fattura": "2026-03-01",
                "importo_netto": 200.0,
                "document_type": "TD04",
                "original_invoice_id": orig_id,
                "original_invoice_numero": orig_numero,
                "original_invoice_date": "2026-02-01",
            },
            headers=auth_headers,
        )
        assert nc_resp.status_code == 201
        data = nc_resp.json()
        assert data["document_type"] == "TD04"
        assert data["original_invoice_id"] == orig_id
        assert data["original_invoice_numero"] == orig_numero

        # Check XML has TD04 and DatiFattureCollegate
        xml = data["raw_xml"]
        assert "<TipoDocumento>TD04</TipoDocumento>" in xml
        assert "<DatiFattureCollegate>" in xml
        assert f"<IdDocumento>{orig_numero}</IdDocumento>" in xml

    async def test_ac_215_nc_numero_progressivo_separato(
        self, client: AsyncClient, auth_headers: dict
    ):
        """AC-21.5: Le note di credito hanno numerazione separata (NC-)."""
        nc_resp = await client.post(
            "/api/v1/invoices/active",
            json={
                "cliente_piva": "IT88899900011",
                "cliente_nome": "NC Numbering SRL",
                "data_fattura": "2026-04-01",
                "importo_netto": 100.0,
                "document_type": "TD04",
                "original_invoice_numero": "FTA-2026-0001",
                "original_invoice_date": "2026-03-01",
            },
            headers=auth_headers,
        )
        assert nc_resp.status_code == 201
        assert nc_resp.json()["numero_fattura"].startswith("NC-2026-")
