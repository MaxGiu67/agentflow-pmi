"""
Test suite for US-23: Bilancio CEE
Tests for 4 Acceptance Criteria (AC-23.1 through AC-23.4)
"""

from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import (
    Tenant, User, ChartAccount, JournalEntry, JournalLine,
)
from api.modules.fiscal.balance_sheet import BalanceSheetService
from api.modules.fiscal.accounting_engine import (
    AccountingEngine, PIANO_CONTI_SRL_ORDINARIO,
)
from tests.conftest import get_auth_token


async def _setup_piano_conti(db_session: AsyncSession, tenant: Tenant) -> None:
    """Helper: create chart of accounts for a tenant."""
    engine = AccountingEngine(db_session)
    await engine.create_piano_conti(
        tenant_id=str(tenant.id),
        tipo_azienda=tenant.type,
        regime_fiscale=tenant.regime_fiscale,
    )


async def _create_journal_entry(
    db_session: AsyncSession,
    tenant: Tenant,
    entry_date: date,
    lines: list[dict],
    status: str = "posted",
) -> JournalEntry:
    """Helper: create a journal entry with lines."""
    total_debit = sum(l.get("debit", 0) for l in lines)
    total_credit = sum(l.get("credit", 0) for l in lines)
    entry = JournalEntry(
        tenant_id=tenant.id,
        description="Test entry",
        entry_date=entry_date,
        total_debit=total_debit,
        total_credit=total_credit,
        status=status,
    )
    db_session.add(entry)
    await db_session.flush()

    for l in lines:
        line = JournalLine(
            entry_id=entry.id,
            account_code=l["account_code"],
            account_name=l["account_name"],
            debit=l.get("debit", 0.0),
            credit=l.get("credit", 0.0),
        )
        db_session.add(line)
    await db_session.flush()
    return entry


# ============================================================
# AC-23.1 — Genera SP e CE formato CEE, esportabile PDF/XBRL
# ============================================================


class TestAC231GeneraSPCE:
    """AC-23.1: Generate Stato Patrimoniale and Conto Economico in CEE format."""

    async def test_ac_231_genera_bilancio_cee(
        self, db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-23.1: DATO un tenant con piano conti e scritture,
        QUANDO genera bilancio CEE, ALLORA contiene SP e CE con codici CEE."""
        await _setup_piano_conti(db_session, tenant)

        # Create some journal entries
        await _create_journal_entry(
            db_session, tenant, date(2026, 3, 15),
            [
                {"account_code": "4010", "account_name": "Ricavi da vendite", "credit": 10000.0},
                {"account_code": "1020", "account_name": "Banca c/c", "debit": 10000.0},
            ],
        )
        await _create_journal_entry(
            db_session, tenant, date(2026, 3, 20),
            [
                {"account_code": "5020", "account_name": "Servizi", "debit": 3000.0},
                {"account_code": "2010", "account_name": "Debiti verso fornitori", "credit": 3000.0},
            ],
        )

        service = BalanceSheetService(db_session)
        result = await service.generate(tenant_id=tenant.id, year=2026)

        assert "stato_patrimoniale" in result
        assert "conto_economico" in result
        assert "attivo" in result["stato_patrimoniale"]
        assert "passivo" in result["stato_patrimoniale"]
        assert result["year"] == 2026

        # CE should contain revenue and expense items
        ce = result["conto_economico"]
        assert len(ce) > 0

        # Check CEE codes are present
        cee_keys = list(ce.keys())
        assert any("A.1" in k for k in cee_keys), "Should have revenue CEE code A.1"
        assert any("B.7" in k for k in cee_keys), "Should have expense CEE code B.7"

    async def test_ac_231_export_formats_available(
        self, db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-23.1: DATO bilancio generato,
        ALLORA export_formats include pdf e xbrl."""
        await _setup_piano_conti(db_session, tenant)

        service = BalanceSheetService(db_session)
        result = await service.generate(tenant_id=tenant.id, year=2026)

        assert "export_formats" in result
        assert "pdf" in result["export_formats"]
        assert "xbrl" in result["export_formats"]

    async def test_ac_231_bilancio_via_api(
        self, client: AsyncClient, db_session: AsyncSession,
        tenant: Tenant, auth_headers: dict,
    ):
        """AC-23.1: DATO utente autenticato con piano conti,
        QUANDO richiede bilancio via API, ALLORA riceve risposta valida."""
        await _setup_piano_conti(db_session, tenant)

        resp = await client.get(
            "/api/v1/accounting/balance-sheet?year=2026",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["year"] == 2026
        assert "stato_patrimoniale" in data
        assert "conto_economico" in data

    async def test_ac_231_senza_piano_conti_errore(
        self, client: AsyncClient, auth_headers: dict,
    ):
        """AC-23.1: DATO tenant senza piano conti,
        QUANDO richiede bilancio, ALLORA errore."""
        resp = await client.get(
            "/api/v1/accounting/balance-sheet?year=2026",
            headers=auth_headers,
        )
        assert resp.status_code == 400
        assert "Piano dei conti" in resp.json()["detail"]


# ============================================================
# AC-23.2 — Scritture non chiuse -> avviso
# ============================================================


class TestAC232ScrittureNonChiuse:
    """AC-23.2: Unclosed entries generate warning."""

    async def test_ac_232_avviso_scritture_draft(
        self, db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-23.2: DATO scritture in stato draft,
        QUANDO genera bilancio, ALLORA avviso con conteggio."""
        await _setup_piano_conti(db_session, tenant)

        # Create a posted entry
        await _create_journal_entry(
            db_session, tenant, date(2026, 1, 15),
            [
                {"account_code": "4010", "account_name": "Ricavi", "credit": 5000.0},
                {"account_code": "1020", "account_name": "Banca", "debit": 5000.0},
            ],
            status="posted",
        )

        # Create a draft entry (not closed)
        await _create_journal_entry(
            db_session, tenant, date(2026, 2, 10),
            [
                {"account_code": "5020", "account_name": "Servizi", "debit": 1000.0},
                {"account_code": "2010", "account_name": "Fornitori", "credit": 1000.0},
            ],
            status="draft",
        )

        service = BalanceSheetService(db_session)
        result = await service.generate(tenant_id=tenant.id, year=2026)

        assert len(result["warnings"]) > 0
        warning = result["warnings"][0]
        assert "bozza" in warning.lower() or "draft" in warning.lower()
        assert "1" in warning  # 1 draft entry

    async def test_ac_232_no_avviso_se_tutte_chiuse(
        self, db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-23.2: DATO tutte scritture posted,
        QUANDO genera bilancio, ALLORA nessun avviso."""
        await _setup_piano_conti(db_session, tenant)

        await _create_journal_entry(
            db_session, tenant, date(2026, 3, 1),
            [
                {"account_code": "4010", "account_name": "Ricavi", "credit": 2000.0},
                {"account_code": "1020", "account_name": "Banca", "debit": 2000.0},
            ],
            status="posted",
        )

        service = BalanceSheetService(db_session)
        result = await service.generate(tenant_id=tenant.id, year=2026)

        assert len(result["warnings"]) == 0


# ============================================================
# AC-23.3 — Bilancio abbreviato micro-impresa (< art. 2435-ter)
# ============================================================


class TestAC233MicroImpresa:
    """AC-23.3: Micro-impresa gets abbreviated balance sheet."""

    async def test_ac_233_micro_impresa_format_abbreviato(
        self, db_session: AsyncSession,
    ):
        """AC-23.3: DATO tenant ditta individuale (micro),
        QUANDO genera bilancio, ALLORA formato abbreviato."""
        tenant_micro = Tenant(
            name="Mario Rossi P.IVA",
            type="ditta_individuale",
            regime_fiscale="semplificato",
            piva="11122233344",
        )
        db_session.add(tenant_micro)
        await db_session.flush()

        # Create minimal piano conti
        engine = AccountingEngine(db_session)
        await engine.create_piano_conti(
            tenant_id=str(tenant_micro.id),
            tipo_azienda=tenant_micro.type,
            regime_fiscale=tenant_micro.regime_fiscale,
        )

        service = BalanceSheetService(db_session)
        result = await service.generate(tenant_id=tenant_micro.id, year=2026)

        assert result["is_micro_impresa"] is True
        assert result["format"] == "abbreviato"

    async def test_ac_233_srl_non_micro(
        self, db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-23.3: DATO tenant SRL,
        QUANDO genera bilancio, ALLORA formato ordinario."""
        await _setup_piano_conti(db_session, tenant)

        service = BalanceSheetService(db_session)
        result = await service.generate(tenant_id=tenant.id, year=2026)

        assert result["is_micro_impresa"] is False
        assert result["format"] == "ordinario"

    async def test_ac_233_srls_micro(
        self, db_session: AsyncSession,
    ):
        """AC-23.3: DATO tenant SRLS (sotto soglie),
        QUANDO genera bilancio, ALLORA formato abbreviato."""
        tenant_srls = Tenant(
            name="Piccola SRLS",
            type="srls",
            regime_fiscale="semplificato",
            piva="55566677788",
        )
        db_session.add(tenant_srls)
        await db_session.flush()

        engine = AccountingEngine(db_session)
        await engine.create_piano_conti(
            tenant_id=str(tenant_srls.id),
            tipo_azienda=tenant_srls.type,
            regime_fiscale=tenant_srls.regime_fiscale,
        )

        service = BalanceSheetService(db_session)
        result = await service.generate(tenant_id=tenant_srls.id, year=2026)

        assert result["is_micro_impresa"] is True
        assert result["format"] == "abbreviato"


# ============================================================
# AC-23.4 — Primo esercizio -> colonna anno precedente vuota
# ============================================================


class TestAC234PrimoEsercizio:
    """AC-23.4: First fiscal year shows empty prior-year column."""

    async def test_ac_234_primo_esercizio_prior_vuota(
        self, db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-23.4: DATO primo esercizio,
        QUANDO genera bilancio, ALLORA anno precedente vuoto."""
        await _setup_piano_conti(db_session, tenant)

        # Create entry for current year
        await _create_journal_entry(
            db_session, tenant, date(2026, 6, 1),
            [
                {"account_code": "4010", "account_name": "Ricavi", "credit": 8000.0},
                {"account_code": "1020", "account_name": "Banca", "debit": 8000.0},
            ],
        )

        service = BalanceSheetService(db_session)
        result = await service.generate(
            tenant_id=tenant.id, year=2026, is_first_year=True,
        )

        assert result["is_first_year"] is True
        assert result["stato_patrimoniale_prior"]["attivo"] == {}
        assert result["stato_patrimoniale_prior"]["passivo"] == {}
        assert result["conto_economico_prior"] == {}

    async def test_ac_234_secondo_esercizio_prior_popolata(
        self, db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-23.4: DATO secondo esercizio con dati anno precedente,
        QUANDO genera bilancio, ALLORA anno precedente popolato."""
        await _setup_piano_conti(db_session, tenant)

        # Create entry for prior year (2025)
        await _create_journal_entry(
            db_session, tenant, date(2025, 6, 1),
            [
                {"account_code": "4010", "account_name": "Ricavi", "credit": 5000.0},
                {"account_code": "1020", "account_name": "Banca", "debit": 5000.0},
            ],
        )
        # Create entry for current year (2026)
        await _create_journal_entry(
            db_session, tenant, date(2026, 3, 1),
            [
                {"account_code": "4010", "account_name": "Ricavi", "credit": 7000.0},
                {"account_code": "1020", "account_name": "Banca", "debit": 7000.0},
            ],
        )

        service = BalanceSheetService(db_session)
        result = await service.generate(
            tenant_id=tenant.id, year=2026, is_first_year=False,
        )

        assert result["is_first_year"] is False
        # Prior year should have data
        sp_prior = result["stato_patrimoniale_prior"]
        ce_prior = result["conto_economico_prior"]
        assert len(sp_prior["attivo"]) > 0 or len(ce_prior) > 0

    async def test_ac_234_api_primo_esercizio(
        self, client: AsyncClient, db_session: AsyncSession,
        tenant: Tenant, auth_headers: dict,
    ):
        """AC-23.4: DATO primo esercizio via API,
        QUANDO richiede bilancio, ALLORA is_first_year detection works."""
        await _setup_piano_conti(db_session, tenant)

        resp = await client.get(
            "/api/v1/accounting/balance-sheet?year=2026",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        # API defaults to is_first_year=False, but should work
        assert "stato_patrimoniale_prior" in data
