"""
Test suite for US-27: Pagamenti fornitori via PISP
Tests for 4 Acceptance Criteria (AC-27.1 through AC-27.4)
"""

import uuid
from datetime import date, datetime, timedelta, UTC

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import BankAccount, Invoice, Tenant


# ============================================================
# AC-27.1 — Pagamento con SCA -> registra uscita, riconcilia
# ============================================================


class TestAC271PagamentoSCA:
    """AC-27.1: Pagamento con SCA -> via A-Cube PISP, registra uscita, riconcilia."""

    async def test_ac_271_single_payment_success(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-27.1: DATO fattura e conto con fondi,
        QUANDO POST /payments/execute,
        ALLORA pagamento eseguito, uscita registrata, riconciliato."""
        # Create bank account with balance
        account = BankAccount(
            tenant_id=tenant.id,
            iban="IT60X0542811101000000123456",
            bank_name="Test Bank",
            provider="cbi_globe",
            balance=10000.0,
            status="connected",
        )
        db_session.add(account)
        await db_session.flush()

        # Create invoice
        inv = Invoice(
            tenant_id=tenant.id,
            type="passiva",
            document_type="TD01",
            source="upload",
            numero_fattura="FT-PAY-001",
            emittente_piva="IT01234567890",
            emittente_nome="Fornitore Alpha SRL",
            data_fattura=date(2025, 1, 15),
            importo_netto=1000.0,
            importo_iva=220.0,
            importo_totale=1220.0,
            processing_status="parsed",
        )
        db_session.add(inv)
        await db_session.flush()

        resp = await client.post(
            "/api/v1/payments/execute",
            json={
                "bank_account_id": str(account.id),
                "invoice_id": str(inv.id),
                "beneficiary_name": "Fornitore Alpha SRL",
                "beneficiary_iban": "IT60X0542811101000000123456",
                "amount": 1220.0,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["sca_status"] == "completed"
        assert data["reconciled"] is True
        assert data["amount"] == 1220.0
        assert data["payment_type"] == "single"

    async def test_ac_271_payment_reduces_balance(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-27.1: DATO pagamento eseguito,
        QUANDO controlla saldo, ALLORA ridotto dell'importo."""
        account = BankAccount(
            tenant_id=tenant.id,
            iban="IT60X0542811101000000123456",
            bank_name="Test Bank",
            provider="cbi_globe",
            balance=5000.0,
            status="connected",
        )
        db_session.add(account)
        await db_session.flush()

        inv = Invoice(
            tenant_id=tenant.id,
            type="passiva",
            document_type="TD01",
            source="upload",
            numero_fattura="FT-BAL-001",
            emittente_piva="IT01234567890",
            emittente_nome="Fornitore Balance",
            data_fattura=date(2025, 2, 15),
            importo_netto=1000.0,
            importo_iva=220.0,
            importo_totale=1220.0,
            processing_status="parsed",
        )
        db_session.add(inv)
        await db_session.flush()

        await client.post(
            "/api/v1/payments/execute",
            json={
                "bank_account_id": str(account.id),
                "invoice_id": str(inv.id),
                "beneficiary_name": "Fornitore Balance",
                "beneficiary_iban": "IT60X0542811101000000123456",
                "amount": 1220.0,
            },
            headers=auth_headers,
        )

        # Check balance was reduced
        await db_session.refresh(account)
        assert account.balance == 3780.0  # 5000 - 1220


# ============================================================
# AC-27.2 — Fondi insufficienti -> errore con saldo
# ============================================================


class TestAC272FondiInsufficienti:
    """AC-27.2: Fondi insufficienti -> errore con saldo."""

    async def test_ac_272_insufficient_funds_error(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-27.2: DATO saldo insufficiente,
        QUANDO execute payment, ALLORA errore con saldo disponibile."""
        account = BankAccount(
            tenant_id=tenant.id,
            iban="IT60X0542811101000000123456",
            bank_name="Test Bank",
            provider="cbi_globe",
            balance=500.0,  # Low balance
            status="connected",
        )
        db_session.add(account)
        await db_session.flush()

        inv = Invoice(
            tenant_id=tenant.id,
            type="passiva",
            document_type="TD01",
            source="upload",
            numero_fattura="FT-LOW-001",
            emittente_piva="IT01234567890",
            emittente_nome="Fornitore Low",
            data_fattura=date(2025, 3, 15),
            importo_netto=1000.0,
            importo_iva=220.0,
            importo_totale=1220.0,
            processing_status="parsed",
        )
        db_session.add(inv)
        await db_session.flush()

        resp = await client.post(
            "/api/v1/payments/execute",
            json={
                "bank_account_id": str(account.id),
                "invoice_id": str(inv.id),
                "beneficiary_name": "Fornitore Low",
                "beneficiary_iban": "IT60X0542811101000000123456",
                "amount": 1220.0,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["error"] == "fondi_insufficienti"
        assert data["saldo_disponibile"] == 500.0
        assert "500.00" in data["detail"]


# ============================================================
# AC-27.3 — IBAN non valido -> errore validazione
# ============================================================


class TestAC273IBANNonValido:
    """AC-27.3: IBAN non valido -> errore validazione."""

    async def test_ac_273_invalid_iban_error(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-27.3: DATO IBAN malformato,
        QUANDO execute payment, ALLORA errore validazione IBAN."""
        account = BankAccount(
            tenant_id=tenant.id,
            iban="IT60X0542811101000000123456",
            bank_name="Test Bank",
            provider="cbi_globe",
            balance=10000.0,
            status="connected",
        )
        db_session.add(account)
        await db_session.flush()

        inv = Invoice(
            tenant_id=tenant.id,
            type="passiva",
            document_type="TD01",
            source="upload",
            numero_fattura="FT-IBAN-001",
            emittente_piva="IT01234567890",
            emittente_nome="Fornitore IBAN",
            data_fattura=date(2025, 4, 15),
            importo_netto=1000.0,
            importo_iva=220.0,
            importo_totale=1220.0,
            processing_status="parsed",
        )
        db_session.add(inv)
        await db_session.flush()

        resp = await client.post(
            "/api/v1/payments/execute",
            json={
                "bank_account_id": str(account.id),
                "invoice_id": str(inv.id),
                "beneficiary_name": "Fornitore IBAN",
                "beneficiary_iban": "INVALID_IBAN_123",
                "amount": 1220.0,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 400
        assert "IBAN non valido" in resp.json()["detail"]

    async def test_ac_273_valid_iban_passes(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-27.3: DATO IBAN valido,
        QUANDO execute payment, ALLORA pagamento procede."""
        account = BankAccount(
            tenant_id=tenant.id,
            iban="IT60X0542811101000000123456",
            bank_name="Test Bank",
            provider="cbi_globe",
            balance=10000.0,
            status="connected",
        )
        db_session.add(account)
        await db_session.flush()

        inv = Invoice(
            tenant_id=tenant.id,
            type="passiva",
            document_type="TD01",
            source="upload",
            numero_fattura="FT-VALID-001",
            emittente_piva="IT01234567890",
            emittente_nome="Fornitore Valid",
            data_fattura=date(2025, 5, 15),
            importo_netto=1000.0,
            importo_iva=220.0,
            importo_totale=1220.0,
            processing_status="parsed",
        )
        db_session.add(inv)
        await db_session.flush()

        resp = await client.post(
            "/api/v1/payments/execute",
            json={
                "bank_account_id": str(account.id),
                "invoice_id": str(inv.id),
                "beneficiary_name": "Fornitore Valid",
                "beneficiary_iban": "IT60X0542811101000000123456",
                "amount": 1220.0,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "error" not in data


# ============================================================
# AC-27.4 — Pagamento batch -> bonifico cumulativo con causale
# ============================================================


class TestAC274PagamentoBatch:
    """AC-27.4: Pagamento batch -> bonifico cumulativo con causale che elenca numeri fattura."""

    async def test_ac_274_batch_payment_cumulative(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-27.4: DATO multiple fatture stesso fornitore,
        QUANDO POST /payments/batch,
        ALLORA bonifico cumulativo con causale elencante numeri fattura."""
        account = BankAccount(
            tenant_id=tenant.id,
            iban="IT60X0542811101000000123456",
            bank_name="Test Bank",
            provider="cbi_globe",
            balance=50000.0,
            status="connected",
        )
        db_session.add(account)
        await db_session.flush()

        # Create multiple invoices
        inv1 = Invoice(
            tenant_id=tenant.id,
            type="passiva",
            document_type="TD01",
            source="upload",
            numero_fattura="FT-BATCH-001",
            emittente_piva="IT01234567890",
            emittente_nome="Fornitore Batch",
            data_fattura=date(2025, 6, 15),
            importo_netto=1000.0,
            importo_iva=220.0,
            importo_totale=1220.0,
            processing_status="parsed",
        )
        inv2 = Invoice(
            tenant_id=tenant.id,
            type="passiva",
            document_type="TD01",
            source="upload",
            numero_fattura="FT-BATCH-002",
            emittente_piva="IT01234567890",
            emittente_nome="Fornitore Batch",
            data_fattura=date(2025, 7, 20),
            importo_netto=2000.0,
            importo_iva=440.0,
            importo_totale=2440.0,
            processing_status="parsed",
        )
        inv3 = Invoice(
            tenant_id=tenant.id,
            type="passiva",
            document_type="TD01",
            source="upload",
            numero_fattura="FT-BATCH-003",
            emittente_piva="IT01234567890",
            emittente_nome="Fornitore Batch",
            data_fattura=date(2025, 8, 10),
            importo_netto=500.0,
            importo_iva=110.0,
            importo_totale=610.0,
            processing_status="parsed",
        )
        db_session.add(inv1)
        db_session.add(inv2)
        db_session.add(inv3)
        await db_session.flush()

        resp = await client.post(
            "/api/v1/payments/batch",
            json={
                "bank_account_id": str(account.id),
                "beneficiary_name": "Fornitore Batch",
                "beneficiary_iban": "IT60X0542811101000000123456",
                "invoice_ids": [str(inv1.id), str(inv2.id), str(inv3.id)],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["invoice_count"] == 3
        assert data["total_amount"] == 4270.0  # 1220 + 2440 + 610

        # Causale should list all invoice numbers
        causale = data["causale"]
        assert "FT-BATCH-001" in causale
        assert "FT-BATCH-002" in causale
        assert "FT-BATCH-003" in causale

        # Payment should be reconciled
        assert data["payment"]["reconciled"] is True
        assert data["payment"]["payment_type"] == "batch"

    async def test_ac_274_batch_insufficient_funds(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-27.4: DATO batch con importo superiore al saldo,
        QUANDO batch payment, ALLORA errore fondi insufficienti."""
        account = BankAccount(
            tenant_id=tenant.id,
            iban="IT60X0542811101000000123456",
            bank_name="Test Bank",
            provider="cbi_globe",
            balance=1000.0,  # Not enough for batch
            status="connected",
        )
        db_session.add(account)
        await db_session.flush()

        inv1 = Invoice(
            tenant_id=tenant.id,
            type="passiva",
            document_type="TD01",
            source="upload",
            numero_fattura="FT-BATCHLOW-001",
            emittente_piva="IT01234567890",
            emittente_nome="Fornitore BatchLow",
            data_fattura=date(2025, 9, 15),
            importo_netto=1000.0,
            importo_iva=220.0,
            importo_totale=1220.0,
            processing_status="parsed",
        )
        inv2 = Invoice(
            tenant_id=tenant.id,
            type="passiva",
            document_type="TD01",
            source="upload",
            numero_fattura="FT-BATCHLOW-002",
            emittente_piva="IT01234567890",
            emittente_nome="Fornitore BatchLow",
            data_fattura=date(2025, 10, 20),
            importo_netto=2000.0,
            importo_iva=440.0,
            importo_totale=2440.0,
            processing_status="parsed",
        )
        db_session.add(inv1)
        db_session.add(inv2)
        await db_session.flush()

        resp = await client.post(
            "/api/v1/payments/batch",
            json={
                "bank_account_id": str(account.id),
                "beneficiary_name": "Fornitore BatchLow",
                "beneficiary_iban": "IT60X0542811101000000123456",
                "invoice_ids": [str(inv1.id), str(inv2.id)],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["error"] == "fondi_insufficienti"
        assert data["saldo_disponibile"] == 1000.0
