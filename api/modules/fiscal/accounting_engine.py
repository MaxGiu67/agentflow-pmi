"""AccountingEngine — internal chart-of-accounts engine replacing Odoo CE 18.

ADR-007: stores piano dei conti directly in the DB (ChartAccount table)
instead of calling Odoo XML-RPC.  Each account now carries CEE mapping
(cee_code / cee_name) for bilancio CEE compliance.
"""

import logging
from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import ChartAccount, FiscalRule

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Templates with CEE mapping
# ---------------------------------------------------------------------------

PIANO_CONTI_SRL_ORDINARIO = [
    {"code": "1010", "name": "Cassa", "account_type": "asset", "cee_code": "C.IV.3", "cee_name": "Disponibilita liquide - Denaro in cassa"},
    {"code": "1020", "name": "Banca c/c", "account_type": "asset", "cee_code": "C.IV.1", "cee_name": "Disponibilita liquide - Depositi bancari"},
    {"code": "1110", "name": "Crediti verso clienti", "account_type": "asset", "cee_code": "C.II.1", "cee_name": "Crediti - Verso clienti"},
    {"code": "1120", "name": "Crediti IVA", "account_type": "asset", "cee_code": "C.II.5-bis", "cee_name": "Crediti tributari"},
    {"code": "1210", "name": "Immobilizzazioni materiali", "account_type": "asset", "cee_code": "B.II", "cee_name": "Immobilizzazioni materiali"},
    {"code": "1220", "name": "Fondo ammortamento immob. materiali", "account_type": "asset", "cee_code": "B.II", "cee_name": "Immobilizzazioni materiali"},
    {"code": "1310", "name": "Immobilizzazioni immateriali", "account_type": "asset", "cee_code": "B.I", "cee_name": "Immobilizzazioni immateriali"},
    {"code": "2010", "name": "Debiti verso fornitori", "account_type": "liability", "cee_code": "D.7", "cee_name": "Debiti verso fornitori"},
    {"code": "2020", "name": "Debiti tributari", "account_type": "liability", "cee_code": "D.12", "cee_name": "Debiti tributari"},
    {"code": "2030", "name": "Debiti vs istituti previdenziali", "account_type": "liability", "cee_code": "D.13", "cee_name": "Debiti verso istituti previdenziali"},
    {"code": "2040", "name": "TFR", "account_type": "liability", "cee_code": "C", "cee_name": "Trattamento di fine rapporto"},
    {"code": "2110", "name": "IVA a debito", "account_type": "liability", "cee_code": "D.12", "cee_name": "Debiti tributari"},
    {"code": "2120", "name": "Ritenute da versare", "account_type": "liability", "cee_code": "D.12", "cee_name": "Debiti tributari"},
    {"code": "2212", "name": "IVA a credito", "account_type": "asset", "cee_code": "C.II.5-bis", "cee_name": "Crediti tributari"},
    {"code": "3010", "name": "Capitale sociale", "account_type": "equity", "cee_code": "A.I", "cee_name": "Capitale"},
    {"code": "3020", "name": "Riserva legale", "account_type": "equity", "cee_code": "A.IV", "cee_name": "Riserva legale"},
    {"code": "3030", "name": "Utile/perdita d'esercizio", "account_type": "equity", "cee_code": "A.IX", "cee_name": "Utile (perdita) d'esercizio"},
    {"code": "4010", "name": "Ricavi da vendite", "account_type": "income", "cee_code": "A.1", "cee_name": "Ricavi delle vendite"},
    {"code": "4020", "name": "Ricavi da prestazioni di servizi", "account_type": "income", "cee_code": "A.1", "cee_name": "Ricavi delle vendite"},
    {"code": "4030", "name": "Altri ricavi", "account_type": "income", "cee_code": "A.5", "cee_name": "Altri ricavi e proventi"},
    {"code": "5010", "name": "Acquisti materie prime", "account_type": "expense", "cee_code": "B.6", "cee_name": "Costi materie prime"},
    {"code": "5020", "name": "Servizi", "account_type": "expense", "cee_code": "B.7", "cee_name": "Costi per servizi"},
    {"code": "5030", "name": "Godimento beni di terzi", "account_type": "expense", "cee_code": "B.8", "cee_name": "Godimento beni di terzi"},
    {"code": "5040", "name": "Costi del personale", "account_type": "expense", "cee_code": "B.9", "cee_name": "Costi del personale"},
    {"code": "5050", "name": "Ammortamenti", "account_type": "expense", "cee_code": "B.10", "cee_name": "Ammortamenti e svalutazioni"},
    {"code": "5060", "name": "Oneri diversi di gestione", "account_type": "expense", "cee_code": "B.14", "cee_name": "Oneri diversi di gestione"},
    {"code": "6010", "name": "Interessi attivi", "account_type": "income", "cee_code": "C.16", "cee_name": "Proventi finanziari"},
    {"code": "6020", "name": "Interessi passivi", "account_type": "expense", "cee_code": "C.17", "cee_name": "Oneri finanziari"},
    {"code": "6110", "name": "Consulenze", "account_type": "expense", "cee_code": "B.7", "cee_name": "Costi per servizi"},
    {"code": "6120", "name": "Utenze", "account_type": "expense", "cee_code": "B.7", "cee_name": "Costi per servizi"},
]

PIANO_CONTI_FORFETTARIO = [
    {"code": "1010", "name": "Cassa", "account_type": "asset", "cee_code": None, "cee_name": None},
    {"code": "1020", "name": "Banca c/c", "account_type": "asset", "cee_code": None, "cee_name": None},
    {"code": "1110", "name": "Crediti verso clienti", "account_type": "asset", "cee_code": None, "cee_name": None},
    {"code": "2010", "name": "Debiti verso fornitori", "account_type": "liability", "cee_code": None, "cee_name": None},
    {"code": "3010", "name": "Patrimonio netto", "account_type": "equity", "cee_code": None, "cee_name": None},
    {"code": "4010", "name": "Ricavi (compensi)", "account_type": "income", "cee_code": None, "cee_name": None},
    {"code": "5010", "name": "Costi deducibili", "account_type": "expense", "cee_code": None, "cee_name": None},
    {"code": "5020", "name": "Contributi previdenziali", "account_type": "expense", "cee_code": None, "cee_name": None},
    {"code": "5030", "name": "Imposta sostitutiva", "account_type": "expense", "cee_code": None, "cee_name": None},
]

PIANO_CONTI_GENERICO = [
    {"code": "1010", "name": "Cassa", "account_type": "asset", "cee_code": "C.IV.3", "cee_name": "Disponibilita liquide - Denaro in cassa"},
    {"code": "1020", "name": "Banca c/c", "account_type": "asset", "cee_code": "C.IV.1", "cee_name": "Disponibilita liquide - Depositi bancari"},
    {"code": "1110", "name": "Crediti verso clienti", "account_type": "asset", "cee_code": "C.II.1", "cee_name": "Crediti - Verso clienti"},
    {"code": "1210", "name": "Immobilizzazioni", "account_type": "asset", "cee_code": "B.II", "cee_name": "Immobilizzazioni materiali"},
    {"code": "2010", "name": "Debiti verso fornitori", "account_type": "liability", "cee_code": "D.7", "cee_name": "Debiti verso fornitori"},
    {"code": "2020", "name": "Debiti tributari", "account_type": "liability", "cee_code": "D.12", "cee_name": "Debiti tributari"},
    {"code": "2110", "name": "IVA a debito", "account_type": "liability", "cee_code": "D.12", "cee_name": "Debiti tributari"},
    {"code": "3010", "name": "Capitale", "account_type": "equity", "cee_code": "A.I", "cee_name": "Capitale"},
    {"code": "4010", "name": "Ricavi", "account_type": "income", "cee_code": "A.1", "cee_name": "Ricavi delle vendite"},
    {"code": "5010", "name": "Costi", "account_type": "expense", "cee_code": "B.6", "cee_name": "Costi materie prime"},
    {"code": "5020", "name": "Servizi", "account_type": "expense", "cee_code": "B.7", "cee_name": "Costi per servizi"},
    {"code": "5030", "name": "Ammortamenti", "account_type": "expense", "cee_code": "B.10", "cee_name": "Ammortamenti e svalutazioni"},
]


class AccountingEngine:
    """Internal accounting engine — replaces Odoo CE 18 (ADR-007).

    Stores chart of accounts in ChartAccount table.
    Reads fiscal rules from FiscalRule table.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Piano dei conti
    # ------------------------------------------------------------------

    async def create_piano_conti(
        self,
        tenant_id: str,
        tipo_azienda: str,
        regime_fiscale: str,
        force: bool = False,
    ) -> dict:
        """Create chart of accounts in ChartAccount table.

        Returns the same dict shape the old OdooClient used to return so
        that callers (AccountingService) don't need restructuring.
        """
        import uuid as _uuid

        tid = _uuid.UUID(str(tenant_id)) if not isinstance(tenant_id, _uuid.UUID) else tenant_id

        # If force, delete existing accounts for this tenant
        if force:
            await self.db.execute(
                delete(ChartAccount).where(ChartAccount.tenant_id == tid)
            )

        # Select template based on tipo / regime
        if regime_fiscale == "forfettario":
            template = PIANO_CONTI_FORFETTARIO
            tax_codes: list[str] = []
            journals = ["Vendite", "Acquisti", "Banca"]
        elif tipo_azienda in ("srl", "srls"):
            template = PIANO_CONTI_SRL_ORDINARIO
            tax_codes = ["4%", "10%", "22%"]
            journals = ["Vendite", "Acquisti", "Banca", "Cassa", "Vari"]
        elif tipo_azienda == "altro":
            template = PIANO_CONTI_GENERICO
            tax_codes = ["4%", "10%", "22%"]
            journals = ["Vendite", "Acquisti", "Banca", "Vari"]
        else:
            # piva, ditta_individuale with non-forfettario
            template = PIANO_CONTI_SRL_ORDINARIO
            tax_codes = ["4%", "10%", "22%"]
            journals = ["Vendite", "Acquisti", "Banca", "Vari"]

        # Insert ChartAccount rows
        created_accounts: list[dict] = []
        for acct in template:
            row = ChartAccount(
                tenant_id=tid,
                code=acct["code"],
                name=acct["name"],
                account_type=acct["account_type"],
                cee_code=acct.get("cee_code"),
                cee_name=acct.get("cee_name"),
            )
            self.db.add(row)
            created_accounts.append({
                "code": acct["code"],
                "name": acct["name"],
                "account_type": acct["account_type"],
            })

        await self.db.flush()

        logger.info(
            "Created piano conti for tenant %s (%s/%s): %d accounts",
            tid, tipo_azienda, regime_fiscale, len(created_accounts),
        )

        return {
            "accounts": created_accounts,
            "journals": journals,
            "tax_codes": tax_codes,
        }

    async def get_piano_conti(self, tenant_id: str) -> dict | None:
        """Read chart of accounts from ChartAccount table."""
        import uuid as _uuid

        tid = _uuid.UUID(str(tenant_id)) if not isinstance(tenant_id, _uuid.UUID) else tenant_id

        result = await self.db.execute(
            select(ChartAccount).where(
                ChartAccount.tenant_id == tid,
                ChartAccount.active.is_(True),
            )
        )
        rows = result.scalars().all()
        if not rows:
            return None

        return {
            "accounts": [
                {"code": r.code, "name": r.name, "account_type": r.account_type}
                for r in rows
            ],
        }

    # ------------------------------------------------------------------
    # Fiscal rules
    # ------------------------------------------------------------------

    async def get_fiscal_rule(
        self, key: str, as_of_date: date | None = None,
    ) -> str | None:
        """Read a fiscal rule value, optionally as of a specific date."""
        ref_date = as_of_date or date.today()
        stmt = (
            select(FiscalRule)
            .where(
                FiscalRule.key == key,
                FiscalRule.valid_from <= ref_date,
            )
            .order_by(FiscalRule.valid_from.desc())
        )
        result = await self.db.execute(stmt)
        for rule in result.scalars():
            if rule.valid_to is None or rule.valid_to >= ref_date:
                return rule.value
        return None

    async def list_fiscal_rules(self, key_pattern: str | None = None) -> list[dict]:
        """List all fiscal rules, optionally filtered by key pattern."""
        stmt = select(FiscalRule).order_by(FiscalRule.key, FiscalRule.valid_from)
        if key_pattern:
            stmt = stmt.where(FiscalRule.key.contains(key_pattern))

        result = await self.db.execute(stmt)
        rules = result.scalars().all()
        return [
            {
                "id": str(r.id),
                "key": r.key,
                "value": r.value,
                "value_type": r.value_type,
                "valid_from": r.valid_from.isoformat(),
                "valid_to": r.valid_to.isoformat() if r.valid_to else None,
                "law_reference": r.law_reference,
                "description": r.description,
            }
            for r in rules
        ]
