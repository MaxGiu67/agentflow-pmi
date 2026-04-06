"""Tests for LinkedIn Social Selling + Cross-sell — Sprint 39-41 (US-214→US-218).

Covers:
- US-214: LinkedIn message generation
- US-215: Warmth score + cadence tracking
- US-216: CSV import
- US-217: Cross-sell signal detection
- US-218: Cross-sell report
"""

import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import CrmActivity, CrmContact, CrmCompany, CrmDeal, Tenant, User
from api.modules.sales_tools.linkedin_service import LinkedInService
from api.modules.sales_tools.cross_sell_service import CrossSellService
from tests.conftest import _hash_pw


@pytest.fixture
async def contact_with_activities(db_session: AsyncSession, tenant: Tenant) -> CrmContact:
    contact = CrmContact(tenant_id=tenant.id, name="Prospect SRL", contact_name="Marco Rossi")
    db_session.add(contact)
    await db_session.flush()

    # Add LinkedIn activities
    for act_type in ["linkedin_connection", "linkedin_dm", "linkedin_like"]:
        db_session.add(CrmActivity(
            tenant_id=tenant.id, contact_id=contact.id, type=act_type,
            subject=f"Activity {act_type}", status="completed",
        ))
    await db_session.flush()
    return contact


@pytest.fixture
async def deal_with_notes(db_session: AsyncSession, tenant: Tenant) -> CrmDeal:
    deal = CrmDeal(tenant_id=tenant.id, name="Deal Test CrossSell")
    db_session.add(deal)
    await db_session.flush()

    # Add activity with cross-sell keyword
    db_session.add(CrmActivity(
        tenant_id=tenant.id, deal_id=deal.id, type="note",
        subject="Call recap", description="Il cliente ha problemi di documentazione tecnica dispersa e knowledge base",
        status="completed",
    ))
    await db_session.flush()
    return deal


# ── US-214: LinkedIn Messages ──────────────────────────


class TestUS214LinkedInMessages:
    def test_connection_request(self):
        svc = LinkedInService(None)
        msg = svc.generate_message("connection_request", "Marco", "ACME SRL", "metallurgia", "il suo post su Industry 4.0")
        assert msg["char_count"] <= 200
        assert "Marco" in msg["text"]
        assert msg["message_type"] == "connection_request"

    def test_conversation_starter(self):
        svc = LinkedInService(None)
        msg = svc.generate_message("conversation_starter", "Marco", "ACME SRL", "metallurgia")
        assert msg["char_count"] <= 300
        assert "ACME" in msg["text"]
        assert "pitch" not in msg["text"].lower()

    def test_soft_ask(self):
        svc = LinkedInService(None)
        msg = svc.generate_message("soft_ask", "Marco", "ACME SRL")
        assert "10 minuti" in msg["text"] or "chiacchierata" in msg["text"]

    def test_breakup(self):
        svc = LinkedInService(None)
        msg = svc.generate_message("breakup", "Marco", "ACME SRL")
        assert "disponibile" in msg["text"].lower() or "futuro" in msg["text"].lower()


# ── US-215: Warmth Score + Cadence ─────────────────────


class TestUS215WarmthCadence:
    @pytest.mark.anyio
    async def test_warmth_score_hot(self, db_session: AsyncSession, contact_with_activities: CrmContact):
        svc = LinkedInService(db_session)
        result = await svc.calc_warmth_score(contact_with_activities.id)
        # connection (20) + dm (30) + like (15) = 65
        assert result["score"] >= 60
        assert result["label"] == "hot"

    @pytest.mark.anyio
    async def test_warmth_score_cold(self, db_session: AsyncSession, tenant: Tenant):
        contact = CrmContact(tenant_id=tenant.id, name="Cold Prospect")
        db_session.add(contact)
        await db_session.flush()

        svc = LinkedInService(db_session)
        result = await svc.calc_warmth_score(contact.id)
        assert result["score"] == 0
        assert result["label"] == "cold"

    @pytest.mark.anyio
    async def test_cadence_not_started(self, db_session: AsyncSession, tenant: Tenant):
        contact = CrmContact(tenant_id=tenant.id, name="New Prospect")
        db_session.add(contact)
        await db_session.flush()

        svc = LinkedInService(db_session)
        result = await svc.check_cadence(contact.id)
        assert result["cadence_started"] is False
        assert result["next_action"]["action"] == "linkedin_view"

    @pytest.mark.anyio
    async def test_cadence_in_progress(self, db_session: AsyncSession, contact_with_activities: CrmContact):
        svc = LinkedInService(db_session)
        result = await svc.check_cadence(contact_with_activities.id)
        assert result["cadence_started"] is True
        assert result["total_touchpoints"] >= 3


# ── US-216: CSV Import ─────────────────────────────────


class TestUS216CSVImport:
    @pytest.mark.anyio
    async def test_import_csv(self, db_session: AsyncSession, tenant: Tenant):
        svc = LinkedInService(db_session)
        csv_data = (
            "First Name,Last Name,Company,Title\n"
            "Marco,Rossi,Fonderia ABC,CTO\n"
            "Anna,Bianchi,Commercio XYZ,CEO\n"
            "Luca,Verdi,Fonderia ABC,COO\n"
        )
        result = await svc.import_csv(tenant.id, csv_data)
        assert result["imported"] == 3
        assert result["duplicates"] == 0
        assert result["errors"] == 0

    @pytest.mark.anyio
    async def test_import_csv_duplicates(self, db_session: AsyncSession, tenant: Tenant):
        svc = LinkedInService(db_session)
        csv_data = "First Name,Last Name,Company,Title\nMarco,Rossi,Test SRL,CTO\n"
        await svc.import_csv(tenant.id, csv_data)
        # Import again → duplicate
        result = await svc.import_csv(tenant.id, csv_data)
        assert result["duplicates"] == 1
        assert result["imported"] == 0

    @pytest.mark.anyio
    async def test_import_csv_errors(self, db_session: AsyncSession, tenant: Tenant):
        svc = LinkedInService(db_session)
        csv_data = "First Name,Last Name,Company,Title\n,,, \nAnna,Bianchi,Valid SRL,CEO\n"
        result = await svc.import_csv(tenant.id, csv_data)
        assert result["errors"] == 1
        assert result["imported"] == 1


# ── US-217: Cross-sell Detection ───────────────────────


class TestUS217CrossSell:
    @pytest.mark.anyio
    async def test_detect_tm_to_elevia(self, db_session: AsyncSession, tenant: Tenant, deal_with_notes: CrmDeal):
        svc = CrossSellService(db_session)
        signals = await svc.detect_signals(tenant.id, deal_with_notes.id)
        assert len(signals) >= 1
        assert signals[0]["direction"] == "tm_to_elevia"
        assert signals[0]["suggested_product"] == "Elevia AI"

    @pytest.mark.anyio
    async def test_detect_no_signal(self, db_session: AsyncSession, tenant: Tenant):
        deal = CrmDeal(tenant_id=tenant.id, name="Normal Deal")
        db_session.add(deal)
        await db_session.flush()
        # No activities with keywords
        svc = CrossSellService(db_session)
        signals = await svc.detect_signals(tenant.id, deal.id)
        assert len(signals) == 0

    @pytest.mark.anyio
    async def test_detect_idempotent(self, db_session: AsyncSession, tenant: Tenant, deal_with_notes: CrmDeal):
        svc = CrossSellService(db_session)
        signals1 = await svc.detect_signals(tenant.id, deal_with_notes.id)
        signals2 = await svc.detect_signals(tenant.id, deal_with_notes.id)
        # Second call doesn't create duplicates
        assert len(signals2) == 0

    @pytest.mark.anyio
    async def test_list_signals(self, db_session: AsyncSession, tenant: Tenant, deal_with_notes: CrmDeal):
        svc = CrossSellService(db_session)
        await svc.detect_signals(tenant.id, deal_with_notes.id)
        signals = await svc.list_signals(tenant.id)
        assert len(signals) >= 1


# ── US-218: Cross-sell Report ──────────────────────────


class TestUS218CrossSellReport:
    @pytest.mark.anyio
    async def test_report(self, db_session: AsyncSession, tenant: Tenant, deal_with_notes: CrmDeal):
        svc = CrossSellService(db_session)
        await svc.detect_signals(tenant.id, deal_with_notes.id)
        report = await svc.get_report(tenant.id)
        assert report["total_signals"] >= 1
        assert "documentation_pain" in report["by_signal_type"]
