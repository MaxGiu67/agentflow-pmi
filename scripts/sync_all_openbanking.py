#!/usr/bin/env python3
"""Sync batch di tutte le BankConnection A-Cube attive (Sprint 49 US-OB-08).

Pensato per essere eseguito da **Railway cron** (o cron locale) orario/giornaliero.

Uso:
    python3 scripts/sync_all_openbanking.py                # default: 30gg backfill, accounts+tx
    python3 scripts/sync_all_openbanking.py --only-tx      # salta sync accounts
    python3 scripts/sync_all_openbanking.py --since 2026-01-01

Exit code:
    0 = ok (anche se singola connection ha fallito — errori loggati, non fatali)
    1 = errore fatale (auth A-Cube, DB unreachable, ecc.)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import date, datetime
from pathlib import Path

# Aggiungi root repo al path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Carica .env
env_file = ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            v = v.strip().strip('"').strip("'")
            os.environ.setdefault(k.strip(), v)

from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from api.db.models import BankConnection  # noqa: E402
from api.db.session import async_session_factory  # noqa: E402
from api.modules.banking.acube_ob_service import (  # noqa: E402
    ACubeOBServiceError,
    ACubeOpenBankingService,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("sync_all_openbanking")


async def _sync_one(
    db: AsyncSession,
    conn: BankConnection,
    *,
    since: date | None,
    only_tx: bool,
) -> dict:
    service = ACubeOpenBankingService(db)
    tag = f"tenant={conn.tenant_id} fiscal_id={conn.fiscal_id}"
    try:
        if only_tx:
            result = await service.sync_transactions(conn.id, conn.tenant_id, since=since)
        else:
            result = await service.sync_now(conn.id, conn.tenant_id, since=since)
        logger.info("[OK] %s → %s", tag, result.get("message"))
        return {"connection_id": str(conn.id), "ok": True, "result": result}
    except ACubeOBServiceError as exc:
        logger.warning("[SKIP] %s → %s", tag, exc)
        return {"connection_id": str(conn.id), "ok": False, "error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        logger.exception("[FAIL] %s → %s", tag, exc)
        return {"connection_id": str(conn.id), "ok": False, "error": repr(exc)}


async def run(*, since: date | None, only_tx: bool) -> int:
    started_at = datetime.utcnow()
    processed: list[dict] = []
    expired_count = 0
    try:
        async with async_session_factory() as db:
            # Marca come expired le connection con consenso scaduto
            expired_count = await ACubeOpenBankingService(db).mark_expired_consents()
            if expired_count:
                logger.warning("Marcate %d connection come 'expired' (consenso scaduto)", expired_count)

            rows = (
                await db.execute(
                    select(BankConnection).where(BankConnection.status == "active")
                )
            ).scalars().all()

            logger.info("Connections attive: %d", len(rows))
            if not rows:
                print(json.dumps({"processed": 0, "items": []}))
                return 0

            for conn in rows:
                # Uso una session fresh per isolare gli errori della singola conn
                async with async_session_factory() as conn_db:
                    out = await _sync_one(conn_db, conn, since=since, only_tx=only_tx)
                    processed.append(out)
    except Exception as exc:  # noqa: BLE001
        logger.exception("FATAL: %s", exc)
        return 1

    ok = sum(1 for p in processed if p["ok"])
    failed = len(processed) - ok
    elapsed = (datetime.utcnow() - started_at).total_seconds()
    logger.info("Done — %d ok, %d failed, %d expired in %.1fs", ok, failed, expired_count, elapsed)
    print(
        json.dumps(
            {
                "processed": len(processed),
                "ok": ok,
                "failed": failed,
                "expired": expired_count,
                "items": processed,
            },
            default=str,
        )
    )
    return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", help="Backfill da questa data ISO (YYYY-MM-DD). Default: 30gg fa.")
    parser.add_argument(
        "--only-tx",
        action="store_true",
        help="Skip sync accounts, solo transazioni (più veloce in sync incrementale).",
    )
    args = parser.parse_args()

    since: date | None = None
    if args.since:
        try:
            since = date.fromisoformat(args.since)
        except ValueError:
            print(f"ERROR: --since non valido: {args.since}", file=sys.stderr)
            sys.exit(2)

    code = asyncio.run(run(since=since, only_tx=args.only_tx))
    sys.exit(code)


if __name__ == "__main__":
    main()
