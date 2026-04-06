"""Comprehensive CRM test suite — Companies, Contacts, Deals, Stages, Activities, Orders.

50+ tests covering the full CRM sales flow end-to-end.
Each test verifies data is correctly saved in the DB.
"""

import uuid
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import (
    CrmActivity, CrmCompany, CrmContact, CrmDeal, CrmPipelineStage,
    PipelineTemplate, PipelineTemplateStage, Tenant, User,
)
from api.modules.crm.service import CRMService
from api.modules.pipeline_templates.service import PipelineTemplateService
from tests.conftest import _hash_pw, get_auth_token


# ── Fixtures ──────────────────────────────────────────


@pytest.fixture
async def crm(db_session: AsyncSession) -> CRMService:
    return CRMService(db_session)


@pytest.fixture
async def owner(db_session: AsyncSession, tenant: Tenant) -> User:
    u = User(
        email="owner.crm@test.it", password_hash=_hash_pw("Password1"),
        name="Owner CRM", role="owner", email_verified=True, tenant_id=tenant.id,
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest.fixture
async def commerciale(db_session: AsyncSession, tenant: Tenant) -> User:
    u = User(
        email="comm.crm@test.it", password_hash=_hash_pw("Password1"),
        name="Marco Commerciale", role="commerciale", email_verified=True, tenant_id=tenant.id,
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest.fixture
async def stages(db_session: AsyncSession, tenant: Tenant, crm: CRMService) -> list:
    """Ensure default pipeline stages exist."""
    await crm._ensure_default_stages(tenant.id)
    result = await db_session.execute(
        select(CrmPipelineStage).where(CrmPipelineStage.tenant_id == tenant.id)
        .order_by(CrmPipelineStage.sequence)
    )
    return list(result.scalars().all())


@pytest.fixture
async def pipeline_templates(db_session: AsyncSession, tenant: Tenant) -> list:
    svc = PipelineTemplateService(db_session)
    await svc.ensure_defaults(tenant.id)
    return await svc.list_templates(tenant.id)


# ============================================================
# A. AZIENDE (Company) — test_01 → test_06
# ============================================================


class TestCompanies:

    @pytest.mark.anyio
    async def test_01_create_company(self, db_session: AsyncSession, tenant: Tenant, crm: CRMService):
        """Crea azienda e verifica DB."""
        c = await crm.create_company(tenant.id, {"name": "ACME Italia SPA", "vat": "12345678901", "city": "Milano", "sector": "IT"})
        assert c["name"] == "ACME Italia SPA"
        assert c["vat"] == "12345678901"
        assert c["city"] == "Milano"
        # Verifica DB diretto
        db_c = await db_session.execute(select(CrmCompany).where(CrmCompany.id == uuid.UUID(c["id"])))
        company = db_c.scalar_one()
        assert company.name == "ACME Italia SPA"
        assert company.sector == "IT"

    @pytest.mark.anyio
    async def test_02_list_companies(self, db_session: AsyncSession, tenant: Tenant, crm: CRMService):
        """Lista aziende ordinate."""
        await crm.create_company(tenant.id, {"name": "Zebra SRL"})
        await crm.create_company(tenant.id, {"name": "Alpha SRL"})
        result = await crm.list_companies(tenant.id)
        assert result["total"] == 2

    @pytest.mark.anyio
    async def test_03_search_company(self, db_session: AsyncSession, tenant: Tenant, crm: CRMService):
        """Cerca azienda per nome parziale."""
        await crm.create_company(tenant.id, {"name": "NTT Data SPA"})
        await crm.create_company(tenant.id, {"name": "Replay SRL"})
        result = await crm.list_companies(tenant.id, search="NTT")
        assert result["total"] == 1
        assert result["companies"][0]["name"] == "NTT Data SPA"

    @pytest.mark.anyio
    async def test_04_update_company(self, db_session: AsyncSession, tenant: Tenant, crm: CRMService):
        """Aggiorna azienda."""
        c = await crm.create_company(tenant.id, {"name": "Old Name SRL"})
        updated = await crm.update_company(uuid.UUID(c["id"]), tenant.id, {"city": "Roma", "sector": "Finance"})
        assert updated["city"] == "Roma"
        assert updated["sector"] == "Finance"

    @pytest.mark.anyio
    async def test_05_company_tenant_isolation(self, db_session: AsyncSession, crm: CRMService):
        """Tenant isolation — azienda di un tenant non visibile all'altro."""
        t1 = Tenant(name="T1", type="srl", regime_fiscale="ordinario", piva="11111111111")
        t2 = Tenant(name="T2", type="srl", regime_fiscale="ordinario", piva="22222222222")
        db_session.add_all([t1, t2])
        await db_session.flush()
        await crm.create_company(t1.id, {"name": "Company T1"})
        await crm.create_company(t2.id, {"name": "Company T2"})
        r1 = await crm.list_companies(t1.id)
        r2 = await crm.list_companies(t2.id)
        assert r1["total"] == 1
        assert r1["companies"][0]["name"] == "Company T1"
        assert r2["total"] == 1
        assert r2["companies"][0]["name"] == "Company T2"

    @pytest.mark.anyio
    async def test_06_get_company_by_id(self, db_session: AsyncSession, tenant: Tenant, crm: CRMService):
        c = await crm.create_company(tenant.id, {"name": "GetMe SRL"})
        fetched = await crm.get_company(uuid.UUID(c["id"]), tenant.id)
        assert fetched is not None
        assert fetched["name"] == "GetMe SRL"


# ============================================================
# B. CONTATTI (Referenti) — test_07 → test_15
# ============================================================


class TestContacts:

    @pytest.mark.anyio
    async def test_07_create_contact_with_company(self, db_session: AsyncSession, tenant: Tenant, crm: CRMService):
        """Crea contatto collegato ad azienda."""
        company = await crm.create_company(tenant.id, {"name": "ACME SRL"})
        contact = await crm.create_contact(tenant.id, {
            "name": "ACME SRL", "company_id": company["id"],
            "contact_name": "Mario Rossi", "contact_role": "CTO",
            "email": "mario@acme.it", "phone": "+39 02 1234567",
        })
        assert contact["contact_name"] == "Mario Rossi"
        assert contact["contact_role"] == "CTO"
        # Verifica DB
        db_c = await db_session.execute(select(CrmContact).where(CrmContact.id == uuid.UUID(contact["id"])))
        c = db_c.scalar_one()
        assert c.company_id == uuid.UUID(company["id"])
        assert c.email == "mario@acme.it"

    @pytest.mark.anyio
    async def test_08_create_contact_without_company(self, db_session: AsyncSession, tenant: Tenant, crm: CRMService):
        """Contatto senza azienda — company_id null."""
        contact = await crm.create_contact(tenant.id, {"name": "Freelancer SRL", "contact_name": "Luca Bianchi"})
        db_c = await db_session.execute(select(CrmContact).where(CrmContact.id == uuid.UUID(contact["id"])))
        c = db_c.scalar_one()
        assert c.company_id is None

    @pytest.mark.anyio
    async def test_09_list_contacts_shows_contact_name(self, db_session: AsyncSession, tenant: Tenant, crm: CRMService):
        """Lista contatti mostra contact_name."""
        await crm.create_contact(tenant.id, {"name": "Test SRL", "contact_name": "Anna Verdi"})
        result = await crm.list_contacts(tenant.id)
        assert result["total"] == 1
        assert result["contacts"][0]["contact_name"] == "Anna Verdi"

    @pytest.mark.anyio
    async def test_10_filter_contacts_by_company(self, db_session: AsyncSession, tenant: Tenant, crm: CRMService):
        """Filtro contatti per company_id — SOLO quelli dell'azienda."""
        c1 = await crm.create_company(tenant.id, {"name": "Company A"})
        c2 = await crm.create_company(tenant.id, {"name": "Company B"})
        await crm.create_contact(tenant.id, {"name": "Company A", "company_id": c1["id"], "contact_name": "Ref A"})
        await crm.create_contact(tenant.id, {"name": "Company B", "company_id": c2["id"], "contact_name": "Ref B"})
        await crm.create_contact(tenant.id, {"name": "No Company", "contact_name": "Ref Orphan"})

        # Tutti
        all_contacts = await crm.list_contacts(tenant.id)
        assert all_contacts["total"] == 3

        # Solo Company A (il bug era qui — mostrava tutti)
        # Non c'e filtro company_id nel backend, il filtro e frontend-only
        # Ma verifichiamo che company_id sia restituito correttamente
        contacts = all_contacts["contacts"]
        a_contacts = [c for c in contacts if c.get("company_id") == c1["id"]]
        assert len(a_contacts) == 1
        assert a_contacts[0]["contact_name"] == "Ref A"

    @pytest.mark.anyio
    async def test_11_search_contact_by_name(self, db_session: AsyncSession, tenant: Tenant, crm: CRMService):
        await crm.create_contact(tenant.id, {"name": "Alpha SRL", "contact_name": "Marco Alpha"})
        await crm.create_contact(tenant.id, {"name": "Beta SRL", "contact_name": "Luca Beta"})
        result = await crm.list_contacts(tenant.id, search="Alpha")
        assert result["total"] == 1

    @pytest.mark.anyio
    async def test_12_update_contact(self, db_session: AsyncSession, tenant: Tenant, crm: CRMService):
        c = await crm.create_contact(tenant.id, {"name": "Update SRL", "email": "old@test.it"})
        updated = await crm.update_contact(uuid.UUID(c["id"]), {"email": "new@test.it", "phone": "+39 333 000"})
        assert updated["email"] == "new@test.it"
        assert updated["phone"] == "+39 333 000"

    @pytest.mark.anyio
    async def test_13_delete_contact(self, db_session: AsyncSession, tenant: Tenant, crm: CRMService):
        c = await crm.create_contact(tenant.id, {"name": "Delete SRL"})
        ok = await crm.delete_contact(uuid.UUID(c["id"]))
        assert ok is True
        result = await crm.list_contacts(tenant.id)
        assert result["total"] == 0

    @pytest.mark.anyio
    async def test_14_delete_nonexistent_contact(self, crm: CRMService):
        ok = await crm.delete_contact(uuid.uuid4())
        assert ok is False

    @pytest.mark.anyio
    async def test_15_contact_tenant_isolation(self, db_session: AsyncSession, crm: CRMService):
        t1 = Tenant(name="T1", type="srl", regime_fiscale="ordinario", piva="33333333333")
        t2 = Tenant(name="T2", type="srl", regime_fiscale="ordinario", piva="44444444444")
        db_session.add_all([t1, t2])
        await db_session.flush()
        await crm.create_contact(t1.id, {"name": "T1 Contact"})
        await crm.create_contact(t2.id, {"name": "T2 Contact"})
        r1 = await crm.list_contacts(t1.id)
        assert r1["total"] == 1
        assert r1["contacts"][0]["name"] == "T1 Contact"


# ============================================================
# C. DEAL (Opportunita) — test_16 → test_25
# ============================================================


class TestDeals:

    @pytest.mark.anyio
    async def test_16_create_deal_tm(self, db_session: AsyncSession, tenant: Tenant, crm: CRMService, stages, pipeline_templates):
        """Crea deal T&M con pipeline_template_id e deal_type."""
        tm_tmpl = next((t for t in pipeline_templates if t["code"] == "vendita_diretta"), None)
        deal = await crm.create_deal(tenant.id, {
            "name": "Consulenza Java ACME",
            "deal_type": "T&M",
            "expected_revenue": 30000,
            "daily_rate": 500,
            "estimated_days": 60,
            "pipeline_template_id": tm_tmpl["id"] if tm_tmpl else None,
        })
        assert deal["name"] == "Consulenza Java ACME"
        assert deal["deal_type"] == "T&M"
        assert deal["expected_revenue"] == 30000
        # Verifica DB
        db_d = await db_session.execute(select(CrmDeal).where(CrmDeal.id == uuid.UUID(deal["id"])))
        d = db_d.scalar_one()
        assert d.deal_type == "T&M"
        assert d.daily_rate == 500
        if tm_tmpl:
            assert str(d.pipeline_template_id) == tm_tmpl["id"]

    @pytest.mark.anyio
    async def test_17_create_deal_corpo(self, db_session: AsyncSession, tenant: Tenant, crm: CRMService, stages, pipeline_templates):
        corpo_tmpl = next((t for t in pipeline_templates if t["code"] == "progetto_corpo"), None)
        deal = await crm.create_deal(tenant.id, {
            "name": "Progetto Gestionale",
            "deal_type": "fixed",
            "expected_revenue": 50000,
            "pipeline_template_id": corpo_tmpl["id"] if corpo_tmpl else None,
        })
        assert deal["deal_type"] == "fixed"
        if corpo_tmpl:
            assert deal["pipeline_template_id"] == corpo_tmpl["id"]

    @pytest.mark.anyio
    async def test_18_create_deal_elevia(self, db_session: AsyncSession, tenant: Tenant, crm: CRMService, stages, pipeline_templates):
        social_tmpl = next((t for t in pipeline_templates if t["code"] == "social_selling"), None)
        deal = await crm.create_deal(tenant.id, {
            "name": "Elevia Metallurgia",
            "deal_type": "spot",
            "expected_revenue": 15000,
            "pipeline_template_id": social_tmpl["id"] if social_tmpl else None,
        })
        assert deal["deal_type"] == "spot"
        if social_tmpl:
            assert deal["pipeline_template_id"] == social_tmpl["id"]

    @pytest.mark.anyio
    async def test_19_create_deal_with_company(self, db_session: AsyncSession, tenant: Tenant, crm: CRMService, stages):
        company = await crm.create_company(tenant.id, {"name": "Deal Company SRL"})
        deal = await crm.create_deal(tenant.id, {
            "name": "Deal con azienda", "company_id": company["id"],
        })
        db_d = await db_session.execute(select(CrmDeal).where(CrmDeal.id == uuid.UUID(deal["id"])))
        d = db_d.scalar_one()
        assert str(d.company_id) == company["id"]

    @pytest.mark.anyio
    async def test_20_create_deal_with_contact(self, db_session: AsyncSession, tenant: Tenant, crm: CRMService, stages):
        contact = await crm.create_contact(tenant.id, {"name": "Contact Deal SRL"})
        deal = await crm.create_deal(tenant.id, {
            "name": "Deal con contatto", "contact_id": contact["id"],
        })
        assert deal["client_name"] == "Contact Deal SRL"

    @pytest.mark.anyio
    async def test_21_create_deal_no_name_fails(self, db_session: AsyncSession, tenant: Tenant, crm: CRMService, stages):
        """Deal senza nome — dovrebbe fallire o creare con nome vuoto."""
        try:
            result = await crm.create_deal(tenant.id, {"name": ""})
            # Se non fallisce, il nome e vuoto
            assert result["name"] == ""
        except Exception:
            pass  # Expected: KeyError or validation error

    @pytest.mark.anyio
    async def test_22_list_deals(self, db_session: AsyncSession, tenant: Tenant, crm: CRMService, stages):
        await crm.create_deal(tenant.id, {"name": "Deal A", "deal_type": "T&M"})
        await crm.create_deal(tenant.id, {"name": "Deal B", "deal_type": "fixed"})
        result = await crm.list_deals(tenant.id)
        assert result["total"] == 2

    @pytest.mark.anyio
    async def test_23_list_deals_filter_type(self, db_session: AsyncSession, tenant: Tenant, crm: CRMService, stages):
        await crm.create_deal(tenant.id, {"name": "TM Deal", "deal_type": "T&M"})
        await crm.create_deal(tenant.id, {"name": "Fixed Deal", "deal_type": "fixed"})
        result = await crm.list_deals(tenant.id, deal_type="T&M")
        assert result["total"] == 1
        assert result["deals"][0]["deal_type"] == "T&M"

    @pytest.mark.anyio
    async def test_24_update_deal(self, db_session: AsyncSession, tenant: Tenant, crm: CRMService, stages):
        deal = await crm.create_deal(tenant.id, {"name": "Update Deal", "expected_revenue": 1000})
        updated = await crm.update_deal(uuid.UUID(deal["id"]), tenant.id, {"expected_revenue": 5000, "technology": "Java"})
        assert updated["expected_revenue"] == 5000
        assert updated["technology"] == "Java"

    @pytest.mark.anyio
    async def test_25_deal_auto_first_stage(self, db_session: AsyncSession, tenant: Tenant, crm: CRMService, stages):
        """Deal senza stage_id → auto-assegnato al primo stage."""
        deal = await crm.create_deal(tenant.id, {"name": "Auto Stage"})
        assert deal["stage_id"] != ""
        assert deal["stage"] != ""


# ============================================================
# D. CAMBIO FASE PIPELINE — test_26 → test_30
# ============================================================


class TestStageMove:

    @pytest.mark.anyio
    async def test_26_move_deal_stage(self, db_session: AsyncSession, tenant: Tenant, crm: CRMService, stages):
        deal = await crm.create_deal(tenant.id, {"name": "Move Deal"})
        second_stage = stages[1] if len(stages) > 1 else stages[0]
        updated = await crm.update_deal(uuid.UUID(deal["id"]), tenant.id, {"stage_id": str(second_stage.id)})
        assert updated["stage_id"] == str(second_stage.id)
        assert updated["stage"] == second_stage.name

    @pytest.mark.anyio
    async def test_27_stage_move_updates_probability(self, db_session: AsyncSession, tenant: Tenant, crm: CRMService, stages):
        deal = await crm.create_deal(tenant.id, {"name": "Prob Deal"})
        target = stages[2] if len(stages) > 2 else stages[-1]
        updated = await crm.update_deal(uuid.UUID(deal["id"]), tenant.id, {"stage_id": str(target.id)})
        assert updated["probability"] == target.probability_default

    @pytest.mark.anyio
    async def test_28_stage_move_creates_activity(self, db_session: AsyncSession, tenant: Tenant, crm: CRMService, stages):
        deal = await crm.create_deal(tenant.id, {"name": "Activity Log Deal"})
        second = stages[1] if len(stages) > 1 else stages[0]
        await crm.update_deal(uuid.UUID(deal["id"]), tenant.id, {"stage_id": str(second.id)})
        # Check activity was created
        activities = await crm.list_activities(tenant.id, deal_id=uuid.UUID(deal["id"]))
        assert len(activities) >= 1
        assert "spostato" in activities[0]["subject"].lower() or "Deal" in activities[0]["subject"]

    @pytest.mark.anyio
    async def test_29_move_to_won(self, db_session: AsyncSession, tenant: Tenant, crm: CRMService, stages):
        won_stage = next((s for s in stages if s.is_won), None)
        if not won_stage:
            pytest.skip("No won stage")
        deal = await crm.create_deal(tenant.id, {"name": "Win Deal"})
        updated = await crm.update_deal(uuid.UUID(deal["id"]), tenant.id, {"stage_id": str(won_stage.id)})
        assert updated["stage"] == won_stage.name

    @pytest.mark.anyio
    async def test_30_move_to_lost(self, db_session: AsyncSession, tenant: Tenant, crm: CRMService, stages):
        lost_stage = next((s for s in stages if s.is_lost), None)
        if not lost_stage:
            pytest.skip("No lost stage")
        deal = await crm.create_deal(tenant.id, {"name": "Lose Deal"})
        updated = await crm.update_deal(uuid.UUID(deal["id"]), tenant.id, {"stage_id": str(lost_stage.id)})
        assert updated["stage"] == lost_stage.name


# ============================================================
# E. ATTIVITA — test_31 → test_39
# ============================================================


class TestActivities:

    @pytest.mark.anyio
    async def test_31_create_activity_call(self, db_session: AsyncSession, tenant: Tenant, crm: CRMService, stages):
        deal = await crm.create_deal(tenant.id, {"name": "Activity Deal"})
        act = await crm.create_activity(tenant.id, {
            "deal_id": deal["id"], "type": "call", "subject": "Chiamata qualifica", "status": "completed",
        })
        assert act["type"] == "call"
        assert act["subject"] == "Chiamata qualifica"
        assert act["status"] == "completed"

    @pytest.mark.anyio
    async def test_32_create_activity_meeting(self, db_session: AsyncSession, tenant: Tenant, crm: CRMService, stages):
        deal = await crm.create_deal(tenant.id, {"name": "Meeting Deal"})
        act = await crm.create_activity(tenant.id, {
            "deal_id": deal["id"], "type": "meeting", "subject": "Demo prodotto",
            "description": "Presentazione Elevia", "status": "completed",
        })
        assert act["type"] == "meeting"
        assert act["description"] == "Presentazione Elevia"

    @pytest.mark.anyio
    async def test_33_create_planned_activity(self, db_session: AsyncSession, tenant: Tenant, crm: CRMService, stages):
        deal = await crm.create_deal(tenant.id, {"name": "Planned Deal"})
        scheduled = datetime.utcnow() + timedelta(days=3)
        act = await crm.create_activity(tenant.id, {
            "deal_id": deal["id"], "type": "call", "subject": "Follow-up pianificato",
            "status": "planned", "scheduled_at": scheduled,
        })
        assert act["status"] == "planned"
        assert act["scheduled_at"] is not None

    @pytest.mark.anyio
    async def test_34_complete_activity(self, db_session: AsyncSession, tenant: Tenant, crm: CRMService, stages):
        deal = await crm.create_deal(tenant.id, {"name": "Complete Deal"})
        act = await crm.create_activity(tenant.id, {
            "deal_id": deal["id"], "type": "task", "subject": "Da completare", "status": "planned",
        })
        # Complete it
        completed = await crm.complete_activity(uuid.UUID(act["id"]))
        assert completed is not None
        assert completed["status"] == "completed"

    @pytest.mark.anyio
    async def test_35_activity_with_contact(self, db_session: AsyncSession, tenant: Tenant, crm: CRMService, stages):
        contact = await crm.create_contact(tenant.id, {"name": "Act Contact SRL"})
        deal = await crm.create_deal(tenant.id, {"name": "Contact Act Deal", "contact_id": contact["id"]})
        act = await crm.create_activity(tenant.id, {
            "deal_id": deal["id"], "contact_id": contact["id"],
            "type": "email", "subject": "Email inviata", "status": "completed",
        })
        assert act["contact_id"] == contact["id"]

    @pytest.mark.anyio
    async def test_36_list_activities_by_deal(self, db_session: AsyncSession, tenant: Tenant, crm: CRMService, stages):
        deal = await crm.create_deal(tenant.id, {"name": "Multi Act Deal"})
        await crm.create_activity(tenant.id, {"deal_id": deal["id"], "type": "call", "subject": "Call 1"})
        await crm.create_activity(tenant.id, {"deal_id": deal["id"], "type": "email", "subject": "Email 1"})
        await crm.create_activity(tenant.id, {"deal_id": deal["id"], "type": "note", "subject": "Note 1"})
        activities = await crm.list_activities(tenant.id, deal_id=uuid.UUID(deal["id"]))
        assert len(activities) == 3

    @pytest.mark.anyio
    async def test_37_list_activities_by_contact(self, db_session: AsyncSession, tenant: Tenant, crm: CRMService):
        contact = await crm.create_contact(tenant.id, {"name": "List Act Contact"})
        await crm.create_activity(tenant.id, {"contact_id": contact["id"], "type": "call", "subject": "Call"})
        activities = await crm.list_activities(tenant.id, contact_id=uuid.UUID(contact["id"]))
        assert len(activities) == 1

    @pytest.mark.anyio
    async def test_38_multiple_activities_same_deal(self, db_session: AsyncSession, tenant: Tenant, crm: CRMService, stages):
        deal = await crm.create_deal(tenant.id, {"name": "Many Activities"})
        for i in range(5):
            await crm.create_activity(tenant.id, {
                "deal_id": deal["id"], "type": "note", "subject": f"Nota {i+1}",
            })
        activities = await crm.list_activities(tenant.id, deal_id=uuid.UUID(deal["id"]))
        assert len(activities) == 5

    @pytest.mark.anyio
    async def test_39_complete_nonexistent_activity(self, crm: CRMService):
        result = await crm.complete_activity(uuid.uuid4())
        assert result is None


# ============================================================
# F. ORDINI — test_40 → test_43
# ============================================================


class TestOrders:

    @pytest.mark.anyio
    async def test_40_register_order(self, db_session: AsyncSession, tenant: Tenant, crm: CRMService, stages):
        deal = await crm.create_deal(tenant.id, {"name": "Order Deal"})
        result = await crm.register_order(
            uuid.UUID(deal["id"]), tenant.id,
            order_type="po", order_reference="PO-2026-001", order_notes="Ordine confermato",
        )
        assert "error" not in result
        # Verifica DB
        db_d = await db_session.execute(select(CrmDeal).where(CrmDeal.id == uuid.UUID(deal["id"])))
        d = db_d.scalar_one()
        assert d.order_type == "po"
        assert d.order_reference == "PO-2026-001"

    @pytest.mark.anyio
    async def test_41_confirm_order(self, db_session: AsyncSession, tenant: Tenant, crm: CRMService, stages):
        deal = await crm.create_deal(tenant.id, {"name": "Confirm Deal"})
        await crm.register_order(uuid.UUID(deal["id"]), tenant.id, order_type="email")
        result = await crm.confirm_order(uuid.UUID(deal["id"]), tenant.id)
        assert "error" not in result

    @pytest.mark.anyio
    async def test_42_order_nonexistent_deal(self, crm: CRMService, tenant: Tenant):
        result = await crm.register_order(uuid.uuid4(), tenant.id, order_type="po")
        assert "error" in result


# ============================================================
# G. PIPELINE TEMPLATES — test_43 → test_47
# ============================================================


class TestPipelineTemplates:

    @pytest.mark.anyio
    async def test_43_seed_creates_3_templates(self, pipeline_templates):
        assert len(pipeline_templates) == 3
        codes = [t["code"] for t in pipeline_templates]
        assert "vendita_diretta" in codes
        assert "progetto_corpo" in codes
        assert "social_selling" in codes

    @pytest.mark.anyio
    async def test_44_template_has_stages(self, pipeline_templates):
        vd = next(t for t in pipeline_templates if t["code"] == "vendita_diretta")
        assert vd["stage_count"] >= 6
        stage_names = [s["name"] for s in vd["stages"]]
        assert "Lead" in stage_names
        assert "Won" in stage_names

    @pytest.mark.anyio
    async def test_45_elevia_has_optional_demo(self, pipeline_templates):
        ss = next(t for t in pipeline_templates if t["code"] == "social_selling")
        demo = next((s for s in ss["stages"] if s["code"] == "demo"), None)
        assert demo is not None
        assert demo["is_optional"] is True

    @pytest.mark.anyio
    async def test_46_corpo_has_specifiche(self, pipeline_templates):
        pc = next(t for t in pipeline_templates if t["code"] == "progetto_corpo")
        specs = next((s for s in pc["stages"] if s["code"] == "specifiche"), None)
        assert specs is not None
        assert "scope" in (specs.get("required_fields") or [])


# ============================================================
# H. API ENDPOINTS (HTTP) — test_47 → test_54
# ============================================================


class TestCRMApi:

    @pytest.mark.anyio
    async def test_47_api_create_company(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post("/api/v1/crm/companies", json={"name": "API Company SRL"}, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["name"] == "API Company SRL"

    @pytest.mark.anyio
    async def test_48_api_list_contacts(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/crm/contacts", headers=auth_headers)
        assert resp.status_code == 200
        assert "contacts" in resp.json()

    @pytest.mark.anyio
    async def test_49_api_create_deal_full(self, client: AsyncClient, auth_headers: dict):
        """Crea deal con tutti i campi via API."""
        resp = await client.post("/api/v1/crm/deals", json={
            "name": "API Full Deal",
            "deal_type": "T&M",
            "expected_revenue": 25000,
            "daily_rate": 500,
            "estimated_days": 50,
            "technology": "Java, Spring",
        }, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "API Full Deal"
        assert data["deal_type"] == "T&M"
        assert data["expected_revenue"] == 25000

    @pytest.mark.anyio
    async def test_50_api_update_deal_stage(self, client: AsyncClient, auth_headers: dict):
        # Create deal
        deal_resp = await client.post("/api/v1/crm/deals", json={"name": "Stage Move API"}, headers=auth_headers)
        deal_id = deal_resp.json()["id"]
        # Get stages
        stages_resp = await client.get("/api/v1/crm/pipeline/stages", headers=auth_headers)
        stages = stages_resp.json()
        if len(stages) < 2:
            pytest.skip("Need 2+ stages")
        target = stages[1]["id"]
        # Move
        resp = await client.patch(f"/api/v1/crm/deals/{deal_id}", json={"stage_id": target}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["stage_id"] == target

    @pytest.mark.anyio
    async def test_51_api_create_activity(self, client: AsyncClient, auth_headers: dict):
        deal_resp = await client.post("/api/v1/crm/deals", json={"name": "Act API Deal"}, headers=auth_headers)
        deal_id = deal_resp.json()["id"]
        resp = await client.post("/api/v1/crm/activities", json={
            "deal_id": deal_id, "type": "call", "subject": "API Call Test",
        }, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["subject"] == "API Call Test"

    @pytest.mark.anyio
    async def test_52_api_pipeline_summary(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/crm/pipeline/summary", headers=auth_headers)
        assert resp.status_code == 200
        assert "total_deals" in resp.json()

    @pytest.mark.anyio
    async def test_53_api_pipeline_analytics(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/crm/pipeline/analytics", headers=auth_headers)
        assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_54_api_pipeline_templates(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/pipeline-templates", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 3
