"""Test registrazione con creazione tenant automatica."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import Tenant, User


@pytest.mark.asyncio
async def test_register_creates_tenant(client: AsyncClient, db_session: AsyncSession):
    """Registrazione con dati azienda crea Tenant + User owner."""
    resp = await client.post("/api/v1/auth/register", json={
        "email": "nuovo@azienda.it",
        "password": "TestPass1",
        "name": "Nuovo Utente",
        "azienda_nome": "Nuova Azienda SRL",
        "azienda_tipo": "srl",
        "azienda_piva": "11111111111",
        "regime_fiscale": "ordinario",
    })

    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "nuovo@azienda.it"

    # Verify tenant created
    result = await db_session.execute(
        select(Tenant).where(Tenant.name == "Nuova Azienda SRL")
    )
    tenant = result.scalar_one_or_none()
    assert tenant is not None
    assert tenant.piva == "11111111111"
    assert tenant.type == "srl"

    # Verify user linked to tenant
    user_result = await db_session.execute(
        select(User).where(User.email == "nuovo@azienda.it")
    )
    user = user_result.scalar_one()
    assert user.tenant_id == tenant.id
    assert user.role == "owner"


@pytest.mark.asyncio
async def test_register_without_azienda(client: AsyncClient, db_session: AsyncSession):
    """Registrazione senza dati azienda — user senza tenant (completa dopo)."""
    resp = await client.post("/api/v1/auth/register", json={
        "email": "solo@utente.it",
        "password": "TestPass1",
        "name": "Solo Utente",
    })

    assert resp.status_code == 201

    user_result = await db_session.execute(
        select(User).where(User.email == "solo@utente.it")
    )
    user = user_result.scalar_one()
    assert user.tenant_id is None  # no tenant yet
