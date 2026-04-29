"""Re-esegue assign (modalità A-CUBE delega) + schedule per Qubika e TAAL.

Necessario dopo il fix Federico 2026-04-29: l'assign precedente usava
P.IVA 10442360961 invece di stringa "A-CUBE" come path-param.
"""

from __future__ import annotations
import asyncio
import logging
from sqlalchemy import select

from api.adapters.acube_scarico_massivo import (
    ACUBE_PROXY_APPOINTEE_ID,
    ACubeScaricoMassivoClient,
)
from api.db.models import ScaricoMassivoConfig
from api.db.session import async_session_factory

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("fix-assign")

TENANT_PIVAS = ["12136821001", "16966051001"]  # TAAL, Qubika


async def main() -> int:
    async with async_session_factory() as db:
        cfgs = (
            await db.execute(
                select(ScaricoMassivoConfig).where(
                    ScaricoMassivoConfig.client_fiscal_id.in_(TENANT_PIVAS)
                )
            )
        ).scalars().all()
        log.info("Trovate %d config (target: TAAL+Qubika)", len(cfgs))

        client = ACubeScaricoMassivoClient()

        for cfg in cfgs:
            piva = cfg.client_fiscal_id
            log.info("=" * 50)
            log.info("Processo P.IVA %s (%s)", piva, cfg.tenant_id)

            # Step 1 — POST /ade-appointees/A-CUBE/assign
            try:
                r1 = await client.assign_to_appointee(
                    appointee_fiscal_id=ACUBE_PROXY_APPOINTEE_ID,
                    client_fiscal_id=piva,
                )
                log.info("✓ assign A-CUBE → %s OK: keys=%s", piva, list(r1.keys())[:6])
            except Exception as e:
                log.exception("✗ assign FAIL %s: %s", piva, e)
                continue

            # Step 2 — POST /schedule/invoice-download/{piva} con archive=true
            try:
                r2 = await client.schedule_daily_download(piva, download_archive=True)
                log.info("✓ schedule daily archive=true %s OK: keys=%s", piva, list(r2.keys())[:6])
            except Exception as e:
                log.exception("✗ schedule FAIL %s: %s", piva, e)
                continue

            # Step 3 — verifica status
            try:
                r3 = await client.get_schedule_status(piva)
                log.info(
                    "  schedule status %s: enabled=%s valid_until=%s auto_renew=%s",
                    piva,
                    r3.get("enabled"),
                    r3.get("valid_until"),
                    r3.get("auto_renew"),
                )
            except Exception as e:
                log.warning("get_schedule_status %s: %s", piva, e)

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
