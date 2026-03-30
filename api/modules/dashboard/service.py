"""Service layer for dashboard module."""

import logging
import uuid

from sqlalchemy import select, and_, func, text, extract
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import AgentEvent, Invoice, User

logger = logging.getLogger(__name__)


class DashboardService:
    """Service for dashboard operations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_summary(self, user: User) -> dict:
        """Get complete dashboard summary."""
        if not user.tenant_id:
            return {
                "counters": {
                    "total": 0,
                    "pending": 0,
                    "parsed": 0,
                    "categorized": 0,
                    "registered": 0,
                    "error": 0,
                },
                "recent_invoices": [],
                "agents": await self._get_agent_statuses(None),
                "last_sync_at": None,
                "message": "Nessuna fattura presente. Collega il cassetto fiscale per iniziare.",
            }

        tenant_id = user.tenant_id

        # Counters by status
        counters = await self._get_counters(tenant_id)

        # Recent 10 invoices
        recent_result = await self.db.execute(
            select(Invoice)
            .where(Invoice.tenant_id == tenant_id)
            .order_by(Invoice.created_at.desc())
            .limit(10)
        )
        recent_invoices = recent_result.scalars().all()

        # Last sync
        last_sync_result = await self.db.execute(
            select(Invoice.created_at)
            .where(
                and_(
                    Invoice.tenant_id == tenant_id,
                    Invoice.source == "cassetto_fiscale",
                )
            )
            .order_by(Invoice.created_at.desc())
            .limit(1)
        )
        last_sync_at = last_sync_result.scalar_one_or_none()

        # Agent statuses
        agents = await self._get_agent_statuses(tenant_id)

        # Message
        if counters["total"] == 0:
            message = "Nessuna fattura presente. Collega il cassetto fiscale per iniziare."
        else:
            message = f"{counters['total']} fatture totali, {counters['pending']} in attesa di elaborazione"

        return {
            "counters": counters,
            "recent_invoices": recent_invoices,
            "agents": agents,
            "last_sync_at": last_sync_at,
            "message": message,
        }

    async def _get_counters(self, tenant_id: uuid.UUID) -> dict:
        """Get invoice counters by processing status."""
        statuses = ["pending", "parsed", "categorized", "registered", "error"]
        counters = {"total": 0}

        for s in statuses:
            result = await self.db.execute(
                select(func.count(Invoice.id)).where(
                    and_(
                        Invoice.tenant_id == tenant_id,
                        Invoice.processing_status == s,
                    )
                )
            )
            count = result.scalar() or 0
            counters[s] = count
            counters["total"] += count

        return counters

    async def _get_agent_statuses(self, tenant_id: uuid.UUID | None) -> list[dict]:
        """Get agent statuses from recent events."""
        agent_names = ["fisco_agent", "parser_agent", "learning_agent"]
        statuses = []

        for agent_name in agent_names:
            if tenant_id is None:
                statuses.append({
                    "name": agent_name,
                    "status": "idle",
                    "last_run": None,
                    "events_published": 0,
                    "events_failed": 0,
                })
                continue

            # Last event
            last_event_result = await self.db.execute(
                select(AgentEvent.created_at)
                .where(
                    and_(
                        AgentEvent.tenant_id == tenant_id,
                        AgentEvent.agent_name == agent_name,
                    )
                )
                .order_by(AgentEvent.created_at.desc())
                .limit(1)
            )
            last_run = last_event_result.scalar_one_or_none()

            # Published events count
            published_result = await self.db.execute(
                select(func.count(AgentEvent.id)).where(
                    and_(
                        AgentEvent.tenant_id == tenant_id,
                        AgentEvent.agent_name == agent_name,
                        AgentEvent.status == "published",
                    )
                )
            )
            events_published = published_result.scalar() or 0

            # Failed events count
            failed_result = await self.db.execute(
                select(func.count(AgentEvent.id)).where(
                    and_(
                        AgentEvent.tenant_id == tenant_id,
                        AgentEvent.agent_name == agent_name,
                        AgentEvent.status == "dead_letter",
                    )
                )
            )
            events_failed = failed_result.scalar() or 0

            agent_status = "idle"
            if last_run:
                agent_status = "active"

            statuses.append({
                "name": agent_name,
                "status": agent_status,
                "last_run": last_run,
                "events_published": events_published,
                "events_failed": events_failed,
            })

        return statuses

    async def get_agent_statuses(self, user: User) -> list[dict]:
        """Get agent statuses for the user's tenant."""
        return await self._get_agent_statuses(user.tenant_id)

    async def get_yearly_stats(self, user: User, year: int) -> dict:
        """Get yearly statistics for the dashboard."""
        tenant_id = user.tenant_id
        if not tenant_id:
            return self._empty_yearly_stats(year)

        # Detect DB dialect for JSON access syntax and UUID format
        dialect = self.db.bind.dialect.name if self.db.bind else "postgresql"
        is_sqlite = dialect == "sqlite"

        # SQLite stores UUIDs as hex without dashes; PostgreSQL uses dashed format
        tid = tenant_id.hex if is_sqlite else str(tenant_id)

        # --- Fatture attive aggregate ---
        attive_result = await self.db.execute(
            select(
                func.count(Invoice.id).label("count"),
                func.coalesce(func.sum(Invoice.importo_totale), 0.0).label("totale"),
                func.coalesce(func.sum(Invoice.importo_netto), 0.0).label("imponibile"),
                func.coalesce(func.sum(Invoice.importo_iva), 0.0).label("iva"),
            ).where(
                and_(
                    Invoice.tenant_id == tenant_id,
                    Invoice.type == "attiva",
                    extract("year", Invoice.data_fattura) == year,
                )
            )
        )
        att = attive_result.one()
        fatture_attive = {
            "count": att.count or 0,
            "totale": round(float(att.totale), 2),
            "imponibile": round(float(att.imponibile), 2),
            "iva": round(float(att.iva), 2),
        }

        # --- Fatture passive aggregate ---
        passive_result = await self.db.execute(
            select(
                func.count(Invoice.id).label("count"),
                func.coalesce(func.sum(Invoice.importo_totale), 0.0).label("totale"),
                func.coalesce(func.sum(Invoice.importo_netto), 0.0).label("imponibile"),
                func.coalesce(func.sum(Invoice.importo_iva), 0.0).label("iva"),
            ).where(
                and_(
                    Invoice.tenant_id == tenant_id,
                    Invoice.type == "passiva",
                    extract("year", Invoice.data_fattura) == year,
                )
            )
        )
        pas = passive_result.one()
        fatture_passive = {
            "count": pas.count or 0,
            "totale": round(float(pas.totale), 2),
            "imponibile": round(float(pas.imponibile), 2),
            "iva": round(float(pas.iva), 2),
        }

        margine_lordo = round(fatture_attive["totale"] - fatture_passive["totale"], 2)

        # --- Top 10 clienti (from attiva invoices, client in structured_data) ---
        if is_sqlite:
            top_clienti_sql = text("""
                SELECT
                    json_extract(structured_data, '$.destinatario_nome') as nome,
                    json_extract(structured_data, '$.destinatario_piva') as piva,
                    SUM(importo_totale) as totale,
                    COUNT(*) as count
                FROM invoices
                WHERE tenant_id = :tid
                  AND type = 'attiva'
                  AND CAST(strftime('%Y', data_fattura) AS INTEGER) = :year
                  AND structured_data IS NOT NULL
                GROUP BY nome, piva
                ORDER BY totale DESC
                LIMIT 10
            """)
        else:
            top_clienti_sql = text("""
                SELECT
                    structured_data->>'destinatario_nome' as nome,
                    structured_data->>'destinatario_piva' as piva,
                    SUM(importo_totale) as totale,
                    COUNT(*) as count
                FROM invoices
                WHERE tenant_id = :tid
                  AND type = 'attiva'
                  AND EXTRACT(YEAR FROM data_fattura) = :year
                  AND structured_data IS NOT NULL
                GROUP BY structured_data->>'destinatario_nome',
                         structured_data->>'destinatario_piva'
                ORDER BY totale DESC
                LIMIT 10
            """)

        clienti_result = await self.db.execute(top_clienti_sql, {"tid": tid, "year": year})
        top_clienti = [
            {
                "nome": row.nome or "Sconosciuto",
                "piva": row.piva or "",
                "totale": round(float(row.totale or 0), 2),
                "count": int(row.count or 0),
            }
            for row in clienti_result.fetchall()
        ]

        # --- Top 10 fornitori (from passiva invoices, emittente fields) ---
        if is_sqlite:
            top_fornitori_sql = text("""
                SELECT
                    emittente_nome as nome,
                    emittente_piva as piva,
                    SUM(importo_totale) as totale,
                    COUNT(*) as count
                FROM invoices
                WHERE tenant_id = :tid
                  AND type = 'passiva'
                  AND CAST(strftime('%Y', data_fattura) AS INTEGER) = :year
                GROUP BY emittente_nome, emittente_piva
                ORDER BY totale DESC
                LIMIT 10
            """)
        else:
            top_fornitori_sql = text("""
                SELECT
                    emittente_nome as nome,
                    emittente_piva as piva,
                    SUM(importo_totale) as totale,
                    COUNT(*) as count
                FROM invoices
                WHERE tenant_id = :tid
                  AND type = 'passiva'
                  AND EXTRACT(YEAR FROM data_fattura) = :year
                GROUP BY emittente_nome, emittente_piva
                ORDER BY totale DESC
                LIMIT 10
            """)

        fornitori_result = await self.db.execute(top_fornitori_sql, {"tid": tid, "year": year})
        top_fornitori = [
            {
                "nome": row.nome or "Sconosciuto",
                "piva": row.piva or "",
                "totale": round(float(row.totale or 0), 2),
                "count": int(row.count or 0),
            }
            for row in fornitori_result.fetchall()
        ]

        # --- Fatture per mese ---
        if is_sqlite:
            per_mese_sql = text("""
                SELECT
                    CAST(strftime('%m', data_fattura) AS INTEGER) as mese,
                    SUM(CASE WHEN type = 'attiva' THEN 1 ELSE 0 END) as attive_count,
                    SUM(CASE WHEN type = 'attiva' THEN importo_totale ELSE 0 END) as attive_totale,
                    SUM(CASE WHEN type = 'passiva' THEN 1 ELSE 0 END) as passive_count,
                    SUM(CASE WHEN type = 'passiva' THEN importo_totale ELSE 0 END) as passive_totale
                FROM invoices
                WHERE tenant_id = :tid
                  AND CAST(strftime('%Y', data_fattura) AS INTEGER) = :year
                GROUP BY mese
                ORDER BY mese
            """)
        else:
            per_mese_sql = text("""
                SELECT
                    EXTRACT(MONTH FROM data_fattura)::int as mese,
                    SUM(CASE WHEN type = 'attiva' THEN 1 ELSE 0 END) as attive_count,
                    SUM(CASE WHEN type = 'attiva' THEN importo_totale ELSE 0 END) as attive_totale,
                    SUM(CASE WHEN type = 'passiva' THEN 1 ELSE 0 END) as passive_count,
                    SUM(CASE WHEN type = 'passiva' THEN importo_totale ELSE 0 END) as passive_totale
                FROM invoices
                WHERE tenant_id = :tid
                  AND EXTRACT(YEAR FROM data_fattura) = :year
                GROUP BY mese
                ORDER BY mese
            """)

        mese_result = await self.db.execute(per_mese_sql, {"tid": tid, "year": year})
        mese_map: dict[int, dict] = {}
        for row in mese_result.fetchall():
            mese_map[int(row.mese)] = {
                "mese": int(row.mese),
                "attive_count": int(row.attive_count),
                "attive_totale": round(float(row.attive_totale or 0), 2),
                "passive_count": int(row.passive_count),
                "passive_totale": round(float(row.passive_totale or 0), 2),
            }

        fatture_per_mese = []
        for m in range(1, 13):
            if m in mese_map:
                fatture_per_mese.append(mese_map[m])
            else:
                fatture_per_mese.append({
                    "mese": m,
                    "attive_count": 0,
                    "attive_totale": 0.0,
                    "passive_count": 0,
                    "passive_totale": 0.0,
                })

        # --- Available years ---
        if is_sqlite:
            years_sql = text("""
                SELECT DISTINCT CAST(strftime('%Y', data_fattura) AS INTEGER) as anno
                FROM invoices
                WHERE tenant_id = :tid AND data_fattura IS NOT NULL
                ORDER BY anno
            """)
        else:
            years_sql = text("""
                SELECT DISTINCT EXTRACT(YEAR FROM data_fattura)::int as anno
                FROM invoices
                WHERE tenant_id = :tid AND data_fattura IS NOT NULL
                ORDER BY anno
            """)

        years_result = await self.db.execute(years_sql, {"tid": tid})
        available_years = [int(row.anno) for row in years_result.fetchall()]

        return {
            "year": year,
            "fatture_attive": fatture_attive,
            "fatture_passive": fatture_passive,
            "margine_lordo": margine_lordo,
            "top_clienti": top_clienti,
            "top_fornitori": top_fornitori,
            "fatture_per_mese": fatture_per_mese,
            "available_years": available_years,
        }

    def _empty_yearly_stats(self, year: int) -> dict:
        """Return empty yearly stats for users without a tenant."""
        return {
            "year": year,
            "fatture_attive": {"count": 0, "totale": 0.0, "imponibile": 0.0, "iva": 0.0},
            "fatture_passive": {"count": 0, "totale": 0.0, "imponibile": 0.0, "iva": 0.0},
            "margine_lordo": 0.0,
            "top_clienti": [],
            "top_fornitori": [],
            "fatture_per_mese": [
                {"mese": m, "attive_count": 0, "attive_totale": 0.0, "passive_count": 0, "passive_totale": 0.0}
                for m in range(1, 13)
            ],
            "available_years": [],
        }
