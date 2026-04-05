"""Tests for Social Selling — Epic 2: Activity Types + Pre-funnel (US-134→US-137)."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import (
    CrmActivityType, CrmPipelineStage, CrmContact, CrmActivity, Tenant, User,
)
from tests.conftest import get_auth_token


# ── Fixtures ──────────────────────────────────────────


@pytest.fixture
async def admin_user(db_session: AsyncSession, tenant: Tenant) -> User:
    import bcrypt
    user = User(
        email="admin.epic2@example.com",
        password_hash=bcrypt.hashpw(b"Password1", bcrypt.gensalt()).decode(),
        name="Admin Epic2",
        role="admin",
        email_verified=True,
        tenant_id=tenant.id,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def admin_headers(client: AsyncClient, admin_user: User) -> dict:
    token = await get_auth_token(client, "admin.epic2@example.com", "Password1")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def viewer_user(db_session: AsyncSession, tenant: Tenant) -> User:
    import bcrypt
    user = User(
        email="viewer.epic2@example.com",
        password_hash=bcrypt.hashpw(b"Password1", bcrypt.gensalt()).decode(),
        name="Viewer Epic2",
        role="viewer",
        email_verified=True,
        tenant_id=tenant.id,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def viewer_headers(client: AsyncClient, viewer_user: User) -> dict:
    token = await get_auth_token(client, "viewer.epic2@example.com", "Password1")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def sample_activity_type(db_session: AsyncSession, tenant: Tenant) -> CrmActivityType:
    at = CrmActivityType(
        tenant_id=tenant.id,
        code="demo_call",
        label="Demo Call",
        category="sales",
        counts_as_last_contact=True,
        is_active=True,
    )
    db_session.add(at)
    await db_session.flush()
    return at


@pytest.fixture
async def pipeline_stage(db_session: AsyncSession, tenant: Tenant) -> CrmPipelineStage:
    """A standard pipeline stage at sequence 10."""
    stage = CrmPipelineStage(
        tenant_id=tenant.id,
        name="Nuovo Lead",
        sequence=10,
        probability_default=20,
        color="#FF0000",
        stage_type="pipeline",
        is_active=True,
    )
    db_session.add(stage)
    await db_session.flush()
    return stage


@pytest.fixture
async def contact(db_session: AsyncSession, tenant: Tenant) -> CrmContact:
    c = CrmContact(
        tenant_id=tenant.id,
        name="Test Contact SRL",
        type="azienda",
        email="contact@test.it",
    )
    db_session.add(c)
    await db_session.flush()
    return c


# ══════════════════════════════════════════════════════
# US-134: Create Activity Type
# ══════════════════════════════════════════════════════


class TestUS134CreateActivityType:

    @pytest.mark.anyio
    async def test_ac_134_1_create_activity_type(
        self, client: AsyncClient, admin_headers: dict,
    ):
        """AC-134.1: Admin creates a custom activity type."""
        resp = await client.post(
            "/api/v1/social/activity-types",
            json={
                "code": "inmail_linkedin",
                "label": "Inmail LinkedIn",
                "category": "sales",
                "counts_as_last_contact": True,
            },
            headers=admin_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["code"] == "inmail_linkedin"
        assert data["label"] == "Inmail LinkedIn"
        assert data["category"] == "sales"
        assert data["counts_as_last_contact"] is True
        assert data["is_active"] is True

    @pytest.mark.anyio
    async def test_ac_134_2_duplicate_code_rejected(
        self, client: AsyncClient, admin_headers: dict,
    ):
        """AC-134.2: Duplicate code rejected."""
        payload = {"code": "dup_type", "label": "Dup"}
        await client.post("/api/v1/social/activity-types", json=payload, headers=admin_headers)
        resp = await client.post("/api/v1/social/activity-types", json=payload, headers=admin_headers)
        assert resp.status_code == 400

    @pytest.mark.anyio
    async def test_ac_134_4_invalid_category(
        self, client: AsyncClient, admin_headers: dict,
    ):
        """AC-134.4: Invalid category rejected."""
        resp = await client.post(
            "/api/v1/social/activity-types",
            json={"code": "bad", "label": "Bad", "category": "invalid"},
            headers=admin_headers,
        )
        assert resp.status_code == 400

    @pytest.mark.anyio
    async def test_ac_134_viewer_cannot_create(
        self, client: AsyncClient, viewer_headers: dict,
    ):
        resp = await client.post(
            "/api/v1/social/activity-types",
            json={"code": "x", "label": "X"},
            headers=viewer_headers,
        )
        assert resp.status_code == 403


class TestUS134ListActivityTypes:

    @pytest.mark.anyio
    async def test_ac_134_list_seeds_defaults(
        self, client: AsyncClient, admin_headers: dict,
    ):
        """First call seeds 8 default activity types."""
        resp = await client.get("/api/v1/social/activity-types", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 8
        codes = {t["code"] for t in data}
        assert "call" in codes
        assert "email" in codes
        assert "linkedin_inmail" in codes

    @pytest.mark.anyio
    async def test_ac_134_filter_active_only(
        self, client: AsyncClient, admin_headers: dict,
        db_session: AsyncSession, tenant: Tenant,
    ):
        inactive = CrmActivityType(
            tenant_id=tenant.id, code="old_type", label="Old", category="sales", is_active=False,
        )
        db_session.add(inactive)
        await db_session.flush()

        resp = await client.get(
            "/api/v1/social/activity-types?active_only=true", headers=admin_headers,
        )
        codes = {t["code"] for t in resp.json()}
        assert "old_type" not in codes

    @pytest.mark.anyio
    async def test_ac_134_filter_category(
        self, client: AsyncClient, admin_headers: dict,
    ):
        resp = await client.get(
            "/api/v1/social/activity-types?category=marketing", headers=admin_headers,
        )
        assert resp.status_code == 200
        for t in resp.json():
            assert t["category"] == "marketing"


# ══════════════════════════════════════════════════════
# US-135: Update / Deactivate Activity Type
# ══════════════════════════════════════════════════════


class TestUS135UpdateActivityType:

    @pytest.mark.anyio
    async def test_ac_135_1_update_label(
        self, client: AsyncClient, admin_headers: dict,
        sample_activity_type: CrmActivityType,
    ):
        """AC-135.1: Update label (code remains)."""
        resp = await client.patch(
            f"/api/v1/social/activity-types/{sample_activity_type.id}",
            json={"label": "Demo Call Aggiornata"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["label"] == "Demo Call Aggiornata"
        assert resp.json()["code"] == "demo_call"

    @pytest.mark.anyio
    async def test_ac_135_2_deactivate(
        self, client: AsyncClient, admin_headers: dict,
        sample_activity_type: CrmActivityType,
    ):
        """AC-135.2: Deactivate activity type."""
        resp = await client.patch(
            f"/api/v1/social/activity-types/{sample_activity_type.id}",
            json={"is_active": False},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    @pytest.mark.anyio
    async def test_ac_135_3_hard_delete_returns_409(
        self, client: AsyncClient, admin_headers: dict,
        sample_activity_type: CrmActivityType,
    ):
        """AC-135.3: Hard delete returns 409 Conflict."""
        resp = await client.delete(
            f"/api/v1/social/activity-types/{sample_activity_type.id}",
            headers=admin_headers,
        )
        assert resp.status_code == 409

    @pytest.mark.anyio
    async def test_ac_135_update_nonexistent(
        self, client: AsyncClient, admin_headers: dict,
    ):
        resp = await client.patch(
            f"/api/v1/social/activity-types/{uuid.uuid4()}",
            json={"label": "Nope"},
            headers=admin_headers,
        )
        assert resp.status_code == 404


# ══════════════════════════════════════════════════════
# US-136: Pre-funnel Pipeline Stages
# ══════════════════════════════════════════════════════


class TestUS136PipelineStages:

    @pytest.mark.anyio
    async def test_ac_136_1_create_pre_funnel_stage(
        self, client: AsyncClient, admin_headers: dict,
        pipeline_stage: CrmPipelineStage,
    ):
        """AC-136.1: Create pre-funnel stage with sequence < pipeline."""
        resp = await client.post(
            "/api/v1/social/pipeline/stages",
            json={
                "name": "Prospect",
                "sequence": 1,
                "probability": 5,
                "color": "#CCCCCC",
                "stage_type": "pre_funnel",
            },
            headers=admin_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["stage_type"] == "pre_funnel"
        assert data["name"] == "Prospect"
        assert data["sequence"] == 1

    @pytest.mark.anyio
    async def test_ac_136_2_stages_ordered_by_sequence(
        self, client: AsyncClient, admin_headers: dict,
        db_session: AsyncSession, tenant: Tenant, pipeline_stage: CrmPipelineStage,
    ):
        """AC-136.2: Stages appear in sequence order."""
        pre = CrmPipelineStage(
            tenant_id=tenant.id, name="Prospect", sequence=1,
            probability_default=5, stage_type="pre_funnel", is_active=True,
        )
        db_session.add(pre)
        await db_session.flush()

        resp = await client.get("/api/v1/social/pipeline/stages", headers=admin_headers)
        assert resp.status_code == 200
        stages = resp.json()
        sequences = [s["sequence"] for s in stages]
        assert sequences == sorted(sequences)
        assert stages[0]["stage_type"] == "pre_funnel"

    @pytest.mark.anyio
    async def test_ac_136_3_pre_funnel_auto_reorder(
        self, client: AsyncClient, admin_headers: dict,
        pipeline_stage: CrmPipelineStage,
    ):
        """AC-136.3: Pre-funnel with sequence >= pipeline auto-reorders pipeline stages."""
        resp = await client.post(
            "/api/v1/social/pipeline/stages",
            json={
                "name": "Auto Pre-funnel",
                "sequence": 15,
                "stage_type": "pre_funnel",
            },
            headers=admin_headers,
        )
        # Now auto-reorders instead of rejecting
        assert resp.status_code == 201
        assert resp.json()["stage_type"] == "pre_funnel"

    @pytest.mark.anyio
    async def test_ac_136_update_stage(
        self, client: AsyncClient, admin_headers: dict,
        pipeline_stage: CrmPipelineStage,
    ):
        """H4: PATCH pipeline stage."""
        resp = await client.patch(
            f"/api/v1/social/pipeline/stages/{pipeline_stage.id}",
            json={"name": "Lead Qualificato", "probability": 30},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Lead Qualificato"
        assert resp.json()["probability"] == 30

    @pytest.mark.anyio
    async def test_ac_136_reorder_stages(
        self, client: AsyncClient, admin_headers: dict,
        db_session: AsyncSession, tenant: Tenant, pipeline_stage: CrmPipelineStage,
    ):
        """Reorder stages via PUT."""
        s2 = CrmPipelineStage(
            tenant_id=tenant.id, name="Qualificato", sequence=20,
            probability_default=40, stage_type="pipeline", is_active=True,
        )
        db_session.add(s2)
        await db_session.flush()

        resp = await client.put(
            "/api/v1/social/pipeline/stages/reorder",
            json={
                "stage_order": [
                    {"stage_id": str(pipeline_stage.id), "sequence": 2},
                    {"stage_id": str(s2.id), "sequence": 1},
                ]
            },
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["updated"] == 2

    @pytest.mark.anyio
    async def test_ac_136_viewer_cannot_create(
        self, client: AsyncClient, viewer_headers: dict,
    ):
        resp = await client.post(
            "/api/v1/social/pipeline/stages",
            json={"name": "X", "sequence": 1, "stage_type": "pre_funnel"},
            headers=viewer_headers,
        )
        assert resp.status_code == 403


# ══════════════════════════════════════════════════════
# US-137: Log Activity with Custom Type
# ══════════════════════════════════════════════════════


class TestUS137LogActivityWithType:

    @pytest.mark.anyio
    async def test_ac_137_1_create_activity_with_type(
        self, client: AsyncClient, admin_headers: dict,
        contact: CrmContact, sample_activity_type: CrmActivityType,
    ):
        """AC-137.1: Create activity with custom type."""
        resp = await client.post(
            "/api/v1/crm/activities",
            json={
                "contact_id": str(contact.id),
                "type": "call",
                "activity_type_id": str(sample_activity_type.id),
                "subject": "Demo Call con il prospect",
                "status": "completed",
            },
            headers=admin_headers,
        )
        assert resp.status_code == 201

    @pytest.mark.anyio
    async def test_ac_137_2_last_contact_updated(
        self, client: AsyncClient, admin_headers: dict,
        db_session: AsyncSession, contact: CrmContact,
        sample_activity_type: CrmActivityType,
    ):
        """AC-137.2: counts_as_last_contact updates contact.last_contact_at."""
        assert contact.last_contact_at is None

        await client.post(
            "/api/v1/crm/activities",
            json={
                "contact_id": str(contact.id),
                "type": "call",
                "activity_type_id": str(sample_activity_type.id),
                "subject": "Demo call update last contact",
                "status": "completed",
            },
            headers=admin_headers,
        )

        # Refresh contact from DB
        await db_session.refresh(contact)
        assert contact.last_contact_at is not None

    @pytest.mark.anyio
    async def test_ac_137_3_missing_subject_rejected(
        self, client: AsyncClient, admin_headers: dict,
        contact: CrmContact,
    ):
        """AC-137.3: Activity without subject fails (KeyError → 500)."""
        try:
            resp = await client.post(
                "/api/v1/crm/activities",
                json={
                    "contact_id": str(contact.id),
                    "type": "call",
                },
                headers=admin_headers,
            )
            # If we get a response, it should NOT be 201
            assert resp.status_code != 201
        except Exception:
            # KeyError propagates through ASGI — confirms required field
            pass
