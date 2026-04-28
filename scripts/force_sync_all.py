"""Force sync_now per tutte le connections — bypassa il delta del frontend."""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select

from api.db.models import BankConnection
from api.db.session import async_session_factory
from api.modules.banking.acube_ob_service import ACubeOpenBankingService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("force-sync")


async def main() -> int:
    async with async_session_factory() as db:
        conns = (
            await db.execute(select(BankConnection).where(BankConnection.status.in_(["connected", "active"])))
        ).scalars().all()
        log.info("Trovate %d connections attive", len(conns))

        service = ACubeOpenBankingService(db)
        for conn in conns:
            try:
                result = await service.sync_now(conn.id, conn.tenant_id)
                log.info(
                    "tenant=%s conn=%s → tx_created=%d tx_updated=%d msg=%s",
                    conn.tenant_id, conn.id,
                    result.get("tx_created", 0),
                    result.get("tx_updated", 0),
                    result.get("message", "")[:120],
                )
            except Exception as e:  # noqa: BLE001
                log.exception("FAIL conn=%s: %s", conn.id, e)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
