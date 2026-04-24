"""Service for Scarico Massivo Cassetto Fiscale — manages per-client configs and sync.

STATO: SCAFFOLDING — logica CRUD completa, sync_now() ritorna NotImplementedError
finché non arriva la risposta A-Cube Ticket 02 con gli endpoint esatti.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.adapters.acube_scarico_massivo import (
    ACUBE_PROXY_FISCAL_ID,
    ACubeScaricoMassivoClient,
)
from api.db.models import ScaricoFatturaLog, ScaricoMassivoConfig

logger = logging.getLogger(__name__)


class ScaricoMassivoServiceError(Exception):
    pass


class ScaricoMassivoService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._client: ACubeScaricoMassivoClient | None = None

    @property
    def client(self) -> ACubeScaricoMassivoClient:
        if self._client is None:
            self._client = ACubeScaricoMassivoClient()
        return self._client

    # ── CRUD config ───────────────────────────────────────

    async def list_configs(self, tenant_id: uuid.UUID) -> list[ScaricoMassivoConfig]:
        res = await self.db.execute(
            select(ScaricoMassivoConfig)
            .where(ScaricoMassivoConfig.tenant_id == tenant_id)
            .order_by(ScaricoMassivoConfig.created_at.desc())
        )
        return list(res.scalars().all())

    async def get_config(
        self, config_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> ScaricoMassivoConfig | None:
        res = await self.db.execute(
            select(ScaricoMassivoConfig).where(
                and_(
                    ScaricoMassivoConfig.id == config_id,
                    ScaricoMassivoConfig.tenant_id == tenant_id,
                )
            )
        )
        return res.scalar_one_or_none()

    async def register_client(
        self,
        tenant_id: uuid.UUID,
        client_fiscal_id: str,
        client_name: str,
        onboarding_mode: str = "proxy",
    ) -> ScaricoMassivoConfig:
        # Dedupe: one row per (tenant, fiscal_id)
        existing_res = await self.db.execute(
            select(ScaricoMassivoConfig).where(
                and_(
                    ScaricoMassivoConfig.tenant_id == tenant_id,
                    ScaricoMassivoConfig.client_fiscal_id == client_fiscal_id,
                )
            )
        )
        existing = existing_res.scalar_one_or_none()
        if existing:
            raise ScaricoMassivoServiceError(
                f"P.IVA {client_fiscal_id} già registrata (stato: {existing.status})"
            )

        cfg = ScaricoMassivoConfig(
            tenant_id=tenant_id,
            client_fiscal_id=client_fiscal_id,
            client_name=client_name,
            onboarding_mode=onboarding_mode,
            status="pending",
            environment=self.client.env,
        )
        self.db.add(cfg)
        await self.db.commit()
        await self.db.refresh(cfg)
        return cfg

    async def delete_config(self, config_id: uuid.UUID, tenant_id: uuid.UUID) -> bool:
        cfg = await self.get_config(config_id, tenant_id)
        if not cfg:
            return False
        await self.db.delete(cfg)
        await self.db.commit()
        return True

    # ── Sync — implementazione pending Ticket 02 ──────────

    async def sync_now(
        self,
        config_id: uuid.UUID,
        tenant_id: uuid.UUID,
        *,
        since=None,
        until=None,
        direction: str | None = None,
    ) -> dict:
        """Trigger a bulk download for a single client.

        TODO: Implementazione completa appena arriva la doc A-Cube.
        """
        cfg = await self.get_config(config_id, tenant_id)
        if not cfg:
            raise ScaricoMassivoServiceError("Configurazione non trovata")

        # Mark error so UI shows that the sync isn't wired yet
        cfg.last_sync_error = (
            "Integrazione scarico massivo in attesa risposta A-Cube Ticket 02 "
            "(inviato 2026-04-24). Endpoints e formato risposta non ancora confermati."
        )
        await self.db.commit()

        raise ScaricoMassivoServiceError(
            "Scarico massivo non ancora operativo — attesa risposta tecnica A-Cube."
        )

    # ── Invoice log ───────────────────────────────────────

    async def list_invoice_log(
        self,
        tenant_id: uuid.UUID,
        config_id: uuid.UUID | None = None,
        limit: int = 100,
    ) -> list[ScaricoFatturaLog]:
        conditions = [ScaricoFatturaLog.tenant_id == tenant_id]
        if config_id:
            conditions.append(ScaricoFatturaLog.config_id == config_id)
        res = await self.db.execute(
            select(ScaricoFatturaLog)
            .where(and_(*conditions))
            .order_by(ScaricoFatturaLog.downloaded_at.desc())
            .limit(limit)
        )
        return list(res.scalars().all())

    # ── Delega guide (UI helper, proxy mode) ──────────────

    @staticmethod
    def get_delega_guide() -> dict:
        """Return the step-by-step delega procedure (A-Cube proxy mode)."""
        return {
            "acube_fiscal_id": ACUBE_PROXY_FISCAL_ID,
            "portale_ade_url": "https://www.agenziaentrate.gov.it/portale/area-riservata",
            "steps": [
                "Accedi al portale AdE con SPID/CIE/CNS (o Fisconline/Entratel)",
                "In alto a destra verifica che l'utenza di lavoro sia l'azienda (non persona fisica)",
                "Menu → Il tuo profilo",
                "Menu laterale → Deleghe → Intermediari",
                'Card "Delega unica ai servizi online" → clicca "Nuova delega →"',
                f"Inserisci il codice fiscale del delegato: {ACUBE_PROXY_FISCAL_ID} (A-Cube S.r.l.)",
                "Spunta i 3 servizi indicati qui sotto",
                'Clicca "Inserisci" — la delega sarà subito "Attiva" con scadenza 31/12 del 4° anno successivo',
            ],
            "services_to_delegate": [
                "Consultazione e acquisizione delle fatture elettroniche o dei loro duplicati informatici",
                "Consultazione dei dati rilevanti ai fini IVA",
                "Registrazione dell'indirizzo telematico",
            ],
        }
