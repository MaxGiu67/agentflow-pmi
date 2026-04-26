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

from sqlalchemy import and_, select
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

        # Create BR on A-Cube if missing — idempotent (handles "already exists" 422)
        if not conn.acube_br_uuid:
            try:
                br = await self.client.create_business_registry(
                    fiscal_id=resolved_fiscal_id,
                    email=conn.acube_email or self._generate_br_email(resolved_fiscal_id),
                    business_name=business_name,
                    enabled=True,  # required by A-Cube to start /connect (PSD2 SCA)
                )
                conn.acube_br_uuid = br.get("uuid") or br.get("@id") or br.get("fiscalId")
                logger.info("A-Cube BR creato per fiscal_id=%s", resolved_fiscal_id)
            except ACubeAPIError as exc:
                # Idempotent fallback: if BR already exists on A-Cube (422 "already used"),
                # adopt the existing one instead of failing
                if exc.status_code == 422 and "already used" in (exc.body or ""):
                    logger.info("A-Cube BR già esistente per fiscal_id=%s — adopting", resolved_fiscal_id)
                    try:
                        existing = await self.client.get_business_registry(resolved_fiscal_id)
                        conn.acube_br_uuid = (
                            existing.get("uuid") or existing.get("@id") or existing.get("fiscalId")
                        )
                        # Ensure enabled=true so /connect works
                        if not existing.get("enabled"):
                            await self.client.update_business_registry(resolved_fiscal_id, enabled=True)
                    except ACubeAPIError as exc2:
                        conn.last_connect_error = (
                            f"BR exists but cannot adopt: HTTP {exc2.status_code}: {exc2.body[:200]}"
                        )
                        await self.db.commit()
                        raise ACubeOBServiceError(
                            f"BR già esistente ma adozione fallita: HTTP {exc2.status_code}"
                        ) from exc2
                else:
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

        # A-Cube returns "connectUrl" in production (not "redirectUrl" as old docs said)
        connect_url = result.get("connectUrl") or result.get("redirectUrl") or result.get("url")
        if not connect_url:
            raise ACubeOBServiceError(
                f"A-Cube non ha restituito connect URL: {str(result)[:200]}"
            )

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
        # Don't fail on pending — A-Cube is the source of truth. If it returns
        # accounts, the consent is in place even if our webhook didn't fire.
        # We auto-promote to "active" further below when we see remote accounts.

        remote_accounts = await self.client.list_accounts(conn.fiscal_id)

        # Self-heal: A-Cube has accounts → consent confirmed → promote to active
        if remote_accounts and conn.status != "active":
            conn.status = "active"
            conn.acube_enabled = True
            logger.info(
                "Connection %s self-healed pending→active (A-Cube returned %d accounts)",
                connection_id, len(remote_accounts),
            )

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
        # No hard fail on pending — sync_accounts self-heals first

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
                # A-Cube returns "transactionId" (snake/camel mix); fallback to "id" or "@id"
                acube_tx_id = (
                    tx_data.get("transactionId")
                    or tx_data.get("id")
                    or (tx_data.get("@id") or "").split("/")[-1]
                )
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

        # Auto-parse new transactions with rules-only (free, fast). LLM upgrade
        # è on-demand via /parse endpoint per non rallentare il sync.
        if tx_created > 0:
            try:
                from api.modules.banking.tx_ai_parser import parse_with_rules
                tenant_accounts = [a.id for a in accounts]
                unparsed = (
                    await self.db.execute(
                        select(BankTransaction).where(
                            BankTransaction.bank_account_id.in_(tenant_accounts),
                            BankTransaction.parsed_at.is_(None),
                        )
                    )
                ).scalars().all()
                for tx in unparsed:
                    res = parse_with_rules(tx.description, tx.direction, tx.amount or 0.0)
                    tx.parsed_counterparty = res.counterparty
                    tx.parsed_counterparty_iban = res.counterparty_iban
                    tx.parsed_invoice_ref = res.invoice_ref
                    tx.parsed_category = res.category
                    tx.parsed_subcategory = res.subcategory
                    tx.parsed_confidence = res.confidence
                    tx.parsed_method = res.method
                    tx.parsed_at = now
                await self.db.commit()
                logger.info("Auto-parsed %d new transactions (rules-only)", len(unparsed))
            except Exception as e:
                logger.warning("Auto-parse failed (non-blocking): %s", e)
        return {
            "connection_id": connection_id,
            "accounts_processed": len(accounts),
            "tx_created": tx_created,
            "tx_updated": tx_updated,
            "since": since.isoformat() if since else None,
            "until": until.isoformat() if until else None,
            "message": f"Sync transazioni: {tx_created} nuove, {tx_updated} aggiornate su {len(accounts)} conti",
        }

    # ── Parse AI (rules + LLM upgrade) ────────────────────

    async def parse_transactions(
        self,
        connection_id: uuid.UUID,
        tenant_id: uuid.UUID,
        *,
        force: bool = False,
        use_llm: bool = True,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """Esegui parsing AI sulle transazioni di una connection.

        Args:
            force: se True ri-parsa anche tx già parsate (escluse user_corrected)
            use_llm: se True applica fallback LLM per low-confidence (costo ~$0.0005/tx)
            limit: max transazioni da parsare in questa chiamata
        """
        from api.modules.banking.tx_ai_parser import parse_transaction

        conn = await self.get_connection(connection_id, tenant_id)

        # Carica tenant info per identità (LLM context)
        tenant_res = await self.db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = tenant_res.scalar_one_or_none()
        tenant_name = tenant.name if tenant else None
        tenant_piva = tenant.piva if tenant else None

        # Trova accounts della connection
        accounts = (
            await self.db.execute(
                select(BankAccount).where(BankAccount.acube_connection_id == conn.id)
            )
        ).scalars().all()
        account_ids = [a.id for a in accounts]
        if not account_ids:
            return {"connection_id": connection_id, "parsed": 0, "skipped": 0, "message": "Nessun conto"}

        # Query tx da parsare
        conditions = [BankTransaction.bank_account_id.in_(account_ids)]
        if not force:
            conditions.append(BankTransaction.parsed_at.is_(None))
        else:
            # Anche con force, NON sovrascrivere correzioni manuali
            conditions.append(BankTransaction.user_corrected == False)  # noqa: E712

        q = select(BankTransaction).where(and_(*conditions))
        if limit:
            q = q.limit(limit)
        txs = (await self.db.execute(q)).scalars().all()

        parsed_count = 0
        llm_count = 0
        rules_count = 0
        now = datetime.utcnow()

        for tx in txs:
            res = await parse_transaction(
                tx.description, tx.direction, tx.amount or 0.0, use_llm=use_llm,
                tenant_name=tenant_name, tenant_piva=tenant_piva,
            )
            tx.parsed_counterparty = res.counterparty
            tx.parsed_counterparty_iban = res.counterparty_iban
            tx.parsed_invoice_ref = res.invoice_ref
            tx.parsed_category = res.category
            tx.parsed_subcategory = res.subcategory
            tx.parsed_confidence = res.confidence
            tx.parsed_method = res.method
            tx.parsed_notes = res.notes
            tx.parsed_at = now
            parsed_count += 1
            if res.method == "llm":
                llm_count += 1
            else:
                rules_count += 1

        await self.db.commit()
        return {
            "connection_id": connection_id,
            "parsed": parsed_count,
            "rules_count": rules_count,
            "llm_count": llm_count,
            "use_llm": use_llm,
            "force": force,
            "message": f"Parsed {parsed_count} transazioni ({rules_count} rules, {llm_count} LLM)",
        }

    async def correct_transaction_parse(
        self,
        tx_id: uuid.UUID,
        tenant_id: uuid.UUID,
        *,
        counterparty: str | None = None,
        category: str | None = None,
        invoice_ref: str | None = None,
    ) -> BankTransaction:
        """Correzione manuale del parse — alza user_corrected=True (non sovrascritto da reparse).

        Anche scrive in CategorizationFeedback per future fine-tuning del parser.
        """
        # Trova la tx + verifica tenant ownership via account → connection
        tx_res = await self.db.execute(
            select(BankTransaction, BankAccount, BankConnection)
            .join(BankAccount, BankAccount.id == BankTransaction.bank_account_id)
            .outerjoin(BankConnection, BankConnection.id == BankAccount.acube_connection_id)
            .where(
                BankTransaction.id == tx_id,
                BankAccount.tenant_id == tenant_id,
            )
        )
        row = tx_res.first()
        if not row:
            raise ACubeOBServiceError("Transazione non trovata")
        tx: BankTransaction = row[0]

        if counterparty is not None:
            tx.parsed_counterparty = counterparty
        if category is not None:
            tx.parsed_category = category
        if invoice_ref is not None:
            tx.parsed_invoice_ref = invoice_ref
        tx.user_corrected = True
        tx.parsed_method = "manual"
        tx.parsed_confidence = 1.0
        tx.parsed_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(tx)
        return tx

    # ── Sync combinato accounts + transazioni ──────────────

    async def sync_now(
        self,
        connection_id: uuid.UUID,
        tenant_id: uuid.UUID,
        *,
        since: date | None = None,
        until: date | None = None,
    ) -> dict[str, Any]:
        """Comodità: esegue sync_accounts seguito da sync_transactions.

        Se since è None: usa connection.last_sync_at - 1gg (delta + safety overlap)
        oppure 30gg fa se è la prima sync.
        """
        acc_result = await self.sync_accounts(connection_id, tenant_id)

        # Smart default for `since`: delta from last sync of any account on this connection,
        # or None (which falls back to 30 days inside sync_transactions) if first sync
        if since is None:
            conn = await self.get_connection(connection_id, tenant_id)
            last_sync_row = (
                await self.db.execute(
                    select(BankAccount.last_sync_at)
                    .where(BankAccount.acube_connection_id == conn.id)
                    .order_by(BankAccount.last_sync_at.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()
            if last_sync_row:
                # Delta sync with 1-day overlap to catch late-posted transactions
                since = (last_sync_row - timedelta(days=1)).date()

        tx_result = await self.sync_transactions(
            connection_id, tenant_id, since=since, until=until
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
