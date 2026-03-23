"""
Test suite for US-26: Riconciliazione fatture-movimenti
Tests for 6 Acceptance Criteria (AC-26.1 through AC-26.6)
"""

import uuid
from datetime import date, datetime, timedelta, UTC

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import (
    BankAccount, BankTransaction, Invoice, Reconciliation, Tenant,
)
from tests.conftest import create_invoice


# ============================================================
# AC-26.1 — Match automatico per importo+data+causale
# ============================================================


class TestAC261MatchAutomatico:
    """AC-26.1: Match automatico per importo+data+causale -> riconciliati."""

    async def test_ac_261_exact_match_found(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-26.1: DATO transazione con importo+data+causale matching,
        QUANDO richiedo pending, ALLORA suggerimento con confidence 0.95."""
        account = BankAccount(
            tenant_id=tenant.id,
            iban="IT60X0542811101000000RC0001",
            bank_name="Banca RC",
            provider="cbi_globe",
            balance=10000.0,
            status="connected",
        )
        db_session.add(account)
        await db_session.flush()

        # Create matching invoice and transaction
        inv = create_invoice(
            tenant_id=tenant.id,
            numero="FT-RC-001",
            piva="IT11223344556",
            nome="Fornitore Match SRL",
            importo=1000.0,
            status="parsed",
            data=date.today() - timedelta(days=2),
        )
        db_session.add(inv)
        await db_session.flush()

        tx = BankTransaction(
            bank_account_id=account.id,
            transaction_id="TX-RC-001",
            date=date.today(),
            amount=inv.importo_totale,
            direction="debit",
            counterpart="Fornitore Match SRL",
            description=f"Pagamento FT-RC-001",
        )
        db_session.add(tx)
        await db_session.flush()

        resp = await client.get(
            "/api/v1/reconciliation/pending",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        item = next(
            (i for i in data["items"] if i["bank_transaction_id"] == "TX-RC-001"),
            None,
        )
        assert item is not None
        assert len(item["suggestions"]) >= 1
        assert item["suggestions"][0]["confidence"] == 0.95

    async def test_ac_261_match_and_reconcile(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-26.1: DATO match esatto, QUANDO confermo match,
        ALLORA status 'matched' (riconciliati)."""
        account = BankAccount(
            tenant_id=tenant.id,
            iban="IT60X0542811101000000RC0002",
            bank_name="Banca RC2",
            provider="cbi_globe",
            balance=10000.0,
            status="connected",
        )
        db_session.add(account)
        await db_session.flush()

        inv = create_invoice(
            tenant_id=tenant.id,
            numero="FT-RC-002",
            importo=500.0,
            status="parsed",
            data=date.today(),
        )
        db_session.add(inv)
        await db_session.flush()

        tx = BankTransaction(
            bank_account_id=account.id,
            transaction_id="TX-RC-002",
            date=date.today(),
            amount=inv.importo_totale,
            direction="debit",
        )
        db_session.add(tx)
        await db_session.flush()

        resp = await client.post(
            f"/api/v1/reconciliation/{tx.id}/match",
            json={
                "invoice_id": str(inv.id),
                "match_type": "exact",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "matched"
        assert data["confidence"] == 0.95
        assert "riconciliata" in data["message"].lower()


# ============================================================
# AC-26.2 — Suggerimento con confidence (top 3 match)
# ============================================================


class TestAC262SuggerimentoConfidence:
    """AC-26.2: Suggerimento con confidence (top 3 match possibili)."""

    async def test_ac_262_top_3_suggestions(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-26.2: DATO transazione con piu match possibili,
        QUANDO pending, ALLORA max 3 suggerimenti ordinati per confidence."""
        account = BankAccount(
            tenant_id=tenant.id,
            iban="IT60X0542811101000000RC0003",
            bank_name="Banca RC3",
            provider="cbi_globe",
            balance=10000.0,
            status="connected",
        )
        db_session.add(account)
        await db_session.flush()

        # Create multiple invoices with similar amounts
        for i in range(5):
            inv = create_invoice(
                tenant_id=tenant.id,
                numero=f"FT-MULTI-{i:03d}",
                importo=1000.0,
                status="parsed",
                data=date.today() - timedelta(days=i),
            )
            db_session.add(inv)
        await db_session.flush()

        tx = BankTransaction(
            bank_account_id=account.id,
            transaction_id="TX-MULTI-001",
            date=date.today(),
            amount=1220.0,  # matches 1000 + 22% IVA
            direction="debit",
        )
        db_session.add(tx)
        await db_session.flush()

        resp = await client.get(
            "/api/v1/reconciliation/pending",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        item = next(
            (i for i in data["items"] if i["bank_transaction_id"] == "TX-MULTI-001"),
            None,
        )
        assert item is not None
        # Max 3 suggestions
        assert len(item["suggestions"]) <= 3
        # Ordered by confidence
        confidences = [s["confidence"] for s in item["suggestions"]]
        assert confidences == sorted(confidences, reverse=True)


# ============================================================
# AC-26.3 — Nessun match -> non riconciliati con opzioni
# ============================================================


class TestAC263NessunMatch:
    """AC-26.3: Nessun match -> 'non riconciliati' con opzioni."""

    async def test_ac_263_unmatched_transaction(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-26.3: DATO transazione senza match, QUANDO pending,
        ALLORA status 'unmatched' con suggerimenti vuoti."""
        account = BankAccount(
            tenant_id=tenant.id,
            iban="IT60X0542811101000000RC0004",
            bank_name="Banca RC4",
            provider="cbi_globe",
            balance=10000.0,
            status="connected",
        )
        db_session.add(account)
        await db_session.flush()

        tx = BankTransaction(
            bank_account_id=account.id,
            transaction_id="TX-NOMATCH-001",
            date=date.today(),
            amount=99999.99,
            direction="debit",
            counterpart="Fornitore Sconosciuto",
        )
        db_session.add(tx)
        await db_session.flush()

        resp = await client.get(
            "/api/v1/reconciliation/pending",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        item = next(
            (i for i in data["items"] if i["bank_transaction_id"] == "TX-NOMATCH-001"),
            None,
        )
        assert item is not None
        assert item["status"] == "unmatched"
        assert len(item["suggestions"]) == 0


# ============================================================
# AC-26.4 — Movimento valuta estera -> conversione BCE
# ============================================================


class TestAC264ValutaEstera:
    """AC-26.4: Movimento valuta estera -> conversione BCE."""

    async def test_ac_264_foreign_currency_conversion(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-26.4: DATO movimento in USD, QUANDO riconcilio,
        ALLORA conversione con tasso BCE."""
        account = BankAccount(
            tenant_id=tenant.id,
            iban="IT60X0542811101000000RC0005",
            bank_name="Banca RC5",
            provider="cbi_globe",
            balance=10000.0,
            status="connected",
        )
        db_session.add(account)
        await db_session.flush()

        inv = create_invoice(
            tenant_id=tenant.id,
            numero="FT-USD-001",
            importo=1000.0,
            status="parsed",
            data=date.today(),
        )
        db_session.add(inv)
        await db_session.flush()

        tx = BankTransaction(
            bank_account_id=account.id,
            transaction_id="TX-USD-001",
            date=date.today(),
            amount=1317.60,  # 1220 EUR * 1.08 USD rate
            direction="debit",
        )
        db_session.add(tx)
        await db_session.flush()

        resp = await client.post(
            f"/api/v1/reconciliation/{tx.id}/match",
            json={
                "invoice_id": str(inv.id),
                "match_type": "manual",
                "currency": "USD",
                "exchange_rate": 1.08,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "matched"

    async def test_ac_264_unsupported_currency(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-26.4: DATO valuta non supportata, QUANDO riconcilio,
        ALLORA errore."""
        account = BankAccount(
            tenant_id=tenant.id,
            iban="IT60X0542811101000000RC0006",
            bank_name="Banca RC6",
            provider="cbi_globe",
            balance=10000.0,
            status="connected",
        )
        db_session.add(account)
        await db_session.flush()

        inv = create_invoice(
            tenant_id=tenant.id,
            numero="FT-XYZ-001",
            importo=1000.0,
            status="parsed",
        )
        db_session.add(inv)
        await db_session.flush()

        tx = BankTransaction(
            bank_account_id=account.id,
            transaction_id="TX-XYZ-001",
            date=date.today(),
            amount=1000.0,
            direction="debit",
        )
        db_session.add(tx)
        await db_session.flush()

        resp = await client.post(
            f"/api/v1/reconciliation/{tx.id}/match",
            json={
                "invoice_id": str(inv.id),
                "currency": "XYZ",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 400
        assert "non supportata" in resp.json()["detail"].lower()


# ============================================================
# AC-26.5 — Pagamento parziale -> parzialmente pagata (X/Y)
# ============================================================


class TestAC265PagamentoParziale:
    """AC-26.5: Pagamento parziale -> 'parzialmente pagata (X/Y)'."""

    async def test_ac_265_partial_payment(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-26.5: DATO pagamento parziale, QUANDO riconcilio con amount,
        ALLORA status 'partial' con importo rimanente."""
        account = BankAccount(
            tenant_id=tenant.id,
            iban="IT60X0542811101000000RC0007",
            bank_name="Banca RC7",
            provider="cbi_globe",
            balance=10000.0,
            status="connected",
        )
        db_session.add(account)
        await db_session.flush()

        inv = create_invoice(
            tenant_id=tenant.id,
            numero="FT-PARTIAL-001",
            importo=1000.0,
            status="parsed",
        )
        db_session.add(inv)
        await db_session.flush()

        tx = BankTransaction(
            bank_account_id=account.id,
            transaction_id="TX-PARTIAL-001",
            date=date.today(),
            amount=500.0,
            direction="debit",
        )
        db_session.add(tx)
        await db_session.flush()

        resp = await client.post(
            f"/api/v1/reconciliation/{tx.id}/match",
            json={
                "invoice_id": str(inv.id),
                "match_type": "partial",
                "amount": 500.0,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "partial"
        assert data["amount_matched"] == 500.0
        assert data["amount_remaining"] == 720.0  # 1220 - 500
        assert "parzialmente" in data["message"].lower()


# ============================================================
# AC-26.6 — Sync concorrente -> dedup su transaction_id
# ============================================================


class TestAC266SyncConcorrente:
    """AC-26.6: Sync concorrente -> dedup su transaction_id."""

    async def test_ac_266_dedup_on_transaction_id(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-26.6: DATO riconciliazione gia esistente, QUANDO provo match duplicato,
        ALLORA errore dedup."""
        account = BankAccount(
            tenant_id=tenant.id,
            iban="IT60X0542811101000000RC0008",
            bank_name="Banca RC8",
            provider="cbi_globe",
            balance=10000.0,
            status="connected",
        )
        db_session.add(account)
        await db_session.flush()

        inv = create_invoice(
            tenant_id=tenant.id,
            numero="FT-DUP-001",
            importo=500.0,
            status="parsed",
        )
        db_session.add(inv)
        await db_session.flush()

        tx = BankTransaction(
            bank_account_id=account.id,
            transaction_id="TX-DUP-001",
            date=date.today(),
            amount=inv.importo_totale,
            direction="debit",
        )
        db_session.add(tx)
        await db_session.flush()

        # First match succeeds
        resp1 = await client.post(
            f"/api/v1/reconciliation/{tx.id}/match",
            json={"invoice_id": str(inv.id)},
            headers=auth_headers,
        )
        assert resp1.status_code == 200

        # Second match (duplicate) fails
        resp2 = await client.post(
            f"/api/v1/reconciliation/{tx.id}/match",
            json={"invoice_id": str(inv.id)},
            headers=auth_headers,
        )
        assert resp2.status_code == 400
        assert "dedup" in resp2.json()["detail"].lower() or "riconciliata" in resp2.json()["detail"].lower()
