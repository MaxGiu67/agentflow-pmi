"""
Test suite for US-13: Registrazione automatica scritture partita doppia
Tests for 6 Acceptance Criteria (AC-13.1 through AC-13.6)
"""

import uuid
from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.agents.conta_agent import ContaAgent, ACCOUNT_MAPPINGS
from api.agents.base_agent import event_bus
from api.db.models import Invoice, JournalEntry, JournalLine, Tenant
from tests.conftest import create_invoice


# ============================================================
# AC-13.1 — Fattura passiva → DARE conto spesa + DARE IVA + AVERE Fornitori
# ============================================================


class TestAC131RegistrazioneFatturaPassiva:
    """AC-13.1: Fattura passiva crea scrittura DARE spesa + DARE IVA + AVERE Fornitori."""

    async def test_ac_131_registrazione_fattura_passiva(
        self,
        db_session: AsyncSession,
        tenant: Tenant,
    ):
        """AC-13.1: DATO fattura passiva verificata e categorizzata,
        QUANDO registro, ALLORA DARE conto spesa + DARE IVA credito + AVERE Fornitori."""
        invoice = create_invoice(
            tenant_id=tenant.id,
            numero="FT-REG-001",
            piva="IT11111111111",
            nome="Fornitore Test SRL",
            importo=1000.0,
            category="Consulenze",
            verified=True,
            status="categorized",
        )
        db_session.add(invoice)
        await db_session.flush()

        event_bus.clear()
        agent = ContaAgent(db_session)
        result = await agent.register_entry(invoice.id, tenant.id)

        assert result["status"] == "posted"
        assert result["total_debit"] == result["total_credit"]
        assert result["lines_count"] == 3

        # Check lines in DB
        entry_id = uuid.UUID(result["entry_id"])
        lines_result = await db_session.execute(
            select(JournalLine).where(JournalLine.entry_id == entry_id)
        )
        lines = lines_result.scalars().all()

        # Verify DARE conto spesa (netto)
        expense_lines = [l for l in lines if l.account_code == "6110" and l.debit > 0]
        assert len(expense_lines) == 1
        assert expense_lines[0].debit == 1000.0

        # Verify DARE IVA credito
        iva_lines = [l for l in lines if l.account_code == "1120" and l.debit > 0]
        assert len(iva_lines) == 1
        assert iva_lines[0].debit == 220.0

        # Verify AVERE Fornitori (totale)
        fornitori_lines = [l for l in lines if l.account_code == "2010" and l.credit > 0]
        assert len(fornitori_lines) == 1
        assert fornitori_lines[0].credit == 1220.0

        # Check event published
        events = event_bus.get_events("journal.entry.created")
        assert len(events) >= 1

        # Check invoice status updated
        await db_session.refresh(invoice)
        assert invoice.processing_status == "registered"


# ============================================================
# AC-13.2 — Reverse charge → doppia scrittura IVA
# ============================================================


class TestAC132ReverseCharge:
    """AC-13.2: Reverse charge crea doppia scrittura IVA (credito + debito)."""

    async def test_ac_132_reverse_charge(
        self,
        db_session: AsyncSession,
        tenant: Tenant,
    ):
        """AC-13.2: DATO fattura reverse charge,
        QUANDO registro, ALLORA doppia IVA (credito + debito)."""
        invoice = create_invoice(
            tenant_id=tenant.id,
            numero="FT-RC-001",
            piva="IT22222222222",
            nome="Fornitore EU SRL",
            importo=2000.0,
            category="Servizi",
            verified=True,
            status="categorized",
            doc_type="TD17",  # Reverse charge
        )
        db_session.add(invoice)
        await db_session.flush()

        agent = ContaAgent(db_session)
        result = await agent.register_entry(invoice.id, tenant.id)

        assert result["status"] == "posted"
        assert result["total_debit"] == result["total_credit"]

        # Check lines
        entry_id = uuid.UUID(result["entry_id"])
        lines_result = await db_session.execute(
            select(JournalLine).where(JournalLine.entry_id == entry_id)
        )
        lines = lines_result.scalars().all()

        # Should have IVA credito (normal + reverse charge) and IVA debito
        iva_credito_lines = [l for l in lines if l.account_code == "1120" and l.debit > 0]
        iva_debito_lines = [l for l in lines if l.account_code == "2110" and l.credit > 0]

        # Reverse charge: additional IVA credito DARE + IVA debito AVERE
        assert len(iva_credito_lines) >= 2  # Normal + reverse charge
        assert len(iva_debito_lines) >= 1


# ============================================================
# AC-13.3 — Conto contabile mancante → sospesa, notifica utente
# ============================================================


class TestAC133ContoMancante:
    """AC-13.3: Conto contabile mancante crea entry error + notifica."""

    async def test_ac_133_conto_mancante(
        self,
        db_session: AsyncSession,
        tenant: Tenant,
    ):
        """AC-13.3: DATO fattura con categoria sconosciuta nel piano conti,
        QUANDO registro, ALLORA sospesa con errore pending_accounting."""
        invoice = create_invoice(
            tenant_id=tenant.id,
            numero="FT-MISSING-001",
            piva="IT33333333333",
            nome="Fornitore Unknown SRL",
            importo=500.0,
            category="CategoriaInesistente",
            verified=True,
            status="categorized",
        )
        db_session.add(invoice)
        await db_session.flush()

        event_bus.clear()
        agent = ContaAgent(db_session)
        result = await agent.register_entry(invoice.id, tenant.id)

        assert result["status"] == "error"
        assert result["error"] == "pending_accounting"
        assert "CategoriaInesistente" in result["message"]

        # Check invoice status
        await db_session.refresh(invoice)
        assert invoice.processing_status == "error"

        # Check error event published
        events = event_bus.get_events("journal.entry.error")
        assert len(events) >= 1


# ============================================================
# AC-13.4 — Sbilanciamento dare/avere → errore, logga, notifica
# ============================================================


class TestAC134Sbilanciamento:
    """AC-13.4: Validated entries must always be balanced (debit == credit)."""

    async def test_ac_134_sbilanciamento_validazione(
        self,
        db_session: AsyncSession,
        tenant: Tenant,
    ):
        """AC-13.4: DATO fattura con importi corretti,
        QUANDO registro, ALLORA dare == avere sempre bilanciato."""
        # Test with a normal invoice - should always be balanced
        invoice = create_invoice(
            tenant_id=tenant.id,
            numero="FT-BAL-001",
            piva="IT44444444444",
            nome="Fornitore Balance SRL",
            importo=1500.0,
            category="Utenze",
            verified=True,
            status="categorized",
        )
        db_session.add(invoice)
        await db_session.flush()

        agent = ContaAgent(db_session)
        result = await agent.register_entry(invoice.id, tenant.id)

        assert result["status"] == "posted"
        assert result["total_debit"] == result["total_credit"]

        # Verify in DB
        entry_result = await db_session.execute(
            select(JournalEntry).where(
                JournalEntry.invoice_id == invoice.id
            )
        )
        entry = entry_result.scalar_one()
        assert abs(entry.total_debit - entry.total_credit) < 0.01

    async def test_ac_134_balance_with_different_amounts(
        self,
        db_session: AsyncSession,
        tenant: Tenant,
    ):
        """AC-13.4: Multiple invoices with varying amounts all balanced."""
        amounts = [100.0, 999.99, 50000.0, 0.01]
        for i, amount in enumerate(amounts):
            invoice = create_invoice(
                tenant_id=tenant.id,
                numero=f"FT-BAL-{i:03d}",
                piva=f"IT{50000000000 + i}",
                nome=f"Fornitore Balance {i}",
                importo=amount,
                category="Consulenze",
                verified=True,
                status="categorized",
            )
            db_session.add(invoice)
            await db_session.flush()

            agent = ContaAgent(db_session)
            result = await agent.register_entry(invoice.id, tenant.id)
            assert result["status"] == "posted"
            assert abs(result["total_debit"] - result["total_credit"]) < 0.01


# ============================================================
# AC-13.5 — Fattura multi-aliquota IVA → righe separate per aliquota
# ============================================================


class TestAC135MultiAliquota:
    """AC-13.5: Multi-aliquota IVA creates separate lines per aliquota."""

    async def test_ac_135_multi_aliquota(
        self,
        db_session: AsyncSession,
        tenant: Tenant,
    ):
        """AC-13.5: DATO fattura con 2 aliquote IVA,
        QUANDO registro, ALLORA righe separate per ciascuna aliquota."""
        structured_data = {
            "iva_lines": [
                {"aliquota": 22.0, "imponibile": 1000.0, "imposta": 220.0},
                {"aliquota": 10.0, "imponibile": 500.0, "imposta": 50.0},
            ]
        }
        invoice = create_invoice(
            tenant_id=tenant.id,
            numero="FT-MULTI-001",
            piva="IT55555555555",
            nome="Fornitore Multi IVA SRL",
            importo=1500.0,
            category="Consulenze",
            verified=True,
            status="categorized",
            structured_data=structured_data,
        )
        # Fix totals for multi-aliquota
        invoice.importo_netto = 1500.0
        invoice.importo_iva = 270.0
        invoice.importo_totale = 1770.0
        db_session.add(invoice)
        await db_session.flush()

        agent = ContaAgent(db_session)
        result = await agent.register_entry(invoice.id, tenant.id)

        assert result["status"] == "posted"
        assert result["total_debit"] == result["total_credit"]

        # Check lines
        entry_id = uuid.UUID(result["entry_id"])
        lines_result = await db_session.execute(
            select(JournalLine).where(JournalLine.entry_id == entry_id)
        )
        lines = lines_result.scalars().all()

        # Should have: 2 expense lines + 2 IVA lines + 1 fornitori = 5 lines
        expense_lines = [l for l in lines if l.account_code == "6110"]
        iva_lines = [l for l in lines if l.account_code == "1120"]
        fornitori_lines = [l for l in lines if l.account_code == "2010"]

        assert len(expense_lines) == 2
        assert len(iva_lines) == 2
        assert len(fornitori_lines) == 1

        # Verify IVA amounts are correct per aliquota
        iva_debits = sorted([l.debit for l in iva_lines])
        assert iva_debits == [50.0, 220.0]

        # Verify fornitori total
        assert fornitori_lines[0].credit == 1770.0


# ============================================================
# AC-13.6 — Registrazione concorrente → idempotency check
# ============================================================


class TestAC136RegistrazioneConcorrente:
    """AC-13.6: Idempotency check prevents duplicate journal entries."""

    async def test_ac_136_registrazione_concorrente(
        self,
        db_session: AsyncSession,
        tenant: Tenant,
    ):
        """AC-13.6: DATO fattura gia registrata,
        QUANDO registro di nuovo, ALLORA nessun duplicato."""
        invoice = create_invoice(
            tenant_id=tenant.id,
            numero="FT-IDEMP-001",
            piva="IT66666666666",
            nome="Fornitore Idempotency SRL",
            importo=750.0,
            category="Utenze",
            verified=True,
            status="categorized",
        )
        db_session.add(invoice)
        await db_session.flush()

        agent = ContaAgent(db_session)

        # First registration
        result1 = await agent.register_entry(invoice.id, tenant.id)
        assert result1["status"] == "posted"

        # Second registration (should be idempotent)
        result2 = await agent.register_entry(invoice.id, tenant.id)
        assert result2["status"] == "already_registered"
        assert "gia registrata" in result2["message"].lower()

        # Verify only one entry exists
        entries_result = await db_session.execute(
            select(JournalEntry).where(
                JournalEntry.invoice_id == invoice.id,
                JournalEntry.status == "posted",
            )
        )
        entries = entries_result.scalars().all()
        assert len(entries) == 1
