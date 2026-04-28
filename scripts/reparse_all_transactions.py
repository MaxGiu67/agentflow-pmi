"""One-shot: re-parsa tutte le transazioni di tutti i tenant col nuovo motore.

Lancio:
    railway run --service api python3 scripts/reparse_all_transactions.py

Idempotente. Skip-a transazioni con user_corrected=True (corrette a mano).
Aggiornamenti applicati: nuova logica fee/commissione_bonifico per piccoli
importi, keyword payroll/stipendi/compensi più ampie, prompt LLM rinforzato.
"""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select

from api.db.models import ACubeOBConnection
from api.db.session import async_session_factory
from api.modules.banking.acube_ob_service import ACubeOpenBankingService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("reparse")


async def main() -> int:
    async with async_session_factory() as db:
        conns = (
            await db.execute(
                select(ACubeOBConnection).order_by(ACubeOBConnection.created_at)
            )
        ).scalars().all()
        logger.info("Trovate %d connections totali", len(conns))

        service = ACubeOpenBankingService(db)
        grand_total = 0
        grand_rules = 0
        grand_llm = 0
        failures = 0

        for conn in conns:
            try:
                result = await service.parse_transactions(
                    connection_id=conn.id,
                    tenant_id=conn.tenant_id,
                    force=True,
                    use_llm=True,
                )
                logger.info(
                    "tenant=%s conn=%s → %s",
                    conn.tenant_id, conn.id, result.get("message"),
                )
                grand_total += result.get("parsed", 0)
                grand_rules += result.get("rules_count", 0)
                grand_llm += result.get("llm_count", 0)
            except Exception as e:  # noqa: BLE001
                logger.exception("FAIL tenant=%s conn=%s: %s", conn.tenant_id, conn.id, e)
                failures += 1

        logger.info("=" * 60)
        logger.info(
            "DONE — totale parsed=%d (rules=%d, llm=%d). Failures=%d/%d",
            grand_total, grand_rules, grand_llm, failures, len(conns),
        )
        return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
