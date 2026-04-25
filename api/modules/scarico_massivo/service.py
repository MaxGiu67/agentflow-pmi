"""Service for Scarico Massivo Cassetto Fiscale — manages per-client configs and sync.

Uses the real A-Cube E-Invoicing API (api/adapters/acube_einvoicing.py) — same
endpoints + same JWT as invoice emission. The "Scarico Massivo" surface is
just `GET /invoices?direction=passive&fiscalId={piva}` filtered per delegate.
"""

from __future__ import annotations

import logging
import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.adapters.acube_einvoicing import (
    ACubeAPIError,
    ACubeAuthError,
    ACubeEInvoicingClient,
)
from api.adapters.acube_scarico_massivo import ACUBE_PROXY_FISCAL_ID
from api.db.models import ScaricoFatturaLog, ScaricoMassivoConfig

logger = logging.getLogger(__name__)


class ScaricoMassivoServiceError(Exception):
    pass


class ScaricoMassivoService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._client: ACubeEInvoicingClient | None = None

    @property
    def client(self) -> ACubeEInvoicingClient:
        if self._client is None:
            self._client = ACubeEInvoicingClient()
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

    # ── Sync — real implementation (A-Cube E-Invoicing API) ──

    async def sync_now(
        self,
        config_id: uuid.UUID,
        tenant_id: uuid.UUID,
        *,
        since: date | None = None,
        until: date | None = None,
        direction: str | None = None,
    ) -> dict:
        """Pull invoices from A-Cube for a single client P.IVA and persist.

        Calls `GET /invoices?fiscalId={piva}&direction=...` and saves new rows
        in ScaricoFatturaLog (deduped by codice_univoco_sdi).
        """
        cfg = await self.get_config(config_id, tenant_id)
        if not cfg:
            raise ScaricoMassivoServiceError("Configurazione non trovata")

        if not self.client.enabled:
            cfg.last_sync_error = "Client A-Cube non configurato"
            await self.db.commit()
            raise ScaricoMassivoServiceError("Client A-Cube non configurato")

        directions = ["passive", "active"] if direction is None else [direction]
        new_count = 0
        total_scanned = 0
        errors = 0

        for d in directions:
            try:
                items = await self.client.list_invoices(
                    direction=d,
                    fiscal_id=cfg.client_fiscal_id,
                    since=since,
                    until=until,
                )
            except (ACubeAPIError, ACubeAuthError) as e:
                logger.warning(
                    "scarico_massivo sync failed for %s direction=%s: %s",
                    cfg.client_fiscal_id, d, e,
                )
                errors += 1
                cfg.last_sync_error = f"A-Cube {d}: {e}"
                continue

            total_scanned += len(items)
            for item in items:
                if await self._upsert_invoice_log(cfg, d, item):
                    new_count += 1

        cfg.last_sync_at = datetime.utcnow()
        cfg.last_sync_new_count = new_count
        if errors == 0:
            cfg.last_sync_error = None
            cfg.status = "active"
        cfg.invoices_downloaded_total += new_count
        # Reset YTD counter on year change
        current_year = datetime.utcnow().year
        if cfg.last_sync_at and cfg.last_sync_at.year == current_year:
            cfg.invoices_downloaded_ytd += new_count

        await self.db.commit()

        return {
            "config_id": cfg.id,
            "client_fiscal_id": cfg.client_fiscal_id,
            "new_invoices": new_count,
            "total_scanned": total_scanned,
            "errors": errors,
            "message": (
                f"Sync OK: {new_count} nuove fatture su {total_scanned} trovate"
                if errors == 0
                else f"Sync con errori: {new_count} nuove, {errors} direzioni fallite"
            ),
        }

    async def _upsert_invoice_log(
        self,
        cfg: ScaricoMassivoConfig,
        direction: str,
        item: dict[str, Any],
    ) -> bool:
        """Insert a new invoice log row if not already present. Returns True if inserted."""
        # Identify the dedupe key — A-Cube returns "uuid" + "number" + sometimes "sdiId"
        codice_univoco = (
            item.get("sdiId")
            or item.get("uuid")
            or item.get("@id", "").split("/")[-1]
            or item.get("number")
        )
        if not codice_univoco:
            logger.warning("Invoice without identifiable dedupe key: %s", item)
            return False

        existing_res = await self.db.execute(
            select(ScaricoFatturaLog).where(
                and_(
                    ScaricoFatturaLog.tenant_id == cfg.tenant_id,
                    ScaricoFatturaLog.config_id == cfg.id,
                    ScaricoFatturaLog.codice_univoco_sdi == codice_univoco,
                )
            )
        )
        if existing_res.scalar_one_or_none():
            return False

        # Try to extract canonical fields — A-Cube responses can have multiple shapes
        date_str = item.get("date") or item.get("invoiceDate") or item.get("data")
        try:
            data_fattura = date.fromisoformat(date_str[:10]) if date_str else None
        except (ValueError, TypeError):
            data_fattura = None

        controparte = item.get("counterparty") or item.get("recipient") or item.get("supplier") or {}
        if not isinstance(controparte, dict):
            controparte = {}

        log = ScaricoFatturaLog(
            tenant_id=cfg.tenant_id,
            config_id=cfg.id,
            client_fiscal_id=cfg.client_fiscal_id,
            codice_univoco_sdi=str(codice_univoco),
            numero_fattura=item.get("number") or item.get("numero"),
            tipo_documento=item.get("type") or item.get("documentType"),
            direction=direction,
            data_fattura=data_fattura,
            importo_totale=item.get("total") or item.get("totalAmount"),
            controparte_piva=controparte.get("fiscalId") or controparte.get("piva"),
            controparte_nome=controparte.get("name") or controparte.get("denominazione"),
            acube_invoice_id=item.get("uuid"),
        )
        self.db.add(log)
        return True

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
