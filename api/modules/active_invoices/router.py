"""Router for active invoices / fatturazione attiva SDI (US-21)."""

from uuid import UUID

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from api.modules.active_invoices.schemas import (
    ActiveInvoiceCreate,
    ActiveInvoiceCreateLegacy,
    ActiveInvoiceListResponse,
    ActiveInvoiceResponse,
    ActiveInvoiceSendResponse,
    ActiveInvoiceStatusResponse,
)
from api.modules.active_invoices.service import ActiveInvoiceService

router = APIRouter(prefix="/invoices/active", tags=["active_invoices"])


def get_service(db: AsyncSession = Depends(get_db)) -> ActiveInvoiceService:
    return ActiveInvoiceService(db)


@router.post("", response_model=ActiveInvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_active_invoice(
    request: ActiveInvoiceCreate,
    user: User = Depends(get_current_user),
    service: ActiveInvoiceService = Depends(get_service),
) -> ActiveInvoiceResponse:
    """Create a new active invoice with multi-line items (US-41).

    Generates full FatturaPA v1.2.2 XML with Sede, RegimeFiscale, DatiPagamento.
    """
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    try:
        result = await service.create_invoice_multiline(
            tenant_id=user.tenant_id,
            cliente=request.cliente.model_dump(),
            linee=[l.model_dump() for l in request.linee],
            data_fattura=request.data_fattura,
            document_type=request.document_type,
            causale=request.causale,
            modalita_pagamento=request.modalita_pagamento,
            condizioni_pagamento=request.condizioni_pagamento,
            giorni_pagamento=request.giorni_pagamento,
            iban=request.iban,
            original_invoice_numero=request.original_invoice_numero,
            original_invoice_date=request.original_invoice_date,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return ActiveInvoiceResponse(**result)


@router.post("/legacy", response_model=ActiveInvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_active_invoice_legacy(
    request: ActiveInvoiceCreateLegacy,
    user: User = Depends(get_current_user),
    service: ActiveInvoiceService = Depends(get_service),
) -> ActiveInvoiceResponse:
    """Legacy single-line create (backward compatible)."""
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    try:
        result = await service.create_invoice(
            tenant_id=user.tenant_id,
            data=request.model_dump(),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return ActiveInvoiceResponse(**result)


@router.post("/{invoice_id}/send", response_model=ActiveInvoiceSendResponse)
async def send_to_sdi(
    invoice_id: UUID,
    user: User = Depends(get_current_user),
    service: ActiveInvoiceService = Depends(get_service),
) -> ActiveInvoiceSendResponse:
    """Send an active invoice to SDI via A-Cube."""
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    try:
        result = await service.send_to_sdi(invoice_id, user.tenant_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return ActiveInvoiceSendResponse(**result)


@router.get("/{invoice_id}/status", response_model=ActiveInvoiceStatusResponse)
async def get_sdi_status(
    invoice_id: UUID,
    user: User = Depends(get_current_user),
    service: ActiveInvoiceService = Depends(get_service),
) -> ActiveInvoiceStatusResponse:
    """Get SDI delivery status for an active invoice."""
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    try:
        result = await service.get_sdi_status(invoice_id, user.tenant_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    return ActiveInvoiceStatusResponse(**result)


@router.get("", response_model=ActiveInvoiceListResponse)
async def list_active_invoices(
    user: User = Depends(get_current_user),
    service: ActiveInvoiceService = Depends(get_service),
) -> ActiveInvoiceListResponse:
    """List all active invoices for the tenant."""
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profilo azienda non configurato",
        )

    items = await service.list_invoices(user.tenant_id)
    return ActiveInvoiceListResponse(
        items=[ActiveInvoiceResponse(**i) for i in items],
        total=len(items),
    )


@router.get("/{invoice_id}/pdf")
async def get_invoice_pdf(
    invoice_id: UUID,
    user: User = Depends(get_current_user),
    service: ActiveInvoiceService = Depends(get_service),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Generate and return PDF courtesy copy (copia di cortesia) for an invoice (US-43)."""
    if not user.tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Profilo azienda non configurato")

    inv = await service.get_invoice(invoice_id, user.tenant_id)
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fattura non trovata")

    # Get tenant for emittente data
    from sqlalchemy import select
    from api.db.models import Tenant
    result = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tenant non trovato")

    sede_emit = None
    if tenant.sede_indirizzo:
        parts = [tenant.sede_indirizzo]
        if tenant.sede_numero_civico:
            parts[0] += f" {tenant.sede_numero_civico}"
        parts.append(f"{tenant.sede_cap or ''} {tenant.sede_comune or ''} ({tenant.sede_provincia or ''})")
        sede_emit = ", ".join(parts)

    # Build line items from raw_xml or single-line fallback
    linee = [{"descrizione": inv["descrizione"] or "Prestazione", "quantita": 1, "prezzo_unitario": inv["importo_netto"], "aliquota_iva": inv["aliquota_iva"]}]

    # Scadenza
    from datetime import date as date_type
    data_f = inv["data_fattura"]
    if isinstance(data_f, str):
        data_f = date_type.fromisoformat(data_f)
    gg = tenant.giorni_pagamento or 30
    scadenza = (data_f + timedelta(days=gg)).strftime("%d/%m/%Y")

    from api.modules.active_invoices.pdf_generator import generate_courtesy_pdf
    pdf_bytes = generate_courtesy_pdf(
        tenant_name=tenant.name,
        tenant_piva=tenant.piva or "",
        tenant_sede=sede_emit,
        tenant_email=tenant.email_aziendale,
        tenant_pec=tenant.pec,
        tenant_telefono=tenant.telefono,
        numero_fattura=inv["numero_fattura"],
        data_fattura=data_f,
        document_type=inv["document_type"],
        cliente_nome=inv["cliente_nome"],
        cliente_piva=inv["cliente_piva"],
        cliente_sede=None,
        linee=linee,
        importo_netto=inv["importo_netto"],
        importo_iva=inv["importo_iva"],
        importo_totale=inv["importo_totale"],
        modalita_pagamento=tenant.modalita_pagamento,
        iban=tenant.iban,
        banca_nome=tenant.banca_nome,
        scadenza_pagamento=scadenza,
    )

    filename = f"Fattura_{inv['numero_fattura'].replace('/', '-')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
