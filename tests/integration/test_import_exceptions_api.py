"""Integration tests for import exceptions / silent import (US-71)."""

import pytest
from httpx import AsyncClient

from tests.conftest import get_auth_token


@pytest.fixture
async def exceptions_data(db_session, tenant):
    """Create test import exceptions with varying severity."""
    from api.db.models import ImportException

    items = []
    for i, (sev, title) in enumerate([
        ("error", "Fattura #234: importo anomalo (€45.000 vs media €2.000)"),
        ("warning", "Fattura #567: fornitore nuovo, categorizzazione manuale richiesta"),
        ("warning", "Corrispettivo 15/03: totale non quadra con scontrini"),
        ("info", "3 movimenti bancari non abbinati automaticamente"),
        ("warning", "F24 Marzo: differenza €12 rispetto al calcolato"),
    ]):
        exc = ImportException(
            tenant_id=tenant.id,
            source_type="fatture" if i < 2 else "corrispettivi" if i == 2 else "banca" if i == 3 else "f24",
            severity=sev,
            title=title,
            description=f"Dettaglio eccezione {i+1}",
            action_label="Verifica" if sev == "error" else "Rivedi",
        )
        db_session.add(exc)
        items.append(exc)

    await db_session.flush()
    return items


# --- AC-71.1: Successful import → synthetic message, no action ---

@pytest.mark.asyncio
async def test_ac_71_1_no_exceptions_returns_empty(client: AsyncClient, verified_user):
    """AC-71.1: Nessuna eccezione → lista vuota, zero azioni richieste."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")

    resp = await client.get(
        "/api/v1/completeness-score/exceptions",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["visible_count"] == 0
    assert data["total_pending"] == 0
    assert data["has_more"] is False


# --- AC-71.2: Import with anomalies → exceptions as pending actions (max 3) ---

@pytest.mark.asyncio
async def test_ac_71_2_shows_max_3_exceptions(client: AsyncClient, verified_user, exceptions_data):
    """AC-71.2: Con 5 eccezioni → mostra solo le 3 piu urgenti."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")

    resp = await client.get(
        "/api/v1/completeness-score/exceptions",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["visible_count"] == 3  # max 3
    assert data["total_pending"] == 5

    # First should be error (highest severity)
    assert data["visible"][0]["severity"] == "error"


@pytest.mark.asyncio
async def test_ac_71_2_exceptions_ordered_by_severity(client: AsyncClient, verified_user, exceptions_data):
    """AC-71.2: Le eccezioni sono ordinate: error > warning > info."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")

    resp = await client.get(
        "/api/v1/completeness-score/exceptions",
        headers={"Authorization": f"Bearer {token}"},
    )

    visible = resp.json()["visible"]
    severities = [e["severity"] for e in visible]

    # error should come first
    assert severities[0] == "error"
    # no info should appear before warnings (in top 3)
    assert "info" not in severities[:2]


# --- AC-71.3: More than 3 → has_more + remaining count ---

@pytest.mark.asyncio
async def test_ac_71_3_has_more_with_count(client: AsyncClient, verified_user, exceptions_data):
    """AC-71.3: 5 eccezioni → has_more=true, remaining=2."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")

    resp = await client.get(
        "/api/v1/completeness-score/exceptions",
        headers={"Authorization": f"Bearer {token}"},
    )

    data = resp.json()
    assert data["has_more"] is True
    assert data["remaining"] == 2


@pytest.mark.asyncio
async def test_ac_71_3_all_endpoint_shows_full_backlog(client: AsyncClient, verified_user, exceptions_data):
    """AC-71.3: /exceptions/all mostra tutte le eccezioni (backlog completo)."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")

    resp = await client.get(
        "/api/v1/completeness-score/exceptions/all",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert len(data["items"]) == 5


# --- Resolve exception ---

@pytest.mark.asyncio
async def test_resolve_exception_removes_from_pending(client: AsyncClient, verified_user, exceptions_data):
    """Risolvere un'eccezione la rimuove dalle pending."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")

    # Get current exceptions
    resp = await client.get(
        "/api/v1/completeness-score/exceptions",
        headers={"Authorization": f"Bearer {token}"},
    )
    first_id = resp.json()["visible"][0]["id"]

    # Resolve it
    resp2 = await client.post(
        f"/api/v1/completeness-score/exceptions/{first_id}/resolve",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp2.status_code == 200
    assert resp2.json()["resolved"] is True

    # Check it's gone from pending
    resp3 = await client.get(
        "/api/v1/completeness-score/exceptions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp3.json()["total_pending"] == 4
