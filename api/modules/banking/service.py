"""Service layer for banking / Open Banking (US-24)."""

import logging
import uuid
from datetime import date, datetime, timedelta, UTC

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.adapters.banking import MockBankingAdapter
from api.db.models import BankAccount, BankTransaction

logger = logging.getLogger(__name__)


class BankingService:
    """Business logic for bank account connection, sync, and management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.adapter = MockBankingAdapter()

    async def connect_account(
        self,
        tenant_id: uuid.UUID,
        iban: str,
        bank_name: str | None = None,
    ) -> dict:
        """Initiate SCA flow to connect a bank account.

        Returns connection result with redirect URL and consent info.
        """
        # Check if IBAN is for an Italian bank (supported)
        is_italian = iban.upper().startswith("IT")

        # Check CBI Globe support
        if not self.adapter.is_bank_supported(iban):
            if not is_italian:
                return {
                    "supported": False,
                    "iban": iban,
                    "message": (
                        f"IBAN {iban[:2]} non italiano. "
                        "Verificare supporto Open Banking per il paese di origine."
                    ),
                }
            return {
                "supported": False,
                "iban": iban,
                "message": (
                    "Banca non disponibile su CBI Globe. "
                    "Suggerimento: utilizzare l'upload manuale dei movimenti bancari."
                ),
            }

        # Init SCA flow
        sca_result = await self.adapter.init_sca_flow(iban)

        # Create bank account record
        account = BankAccount(
            tenant_id=tenant_id,
            iban=iban,
            bank_name=bank_name or sca_result.bank_name,
            provider="cbi_globe",
            consent_token=sca_result.consent_token,
            consent_expires_at=sca_result.consent_expires_at,
            status="connected",
        )
        self.db.add(account)
        await self.db.flush()

        # Get initial balance
        account_info = await self.adapter.get_account_info(sca_result.consent_token, iban)
        account.balance = account_info.balance
        await self.db.flush()

        logger.info("Connected bank account %s for tenant %s", iban, tenant_id)

        return {
            "account_id": str(account.id),
            "iban": iban,
            "bank_name": account.bank_name,
            "status": "connected",
            "balance": account.balance,
            "consent_expires_at": sca_result.consent_expires_at.isoformat(),
            "redirect_url": sca_result.redirect_url,
            "message": f"Conto {iban} collegato con successo. Consent valido 90 giorni.",
        }

    async def list_accounts(self, tenant_id: uuid.UUID) -> list[dict]:
        """List all connected bank accounts."""
        result = await self.db.execute(
            select(BankAccount)
            .where(BankAccount.tenant_id == tenant_id)
            .order_by(BankAccount.created_at.desc())
        )
        accounts = result.scalars().all()

        items = []
        for acct in accounts:
            # Check consent expiry warning
            d = self._to_dict(acct)
            if acct.consent_expires_at and acct.status == "connected":
                days_left = (acct.consent_expires_at.replace(tzinfo=None) - datetime.now()).days
                if days_left <= 7:
                    d["consent_warning"] = (
                        f"Consent PSD2 in scadenza tra {max(days_left, 0)} giorni. "
                        "Rinnovare il collegamento."
                    )
            items.append(d)
        return items

    async def get_balance(self, account_id: uuid.UUID, tenant_id: uuid.UUID) -> dict:
        """Get account balance."""
        account = await self._get_account(account_id, tenant_id)
        if not account:
            raise ValueError("Conto non trovato")

        return {
            "account_id": str(account.id),
            "iban": account.iban,
            "balance": account.balance or 0.0,
            "currency": "EUR",
            "last_sync_at": account.last_sync_at.isoformat() if account.last_sync_at else None,
        }

    async def get_transactions(
        self,
        account_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> list[dict]:
        """Get transactions for a bank account."""
        account = await self._get_account(account_id, tenant_id)
        if not account:
            raise ValueError("Conto non trovato")

        result = await self.db.execute(
            select(BankTransaction)
            .where(BankTransaction.bank_account_id == account_id)
            .order_by(BankTransaction.date.desc())
        )
        transactions = result.scalars().all()

        return [
            {
                "id": str(tx.id),
                "bank_account_id": str(tx.bank_account_id),
                "transaction_id": tx.transaction_id,
                "date": tx.date.isoformat(),
                "amount": tx.amount,
                "direction": tx.direction,
                "counterpart": tx.counterpart,
                "description": tx.description,
                "reconciled": tx.reconciled,
            }
            for tx in transactions
        ]

    async def sync_transactions(
        self,
        account_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> dict:
        """Sync transactions from bank.

        First sync: last 90 days. Subsequent: incremental from last_sync_at.
        """
        account = await self._get_account(account_id, tenant_id)
        if not account:
            raise ValueError("Conto non trovato")

        if account.status != "connected":
            raise ValueError(f"Conto in stato '{account.status}', sync non disponibile")

        # Determine from_date (first sync: 90 days, then incremental)
        if account.last_sync_at:
            from_date = account.last_sync_at.date()
        else:
            from_date = date.today() - timedelta(days=90)

        # Get transactions from adapter
        new_transactions = await self.adapter.get_transactions(
            consent_token=account.consent_token or "",
            iban=account.iban,
            from_date=from_date,
        )

        # Deduplicate and insert
        new_count = 0
        for tx in new_transactions:
            # Check if already exists
            existing = await self.db.execute(
                select(BankTransaction).where(
                    BankTransaction.bank_account_id == account_id,
                    BankTransaction.transaction_id == tx.transaction_id,
                )
            )
            if existing.scalar_one_or_none() is None:
                bt = BankTransaction(
                    bank_account_id=account_id,
                    transaction_id=tx.transaction_id,
                    date=tx.date,
                    amount=tx.amount,
                    direction=tx.direction,
                    counterpart=tx.counterpart,
                    description=tx.description,
                )
                self.db.add(bt)
                new_count += 1

        # Update account
        account.last_sync_at = datetime.now(UTC).replace(tzinfo=None)

        # Refresh balance
        account_info = await self.adapter.get_account_info(
            account.consent_token or "", account.iban,
        )
        account.balance = account_info.balance

        await self.db.flush()

        # Count total transactions
        total_result = await self.db.execute(
            select(BankTransaction)
            .where(BankTransaction.bank_account_id == account_id)
        )
        total = len(total_result.scalars().all())

        return {
            "account_id": str(account_id),
            "new_transactions": new_count,
            "total_transactions": total,
            "message": f"Sincronizzati {new_count} nuovi movimenti. Totale: {total}.",
        }

    async def revoke_consent(
        self, account_id: uuid.UUID, tenant_id: uuid.UUID,
    ) -> dict:
        """Revoke PSD2 consent for a bank account."""
        account = await self._get_account(account_id, tenant_id)
        if not account:
            raise ValueError("Conto non trovato")

        await self.adapter.revoke_consent(account.consent_token or "")
        account.status = "revoked"
        account.consent_token = None
        await self.db.flush()

        return {
            "account_id": str(account.id),
            "status": "revoked",
            "message": (
                "Consent PSD2 revocato. Il conto non sara piu sincronizzato. "
                "Puoi ricollegare il conto in qualsiasi momento."
            ),
        }

    async def check_consent_expiry(self, tenant_id: uuid.UUID) -> list[dict]:
        """Check for accounts with consent expiring within 7 days."""
        threshold = datetime.now(UTC).replace(tzinfo=None) + timedelta(days=7)
        result = await self.db.execute(
            select(BankAccount).where(
                BankAccount.tenant_id == tenant_id,
                BankAccount.status == "connected",
                BankAccount.consent_expires_at <= threshold,
            )
        )
        expiring = result.scalars().all()
        return [
            {
                "account_id": str(acct.id),
                "iban": acct.iban,
                "bank_name": acct.bank_name,
                "consent_expires_at": acct.consent_expires_at.isoformat() if acct.consent_expires_at else None,
                "days_remaining": max(
                    (acct.consent_expires_at.replace(tzinfo=None) - datetime.now()).days, 0
                ) if acct.consent_expires_at else 0,
                "message": "Consent PSD2 in scadenza. Rinnovare per mantenere la sincronizzazione.",
            }
            for acct in expiring
        ]

    async def _get_account(
        self, account_id: uuid.UUID, tenant_id: uuid.UUID,
    ) -> BankAccount | None:
        """Get bank account by ID and tenant."""
        result = await self.db.execute(
            select(BankAccount).where(
                BankAccount.id == account_id,
                BankAccount.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    def _to_dict(self, account: BankAccount) -> dict:
        """Convert BankAccount to dict."""
        return {
            "id": str(account.id),
            "tenant_id": str(account.tenant_id),
            "iban": account.iban,
            "bank_name": account.bank_name,
            "provider": account.provider,
            "balance": account.balance,
            "status": account.status,
            "consent_expires_at": account.consent_expires_at.isoformat() if account.consent_expires_at else None,
            "last_sync_at": account.last_sync_at.isoformat() if account.last_sync_at else None,
            "created_at": account.created_at.isoformat() if account.created_at else None,
        }
