"""Router for payroll/personnel costs (US-44)."""

import os
import subprocess
import tempfile
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from api.modules.payroll.schemas import (
    PayrollCostCreate,
    PayrollCostListResponse,
    PayrollCostResponse,
    PayrollSummaryResponse,
)
from api.modules.payroll.service import PayrollService

router = APIRouter(prefix="/payroll", tags=["payroll"])


def get_service(db: AsyncSession = Depends(get_db)) -> PayrollService:
    return PayrollService(db)


@router.post("", response_model=PayrollCostResponse, status_code=status.HTTP_201_CREATED)
async def create_payroll_cost(
    request: PayrollCostCreate,
    user: User = Depends(get_current_user),
    service: PayrollService = Depends(get_service),
) -> PayrollCostResponse:
    """Create a payroll cost entry (cedolino/stipendio)."""
    if not user.tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Profilo azienda non configurato")
    result = await service.create(user.tenant_id, request.model_dump())
    return PayrollCostResponse(**result)


@router.get("", response_model=PayrollCostListResponse)
async def list_payroll_costs(
    year: int | None = None,
    month: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    service: PayrollService = Depends(get_service),
) -> PayrollCostListResponse:
    """List payroll costs with optional year/month filter."""
    if not user.tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Profilo azienda non configurato")
    data = await service.list_costs(user.tenant_id, year=year, month=month, page=page, page_size=page_size)
    return PayrollCostListResponse(
        items=[PayrollCostResponse(**i) for i in data["items"]],
        total=data["total"],
    )


@router.get("/summary", response_model=PayrollSummaryResponse)
async def get_payroll_summary(
    year: int = Query(..., description="Anno di riferimento"),
    user: User = Depends(get_current_user),
    service: PayrollService = Depends(get_service),
) -> PayrollSummaryResponse:
    """Get yearly payroll summary with monthly breakdown."""
    if not user.tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Profilo azienda non configurato")
    data = await service.get_summary(user.tenant_id, year)
    return PayrollSummaryResponse(**data)


@router.delete("/{cost_id}")
async def delete_payroll_cost(
    cost_id: UUID,
    user: User = Depends(get_current_user),
    service: PayrollService = Depends(get_service),
) -> dict:
    """Delete a payroll cost entry."""
    if not user.tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Profilo azienda non configurato")
    try:
        return await service.delete(user.tenant_id, cost_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.post("/import-pdf")
async def import_payroll_pdf(
    file: UploadFile = File(...),
    create_journal: bool = Query(False, description="Crea scritture in partita doppia"),
    user: User = Depends(get_current_user),
    service: PayrollService = Depends(get_service),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Import a Riepilogo Paghe e Contributi PDF.

    Parses the PDF, extracts payroll data, and optionally creates
    journal entries in partita doppia.
    """
    if not user.tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Profilo azienda non configurato")

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Solo file PDF accettati")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File troppo grande (max 10MB)")

    # Extract text from PDF
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # Try pdftotext first (poppler)
        try:
            result = subprocess.run(
                ["pdftotext", "-layout", tmp_path, "-"],
                capture_output=True, text=True, timeout=30,
            )
            text = result.stdout
        except (FileNotFoundError, subprocess.TimeoutExpired):
            # Fallback: basic Python PDF text extraction
            text = _extract_text_basic(content)

        if not text or len(text) < 100:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Impossibile estrarre testo dal PDF. Verificare il formato.",
            )

        # Parse payroll data
        from api.modules.payroll.pdf_parser import parse_payroll_text, payroll_to_journal_lines
        summary = parse_payroll_text(text)

        if summary.mese == 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Mese non trovato nel PDF. Verificare formato 'Riepilogo Paghe e Contributi'.",
            )

        # Create PayrollCost aggregate entry
        from datetime import date as date_type
        mese_date = date_type(summary.anno, summary.mese, 1)

        payroll_data = {
            "mese": mese_date,
            "dipendente_nome": "Riepilogo aziendale",
            "importo_lordo": summary.salari_stipendi,
            "importo_netto": summary.netto_in_busta,
            "contributi_inps": summary.saldo_dm10,
            "irpef": summary.irpef,
            "tfr": summary.tfr,
            "costo_totale_azienda": summary.totale_dare,
            "note": f"Import da PDF: {file.filename}",
        }
        entry = await service.create(user.tenant_id, payroll_data)

        # Optionally create journal entries
        journal_result = None
        if create_journal:
            journal_lines = payroll_to_journal_lines(summary)
            if journal_lines:
                from api.db.models import JournalEntry, JournalLine
                je = JournalEntry(
                    tenant_id=user.tenant_id,
                    description=f"Paghe e contributi {summary.mese:02d}/{summary.anno}",
                    entry_date=mese_date,
                    total_debit=round(summary.totale_dare, 2),
                    total_credit=round(summary.totale_avere, 2),
                    status="posted",
                )
                db.add(je)
                await db.flush()

                for jl in journal_lines:
                    line = JournalLine(
                        entry_id=je.id,
                        account_code=jl["account"],
                        account_name=jl["description"][:255],
                        description=jl["description"][:255],
                        debit=jl["debit"],
                        credit=jl["credit"],
                    )
                    db.add(line)
                await db.flush()

                journal_result = {
                    "journal_entry_id": str(je.id),
                    "lines": len(journal_lines),
                    "total_debit": round(summary.totale_dare, 2),
                    "total_credit": round(summary.totale_avere, 2),
                }

        # Build journal lines for the response (always, for review purposes)
        journal_lines_data = payroll_to_journal_lines(summary)
        linee_contabili = [
            {
                "account": jl["account"],
                "description": jl["description"],
                "debit": jl["debit"],
                "credit": jl["credit"],
            }
            for jl in journal_lines_data
        ]

        return {
            "payroll_cost_id": str(entry["id"]),
            "mese": f"{summary.mese:02d}/{summary.anno}",
            "azienda": summary.azienda,
            "salari_stipendi": summary.salari_stipendi,
            "netto_in_busta": summary.netto_in_busta,
            "contributi_inps": summary.saldo_dm10,
            "irpef": summary.irpef,
            "totale_dare": round(summary.totale_dare, 2),
            "totale_avere": round(summary.totale_avere, 2),
            "bilanciato": abs(summary.totale_dare - summary.totale_avere) < 0.10,
            "linee_estratte": len(summary.linee),
            "linee_contabili": linee_contabili,
            "journal_entry": journal_result,
            "message": f"Paghe {summary.mese:02d}/{summary.anno} importate: €{summary.totale_dare:,.2f}",
        }
    finally:
        os.unlink(tmp_path)


class CreateJournalRequest(BaseModel):
    """Request to create journal entries from payroll import lines."""
    linee_contabili: list[dict]
    totale_dare: float
    totale_avere: float


@router.post("/{cost_id}/create-journal")
async def create_journal_from_payroll(
    cost_id: UUID,
    request: CreateJournalRequest,
    user: User = Depends(get_current_user),
    service: PayrollService = Depends(get_service),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create journal entries from an existing payroll import.

    Used after reviewing an unbalanced import in the gestione-import page,
    or automatically when the import is balanced.
    """
    if not user.tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Profilo azienda non configurato")

    # Verify payroll cost exists and belongs to tenant
    from sqlalchemy import select
    from api.db.models import PayrollCost
    result = await db.execute(
        select(PayrollCost).where(PayrollCost.id == cost_id, PayrollCost.tenant_id == user.tenant_id)
    )
    payroll_cost = result.scalar_one_or_none()
    if not payroll_cost:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voce costo personale non trovata")

    mese_str = payroll_cost.mese.strftime("%m/%Y") if payroll_cost.mese else "N/D"

    from api.db.models import JournalEntry, JournalLine
    je = JournalEntry(
        tenant_id=user.tenant_id,
        description=f"Paghe e contributi {mese_str}",
        entry_date=payroll_cost.mese,
        total_debit=round(request.totale_dare, 2),
        total_credit=round(request.totale_avere, 2),
        status="posted",
    )
    db.add(je)
    await db.flush()

    for jl in request.linee_contabili:
        line = JournalLine(
            entry_id=je.id,
            account_code=jl.get("account", ""),
            account_name=jl.get("description", "")[:255],
            description=jl.get("description", "")[:255],
            debit=jl.get("debit", 0.0),
            credit=jl.get("credit", 0.0),
        )
        db.add(line)
    await db.flush()

    return {
        "journal_entry_id": str(je.id),
        "lines": len(request.linee_contabili),
        "total_debit": round(request.totale_dare, 2),
        "total_credit": round(request.totale_avere, 2),
        "message": f"Scrittura contabile creata per paghe {mese_str}",
    }


def _extract_text_basic(pdf_bytes: bytes) -> str:
    """Basic PDF text extraction without external tools."""
    # Simple extraction from PDF binary (works for text-based PDFs)
    import re
    text_parts = []
    # Find text streams in PDF
    content = pdf_bytes.decode("latin-1", errors="replace")
    # Extract text between BT and ET markers
    for match in re.finditer(r"\(([^)]+)\)", content):
        text_parts.append(match.group(1))
    return "\n".join(text_parts)
