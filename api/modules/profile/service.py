import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import Tenant, User

logger = logging.getLogger(__name__)


class ProfileService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_profile(self, user: User) -> dict:
        """Get user profile with tenant info."""
        tenant = None
        if user.tenant_id:
            result = await self.db.execute(
                select(Tenant).where(Tenant.id == user.tenant_id)
            )
            tenant = result.scalar_one_or_none()

        return {
            "user_id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "tenant_id": user.tenant_id,
            "azienda_nome": tenant.name if tenant else None,
            "tipo_azienda": tenant.type if tenant else None,
            "regime_fiscale": tenant.regime_fiscale if tenant else None,
            "piva": tenant.piva if tenant else None,
            "codice_ateco": tenant.codice_ateco if tenant else None,
            "has_piano_conti": tenant.odoo_db_name is not None if tenant else False,
            "created_at": user.created_at,
        }

    async def update_profile(
        self,
        user: User,
        name: str | None = None,
        tipo_azienda: str | None = None,
        regime_fiscale: str | None = None,
        piva: str | None = None,
        codice_ateco: str | None = None,
        azienda_nome: str | None = None,
    ) -> dict:
        """Update user profile and tenant configuration."""
        # Update user fields
        if name is not None:
            user.name = name

        # Handle tenant
        tenant = None
        if user.tenant_id:
            result = await self.db.execute(
                select(Tenant).where(Tenant.id == user.tenant_id)
            )
            tenant = result.scalar_one_or_none()

        # Check if P.IVA is already used by another tenant
        if piva and tenant and tenant.piva != piva:
            existing = await self.db.execute(
                select(Tenant).where(Tenant.piva == piva, Tenant.id != tenant.id)
            )
            if existing.scalar_one_or_none():
                raise ValueError("P.IVA gia associata a un altro account")

        if not tenant and (tipo_azienda or regime_fiscale or piva):
            # Create new tenant
            tenant = Tenant(
                name=azienda_nome or user.name or "Azienda",
                type=tipo_azienda or "piva",
                regime_fiscale=regime_fiscale or "ordinario",
                piva=piva,
                codice_ateco=codice_ateco,
            )
            self.db.add(tenant)
            await self.db.flush()
            user.tenant_id = tenant.id
        elif tenant:
            # Update existing tenant
            if azienda_nome is not None:
                tenant.name = azienda_nome
            if tipo_azienda is not None:
                tenant.type = tipo_azienda
            if regime_fiscale is not None:
                tenant.regime_fiscale = regime_fiscale
            if piva is not None:
                tenant.piva = piva
            if codice_ateco is not None:
                tenant.codice_ateco = codice_ateco

        await self.db.flush()
        logger.info("Profile updated for user %s", user.email)
        return await self.get_profile(user)

    async def check_profile_change_impact(
        self,
        user: User,
        tipo_azienda: str | None = None,
        regime_fiscale: str | None = None,
    ) -> dict | None:
        """Check if profile change requires piano conti recreation."""
        if not user.tenant_id:
            return None

        result = await self.db.execute(
            select(Tenant).where(Tenant.id == user.tenant_id)
        )
        tenant = result.scalar_one_or_none()
        if not tenant or not tenant.odoo_db_name:
            return None  # No piano conti yet

        changes = []
        if tipo_azienda and tipo_azienda != tenant.type:
            changes.append(f"tipo azienda da '{tenant.type}' a '{tipo_azienda}'")
        if regime_fiscale and regime_fiscale != tenant.regime_fiscale:
            changes.append(f"regime fiscale da '{tenant.regime_fiscale}' a '{regime_fiscale}'")

        if not changes:
            return None

        return {
            "message": (
                f"Attenzione: modificare {', '.join(changes)} richiede la ricreazione "
                "del piano dei conti. Le scritture esistenti potrebbero necessitare riallineamento."
            ),
            "requires_confirmation": True,
            "affected_areas": ["piano_dei_conti", "scritture_contabili"],
        }

    # ── Impostazioni Fatturazione (US-42) ──

    async def get_invoice_settings(self, user: User) -> dict:
        """Get invoice settings from tenant."""
        if not user.tenant_id:
            raise ValueError("Profilo azienda non configurato")

        result = await self.db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
        tenant = result.scalar_one_or_none()
        if not tenant:
            raise ValueError("Tenant non trovato")

        return {
            "name": tenant.name,
            "piva": tenant.piva,
            "codice_fiscale": tenant.codice_fiscale,
            "regime_fiscale_sdi": tenant.regime_fiscale_sdi,
            "sede_indirizzo": tenant.sede_indirizzo,
            "sede_numero_civico": tenant.sede_numero_civico,
            "sede_cap": tenant.sede_cap,
            "sede_comune": tenant.sede_comune,
            "sede_provincia": tenant.sede_provincia,
            "sede_nazione": tenant.sede_nazione,
            "iban": tenant.iban,
            "banca_nome": tenant.banca_nome,
            "bic": tenant.bic,
            "modalita_pagamento": tenant.modalita_pagamento,
            "condizioni_pagamento": tenant.condizioni_pagamento,
            "giorni_pagamento": tenant.giorni_pagamento,
            "rea_ufficio": tenant.rea_ufficio,
            "rea_numero": tenant.rea_numero,
            "rea_capitale_sociale": tenant.rea_capitale_sociale,
            "rea_socio_unico": tenant.rea_socio_unico,
            "rea_stato_liquidazione": tenant.rea_stato_liquidazione,
            "telefono": tenant.telefono,
            "email_aziendale": tenant.email_aziendale,
            "pec": tenant.pec,
        }

    async def update_invoice_settings(self, user: User, data: dict) -> dict:
        """Update invoice settings in tenant. Only non-None fields are updated."""
        if not user.tenant_id:
            raise ValueError("Profilo azienda non configurato")

        result = await self.db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
        tenant = result.scalar_one_or_none()
        if not tenant:
            raise ValueError("Tenant non trovato")

        # Update only provided fields
        settable_fields = [
            "codice_fiscale", "regime_fiscale_sdi",
            "sede_indirizzo", "sede_numero_civico", "sede_cap",
            "sede_comune", "sede_provincia", "sede_nazione",
            "iban", "banca_nome", "bic",
            "modalita_pagamento", "condizioni_pagamento", "giorni_pagamento",
            "rea_ufficio", "rea_numero", "rea_capitale_sociale",
            "rea_socio_unico", "rea_stato_liquidazione",
            "telefono", "email_aziendale", "pec",
        ]

        for field in settable_fields:
            value = data.get(field)
            if value is not None:
                setattr(tenant, field, value)

        await self.db.flush()
        logger.info("Invoice settings updated for tenant %s", tenant.id)
        return await self.get_invoice_settings(user)
