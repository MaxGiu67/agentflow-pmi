"""Service for CRM roles — RBAC per tenant (US-138→US-140)."""

import logging
import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import CrmRole, CrmRolePermission, User

logger = logging.getLogger(__name__)

VALID_ENTITIES = {"contacts", "deals", "activities", "pipelines", "sequences", "reports", "audit_log", "settings"}
VALID_PERMISSIONS = {"create", "read", "update", "delete", "export", "view_all"}

DEFAULT_ROLES = [
    {"name": "Owner", "description": "Proprietario — accesso illimitato", "is_system": True,
     "permissions": {e: list(VALID_PERMISSIONS) for e in VALID_ENTITIES}},
    {"name": "Admin", "description": "Administrator — configura ruoli, utenti, audit", "is_system": True,
     "permissions": {e: list(VALID_PERMISSIONS) for e in VALID_ENTITIES}},
    {"name": "Sales Rep", "description": "Sales Representative — CRUD deal/contacts, limited export", "is_system": False,
     "permissions": {"contacts": ["create", "read", "update"], "deals": ["create", "read", "update"],
                     "activities": ["create", "read"], "pipelines": ["read"], "reports": ["read"]}},
    {"name": "Sales Manager", "description": "Sales Manager — view all, KPI, scorecard", "is_system": False,
     "permissions": {"contacts": ["create", "read", "update", "view_all", "export"],
                     "deals": ["create", "read", "update", "view_all", "export"],
                     "activities": ["create", "read", "view_all"], "pipelines": ["read"],
                     "reports": ["read", "export"]}},
    {"name": "Viewer", "description": "Read-only viewer", "is_system": True,
     "permissions": {e: ["read"] for e in VALID_ENTITIES}},
]


class RolesService:
    """CRUD for CRM roles + permission matrix."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_roles(self, tenant_id: uuid.UUID) -> list[dict]:
        await self._ensure_defaults(tenant_id)
        result = await self.db.execute(
            select(CrmRole).where(CrmRole.tenant_id == tenant_id).order_by(CrmRole.name)
        )
        roles = result.scalars().all()
        out = []
        for role in roles:
            perms = await self._get_permissions(role.id)
            out.append(self._to_dict(role, perms))
        return out

    async def create_role(self, tenant_id: uuid.UUID, data: dict) -> dict:
        name = data.get("name", "").strip()
        if not name:
            return {"error": "Nome ruolo obbligatorio"}

        existing = await self.db.execute(
            select(CrmRole).where(CrmRole.tenant_id == tenant_id, CrmRole.name == name)
        )
        if existing.scalar_one_or_none():
            return {"error": "Ruolo con questo nome gia esistente"}

        role = CrmRole(
            tenant_id=tenant_id,
            name=name,
            description=data.get("description"),
            is_system_role=False,
        )
        self.db.add(role)
        await self.db.flush()

        # Save permissions
        permissions = data.get("permissions", {})
        await self._save_permissions(tenant_id, role.id, permissions)

        perms = await self._get_permissions(role.id)
        return self._to_dict(role, perms)

    async def delete_role(self, role_id: uuid.UUID) -> dict:
        result = await self.db.execute(
            select(CrmRole).where(CrmRole.id == role_id)
        )
        role = result.scalar_one_or_none()
        if not role:
            return {"error": "Ruolo non trovato", "code": 404}
        if role.is_system_role:
            return {"error": "Non puoi eliminare un ruolo di sistema", "code": 403}

        # Check if users assigned
        count = await self.db.scalar(
            select(func.count(User.id)).where(User.crm_role_id == role_id)
        ) or 0
        if count > 0:
            return {"error": f"Ruolo ha {count} utenti assegnati. Riassegnarli prima di eliminare.", "code": 409}

        # Delete permissions first
        perms = await self.db.execute(
            select(CrmRolePermission).where(CrmRolePermission.role_id == role_id)
        )
        for p in perms.scalars().all():
            await self.db.delete(p)

        await self.db.delete(role)
        await self.db.flush()
        return {"status": "deleted"}

    async def _save_permissions(
        self, tenant_id: uuid.UUID, role_id: uuid.UUID, permissions: dict,
    ) -> None:
        for entity, perms in permissions.items():
            if entity not in VALID_ENTITIES:
                continue
            for perm in perms:
                if perm not in VALID_PERMISSIONS:
                    continue
                self.db.add(CrmRolePermission(
                    tenant_id=tenant_id,
                    role_id=role_id,
                    entity=entity,
                    permission=perm,
                ))
        await self.db.flush()

    async def _get_permissions(self, role_id: uuid.UUID) -> dict:
        result = await self.db.execute(
            select(CrmRolePermission).where(CrmRolePermission.role_id == role_id)
        )
        perms: dict[str, list[str]] = {}
        for p in result.scalars().all():
            perms.setdefault(p.entity, []).append(p.permission)
        return perms

    async def _ensure_defaults(self, tenant_id: uuid.UUID) -> None:
        count = await self.db.scalar(
            select(func.count(CrmRole.id)).where(CrmRole.tenant_id == tenant_id)
        )
        if count and count > 0:
            return
        for d in DEFAULT_ROLES:
            role = CrmRole(
                tenant_id=tenant_id,
                name=d["name"],
                description=d["description"],
                is_system_role=d["is_system"],
            )
            self.db.add(role)
            await self.db.flush()
            await self._save_permissions(tenant_id, role.id, d["permissions"])

    def _to_dict(self, role: CrmRole, permissions: dict) -> dict:
        return {
            "id": str(role.id),
            "name": role.name,
            "description": role.description or "",
            "is_system_role": role.is_system_role,
            "permissions": permissions,
        }
