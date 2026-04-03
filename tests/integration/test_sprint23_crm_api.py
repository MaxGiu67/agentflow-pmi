"""Sprint 23 tests — US-87 (contacts), US-88 (deals+stages), US-89 (activities), US-99 (migration).

Tests verify CRM internal DB CRUD, pipeline stages, activities, and API endpoints.
"""

import uuid
from datetime import date, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import CrmContact, CrmDeal, CrmPipelineStage, CrmActivity, Tenant
from api.modules.crm.service import CRMService


# ============================================================
# US-87: Modello contatti CRM
# ============================================================


@pytest.mark.asyncio
async def test_ac_87_1_crud_contacts(db_session: AsyncSession, tenant: Tenant):
    """AC-87.1: CRUD completo su crm_contacts."""
    svc = CRMService(db_session)

    # Create
    c = await svc.create_contact(tenant.id, {
        "name": "Acme Italia SPA",
        "type": "cliente",
        "vat": "12345678901",
        "email": "info@acme.it",
        "phone": "+39 02 1234567",
    })
    assert c["name"] == "Acme Italia SPA"
    assert c["vat"] == "12345678901"
    contact_id = uuid.UUID(c["id"])

    # Read (list)
    result = await svc.list_contacts(tenant.id)
    assert result["total"] == 1

    # Update
    updated = await svc.update_contact(contact_id, {"city": "Milano", "province": "MI"})
    assert updated["city"] == "Milano"

    # Delete
    ok = await svc.delete_contact(contact_id)
    assert ok is True
    result2 = await svc.list_contacts(tenant.id)
    assert result2["total"] == 0


@pytest.mark.asyncio
async def test_ac_87_2_ricerca_contatti(db_session: AsyncSession, tenant: Tenant):
    """AC-87.2: Ricerca per nome, P.IVA, email."""
    svc = CRMService(db_session)
    await svc.create_contact(tenant.id, {"name": "Beta Consulting SRL", "vat": "99887766554", "email": "info@beta.it"})
    await svc.create_contact(tenant.id, {"name": "Gamma Tech SPA", "vat": "11223344556", "email": "hello@gamma.it"})

    # Search by name
    r = await svc.list_contacts(tenant.id, search="Beta")
    assert r["total"] == 1
    assert r["contacts"][0]["name"] == "Beta Consulting SRL"

    # Search by P.IVA
    r = await svc.list_contacts(tenant.id, search="11223344556")
    assert r["total"] == 1

    # Search by email
    r = await svc.list_contacts(tenant.id, search="gamma")
    assert r["total"] == 1


@pytest.mark.asyncio
async def test_ac_87_3_filtro_tipo(db_session: AsyncSession, tenant: Tenant):
    """AC-87.3: Filtro per tipo."""
    svc = CRMService(db_session)
    await svc.create_contact(tenant.id, {"name": "Lead SRL", "type": "lead"})
    await svc.create_contact(tenant.id, {"name": "Cliente SRL", "type": "cliente"})

    r_lead = await svc.list_contacts(tenant.id, contact_type="lead")
    assert r_lead["total"] == 1
    assert r_lead["contacts"][0]["name"] == "Lead SRL"

    r_cliente = await svc.list_contacts(tenant.id, contact_type="cliente")
    assert r_cliente["total"] == 1


@pytest.mark.asyncio
async def test_ac_87_4_assegnazione_commerciale(db_session: AsyncSession, tenant: Tenant, verified_user):
    """AC-87.4: Assegnazione contatto a un commerciale."""
    svc = CRMService(db_session)
    c = await svc.create_contact(tenant.id, {
        "name": "Assegnato SRL",
        "assigned_to": str(verified_user.id),
    })
    assert c["assigned_to"] == str(verified_user.id)


@pytest.mark.asyncio
async def test_ac_87_5_email_opt_in(db_session: AsyncSession, tenant: Tenant):
    """AC-87.5: Campo email_opt_in per GDPR."""
    svc = CRMService(db_session)
    c = await svc.create_contact(tenant.id, {"name": "NoMail SRL", "email_opt_in": False})
    assert c["email_opt_in"] is False

    c2 = await svc.create_contact(tenant.id, {"name": "Mail SRL"})
    assert c2["email_opt_in"] is True  # default


# ============================================================
# US-88: Modello deal + pipeline stages
# ============================================================


@pytest.mark.asyncio
async def test_ac_88_1_crud_deal(db_session: AsyncSession, tenant: Tenant):
    """AC-88.1: CRUD deal."""
    svc = CRMService(db_session)
    contact = await svc.create_contact(tenant.id, {"name": "Deal Client SRL"})

    deal = await svc.create_deal(tenant.id, {
        "name": "Progetto SAP Migration",
        "contact_id": contact["id"],
        "deal_type": "T&M",
        "expected_revenue": 45000.0,
        "daily_rate": 500.0,
        "estimated_days": 90.0,
        "technology": "SAP S/4HANA",
    })
    assert deal["name"] == "Progetto SAP Migration"
    assert deal["deal_type"] == "T&M"
    assert deal["expected_revenue"] == 45000.0
    assert deal["daily_rate"] == 500.0
    assert deal["client_name"] == "Deal Client SRL"

    # List
    deals = await svc.list_deals(tenant.id)
    assert deals["total"] == 1


@pytest.mark.asyncio
async def test_ac_88_2_pipeline_stages_configurabili(db_session: AsyncSession, tenant: Tenant):
    """AC-88.2: Pipeline stages configurabili per tenant."""
    svc = CRMService(db_session)
    stages = await svc.get_stages(tenant.id)

    assert len(stages) == 6
    assert stages[0]["name"] == "Nuovo Lead"
    assert stages[0]["probability_default"] == 10.0
    assert stages[4]["name"] == "Confermato"
    assert stages[4]["is_won"] is True
    assert stages[5]["name"] == "Perso"
    assert stages[5]["is_lost"] is True


@pytest.mark.asyncio
async def test_ac_88_3_auto_probabilita(db_session: AsyncSession, tenant: Tenant):
    """AC-88.3: Quando un deal cambia stage, la probabilita si aggiorna."""
    svc = CRMService(db_session)
    deal = await svc.create_deal(tenant.id, {"name": "Auto Prob Deal"})
    assert deal["probability"] == 10.0  # first stage default

    stages = await svc.get_stages(tenant.id)
    qualificato_id = next(s["id"] for s in stages if s["name"] == "Qualificato")

    updated = await svc.update_deal(uuid.UUID(deal["id"]), tenant.id, {"stage_id": qualificato_id})
    assert updated["probability"] == 30.0
    assert updated["stage"] == "Qualificato"


@pytest.mark.asyncio
async def test_ac_88_4_deal_types(db_session: AsyncSession, tenant: Tenant):
    """AC-88.4: Deal type T&M, fixed, spot, hardware."""
    svc = CRMService(db_session)
    for dt in ["T&M", "fixed", "spot", "hardware"]:
        d = await svc.create_deal(tenant.id, {"name": f"Deal {dt}", "deal_type": dt})
        assert d["deal_type"] == dt

    # Filter by type
    tm = await svc.list_deals(tenant.id, deal_type="T&M")
    assert tm["total"] == 1


@pytest.mark.asyncio
async def test_ac_88_5_ordine_cliente(db_session: AsyncSession, tenant: Tenant):
    """AC-88.5: Registrazione ordine cliente."""
    svc = CRMService(db_session)
    deal = await svc.create_deal(tenant.id, {"name": "Order Deal"})
    deal_id = uuid.UUID(deal["id"])

    result = await svc.register_order(deal_id, tenant.id, "po", "PO-2026-001", "Urgente")
    assert result["status"] == "registered"
    assert result["order_type"] == "po"

    # Verify deal moved to "Ordine Ricevuto"
    d = await svc.get_deal(deal_id, tenant.id)
    assert d["stage"] == "Ordine Ricevuto"
    assert d["order_reference"] == "PO-2026-001"


@pytest.mark.asyncio
async def test_ac_88_6_stages_default(db_session: AsyncSession, tenant: Tenant):
    """AC-88.6: Stages default creati automaticamente."""
    svc = CRMService(db_session)
    # First call creates stages
    stages1 = await svc.get_stages(tenant.id)
    assert len(stages1) == 6

    # Second call doesn't duplicate
    stages2 = await svc.get_stages(tenant.id)
    assert len(stages2) == 6


# ============================================================
# US-89: Modello attivita CRM
# ============================================================


@pytest.mark.asyncio
async def test_ac_89_1_crud_activity(db_session: AsyncSession, tenant: Tenant):
    """AC-89.1: CRUD attivita."""
    svc = CRMService(db_session)
    contact = await svc.create_contact(tenant.id, {"name": "Activity Client"})
    deal = await svc.create_deal(tenant.id, {"name": "Activity Deal", "contact_id": contact["id"]})

    activity = await svc.create_activity(tenant.id, {
        "deal_id": deal["id"],
        "contact_id": contact["id"],
        "type": "call",
        "subject": "Chiamata introduttiva",
        "description": "Presentazione servizi NExadata",
    })
    assert activity["type"] == "call"
    assert activity["subject"] == "Chiamata introduttiva"
    assert activity["status"] == "planned"


@pytest.mark.asyncio
async def test_ac_89_2_lista_per_deal(db_session: AsyncSession, tenant: Tenant):
    """AC-89.2: Lista attivita per deal."""
    svc = CRMService(db_session)
    deal = await svc.create_deal(tenant.id, {"name": "Deal Activities"})
    deal_id = deal["id"]

    await svc.create_activity(tenant.id, {"deal_id": deal_id, "type": "call", "subject": "Call 1"})
    await svc.create_activity(tenant.id, {"deal_id": deal_id, "type": "email", "subject": "Email 1"})

    activities = await svc.list_activities(tenant.id, deal_id=uuid.UUID(deal_id))
    assert len(activities) == 2


@pytest.mark.asyncio
async def test_ac_89_3_lista_per_contatto(db_session: AsyncSession, tenant: Tenant):
    """AC-89.3: Lista attivita per contatto."""
    svc = CRMService(db_session)
    contact = await svc.create_contact(tenant.id, {"name": "Contact Activities"})
    contact_id = contact["id"]

    await svc.create_activity(tenant.id, {"contact_id": contact_id, "type": "meeting", "subject": "Meeting 1"})

    activities = await svc.list_activities(tenant.id, contact_id=uuid.UUID(contact_id))
    assert len(activities) == 1


@pytest.mark.asyncio
async def test_ac_89_4_filtro_tipo_status(db_session: AsyncSession, tenant: Tenant):
    """AC-89.4: Filtro per tipo e status."""
    svc = CRMService(db_session)
    await svc.create_activity(tenant.id, {"type": "call", "subject": "Call", "status": "planned"})
    await svc.create_activity(tenant.id, {"type": "email", "subject": "Email", "status": "completed"})

    calls = await svc.list_activities(tenant.id, activity_type="call")
    assert len(calls) == 1

    completed = await svc.list_activities(tenant.id, status="completed")
    assert len(completed) == 1


@pytest.mark.asyncio
async def test_ac_89_5_last_contact_at(db_session: AsyncSession, tenant: Tenant):
    """AC-89.5: Completamento attivita aggiorna last_contact_at."""
    svc = CRMService(db_session)
    contact = await svc.create_contact(tenant.id, {"name": "LastContact SRL"})
    contact_id = uuid.UUID(contact["id"])

    activity = await svc.create_activity(tenant.id, {
        "contact_id": str(contact_id),
        "type": "call",
        "subject": "Follow-up",
    })

    # Complete the activity
    completed = await svc.complete_activity(uuid.UUID(activity["id"]))
    assert completed["status"] == "completed"
    assert completed["completed_at"] is not None

    # Verify contact.last_contact_at updated
    result = await db_session.execute(
        select(CrmContact).where(CrmContact.id == contact_id)
    )
    c = result.scalar_one()
    assert c.last_contact_at is not None


# ============================================================
# US-99: Migration — API endpoint tests
# ============================================================


@pytest.mark.asyncio
async def test_ac_99_1_api_contacts(client: AsyncClient, auth_headers: dict, tenant: Tenant):
    """AC-99.1: GET /crm/contacts funziona con DB interno."""
    resp = await client.get("/api/v1/crm/contacts", headers=auth_headers)
    assert resp.status_code == 200
    assert "contacts" in resp.json()


@pytest.mark.asyncio
async def test_ac_99_2_api_deals(client: AsyncClient, auth_headers: dict, tenant: Tenant):
    """AC-99.2: GET /crm/deals funziona con DB interno."""
    resp = await client.get("/api/v1/crm/deals", headers=auth_headers)
    assert resp.status_code == 200
    assert "deals" in resp.json()


@pytest.mark.asyncio
async def test_ac_99_3_api_pipeline_summary(client: AsyncClient, auth_headers: dict):
    """AC-99.3: GET /crm/pipeline/summary funziona."""
    resp = await client.get("/api/v1/crm/pipeline/summary", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_deals" in data
    assert "by_stage" in data


@pytest.mark.asyncio
async def test_ac_99_4_api_create_deal(client: AsyncClient, auth_headers: dict):
    """AC-99.4: POST /crm/deals scrive su DB interno."""
    resp = await client.post(
        "/api/v1/crm/deals",
        json={"name": "API Test Deal", "deal_type": "T&M", "expected_revenue": 10000.0},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "API Test Deal"


@pytest.mark.asyncio
async def test_ac_99_5_api_pipeline_stages(client: AsyncClient, auth_headers: dict):
    """AC-99.5: GET /crm/pipeline/stages returns 6 default stages."""
    resp = await client.get("/api/v1/crm/pipeline/stages", headers=auth_headers)
    assert resp.status_code == 200
    stages = resp.json()
    assert len(stages) == 6
    assert stages[0]["name"] == "Nuovo Lead"


@pytest.mark.asyncio
async def test_ac_99_api_order_flow(client: AsyncClient, auth_headers: dict):
    """AC-99: Full order flow via API — create deal, register order, confirm."""
    # Create deal
    deal_resp = await client.post(
        "/api/v1/crm/deals",
        json={"name": "Order Flow Deal"},
        headers=auth_headers,
    )
    deal_id = deal_resp.json()["id"]

    # Register order
    order_resp = await client.post(
        f"/api/v1/crm/deals/{deal_id}/order",
        json={"order_type": "po", "order_reference": "PO-TEST-001"},
        headers=auth_headers,
    )
    assert order_resp.status_code == 200
    assert order_resp.json()["status"] == "registered"

    # Confirm order
    confirm_resp = await client.post(
        f"/api/v1/crm/deals/{deal_id}/order/confirm",
        headers=auth_headers,
    )
    assert confirm_resp.status_code == 200
    assert confirm_resp.json()["status"] == "confirmed"

    # Verify won
    won_resp = await client.get("/api/v1/crm/deals/won", headers=auth_headers)
    assert won_resp.json()["total"] >= 1


@pytest.mark.asyncio
async def test_ac_99_api_activities(client: AsyncClient, auth_headers: dict):
    """AC-99: Activities API endpoints work."""
    # Create activity
    resp = await client.post(
        "/api/v1/crm/activities",
        json={"type": "note", "subject": "API test note"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    activity_id = resp.json()["id"]

    # List activities
    list_resp = await client.get("/api/v1/crm/activities", headers=auth_headers)
    assert list_resp.status_code == 200

    # Complete
    complete_resp = await client.post(
        f"/api/v1/crm/activities/{activity_id}/complete",
        headers=auth_headers,
    )
    assert complete_resp.status_code == 200
    assert complete_resp.json()["status"] == "completed"
