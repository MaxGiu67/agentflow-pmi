"""State snapshots — router aggregato.

Espone un endpoint combinato /state/all che chiama tutti gli snapshot in parallelo
+ i 3 endpoint individuali.
"""

from __future__ import annotations

import asyncio
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from api.modules.state.banking_snapshot import BankingSnapshot, banking_snapshot
from api.modules.state.invoicing_snapshot import (
    InvoicingSnapshot,
    invoicing_snapshot,
)
from api.modules.state.sales_snapshot import SalesSnapshot, sales_snapshot

# Re-export individual routers
from api.modules.state.banking_snapshot import router as banking_router
from api.modules.state.invoicing_snapshot import router as invoicing_router
from api.modules.state.sales_snapshot import router as sales_router

router = APIRouter(prefix="/state", tags=["state"])


class FullSnapshot(BaseModel):
    snapshot_at: datetime
    banking: BankingSnapshot
    invoicing: InvoicingSnapshot
    sales: SalesSnapshot
    all_flags: list[str]


@router.get("/all", response_model=FullSnapshot)
async def full_snapshot(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FullSnapshot:
    """Snapshot combinato banking + invoicing + sales — eseguito in parallelo (asyncio.gather).

    Usato dagli agenti AI per ottenere stato completo del tenant in 1 sola chiamata
    HTTP. Le 3 query DB partono in concorrenza grazie a asyncio.gather.
    """
    if not user.tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Profilo azienda non configurato")

    # Esecuzione in parallelo — riduce latenza totale
    banking, invoicing, sales = await asyncio.gather(
        banking_snapshot(user=user, db=db),
        invoicing_snapshot(user=user, db=db),
        sales_snapshot(user=user, db=db),
    )

    all_flags = (banking.flags or []) + (invoicing.flags or []) + (sales.flags or [])

    return FullSnapshot(
        snapshot_at=datetime.utcnow(),
        banking=banking,
        invoicing=invoicing,
        sales=sales,
        all_flags=all_flags,
    )
