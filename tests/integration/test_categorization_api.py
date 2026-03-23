"""
Test suite for US-10: Categorizzazione automatica con learning
Tests for 5 Acceptance Criteria (AC-10.1 through AC-10.5)
"""

import uuid
from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from api.agents.learning_agent import LearningAgent
from api.agents.base_agent import event_bus
from api.db.models import CategorizationFeedback, Invoice, Tenant
from tests.conftest import create_invoice


# ============================================================
# AC-10.1 — Rules engine: P.IVA nota → categoria storica
# ============================================================


class TestAC101CategorizzazioneRules:
    """AC-10.1: P.IVA nota → categoria storica con confidence score."""

    async def test_ac_101_categorizzazione_rules(
        self,
        db_session: AsyncSession,
        tenant: Tenant,
    ):
        """AC-10.1: DATO fornitore con P.IVA gia categorizzata,
        QUANDO nuova fattura stesso fornitore, ALLORA stessa categoria con alta confidence."""
        # Create a verified invoice with a known category
        existing = create_invoice(
            tenant_id=tenant.id,
            numero="FT-OLD-001",
            piva="IT11111111111",
            nome="Fornitore Noto SRL",
            category="Consulenze",
            verified=True,
            status="categorized",
        )
        db_session.add(existing)
        await db_session.flush()

        # Create new invoice from same supplier
        new_invoice = create_invoice(
            tenant_id=tenant.id,
            numero="FT-NEW-001",
            piva="IT11111111111",
            nome="Fornitore Noto SRL",
            status="parsed",
        )
        db_session.add(new_invoice)
        await db_session.flush()

        # Categorize
        agent = LearningAgent(db_session)
        result = await agent.categorize(new_invoice.id, tenant.id)

        assert result["category"] == "Consulenze"
        assert result["confidence"] >= 0.8
        assert result["rule_used"] == "piva_match"

        await db_session.refresh(new_invoice)
        assert new_invoice.category == "Consulenze"
        assert new_invoice.processing_status == "categorized"


# ============================================================
# AC-10.2 — Learning da 30+ verifiche
# ============================================================


class TestAC102LearningMigliora:
    """AC-10.2: Learning migliora con 30+ verifiche."""

    async def test_ac_102_learning_migliora(
        self,
        db_session: AsyncSession,
        tenant: Tenant,
    ):
        """AC-10.2: DATO 30+ verifiche utente,
        QUANDO categorizzazione, ALLORA similarity model attivo."""
        agent = LearningAgent(db_session)

        # Record 30+ feedbacks to activate learning
        for i in range(35):
            inv = create_invoice(
                tenant_id=tenant.id,
                numero=f"FT-LEARN-{i:03d}",
                piva=f"IT{90000000000 + i}",
                nome=f"Fornitore Learning {i}",
                importo=1000.0 + i * 10,
                category="Utenze" if i % 2 == 0 else "Consulenze",
                verified=True,
                status="categorized",
            )
            db_session.add(inv)
            await db_session.flush()

            feedback = CategorizationFeedback(
                tenant_id=tenant.id,
                invoice_id=inv.id,
                suggested_category="Utenze" if i % 2 == 0 else "Consulenze",
                final_category="Utenze" if i % 2 == 0 else "Consulenze",
                was_correct=True,
            )
            db_session.add(feedback)

        await db_session.flush()

        # Check accuracy stats
        accuracy = await agent.get_accuracy(tenant.id)
        assert accuracy["total_feedback"] >= 30
        assert accuracy["learning_active"] is True
        assert accuracy["accuracy"] > 0


# ============================================================
# AC-10.3 — Nessuna regola applicabile
# ============================================================


class TestAC103NessunaRegola:
    """AC-10.3: Nessuna regola → categoria suggerita nessuna, manuale."""

    async def test_ac_103_nessuna_regola(
        self,
        db_session: AsyncSession,
        tenant: Tenant,
    ):
        """AC-10.3: DATO fornitore sconosciuto senza match,
        QUANDO categorizzazione, ALLORA 'categoria suggerita: nessuna'."""
        # Create invoice from unknown supplier
        invoice = create_invoice(
            tenant_id=tenant.id,
            numero="FT-UNKNOWN-001",
            piva="IT99999999999",
            nome="Fornitore Sconosciuto XYZ",
            status="parsed",
        )
        db_session.add(invoice)
        await db_session.flush()

        agent = LearningAgent(db_session)
        result = await agent.categorize(invoice.id, tenant.id)

        assert result["category"] is None
        assert result["confidence"] == 0.0
        assert "nessuna" in result["message"].lower()


# ============================================================
# AC-10.4 — Redis down → dead letter queue
# ============================================================


class TestAC104DeadLetterQueue:
    """AC-10.4: Redis down → dead letter queue, events not lost."""

    async def test_ac_104_dead_letter_queue(
        self,
        db_session: AsyncSession,
        tenant: Tenant,
    ):
        """AC-10.4: DATO evento non pubblicabile (Redis down simulato),
        QUANDO categorizzazione, ALLORA evento in dead letter queue."""
        # Create verified invoice for match
        existing = create_invoice(
            tenant_id=tenant.id,
            numero="FT-DLQ-OLD",
            piva="IT77777777777",
            nome="Fornitore DLQ",
            category="Materiali",
            verified=True,
            status="categorized",
        )
        db_session.add(existing)
        await db_session.flush()

        # Create new invoice to categorize
        invoice = create_invoice(
            tenant_id=tenant.id,
            numero="FT-DLQ-NEW",
            piva="IT77777777777",
            nome="Fornitore DLQ",
            status="parsed",
        )
        db_session.add(invoice)
        await db_session.flush()

        # Clear event bus to get clean state
        event_bus.clear()

        # Monkey-patch the publish_event to simulate failure (Redis down)
        agent = LearningAgent(db_session)
        original_publish = agent.publish_event

        async def failing_publish(event_type, payload, tid):
            raise ConnectionError("Redis non raggiungibile")

        agent.publish_event = failing_publish

        result = await agent.categorize(invoice.id, tenant.id)

        # Categorization should still work, event goes to dead letter
        assert result["category"] == "Materiali"

        # Check dead letter queue has the event
        dead_letters = event_bus.get_dead_letter()
        assert len(dead_letters) >= 1
        dl_event = dead_letters[-1]
        assert dl_event["event_type"] == "invoice.categorized"
        assert dl_event["status"] == "dead_letter"


# ============================================================
# AC-10.5 — Fornitore cambia nome, stessa P.IVA → stessa categoria
# ============================================================


class TestAC105FornitoreCambiaNome:
    """AC-10.5: Fornitore cambia nome ma stessa P.IVA → stessa categoria."""

    async def test_ac_105_fornitore_cambia_nome(
        self,
        db_session: AsyncSession,
        tenant: Tenant,
    ):
        """AC-10.5: DATO fornitore con P.IVA nota che cambia ragione sociale,
        QUANDO categorizzazione, ALLORA stessa categoria (matching per P.IVA)."""
        # Old invoice with old name
        old_invoice = create_invoice(
            tenant_id=tenant.id,
            numero="FT-RENAME-OLD",
            piva="IT55555555555",
            nome="Vecchio Nome SRL",
            category="Servizi IT",
            verified=True,
            status="categorized",
        )
        db_session.add(old_invoice)
        await db_session.flush()

        # New invoice with new name, same P.IVA
        new_invoice = create_invoice(
            tenant_id=tenant.id,
            numero="FT-RENAME-NEW",
            piva="IT55555555555",
            nome="Nuovo Nome SPA",  # Name changed
            status="parsed",
        )
        db_session.add(new_invoice)
        await db_session.flush()

        agent = LearningAgent(db_session)
        result = await agent.categorize(new_invoice.id, tenant.id)

        # Should match by P.IVA regardless of name change
        assert result["category"] == "Servizi IT"
        assert result["rule_used"] == "piva_match"
        assert result["confidence"] >= 0.8
