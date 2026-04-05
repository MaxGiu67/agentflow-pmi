"""Tests for Social Selling — Origins (US-130→US-133)."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import CrmContact, CrmContactOrigin, Tenant, User
from tests.conftest import get_auth_token


# ── Fixtures ──────────────────────────────────────────


@pytest.fixture
async def admin_user(db_session: AsyncSession, tenant: Tenant) -> User:
    """Admin user for social selling tests."""
    import bcrypt

    user = User(
        email="admin.social@example.com",
        password_hash=bcrypt.hashpw(b"Password1", bcrypt.gensalt()).decode(),
        name="Admin Social",
        role="admin",
        email_verified=True,
        tenant_id=tenant.id,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def admin_headers(client: AsyncClient, admin_user: User) -> dict:
    token = await get_auth_token(client, "admin.social@example.com", "Password1")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def viewer_user(db_session: AsyncSession, tenant: Tenant) -> User:
    """Viewer user (read-only)."""
    import bcrypt

    user = User(
        email="viewer.social@example.com",
        password_hash=bcrypt.hashpw(b"Password1", bcrypt.gensalt()).decode(),
        name="Viewer Social",
        role="viewer",
        email_verified=True,
        tenant_id=tenant.id,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def viewer_headers(client: AsyncClient, viewer_user: User) -> dict:
    token = await get_auth_token(client, "viewer.social@example.com", "Password1")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def sample_origin(db_session: AsyncSession, tenant: Tenant) -> CrmContactOrigin:
    """A pre-existing origin."""
    origin = CrmContactOrigin(
        tenant_id=tenant.id,
        code="website",
        label="Sito Web",
        parent_channel="digital",
        is_active=True,
    )
    db_session.add(origin)
    await db_session.flush()
    return origin


@pytest.fixture
async def contact_with_source(db_session: AsyncSession, tenant: Tenant) -> CrmContact:
    """A contact with legacy source field but no origin_id."""
    contact = CrmContact(
        tenant_id=tenant.id,
        name="Azienda Test SRL",
        type="azienda",
        email="test@azienda.it",
        source="LinkedIn",
    )
    db_session.add(contact)
    await db_session.flush()
    return contact


@pytest.fixture
async def contact_with_origin(
    db_session: AsyncSession, tenant: Tenant, sample_origin: CrmContactOrigin,
) -> CrmContact:
    """A contact already linked to an origin."""
    contact = CrmContact(
        tenant_id=tenant.id,
        name="Collegata SRL",
        type="azienda",
        email="collegata@test.it",
        origin_id=sample_origin.id,
    )
    db_session.add(contact)
    await db_session.flush()
    return contact


# ── US-130: List / Create Origins ─────────────────────


class TestUS130ListOrigins:
    """US-130: List contact origins for tenant."""

    @pytest.mark.anyio
    async def test_ac_130_list_origins_seeds_defaults(
        self, client: AsyncClient, admin_headers: dict,
    ):
        """AC-130: First call seeds 6 default origins."""
        resp = await client.get("/api/v1/social/origins", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 6
        codes = {o["code"] for o in data}
        assert "web" in codes
        assert "linkedin" in codes
        assert "referral" in codes

    @pytest.mark.anyio
    async def test_ac_130_list_origins_active_only(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-130: Filter active-only origins."""
        # Create an inactive origin
        inactive = CrmContactOrigin(
            tenant_id=tenant.id, code="old_channel", label="Vecchio", is_active=False,
        )
        db_session.add(inactive)
        await db_session.flush()

        resp = await client.get(
            "/api/v1/social/origins?active_only=true", headers=admin_headers,
        )
        assert resp.status_code == 200
        codes = {o["code"] for o in resp.json()}
        assert "old_channel" not in codes


class TestUS130CreateOrigin:
    """US-130: Create custom contact origin."""

    @pytest.mark.anyio
    async def test_ac_130_1_create_origin(
        self, client: AsyncClient, admin_headers: dict,
    ):
        """AC-130.1: Admin creates a new origin."""
        resp = await client.post(
            "/api/v1/social/origins",
            json={"code": "instagram", "label": "Instagram", "parent_channel": "social"},
            headers=admin_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["code"] == "instagram"
        assert data["label"] == "Instagram"
        assert data["parent_channel"] == "social"
        assert data["is_active"] is True

    @pytest.mark.anyio
    async def test_ac_130_2_duplicate_code_rejected(
        self, client: AsyncClient, admin_headers: dict,
    ):
        """AC-130.2: Duplicate code for same tenant is rejected."""
        payload = {"code": "test_dup", "label": "Test Dup"}
        await client.post("/api/v1/social/origins", json=payload, headers=admin_headers)
        resp = await client.post("/api/v1/social/origins", json=payload, headers=admin_headers)
        assert resp.status_code == 400

    @pytest.mark.anyio
    async def test_ac_130_viewer_cannot_create(
        self, client: AsyncClient, viewer_headers: dict,
    ):
        """AC-130: Only admin/owner can create origins."""
        resp = await client.post(
            "/api/v1/social/origins",
            json={"code": "test", "label": "Test"},
            headers=viewer_headers,
        )
        assert resp.status_code == 403


# ── US-131: Update / Deactivate / Delete Origin ──────


class TestUS131UpdateOrigin:
    """US-131: Update origin (code immutable)."""

    @pytest.mark.anyio
    async def test_ac_131_1_update_label(
        self, client: AsyncClient, admin_headers: dict, sample_origin: CrmContactOrigin,
    ):
        """AC-131.1: Admin can update label."""
        resp = await client.patch(
            f"/api/v1/social/origins/{sample_origin.id}",
            json={"label": "Website Aziendale"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["label"] == "Website Aziendale"
        # Code should remain the same
        assert resp.json()["code"] == "website"

    @pytest.mark.anyio
    async def test_ac_131_3_code_immutable(
        self, client: AsyncClient, admin_headers: dict, sample_origin: CrmContactOrigin,
    ):
        """AC-131.3: Code field cannot be changed via PATCH."""
        resp = await client.patch(
            f"/api/v1/social/origins/{sample_origin.id}",
            json={"label": "New Label"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == "website"  # unchanged

    @pytest.mark.anyio
    async def test_ac_131_deactivate(
        self, client: AsyncClient, admin_headers: dict, sample_origin: CrmContactOrigin,
    ):
        """AC-131: Deactivate an origin."""
        resp = await client.patch(
            f"/api/v1/social/origins/{sample_origin.id}",
            json={"is_active": False},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    @pytest.mark.anyio
    async def test_ac_131_update_nonexistent(
        self, client: AsyncClient, admin_headers: dict,
    ):
        """AC-131: Update non-existent origin returns 404."""
        resp = await client.patch(
            f"/api/v1/social/origins/{uuid.uuid4()}",
            json={"label": "Nope"},
            headers=admin_headers,
        )
        assert resp.status_code == 404


class TestUS131DeleteOrigin:
    """US-131: Delete origin (blocked if contacts assigned)."""

    @pytest.mark.anyio
    async def test_ac_131_4_delete_free_origin(
        self, client: AsyncClient, admin_headers: dict, sample_origin: CrmContactOrigin,
    ):
        """AC-131.4: Can delete origin with no contacts."""
        resp = await client.delete(
            f"/api/v1/social/origins/{sample_origin.id}",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"

    @pytest.mark.anyio
    async def test_ac_131_4_delete_blocked_if_contacts(
        self, client: AsyncClient, admin_headers: dict,
        sample_origin: CrmContactOrigin, contact_with_origin: CrmContact,
    ):
        """AC-131.4: Cannot delete origin with contacts assigned."""
        resp = await client.delete(
            f"/api/v1/social/origins/{sample_origin.id}",
            headers=admin_headers,
        )
        assert resp.status_code == 400
        assert "contatti" in resp.json()["detail"].lower()

    @pytest.mark.anyio
    async def test_ac_131_delete_nonexistent(
        self, client: AsyncClient, admin_headers: dict,
    ):
        """Delete non-existent origin returns 404."""
        resp = await client.delete(
            f"/api/v1/social/origins/{uuid.uuid4()}",
            headers=admin_headers,
        )
        assert resp.status_code == 404


# ── US-132: Migration source → origin_id ─────────────


class TestUS132MigrateSources:
    """US-132: Migrate legacy source field to origin_id."""

    @pytest.mark.anyio
    async def test_ac_132_1_migrate_creates_origin(
        self, client: AsyncClient, admin_headers: dict,
        contact_with_source: CrmContact,
    ):
        """AC-132.1: Migration auto-creates origin from source value."""
        resp = await client.post(
            "/api/v1/social/origins/migrate",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["migrated"] >= 1

    @pytest.mark.anyio
    async def test_ac_132_2_migrate_idempotent(
        self, client: AsyncClient, admin_headers: dict,
        contact_with_source: CrmContact,
    ):
        """AC-132.2: Second migration run has 0 migrated."""
        await client.post("/api/v1/social/origins/migrate", headers=admin_headers)
        resp = await client.post("/api/v1/social/origins/migrate", headers=admin_headers)
        assert resp.json()["migrated"] == 0

    @pytest.mark.anyio
    async def test_ac_132_viewer_cannot_migrate(
        self, client: AsyncClient, viewer_headers: dict,
    ):
        """Only admin/owner can migrate."""
        resp = await client.post("/api/v1/social/origins/migrate", headers=viewer_headers)
        assert resp.status_code == 403


# ── US-133: Assign origin to contact ─────────────────


class TestUS133AssignOrigin:
    """US-133: Assign origin to contact."""

    @pytest.mark.anyio
    async def test_ac_133_assign_origin(
        self, client: AsyncClient, admin_headers: dict,
        contact_with_source: CrmContact, sample_origin: CrmContactOrigin,
    ):
        """AC-133: Assign existing origin to contact."""
        resp = await client.post(
            f"/api/v1/social/contacts/{contact_with_source.id}/origin?origin_id={sample_origin.id}",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "assigned"

    @pytest.mark.anyio
    async def test_ac_133_assign_inactive_origin_rejected(
        self, client: AsyncClient, admin_headers: dict,
        db_session: AsyncSession, tenant: Tenant, contact_with_source: CrmContact,
    ):
        """AC-133: Cannot assign inactive origin."""
        inactive = CrmContactOrigin(
            tenant_id=tenant.id, code="dead_channel", label="Dead", is_active=False,
        )
        db_session.add(inactive)
        await db_session.flush()

        resp = await client.post(
            f"/api/v1/social/contacts/{contact_with_source.id}/origin?origin_id={inactive.id}",
            headers=admin_headers,
        )
        assert resp.status_code == 400

    @pytest.mark.anyio
    async def test_ac_133_assign_nonexistent_contact(
        self, client: AsyncClient, admin_headers: dict, sample_origin: CrmContactOrigin,
    ):
        """AC-133: Assign to non-existent contact returns error."""
        resp = await client.post(
            f"/api/v1/social/contacts/{uuid.uuid4()}/origin?origin_id={sample_origin.id}",
            headers=admin_headers,
        )
        assert resp.status_code == 400
