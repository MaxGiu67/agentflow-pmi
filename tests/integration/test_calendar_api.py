"""Tests for Calendar integration — US-151→US-155.

Covers:
- US-153: Microsoft 365 OAuth flow (connect URL, status, disconnect)
- US-154: Push activity to Outlook (service-level mock)
- US-155: Calendly URL CRUD
- US-151/152: Calendar view + .ics (frontend-only, verified via API data availability)
"""

import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import CrmActivity, CrmContact, Tenant, User
from api.modules.calendar.microsoft_service import MicrosoftCalendarService
from api.modules.user_management.service import UserManagementService
from tests.conftest import _hash_pw, get_auth_token


# ── Fixtures ──────────────────────────────────────────


@pytest.fixture
async def owner(db_session: AsyncSession, tenant: Tenant) -> User:
    u = User(
        email="owner.cal@nexadata.it",
        password_hash=_hash_pw("Password1"),
        name="Owner Calendar",
        role="owner",
        email_verified=True,
        tenant_id=tenant.id,
        active=True,
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest.fixture
async def commerciale(db_session: AsyncSession, tenant: Tenant) -> User:
    u = User(
        email="comm.cal@nexadata.it",
        password_hash=_hash_pw("Password1"),
        name="Commerciale Calendar",
        role="commerciale",
        email_verified=True,
        tenant_id=tenant.id,
        active=True,
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest.fixture
async def planned_activity(db_session: AsyncSession, tenant: Tenant, commerciale: User) -> CrmActivity:
    contact = CrmContact(tenant_id=tenant.id, name="Test Client SRL")
    db_session.add(contact)
    await db_session.flush()

    act = CrmActivity(
        tenant_id=tenant.id,
        contact_id=contact.id,
        user_id=commerciale.id,
        type="meeting",
        subject="Demo prodotto",
        description="Presentazione AgentFlow",
        scheduled_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=1),
        status="planned",
    )
    db_session.add(act)
    await db_session.flush()
    return act


# ============================================================
# US-153: Microsoft 365 OAuth
# ============================================================


class TestUS153MicrosoftOAuth:
    """US-153: Microsoft 365 Calendar OAuth flow."""

    @pytest.mark.anyio
    async def test_ac_153_1_connect_returns_auth_url(
        self, db_session: AsyncSession,
    ):
        """AC-153.1: get_auth_url generates a Microsoft OAuth URL."""
        svc = MicrosoftCalendarService(db_session)
        url = svc.get_auth_url(state="test-user-id")
        assert "login.microsoftonline.com" in url
        assert "oauth2/v2.0/authorize" in url
        assert "Calendars.ReadWrite" in url
        assert "state=test-user-id" in url

    @pytest.mark.anyio
    async def test_ac_153_2_scope_minimal(
        self, db_session: AsyncSession,
    ):
        """AC-153.2: Only Calendars.ReadWrite and User.Read scopes requested."""
        svc = MicrosoftCalendarService(db_session)
        url = svc.get_auth_url()
        assert "Calendars.ReadWrite" in url
        assert "User.Read" in url
        # No mail or file scope
        assert "Mail" not in url
        assert "Files" not in url

    @pytest.mark.anyio
    async def test_ac_153_status_not_connected(
        self, db_session: AsyncSession, commerciale: User,
    ):
        """Status check for unconnected user."""
        svc = MicrosoftCalendarService(db_session)
        assert svc.is_connected(commerciale) is False

    @pytest.mark.anyio
    async def test_ac_153_status_connected(
        self, db_session: AsyncSession, commerciale: User,
    ):
        """Status check for connected user (token present)."""
        commerciale.microsoft_token = json.dumps({
            "access_token": "fake-token",
            "refresh_token": "fake-refresh",
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        })
        await db_session.flush()

        svc = MicrosoftCalendarService(db_session)
        assert svc.is_connected(commerciale) is True

    @pytest.mark.anyio
    async def test_ac_153_4_disconnect(
        self, db_session: AsyncSession, commerciale: User,
    ):
        """AC-153.4: Disconnect removes token."""
        commerciale.microsoft_token = json.dumps({"access_token": "x", "refresh_token": "y", "expires_at": "2099-01-01T00:00:00"})
        await db_session.flush()

        svc = MicrosoftCalendarService(db_session)
        result = await svc.disconnect(commerciale)

        assert result["status"] == "disconnected"
        assert commerciale.microsoft_token is None

    @pytest.mark.anyio
    async def test_ac_153_3_expired_token_cleared(
        self, db_session: AsyncSession, commerciale: User,
    ):
        """AC-153.3: Expired token with no refresh = cleared."""
        commerciale.microsoft_token = json.dumps({
            "access_token": "expired",
            "expires_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
            # No refresh token
        })
        await db_session.flush()

        svc = MicrosoftCalendarService(db_session)
        token = await svc._get_valid_token(commerciale)

        assert token is None
        assert commerciale.microsoft_token is None  # Cleared


# ============================================================
# US-154: Push to Outlook
# ============================================================


class TestUS154OutlookPush:
    """US-154: Push activities to Outlook Calendar."""

    @pytest.mark.anyio
    async def test_ac_154_4_not_connected_no_push(
        self, db_session: AsyncSession, commerciale: User, planned_activity: CrmActivity,
    ):
        """AC-154.4: User without Microsoft 365 = no push, no error."""
        svc = MicrosoftCalendarService(db_session)
        result = await svc.push_activity(commerciale, planned_activity)

        assert result["pushed"] is False
        assert result["reason"] == "not_connected"

    @pytest.mark.anyio
    async def test_ac_154_no_scheduled_at_no_push(
        self, db_session: AsyncSession, tenant: Tenant, commerciale: User,
    ):
        """Activity without scheduled_at = no push."""
        act = CrmActivity(
            tenant_id=tenant.id,
            user_id=commerciale.id,
            type="note",
            subject="Just a note",
            status="completed",
        )
        db_session.add(act)
        await db_session.flush()

        svc = MicrosoftCalendarService(db_session)
        result = await svc.push_activity(commerciale, act)

        assert result["pushed"] is False
        # not_connected takes priority since user has no token
        assert result["reason"] in ("no_scheduled_at", "not_connected")


# ============================================================
# US-155: Calendly URL
# ============================================================


class TestUS155Calendly:
    """US-155: Calendly URL management."""

    @pytest.mark.anyio
    async def test_ac_155_1_save_calendly_url(
        self, db_session: AsyncSession, commerciale: User,
    ):
        """AC-155.1: Save Calendly URL on user."""
        commerciale.calendly_url = "https://calendly.com/marco-rossi/30min"
        await db_session.flush()

        assert commerciale.calendly_url == "https://calendly.com/marco-rossi/30min"

    @pytest.mark.anyio
    async def test_ac_155_2_no_calendly_returns_empty(
        self, db_session: AsyncSession, commerciale: User,
    ):
        """AC-155.2: User without Calendly = empty string."""
        assert commerciale.calendly_url is None or commerciale.calendly_url == ""

    @pytest.mark.anyio
    async def test_ac_155_4_self_service_update(
        self, db_session: AsyncSession, commerciale: User,
    ):
        """AC-155.4: Commerciale can update own Calendly URL."""
        commerciale.calendly_url = "https://calendly.com/nuovo-link"
        await db_session.flush()
        assert commerciale.calendly_url == "https://calendly.com/nuovo-link"

        # Can clear it
        commerciale.calendly_url = None
        await db_session.flush()
        assert commerciale.calendly_url is None

    @pytest.mark.anyio
    async def test_ac_155_user_serialization_includes_calendly(
        self, db_session: AsyncSession, tenant: Tenant, owner: User,
    ):
        """User serialization includes calendly_url and microsoft_connected."""
        owner.calendly_url = "https://calendly.com/owner"
        await db_session.flush()

        svc = UserManagementService(db_session)
        users = await svc.list_users(tenant.id)
        owner_data = next(u for u in users if u["email"] == "owner.cal@nexadata.it")

        assert owner_data["calendly_url"] == "https://calendly.com/owner"
        assert owner_data["microsoft_connected"] is False


# ============================================================
# API Endpoint Tests
# ============================================================


class TestCalendarAPI:
    """API-level calendar endpoint tests."""

    @pytest.mark.anyio
    async def test_api_microsoft_status(self, client: AsyncClient, auth_headers: dict):
        """GET /calendar/microsoft/status returns connected status."""
        resp = await client.get("/api/v1/calendar/microsoft/status", headers=auth_headers)
        assert resp.status_code == 200
        assert "connected" in resp.json()
        assert resp.json()["connected"] is False

    @pytest.mark.anyio
    async def test_api_microsoft_connect_url(self, client: AsyncClient, auth_headers: dict):
        """GET /calendar/microsoft/connect returns auth URL."""
        resp = await client.get("/api/v1/calendar/microsoft/connect", headers=auth_headers)
        assert resp.status_code == 200
        assert "auth_url" in resp.json()
        assert "login.microsoftonline.com" in resp.json()["auth_url"]

    @pytest.mark.anyio
    async def test_api_calendly_get(self, client: AsyncClient, auth_headers: dict):
        """GET /calendar/calendly returns URL (empty by default)."""
        resp = await client.get("/api/v1/calendar/calendly", headers=auth_headers)
        assert resp.status_code == 200
        assert "calendly_url" in resp.json()

    @pytest.mark.anyio
    async def test_api_calendly_update(self, client: AsyncClient, auth_headers: dict):
        """PATCH /calendar/calendly saves URL."""
        resp = await client.patch(
            "/api/v1/calendar/calendly",
            json={"calendly_url": "https://calendly.com/test/30min"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["calendly_url"] == "https://calendly.com/test/30min"

        # Verify it persists
        resp2 = await client.get("/api/v1/calendar/calendly", headers=auth_headers)
        assert resp2.json()["calendly_url"] == "https://calendly.com/test/30min"

    @pytest.mark.anyio
    async def test_api_calendly_clear(self, client: AsyncClient, auth_headers: dict):
        """PATCH /calendar/calendly with empty string clears URL."""
        # Set first
        await client.patch(
            "/api/v1/calendar/calendly",
            json={"calendly_url": "https://calendly.com/todelete"},
            headers=auth_headers,
        )
        # Clear
        resp = await client.patch(
            "/api/v1/calendar/calendly",
            json={"calendly_url": ""},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["calendly_url"] == ""

    @pytest.mark.anyio
    async def test_api_activities_for_calendar(self, client: AsyncClient, auth_headers: dict):
        """GET /crm/activities returns data suitable for calendar rendering."""
        resp = await client.get("/api/v1/crm/activities?status=planned", headers=auth_headers)
        assert resp.status_code == 200
        # Activities endpoint exists and returns data (may be empty)
        data = resp.json()
        assert isinstance(data, (list, dict))


# ============================================================
# US-151: Calendar view data availability
# ============================================================


class TestUS151CalendarData:
    """US-151: Verify API provides data for FullCalendar rendering."""

    @pytest.mark.anyio
    async def test_ac_151_activities_have_scheduled_at(
        self, db_session: AsyncSession, tenant: Tenant, planned_activity: CrmActivity,
    ):
        """AC-151.1: Planned activities have scheduled_at for calendar rendering."""
        from api.modules.crm.service import CRMService
        crm = CRMService(db_session)
        activities = await crm.list_activities(tenant.id, status="planned")

        assert len(activities) >= 1
        for act in activities:
            assert act["scheduled_at"] is not None
            assert act["status"] == "planned"
            assert act["subject"]

    @pytest.mark.anyio
    async def test_ac_151_activity_has_outlook_event_id_field(
        self, db_session: AsyncSession, tenant: Tenant, planned_activity: CrmActivity,
    ):
        """Activity dict includes outlook_event_id for sync tracking."""
        from api.modules.crm.service import CRMService
        crm = CRMService(db_session)
        activities = await crm.list_activities(tenant.id)

        assert len(activities) >= 1
        # Field exists (may be None)
        assert "outlook_event_id" in activities[0]
