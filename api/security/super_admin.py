"""Super admin guard — globale, multi-tenant.

Whitelist via env var `SUPER_ADMIN_EMAILS` (comma-separated). I super admin
sono operatori NexaData con accesso a funzioni di setup piattaforma
(es. salvare credenziali appointee A-Cube). NON è il ruolo `admin` per-tenant.
"""

from __future__ import annotations

from fastapi import HTTPException, status

from api.config import settings
from api.db.models import User


def is_super_admin(user: User) -> bool:
    if not user or not user.email:
        return False
    return user.email.lower() in settings.super_admin_emails_set


def require_super_admin(user: User) -> None:
    if not is_super_admin(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operazione riservata ai super admin della piattaforma",
        )
