"""
Test suite for US-30: Note spese — approvazione e rimborso
Tests for 5 Acceptance Criteria (AC-30.1 through AC-30.5)
"""

import uuid
from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import Expense, Tenant, User
from tests.conftest import get_auth_token


# ============================================================
# AC-30.1 — Approvazione -> DARE Trasferte / AVERE Debiti dipendenti
# ============================================================


class TestAC301Approvazione:
    """AC-30.1: Approvazione -> DARE Trasferte / AVERE Debiti dipendenti."""

    async def test_ac_301_approve_generates_journal_entry(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant, verified_user: User,
    ):
        """AC-30.1: DATO spesa submitted,
        QUANDO approve, ALLORA journal entry DARE Trasferte/AVERE Debiti."""
        # Create expense
        expense = Expense(
            tenant_id=tenant.id,
            user_id=verified_user.id,
            description="Pranzo di lavoro",
            amount=22.50,
            currency="EUR",
            amount_eur=22.50,
            category="Pranzo",
            expense_date=date(2026, 3, 20),
            status="submitted",
        )
        db_session.add(expense)
        await db_session.flush()

        resp = await client.patch(
            f"/api/v1/expenses/{expense.id}/approve",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "approved"
        assert data["journal_entry"] is not None

        je = data["journal_entry"]
        lines = je["lines"]
        assert len(lines) == 2

        debit_line = [l for l in lines if l["debit"] > 0][0]
        assert debit_line["account_code"] == "6300"
        assert debit_line["account_name"] == "Spese di trasferta"
        assert debit_line["debit"] == 22.50

        credit_line = [l for l in lines if l["credit"] > 0][0]
        assert credit_line["account_code"] == "2040"
        assert credit_line["account_name"] == "Debiti verso dipendenti"
        assert credit_line["credit"] == 22.50

    async def test_ac_301_cannot_approve_non_submitted(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant, verified_user: User,
    ):
        """AC-30.1: DATO spesa gia' approvata,
        QUANDO approve, ALLORA errore."""
        expense = Expense(
            tenant_id=tenant.id,
            user_id=verified_user.id,
            description="Spesa gia approvata",
            amount=10.0,
            currency="EUR",
            amount_eur=10.0,
            expense_date=date(2026, 3, 20),
            status="approved",
        )
        db_session.add(expense)
        await db_session.flush()

        resp = await client.patch(
            f"/api/v1/expenses/{expense.id}/approve",
            headers=auth_headers,
        )
        assert resp.status_code == 400


# ============================================================
# AC-30.2 — Rimborso -> DARE Debiti dipendenti / AVERE Banca
# ============================================================


class TestAC302Rimborso:
    """AC-30.2: Rimborso -> DARE Debiti dipendenti / AVERE Banca."""

    async def test_ac_302_reimburse_generates_journal_entry(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant, verified_user: User,
    ):
        """AC-30.2: DATO spesa approved,
        QUANDO reimburse, ALLORA journal entry DARE Debiti/AVERE Banca."""
        expense = Expense(
            tenant_id=tenant.id,
            user_id=verified_user.id,
            description="Taxi",
            amount=35.0,
            currency="EUR",
            amount_eur=35.0,
            expense_date=date(2026, 3, 20),
            status="approved",
        )
        db_session.add(expense)
        await db_session.flush()

        resp = await client.post(
            f"/api/v1/expenses/{expense.id}/reimburse",
            json={},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "reimbursed"
        assert data["journal_entry"] is not None

        je = data["journal_entry"]
        lines = je["lines"]
        debit_line = [l for l in lines if l["debit"] > 0][0]
        assert debit_line["account_code"] == "2040"  # Debiti verso dipendenti
        credit_line = [l for l in lines if l["credit"] > 0][0]
        assert credit_line["account_code"] == "1010"  # Banca c/c


# ============================================================
# AC-30.3 — Rifiuto con motivazione -> notifica dipendente
# ============================================================


class TestAC303Rifiuto:
    """AC-30.3: Rifiuto con motivazione -> notifica dipendente."""

    async def test_ac_303_reject_with_reason(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant, verified_user: User,
    ):
        """AC-30.3: DATO spesa submitted,
        QUANDO reject con motivazione,
        ALLORA stato rejected + reason salvata."""
        expense = Expense(
            tenant_id=tenant.id,
            user_id=verified_user.id,
            description="Spesa non conforme",
            amount=500.0,
            currency="EUR",
            amount_eur=500.0,
            expense_date=date(2026, 3, 20),
            status="submitted",
        )
        db_session.add(expense)
        await db_session.flush()

        resp = await client.patch(
            f"/api/v1/expenses/{expense.id}/reject",
            json={"reason": "Importo eccessivo, servono giustificativi aggiuntivi"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "rejected"
        assert data["rejection_reason"] == "Importo eccessivo, servono giustificativi aggiuntivi"


# ============================================================
# AC-30.4 — Rimborso PISP fallito -> stato "rimborso fallito"
# ============================================================


class TestAC304PISPFallito:
    """AC-30.4: Rimborso PISP fallito -> stato 'reimburse_failed'."""

    async def test_ac_304_pisp_failure(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant, verified_user: User,
    ):
        """AC-30.4: DATO spesa approved,
        QUANDO PISP fallisce,
        ALLORA stato reimburse_failed."""
        expense = Expense(
            tenant_id=tenant.id,
            user_id=verified_user.id,
            description="Spesa PISP fail",
            amount=100.0,
            currency="EUR",
            amount_eur=100.0,
            expense_date=date(2026, 3, 20),
            status="approved",
        )
        db_session.add(expense)
        await db_session.flush()

        # We test the service directly since the API doesn't expose simulate_failure
        from api.modules.expenses.service import ExpenseService
        service = ExpenseService(db_session)
        result = await service.reimburse_expense(
            expense_id=expense.id,
            tenant_id=tenant.id,
            simulate_failure=True,
        )
        assert result["status"] == "reimburse_failed"
        assert result["journal_entry"] is None
        assert "fallito" in result["message"].lower()


# ============================================================
# AC-30.5 — Auto-approvazione titolare unico (BR-10)
# ============================================================


class TestAC305AutoApprovazione:
    """AC-30.5: Auto-approvazione titolare unico (BR-10)."""

    async def test_ac_305_sole_owner_can_auto_approve(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant, verified_user: User,
    ):
        """AC-30.5: DATO titolare unico (1 owner nel tenant),
        QUANDO check_auto_approval,
        ALLORA True (puo' auto-approvare)."""
        from api.modules.expenses.service import ExpenseService
        service = ExpenseService(db_session)
        result = await service.check_auto_approval(tenant.id, verified_user.id)
        assert result is True

    async def test_ac_305_multiple_owners_no_auto_approve(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant, verified_user: User,
    ):
        """AC-30.5: DATO 2 owner nel tenant,
        QUANDO check_auto_approval,
        ALLORA False."""
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        second_owner = User(
            email="secondo.owner@example.com",
            password_hash=pwd_context.hash("Password1"),
            name="Secondo Owner",
            role="owner",
            email_verified=True,
            tenant_id=tenant.id,
        )
        db_session.add(second_owner)
        await db_session.flush()

        from api.modules.expenses.service import ExpenseService
        service = ExpenseService(db_session)
        result = await service.check_auto_approval(tenant.id, verified_user.id)
        assert result is False

    async def test_ac_305_sole_owner_approve_own_expense(
        self, client: AsyncClient, auth_headers: dict,
        db_session: AsyncSession, tenant: Tenant, verified_user: User,
    ):
        """AC-30.5: DATO titolare unico con spesa submitted,
        QUANDO approve propria spesa,
        ALLORA approvata (auto-approval)."""
        expense = Expense(
            tenant_id=tenant.id,
            user_id=verified_user.id,
            description="Auto-approvazione titolare",
            amount=15.0,
            currency="EUR",
            amount_eur=15.0,
            expense_date=date(2026, 3, 20),
            status="submitted",
        )
        db_session.add(expense)
        await db_session.flush()

        resp = await client.patch(
            f"/api/v1/expenses/{expense.id}/approve",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "approved"
        assert data["approved_by"] == str(verified_user.id)
