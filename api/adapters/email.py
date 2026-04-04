"""Email adapter using Brevo API for transactional emails (verification, reset, lockout)."""

import logging
import os

logger = logging.getLogger(__name__)

SERVICE_SENDER_EMAIL = "noreply@iridia.tech"
SERVICE_SENDER_NAME = "AgentFlow"


async def _send_via_brevo(to_email: str, subject: str, html: str) -> bool:
    """Send email via Brevo transactional API."""
    api_key = os.getenv("BREVO_API_KEY", "")
    if not api_key:
        logger.info("Brevo not configured — email logged only: to=%s subject=%s", to_email, subject)
        return False

    try:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.brevo.com/v3/smtp/email",
                headers={"api-key": api_key, "Content-Type": "application/json"},
                json={
                    "sender": {"name": SERVICE_SENDER_NAME, "email": SERVICE_SENDER_EMAIL},
                    "to": [{"email": to_email}],
                    "subject": subject,
                    "htmlContent": html,
                    "tags": ["system"],
                },
                timeout=15.0,
            )
            if resp.status_code in (200, 201):
                logger.info("Email sent via Brevo: to=%s subject=%s", to_email, subject)
                return True
            else:
                logger.error("Brevo error %s: %s", resp.status_code, resp.text)
                return False
    except Exception as e:
        logger.error("Failed to send email to %s: %s", to_email, e)
        return False


async def send_verification_email(email: str, token: str) -> bool:
    """Send email verification link."""
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    verify_url = f"{frontend_url}/verify-email?token={token}"

    html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="text-align: center; margin-bottom: 24px;">
            <div style="display: inline-block; background: #863bff; color: white; font-weight: bold; font-size: 18px; width: 48px; height: 48px; line-height: 48px; border-radius: 12px;">AF</div>
        </div>
        <h2 style="color: #1a1a2e; text-align: center;">Benvenuto su AgentFlow!</h2>
        <p style="color: #555; text-align: center;">Clicca il bottone per verificare il tuo account:</p>
        <div style="text-align: center; margin: 24px 0;">
            <a href="{verify_url}"
               style="display: inline-block; background: #863bff; color: white;
                      padding: 14px 32px; border-radius: 10px; text-decoration: none;
                      font-weight: 600; font-size: 16px;">
                Verifica email
            </a>
        </div>
        <p style="color: #999; font-size: 13px; text-align: center;">
            Oppure copia questo link: {verify_url}
        </p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;">
        <p style="color: #bbb; font-size: 12px; text-align: center;">
            AgentFlow PMI — Controller aziendale AI
        </p>
    </div>
    """
    return await _send_via_brevo(email, "Verifica il tuo account — AgentFlow", html)


async def send_password_reset_email(email: str, token: str) -> bool:
    """Send password reset link."""
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    reset_url = f"{frontend_url}/reset-password?token={token}"

    html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="text-align: center; margin-bottom: 24px;">
            <div style="display: inline-block; background: #863bff; color: white; font-weight: bold; font-size: 18px; width: 48px; height: 48px; line-height: 48px; border-radius: 12px;">AF</div>
        </div>
        <h2 style="color: #1a1a2e; text-align: center;">Reimposta la password</h2>
        <p style="color: #555; text-align: center;">Hai richiesto di reimpostare la password del tuo account.</p>
        <div style="text-align: center; margin: 24px 0;">
            <a href="{reset_url}"
               style="display: inline-block; background: #863bff; color: white;
                      padding: 14px 32px; border-radius: 10px; text-decoration: none;
                      font-weight: 600; font-size: 16px;">
                Reimposta password
            </a>
        </div>
        <p style="color: #999; font-size: 13px; text-align: center;">
            Il link scade tra 60 minuti. Se non hai richiesto tu il reset, ignora questa email.
        </p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;">
        <p style="color: #bbb; font-size: 12px; text-align: center;">
            AgentFlow PMI — Controller aziendale AI
        </p>
    </div>
    """
    return await _send_via_brevo(email, "Reimposta la password — AgentFlow", html)


async def send_lockout_notification(email: str) -> bool:
    """Send account lockout notification."""
    html = """
    <div style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="text-align: center; margin-bottom: 24px;">
            <div style="display: inline-block; background: #863bff; color: white; font-weight: bold; font-size: 18px; width: 48px; height: 48px; line-height: 48px; border-radius: 12px;">AF</div>
        </div>
        <h2 style="color: #dc2626; text-align: center;">Accesso bloccato</h2>
        <p style="color: #555; text-align: center;">
            Abbiamo rilevato 5 tentativi di login falliti sul tuo account.
            L'accesso e stato bloccato per 15 minuti per sicurezza.
        </p>
        <p style="color: #555; text-align: center;">Se non sei stato tu, cambia la password.</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;">
        <p style="color: #bbb; font-size: 12px; text-align: center;">
            AgentFlow PMI — Controller aziendale AI
        </p>
    </div>
    """
    return await _send_via_brevo(email, "Tentativo di accesso sospetto — AgentFlow", html)
