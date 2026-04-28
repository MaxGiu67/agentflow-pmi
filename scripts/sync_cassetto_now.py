"""Force sync di tutte le config Scarico Massivo attive — per check stato scarico."""
from __future__ import annotations
import asyncio, logging
from sqlalchemy import select
from api.db.models import ScaricoMassivoConfig
from api.db.session import async_session_factory
from api.modules.scarico_massivo.service import ScaricoMassivoService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("sync-cassetto")

async def main() -> int:
    async with async_session_factory() as db:
        cfgs = (
            await db.execute(
                select(ScaricoMassivoConfig).where(ScaricoMassivoConfig.status == "active")
            )
        ).scalars().all()
        log.info("Trovate %d config attive", len(cfgs))
        service = ScaricoMassivoService(db)
        for cfg in cfgs:
            try:
                r = await service.sync_now(config_id=cfg.id, tenant_id=cfg.tenant_id)
                log.info(
                    "tenant=%s piva=%s → new=%s scanned=%s err=%s msg=%s",
                    cfg.tenant_id, cfg.client_fiscal_id,
                    r.get("new_invoices"), r.get("total_scanned"), r.get("errors"),
                    (r.get("message") or "")[:100],
                )
            except Exception as e:
                log.exception("FAIL %s: %s", cfg.client_fiscal_id, e)
    return 0

if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
