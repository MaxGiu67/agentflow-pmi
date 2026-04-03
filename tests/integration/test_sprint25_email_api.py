"""Sprint 25 tests — US-92 (Brevo adapter), US-93 (webhook), US-94 (templates)."""

import uuid
from datetime import datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import EmailTemplate, EmailSend, EmailEvent, CrmContact, Tenant
from api.modules.email_marketing.service import EmailMarketingService


# ============================================================
# US-92: Adapter Brevo (mock — no real API calls)
# ============================================================


@pytest.mark.asyncio
async def test_ac_92_1_send_email_mock(db_session: AsyncSession, tenant: Tenant):
    """AC-92.1/92.2/92.3: Send email via service (mocked Brevo)."""
    svc = EmailMarketingService(db_session)

    result = await svc.send_email(
        tenant_id=tenant.id,
        to_email="cliente@example.com",
        to_name="Mario Rossi",
        subject="Test email {{nome}}",
        html_body="<p>Ciao {{nome}}, come va?</p>",
        params={"nome": "Mario"},
    )

    assert result["status"] == "sent"
    assert result["to_email"] == "cliente@example.com"
    assert "brevo_message_id" in result
    assert result["brevo_message_id"].startswith("mock-")
    # Subject should have variable substituted
    assert result["subject"] == "Test email Mario"


@pytest.mark.asyncio
async def test_ac_92_send_records_in_db(db_session: AsyncSession, tenant: Tenant):
    """AC-92: Send is recorded in email_sends table."""
    svc = EmailMarketingService(db_session)
    await svc.send_email(
        tenant_id=tenant.id,
        to_email="db@example.com",
        to_name="DB Test",
        subject="DB Test",
        html_body="<p>Test</p>",
    )

    sends = await svc.list_sends(tenant.id)
    assert len(sends) == 1
    assert sends[0]["to_email"] == "db@example.com"
    assert sends[0]["status"] == "sent"


# ============================================================
# US-93: Webhook email tracking
# ============================================================


@pytest.mark.asyncio
async def test_ac_93_3_webhook_opened(db_session: AsyncSession, tenant: Tenant):
    """AC-93.3: Evento 'opened' aggiorna send.opened_at e open_count."""
    svc = EmailMarketingService(db_session)
    send_result = await svc.send_email(
        tenant_id=tenant.id, to_email="open@test.com", to_name="Open Test",
        subject="Open test", html_body="<p>Hi</p>",
    )
    msg_id = send_result["brevo_message_id"]

    # Simulate webhook
    result = await svc.process_webhook_event({
        "event": "opened",
        "message-id": msg_id,
        "date": "2026-04-03T10:30:00Z",
        "ip": "1.2.3.4",
    })
    assert result["status"] == "processed"
    assert result["event_type"] == "opened"

    # Verify send updated
    sends = await svc.list_sends(tenant.id)
    send = next(s for s in sends if s["brevo_message_id"] == msg_id)
    assert send["status"] == "opened"
    assert send["open_count"] == 1
    assert send["opened_at"] is not None


@pytest.mark.asyncio
async def test_ac_93_4_webhook_clicked(db_session: AsyncSession, tenant: Tenant):
    """AC-93.4: Evento 'click' aggiorna send.clicked_at e salva URL."""
    svc = EmailMarketingService(db_session)
    send_result = await svc.send_email(
        tenant_id=tenant.id, to_email="click@test.com", to_name="Click",
        subject="Click test", html_body="<p>Click <a href='https://example.com'>here</a></p>",
    )
    msg_id = send_result["brevo_message_id"]

    result = await svc.process_webhook_event({
        "event": "click",
        "message-id": msg_id,
        "link": "https://example.com",
        "date": "2026-04-03T11:00:00Z",
    })
    assert result["event_type"] == "clicked"

    sends = await svc.list_sends(tenant.id)
    send = next(s for s in sends if s["brevo_message_id"] == msg_id)
    assert send["status"] == "clicked"
    assert send["click_count"] == 1


@pytest.mark.asyncio
async def test_ac_93_5_webhook_bounce_marks_contact(db_session: AsyncSession, tenant: Tenant):
    """AC-93.5: Hard bounce marks contact email_opt_in=False."""
    svc = EmailMarketingService(db_session)

    # Create contact
    from api.modules.crm.service import CRMService
    crm = CRMService(db_session)
    contact = await crm.create_contact(tenant.id, {"name": "Bounce SRL", "email": "bounce@invalid.com"})
    contact_id = uuid.UUID(contact["id"])

    # Send email to contact
    send_result = await svc.send_email(
        tenant_id=tenant.id, to_email="bounce@invalid.com", to_name="Bounce",
        subject="Bounce test", html_body="<p>Test</p>",
        contact_id=contact_id,
    )

    # Simulate hard bounce
    await svc.process_webhook_event({
        "event": "hard_bounce",
        "message-id": send_result["brevo_message_id"],
        "date": "2026-04-03T12:00:00Z",
    })

    # Verify contact opt-in disabled
    from sqlalchemy import select
    result = await db_session.execute(
        select(CrmContact).where(CrmContact.id == contact_id)
    )
    c = result.scalar_one()
    assert c.email_opt_in is False


@pytest.mark.asyncio
async def test_ac_93_6_webhook_unsubscribed(db_session: AsyncSession, tenant: Tenant):
    """AC-93.6: Unsubscribe sets email_opt_in=False."""
    svc = EmailMarketingService(db_session)
    from api.modules.crm.service import CRMService
    crm = CRMService(db_session)
    contact = await crm.create_contact(tenant.id, {"name": "Unsub SRL", "email": "unsub@test.com"})
    contact_id = uuid.UUID(contact["id"])

    send_result = await svc.send_email(
        tenant_id=tenant.id, to_email="unsub@test.com", to_name="Unsub",
        subject="Test", html_body="<p>Test</p>",
        contact_id=contact_id,
    )

    await svc.process_webhook_event({
        "event": "unsubscribed",
        "message-id": send_result["brevo_message_id"],
        "date": "2026-04-03T13:00:00Z",
    })

    from sqlalchemy import select
    result = await db_session.execute(
        select(CrmContact).where(CrmContact.id == contact_id)
    )
    assert result.scalar_one().email_opt_in is False


@pytest.mark.asyncio
async def test_ac_93_ignored_unknown_message(db_session: AsyncSession, tenant: Tenant):
    """AC-93: Webhook with unknown message ID is ignored."""
    svc = EmailMarketingService(db_session)
    result = await svc.process_webhook_event({
        "event": "opened",
        "message-id": "nonexistent-id",
        "date": "2026-04-03T10:00:00Z",
    })
    assert result["status"] == "ignored"


# ============================================================
# US-94: Email templates
# ============================================================


@pytest.mark.asyncio
async def test_ac_94_1_crud_templates(db_session: AsyncSession, tenant: Tenant):
    """AC-94.1: CRUD email templates."""
    svc = EmailMarketingService(db_session)

    # Create
    tpl = await svc.create_template(tenant.id, {
        "name": "Test Template",
        "subject": "Subject {{nome}}",
        "html_body": "<p>Hello {{nome}}</p>",
        "variables": ["nome"],
        "category": "followup",
    })
    assert tpl["name"] == "Test Template"
    tpl_id = uuid.UUID(tpl["id"])

    # Read
    loaded = await svc.get_template(tpl_id)
    assert loaded["name"] == "Test Template"

    # Update
    updated = await svc.update_template(tpl_id, {"name": "Updated Template"})
    assert updated["name"] == "Updated Template"


@pytest.mark.asyncio
async def test_ac_94_4_preview(db_session: AsyncSession, tenant: Tenant):
    """AC-94.4: Preview template with sample data."""
    svc = EmailMarketingService(db_session)
    tpl = await svc.create_template(tenant.id, {
        "name": "Preview Test",
        "subject": "Ciao {{nome}}",
        "html_body": "<p>Proposta per {{deal_name}}: {{deal_value}} EUR</p>",
        "variables": ["nome", "deal_name", "deal_value"],
    })

    preview = await svc.preview_template(uuid.UUID(tpl["id"]), {
        "nome": "Marco",
        "deal_name": "SAP Migration",
        "deal_value": "45000",
    })
    assert preview["subject"] == "Ciao Marco"
    assert "SAP Migration" in preview["html_body"]
    assert "45000" in preview["html_body"]


@pytest.mark.asyncio
async def test_ac_94_6_default_templates(db_session: AsyncSession, tenant: Tenant):
    """AC-94.6: Default templates pre-loaded."""
    svc = EmailMarketingService(db_session)
    templates = await svc.list_templates(tenant.id)

    assert len(templates) >= 3
    names = [t["name"] for t in templates]
    assert "Benvenuto" in names
    assert "Follow-up proposta" in names
    assert "Reminder scadenza" in names


@pytest.mark.asyncio
async def test_ac_94_5_categories(db_session: AsyncSession, tenant: Tenant):
    """AC-94.5: Template categories."""
    svc = EmailMarketingService(db_session)
    templates = await svc.list_templates(tenant.id)

    categories = {t["category"] for t in templates}
    assert "welcome" in categories
    assert "followup" in categories
    assert "reminder" in categories


# ============================================================
# API Endpoints
# ============================================================


@pytest.mark.asyncio
async def test_api_templates(client: AsyncClient, auth_headers: dict):
    """API: GET /email/templates returns defaults."""
    resp = await client.get("/api/v1/email/templates", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 3


@pytest.mark.asyncio
async def test_api_send_email(client: AsyncClient, auth_headers: dict):
    """API: POST /email/send."""
    resp = await client.post(
        "/api/v1/email/send",
        json={
            "to_email": "api@test.com",
            "to_name": "API Test",
            "subject": "API test",
            "html_body": "<p>Test from API</p>",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "sent"


@pytest.mark.asyncio
async def test_api_email_stats(client: AsyncClient, auth_headers: dict):
    """API: GET /email/stats."""
    resp = await client.get("/api/v1/email/stats", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_sent" in data
    assert "open_rate" in data


@pytest.mark.asyncio
async def test_api_webhook(client: AsyncClient):
    """API: POST /email/webhook (no auth required)."""
    resp = await client.post(
        "/api/v1/email/webhook",
        json={
            "event": "opened",
            "message-id": "test-nonexistent",
            "date": "2026-04-03T10:00:00Z",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"


@pytest.mark.asyncio
async def test_api_email_sends_list(client: AsyncClient, auth_headers: dict):
    """API: GET /email/sends."""
    resp = await client.get("/api/v1/email/sends", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
