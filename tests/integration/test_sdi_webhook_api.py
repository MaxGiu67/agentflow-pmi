"""
Test suite for US-07: Ricezione fatture SDI A-Cube
Tests for 4 Acceptance Criteria (AC-07.1 through AC-07.4)
"""

import uuid
from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import Invoice, Tenant
from tests.conftest import create_invoice


# ============================================================
# AC-07.1 — Webhook riceve fattura
# ============================================================


class TestAC071WebhookRiceveFattura:
    """AC-07.1: Webhook SDI riceve fattura e la salva."""

    async def test_ac_071_webhook_riceve_fattura(
        self, client: AsyncClient, tenant: Tenant
    ):
        """AC-07.1: DATO webhook configurato, QUANDO A-Cube invia fattura,
        ALLORA fattura salvata con source=sdi_realtime."""
        payload = {
            "id_sdi": "SDI-12345",
            "numero_fattura": "FT-SDI-001",
            "emittente_piva": "IT09876543210",
            "emittente_nome": "Fornitore SDI SRL",
            "data_fattura": "2026-01-15",
            "importo_totale": 1220.0,
            "importo_netto": 1000.0,
            "importo_iva": 220.0,
            "tipo_documento": "TD01",
        }
        response = await client.post(
            "/api/v1/webhooks/sdi",
            json=payload,
            headers={"X-Tenant-Id": str(tenant.id)},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "accepted"
        assert data["invoice_id"] is not None
        assert "salvata" in data["message"].lower() or "ricevuta" in data["message"].lower()

    async def test_ac_071_invoice_source_sdi_realtime(
        self, client: AsyncClient, tenant: Tenant, auth_headers: dict
    ):
        """AC-07.1: Verify invoice created with source=sdi_realtime appears in list."""
        # First send via webhook
        payload = {
            "id_sdi": "SDI-99999",
            "numero_fattura": "FT-SDI-CHECK",
            "emittente_piva": "IT11111111111",
            "data_fattura": "2026-02-01",
            "importo_totale": 500.0,
        }
        await client.post(
            "/api/v1/webhooks/sdi",
            json=payload,
            headers={"X-Tenant-Id": str(tenant.id)},
        )

        # Then check via invoice list
        list_resp = await client.get(
            "/api/v1/invoices?source=sdi_realtime",
            headers=auth_headers,
        )
        assert list_resp.status_code == 200
        items = list_resp.json()["items"]
        sdi_items = [i for i in items if i["source"] == "sdi_realtime"]
        assert len(sdi_items) >= 1


# ============================================================
# AC-07.2 — Webhook non raggiungibile (tenant non trovato)
# ============================================================


class TestAC072WebhookNonRaggiungibile:
    """AC-07.2: Webhook con tenant inesistente restituisce errore."""

    async def test_ac_072_tenant_non_trovato(
        self, client: AsyncClient
    ):
        """AC-07.2: DATO webhook, QUANDO tenant non esiste,
        ALLORA errore 404."""
        payload = {
            "id_sdi": "SDI-00000",
            "numero_fattura": "FT-GHOST",
            "emittente_piva": "IT00000000000",
            "data_fattura": "2026-01-01",
            "importo_totale": 100.0,
        }
        fake_tenant_id = str(uuid.uuid4())
        response = await client.post(
            "/api/v1/webhooks/sdi",
            json=payload,
            headers={"X-Tenant-Id": fake_tenant_id},
        )
        assert response.status_code == 404
        assert "tenant" in response.json()["detail"].lower()

    async def test_ac_072_tenant_id_invalido(
        self, client: AsyncClient
    ):
        """AC-07.2: DATO webhook con X-Tenant-Id invalido,
        ALLORA errore 400."""
        payload = {
            "id_sdi": "SDI-BAD",
            "numero_fattura": "FT-BAD",
            "emittente_piva": "IT00000000000",
            "data_fattura": "2026-01-01",
            "importo_totale": 100.0,
        }
        response = await client.post(
            "/api/v1/webhooks/sdi",
            json=payload,
            headers={"X-Tenant-Id": "not-a-uuid"},
        )
        assert response.status_code == 400


# ============================================================
# AC-07.3 — Fattura gia presente (dedup)
# ============================================================


class TestAC073FatturaDuplicataSDI:
    """AC-07.3: Fattura gia presente nel cassetto viene rilevata come duplicata."""

    async def test_ac_073_dedup_sdi_con_cassetto(
        self,
        client: AsyncClient,
        tenant: Tenant,
        db_session: AsyncSession,
    ):
        """AC-07.3: DATO fattura gia nel cassetto, QUANDO stessa arriva via SDI,
        ALLORA segnalata come duplicata."""
        # Pre-insert from cassetto
        existing = create_invoice(
            tenant_id=tenant.id,
            numero="FT-DEDUP-001",
            piva="IT55566677788",
            nome="Fornitore Dedup",
            source="cassetto_fiscale",
        )
        existing.data_fattura = date(2026, 3, 1)
        db_session.add(existing)
        await db_session.flush()

        # Same invoice via SDI
        payload = {
            "id_sdi": "SDI-DEDUP",
            "numero_fattura": "FT-DEDUP-001",
            "emittente_piva": "IT55566677788",
            "data_fattura": "2026-03-01",
            "importo_totale": 1220.0,
        }
        response = await client.post(
            "/api/v1/webhooks/sdi",
            json=payload,
            headers={"X-Tenant-Id": str(tenant.id)},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "duplicate"
        assert "gia presente" in data["message"].lower() or "duplicat" in data["message"].lower()


# ============================================================
# AC-07.4 — Payload corrotto
# ============================================================


class TestAC074PayloadCorrotto:
    """AC-07.4: Payload SDI incompleto o corrotto viene rifiutato."""

    async def test_ac_074_payload_senza_campi_obbligatori(
        self, client: AsyncClient, tenant: Tenant
    ):
        """AC-07.4: DATO webhook, QUANDO payload manca campi obbligatori,
        ALLORA errore 422."""
        # Missing numero_fattura, emittente_piva, etc.
        payload = {
            "id_sdi": "SDI-BROKEN",
        }
        response = await client.post(
            "/api/v1/webhooks/sdi",
            json=payload,
            headers={"X-Tenant-Id": str(tenant.id)},
        )
        assert response.status_code == 422

    async def test_ac_074_payload_json_invalido(
        self, client: AsyncClient, tenant: Tenant
    ):
        """AC-07.4: DATO webhook, QUANDO body non e JSON valido,
        ALLORA errore 422."""
        response = await client.post(
            "/api/v1/webhooks/sdi",
            content=b"not json at all",
            headers={
                "X-Tenant-Id": str(tenant.id),
                "Content-Type": "application/json",
            },
        )
        assert response.status_code == 422
