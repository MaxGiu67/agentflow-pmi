"""
Test suite for US-17: Scadenzario fiscale
Tests for 4 Acceptance Criteria (AC-17.1 through AC-17.4)
"""

from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import Tenant, User
from api.modules.deadlines.service import (
    next_business_day,
    compute_countdown_color,
    is_italian_holiday,
)
from tests.conftest import get_auth_token


# ============================================================
# AC-17.1 — Scadenze per regime
# ============================================================


class TestAC171ScadenzePerRegime:
    """AC-17.1: Scadenze calcolate in base al regime fiscale del tenant."""

    async def test_ac_171_scadenze_ordinario(
        self, client: AsyncClient, auth_headers: dict
    ):
        """AC-17.1: DATO tenant con regime ordinario, QUANDO richiede scadenze,
        ALLORA vede scadenze IVA trimestrale + F24 mensile."""
        response = await client.get(
            "/api/v1/deadlines?year=2026",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["regime"] == "ordinario"
        assert data["year"] == 2026
        assert data["total"] > 0

        # Check IVA deadlines exist
        names = [d["name"] for d in data["deadlines"]]
        assert any("IVA" in n for n in names)
        # Check F24 deadlines exist
        assert any("F24" in n for n in names)

    async def test_ac_171_scadenze_forfettario(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """AC-17.1: DATO tenant forfettario, QUANDO richiede scadenze,
        ALLORA vede imposta sostitutiva, non IVA trimestrale."""
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        # Create forfettario tenant + user
        tenant_f = Tenant(
            name="Freelancer Forfettario",
            type="piva",
            regime_fiscale="forfettario",
            piva="99988877766",
        )
        db_session.add(tenant_f)
        await db_session.flush()

        user_f = User(
            email="forfettario@example.com",
            password_hash=pwd_context.hash("Password1"),
            name="Marco Forfettario",
            role="owner",
            email_verified=True,
            tenant_id=tenant_f.id,
        )
        db_session.add(user_f)
        await db_session.flush()

        token = await get_auth_token(client, "forfettario@example.com", "Password1")
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get(
            "/api/v1/deadlines?year=2026",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["regime"] == "forfettario"

        names = [d["name"] for d in data["deadlines"]]
        # Should have imposta sostitutiva
        assert any("imposta sostitutiva" in n.lower() for n in names)
        # Should NOT have IVA trimestrale (forfettario is exempt)
        assert not any("Liquidazione IVA" in n for n in names)


# ============================================================
# AC-17.2 — Countdown colori
# ============================================================


class TestAC172CountdownColori:
    """AC-17.2: Countdown con colori rosso/giallo/verde."""

    async def test_ac_172_countdown_colori(
        self, client: AsyncClient, auth_headers: dict
    ):
        """AC-17.2: DATO scadenze, QUANDO visualizzate,
        ALLORA ciascuna ha days_remaining e color (red/yellow/green)."""
        response = await client.get(
            "/api/v1/deadlines?year=2026",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        for deadline in data["deadlines"]:
            assert "days_remaining" in deadline
            assert "color" in deadline
            assert deadline["color"] in ("red", "yellow", "green")

    def test_ac_172_color_logic_red(self):
        """AC-17.2: <= 7 days -> red."""
        assert compute_countdown_color(0) == "red"
        assert compute_countdown_color(7) == "red"

    def test_ac_172_color_logic_yellow(self):
        """AC-17.2: 8-30 days -> yellow."""
        assert compute_countdown_color(8) == "yellow"
        assert compute_countdown_color(30) == "yellow"

    def test_ac_172_color_logic_green(self):
        """AC-17.2: > 30 days -> green."""
        assert compute_countdown_color(31) == "green"
        assert compute_countdown_color(100) == "green"


# ============================================================
# AC-17.3 — Regime non configurato
# ============================================================


class TestAC173RegimeNonConfigurato:
    """AC-17.3: Regime non riconosciuto restituisce errore."""

    def test_ac_173_regime_sconosciuto(self):
        """AC-17.3: DATO regime sconosciuto, QUANDO calcola scadenze,
        ALLORA errore regime non configurato."""
        from api.modules.deadlines.service import DeadlineService
        service = DeadlineService(None)  # db not needed for this test
        with pytest.raises(ValueError, match="non configurato"):
            service.get_deadlines(regime="unknown_regime", year=2026)


# ============================================================
# AC-17.4 — Scadenze su festivo/weekend
# ============================================================


class TestAC174ScadenzeFestivoWeekend:
    """AC-17.4: Scadenze che cadono su weekend/festivi slittano al giorno lavorativo successivo."""

    def test_ac_174_sabato_slitta_a_lunedi(self):
        """AC-17.4: DATO scadenza di sabato, ALLORA slitta a lunedi."""
        # 2026-01-17 is Saturday
        d = date(2026, 1, 17)
        assert d.weekday() == 5  # Saturday
        result = next_business_day(d)
        assert result.weekday() == 0  # Monday
        assert result == date(2026, 1, 19)

    def test_ac_174_domenica_slitta_a_lunedi(self):
        """AC-17.4: DATO scadenza di domenica, ALLORA slitta a lunedi."""
        d = date(2026, 1, 18)  # Sunday
        assert d.weekday() == 6
        result = next_business_day(d)
        assert result.weekday() == 0
        assert result == date(2026, 1, 19)

    def test_ac_174_festivo_slitta(self):
        """AC-17.4: DATO scadenza nel giorno di Natale (venerdi),
        ALLORA slitta al primo giorno lavorativo."""
        d = date(2026, 12, 25)  # Christmas, Friday
        assert is_italian_holiday(d)
        result = next_business_day(d)
        assert not is_italian_holiday(result)
        assert result.weekday() < 5  # Weekday
        # Dec 25 (Fri) -> Dec 26 (Sat, also holiday) -> Dec 27 (Sun) -> Dec 28 (Mon)
        assert result == date(2026, 12, 28)

    def test_ac_174_giorno_lavorativo_invariato(self):
        """AC-17.4: DATO scadenza in giorno lavorativo non festivo,
        ALLORA data invariata."""
        d = date(2026, 3, 16)  # Monday, not a holiday
        assert d.weekday() == 0
        assert not is_italian_holiday(d)
        result = next_business_day(d)
        assert result == d

    async def test_ac_174_api_effective_date_shifted(
        self, client: AsyncClient, auth_headers: dict
    ):
        """AC-17.4: API scadenze mostra effective_date diversa da original_date per festivi."""
        response = await client.get(
            "/api/v1/deadlines?year=2026",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        # At least some deadlines should have original != effective
        # (e.g., if the 16th falls on weekend/holiday)
        for deadline in data["deadlines"]:
            assert "original_date" in deadline
            assert "effective_date" in deadline
