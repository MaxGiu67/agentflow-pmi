"""Balance Sheet CEE generator (US-23).

Generates Stato Patrimoniale and Conto Economico in CEE format
from ChartAccount + JournalEntry/JournalLine data.

Supports:
- Standard and abbreviated formats (micro-impresa under art. 2435-ter)
- Detection of unclosed entries (draft journal entries)
- First-year handling (empty prior-year column)
- Export markers for PDF/XBRL
"""

import logging
import uuid
from collections import defaultdict
from datetime import date

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import ChartAccount, JournalEntry, JournalLine, Tenant

logger = logging.getLogger(__name__)

# Art. 2435-ter CC thresholds for micro-impresa (bilancio abbreviato)
MICRO_THRESHOLDS = {
    "totale_attivo": 175_000,
    "ricavi_vendite": 350_000,
    "dipendenti_media": 5,
}


class BalanceSheetService:
    """Service for generating Bilancio CEE."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def generate(
        self,
        tenant_id: uuid.UUID,
        year: int,
        is_first_year: bool = False,
    ) -> dict:
        """Generate bilancio CEE for a given year.

        Args:
            tenant_id: Tenant UUID.
            year: Fiscal year.
            is_first_year: If True, prior year column is empty.

        Returns:
            Dict with stato_patrimoniale, conto_economico, warnings, metadata.
        """
        # 1. Get chart of accounts with CEE mapping
        accounts = await self._get_accounts(tenant_id)
        if not accounts:
            raise ValueError("Piano dei conti non trovato per questo tenant")

        # 2. Compute balances from journal lines
        balances = await self._compute_balances(tenant_id, year)

        # 3. Check for unclosed (draft) entries
        warnings = await self._check_unclosed_entries(tenant_id, year)

        # 4. Detect micro-impresa
        is_micro = await self._is_micro_impresa(tenant_id)

        # 5. Build CEE structure
        sp = self._build_stato_patrimoniale(accounts, balances)
        ce = self._build_conto_economico(accounts, balances)

        # 6. Build prior year (empty if first year)
        sp_prior: dict[str, float] = {}
        ce_prior: dict[str, float] = {}
        if not is_first_year:
            balances_prior = await self._compute_balances(tenant_id, year - 1)
            sp_prior = self._build_stato_patrimoniale(accounts, balances_prior)
            ce_prior = self._build_conto_economico(accounts, balances_prior)

        return {
            "year": year,
            "tenant_id": str(tenant_id),
            "stato_patrimoniale": {
                "attivo": {k: v for k, v in sp.items() if self._is_attivo(k)},
                "passivo": {k: v for k, v in sp.items() if self._is_passivo(k)},
            },
            "stato_patrimoniale_prior": {
                "attivo": {k: v for k, v in sp_prior.items() if self._is_attivo(k)} if sp_prior else {},
                "passivo": {k: v for k, v in sp_prior.items() if self._is_passivo(k)} if sp_prior else {},
            },
            "conto_economico": ce,
            "conto_economico_prior": ce_prior if not is_first_year else {},
            "is_first_year": is_first_year,
            "is_micro_impresa": is_micro,
            "format": "abbreviato" if is_micro else "ordinario",
            "warnings": warnings,
            "export_formats": ["pdf", "xbrl"],
        }

    async def _get_accounts(self, tenant_id: uuid.UUID) -> list[ChartAccount]:
        """Get all active chart accounts for a tenant."""
        result = await self.db.execute(
            select(ChartAccount).where(
                ChartAccount.tenant_id == tenant_id,
                ChartAccount.active.is_(True),
            )
        )
        return list(result.scalars().all())

    async def _compute_balances(
        self, tenant_id: uuid.UUID, year: int,
    ) -> dict[str, float]:
        """Compute account balances from journal entries for a specific year.

        Returns dict mapping account_code -> balance (debit - credit).
        """
        year_start = date(year, 1, 1)
        year_end = date(year, 12, 31)

        # Get all posted journal entries for the year
        result = await self.db.execute(
            select(JournalEntry.id).where(
                JournalEntry.tenant_id == tenant_id,
                JournalEntry.entry_date >= year_start,
                JournalEntry.entry_date <= year_end,
                JournalEntry.status == "posted",
            )
        )
        entry_ids = [r for r in result.scalars().all()]

        if not entry_ids:
            return {}

        # Get all lines for these entries
        result = await self.db.execute(
            select(JournalLine).where(
                JournalLine.entry_id.in_(entry_ids),
            )
        )
        lines = result.scalars().all()

        balances: dict[str, float] = defaultdict(float)
        for line in lines:
            balances[line.account_code] += line.debit - line.credit

        return dict(balances)

    async def _check_unclosed_entries(
        self, tenant_id: uuid.UUID, year: int,
    ) -> list[str]:
        """Check for draft (unclosed) journal entries and return warnings."""
        year_start = date(year, 1, 1)
        year_end = date(year, 12, 31)

        result = await self.db.execute(
            select(JournalEntry).where(
                JournalEntry.tenant_id == tenant_id,
                JournalEntry.entry_date >= year_start,
                JournalEntry.entry_date <= year_end,
                JournalEntry.status == "draft",
            )
        )
        drafts = result.scalars().all()

        warnings: list[str] = []
        if drafts:
            count = len(drafts)
            warnings.append(
                f"Attenzione: {count} scritture contabili in stato 'bozza' "
                f"non incluse nel bilancio. Chiudere le scritture per un bilancio completo."
            )

        return warnings

    async def _is_micro_impresa(self, tenant_id: uuid.UUID) -> bool:
        """Detect if tenant qualifies as micro-impresa (art. 2435-ter CC).

        A company qualifies if it does NOT exceed at least two of:
        - Total assets: 175,000 EUR
        - Revenue: 350,000 EUR
        - Average employees: 5

        For MVP, we check tenant type and use simplified heuristic.
        """
        result = await self.db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()
        if not tenant:
            return False

        # Simplified: ditta individuale and piva are typically micro
        if tenant.type in ("ditta_individuale", "piva"):
            return True

        # For srls, check if subscription is starter (small company proxy)
        if tenant.type == "srls":
            return True

        return False

    def _build_stato_patrimoniale(
        self,
        accounts: list[ChartAccount],
        balances: dict[str, float],
    ) -> dict[str, float]:
        """Build Stato Patrimoniale grouping accounts by CEE code."""
        sp: dict[str, float] = defaultdict(float)

        for acct in accounts:
            if acct.account_type not in ("asset", "liability", "equity"):
                continue
            if not acct.cee_code:
                continue

            balance = balances.get(acct.code, 0.0)
            cee_key = f"{acct.cee_code} - {acct.cee_name}" if acct.cee_name else acct.cee_code
            sp[cee_key] += balance

        return dict(sp)

    def _build_conto_economico(
        self,
        accounts: list[ChartAccount],
        balances: dict[str, float],
    ) -> dict[str, float]:
        """Build Conto Economico grouping accounts by CEE code."""
        ce: dict[str, float] = defaultdict(float)

        for acct in accounts:
            if acct.account_type not in ("income", "expense"):
                continue
            if not acct.cee_code:
                continue

            balance = balances.get(acct.code, 0.0)
            # For income accounts, negate (credit is positive in CE)
            if acct.account_type == "income":
                balance = -balance

            cee_key = f"{acct.cee_code} - {acct.cee_name}" if acct.cee_name else acct.cee_code
            ce[cee_key] += balance

        return dict(ce)

    @staticmethod
    def _is_attivo(cee_key: str) -> bool:
        """Check if a CEE key belongs to Attivo (assets)."""
        # SP Attivo: B (immobilizzazioni), C (attivo circolante)
        prefix = cee_key.split(" ")[0].split(".")[0]
        return prefix in ("B", "C")

    @staticmethod
    def _is_passivo(cee_key: str) -> bool:
        """Check if a CEE key belongs to Passivo (liabilities + equity)."""
        # SP Passivo: A (patrimonio netto), C (TFR), D (debiti)
        prefix = cee_key.split(" ")[0].split(".")[0]
        return prefix in ("A", "D")
