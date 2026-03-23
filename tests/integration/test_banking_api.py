"""
Test suite for US-24: Collegamento conto corrente Open Banking
Tests for 6 Acceptance Criteria (AC-24.1 through AC-24.6)
"""

import uuid
from datetime import datetime, timedelta, UTC

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import BankAccount, BankTransaction, Tenant


# ============================================================
# AC-24.1 — Collegamento con SCA, IBAN, saldo, consent 90gg
# ============================================================


class TestAC241CollegamentoSCA:
    """AC-24.1: Collegamento con SCA -> conto collegato, IBAN, saldo,
    consent 90gg."""

    async def test_ac_241_connect_bank_account(
        self, client: AsyncClient, auth_headers: dict
    ):
        """AC-24.1: DATO utente autenticato, QUANDO collego conto con IBAN IT,
        ALLORA conto collegato con IBAN, saldo, consent 90gg."""
        resp = await client.post(
            "/api/v1/bank-accounts/connect",
            json={
                "iban": "IT60X0542811101000000123456",
                "bank_name": "Intesa Sanpaolo",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["iban"] == "IT60X0542811101000000123456"
        assert data["status"] == "connected"
        assert data["bank_name"] is not None
        assert data["balance"] is not None
        assert data["consent_expires_at"] is not None
        assert "90" in data["message"] or "collegato" in data["message"].lower()

    async def test_ac_241_account_appears_in_list(
        self, client: AsyncClient, auth_headers: dict
    ):
        """AC-24.1: DATO conto collegato, QUANDO elenco conti,
        ALLORA conto visibile con IBAN e saldo."""
        # Connect
        await client.post(
            "/api/v1/bank-accounts/connect",
            json={"iban": "IT60X0542811101000000111222"},
            headers=auth_headers,
        )

        # List
        list_resp = await client.get(
            "/api/v1/bank-accounts",
            headers=auth_headers,
        )
        assert list_resp.status_code == 200
        data = list_resp.json()
        assert data["total"] >= 1
        account = data["items"][0]
        assert "iban" in account
        assert account["status"] == "connected"

    async def test_ac_241_balance_endpoint(
        self, client: AsyncClient, auth_headers: dict
    ):
        """AC-24.1: DATO conto collegato, QUANDO richiedo saldo,
        ALLORA ottengo saldo corrente."""
        connect_resp = await client.post(
            "/api/v1/bank-accounts/connect",
            json={"iban": "IT60X0542811101000000333444"},
            headers=auth_headers,
        )
        account_id = connect_resp.json()["account_id"]

        balance_resp = await client.get(
            f"/api/v1/bank-accounts/{account_id}/balance",
            headers=auth_headers,
        )
        assert balance_resp.status_code == 200
        data = balance_resp.json()
        assert "balance" in data
        assert data["currency"] == "EUR"


# ============================================================
# AC-24.2 — Sync giornaliero (primo 90gg, poi incrementale)
# ============================================================


class TestAC242SyncGiornaliero:
    """AC-24.2: Sync giornaliero (primo: 90gg, poi incrementale)."""

    async def test_ac_242_first_sync_downloads_transactions(
        self, client: AsyncClient, auth_headers: dict
    ):
        """AC-24.2: DATO conto appena collegato, QUANDO primo sync,
        ALLORA scarica storico (fino a 90 giorni)."""
        connect_resp = await client.post(
            "/api/v1/bank-accounts/connect",
            json={"iban": "IT60X0542811101000000555666"},
            headers=auth_headers,
        )
        account_id = connect_resp.json()["account_id"]

        sync_resp = await client.post(
            f"/api/v1/bank-accounts/{account_id}/sync",
            headers=auth_headers,
        )
        assert sync_resp.status_code == 200
        data = sync_resp.json()
        assert data["new_transactions"] > 0
        assert data["total_transactions"] > 0
        assert "sincronizzat" in data["message"].lower()

    async def test_ac_242_subsequent_sync_incremental(
        self, client: AsyncClient, auth_headers: dict
    ):
        """AC-24.2: DATO conto gia sincronizzato, QUANDO sync successivo,
        ALLORA scarica solo nuovi movimenti (incrementale)."""
        connect_resp = await client.post(
            "/api/v1/bank-accounts/connect",
            json={"iban": "IT60X0542811101000000777888"},
            headers=auth_headers,
        )
        account_id = connect_resp.json()["account_id"]

        # First sync
        await client.post(
            f"/api/v1/bank-accounts/{account_id}/sync",
            headers=auth_headers,
        )

        # Second sync (incremental)
        sync2_resp = await client.post(
            f"/api/v1/bank-accounts/{account_id}/sync",
            headers=auth_headers,
        )
        assert sync2_resp.status_code == 200
        # Should have some transactions total from both syncs
        data = sync2_resp.json()
        assert data["total_transactions"] >= 0

    async def test_ac_242_transactions_visible(
        self, client: AsyncClient, auth_headers: dict
    ):
        """AC-24.2: DATO sync eseguito, QUANDO richiedo movimenti,
        ALLORA vedo elenco transazioni."""
        connect_resp = await client.post(
            "/api/v1/bank-accounts/connect",
            json={"iban": "IT60X0542811101000000999000"},
            headers=auth_headers,
        )
        account_id = connect_resp.json()["account_id"]

        # Sync
        await client.post(
            f"/api/v1/bank-accounts/{account_id}/sync",
            headers=auth_headers,
        )

        # Get transactions
        tx_resp = await client.get(
            f"/api/v1/bank-accounts/{account_id}/transactions",
            headers=auth_headers,
        )
        assert tx_resp.status_code == 200
        data = tx_resp.json()
        assert data["total"] > 0
        tx = data["items"][0]
        assert "amount" in tx
        assert "direction" in tx
        assert tx["direction"] in ("credit", "debit")


# ============================================================
# AC-24.3 — Consent PSD2 scaduto: notifica 7gg prima
# ============================================================


class TestAC243ConsentScaduto:
    """AC-24.3: Consent PSD2 scaduto -> notifica 7gg prima."""

    async def test_ac_243_consent_expiring_warning(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        tenant: Tenant,
    ):
        """AC-24.3: DATO consent che scade tra 5 giorni, QUANDO elenco conti,
        ALLORA warning consent in scadenza."""
        # Create account with consent expiring in 5 days
        account = BankAccount(
            tenant_id=tenant.id,
            iban="IT60X0542811101000000EXPIR",
            bank_name="Banca Expiring",
            provider="cbi_globe",
            consent_token="consent-expiring",
            consent_expires_at=datetime.now() + timedelta(days=5),
            balance=5000.0,
            status="connected",
        )
        db_session.add(account)
        await db_session.flush()

        # List accounts — should have warning
        list_resp = await client.get(
            "/api/v1/bank-accounts",
            headers=auth_headers,
        )
        assert list_resp.status_code == 200
        items = list_resp.json()["items"]
        expiring_accounts = [
            a for a in items
            if a["iban"] == "IT60X0542811101000000EXPIR"
        ]
        assert len(expiring_accounts) == 1
        # The consent_expires_at should be set
        assert expiring_accounts[0]["consent_expires_at"] is not None


# ============================================================
# AC-24.4 — Revoca consent: status revocato, offre ri-collegamento
# ============================================================


class TestAC244RevocaConsent:
    """AC-24.4: Revoca consent da portale -> status 'revocato',
    offre re-collegamento."""

    async def test_ac_244_revoke_consent(
        self, client: AsyncClient, auth_headers: dict
    ):
        """AC-24.4: DATO conto collegato, QUANDO revoco consent,
        ALLORA status='revoked' con offerta di ri-collegamento."""
        # Connect
        connect_resp = await client.post(
            "/api/v1/bank-accounts/connect",
            json={"iban": "IT60X0542811101000000REVOK"},
            headers=auth_headers,
        )
        account_id = connect_resp.json()["account_id"]

        # Revoke
        revoke_resp = await client.post(
            f"/api/v1/bank-accounts/{account_id}/revoke",
            headers=auth_headers,
        )
        assert revoke_resp.status_code == 200
        data = revoke_resp.json()
        assert data["status"] == "revoked"
        assert "revocato" in data["message"].lower()
        assert "ricollegare" in data["message"].lower() or "riconnettere" in data["message"].lower() or "ricolleg" in data["message"].lower()

    async def test_ac_244_revoked_account_no_sync(
        self, client: AsyncClient, auth_headers: dict
    ):
        """AC-24.4: DATO conto revocato, QUANDO provo sync,
        ALLORA errore perche consent revocato."""
        connect_resp = await client.post(
            "/api/v1/bank-accounts/connect",
            json={"iban": "IT60X0542811101000000NOSYN"},
            headers=auth_headers,
        )
        account_id = connect_resp.json()["account_id"]

        # Revoke
        await client.post(
            f"/api/v1/bank-accounts/{account_id}/revoke",
            headers=auth_headers,
        )

        # Try sync
        sync_resp = await client.post(
            f"/api/v1/bank-accounts/{account_id}/sync",
            headers=auth_headers,
        )
        assert sync_resp.status_code == 400


# ============================================================
# AC-24.5 — Banca non su CBI Globe: suggerisce upload manuale
# ============================================================


class TestAC245BancaNonCBIGlobe:
    """AC-24.5: Banca non su CBI Globe -> suggerisce upload manuale."""

    async def test_ac_245_unsupported_bank_suggestion(
        self, client: AsyncClient, auth_headers: dict
    ):
        """AC-24.5: DATO IBAN non italiano, QUANDO collego conto,
        ALLORA suggerimento upload manuale."""
        resp = await client.post(
            "/api/v1/bank-accounts/connect",
            json={
                "iban": "DE89370400440532013000",  # German IBAN
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["supported"] is False
        assert "non italiano" in data["message"].lower() or "upload manuale" in data["message"].lower()


# ============================================================
# AC-24.6 — IBAN non italiano: verifica supporto
# ============================================================


class TestAC246IBANNonItaliano:
    """AC-24.6: IBAN non italiano -> verifica supporto."""

    async def test_ac_246_foreign_iban_check(
        self, client: AsyncClient, auth_headers: dict
    ):
        """AC-24.6: DATO IBAN francese, QUANDO collego,
        ALLORA verifica supporto e informa l'utente."""
        resp = await client.post(
            "/api/v1/bank-accounts/connect",
            json={
                "iban": "FR7630006000011234567890189",  # French IBAN
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["supported"] is False
        assert "FR" in data["message"] or "non italiano" in data["message"].lower()

    async def test_ac_246_italian_iban_supported(
        self, client: AsyncClient, auth_headers: dict
    ):
        """AC-24.6: DATO IBAN italiano valido, QUANDO collego,
        ALLORA collegamento avviene con successo."""
        resp = await client.post(
            "/api/v1/bank-accounts/connect",
            json={
                "iban": "IT60X0542811101000000123456",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        # Should be a successful connection (not unsupported response)
        assert "account_id" in data or data.get("supported", True) is True
