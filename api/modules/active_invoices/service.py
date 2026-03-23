"""Service layer for active invoices (US-21)."""

import logging
import uuid
from datetime import date

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.adapters.acube import ACubeSDIAdapter
from api.db.models import ActiveInvoice, Tenant

logger = logging.getLogger(__name__)


class ActiveInvoiceService:
    """Business logic for active invoice creation, XML generation, SDI sending."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.acube = ACubeSDIAdapter()

    async def create_invoice(
        self,
        tenant_id: uuid.UUID,
        data: dict,
    ) -> dict:
        """Create a new active invoice with auto-generated numero_fattura.

        Validates uniqueness of numero_fattura and generates FatturaPA XML.
        """
        # Get tenant for P.IVA
        result = await self.db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()
        if not tenant:
            raise ValueError("Tenant non trovato")

        # Generate numero_fattura (progressive per year)
        year = data["data_fattura"].year if isinstance(data["data_fattura"], date) else int(data["data_fattura"][:4])
        numero_fattura = await self._generate_numero_fattura(tenant_id, year, data.get("document_type", "TD01"))

        # Compute IVA
        importo_netto = data["importo_netto"]
        aliquota_iva = data.get("aliquota_iva", 22.0)
        importo_iva = round(importo_netto * aliquota_iva / 100, 2)
        importo_totale = round(importo_netto + importo_iva, 2)

        # Generate XML FatturaPA
        doc_type = data.get("document_type", "TD01")
        raw_xml = self._generate_fatturapa_xml(
            tenant=tenant,
            numero=numero_fattura,
            doc_type=doc_type,
            cliente_piva=data["cliente_piva"],
            cliente_nome=data["cliente_nome"],
            cliente_codice_sdi=data.get("cliente_codice_sdi", "0000000"),
            data_fattura=data["data_fattura"],
            importo_netto=importo_netto,
            importo_iva=importo_iva,
            importo_totale=importo_totale,
            aliquota_iva=aliquota_iva,
            descrizione=data.get("descrizione", "Prestazione professionale"),
            original_numero=data.get("original_invoice_numero"),
            original_date=data.get("original_invoice_date"),
        )

        invoice = ActiveInvoice(
            tenant_id=tenant_id,
            numero_fattura=numero_fattura,
            document_type=doc_type,
            cliente_piva=data["cliente_piva"],
            cliente_nome=data["cliente_nome"],
            cliente_codice_sdi=data.get("cliente_codice_sdi"),
            data_fattura=data["data_fattura"],
            importo_netto=importo_netto,
            aliquota_iva=aliquota_iva,
            importo_iva=importo_iva,
            importo_totale=importo_totale,
            descrizione=data.get("descrizione"),
            raw_xml=raw_xml,
            sdi_status="draft",
            original_invoice_id=data.get("original_invoice_id"),
            original_invoice_numero=data.get("original_invoice_numero"),
            original_invoice_date=data.get("original_invoice_date"),
        )

        self.db.add(invoice)
        await self.db.flush()

        logger.info("Created active invoice %s for tenant %s", numero_fattura, tenant_id)

        return self._to_dict(invoice)

    async def send_to_sdi(self, invoice_id: uuid.UUID, tenant_id: uuid.UUID) -> dict:
        """Send an active invoice to SDI via A-Cube.

        Returns dict with sdi_id, status, message.
        """
        result = await self.db.execute(
            select(ActiveInvoice).where(
                ActiveInvoice.id == invoice_id,
                ActiveInvoice.tenant_id == tenant_id,
            )
        )
        invoice = result.scalar_one_or_none()
        if not invoice:
            raise ValueError("Fattura non trovata")

        if invoice.sdi_status not in ("draft", "rejected"):
            raise ValueError(f"Fattura in stato '{invoice.sdi_status}', non inviabile")

        # Get tenant P.IVA
        tenant_result = await self.db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = tenant_result.scalar_one_or_none()

        # Send via A-Cube
        send_result = await self.acube.send_invoice(
            xml_content=invoice.raw_xml or "",
            tenant_piva=tenant.piva if tenant else "",
        )

        invoice.sdi_id = send_result.sdi_id
        invoice.sdi_status = "sent"
        invoice.sdi_reject_reason = None
        await self.db.flush()

        return {
            "invoice_id": str(invoice.id),
            "sdi_id": send_result.sdi_id,
            "sdi_status": "sent",
            "message": send_result.message,
        }

    async def get_sdi_status(self, invoice_id: uuid.UUID, tenant_id: uuid.UUID) -> dict:
        """Check SDI delivery status for an invoice."""
        result = await self.db.execute(
            select(ActiveInvoice).where(
                ActiveInvoice.id == invoice_id,
                ActiveInvoice.tenant_id == tenant_id,
            )
        )
        invoice = result.scalar_one_or_none()
        if not invoice:
            raise ValueError("Fattura non trovata")

        if invoice.sdi_status == "draft":
            return {
                "invoice_id": str(invoice.id),
                "sdi_id": None,
                "sdi_status": "draft",
                "sdi_reject_reason": None,
                "message": "Fattura non ancora inviata a SDI",
            }

        # Only query A-Cube for status when invoice is in "sent" state
        # (awaiting delivery confirmation). If already delivered/rejected,
        # return the DB state.
        if invoice.sdi_id and invoice.sdi_status == "sent":
            status_result = await self.acube.get_delivery_status(invoice.sdi_id)
            invoice.sdi_status = status_result.status
            if status_result.status == "rejected":
                invoice.sdi_reject_reason = status_result.reject_reason
            await self.db.flush()

        return {
            "invoice_id": str(invoice.id),
            "sdi_id": invoice.sdi_id,
            "sdi_status": invoice.sdi_status,
            "sdi_reject_reason": invoice.sdi_reject_reason,
            "message": self._status_message(invoice.sdi_status, invoice.sdi_reject_reason),
        }

    async def get_invoice(self, invoice_id: uuid.UUID, tenant_id: uuid.UUID) -> dict | None:
        """Get a single active invoice."""
        result = await self.db.execute(
            select(ActiveInvoice).where(
                ActiveInvoice.id == invoice_id,
                ActiveInvoice.tenant_id == tenant_id,
            )
        )
        invoice = result.scalar_one_or_none()
        if not invoice:
            return None
        return self._to_dict(invoice)

    async def list_invoices(self, tenant_id: uuid.UUID) -> list[dict]:
        """List all active invoices for a tenant."""
        result = await self.db.execute(
            select(ActiveInvoice)
            .where(ActiveInvoice.tenant_id == tenant_id)
            .order_by(ActiveInvoice.created_at.desc())
        )
        invoices = result.scalars().all()
        return [self._to_dict(inv) for inv in invoices]

    async def check_duplicate_numero(
        self, tenant_id: uuid.UUID, numero_fattura: str,
    ) -> dict | None:
        """Check if numero_fattura already exists. Returns next suggestion if duplicate."""
        result = await self.db.execute(
            select(ActiveInvoice).where(
                ActiveInvoice.tenant_id == tenant_id,
                ActiveInvoice.numero_fattura == numero_fattura,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            # Suggest next available
            year = existing.data_fattura.year if existing.data_fattura else date.today().year
            doc_type = existing.document_type
            next_num = await self._generate_numero_fattura(tenant_id, year, doc_type)
            return {
                "duplicate": True,
                "existing_numero": numero_fattura,
                "suggested_next": next_num,
            }
        return None

    async def _generate_numero_fattura(
        self, tenant_id: uuid.UUID, year: int, doc_type: str,
    ) -> str:
        """Generate progressive numero_fattura for the year."""
        prefix = "FTA" if doc_type == "TD01" else "NC"
        pattern = f"{prefix}-{year}-%"

        result = await self.db.execute(
            select(func.count()).select_from(ActiveInvoice).where(
                ActiveInvoice.tenant_id == tenant_id,
                ActiveInvoice.numero_fattura.like(pattern),
            )
        )
        count = result.scalar() or 0
        next_num = count + 1
        return f"{prefix}-{year}-{next_num:04d}"

    def _generate_fatturapa_xml(
        self,
        tenant: Tenant,
        numero: str,
        doc_type: str,
        cliente_piva: str,
        cliente_nome: str,
        cliente_codice_sdi: str,
        data_fattura: date,
        importo_netto: float,
        importo_iva: float,
        importo_totale: float,
        aliquota_iva: float,
        descrizione: str,
        original_numero: str | None = None,
        original_date: date | None = None,
    ) -> str:
        """Generate FatturaPA 1.2 XML."""
        piva = (tenant.piva or "").replace("IT", "")
        cliente_piva_clean = cliente_piva.replace("IT", "")
        data_str = data_fattura.isoformat() if isinstance(data_fattura, date) else str(data_fattura)

        # Build DatiFattureCollegate for credit notes
        dati_collegati = ""
        if doc_type == "TD04" and original_numero:
            orig_date_str = original_date.isoformat() if original_date else data_str
            dati_collegati = f"""
      <DatiFattureCollegate>
        <IdDocumento>{original_numero}</IdDocumento>
        <Data>{orig_date_str}</Data>
      </DatiFattureCollegate>"""

        return f"""<?xml version="1.0" encoding="UTF-8"?>
<p:FatturaElettronica xmlns:p="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2"
  versione="FPR12">
  <FatturaElettronicaHeader>
    <DatiTrasmissione>
      <IdTrasmittente>
        <IdPaese>IT</IdPaese>
        <IdCodice>{piva}</IdCodice>
      </IdTrasmittente>
      <FormatoTrasmissione>FPR12</FormatoTrasmissione>
      <CodiceDestinatario>{cliente_codice_sdi}</CodiceDestinatario>
    </DatiTrasmissione>
    <CedentePrestatore>
      <DatiAnagrafici>
        <IdFiscaleIVA>
          <IdPaese>IT</IdPaese>
          <IdCodice>{piva}</IdCodice>
        </IdFiscaleIVA>
        <Anagrafica>
          <Denominazione>{tenant.name}</Denominazione>
        </Anagrafica>
      </DatiAnagrafici>
    </CedentePrestatore>
    <CessionarioCommittente>
      <DatiAnagrafici>
        <IdFiscaleIVA>
          <IdPaese>IT</IdPaese>
          <IdCodice>{cliente_piva_clean}</IdCodice>
        </IdFiscaleIVA>
        <Anagrafica>
          <Denominazione>{cliente_nome}</Denominazione>
        </Anagrafica>
      </DatiAnagrafici>
    </CessionarioCommittente>
  </FatturaElettronicaHeader>
  <FatturaElettronicaBody>
    <DatiGenerali>
      <DatiGeneraliDocumento>
        <TipoDocumento>{doc_type}</TipoDocumento>
        <Data>{data_str}</Data>
        <Numero>{numero}</Numero>
        <ImportoTotaleDocumento>{importo_totale:.2f}</ImportoTotaleDocumento>
      </DatiGeneraliDocumento>{dati_collegati}
    </DatiGenerali>
    <DatiBeniServizi>
      <DettaglioLinee>
        <NumeroLinea>1</NumeroLinea>
        <Descrizione>{descrizione}</Descrizione>
        <Quantita>1.00</Quantita>
        <PrezzoUnitario>{importo_netto:.2f}</PrezzoUnitario>
        <PrezzoTotale>{importo_netto:.2f}</PrezzoTotale>
        <AliquotaIVA>{aliquota_iva:.2f}</AliquotaIVA>
      </DettaglioLinee>
      <DatiRiepilogo>
        <AliquotaIVA>{aliquota_iva:.2f}</AliquotaIVA>
        <ImponibileImporto>{importo_netto:.2f}</ImponibileImporto>
        <Imposta>{importo_iva:.2f}</Imposta>
      </DatiRiepilogo>
    </DatiBeniServizi>
  </FatturaElettronicaBody>
</p:FatturaElettronica>"""

    def _status_message(self, status: str, reject_reason: str | None = None) -> str:
        """Human-readable status message."""
        messages = {
            "draft": "Fattura in bozza, non ancora inviata",
            "sent": "Fattura inviata a SDI, in attesa di consegna",
            "delivered": "Fattura consegnata al destinatario",
            "rejected": f"Fattura rifiutata da SDI: {reject_reason or 'motivo sconosciuto'}",
        }
        return messages.get(status, f"Stato sconosciuto: {status}")

    def _to_dict(self, invoice: ActiveInvoice) -> dict:
        """Convert ActiveInvoice model to dict."""
        return {
            "id": str(invoice.id),
            "tenant_id": str(invoice.tenant_id),
            "numero_fattura": invoice.numero_fattura,
            "document_type": invoice.document_type,
            "cliente_piva": invoice.cliente_piva,
            "cliente_nome": invoice.cliente_nome,
            "cliente_codice_sdi": invoice.cliente_codice_sdi,
            "data_fattura": invoice.data_fattura.isoformat() if invoice.data_fattura else None,
            "importo_netto": invoice.importo_netto,
            "aliquota_iva": invoice.aliquota_iva,
            "importo_iva": invoice.importo_iva,
            "importo_totale": invoice.importo_totale,
            "descrizione": invoice.descrizione,
            "sdi_status": invoice.sdi_status,
            "sdi_id": invoice.sdi_id,
            "sdi_reject_reason": invoice.sdi_reject_reason,
            "raw_xml": invoice.raw_xml,
            "original_invoice_id": str(invoice.original_invoice_id) if invoice.original_invoice_id else None,
            "original_invoice_numero": invoice.original_invoice_numero,
            "original_invoice_date": invoice.original_invoice_date.isoformat() if invoice.original_invoice_date else None,
            "created_at": invoice.created_at.isoformat() if invoice.created_at else None,
            "updated_at": invoice.updated_at.isoformat() if invoice.updated_at else None,
        }
