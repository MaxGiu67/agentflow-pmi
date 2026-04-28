"""Probe A-Cube per capire se ha le transazioni recenti che mancano in DB.

Chiama direttamente list_transactions per ogni account collegato e
mostra quante tx sono visibili negli ultimi 30gg.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta

from sqlalchemy import select

from api.adapters.acube_ob import ACubeOpenBankingClient
from api.db.models import BankAccount, BankConnection
from api.db.session import async_session_factory

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("probe")


async def main() -> int:
    async with async_session_factory() as db:
        accounts = (
            await db.execute(select(BankAccount).where(BankAccount.status == "connected"))
        ).scalars().all()
        log.info("Trovati %d account collegati", len(accounts))

        client = ACubeOpenBankingClient()
        since = (date.today() - timedelta(days=45)).isoformat()
        log.info("Range richiesta A-Cube: %s → today", since)

        for acc in accounts:
            if not acc.acube_uuid:
                log.info("SKIP %s — niente acube_uuid", acc.iban)
                continue

            conn = (
                await db.execute(
                    select(BankConnection).where(BankConnection.id == acc.acube_connection_id)
                )
            ).scalar_one_or_none()
            if not conn:
                log.info("SKIP %s — niente connection", acc.iban)
                continue

            try:
                txs = await client.list_transactions(
                    conn.fiscal_id,
                    account_uuid=acc.acube_uuid,
                    made_on_after=since,
                )
                dates = sorted({t.get("madeOn") for t in txs if t.get("madeOn")})
                log.info(
                    "iban=%s bank=%s → %d tx, range madeOn=[%s ... %s]",
                    acc.iban, acc.bank_name, len(txs),
                    dates[0] if dates else "—",
                    dates[-1] if dates else "—",
                )
                # Stampa le 5 più recenti
                txs_sorted = sorted(
                    txs, key=lambda t: t.get("madeOn") or "", reverse=True
                )
                for t in txs_sorted[:5]:
                    log.info(
                        "  %s amt=%s status=%s desc=%s",
                        t.get("madeOn"),
                        t.get("amount"),
                        t.get("status"),
                        (t.get("description") or "")[:60],
                    )
            except Exception as e:  # noqa: BLE001
                log.exception("FAIL %s: %s", acc.iban, e)

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
