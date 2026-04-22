"""Service layer per A-Cube Open Banking (Pivot 11 US-OB-04).

Gestisce il ciclo:
1. Init connessione: crea Business Registry A-Cube (se manca) + avvia PSD2 Connect
2. Tracking stato in `bank_connections`
3. Sync base (placeholder per US-OB-06/07)
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.adapters.acube_ob import (
    ACubeAPIError,
    ACubeAuthError,
    ACubeOpenBankingClient,
)
from api.db.models import BankAccount, BankConnection, Tenant

logger = logging.getLogger(__name__)


class ACubeOBServiceError(Exception):
    """Errore generico livello service (business logic)."""


class ACubeOpenBankingService:
    """Business logic per integrazione A-Cube OB.

    Pattern: istanzia client ad ogni request (singleton globale sarebbe ok,
    ma così facilita l'iniezione di mock nei test).
    """

    def __init__(self, db: AsyncSession, client: ACubeOpenBankingClient | None = None) -> None:
        self.db = db
        self.client = client or ACubeOpenBankingClient()

    # ── Helpers ────────────────────────────────────────────

    async def _get_tenant(self, tenant_id: uuid.UUID) -> Tenant:
        tenant = (await self.db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()
        if not tenant:
            raise ACubeOBServiceError(f"Tenant {tenant_id} non trovato")
        return tenant

    async def _get_or_resolve_fiscal_id(
        self, tenant_id: uuid.UUID, explicit_fiscal_id: str | None
    ) -> str:
        if explicit_fiscal_id:
            return explicit_fiscal_id.strip().upper()
        tenant = await self._get_tenant(tenant_id)
        if not tenant.piva:
            raise ACubeOBServiceError(
                "Nessuna P.IVA configurata per il tenant — impossibile creare Business Registry A-Cube"
            )
        return tenant.piva.strip().upper()

    async def _get_connection(
        self, tenant_id: uuid.UUID, fiscal_id: str
    ) -> BankConnection | None:
        result = await self.db.execute(
            select(BankConnection).where(
                BankConnection.tenant_id == tenant_id,
                BankConnection.fiscal_id == fiscal_id,
            )
        )
        return result.scalar_one_or_none()

    def _generate_br_email(self, fiscal_id: str) -> str:
        """Email univoca per BR A-Cube (vincolo: email non riusabile tra BR diversi)."""
        return f"br-{fiscal_id.lower()}@agentflow.taal.it"

    # ── Core: init connection ──────────────────────────────

    async def init_connection(
        self,
        tenant_id: uuid.UUID,
        return_url: str,
        fiscal_id: str | None = None,
    ) -> dict[str, Any]:
        """Avvia flusso PSD2 Connect.

        Steps:
        1. Resolve fiscal_id (da parametro o da tenant.piva)
        2. Get-or-create BankConnection locale
        3. Se acube_br_uuid mancante → POST /business-registry su A-Cube (⚠️ fee)
        4. POST /business-registry/{fiscalId}/connect → ottiene connect_url
        5. Salva stato, return a frontend per redirect utente
        """
        if not self.client.enabled:
            raise ACubeOBServiceError("Client A-Cube OB non configurato")

        resolved_fiscal_id = await self._get_or_resolve_fiscal_id(tenant_id, fiscal_id)
        tenant = await self._get_tenant(tenant_id)
        business_name = tenant.name or f"Tenant {resolved_fiscal_id}"

        # Get-or-create local connection
        conn = await self._get_connection(tenant_id, resolved_fiscal_id)
        if conn is None:
            conn = BankConnection(
                tenant_id=tenant_id,
                fiscal_id=resolved_fiscal_id,
                business_name=business_name,
                acube_email=self._generate_br_email(resolved_fiscal_id),
                status="pending",
                environment=self.client.env,
            )
            self.db.add(conn)
            await self.db.flush()  # ottiene conn.id senza commit completo

        # Create BR on A-Cube if missing (⚠️ fee charged)
        if not conn.acube_br_uuid:
            try:
                br = await self.client.create_business_registry(
                    fiscal_id=resolved_fiscal_id,
                    email=conn.acube_email or self._generate_br_email(resolved_fiscal_id),
                    business_name=business_name,
                    enabled=False,  # attivato solo al connect riuscito
                )
                # A-Cube non sempre ritorna 'uuid' — a seconda della versione potrebbe essere '@id' o altro
                conn.acube_br_uuid = br.get("uuid") or br.get("@id") or br.get("fiscalId")
                logger.info("A-Cube BR creato per fiscal_id=%s", resolved_fiscal_id)
            except ACubeAPIError as exc:
                conn.last_connect_error = f"BR create failed HTTP {exc.status_code}: {exc.body[:200]}"
                await self.db.commit()
                raise ACubeOBServiceError(
                    f"Creazione Business Registry fallita: HTTP {exc.status_code}"
                ) from exc
            except ACubeAuthError as exc:
                conn.last_connect_error = f"Auth error: {exc}"
                await self.db.commit()
                raise ACubeOBServiceError(f"Errore auth A-Cube: {exc}") from exc

        # Start PSD2 connect
        try:
            result = await self.client.start_connect(
                fiscal_id=resolved_fiscal_id,
                redirect_url=return_url,
                locale="it",
            )
        except ACubeAPIError as exc:
            conn.last_connect_error = f"Connect failed HTTP {exc.status_code}: {exc.body[:200]}"
            await self.db.commit()
            raise ACubeOBServiceError(f"Avvio connect fallito: HTTP {exc.status_code}") from exc

        connect_url = result.get("redirectUrl") or result.get("url")
        if not connect_url:
            raise ACubeOBServiceError("A-Cube non ha restituito redirectUrl per il connect")

        conn.last_connect_error = None
        await self.db.commit()
        await self.db.refresh(conn)

        return {
            "connection_id": conn.id,
            "connect_url": connect_url,
            "status": conn.status,
            "fiscal_id": conn.fiscal_id,
            "acube_br_uuid": conn.acube_br_uuid,
        }

    # ── Lista connessioni per tenant ───────────────────────

    async def list_connections(self, tenant_id: uuid.UUID) -> list[BankConnection]:
        result = await self.db.execute(
            select(BankConnection).where(BankConnection.tenant_id == tenant_id).order_by(BankConnection.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_connection(self, connection_id: uuid.UUID, tenant_id: uuid.UUID) -> BankConnection:
        result = await self.db.execute(
            select(BankConnection).where(
                BankConnection.id == connection_id,
                BankConnection.tenant_id == tenant_id,
            )
        )
        conn = result.scalar_one_or_none()
        if not conn:
            raise ACubeOBServiceError(f"Connection {connection_id} non trovata per questo tenant")
        return conn

    # ── Sync manuale (placeholder — full impl in US-OB-06/07) ──

    async def sync_now(self, connection_id: uuid.UUID, tenant_id: uuid.UUID) -> dict[str, Any]:
        conn = await self.get_connection(connection_id, tenant_id)
        if conn.status != "active":
            raise ACubeOBServiceError(
                f"Connection {connection_id} non attiva (status={conn.status}) — completare prima il consenso PSD2"
            )

        # Solo sync accounts come placeholder — le transazioni saranno in US-OB-07
        accounts = await self.client.list_accounts(conn.fiscal_id)
        synced_count = 0
        for acc_data in accounts:
            acube_uuid = acc_data.get("uuid")
            if not acube_uuid:
                continue
            # upsert by acube_uuid
            existing = (
                await self.db.execute(
                    select(BankAccount).where(BankAccount.acube_uuid == acube_uuid)
                )
            ).scalar_one_or_none()
            if existing:
                existing.balance = float(acc_data.get("balance") or 0)
                existing.acube_enabled = bool(acc_data.get("enabled", True))
                existing.acube_provider_name = acc_data.get("providerName")
                existing.acube_nature = acc_data.get("nature")
            else:
                self.db.add(
                    BankAccount(
                        tenant_id=tenant_id,
                        iban=acc_data.get("iban") or f"ACUBE-{acube_uuid[:10]}",
                        bank_name=acc_data.get("providerName") or "—",
                        provider="acube_aisp",
                        status="connected",
                        acube_uuid=acube_uuid,
                        acube_connection_id=conn.id,
                        acube_provider_name=acc_data.get("providerName"),
                        acube_nature=acc_data.get("nature"),
                        acube_enabled=bool(acc_data.get("enabled", True)),
                        balance=float(acc_data.get("balance") or 0),
                        acube_extra=acc_data.get("extra"),
                    )
                )
                synced_count += 1

        await self.db.commit()
        return {
            "connection_id": connection_id,
            "accounts_synced": synced_count,
            "message": f"Sync accounts completato: {synced_count} nuovi, {len(accounts) - synced_count} aggiornati",
        }
