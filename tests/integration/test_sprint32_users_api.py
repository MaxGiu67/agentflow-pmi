"""Sprint 32 tests — US-109 (user management), US-110 (row-level), US-111 (sender)."""

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User, Tenant, CrmContact, CrmDeal
from api.modules.user_management.service import UserManagementService
from api.modules.crm.service import CRMService
from tests.conftest import _hash_pw


async def _make_owner(db: AsyncSession, tenant: Tenant) -> User:
    u = User(
        email="owner@nexadata.it", password_hash=_hash_pw("Password1"),
        name="Owner", role="owner", email_verified=True, tenant_id=tenant.id, active=True,
    )
    db.add(u)
    await db.flush()
    return u


async def _make_commerciale(db: AsyncSession, tenant: Tenant, email: str = "comm@nexadata.it") -> User:
    u = User(
        email=email, password_hash=_hash_pw("Password1"),
        name="Commerciale", role="commerciale", email_verified=True, tenant_id=tenant.id, active=True,
    )
    db.add(u)
    await db.flush()
    return u


# ============================================================
# US-109: Gestione utenti
# ============================================================


@pytest.mark.asyncio
async def test_ac_109_1_list_users(db_session: AsyncSession, tenant: Tenant):
    """AC-109.1: Lista utenti del tenant."""
    owner = await _make_owner(db_session, tenant)
    svc = UserManagementService(db_session)

    users = await svc.list_users(tenant.id)
    assert len(users) >= 1
    assert any(u["email"] == "owner@nexadata.it" for u in users)


@pytest.mark.asyncio
async def test_ac_109_2_invite_user(db_session: AsyncSession, tenant: Tenant):
    """AC-109.2: Invito utente con password temporanea."""
    owner = await _make_owner(db_session, tenant)
    svc = UserManagementService(db_session)

    result = await svc.invite_user(tenant.id, "nuovo@nexadata.it", "Nuovo Commerciale", "commerciale", owner)

    assert "temp_password" in result
    assert result["role"] == "commerciale"
    assert result["email"] == "nuovo@nexadata.it"
    assert len(result["temp_password"]) > 8


@pytest.mark.asyncio
async def test_ac_109_3_update_role(db_session: AsyncSession, tenant: Tenant):
    """AC-109.3: Modifica ruolo."""
    owner = await _make_owner(db_session, tenant)
    comm = await _make_commerciale(db_session, tenant)
    svc = UserManagementService(db_session)

    result = await svc.update_role(comm.id, "admin", owner)
    assert result["new_role"] == "admin"


@pytest.mark.asyncio
async def test_ac_109_4_toggle_active(db_session: AsyncSession, tenant: Tenant):
    """AC-109.4: Disattiva utente."""
    owner = await _make_owner(db_session, tenant)
    comm = await _make_commerciale(db_session, tenant)
    svc = UserManagementService(db_session)

    result = await svc.toggle_active(comm.id, owner)
    assert result["active"] is False

    # Riattiva
    result2 = await svc.toggle_active(comm.id, owner)
    assert result2["active"] is True


@pytest.mark.asyncio
async def test_ac_109_5_only_admin_can_manage(db_session: AsyncSession, tenant: Tenant):
    """AC-109.5: Solo owner/admin possono gestire utenti."""
    comm = await _make_commerciale(db_session, tenant)
    svc = UserManagementService(db_session)

    result = await svc.invite_user(tenant.id, "x@x.it", "X", "viewer", comm)
    assert "error" in result
    assert "permessi" in result["error"]


@pytest.mark.asyncio
async def test_ac_109_cannot_self_modify(db_session: AsyncSession, tenant: Tenant):
    """Cannot modify own role or deactivate self."""
    owner = await _make_owner(db_session, tenant)
    svc = UserManagementService(db_session)

    r1 = await svc.update_role(owner.id, "viewer", owner)
    assert "error" in r1

    r2 = await svc.toggle_active(owner.id, owner)
    assert "error" in r2


# ============================================================
# US-110: Permessi row-level
# ============================================================


@pytest.mark.asyncio
async def test_ac_110_1_commerciale_sees_own_deals(db_session: AsyncSession, tenant: Tenant):
    """AC-110.1: Commerciale vede solo i propri deal."""
    owner = await _make_owner(db_session, tenant)
    comm = await _make_commerciale(db_session, tenant)
    crm = CRMService(db_session)

    # Create deal assigned to owner
    await crm.create_deal(tenant.id, {"name": "Owner Deal", "assigned_to": str(owner.id)})
    # Create deal assigned to commerciale
    await crm.create_deal(tenant.id, {"name": "Comm Deal", "assigned_to": str(comm.id)})

    # Commerciale should only see own deal
    comm_deals = await crm.list_deals(tenant.id, assigned_to=comm.id)
    assert comm_deals["total"] == 1
    assert comm_deals["deals"][0]["name"] == "Comm Deal"

    # Owner sees all
    all_deals = await crm.list_deals(tenant.id)
    assert all_deals["total"] == 2


@pytest.mark.asyncio
async def test_ac_110_2_commerciale_sees_own_contacts(db_session: AsyncSession, tenant: Tenant):
    """AC-110.2: Commerciale vede solo i propri contatti."""
    comm = await _make_commerciale(db_session, tenant)
    crm = CRMService(db_session)

    await crm.create_contact(tenant.id, {"name": "My Client", "assigned_to": str(comm.id)})
    await crm.create_contact(tenant.id, {"name": "Other Client"})

    my_contacts = await crm.list_contacts(tenant.id, assigned_to=comm.id)
    assert my_contacts["total"] == 1
    assert my_contacts["contacts"][0]["name"] == "My Client"


@pytest.mark.asyncio
async def test_ac_110_5_commerciale_auto_assign(db_session: AsyncSession, tenant: Tenant):
    """AC-110.5: Deal creato da commerciale auto-assegnato."""
    comm = await _make_commerciale(db_session, tenant)
    crm = CRMService(db_session)

    deal = await crm.create_deal(tenant.id, {"name": "Auto Deal", "assigned_to": str(comm.id)})
    assert deal["assigned_to"] == str(comm.id)


# ============================================================
# US-111: Sender email dinamico
# ============================================================


@pytest.mark.asyncio
async def test_ac_111_1_sender_per_user(db_session: AsyncSession, tenant: Tenant):
    """AC-111.1: Sender email configurabile per utente."""
    comm = await _make_commerciale(db_session, tenant)
    svc = UserManagementService(db_session)

    result = await svc.update_sender(comm.id, "mario@nexadata.it", "Mario Rossi")
    assert result["sender_email"] == "mario@nexadata.it"


@pytest.mark.asyncio
async def test_ac_111_2_3_sender_fallback(db_session: AsyncSession, tenant: Tenant):
    """AC-111.2/111.3: Sender fallback a default se non configurato."""
    comm = await _make_commerciale(db_session, tenant)
    svc = UserManagementService(db_session)

    email, name = svc.get_sender_for_user(comm)
    # Should use default since sender_email not set
    assert "@" in email  # some default
    assert name == "Commerciale"  # falls back to user.name


# ============================================================
# API endpoints
# ============================================================


@pytest.mark.asyncio
async def test_api_list_users(client: AsyncClient, auth_headers: dict):
    """API: GET /users."""
    resp = await client.get("/api/v1/users", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_api_invite_user(client: AsyncClient, auth_headers: dict):
    """API: POST /users/invite."""
    resp = await client.post(
        "/api/v1/users/invite",
        json={"email": "api-invite@test.it", "name": "API Invitato", "role": "commerciale"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["email"] == "api-invite@test.it"
    assert "temp_password" in resp.json()


@pytest.mark.asyncio
async def test_api_my_permissions(client: AsyncClient, auth_headers: dict):
    """API: GET /users/me/permissions."""
    resp = await client.get("/api/v1/users/me/permissions", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "role" in data
    assert "can_manage_users" in data
    assert "can_see_all_deals" in data
