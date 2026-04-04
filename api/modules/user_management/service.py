"""Service for user management — invites, roles, permissions (US-109 to US-111)."""

import logging
import uuid
import secrets

import bcrypt
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User

logger = logging.getLogger(__name__)

VALID_ROLES = {"owner", "admin", "commerciale", "viewer"}
MANAGEMENT_ROLES = {"owner", "admin"}


class UserManagementService:
    """Business logic for multi-user team management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── US-109: Team management ───────────────────────────

    async def list_users(self, tenant_id: uuid.UUID) -> list[dict]:
        """AC-109.1: List all users for tenant."""
        result = await self.db.execute(
            select(User).where(User.tenant_id == tenant_id).order_by(User.created_at)
        )
        return [self._user_to_dict(u) for u in result.scalars().all()]

    async def invite_user(
        self, tenant_id: uuid.UUID, email: str, name: str, role: str, inviter: User,
    ) -> dict:
        """AC-109.2: Invite new user with temporary password."""
        if inviter.role not in MANAGEMENT_ROLES:
            return {"error": "Non hai i permessi per invitare utenti"}
        if role not in VALID_ROLES:
            return {"error": f"Ruolo '{role}' non valido. Usa: {', '.join(VALID_ROLES)}"}
        if role == "owner" and inviter.role != "owner":
            return {"error": "Solo l'owner puo creare altri owner"}

        # Check if email exists
        existing = await self.db.execute(
            select(User).where(User.email == email)
        )
        if existing.scalar_one_or_none():
            return {"error": f"Email {email} gia registrata"}

        # Generate temporary password
        temp_password = secrets.token_urlsafe(12)
        password_hash = bcrypt.hashpw(temp_password.encode(), bcrypt.gensalt()).decode()

        user = User(
            tenant_id=tenant_id,
            email=email,
            name=name,
            password_hash=password_hash,
            role=role,
            email_verified=True,  # invited users are pre-verified
            active=True,
        )
        self.db.add(user)
        await self.db.flush()

        logger.info("User invited: %s (%s) by %s", email, role, inviter.email)

        return {
            "id": str(user.id),
            "email": email,
            "name": name,
            "role": role,
            "temp_password": temp_password,
            "message": f"Utente {name} invitato con ruolo {role}. Password temporanea generata.",
        }

    async def update_role(
        self, user_id: uuid.UUID, new_role: str, updater: User,
    ) -> dict:
        """AC-109.3: Change user role."""
        if updater.role not in MANAGEMENT_ROLES:
            return {"error": "Non hai i permessi"}
        if new_role not in VALID_ROLES:
            return {"error": f"Ruolo '{new_role}' non valido"}
        if new_role == "owner" and updater.role != "owner":
            return {"error": "Solo l'owner puo promuovere a owner"}

        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return {"error": "Utente non trovato"}
        if user.id == updater.id:
            return {"error": "Non puoi modificare il tuo stesso ruolo"}

        old_role = user.role
        user.role = new_role
        await self.db.flush()

        return {"id": str(user.id), "old_role": old_role, "new_role": new_role}

    async def toggle_active(
        self, user_id: uuid.UUID, updater: User,
    ) -> dict:
        """AC-109.4: Activate/deactivate user."""
        if updater.role not in MANAGEMENT_ROLES:
            return {"error": "Non hai i permessi"}

        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return {"error": "Utente non trovato"}
        if user.id == updater.id:
            return {"error": "Non puoi disattivare te stesso"}

        user.active = not user.active
        await self.db.flush()

        return {"id": str(user.id), "active": user.active}

    # ── US-111: Sender email per utente ───────────────────

    async def update_sender(
        self, user_id: uuid.UUID, sender_email: str, sender_name: str,
    ) -> dict:
        """AC-111.1: Set sender email/name for user."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return {"error": "Utente non trovato"}

        user.sender_email = sender_email
        user.sender_name = sender_name
        await self.db.flush()

        return {"id": str(user.id), "sender_email": sender_email, "sender_name": sender_name}

    def get_sender_for_user(self, user: User) -> tuple[str, str]:
        """AC-111.2/111.3: Get sender email/name — user's own or global default."""
        import os
        email = user.sender_email or os.getenv("BREVO_SENDER_EMAIL", "noreply@agentflow.it")
        name = user.sender_name or user.name or os.getenv("BREVO_SENDER_NAME", "AgentFlow")
        return email, name

    # ── US-110: Row-level permissions ─────────────────────

    def can_see_all(self, user: User) -> bool:
        """AC-110.3: Owner and admin see everything."""
        return user.role in ("owner", "admin")

    def filter_kwargs(self, user: User) -> dict:
        """Return filter kwargs for CRM queries based on user role.

        Owner/admin: no filter (see all)
        Commerciale: assigned_to = user.id
        Viewer: see all (read-only)
        """
        if user.role == "commerciale":
            return {"assigned_to": user.id}
        return {}

    # ── Serializer ────────────────────────────────────────

    def _user_to_dict(self, u: User) -> dict:
        return {
            "id": str(u.id),
            "email": u.email,
            "name": u.name or "",
            "role": u.role,
            "active": getattr(u, "active", True),
            "sender_email": getattr(u, "sender_email", None) or "",
            "sender_name": getattr(u, "sender_name", None) or "",
            "created_at": u.created_at.isoformat() if u.created_at else "",
        }
