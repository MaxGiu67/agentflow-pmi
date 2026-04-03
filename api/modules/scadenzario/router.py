"""Router for Scadenzario module (US-72 to US-77)."""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user

from .schemas import GenerateResponse, ScadenzarioResponse
from .service import ScadenzarioService


class ChiudiScadenzaRequest(BaseModel):
    importo_pagato: float
    data_pagamento: date


class SegnaInsolitoResponse(BaseModel):
    id: str
    stato: str
    controparte: str | None = None
    warning: str | None = None
    anticipo_id: str | None = None
    error: str | None = None

router = APIRouter(prefix="/api/v1", tags=["scadenzario"])


def get_service(db: AsyncSession = Depends(get_db)) -> ScadenzarioService:
    return ScadenzarioService(db)


@router.post("/scadenzario/generate", response_model=GenerateResponse)
async def generate_scadenze(
    user: User = Depends(get_current_user),
    service: ScadenzarioService = Depends(get_service),
):
    """US-72: Generate scadenze for all invoices without one."""
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )
    count = await service.generate_all_missing(user.tenant_id)
    return GenerateResponse(
        generated=count,
        message=f"{count} scadenze generate",
    )


@router.get("/scadenzario/attivo", response_model=ScadenzarioResponse)
async def list_scadenzario_attivo(
    stato: str | None = Query(None, description="Filtro stato: aperto, pagato, insoluto, parziale"),
    controparte: str | None = Query(None, description="Filtro controparte (ricerca parziale)"),
    data_da: date | None = Query(None, description="Data scadenza da"),
    data_a: date | None = Query(None, description="Data scadenza a"),
    user: User = Depends(get_current_user),
    service: ScadenzarioService = Depends(get_service),
):
    """US-73: List scadenzario attivo (crediti da incassare)."""
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )
    return await service.list_attivo(
        user.tenant_id, stato=stato, controparte=controparte,
        data_da=data_da, data_a=data_a,
    )


@router.get("/scadenzario/passivo", response_model=ScadenzarioResponse)
async def list_scadenzario_passivo(
    stato: str | None = Query(None, description="Filtro stato: aperto, pagato, insoluto, parziale"),
    controparte: str | None = Query(None, description="Filtro controparte (ricerca parziale)"),
    data_da: date | None = Query(None, description="Data scadenza da"),
    data_a: date | None = Query(None, description="Data scadenza a"),
    user: User = Depends(get_current_user),
    service: ScadenzarioService = Depends(get_service),
):
    """US-74: List scadenzario passivo (debiti da pagare)."""
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )
    return await service.list_passivo(
        user.tenant_id, stato=stato, controparte=controparte,
        data_da=data_da, data_a=data_a,
    )


@router.post("/scadenzario/{scadenza_id}/chiudi")
async def chiudi_scadenza(
    scadenza_id: uuid.UUID,
    request: ChiudiScadenzaRequest,
    user: User = Depends(get_current_user),
    service: ScadenzarioService = Depends(get_service),
):
    """US-75: Close a scadenza (full or partial payment)."""
    result = await service.chiudi_scadenza(
        scadenza_id, request.importo_pagato, request.data_pagamento,
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/scadenzario/{scadenza_id}/insoluto")
async def segna_insoluto(
    scadenza_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: ScadenzarioService = Depends(get_service),
):
    """US-76: Mark a scadenza as insoluto."""
    result = await service.segna_insoluto(scadenza_id)
    if "error" in result:
        raise HTTPException(
            status_code=400 if "non valido" in result.get("error", "") else 404,
            detail=result["error"],
        )
    return result


@router.get("/scadenzario/cash-flow")
async def get_cash_flow(
    giorni: int = Query(30, description="Orizzonte previsionale: 30, 60, 90"),
    soglia_alert: float | None = Query(None, description="Soglia liquidità per alert"),
    user: User = Depends(get_current_user),
    service: ScadenzarioService = Depends(get_service),
):
    """US-77: Cash flow previsionale da scadenzario."""
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )
    return await service.cash_flow_previsionale(
        user.tenant_id, giorni=giorni, soglia_alert=soglia_alert,
    )


@router.get("/scadenzario/cash-flow/per-banca")
async def get_cash_flow_per_banca(
    giorni: int = Query(30, description="Orizzonte previsionale"),
    user: User = Depends(get_current_user),
    service: ScadenzarioService = Depends(get_service),
):
    """US-78: Cash flow per banca."""
    if not user.tenant_id:
        raise HTTPException(status_code=400, detail="Profilo azienda non configurato")
    return await service.cash_flow_per_banca(user.tenant_id, giorni=giorni)


@router.get("/fidi")
async def list_fidi(
    user: User = Depends(get_current_user),
    service: ScadenzarioService = Depends(get_service),
):
    """US-79: List fidi bancari con plafond/utilizzato/disponibile."""
    if not user.tenant_id:
        raise HTTPException(status_code=400, detail="Profilo azienda non configurato")
    return await service.list_fidi(user.tenant_id)


class CreateFidoRequest(BaseModel):
    bank_account_id: str
    tipo: str = "anticipo_fatture"
    plafond: float
    percentuale_anticipo: float = 80.0
    tasso_interesse_annuo: float = 0.0
    commissione_presentazione_pct: float = 0.0
    commissione_incasso: float = 0.0
    commissione_insoluto: float = 0.0
    giorni_max: int = 120


@router.post("/fidi")
async def create_fido(
    request: CreateFidoRequest,
    user: User = Depends(get_current_user),
    service: ScadenzarioService = Depends(get_service),
):
    """US-79: Create fido bancario."""
    if not user.tenant_id:
        raise HTTPException(status_code=400, detail="Profilo azienda non configurato")
    return await service.create_fido(user.tenant_id, request.model_dump())


@router.get("/scadenzario/{scadenza_id}/confronta-anticipi")
async def confronta_anticipi(
    scadenza_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: ScadenzarioService = Depends(get_service),
):
    """US-83: Compare advance costs across banks."""
    return await service.confronta_anticipi(scadenza_id)


@router.post("/scadenzario/{scadenza_id}/anticipa")
async def presenta_anticipo(
    scadenza_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: ScadenzarioService = Depends(get_service),
):
    """US-80: Present invoice for advance."""
    result = await service.presenta_anticipo(scadenza_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


class IncassoAnticipoRequest(BaseModel):
    data_incasso: date


@router.post("/anticipi/{anticipo_id}/incassa")
async def incassa_anticipo(
    anticipo_id: uuid.UUID,
    request: IncassoAnticipoRequest,
    user: User = Depends(get_current_user),
    service: ScadenzarioService = Depends(get_service),
):
    """US-81: Close advance after client payment."""
    result = await service.incassa_anticipo(anticipo_id, request.data_incasso)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/anticipi/{anticipo_id}/insoluto")
async def insoluto_anticipo(
    anticipo_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: ScadenzarioService = Depends(get_service),
):
    """US-82: Handle advance on unpaid invoice."""
    result = await service.insoluto_anticipo(anticipo_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result
