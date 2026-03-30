"""LearningAgent: Categorizes invoices using rules engine + similarity model."""

import logging
import uuid
from difflib import SequenceMatcher

from sqlalchemy import select, and_, func

from api.agents.base_agent import BaseAgent
from api.db.models import CategorizationFeedback, Invoice

logger = logging.getLogger(__name__)

# Confidence thresholds
HIGH_CONFIDENCE = 0.9
MEDIUM_CONFIDENCE = 0.6
LOW_CONFIDENCE = 0.3
MIN_FEEDBACK_FOR_LEARNING = 30


class LearningAgent(BaseAgent):
    """Agent that categorizes invoices using rules and learned patterns."""

    agent_name = "learning_agent"

    async def categorize(self, invoice_id: uuid.UUID, tenant_id: uuid.UUID) -> dict:
        """Categorize an invoice using the rules engine and similarity model.

        Strategy:
        1. Rule 1: Exact P.IVA match from previous verified categorizations
        2. Rule 2: Emittente name similarity (fuzzy match)
        3. Rule 3: Amount range pattern (if enough data)
        4. Fallback: No suggestion, manual categorization required

        Returns:
            Dict with category, confidence, and rule_used.
        """
        result = await self.db.execute(
            select(Invoice).where(Invoice.id == invoice_id)
        )
        invoice = result.scalar_one_or_none()
        if not invoice:
            raise ValueError(f"Fattura {invoice_id} non trovata")

        # Try rules in order of confidence
        categorization = await self._rule_piva_match(tenant_id, invoice)
        if not categorization:
            categorization = await self._rule_name_similarity(tenant_id, invoice)
        if not categorization:
            categorization = await self._rule_amount_pattern(tenant_id, invoice)

        if categorization:
            # Apply categorization
            invoice.category = categorization["category"]
            invoice.category_confidence = categorization["confidence"]
            invoice.processing_status = "categorized"
            await self.db.flush()

            # Publish event
            try:
                await self.publish_event(
                    "invoice.categorized",
                    {
                        "invoice_id": str(invoice_id),
                        "category": categorization["category"],
                        "confidence": categorization["confidence"],
                        "rule_used": categorization["rule_used"],
                    },
                    tenant_id,
                )
            except Exception as e:
                # Dead letter queue if event publishing fails (e.g., Redis down)
                logger.error("Failed to publish categorization event: %s", e)
                await self.publish_dead_letter(
                    "invoice.categorized",
                    {
                        "invoice_id": str(invoice_id),
                        "category": categorization["category"],
                        "confidence": categorization["confidence"],
                        "rule_used": categorization["rule_used"],
                    },
                    tenant_id,
                    reason=str(e),
                )

            return categorization

        # No rule matched — needs manual categorization
        invoice.category = None
        invoice.category_confidence = 0.0
        await self.db.flush()

        await self.publish_event(
            "invoice.categorization_manual",
            {
                "invoice_id": str(invoice_id),
                "message": "Nessuna regola applicabile, categorizzazione manuale necessaria",
            },
            tenant_id,
        )

        return {
            "category": None,
            "confidence": 0.0,
            "rule_used": None,
            "message": "categoria suggerita: nessuna",
        }

    async def record_feedback(
        self,
        invoice_id: uuid.UUID,
        tenant_id: uuid.UUID,
        suggested_category: str | None,
        final_category: str,
    ) -> None:
        """Record user feedback on categorization for learning."""
        was_correct = suggested_category == final_category if suggested_category else False

        feedback = CategorizationFeedback(
            tenant_id=tenant_id,
            invoice_id=invoice_id,
            suggested_category=suggested_category,
            final_category=final_category,
            was_correct=was_correct,
        )
        self.db.add(feedback)

        # Update the invoice category
        result = await self.db.execute(
            select(Invoice).where(Invoice.id == invoice_id)
        )
        invoice = result.scalar_one_or_none()
        if invoice:
            invoice.category = final_category
            invoice.verified = True
            invoice.category_confidence = 1.0

        await self.db.flush()

    async def get_accuracy(self, tenant_id: uuid.UUID) -> dict:
        """Get categorization accuracy stats."""
        total_result = await self.db.execute(
            select(func.count(CategorizationFeedback.id)).where(
                CategorizationFeedback.tenant_id == tenant_id
            )
        )
        total = total_result.scalar() or 0

        correct_result = await self.db.execute(
            select(func.count(CategorizationFeedback.id)).where(
                and_(
                    CategorizationFeedback.tenant_id == tenant_id,
                    CategorizationFeedback.was_correct == True,  # noqa: E712
                )
            )
        )
        correct = correct_result.scalar() or 0

        accuracy = correct / total if total > 0 else 0.0

        return {
            "total_feedback": total,
            "correct": correct,
            "accuracy": round(accuracy, 4),
            "learning_active": total >= MIN_FEEDBACK_FOR_LEARNING,
        }

    async def _rule_piva_match(self, tenant_id: uuid.UUID, invoice: Invoice) -> dict | None:
        """Rule 1: Match by emittente P.IVA from verified invoices."""
        # Find verified invoices with same P.IVA
        result = await self.db.execute(
            select(Invoice.category)
            .where(
                and_(
                    Invoice.tenant_id == tenant_id,
                    Invoice.emittente_piva == invoice.emittente_piva,
                    Invoice.verified == True,  # noqa: E712
                    Invoice.category.isnot(None),
                    Invoice.id != invoice.id,
                )
            )
            .order_by(Invoice.created_at.desc())
            .limit(1)
        )
        category = result.scalar_one_or_none()
        if category:
            return {
                "category": category,
                "confidence": HIGH_CONFIDENCE,
                "rule_used": "piva_match",
            }
        return None

    async def _rule_name_similarity(self, tenant_id: uuid.UUID, invoice: Invoice) -> dict | None:
        """Rule 2: Match by emittente name similarity (fuzzy)."""
        if not invoice.emittente_nome:
            return None

        # Get all verified invoices with categories
        result = await self.db.execute(
            select(Invoice.emittente_nome, Invoice.category)
            .where(
                and_(
                    Invoice.tenant_id == tenant_id,
                    Invoice.verified == True,  # noqa: E712
                    Invoice.category.isnot(None),
                    Invoice.emittente_nome.isnot(None),
                    Invoice.id != invoice.id,
                )
            )
            .distinct()
        )
        verified = result.all()

        best_match = None
        best_ratio = 0.0

        for nome, cat in verified:
            if nome:
                ratio = SequenceMatcher(None, invoice.emittente_nome.lower(), nome.lower()).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_match = cat

        if best_match and best_ratio >= 0.8:
            return {
                "category": best_match,
                "confidence": round(best_ratio * MEDIUM_CONFIDENCE / 0.8, 2),
                "rule_used": "name_similarity",
            }
        return None

    async def _rule_amount_pattern(self, tenant_id: uuid.UUID, invoice: Invoice) -> dict | None:
        """Rule 3: Match by amount range pattern (if enough verified data)."""
        if not invoice.importo_totale:
            return None

        # Check if we have enough feedback for learning
        accuracy_data = await self.get_accuracy(tenant_id)
        if not accuracy_data["learning_active"]:
            return None

        # Find verified invoices with similar amounts (within 20%)
        lower = invoice.importo_totale * 0.8
        upper = invoice.importo_totale * 1.2

        result = await self.db.execute(
            select(Invoice.category, func.count(Invoice.id).label("cnt"))
            .where(
                and_(
                    Invoice.tenant_id == tenant_id,
                    Invoice.verified == True,  # noqa: E712
                    Invoice.category.isnot(None),
                    Invoice.importo_totale >= lower,
                    Invoice.importo_totale <= upper,
                    Invoice.id != invoice.id,
                )
            )
            .group_by(Invoice.category)
            .order_by(func.count(Invoice.id).desc())
            .limit(1)
        )
        row = result.first()
        if row and row.cnt >= 3:
            return {
                "category": row.category,
                "confidence": LOW_CONFIDENCE,
                "rule_used": "amount_pattern",
            }
        return None
