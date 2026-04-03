"""Service for email marketing — templates, sends, sequences, webhooks (US-92 to US-98)."""

import logging
import uuid
from datetime import datetime, timedelta

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from api.adapters.brevo import BrevoClient
from api.db.models import (
    EmailTemplate, EmailSend, EmailEvent, EmailCampaign,
    EmailSequenceStep, EmailSequenceEnrollment, CrmContact,
)

logger = logging.getLogger(__name__)

# Default templates created on first access (AC-94.6)
DEFAULT_TEMPLATES = [
    {
        "name": "Benvenuto",
        "subject": "Benvenuto {{nome}} — {{azienda}}",
        "html_body": "<h2>Gentile {{nome}},</h2><p>Grazie per il suo interesse in NExadata. Siamo a disposizione per qualsiasi esigenza.</p><p>Cordiali saluti,<br>{{commerciale}}</p>",
        "category": "welcome",
        "variables": ["nome", "azienda", "commerciale"],
    },
    {
        "name": "Follow-up proposta",
        "subject": "Aggiornamento sulla proposta — {{deal_name}}",
        "html_body": "<h2>Gentile {{nome}},</h2><p>Le scrivo per un aggiornamento sulla proposta per {{deal_name}}.</p><p>Ha avuto modo di valutarla? Sono disponibile per un confronto.</p><p>Cordiali saluti,<br>{{commerciale}}</p>",
        "category": "followup",
        "variables": ["nome", "deal_name", "commerciale"],
    },
    {
        "name": "Reminder scadenza",
        "subject": "Reminder: proposta in scadenza — {{deal_name}}",
        "html_body": "<h2>Gentile {{nome}},</h2><p>La nostra proposta per {{deal_name}} e in scadenza. Le chiedo gentilmente un riscontro entro la prossima settimana.</p><p>Cordiali saluti,<br>{{commerciale}}</p>",
        "category": "reminder",
        "variables": ["nome", "deal_name", "commerciale"],
    },
]


class EmailMarketingService:
    """Business logic for email marketing with Brevo."""

    def __init__(self, db: AsyncSession, brevo: BrevoClient | None = None) -> None:
        self.db = db
        self.brevo = brevo or BrevoClient()

    # ── Templates (US-94) ─────────────────────────────────

    async def list_templates(self, tenant_id: uuid.UUID) -> list[dict]:
        await self._ensure_default_templates(tenant_id)
        result = await self.db.execute(
            select(EmailTemplate).where(
                EmailTemplate.tenant_id == tenant_id,
            ).order_by(EmailTemplate.name)
        )
        return [self._template_to_dict(t) for t in result.scalars().all()]

    async def create_template(self, tenant_id: uuid.UUID, data: dict) -> dict:
        tpl = EmailTemplate(
            tenant_id=tenant_id,
            name=data["name"],
            subject=data["subject"],
            html_body=data["html_body"],
            text_body=data.get("text_body"),
            variables=data.get("variables"),
            category=data.get("category", "followup"),
            active=data.get("active", True),
        )
        self.db.add(tpl)
        await self.db.flush()
        return self._template_to_dict(tpl)

    async def update_template(self, template_id: uuid.UUID, data: dict) -> dict | None:
        result = await self.db.execute(
            select(EmailTemplate).where(EmailTemplate.id == template_id)
        )
        tpl = result.scalar_one_or_none()
        if not tpl:
            return None
        for key, val in data.items():
            if val is not None and hasattr(tpl, key):
                setattr(tpl, key, val)
        await self.db.flush()
        return self._template_to_dict(tpl)

    async def get_template(self, template_id: uuid.UUID) -> dict | None:
        result = await self.db.execute(
            select(EmailTemplate).where(EmailTemplate.id == template_id)
        )
        tpl = result.scalar_one_or_none()
        return self._template_to_dict(tpl) if tpl else None

    async def preview_template(self, template_id: uuid.UUID, params: dict) -> dict | None:
        """AC-94.4: Preview with sample data."""
        tpl = await self.get_template(template_id)
        if not tpl:
            return None
        subject = tpl["subject"]
        body = tpl["html_body"]
        for key, val in params.items():
            subject = subject.replace(f"{{{{{key}}}}}", str(val))
            body = body.replace(f"{{{{{key}}}}}", str(val))
        return {"subject": subject, "html_body": body}

    async def _ensure_default_templates(self, tenant_id: uuid.UUID) -> None:
        count = await self.db.scalar(
            select(func.count(EmailTemplate.id)).where(
                EmailTemplate.tenant_id == tenant_id,
            )
        )
        if count and count > 0:
            return
        for tpl_data in DEFAULT_TEMPLATES:
            self.db.add(EmailTemplate(
                tenant_id=tenant_id,
                name=tpl_data["name"],
                subject=tpl_data["subject"],
                html_body=tpl_data["html_body"],
                category=tpl_data["category"],
                variables=tpl_data["variables"],
            ))
        await self.db.flush()

    # ── Send email (US-92/95) ─────────────────────────────

    async def send_email(
        self,
        tenant_id: uuid.UUID,
        to_email: str,
        to_name: str,
        subject: str,
        html_body: str,
        contact_id: uuid.UUID | None = None,
        template_id: uuid.UUID | None = None,
        campaign_id: uuid.UUID | None = None,
        params: dict | None = None,
    ) -> dict:
        """Send an email via Brevo and record it."""
        # Substitute variables
        final_subject = subject
        final_body = html_body
        if params:
            for key, val in params.items():
                final_subject = final_subject.replace(f"{{{{{key}}}}}", str(val))
                final_body = final_body.replace(f"{{{{{key}}}}}", str(val))

        # Send via Brevo (or mock if not configured)
        brevo_message_id = ""
        if self.brevo.is_configured():
            brevo_message_id = await self.brevo.send_email(
                to_email, to_name, final_subject, final_body,
            )
        else:
            brevo_message_id = f"mock-{uuid.uuid4().hex[:12]}"
            logger.warning("Brevo not configured — email mocked: %s", brevo_message_id)

        # Record send
        send = EmailSend(
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            contact_id=contact_id,
            template_id=template_id,
            brevo_message_id=brevo_message_id,
            subject_sent=final_subject,
            to_email=to_email,
            to_name=to_name,
            status="sent",
        )
        self.db.add(send)
        await self.db.flush()

        return {
            "id": str(send.id),
            "brevo_message_id": brevo_message_id,
            "status": "sent",
            "to_email": to_email,
            "subject": final_subject,
        }

    # ── Webhook (US-93) ───────────────────────────────────

    async def process_webhook_event(self, payload: dict) -> dict:
        """Process Brevo webhook event — open, click, bounce, etc."""
        event_type = payload.get("event", "")
        message_id = payload.get("message-id") or payload.get("messageId", "")
        timestamp_str = payload.get("date") or payload.get("ts_event", "")

        if not message_id or not event_type:
            return {"status": "ignored", "reason": "missing fields"}

        # Find the send record
        result = await self.db.execute(
            select(EmailSend).where(EmailSend.brevo_message_id == message_id)
        )
        send = result.scalar_one_or_none()
        if not send:
            return {"status": "ignored", "reason": "send not found"}

        # Parse timestamp
        try:
            ts = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00")) if timestamp_str else datetime.utcnow()
        except (ValueError, AttributeError):
            ts = datetime.utcnow()

        # Map Brevo event names
        event_map = {
            "delivered": "delivered",
            "opened": "opened", "open": "opened", "unique_opened": "opened",
            "click": "clicked", "clicked": "clicked",
            "hard_bounce": "hard_bounce", "hardBounce": "hard_bounce",
            "soft_bounce": "soft_bounce", "softBounce": "soft_bounce",
            "unsubscribed": "unsubscribed", "unsubscribe": "unsubscribed",
            "spam": "spam", "complaint": "spam",
        }
        normalized_type = event_map.get(event_type, event_type)

        # Save event
        event = EmailEvent(
            send_id=send.id,
            event_type=normalized_type,
            url_clicked=payload.get("link") or payload.get("url"),
            ip_address=payload.get("ip"),
            user_agent=payload.get("user-agent") or payload.get("user_agent"),
            timestamp=ts,
            raw_payload=payload,
        )
        self.db.add(event)

        # Update send record
        if normalized_type == "opened":
            if not send.opened_at:
                send.opened_at = ts
            send.open_count = (send.open_count or 0) + 1
            send.status = "opened"
        elif normalized_type == "clicked":
            if not send.clicked_at:
                send.clicked_at = ts
            send.click_count = (send.click_count or 0) + 1
            send.status = "clicked"
        elif normalized_type == "delivered":
            send.status = "delivered"
        elif normalized_type == "hard_bounce":
            send.status = "bounced"
            # AC-93.5: Mark contact email as invalid
            if send.contact_id:
                contact_result = await self.db.execute(
                    select(CrmContact).where(CrmContact.id == send.contact_id)
                )
                contact = contact_result.scalar_one_or_none()
                if contact:
                    contact.email_opt_in = False
        elif normalized_type in ("unsubscribed", "spam"):
            # AC-93.6/93.7: Update opt-in
            if send.contact_id:
                contact_result = await self.db.execute(
                    select(CrmContact).where(CrmContact.id == send.contact_id)
                )
                contact = contact_result.scalar_one_or_none()
                if contact:
                    contact.email_opt_in = False

        await self.db.flush()
        return {"status": "processed", "event_type": normalized_type, "send_id": str(send.id)}

    # ── Email history ─────────────────────────────────────

    async def list_sends(
        self, tenant_id: uuid.UUID, contact_id: uuid.UUID | None = None, limit: int = 50,
    ) -> list[dict]:
        query = select(EmailSend).where(EmailSend.tenant_id == tenant_id)
        if contact_id:
            query = query.where(EmailSend.contact_id == contact_id)
        query = query.order_by(EmailSend.sent_at.desc()).limit(limit)
        result = await self.db.execute(query)
        return [self._send_to_dict(s) for s in result.scalars().all()]

    async def get_email_stats(self, tenant_id: uuid.UUID) -> dict:
        """Email stats for dashboard."""
        total = await self.db.scalar(
            select(func.count(EmailSend.id)).where(EmailSend.tenant_id == tenant_id)
        ) or 0
        opened = await self.db.scalar(
            select(func.count(EmailSend.id)).where(
                EmailSend.tenant_id == tenant_id, EmailSend.opened_at.isnot(None),
            )
        ) or 0
        clicked = await self.db.scalar(
            select(func.count(EmailSend.id)).where(
                EmailSend.tenant_id == tenant_id, EmailSend.clicked_at.isnot(None),
            )
        ) or 0
        bounced = await self.db.scalar(
            select(func.count(EmailSend.id)).where(
                EmailSend.tenant_id == tenant_id, EmailSend.status == "bounced",
            )
        ) or 0

        return {
            "total_sent": total,
            "total_opened": opened,
            "total_clicked": clicked,
            "total_bounced": bounced,
            "open_rate": round(opened / total * 100, 1) if total > 0 else 0.0,
            "click_rate": round(clicked / total * 100, 1) if total > 0 else 0.0,
            "bounce_rate": round(bounced / total * 100, 1) if total > 0 else 0.0,
        }

    # ── Sequences (US-97/98) ─────────────────────────────

    async def create_sequence(self, tenant_id: uuid.UUID, data: dict) -> dict:
        """AC-97.1: Create email sequence campaign."""
        campaign = EmailCampaign(
            tenant_id=tenant_id,
            name=data["name"],
            type="sequence",
            trigger_event=data.get("trigger_event", "manual"),
            trigger_config=data.get("trigger_config"),
            status="draft",
        )
        self.db.add(campaign)
        await self.db.flush()
        return {
            "id": str(campaign.id),
            "name": campaign.name,
            "type": "sequence",
            "trigger_event": campaign.trigger_event,
            "status": "draft",
        }

    async def add_sequence_step(self, campaign_id: uuid.UUID, data: dict) -> dict:
        """AC-97.2: Add step with template, delay, condition."""
        step = EmailSequenceStep(
            campaign_id=campaign_id,
            step_order=data.get("step_order", 1),
            template_id=uuid.UUID(data["template_id"]),
            delay_days=data.get("delay_days", 0),
            delay_hours=data.get("delay_hours", 0),
            condition_type=data.get("condition_type", "none"),
            condition_link=data.get("condition_link"),
            skip_if_replied=data.get("skip_if_replied", False),
        )
        self.db.add(step)
        await self.db.flush()
        return {
            "id": str(step.id),
            "step_order": step.step_order,
            "template_id": str(step.template_id),
            "delay_days": step.delay_days,
            "condition_type": step.condition_type,
        }

    async def get_sequence_steps(self, campaign_id: uuid.UUID) -> list[dict]:
        result = await self.db.execute(
            select(EmailSequenceStep).where(
                EmailSequenceStep.campaign_id == campaign_id,
            ).order_by(EmailSequenceStep.step_order)
        )
        return [
            {
                "id": str(s.id),
                "step_order": s.step_order,
                "template_id": str(s.template_id),
                "delay_days": s.delay_days,
                "delay_hours": s.delay_hours,
                "condition_type": s.condition_type,
                "condition_link": s.condition_link,
                "skip_if_replied": s.skip_if_replied,
            }
            for s in result.scalars().all()
        ]

    async def enroll_contact(
        self, tenant_id: uuid.UUID, campaign_id: uuid.UUID, contact_id: uuid.UUID,
    ) -> dict:
        """AC-98.4: Enroll contact in sequence (prevent duplicates)."""
        existing = await self.db.execute(
            select(EmailSequenceEnrollment).where(
                EmailSequenceEnrollment.tenant_id == tenant_id,
                EmailSequenceEnrollment.campaign_id == campaign_id,
                EmailSequenceEnrollment.contact_id == contact_id,
                EmailSequenceEnrollment.status == "active",
            )
        )
        if existing.scalar_one_or_none():
            return {"status": "already_enrolled"}

        # Get first step delay
        steps = await self.get_sequence_steps(campaign_id)
        first_delay = timedelta(
            days=steps[0]["delay_days"] if steps else 0,
            hours=steps[0].get("delay_hours", 0) if steps else 0,
        )

        enrollment = EmailSequenceEnrollment(
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            contact_id=contact_id,
            current_step=0,
            status="active",
            next_send_at=datetime.utcnow() + first_delay,
        )
        self.db.add(enrollment)
        await self.db.flush()
        return {"status": "enrolled", "id": str(enrollment.id)}

    async def process_sequence_step(self, enrollment_id: uuid.UUID) -> dict:
        """AC-97.3/97.4: Process next step in sequence with conditions."""
        result = await self.db.execute(
            select(EmailSequenceEnrollment).where(
                EmailSequenceEnrollment.id == enrollment_id,
            )
        )
        enrollment = result.scalar_one_or_none()
        if not enrollment or enrollment.status != "active":
            return {"status": "skipped", "reason": "not active"}

        # Get steps
        steps = await self.get_sequence_steps(enrollment.campaign_id)
        if enrollment.current_step >= len(steps):
            enrollment.status = "completed"
            await self.db.flush()
            return {"status": "completed"}

        step = steps[enrollment.current_step]

        # Check condition
        if step["condition_type"] != "none" and enrollment.current_step > 0:
            prev_step = steps[enrollment.current_step - 1]
            # Find previous send for this contact in this campaign
            prev_send_result = await self.db.execute(
                select(EmailSend).where(
                    EmailSend.contact_id == enrollment.contact_id,
                    EmailSend.campaign_id == enrollment.campaign_id,
                ).order_by(EmailSend.sent_at.desc()).limit(1)
            )
            prev_send = prev_send_result.scalar_one_or_none()

            if step["condition_type"] == "if_opened" and prev_send and not prev_send.opened_at:
                # Skip — condition not met
                enrollment.current_step += 1
                await self.db.flush()
                return {"status": "skipped", "reason": "condition_not_met: if_opened"}

            if step["condition_type"] == "if_not_opened" and prev_send and prev_send.opened_at:
                enrollment.current_step += 1
                await self.db.flush()
                return {"status": "skipped", "reason": "condition_not_met: if_not_opened"}

        # Get contact email
        contact_result = await self.db.execute(
            select(CrmContact).where(CrmContact.id == enrollment.contact_id)
        )
        contact = contact_result.scalar_one_or_none()
        if not contact or not contact.email:
            return {"status": "error", "reason": "no contact email"}

        # Get template
        tpl = await self.get_template(uuid.UUID(step["template_id"]))
        if not tpl:
            return {"status": "error", "reason": "template not found"}

        # Send email
        params = {"nome": contact.name, "azienda": contact.name}
        send_result = await self.send_email(
            tenant_id=enrollment.tenant_id,
            to_email=contact.email,
            to_name=contact.name,
            subject=tpl["subject"],
            html_body=tpl["html_body"],
            contact_id=enrollment.contact_id,
            template_id=uuid.UUID(step["template_id"]),
            campaign_id=enrollment.campaign_id,
            params=params,
        )

        # Advance step
        enrollment.current_step += 1
        if enrollment.current_step >= len(steps):
            enrollment.status = "completed"
            enrollment.next_send_at = None
        else:
            next_step = steps[enrollment.current_step]
            enrollment.next_send_at = datetime.utcnow() + timedelta(
                days=next_step["delay_days"],
                hours=next_step.get("delay_hours", 0),
            )

        await self.db.flush()
        return {"status": "sent", "send_id": send_result["id"], "step": enrollment.current_step}

    async def trigger_on_event(
        self, tenant_id: uuid.UUID, event_name: str, context: dict,
    ) -> list[dict]:
        """AC-98.1/98.2: Trigger sequences on CRM events."""
        # Find active campaigns with matching trigger
        result = await self.db.execute(
            select(EmailCampaign).where(
                EmailCampaign.tenant_id == tenant_id,
                EmailCampaign.type == "sequence",
                EmailCampaign.trigger_event == event_name,
                EmailCampaign.status == "active",
            )
        )
        campaigns = result.scalars().all()

        results = []
        for campaign in campaigns:
            contact_id = context.get("contact_id")
            if not contact_id:
                continue

            # AC-98.3: Check trigger config filter
            if campaign.trigger_config:
                stage = campaign.trigger_config.get("stage")
                if stage and context.get("stage") != stage:
                    continue

            enroll = await self.enroll_contact(
                tenant_id, campaign.id, uuid.UUID(contact_id),
            )
            results.append({"campaign": campaign.name, **enroll})

        return results

    async def get_email_analytics(self, tenant_id: uuid.UUID) -> dict:
        """AC-96.1 to AC-96.5: Full email analytics."""
        stats = await self.get_email_stats(tenant_id)

        # AC-96.2: Breakdown per template
        tpl_result = await self.db.execute(
            select(
                EmailSend.template_id,
                func.count(EmailSend.id).label("sent"),
                func.count(EmailSend.opened_at).label("opened"),
                func.count(EmailSend.clicked_at).label("clicked"),
            ).where(
                EmailSend.tenant_id == tenant_id,
                EmailSend.template_id.isnot(None),
            ).group_by(EmailSend.template_id)
        )
        by_template = []
        for row in tpl_result.fetchall():
            # Get template name
            tpl_name_result = await self.db.execute(
                select(EmailTemplate.name).where(EmailTemplate.id == row.template_id)
            )
            tpl_name = tpl_name_result.scalar() or "Senza template"
            by_template.append({
                "template_id": str(row.template_id),
                "template_name": tpl_name,
                "sent": row.sent,
                "opened": row.opened,
                "clicked": row.clicked,
                "open_rate": round(row.opened / row.sent * 100, 1) if row.sent > 0 else 0.0,
            })

        # AC-96.3: Top contatti che aprono/cliccano
        top_result = await self.db.execute(
            select(
                EmailSend.contact_id,
                EmailSend.to_email,
                EmailSend.to_name,
                func.count(EmailSend.id).label("total"),
                func.count(EmailSend.opened_at).label("opens"),
                func.count(EmailSend.clicked_at).label("clicks"),
            ).where(
                EmailSend.tenant_id == tenant_id,
                EmailSend.contact_id.isnot(None),
            ).group_by(
                EmailSend.contact_id, EmailSend.to_email, EmailSend.to_name,
            ).order_by(func.count(EmailSend.opened_at).desc()).limit(10)
        )
        top_contacts = [
            {
                "contact_id": str(row.contact_id),
                "email": row.to_email,
                "name": row.to_name or "",
                "total_sent": row.total,
                "total_opens": row.opens,
                "total_clicks": row.clicks,
            }
            for row in top_result.fetchall()
        ]

        # AC-96.5: Contacts with bounced emails
        bounced_result = await self.db.execute(
            select(EmailSend.to_email, EmailSend.to_name).where(
                EmailSend.tenant_id == tenant_id,
                EmailSend.status == "bounced",
            ).distinct()
        )
        bounced_contacts = [
            {"email": row.to_email, "name": row.to_name or ""}
            for row in bounced_result.fetchall()
        ]

        return {
            **stats,
            "by_template": by_template,
            "top_contacts": top_contacts,
            "bounced_contacts": bounced_contacts,
        }

    # ── Serializers ───────────────────────────────────────

    def _template_to_dict(self, t: EmailTemplate) -> dict:
        return {
            "id": str(t.id),
            "name": t.name,
            "subject": t.subject,
            "html_body": t.html_body,
            "text_body": t.text_body or "",
            "variables": t.variables or [],
            "category": t.category,
            "active": t.active,
        }

    def _send_to_dict(self, s: EmailSend) -> dict:
        return {
            "id": str(s.id),
            "to_email": s.to_email,
            "to_name": s.to_name or "",
            "subject": s.subject_sent,
            "status": s.status,
            "brevo_message_id": s.brevo_message_id or "",
            "sent_at": s.sent_at.isoformat() if s.sent_at else "",
            "opened_at": s.opened_at.isoformat() if s.opened_at else None,
            "clicked_at": s.clicked_at.isoformat() if s.clicked_at else None,
            "open_count": s.open_count,
            "click_count": s.click_count,
        }
