"""Service layer per A-Cube Open Banking (Pivot 11 US-OB-04/06/07).

Gestisce il ciclo:
1. Init connessione: crea Business Registry A-Cube (se manca) + avvia PSD2 Connect
2. Tracking stato in `bank_connections`
3. Sync accounts (US-OB-06) + sync transactions con backfill (US-OB-07)
"""

from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.adapters.acube_ob import (
    ACubeAPIError,
    ACubeAuthError,
    ACubeOpenBankingClient,
)
from api.db.models import BankAccount, BankConnection, BankTransaction, Tenant
from api.modules.banking.tx_extra_parser import parse_tx_extra

logger = logging.getLogger(__name__)


class ACubeOBServiceError(Exception):
    """Errore generico livello service (business logic)."""


def _parse_amount(raw: Any) -> float:
    """A-Cube ritorna amount come stringa decimale; None → 0.0."""
    if raw is None or raw == "":
        return 0.0
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 0.0


def _parse_date(raw: Any) -> date | None:
    if not raw:
        return None
    if isinstance(raw, date):
        return raw
    try:
        return date.fromisoformat(str(raw)[:10])
    except ValueError:
        return None


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

    # ── US-OB-11: reconnect on-demand ──────────────────────

    async def request_reconnect(
        self, connection_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> dict[str, Any]:
        """Restituisce URL SCA per rinnovo consenso.

        Priorità:
        1. reconnect_url salvato dall'ultimo webhook reconnect (se presente)
        2. chiamata on-demand a A-Cube /accounts/{uuid}/reconnect sul primo account attivo
        """
        conn = await self.get_connection(connection_id, tenant_id)

        if conn.reconnect_url:
            return {
                "connection_id": conn.id,
                "reconnect_url": conn.reconnect_url,
                "source": "webhook_cached",
                "notice_level": conn.notice_level,
                "consent_expires_at": conn.consent_expires_at,
            }

        # Fallback: chiedi a A-Cube on-demand usando il primo account attivo
        first_account = (
            await self.db.execute(
                select(BankAccount)
                .where(
                    BankAccount.acube_connection_id == conn.id,
                    BankAccount.status == "connected",
                    BankAccount.acube_uuid.isnot(None),
                )
                .limit(1)
            )
        ).scalar_one_or_none()

        if not first_account or not first_account.acube_uuid:
            raise ACubeOBServiceError(
                "Nessun account A-Cube disponibile per richiedere reconnect — "
                "eseguire prima init_connection o sync-accounts"
            )

        try:
            result = await self.client.reconnect_account(first_account.acube_uuid)
        except ACubeAPIError as exc:
            raise ACubeOBServiceError(
                f"Richiesta reconnect fallita: HTTP {exc.status_code}"
            ) from exc

        reconnect_url = result.get("redirectUrl") or result.get("url")
        if not reconnect_url:
            raise ACubeOBServiceError("A-Cube non ha restituito redirectUrl per il reconnect")

        # Persist per future chiamate
        conn.reconnect_url = reconnect_url
        await self.db.commit()

        return {
            "connection_id": conn.id,
            "reconnect_url": reconnect_url,
            "source": "on_demand",
            "notice_level": conn.notice_level,
            "consent_expires_at": conn.consent_expires_at,
        }

    async def mark_expired_consents(self) -> int:
        """Scansiona tutte le BankConnection e marca come 'expired' quelle con
        consent_expires_at passato. Chiamata dal sync batch (US-OB-08).

        Returns:
            numero di connection marcate come expired.
        """
        now = datetime.utcnow()
        rows = (
            await self.db.execute(
                select(BankConnection).where(
                    BankConnection.status == "active",
                    BankConnection.consent_expires_at.isnot(None),
                    BankConnection.consent_expires_at < now,
                )
            )
        ).scalars().all()

        for conn in rows:
            conn.status = "expired"
            logger.info(
                "BankConnection %s marcata expired (fiscal_id=%s consent_expires_at=%s)",
                conn.id, conn.fiscal_id, conn.consent_expires_at,
            )

        if rows:
            await self.db.commit()
        return len(rows)

    # ── US-OB-06: sync accounts ────────────────────────────

    async def sync_accounts(
        self, connection_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> dict[str, Any]:
        """Upsert dei BankAccount a partire dagli account A-Cube del BR.

        Idempotente: identifica per `acube_uuid`. Account presenti in DB ma non
        più ritornati da A-Cube → marcati `status=revoked` (consenso perso).
        """
        conn = await self.get_connection(connection_id, tenant_id)
        if conn.status != "active":
            raise ACubeOBServiceError(
                f"Connection {connection_id} non attiva (status={conn.status}) — completare prima il consenso PSD2"
            )

        remote_accounts = await self.client.list_accounts(conn.fiscal_id)

        # Mappa locale per connection
        existing_rows = (
            await self.db.execute(
                select(BankAccount).where(BankAccount.acube_connection_id == conn.id)
            )
        ).scalars().all()
        existing_by_uuid = {a.acube_uuid: a for a in existing_rows if a.acube_uuid}

        created = 0
        updated = 0
        seen_uuids: set[str] = set()
        now = datetime.utcnow()

        for acc_data in remote_accounts:
            acube_uuid = acc_data.get("uuid")
            if not acube_uuid:
                continue
            seen_uuids.add(acube_uuid)

            existing = existing_by_uuid.get(acube_uuid)
            balance = _parse_amount(acc_data.get("balance"))
            provider_name = acc_data.get("providerName")
            iban = acc_data.get("iban") or (existing.iban if existing else f"ACUBE-{acube_uuid[:10]}")

            if existing:
                existing.balance = balance
                existing.acube_enabled = bool(acc_data.get("enabled", True))
                existing.acube_provider_name = provider_name
                existing.acube_nature = acc_data.get("nature")
                existing.acube_extra = acc_data.get("extra")
                existing.bank_name = provider_name or existing.bank_name
                existing.iban = iban
                existing.status = "connected"
                existing.last_sync_at = now
                updated += 1
            else:
                self.db.add(
                    BankAccount(
                        tenant_id=tenant_id,
                        iban=iban,
                        bank_name=provider_name or "—",
                        provider="acube_aisp",
                        status="connected",
                        acube_uuid=acube_uuid,
                        acube_connection_id=conn.id,
                        acube_provider_name=provider_name,
                        acube_nature=acc_data.get("nature"),
                        acube_enabled=bool(acc_data.get("enabled", True)),
                        balance=balance,
                        acube_extra=acc_data.get("extra"),
                        last_sync_at=now,
                    )
                )
                created += 1

        # Orphan: account locali non più su A-Cube → revoked
        orphans = 0
        for uuid_str, row in existing_by_uuid.items():
            if uuid_str not in seen_uuids and row.status != "revoked":
                row.status = "revoked"
                orphans += 1

        await self.db.commit()
        return {
            "connection_id": connection_id,
            "accounts_created": created,
            "accounts_updated": updated,
            "accounts_revoked": orphans,
            "message": f"Sync accounts: {created} nuovi, {updated} aggiornati, {orphans} revocati",
        }

    # ── US-OB-07: sync transactions con backfill ───────────

    async def sync_transactions(
        self,
        connection_id: uuid.UUID,
        tenant_id: uuid.UUID,
        *,
        since: date | None = None,
        until: date | None = None,
        status_filter: list[str] | None = None,
    ) -> dict[str, Any]:
        """Upsert BankTransaction per tutti gli account di una connection.

        - `since`: default = 30 gg fa (il default A-Cube è "mese corrente").
        - Idempotente per `(bank_account_id, acube_transaction_id)`.
        - Status pending = attributi instabili (incluso id) → aggiorniamo ma non
          contiamo come "created" definitivi.
        """
        conn = await self.get_connection(connection_id, tenant_id)
        if conn.status != "active":
            raise ACubeOBServiceError(
                f"Connection {connection_id} non attiva (status={conn.status})"
            )

        if since is None:
            since = (datetime.utcnow() - timedelta(days=30)).date()

        accounts = (
            await self.db.execute(
                select(BankAccount).where(
                    BankAccount.acube_connection_id == conn.id,
                    BankAccount.status == "connected",
                )
            )
        ).scalars().all()

        if not accounts:
            return {
                "connection_id": connection_id,
                "accounts_processed": 0,
                "tx_created": 0,
                "tx_updated": 0,
                "message": "Nessun conto attivo per questa connessione — eseguire prima sync-accounts",
            }

        tx_created = 0
        tx_updated = 0
        now = datetime.utcnow()
        made_on_after = since.isoformat() if since else None
        made_on_before = until.isoformat() if until else None

        for acc in accounts:
            if not acc.acube_uuid:
                continue

            remote_txs = await self.client.list_transactions(
                conn.fiscal_id,
                account_uuid=acc.acube_uuid,
                made_on_after=made_on_after,
                made_on_before=made_on_before,
                status=status_filter,
            )

            existing_map = {
                t.acube_transaction_id: t
                for t in (
                    await self.db.execute(
                        select(BankTransaction).where(
                            BankTransaction.bank_account_id == acc.id,
                            BankTransaction.acube_transaction_id.isnot(None),
                        )
                    )
                ).scalars().all()
            }

            for tx_data in remote_txs:
                acube_tx_id = tx_data.get("id")
                if not acube_tx_id:
                    continue

                amount = _parse_amount(tx_data.get("amount"))
                direction = "credit" if amount >= 0 else "debit"
                made_on = _parse_date(tx_data.get("madeOn")) or now.date()
                description = tx_data.get("description")
                tx_status = tx_data.get("status")
                counterparty = tx_data.get("counterparty")
                category = tx_data.get("category")
                duplicated = bool(tx_data.get("duplicated", False))
                extra = tx_data.get("extra")

                enriched = parse_tx_extra(extra=extra, description=description)

                existing = existing_map.get(acube_tx_id)
                if existing:
                    existing.amount = amount
                    existing.direction = direction
                    existing.date = made_on
                    existing.description = description
                    existing.acube_status = tx_status
                    existing.acube_category = category
                    existing.acube_duplicated = duplicated
                    existing.acube_counterparty = counterparty
                    existing.acube_extra = extra
                    existing.acube_fetched_at = now
                    existing.enriched_cro = enriched["cro"] or existing.enriched_cro
                    existing.enriched_invoice_ref = enriched["invoice_ref"] or existing.enriched_invoice_ref
                    tx_updated += 1
                else:
                    self.db.add(
                        BankTransaction(
                            bank_account_id=acc.id,
                            transaction_id=acube_tx_id,
                            acube_transaction_id=acube_tx_id,
                            date=made_on,
                            value_date=_parse_date(tx_data.get("valueDate")),
                            amount=amount,
                            direction=direction,
                            counterpart=counterparty,
                            description=description,
                            source="open_banking",
                            acube_status=tx_status,
                            acube_category=category,
                            acube_duplicated=duplicated,
                            acube_counterparty=counterparty,
                            acube_fetched_at=now,
                            acube_extra=extra,
                            enriched_cro=enriched["cro"],
                            enriched_invoice_ref=enriched["invoice_ref"],
                        )
                    )
                    tx_created += 1

            acc.last_sync_at = now

        await self.db.commit()
        return {
            "connection_id": connection_id,
            "accounts_processed": len(accounts),
            "tx_created": tx_created,
            "tx_updated": tx_updated,
            "since": since.isoformat() if since else None,
            "until": until.isoformat() if until else None,
            "message": f"Sync transazioni: {tx_created} nuove, {tx_updated} aggiornate su {len(accounts)} conti",
        }

    # ── Sync combinato accounts + transazioni ──────────────

    async def sync_now(
        self,
        connection_id: uuid.UUID,
        tenant_id: uuid.UUID,
        *,
        since: date | None = None,
    ) -> dict[str, Any]:
        """Comodità: esegue sync_accounts seguito da sync_transactions."""
        acc_result = await self.sync_accounts(connection_id, tenant_id)
        tx_result = await self.sync_transactions(
            connection_id, tenant_id, since=since
        )
        return {
            "connection_id": connection_id,
            "accounts_created": acc_result["accounts_created"],
            "accounts_updated": acc_result["accounts_updated"],
            "accounts_revoked": acc_result["accounts_revoked"],
            "accounts_synced": acc_result["accounts_created"] + acc_result["accounts_updated"],
            "tx_created": tx_result["tx_created"],
            "tx_updated": tx_result["tx_updated"],
            "message": (
                f"{acc_result['message']}. {tx_result['message']}"
            ),
        }
