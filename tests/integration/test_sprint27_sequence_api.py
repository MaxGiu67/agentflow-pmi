"""Sprint 27 tests — US-97 (sequences), US-98 (triggers)."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import EmailCampaign, Tenant
from api.modules.email_marketing.service import EmailMarketingService
from api.modules.crm.service import CRMService


@pytest.mark.asyncio
async def test_ac_97_1_create_sequence(db_session: AsyncSession, tenant: Tenant):
    """AC-97.1: Create sequence with trigger."""
    svc = EmailMarketingService(db_session)
    seq = await svc.create_sequence(tenant.id, {
        "name": "Welcome Sequence",
        "trigger_event": "contact_created",
    })
    assert seq["name"] == "Welcome Sequence"
    assert seq["type"] == "sequence"
    assert seq["trigger_event"] == "contact_created"
    assert seq["status"] == "draft"


@pytest.mark.asyncio
async def test_ac_97_2_add_steps(db_session: AsyncSession, tenant: Tenant):
    """AC-97.2: Add steps with template, delay, condition."""
    svc = EmailMarketingService(db_session)
    tpl = await svc.create_template(tenant.id, {
        "name": "Step Tpl", "subject": "Hi", "html_body": "<p>Hi {{nome}}</p>",
    })

    seq = await svc.create_sequence(tenant.id, {"name": "Test Seq"})
    campaign_id = uuid.UUID(seq["id"])

    step1 = await svc.add_sequence_step(campaign_id, {
        "template_id": tpl["id"], "step_order": 1, "delay_days": 0,
        "condition_type": "none",
    })
    step2 = await svc.add_sequence_step(campaign_id, {
        "template_id": tpl["id"], "step_order": 2, "delay_days": 3,
        "condition_type": "if_not_opened",
    })

    steps = await svc.get_sequence_steps(campaign_id)
    assert len(steps) == 2
    assert steps[0]["delay_days"] == 0
    assert steps[1]["delay_days"] == 3
    assert steps[1]["condition_type"] == "if_not_opened"


@pytest.mark.asyncio
async def test_ac_97_3_4_process_with_condition(db_session: AsyncSession, tenant: Tenant):
    """AC-97.3/97.4: if_not_opened skips when email was opened."""
    crm = CRMService(db_session)
    contact = await crm.create_contact(tenant.id, {"name": "Cond Test", "email": "cond@test.it"})
    contact_id = uuid.UUID(contact["id"])

    svc = EmailMarketingService(db_session)
    tpl = await svc.create_template(tenant.id, {
        "name": "Cond Tpl", "subject": "Test", "html_body": "<p>{{nome}}</p>",
    })

    seq = await svc.create_sequence(tenant.id, {"name": "Cond Seq"})
    campaign_id = uuid.UUID(seq["id"])

    await svc.add_sequence_step(campaign_id, {
        "template_id": tpl["id"], "step_order": 1, "delay_days": 0, "condition_type": "none",
    })
    await svc.add_sequence_step(campaign_id, {
        "template_id": tpl["id"], "step_order": 2, "delay_days": 0, "condition_type": "if_not_opened",
    })

    enroll = await svc.enroll_contact(tenant.id, campaign_id, contact_id)
    enrollment_id = uuid.UUID(enroll["id"])

    # Process step 1 (no condition)
    r1 = await svc.process_sequence_step(enrollment_id)
    assert r1["status"] == "sent"

    # Simulate open on step 1
    sends = await svc.list_sends(tenant.id, contact_id=contact_id)
    await svc.process_webhook_event({
        "event": "opened",
        "message-id": sends[0]["brevo_message_id"],
        "date": "2026-04-03T10:00:00Z",
    })

    # Process step 2 (if_not_opened) — should SKIP because email was opened
    r2 = await svc.process_sequence_step(enrollment_id)
    assert r2["status"] == "skipped"


@pytest.mark.asyncio
async def test_ac_97_enroll_prevent_duplicate(db_session: AsyncSession, tenant: Tenant):
    """AC-98.4: Cannot enroll same contact twice in same sequence."""
    crm = CRMService(db_session)
    contact = await crm.create_contact(tenant.id, {"name": "Dup", "email": "dup@test.it"})
    contact_id = uuid.UUID(contact["id"])

    svc = EmailMarketingService(db_session)
    seq = await svc.create_sequence(tenant.id, {"name": "Dup Seq"})
    campaign_id = uuid.UUID(seq["id"])

    r1 = await svc.enroll_contact(tenant.id, campaign_id, contact_id)
    assert r1["status"] == "enrolled"

    r2 = await svc.enroll_contact(tenant.id, campaign_id, contact_id)
    assert r2["status"] == "already_enrolled"


@pytest.mark.asyncio
async def test_ac_97_sequence_completion(db_session: AsyncSession, tenant: Tenant):
    """AC-97: Sequence completes after all steps processed."""
    crm = CRMService(db_session)
    contact = await crm.create_contact(tenant.id, {"name": "Complete", "email": "done@test.it"})

    svc = EmailMarketingService(db_session)
    tpl = await svc.create_template(tenant.id, {
        "name": "Done Tpl", "subject": "Hi", "html_body": "<p>Hi</p>",
    })
    seq = await svc.create_sequence(tenant.id, {"name": "Short Seq"})
    campaign_id = uuid.UUID(seq["id"])

    await svc.add_sequence_step(campaign_id, {
        "template_id": tpl["id"], "step_order": 1, "delay_days": 0,
    })

    enroll = await svc.enroll_contact(tenant.id, campaign_id, uuid.UUID(contact["id"]))
    enrollment_id = uuid.UUID(enroll["id"])

    r = await svc.process_sequence_step(enrollment_id)
    assert r["status"] == "sent"

    # No more steps — enrollment already completed after last step
    r2 = await svc.process_sequence_step(enrollment_id)
    assert r2["status"] in ("completed", "skipped")  # already completed


# ============================================================
# US-98: Trigger automatici
# ============================================================


@pytest.mark.asyncio
async def test_ac_98_1_trigger_deal_stage_changed(db_session: AsyncSession, tenant: Tenant):
    """AC-98.1: Trigger on deal_stage_changed enrolls contact."""
    crm = CRMService(db_session)
    contact = await crm.create_contact(tenant.id, {"name": "Trigger Client", "email": "trigger@test.it"})

    svc = EmailMarketingService(db_session)
    tpl = await svc.create_template(tenant.id, {
        "name": "Trigger Tpl", "subject": "Follow-up", "html_body": "<p>Hi</p>",
    })

    seq = await svc.create_sequence(tenant.id, {
        "name": "Proposta Follow-up",
        "trigger_event": "deal_stage_changed",
        "trigger_config": {"stage": "Proposta Inviata"},
    })
    campaign_id = uuid.UUID(seq["id"])
    await svc.add_sequence_step(campaign_id, {"template_id": tpl["id"], "step_order": 1})

    # Activate campaign
    from sqlalchemy import select
    result = await db_session.execute(
        select(EmailCampaign).where(EmailCampaign.id == campaign_id)
    )
    campaign = result.scalar_one()
    campaign.status = "active"
    await db_session.flush()

    # Trigger event
    results = await svc.trigger_on_event(tenant.id, "deal_stage_changed", {
        "contact_id": contact["id"],
        "stage": "Proposta Inviata",
    })

    assert len(results) == 1
    assert results[0]["status"] == "enrolled"


@pytest.mark.asyncio
async def test_ac_98_2_trigger_contact_created(db_session: AsyncSession, tenant: Tenant):
    """AC-98.2: Trigger on contact_created."""
    svc = EmailMarketingService(db_session)
    tpl = await svc.create_template(tenant.id, {
        "name": "Welcome", "subject": "Benvenuto", "html_body": "<p>Welcome</p>",
    })
    seq = await svc.create_sequence(tenant.id, {
        "name": "Welcome Seq",
        "trigger_event": "contact_created",
    })
    campaign_id = uuid.UUID(seq["id"])
    await svc.add_sequence_step(campaign_id, {"template_id": tpl["id"], "step_order": 1})

    # Activate
    from sqlalchemy import select
    result = await db_session.execute(
        select(EmailCampaign).where(EmailCampaign.id == campaign_id)
    )
    result.scalar_one().status = "active"
    await db_session.flush()

    # Create contact and trigger
    crm = CRMService(db_session)
    contact = await crm.create_contact(tenant.id, {"name": "New Lead", "email": "new@lead.it", "type": "lead"})

    results = await svc.trigger_on_event(tenant.id, "contact_created", {
        "contact_id": contact["id"],
    })
    assert len(results) == 1
    assert results[0]["status"] == "enrolled"


@pytest.mark.asyncio
async def test_ac_98_3_trigger_config_filter(db_session: AsyncSession, tenant: Tenant):
    """AC-98.3: Trigger config filters by stage — non-matching stage ignored."""
    svc = EmailMarketingService(db_session)
    tpl = await svc.create_template(tenant.id, {
        "name": "Filter Tpl", "subject": "Hi", "html_body": "<p>Hi</p>",
    })
    seq = await svc.create_sequence(tenant.id, {
        "name": "Filtered",
        "trigger_event": "deal_stage_changed",
        "trigger_config": {"stage": "Ordine Ricevuto"},
    })
    campaign_id = uuid.UUID(seq["id"])
    await svc.add_sequence_step(campaign_id, {"template_id": tpl["id"], "step_order": 1})

    from sqlalchemy import select
    r = await db_session.execute(select(EmailCampaign).where(EmailCampaign.id == campaign_id))
    r.scalar_one().status = "active"
    await db_session.flush()

    crm = CRMService(db_session)
    contact = await crm.create_contact(tenant.id, {"name": "Filter Client", "email": "filter@t.it"})

    # Wrong stage → should NOT enroll
    results = await svc.trigger_on_event(tenant.id, "deal_stage_changed", {
        "contact_id": contact["id"],
        "stage": "Qualificato",
    })
    assert len(results) == 0

    # Correct stage → should enroll
    results = await svc.trigger_on_event(tenant.id, "deal_stage_changed", {
        "contact_id": contact["id"],
        "stage": "Ordine Ricevuto",
    })
    assert len(results) == 1


# ============================================================
# API Endpoints
# ============================================================


@pytest.mark.asyncio
async def test_api_create_sequence(client, auth_headers):
    """API: POST /email/sequences."""
    resp = await client.post(
        "/api/v1/email/sequences",
        json={"name": "API Seq", "trigger_event": "manual"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "API Seq"


@pytest.mark.asyncio
async def test_api_sequence_steps(client, auth_headers):
    """API: POST + GET /email/sequences/{id}/steps."""
    # Create sequence
    seq_resp = await client.post(
        "/api/v1/email/sequences",
        json={"name": "Steps API Seq"},
        headers=auth_headers,
    )
    seq_id = seq_resp.json()["id"]

    # Create template
    tpl_resp = await client.post(
        "/api/v1/email/templates",
        json={"name": "API Step Tpl", "subject": "Hi", "html_body": "<p>Hi</p>"},
        headers=auth_headers,
    )
    tpl_id = tpl_resp.json()["id"]

    # Add step
    step_resp = await client.post(
        f"/api/v1/email/sequences/{seq_id}/steps",
        json={"template_id": tpl_id, "step_order": 1, "delay_days": 2},
        headers=auth_headers,
    )
    assert step_resp.status_code == 201

    # Get steps
    get_resp = await client.get(
        f"/api/v1/email/sequences/{seq_id}/steps",
        headers=auth_headers,
    )
    assert get_resp.status_code == 200
    assert len(get_resp.json()) == 1
