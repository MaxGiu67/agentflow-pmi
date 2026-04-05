"""Tests for Social Selling — Epic 3: Roles, External Users, Audit (US-138→US-141)."""

import uuid
from datetime import datetime, timedelta, UTC

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import CrmRole, CrmRolePermission, CrmAuditLog, Tenant, User
from tests.conftest import get_auth_token


# ── Fixtures ──────────────────────────────────────────


@pytest.fixture
async def admin_user(db_session: AsyncSession, tenant: Tenant) -> User:
    import bcrypt
    user = User(
        email="admin.epic3@example.com",
        password_hash=bcrypt.hashpw(b"Password1", bcrypt.gensalt()).decode(),
        name="Admin Epic3",
        role="admin",
        email_verified=True,
        tenant_id=tenant.id,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def admin_headers(client: AsyncClient, admin_user: User) -> dict:
    token = await get_auth_token(client, "admin.epic3@example.com", "Password1")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def viewer_user(db_session: AsyncSession, tenant: Tenant) -> User:
    import bcrypt
    user = User(
        email="viewer.epic3@example.com",
        password_hash=bcrypt.hashpw(b"Password1", bcrypt.gensalt()).decode(),
        name="Viewer Epic3",
        role="viewer",
        email_verified=True,
        tenant_id=tenant.id,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def viewer_headers(client: AsyncClient, viewer_user: User) -> dict:
    token = await get_auth_token(client, "viewer.epic3@example.com", "Password1")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def sample_role(db_session: AsyncSession, tenant: Tenant) -> CrmRole:
    role = CrmRole(
        tenant_id=tenant.id,
        name="Test Custom Role",
        description="Test role",
        is_system_role=False,
    )
    db_session.add(role)
    await db_session.flush()
    return role


@pytest.fixture
async def system_role(db_session: AsyncSession, tenant: Tenant) -> CrmRole:
    role = CrmRole(
        tenant_id=tenant.id,
        name="System Admin",
        description="System admin role",
        is_system_role=True,
    )
    db_session.add(role)
    await db_session.flush()
    return role


@pytest.fixture
async def audit_entries(db_session: AsyncSession, tenant: Tenant, admin_user: User) -> list:
    entries = []
    for i, action in enumerate(["create_contact", "update_deal", "login", "export_csv"]):
        entry = CrmAuditLog(
            tenant_id=tenant.id,
            user_id=admin_user.id,
            action=action,
            entity_type="contact" if "contact" in action else "deal" if "deal" in action else "session",
            entity_name=f"Entity {i}",
            status="success",
            ip_address="192.168.1.100",
        )
        db_session.add(entry)
        entries.append(entry)
    await db_session.flush()
    return entries


# ══════════════════════════════════════════════════════
# US-138: Roles RBAC
# ══════════════════════════════════════════════════════


class TestUS138Roles:

    @pytest.mark.anyio
    async def test_ac_138_1_create_role_with_permissions(
        self, client: AsyncClient, admin_headers: dict,
    ):
        """AC-138.1: Admin creates custom role with permission matrix."""
        resp = await client.post(
            "/api/v1/social/roles",
            json={
                "name": "Account Executive",
                "description": "Gestisce pipeline",
                "permissions": {
                    "contacts": ["create", "read", "update", "view_all"],
                    "deals": ["create", "read", "update", "view_all", "export"],
                    "activities": ["create", "read"],
                    "reports": ["read"],
                },
            },
            headers=admin_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Account Executive"
        assert "contacts" in data["permissions"]
        assert "view_all" in data["permissions"]["contacts"]

    @pytest.mark.anyio
    async def test_ac_138_2_default_roles_seeded(
        self, client: AsyncClient, admin_headers: dict,
    ):
        """AC-138.2: Preset roles are seeded on first list."""
        resp = await client.get("/api/v1/social/roles", headers=admin_headers)
        assert resp.status_code == 200
        names = {r["name"] for r in resp.json()}
        assert "Owner" in names
        assert "Admin" in names
        assert "Sales Rep" in names
        assert "Viewer" in names

    @pytest.mark.anyio
    async def test_ac_138_duplicate_name_rejected(
        self, client: AsyncClient, admin_headers: dict,
    ):
        payload = {"name": "Dup Role"}
        await client.post("/api/v1/social/roles", json=payload, headers=admin_headers)
        resp = await client.post("/api/v1/social/roles", json=payload, headers=admin_headers)
        assert resp.status_code == 400

    @pytest.mark.anyio
    async def test_ac_138_viewer_cannot_manage_roles(
        self, client: AsyncClient, viewer_headers: dict,
    ):
        resp = await client.get("/api/v1/social/roles", headers=viewer_headers)
        assert resp.status_code == 403

    @pytest.mark.anyio
    async def test_ac_138_delete_custom_role(
        self, client: AsyncClient, admin_headers: dict, sample_role: CrmRole,
    ):
        resp = await client.delete(
            f"/api/v1/social/roles/{sample_role.id}",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"

    @pytest.mark.anyio
    async def test_ac_138_cannot_delete_system_role(
        self, client: AsyncClient, admin_headers: dict, system_role: CrmRole,
    ):
        resp = await client.delete(
            f"/api/v1/social/roles/{system_role.id}",
            headers=admin_headers,
        )
        assert resp.status_code == 403

    @pytest.mark.anyio
    async def test_ac_138_cannot_delete_role_with_users(
        self, client: AsyncClient, admin_headers: dict,
        db_session: AsyncSession, tenant: Tenant, sample_role: CrmRole,
    ):
        """Cannot delete role with users assigned."""
        import bcrypt
        assigned_user = User(
            email="assigned@example.com",
            password_hash=bcrypt.hashpw(b"Password1", bcrypt.gensalt()).decode(),
            name="Assigned User",
            role="viewer",
            email_verified=True,
            tenant_id=tenant.id,
            crm_role_id=sample_role.id,
        )
        db_session.add(assigned_user)
        await db_session.flush()

        resp = await client.delete(
            f"/api/v1/social/roles/{sample_role.id}",
            headers=admin_headers,
        )
        assert resp.status_code == 409


# ══════════════════════════════════════════════════════
# US-141: Audit Trail
# ══════════════════════════════════════════════════════


class TestUS141AuditLog:

    @pytest.mark.anyio
    async def test_ac_141_1_list_audit_log(
        self, client: AsyncClient, admin_headers: dict, audit_entries: list,
    ):
        """AC-141.1: Admin views audit log with filters."""
        resp = await client.get("/api/v1/social/audit-log", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert "meta" in data
        assert len(data["data"]) >= 4

    @pytest.mark.anyio
    async def test_ac_141_filter_by_action(
        self, client: AsyncClient, admin_headers: dict, audit_entries: list,
    ):
        resp = await client.get(
            "/api/v1/social/audit-log?action=login", headers=admin_headers,
        )
        assert resp.status_code == 200
        for log in resp.json()["data"]:
            assert log["action"] == "login"

    @pytest.mark.anyio
    async def test_ac_141_4_export_csv(
        self, client: AsyncClient, admin_headers: dict, audit_entries: list,
    ):
        """AC-141.4: Export audit log as CSV with SHA256 header."""
        resp = await client.get(
            "/api/v1/social/audit-log/export", headers=admin_headers,
        )
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        assert "X-Signature-SHA256" in resp.headers
        assert len(resp.headers["X-Signature-SHA256"]) == 64  # SHA256 hex

    @pytest.mark.anyio
    async def test_ac_141_viewer_cannot_view_audit(
        self, client: AsyncClient, viewer_headers: dict,
    ):
        resp = await client.get("/api/v1/social/audit-log", headers=viewer_headers)
        assert resp.status_code == 403

    @pytest.mark.anyio
    async def test_ac_141_log_action_service(
        self, client: AsyncClient, admin_headers: dict,
        db_session: AsyncSession, tenant: Tenant, admin_user: User,
    ):
        """Audit service can log actions."""
        from api.modules.social_selling.audit_service import AuditService
        svc = AuditService(db_session)
        result = await svc.log_action(
            tenant_id=tenant.id,
            user_id=admin_user.id,
            action="create_contact",
            entity_type="contact",
            entity_name="ACME Corp",
            ip_address="10.0.0.1",
            status="success",
        )
        assert result["action"] == "create_contact"
        assert result["entity_name"] == "ACME Corp"

    @pytest.mark.anyio
    async def test_ac_141_3_permission_denied_logged(
        self, client: AsyncClient, admin_headers: dict,
        db_session: AsyncSession, tenant: Tenant, admin_user: User,
    ):
        """AC-141.3: Permission denied events are logged."""
        from api.modules.social_selling.audit_service import AuditService
        svc = AuditService(db_session)
        result = await svc.log_action(
            tenant_id=tenant.id,
            user_id=admin_user.id,
            action="permission_denied",
            entity_type="contact",
            entity_id=uuid.uuid4(),
            status="denied",
            error_message="Accesso negato — canale diverso",
        )
        assert result["status"] == "denied"
        assert result["action"] == "permission_denied"
