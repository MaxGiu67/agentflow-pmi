import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import Tenant, User
from api.modules.fiscal.accounting_engine import AccountingEngine

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAYS = [5, 15, 60]  # seconds


class AccountingService:
    def __init__(self, db: AsyncSession, engine: AccountingEngine | None = None) -> None:
        self.db = db
        self.engine = engine or AccountingEngine(db)

    async def _get_tenant(self, user: User) -> Tenant:
        if not user.tenant_id:
            raise ValueError("Profilo azienda non configurato. Completa il profilo prima.")

        result = await self.db.execute(
            select(Tenant).where(Tenant.id == user.tenant_id)
        )
        tenant = result.scalar_one_or_none()
        if not tenant:
            raise ValueError("Tenant non trovato")
        return tenant

    async def create_piano_conti(self, user: User, force: bool = False) -> dict:
        """Create chart of accounts for the user's tenant via AccountingEngine."""
        tenant = await self._get_tenant(user)

        if tenant.odoo_db_name and not force:
            raise ValueError("Piano dei conti gia esistente. Usa force=true per ricrearlo.")

        # Create or reuse DB name (kept as flag for backward compat)
        db_name = tenant.odoo_db_name or f"contabot_{tenant.id.hex[:12]}"

        # Try with retries (AC-12.3)
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                result = await self.engine.create_piano_conti(
                    tenant_id=tenant.id,
                    tipo_azienda=tenant.type,
                    regime_fiscale=tenant.regime_fiscale,
                    force=force,
                )

                # Save DB name to tenant (used as "piano conti created" flag)
                tenant.odoo_db_name = db_name
                await self.db.flush()

                note = None
                if tenant.type == "altro":
                    note = "Piano generico — verifica consigliata dal commercialista"

                logger.info("Piano conti created for tenant %s", tenant.id)
                return {
                    "db_name": db_name,
                    "tipo_azienda": tenant.type,
                    "regime_fiscale": tenant.regime_fiscale,
                    "accounts": result["accounts"],
                    "journals": result["journals"],
                    "tax_codes": result["tax_codes"],
                    "note": note,
                }
            except ConnectionError as e:
                last_error = e
                logger.warning(
                    "AccountingEngine failed (attempt %d/%d): %s",
                    attempt + 1, MAX_RETRIES, e,
                )

        raise ConnectionError(
            f"Impossibile creare il piano dei conti dopo {MAX_RETRIES} tentativi. "
            "Riprova piu tardi o contatta il supporto."
        ) from last_error

    async def get_piano_conti(self, user: User) -> dict:
        """Get existing chart of accounts."""
        tenant = await self._get_tenant(user)

        if not tenant.odoo_db_name:
            raise ValueError("Piano dei conti non ancora creato. Usa POST /accounting/chart per crearlo.")

        # Read from DB via AccountingEngine
        piano_data = await self.engine.get_piano_conti(tenant_id=tenant.id)

        # If no rows in DB yet (e.g. legacy flag set), fall back to template
        if piano_data is None:
            result = await self.engine.create_piano_conti(
                tenant_id=tenant.id,
                tipo_azienda=tenant.type,
                regime_fiscale=tenant.regime_fiscale,
                force=True,
            )
            accounts = result["accounts"]
            journals = result["journals"]
            tax_codes = result["tax_codes"]
        else:
            accounts = piano_data["accounts"]
            # Derive journals/tax_codes from tenant type (same logic as create)
            if tenant.regime_fiscale == "forfettario":
                tax_codes: list[str] = []
                journals = ["Vendite", "Acquisti", "Banca"]
            elif tenant.type in ("srl", "srls"):
                tax_codes = ["4%", "10%", "22%"]
                journals = ["Vendite", "Acquisti", "Banca", "Cassa", "Vari"]
            elif tenant.type == "altro":
                tax_codes = ["4%", "10%", "22%"]
                journals = ["Vendite", "Acquisti", "Banca", "Vari"]
            else:
                tax_codes = ["4%", "10%", "22%"]
                journals = ["Vendite", "Acquisti", "Banca", "Vari"]

        note = None
        if tenant.type == "altro":
            note = "Piano generico — verifica consigliata dal commercialista"

        return {
            "db_name": tenant.odoo_db_name,
            "tipo_azienda": tenant.type,
            "regime_fiscale": tenant.regime_fiscale,
            "accounts": accounts,
            "journals": journals,
            "tax_codes": tax_codes,
            "note": note,
        }
