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
from api.adapters.acube_scarico_massivo import (
    ACUBE_PROXY_FISCAL_ID,
    ACubeScaricoMassivoClient,
)
from api.db.models import ScaricoFatturaLog, ScaricoMassivoConfig, Tenant

logger = logging.getLogger(__name__)


class ScaricoMassivoServiceError(Exception):
    pass


class ScaricoMassivoService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._cf_client: ACubeScaricoMassivoClient | None = None

    @property
    def cf_client(self) -> ACubeScaricoMassivoClient:
        """Client A-Cube gov-it (cassetto fiscale + emissione)."""
        if self._cf_client is None:
            self._cf_client = ACubeScaricoMassivoClient()
        return self._cf_client

    async def save_appointee_credentials(
        self,
        *,
        appointee_fiscal_id: str,
        password: str,
        pin: str,
        username_or_fiscal_id: str | None = None,
    ) -> dict[str, Any]:
        """Salva credenziali Fisconline dell'incaricato su A-Cube (cifrate lato loro).

        Le credenziali NON vengono persistite nel nostro DB — solo trasmesse
        ad A-Cube via PUT. Operazione idempotente.
        """
        client = self.cf_client
        try:
            await client.set_appointee_credentials(
                appointee_fiscal_id=appointee_fiscal_id,
                password=password,
                pin=pin,
                username_or_fiscal_id=username_or_fiscal_id,
            )
        except (ACubeAPIError, ACubeAuthError) as e:
            logger.warning("set_appointee_credentials failed: %s", e)
            raise ScaricoMassivoServiceError(
                f"Salvataggio credenziali fallito: {e}"
            ) from e
        return {
            "appointee_fiscal_id": appointee_fiscal_id,
            "saved": True,
            "message": "Credenziali salvate su A-Cube — incaricato pronto per onboarding clienti.",
        }

    async def setup_client_onboarding(
        self,
        cfg: ScaricoMassivoConfig,
        *,
        backfill_archive: bool = True,
    ) -> dict[str, Any]:
        """Orchestra onboarding cliente A-Cube — appointee mode.

        Sequenza (assume incaricato già configurato lato A-Cube via support):
          1. POST /business-registry-configuration   (crea config per P.IVA cliente)
          2. POST /ade-appointees/{appointee_fid}/assign  (assegna P.IVA cliente all'incaricato)
          3. POST /schedule/invoice-download/{piva}  (daily schedule + archive backfill)

        Salva acube_config_id sulla ScaricoMassivoConfig.

        Prerequisiti utente:
        - Cliente ha conferito incarico sul portale AdE (manuale)
        - Variabile ACUBE_APPOINTEE_FISCAL_ID configurata su Railway (default 'A-CUBE')
        """
        import os
        appointee_fiscal_id = os.getenv("ACUBE_APPOINTEE_FISCAL_ID", "A-CUBE")
        client = self.cf_client

        # Step 1: crea config se non già fatto
        if not cfg.acube_config_id:
            try:
                br_cfg = await client.create_br_configuration(cfg.client_fiscal_id)
                cfg.acube_config_id = br_cfg.get("id") or br_cfg.get("@id", "").split("/")[-1]
                logger.info("BR config creata: %s for piva=%s", cfg.acube_config_id, cfg.client_fiscal_id)
            except (ACubeAPIError, ACubeAuthError) as e:
                cfg.last_sync_error = f"create_br_configuration failed: {e}"
                await self.db.commit()
                raise ScaricoMassivoServiceError(f"Creazione configurazione fallita: {e}") from e

        # Step 2: assegna P.IVA cliente all'incaricato
        try:
            await client.assign_to_appointee(
                appointee_fiscal_id=appointee_fiscal_id,
                client_fiscal_id=cfg.client_fiscal_id,
            )
            logger.info(
                "P.IVA %s assegnata a incaricato %s", cfg.client_fiscal_id, appointee_fiscal_id
            )
        except (ACubeAPIError, ACubeAuthError) as e:
            cfg.last_sync_error = f"assign_to_appointee failed: {e}"
            await self.db.commit()
            raise ScaricoMassivoServiceError(f"Assegnazione incaricato fallita: {e}") from e

        # Step 3: schedule daily (con archivio se backfill richiesto)
        try:
            schedule = await client.schedule_daily_download(
                cfg.client_fiscal_id, download_archive=backfill_archive,
            )
            logger.info("Daily schedule attivato per piva=%s archive=%s", cfg.client_fiscal_id, backfill_archive)
        except (ACubeAPIError, ACubeAuthError) as e:
            cfg.last_sync_error = f"schedule_daily_download failed: {e}"
            await self.db.commit()
            raise ScaricoMassivoServiceError(f"Schedule download fallito: {e}") from e

        cfg.status = "active"
        cfg.last_sync_error = None
        await self.db.commit()

        return {
            "config_id": str(cfg.id),
            "acube_config_id": cfg.acube_config_id,
            "appointee_fiscal_id": appointee_fiscal_id,
            "client_fiscal_id": cfg.client_fiscal_id,
            "schedule_enabled": schedule.get("enabled", True),
            "backfill_archive": backfill_archive,
            "message": (
                "Onboarding completato. Primo scarico massivo entro 72h. "
                "Daily schedule attivo alle 03:00 UTC."
            ),
        }
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

    async def ensure_self_config(self, tenant_id: uuid.UUID) -> ScaricoMassivoConfig:
        """Get-or-create the self-tenant config — each AgentFlow tenant monitors ONLY its own P.IVA.

        Reads tenant.piva and tenant.name to populate the config automatically.
        """
        # Look for existing config (any) for this tenant
        existing_res = await self.db.execute(
            select(ScaricoMassivoConfig).where(ScaricoMassivoConfig.tenant_id == tenant_id)
        )
        existing = existing_res.scalar_one_or_none()
        if existing:
            return existing

        # Read tenant data to seed the new config
        tenant_res = await self.db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = tenant_res.scalar_one_or_none()
        if not tenant:
            raise ScaricoMassivoServiceError("Tenant non trovato")
        if not tenant.piva:
            raise ScaricoMassivoServiceError(
                "P.IVA azienda non configurata — completa il profilo prima di abilitare lo scarico massivo"
            )

        cfg = ScaricoMassivoConfig(
            tenant_id=tenant_id,
            client_fiscal_id=tenant.piva,
            client_name=tenant.name or f"Tenant {tenant.piva}",
            onboarding_mode="proxy",
            status="pending",
            environment=self.client.env,
        )
        self.db.add(cfg)
        await self.db.commit()
        await self.db.refresh(cfg)
        return cfg

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
        """Insert a new invoice log row if not already present. Returns True if inserted.

        A-Cube response shape (`GET /invoices`) — top-level fields:
          uuid, created_at, type, payload (JSON string of full FatturaPA),
          sender (dict), recipient (dict), notifications, sdi_file_name,
          sdi_file_id, marking, document_type, transmission_format
        """
        codice_univoco = (
            item.get("sdi_file_name")  # SDI-assigned filename, unique once delivered
            or item.get("uuid")
            or item.get("@id", "").split("/")[-1]
        )
        if not codice_univoco:
            logger.warning("Invoice without identifiable dedupe key: %s", item)
            return False

        existing_res = await self.db.execute(
            select(ScaricoFatturaLog).where(
                and_(
                    ScaricoFatturaLog.tenant_id == cfg.tenant_id,
                    ScaricoFatturaLog.config_id == cfg.id,
                    ScaricoFatturaLog.codice_univoco_sdi == str(codice_univoco),
                )
            )
        )
        if existing_res.scalar_one_or_none():
            return False

        # Parse the FatturaPA payload (stringified JSON) for canonical fields
        numero_fattura = None
        data_fattura = None
        importo_totale = None
        tipo_documento = item.get("document_type")

        payload = item.get("payload")
        if isinstance(payload, str):
            try:
                import json as _json
                payload = _json.loads(payload)
            except (ValueError, TypeError):
                payload = None

        if isinstance(payload, dict):
            body = payload.get("fattura_elettronica_body") or {}
            if isinstance(body, list):
                body = body[0] if body else {}
            doc = ((body.get("dati_generali") or {}).get("dati_generali_documento")) or {}
            numero_fattura = doc.get("numero")
            tipo_documento = tipo_documento or doc.get("tipo_documento")
            date_str = doc.get("data")
            try:
                data_fattura = date.fromisoformat(date_str[:10]) if date_str else None
            except (ValueError, TypeError):
                data_fattura = None
            try:
                importo_totale = float(doc.get("importo_totale_documento")) if doc.get("importo_totale_documento") else None
            except (ValueError, TypeError):
                importo_totale = None

        # Controparte: for passive invoices it's the sender; for active it's the recipient
        controparte = item.get("sender") if direction == "passive" else item.get("recipient")
        if not isinstance(controparte, dict):
            controparte = {}

        log = ScaricoFatturaLog(
            tenant_id=cfg.tenant_id,
            config_id=cfg.id,
            client_fiscal_id=cfg.client_fiscal_id,
            codice_univoco_sdi=str(codice_univoco),
            numero_fattura=numero_fattura,
            tipo_documento=tipo_documento,
            direction=direction,
            data_fattura=data_fattura,
            importo_totale=importo_totale,
            controparte_piva=controparte.get("fiscal_id") or controparte.get("vat_number") or controparte.get("piva"),
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
