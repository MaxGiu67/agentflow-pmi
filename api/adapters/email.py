"""Email adapter using Resend API for transactional emails."""

import logging

from api.config import settings

logger = logging.getLogger(__name__)


def _get_resend():
    """Lazy import resend to avoid import errors in test env."""
    try:
        import resend
        if settings.resend_api_key:
            resend.api_key = settings.resend_api_key
        return resend
    except ImportError:
        logger.warning("resend package not installed, emails will be logged only")
        return None


async def send_verification_email(email: str, token: str) -> bool:
    """Send email verification link via Resend."""
    verify_url = f"{settings.frontend_url}/verify-email?token={token}"

    resend = _get_resend()
    if not resend or not settings.resend_api_key:
        logger.info("Email verification (mock): to=%s token=%s url=%s", email, token, verify_url)
        return False

    try:
        resend.Emails.send({
            "from": settings.email_from,
            "to": [email],
            "subject": "Verifica il tuo account AgentFlow",
            "html": f"""
            <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #2563eb;">Benvenuto su AgentFlow!</h2>
                <p>Clicca il bottone per verificare il tuo account:</p>
                <a href="{verify_url}"
                   style="display: inline-block; background: #2563eb; color: white;
                          padding: 12px 24px; border-radius: 8px; text-decoration: none;
                          font-weight: bold; margin: 16px 0;">
                    Verifica email
                </a>
                <p style="color: #666; font-size: 14px;">
                    Oppure copia questo link: {verify_url}
                </p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;">
                <p style="color: #999; font-size: 12px;">
                    AgentFlow — L'agente contabile AI per PMI italiane
                </p>
            </div>
            """,
        })
        logger.info("Verification email sent to %s via Resend", email)
        return True
    except Exception as e:
        logger.error("Failed to send verification email to %s: %s", email, e)
        return False


async def send_password_reset_email(email: str, token: str) -> bool:
    """Send password reset link via Resend."""
    reset_url = f"{settings.frontend_url}/reset-password?token={token}"

    resend = _get_resend()
    if not resend or not settings.resend_api_key:
        logger.info("Password reset (mock): to=%s token=%s url=%s", email, token, reset_url)
        return False

    try:
        resend.Emails.send({
            "from": settings.email_from,
            "to": [email],
            "subject": "Reimposta la password — AgentFlow",
            "html": f"""
            <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #2563eb;">Reimposta la password</h2>
                <p>Hai richiesto di reimpostare la password del tuo account AgentFlow.</p>
                <a href="{reset_url}"
                   style="display: inline-block; background: #2563eb; color: white;
                          padding: 12px 24px; border-radius: 8px; text-decoration: none;
                          font-weight: bold; margin: 16px 0;">
                    Reimposta password
                </a>
                <p style="color: #666; font-size: 14px;">
                    Il link scade tra 60 minuti. Se non hai richiesto tu il reset, ignora questa email.
                </p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;">
                <p style="color: #999; font-size: 12px;">
                    AgentFlow — L'agente contabile AI per PMI italiane
                </p>
            </div>
            """,
        })
        logger.info("Password reset email sent to %s via Resend", email)
        return True
    except Exception as e:
        logger.error("Failed to send password reset email to %s: %s", email, e)
        return False


async def send_lockout_notification(email: str) -> bool:
    """Send account lockout notification via Resend."""
    resend = _get_resend()
    if not resend or not settings.resend_api_key:
        logger.warning("Lockout notification (mock): to=%s", email)
        return False

    try:
        resend.Emails.send({
            "from": settings.email_from,
            "to": [email],
            "subject": "Tentativo di accesso sospetto — AgentFlow",
            "html": f"""
            <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #dc2626;">Accesso bloccato</h2>
                <p>Abbiamo rilevato 5 tentativi di login falliti sul tuo account.
                   L'accesso e stato bloccato per 15 minuti per sicurezza.</p>
                <p>Se non sei stato tu, ti consigliamo di cambiare la password.</p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;">
                <p style="color: #999; font-size: 12px;">
                    AgentFlow — L'agente contabile AI per PMI italiane
                </p>
            </div>
            """,
        })
        logger.info("Lockout notification sent to %s via Resend", email)
        return True
    except Exception as e:
        logger.error("Failed to send lockout notification to %s: %s", email, e)
        return False
