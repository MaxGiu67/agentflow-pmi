"""Default Italian fiscal rules — seed data for the fiscal_rules table.

These are the baseline rules valid at the time of ADR-007 implementation.
Admin-editable rules will be added in a future sprint.
"""

import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import FiscalRule

logger = logging.getLogger(__name__)

DEFAULT_FISCAL_RULES: list[dict] = [
    {
        "key": "iva_ordinaria",
        "value": "0.22",
        "value_type": "decimal",
        "valid_from": date(2013, 10, 1),
        "law_reference": "DPR 633/72 art. 16",
    },
    {
        "key": "iva_ridotta",
        "value": "0.10",
        "value_type": "decimal",
        "valid_from": date(2013, 10, 1),
        "law_reference": "DPR 633/72 art. 16",
    },
    {
        "key": "iva_minima",
        "value": "0.04",
        "value_type": "decimal",
        "valid_from": date(2013, 10, 1),
        "law_reference": "DPR 633/72 art. 16",
    },
    {
        "key": "soglia_forfettario",
        "value": "85000",
        "value_type": "integer",
        "valid_from": date(2023, 1, 1),
        "law_reference": "L. 197/2022",
    },
    {
        "key": "soglia_bollo",
        "value": "77.47",
        "value_type": "decimal",
        "valid_from": date(2007, 1, 1),
        "law_reference": "DPR 642/72 Tariffa art. 13.1",
    },
    {
        "key": "bollo_importo",
        "value": "2.00",
        "value_type": "decimal",
        "valid_from": date(2007, 1, 1),
        "law_reference": "DPR 642/72",
    },
    {
        "key": "soglia_cespiti",
        "value": "516.46",
        "value_type": "decimal",
        "valid_from": date(2002, 1, 1),
        "law_reference": "DPR 917/86 art. 102",
    },
    {
        "key": "soglia_minima_versamento_iva",
        "value": "25.82",
        "value_type": "decimal",
        "valid_from": date(2001, 1, 1),
        "law_reference": "DPR 633/72",
    },
    {
        "key": "interessi_liquidazione_trimestrale",
        "value": "0.01",
        "value_type": "decimal",
        "valid_from": date(2001, 1, 1),
        "law_reference": "DPR 633/72 art. 7",
    },
    {
        "key": "ritenuta_standard_professionisti",
        "value": "0.20",
        "value_type": "decimal",
        "valid_from": date(2001, 1, 1),
        "law_reference": "DPR 600/73 art. 25",
    },
]


async def seed_fiscal_rules(db: AsyncSession) -> int:
    """Insert default fiscal rules if not already present.

    Returns the number of rules inserted.
    """
    inserted = 0
    for rule_data in DEFAULT_FISCAL_RULES:
        # Check if rule already exists for this key+valid_from combination
        existing = await db.execute(
            select(FiscalRule).where(
                FiscalRule.key == rule_data["key"],
                FiscalRule.valid_from == rule_data["valid_from"],
            )
        )
        if existing.scalar_one_or_none() is None:
            rule = FiscalRule(**rule_data)
            db.add(rule)
            inserted += 1

    if inserted:
        await db.flush()
        logger.info("Seeded %d fiscal rules", inserted)

    return inserted
