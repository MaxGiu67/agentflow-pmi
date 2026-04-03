"""Sprint 26 tests — US-95 (invio email singola), US-96 (dashboard analytics)."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import Tenant
from api.modules.email_marketing.service import EmailMarketingService
from api.modules.crm.service import CRMService


# ============================================================
# US-95: Invio email singola a contatto
# ============================================================


@pytest.mark.asyncio
async def test_ac_95_1_send_to_contact(db_session: AsyncSession, tenant: Tenant):
    """AC-95.1/95.4: Invia email a contatto con tracking."""
    crm = CRMService(db_session)
    contact = await crm.create_contact(tenant.id, {"name": "Email Client SRL", "email": "client@test.it"})

    svc = EmailMarketingService(db_session)
    result = await svc.send_email(
        tenant_id=tenant.id,
        to_email="client@test.it",
        to_name="Email Client SRL",
        subject="Proposta progetto",
        html_body="<p>Gentile cliente, ecco la nostra proposta.</p>",
        contact_id=uuid.UUID(contact["id"]),
    )

    assert result["status"] == "sent"
    assert result["to_email"] == "client@test.it"


@pytest.mark.asyncio
async def test_ac_95_2_send_with_template(db_session: AsyncSession, tenant: Tenant):
    """AC-95.2/95.3: Invia usando template con variabili sostituite."""
    svc = EmailMarketingService(db_session)
    tpl = await svc.create_template(tenant.id, {
        "name": "Proposta",
        "subject": "Proposta per {{deal_name}}",
        "html_body": "<p>Gentile {{nome}}, le invio la proposta per {{deal_name}} del valore di {{valore}} EUR.</p>",
        "variables": ["nome", "deal_name", "valore"],
        "category": "proposal",
    })

    result = await svc.send_email(
        tenant_id=tenant.id,
        to_email="proposal@client.it",
        to_name="Mario Rossi",
        subject=tpl["subject"],
        html_body=tpl["html_body"],
        template_id=uuid.UUID(tpl["id"]),
        params={"nome": "Mario", "deal_name": "SAP Migration", "valore": "45000"},
    )

    assert result["status"] == "sent"
    assert result["subject"] == "Proposta per SAP Migration"


@pytest.mark.asyncio
async def test_ac_95_5_status_tracking(db_session: AsyncSession, tenant: Tenant):
    """AC-95.5: Stato email visibile: inviata → letta → cliccata."""
    svc = EmailMarketingService(db_session)
    send = await svc.send_email(
        tenant_id=tenant.id, to_email="track@test.it", to_name="Track",
        subject="Track test", html_body="<p>Test</p>",
    )
    msg_id = send["brevo_message_id"]

    # Simulate open
    await svc.process_webhook_event({"event": "opened", "message-id": msg_id, "date": "2026-04-03T10:00:00Z"})
    sends = await svc.list_sends(tenant.id)
    s = next(x for x in sends if x["brevo_message_id"] == msg_id)
    assert s["status"] == "opened"

    # Simulate click
    await svc.process_webhook_event({"event": "click", "message-id": msg_id, "link": "https://nexadata.it", "date": "2026-04-03T10:05:00Z"})
    sends = await svc.list_sends(tenant.id)
    s = next(x for x in sends if x["brevo_message_id"] == msg_id)
    assert s["status"] == "clicked"


@pytest.mark.asyncio
async def test_ac_95_6_storico_per_contatto(db_session: AsyncSession, tenant: Tenant):
    """AC-95.6: Storico email per contatto."""
    crm = CRMService(db_session)
    contact = await crm.create_contact(tenant.id, {"name": "Storico SRL", "email": "storico@test.it"})
    contact_id = uuid.UUID(contact["id"])

    svc = EmailMarketingService(db_session)
    await svc.send_email(tenant_id=tenant.id, to_email="storico@test.it", to_name="Storico", subject="Email 1", html_body="<p>1</p>", contact_id=contact_id)
    await svc.send_email(tenant_id=tenant.id, to_email="storico@test.it", to_name="Storico", subject="Email 2", html_body="<p>2</p>", contact_id=contact_id)
    await svc.send_email(tenant_id=tenant.id, to_email="altro@test.it", to_name="Altro", subject="Other", html_body="<p>3</p>")

    # Filter by contact
    history = await svc.list_sends(tenant.id, contact_id=contact_id)
    assert len(history) == 2
    assert all(s["to_email"] == "storico@test.it" for s in history)


# ============================================================
# US-96: Dashboard email analytics
# ============================================================


@pytest.mark.asyncio
async def test_ac_96_1_stats_base(db_session: AsyncSession, tenant: Tenant):
    """AC-96.1: Dashboard con totale inviate, open rate, click rate, bounce rate."""
    svc = EmailMarketingService(db_session)

    # Send 3 emails
    for i in range(3):
        send = await svc.send_email(
            tenant_id=tenant.id, to_email=f"stat{i}@test.it", to_name=f"Stat {i}",
            subject=f"Stats {i}", html_body=f"<p>{i}</p>",
        )
        # Open 2 of them
        if i < 2:
            await svc.process_webhook_event({"event": "opened", "message-id": send["brevo_message_id"], "date": "2026-04-03T10:00:00Z"})
        # Click 1
        if i == 0:
            await svc.process_webhook_event({"event": "click", "message-id": send["brevo_message_id"], "link": "https://test.it", "date": "2026-04-03T10:05:00Z"})

    stats = await svc.get_email_stats(tenant.id)
    assert stats["total_sent"] == 3
    assert stats["total_opened"] == 2
    assert stats["total_clicked"] == 1
    assert stats["open_rate"] == round(2 / 3 * 100, 1)
    assert stats["click_rate"] == round(1 / 3 * 100, 1)


@pytest.mark.asyncio
async def test_ac_96_2_breakdown_per_template(db_session: AsyncSession, tenant: Tenant):
    """AC-96.2: Breakdown per template."""
    svc = EmailMarketingService(db_session)

    tpl = await svc.create_template(tenant.id, {
        "name": "Breakdown Test", "subject": "Test", "html_body": "<p>T</p>",
    })
    tpl_id = uuid.UUID(tpl["id"])

    await svc.send_email(tenant_id=tenant.id, to_email="a@t.it", to_name="A", subject="T", html_body="<p>T</p>", template_id=tpl_id)
    await svc.send_email(tenant_id=tenant.id, to_email="b@t.it", to_name="B", subject="T", html_body="<p>T</p>", template_id=tpl_id)

    analytics = await svc.get_email_analytics(tenant.id)
    assert len(analytics["by_template"]) >= 1
    tpl_stats = next(t for t in analytics["by_template"] if t["template_name"] == "Breakdown Test")
    assert tpl_stats["sent"] == 2


@pytest.mark.asyncio
async def test_ac_96_3_top_contatti(db_session: AsyncSession, tenant: Tenant):
    """AC-96.3: Top contatti che aprono."""
    crm = CRMService(db_session)
    contact = await crm.create_contact(tenant.id, {"name": "Top Opener", "email": "top@test.it"})
    cid = uuid.UUID(contact["id"])

    svc = EmailMarketingService(db_session)
    for i in range(3):
        send = await svc.send_email(tenant_id=tenant.id, to_email="top@test.it", to_name="Top", subject=f"M{i}", html_body="<p>Hi</p>", contact_id=cid)
        await svc.process_webhook_event({"event": "opened", "message-id": send["brevo_message_id"], "date": "2026-04-03T10:00:00Z"})

    analytics = await svc.get_email_analytics(tenant.id)
    assert len(analytics["top_contacts"]) >= 1
    top = analytics["top_contacts"][0]
    assert top["email"] == "top@test.it"
    assert top["total_opens"] == 3


@pytest.mark.asyncio
async def test_ac_96_5_bounced_contacts(db_session: AsyncSession, tenant: Tenant):
    """AC-96.5: Lista contatti con email invalida."""
    svc = EmailMarketingService(db_session)
    send = await svc.send_email(tenant_id=tenant.id, to_email="bad@invalid.com", to_name="Bad", subject="Bounce", html_body="<p>T</p>")
    await svc.process_webhook_event({"event": "hard_bounce", "message-id": send["brevo_message_id"], "date": "2026-04-03T10:00:00Z"})

    analytics = await svc.get_email_analytics(tenant.id)
    assert len(analytics["bounced_contacts"]) >= 1
    assert any(c["email"] == "bad@invalid.com" for c in analytics["bounced_contacts"])


# ============================================================
# API Endpoints
# ============================================================


@pytest.mark.asyncio
async def test_api_email_analytics(client: AsyncClient, auth_headers: dict):
    """API: GET /email/analytics."""
    resp = await client.get("/api/v1/email/analytics", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "by_template" in data
    assert "top_contacts" in data
    assert "bounced_contacts" in data


@pytest.mark.asyncio
async def test_api_send_with_template(client: AsyncClient, auth_headers: dict):
    """API: POST /email/send with template_id."""
    # Create template first
    tpl_resp = await client.post(
        "/api/v1/email/templates",
        json={"name": "API Tpl", "subject": "Ciao {{nome}}", "html_body": "<p>{{nome}}</p>"},
        headers=auth_headers,
    )
    tpl_id = tpl_resp.json()["id"]

    resp = await client.post(
        "/api/v1/email/send",
        json={
            "to_email": "api-tpl@test.it",
            "to_name": "API Tpl Test",
            "template_id": tpl_id,
            "subject": "Ciao {{nome}}",
            "html_body": "<p>{{nome}}</p>",
            "params": {"nome": "Marco"},
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["subject"] == "Ciao Marco"
