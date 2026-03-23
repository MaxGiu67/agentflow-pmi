"""
Test suite for US-16: Onboarding guidato
Tests for 5 Acceptance Criteria (AC-16.1 through AC-16.5)
"""

import uuid
from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import OnboardingState, Tenant, User
from tests.conftest import get_auth_token


# ============================================================
# AC-16.1 — Wizard in <5 min (tipo azienda → regime/P.IVA → SPID → sync)
# ============================================================


class TestAC161OnboardingWizard:
    """AC-16.1: Onboarding wizard complete flow."""

    async def test_ac_161_onboarding_wizard_full_flow(
        self,
        client: AsyncClient,
        onboarding_auth_headers: dict,
    ):
        """AC-16.1: DATO nuovo utente,
        QUANDO completa tutti i passi, ALLORA onboarding completato."""
        # Check initial status
        resp = await client.get(
            "/api/v1/onboarding/status",
            headers=onboarding_auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["step_completed"] == 0
        assert data["completed"] is False
        assert data["current_step"] == 1

        # Step 1: Profile
        resp = await client.post(
            "/api/v1/onboarding/step/1",
            json={"data": {"tipo_azienda": "srl"}},
            headers=onboarding_auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["step"] == 1
        assert data["step_completed"] == 1

        # Step 2: P.IVA
        resp = await client.post(
            "/api/v1/onboarding/step/2",
            json={"data": {"piva": "12345678901", "regime": "ordinario"}},
            headers=onboarding_auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["step"] == 2
        assert data["step_completed"] == 2

        # Step 3: SPID
        resp = await client.post(
            "/api/v1/onboarding/step/3",
            json={"data": {"spid_success": True}},
            headers=onboarding_auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["step"] == 3
        assert data["step_completed"] == 3

        # Step 4: Sync
        resp = await client.post(
            "/api/v1/onboarding/step/4",
            json={"data": {}},
            headers=onboarding_auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["step"] == 4
        assert data["step_completed"] == 4
        assert data["completed"] is True

        # Verify final status
        resp = await client.get(
            "/api/v1/onboarding/status",
            headers=onboarding_auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["completed"] is True
        assert data["step_completed"] == 4


# ============================================================
# AC-16.2 — Time-to-value → fatture in dashboard entro 60s
# ============================================================


class TestAC162TimeToValue:
    """AC-16.2: After sync, invoices are visible in dashboard."""

    async def test_ac_162_time_to_value(
        self,
        client: AsyncClient,
        spid_auth_headers: dict,
        db_session: AsyncSession,
        tenant: Tenant,
    ):
        """AC-16.2: DATO onboarding completato con sync,
        QUANDO dashboard, ALLORA fatture visibili."""
        from tests.conftest import create_invoice

        # Simulate invoices synced during onboarding
        for i in range(3):
            inv = create_invoice(
                tenant_id=tenant.id,
                numero=f"FT-TTV-{i:03d}",
                piva=f"IT{80000000000 + i}",
                nome=f"Fornitore TTV {i}",
                source="cassetto_fiscale",
                status="pending",
            )
            db_session.add(inv)
        await db_session.flush()

        # Dashboard should show invoices
        response = await client.get(
            "/api/v1/dashboard/summary",
            headers=spid_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["counters"]["total"] >= 3
        assert len(data["recent_invoices"]) >= 3


# ============================================================
# AC-16.3 — Onboarding abbandonato → riprende dal punto lasciato
# ============================================================


class TestAC163Abbandonato:
    """AC-16.3: Abandoned onboarding resumes from where left off."""

    async def test_ac_163_abbandonato(
        self,
        client: AsyncClient,
        onboarding_auth_headers: dict,
    ):
        """AC-16.3: DATO onboarding iniziato e abbandonato a step 2,
        QUANDO riprendo, ALLORA ripartenza da step 2."""
        # Complete step 1
        resp = await client.post(
            "/api/v1/onboarding/step/1",
            json={"data": {"tipo_azienda": "srl"}},
            headers=onboarding_auth_headers,
        )
        assert resp.status_code == 200

        # Complete step 2
        resp = await client.post(
            "/api/v1/onboarding/step/2",
            json={"data": {}},
            headers=onboarding_auth_headers,
        )
        assert resp.status_code == 200

        # "Abandon" — user leaves, then comes back
        # Check status — should resume from step 3
        resp = await client.get(
            "/api/v1/onboarding/status",
            headers=onboarding_auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()

        assert data["step_completed"] == 2
        assert data["current_step"] == 3
        assert data["step1_profile"] is True
        assert data["step2_piva"] is True
        assert data["step3_spid"] is False
        assert data["completed"] is False


# ============================================================
# AC-16.4 — SPID fallisce → completa passi 1-2, suggerisce retry
# ============================================================


class TestAC164SpidFallisce:
    """AC-16.4: SPID failure allows steps 1-2, suggests retry."""

    async def test_ac_164_spid_fallisce(
        self,
        client: AsyncClient,
        onboarding_auth_headers: dict,
    ):
        """AC-16.4: DATO SPID fallisce,
        QUANDO autenticazione SPID non riesce, ALLORA passi 1-2 ok, suggerisce retry."""
        # Complete steps 1-2
        await client.post(
            "/api/v1/onboarding/step/1",
            json={"data": {"tipo_azienda": "srl"}},
            headers=onboarding_auth_headers,
        )
        await client.post(
            "/api/v1/onboarding/step/2",
            json={"data": {}},
            headers=onboarding_auth_headers,
        )

        # Try SPID — fails
        resp = await client.post(
            "/api/v1/onboarding/step/3",
            json={"data": {"spid_success": False}},
            headers=onboarding_auth_headers,
        )
        assert resp.status_code == 400
        data = resp.json()
        assert "spid" in data["detail"].lower() or "riprova" in data["detail"].lower()

        # Status should show steps 1-2 done, step 3 not done
        resp = await client.get(
            "/api/v1/onboarding/status",
            headers=onboarding_auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["step1_profile"] is True
        assert data["step2_piva"] is True
        assert data["step3_spid"] is False
        assert data["step_completed"] == 2


# ============================================================
# AC-16.5 — Tipo "Altro" → piano generico con nota commercialista
# ============================================================


class TestAC165TipoAltro:
    """AC-16.5: Tipo 'Altro' creates generic piano conti with commercialista note."""

    async def test_ac_165_tipo_altro(
        self,
        client: AsyncClient,
        onboarding_auth_headers: dict,
    ):
        """AC-16.5: DATO tipo azienda 'altro',
        QUANDO step 1, ALLORA piano generico con nota commercialista."""
        resp = await client.post(
            "/api/v1/onboarding/step/1",
            json={"data": {"tipo_azienda": "altro"}},
            headers=onboarding_auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()

        assert data["step"] == 1
        assert data["piano_conti_note"] is not None
        assert "commercialista" in data["piano_conti_note"].lower()
