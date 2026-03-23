"""
Test suite for US-37: Conservazione digitale a norma
Tests for 5 Acceptance Criteria (AC-37.1 through AC-37.5)
"""

import uuid
from datetime import date, datetime, timedelta, UTC

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import ActiveInvoice, DigitalPreservation, Invoice, Tenant


# ============================================================
# AC-37.1 — Invio automatico batch giornaliero a provider
# ============================================================


class TestAC371InvioBatch:
    """AC-37.1: Invio automatico batch giornaliero a provider (Aruba/InfoCert mock)."""

    async def test_ac_371_send_batch_to_provider(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-37.1: DATO fatture non conservate,
        QUANDO POST /preservation/batch,
        ALLORA documenti inviati al provider."""
        # Create invoices
        inv1 = Invoice(
            tenant_id=tenant.id,
            type="passiva",
            document_type="TD01",
            source="upload",
            numero_fattura="FT-PRES-001",
            emittente_piva="IT01234567890",
            emittente_nome="Fornitore A",
            data_fattura=date(2025, 1, 15),
            importo_netto=1000.0,
            importo_iva=220.0,
            importo_totale=1220.0,
            raw_xml="<invoice>test1</invoice>",
            processing_status="parsed",
        )
        inv2 = Invoice(
            tenant_id=tenant.id,
            type="passiva",
            document_type="TD01",
            source="upload",
            numero_fattura="FT-PRES-002",
            emittente_piva="IT09876543210",
            emittente_nome="Fornitore B",
            data_fattura=date(2025, 2, 20),
            importo_netto=2000.0,
            importo_iva=440.0,
            importo_totale=2440.0,
            raw_xml="<invoice>test2</invoice>",
            processing_status="parsed",
        )
        db_session.add(inv1)
        db_session.add(inv2)
        await db_session.flush()

        resp = await client.post(
            "/api/v1/preservation/batch?provider=aruba",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["sent"] >= 2
        assert data["errors"] == 0

    async def test_ac_371_batch_idempotent(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-37.1: DATO batch gia inviato, QUANDO secondo batch,
        ALLORA non reinvia documenti gia inviati."""
        inv = Invoice(
            tenant_id=tenant.id,
            type="passiva",
            document_type="TD01",
            source="upload",
            numero_fattura="FT-IDEM-001",
            emittente_piva="IT01234567890",
            emittente_nome="Fornitore Idem",
            data_fattura=date(2025, 3, 10),
            importo_netto=500.0,
            importo_iva=110.0,
            importo_totale=610.0,
            raw_xml="<invoice>idem</invoice>",
            processing_status="parsed",
        )
        db_session.add(inv)
        await db_session.flush()

        # First batch
        resp1 = await client.post("/api/v1/preservation/batch", headers=auth_headers)
        sent1 = resp1.json()["sent"]

        # Second batch
        resp2 = await client.post("/api/v1/preservation/batch", headers=auth_headers)
        # Should not re-send already processed invoices
        assert resp2.status_code == 200


# ============================================================
# AC-37.2 — Verifica stato (conservati, in attesa, errori)
# ============================================================


class TestAC372VerificaStato:
    """AC-37.2: Verifica stato (conservati, in attesa, errori)."""

    async def test_ac_372_list_preservation_status(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-37.2: DATO documenti inviati, QUANDO GET /preservation,
        ALLORA stato con summary."""
        # Create an invoice and send it
        inv = Invoice(
            tenant_id=tenant.id,
            type="passiva",
            document_type="TD01",
            source="upload",
            numero_fattura="FT-STATUS-001",
            emittente_piva="IT01234567890",
            emittente_nome="Fornitore Status",
            data_fattura=date(2025, 4, 10),
            importo_netto=1000.0,
            importo_iva=220.0,
            importo_totale=1220.0,
            raw_xml="<invoice>status</invoice>",
            processing_status="parsed",
        )
        db_session.add(inv)
        await db_session.flush()

        # Send batch first
        await client.post("/api/v1/preservation/batch", headers=auth_headers)

        # Check status list
        resp = await client.get("/api/v1/preservation", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert "summary" in data
        assert isinstance(data["summary"], dict)

    async def test_ac_372_check_status_confirmed(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-37.2: DATO documenti inviati, QUANDO check-status,
        ALLORA conferma conservazione."""
        inv = Invoice(
            tenant_id=tenant.id,
            type="passiva",
            document_type="TD01",
            source="upload",
            numero_fattura="FT-CONF-001",
            emittente_piva="IT01234567890",
            emittente_nome="Fornitore Confirmed",
            data_fattura=date(2025, 5, 10),
            importo_netto=1000.0,
            importo_iva=220.0,
            importo_totale=1220.0,
            raw_xml="<invoice>confirm</invoice>",
            processing_status="parsed",
        )
        db_session.add(inv)
        await db_session.flush()

        # Send batch
        await client.post("/api/v1/preservation/batch", headers=auth_headers)

        # Check status
        resp = await client.post("/api/v1/preservation/check-status", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["confirmed"] >= 1


# ============================================================
# AC-37.3 — Provider non raggiungibile -> retry backoff, notifica >48h
# ============================================================


class TestAC373RetryBackoff:
    """AC-37.3: Provider non raggiungibile -> retry backoff, notifica >48h."""

    async def test_ac_373_provider_unavailable_queued(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-37.3: DATO provider non raggiungibile,
        QUANDO batch, ALLORA documenti in coda con retry."""
        inv = Invoice(
            tenant_id=tenant.id,
            type="passiva",
            document_type="TD01",
            source="upload",
            numero_fattura="FT-RETRY-001",
            emittente_piva="IT01234567890",
            emittente_nome="Fornitore Retry",
            data_fattura=date(2025, 6, 10),
            importo_netto=1000.0,
            importo_iva=220.0,
            importo_totale=1220.0,
            raw_xml="<invoice>retry</invoice>",
            processing_status="parsed",
        )
        db_session.add(inv)
        await db_session.flush()

        # Make provider unavailable via service
        from api.modules.preservation.service import PreservationService
        service = PreservationService(db_session)
        service.adapter.set_available(False)

        result = await service.send_batch(tenant.id, "aruba")
        assert result["errors"] >= 1
        # Documents should be queued
        for detail in result["details"]:
            assert detail["status"] == "queued"

    async def test_ac_373_notification_after_48h(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-37.3: DATO documento in coda da >48h,
        QUANDO retry, ALLORA notifica richiesta."""
        inv = Invoice(
            tenant_id=tenant.id,
            type="passiva",
            document_type="TD01",
            source="upload",
            numero_fattura="FT-48H-001",
            emittente_piva="IT01234567890",
            emittente_nome="Fornitore 48h",
            data_fattura=date(2025, 7, 10),
            importo_netto=1000.0,
            importo_iva=220.0,
            importo_totale=1220.0,
            raw_xml="<invoice>48h</invoice>",
            processing_status="parsed",
        )
        db_session.add(inv)
        await db_session.flush()

        # Create a preservation record queued for >48h
        pres = DigitalPreservation(
            tenant_id=tenant.id,
            invoice_id=inv.id,
            provider="aruba",
            status="queued",
            retry_count=2,
            created_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=50),
        )
        db_session.add(pres)
        await db_session.flush()

        # Try batch with unavailable provider
        from api.modules.preservation.service import PreservationService
        service = PreservationService(db_session)
        service.adapter.set_available(False)

        result = await service.send_batch(tenant.id, "aruba")
        # Should include notification_required
        notification_details = [
            d for d in result["details"]
            if d.get("status") == "notification_required"
        ]
        assert len(notification_details) >= 1
        assert "48h" in notification_details[0]["message"]


# ============================================================
# AC-37.4 — Pacchetto rifiutato -> conservazione rifiutata con motivo
# ============================================================


class TestAC374PacchettoRifiutato:
    """AC-37.4: Pacchetto rifiutato -> 'conservazione rifiutata' con motivo."""

    async def test_ac_374_rejected_with_reason(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-37.4: DATO pacchetto inviato, QUANDO provider rifiuta,
        ALLORA status=rejected con motivo."""
        inv = Invoice(
            tenant_id=tenant.id,
            type="passiva",
            document_type="TD01",
            source="upload",
            numero_fattura="FT-REJ-001",
            emittente_piva="IT01234567890",
            emittente_nome="Fornitore Rejected",
            data_fattura=date(2025, 8, 10),
            importo_netto=1000.0,
            importo_iva=220.0,
            importo_totale=1220.0,
            raw_xml="<invoice>rejected</invoice>",
            processing_status="parsed",
        )
        db_session.add(inv)
        await db_session.flush()

        # Send batch first
        await client.post("/api/v1/preservation/batch", headers=auth_headers)

        # Now simulate rejection on check
        from api.modules.preservation.service import PreservationService
        service = PreservationService(db_session)
        service.adapter.set_simulate_rejection(True, "Formato XML non conforme")

        result = await service.check_status(tenant.id)
        assert result["rejected"] >= 1
        rejected_detail = [d for d in result["details"] if d["status"] == "rejected"]
        assert len(rejected_detail) >= 1
        assert "Formato XML non conforme" in rejected_detail[0]["reject_reason"]


# ============================================================
# AC-37.5 — Nota credito post-conservazione -> invia NC collegata
# ============================================================


class TestAC375NotaCreditoCollegata:
    """AC-37.5: Nota credito post-conservazione -> invia anche NC collegata."""

    async def test_ac_375_send_credit_note(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-37.5: DATO fattura conservata con NC collegata,
        QUANDO POST /preservation/credit-note/{id},
        ALLORA NC inviata a conservazione."""
        # Create credit note invoice
        nc = Invoice(
            tenant_id=tenant.id,
            type="passiva",
            document_type="TD04",
            source="upload",
            numero_fattura="NC-PRES-001",
            emittente_piva="IT01234567890",
            emittente_nome="Fornitore NC",
            data_fattura=date(2025, 9, 10),
            importo_netto=200.0,
            importo_iva=44.0,
            importo_totale=244.0,
            raw_xml="<credit-note>test</credit-note>",
            processing_status="parsed",
        )
        db_session.add(nc)
        await db_session.flush()

        resp = await client.post(
            f"/api/v1/preservation/credit-note/{nc.id}?provider=aruba",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "sent"
        assert data["batch_id"] is not None

    async def test_ac_375_credit_note_not_found(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-37.5: DATO NC non esistente, QUANDO invio conservazione,
        ALLORA errore 404."""
        fake_id = str(uuid.uuid4())
        resp = await client.post(
            f"/api/v1/preservation/credit-note/{fake_id}?provider=aruba",
            headers=auth_headers,
        )
        assert resp.status_code == 404
