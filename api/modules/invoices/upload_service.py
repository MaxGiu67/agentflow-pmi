"""Service layer for invoice upload (US-06)."""

import logging
import uuid
from datetime import date

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from api.agents.parser_agent import ParserAgent
from api.db.models import Invoice

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png", "xml"}
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "application/xml",
    "text/xml",
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


class UploadService:
    """Service for manual invoice upload."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def validate_file_type(self, filename: str, content_type: str) -> str:
        """Validate file type. Returns normalized extension or raises ValueError."""
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(
                f"Formato file non supportato: .{ext}. "
                f"Formati ammessi: PDF, JPG, PNG, XML"
            )
        return ext

    def validate_file_size(self, size: int) -> None:
        """Validate file size. Raises ValueError if too large."""
        if size > MAX_FILE_SIZE:
            size_mb = round(size / (1024 * 1024), 1)
            raise ValueError(
                f"File troppo grande: {size_mb} MB. Dimensione massima: 10 MB"
            )

    async def check_duplicate(
        self,
        tenant_id: uuid.UUID,
        numero_fattura: str,
        emittente_piva: str,
        data_fattura: date | None,
    ) -> Invoice | None:
        """Check for duplicate invoice by numero_fattura + emittente_piva + data_fattura."""
        conditions = [
            Invoice.tenant_id == tenant_id,
            Invoice.numero_fattura == numero_fattura,
            Invoice.emittente_piva == emittente_piva,
        ]
        if data_fattura:
            conditions.append(Invoice.data_fattura == data_fattura)

        result = await self.db.execute(
            select(Invoice).where(and_(*conditions))
        )
        return result.scalar_one_or_none()

    async def upload_file(
        self,
        tenant_id: uuid.UUID,
        filename: str,
        content_type: str,
        file_content: bytes,
    ) -> dict:
        """Process an uploaded invoice file.

        For XML files: parse with ParserAgent.
        For non-XML files: store and mark for OCR (v0.2).
        """
        ext = self.validate_file_type(filename, content_type)
        self.validate_file_size(len(file_content))

        if ext == "xml":
            return await self._process_xml_upload(tenant_id, filename, file_content)
        else:
            return await self._process_non_xml_upload(tenant_id, filename, ext, file_content)

    async def _process_xml_upload(
        self,
        tenant_id: uuid.UUID,
        filename: str,
        file_content: bytes,
    ) -> dict:
        """Process XML FatturaPA upload with parsing."""
        xml_string = file_content.decode("utf-8")

        # Create a temporary invoice to parse
        invoice = Invoice(
            tenant_id=tenant_id,
            type="passiva",
            document_type="TD01",
            source="upload",
            numero_fattura=f"UPLOAD-{uuid.uuid4().hex[:8]}",
            emittente_piva="UNKNOWN",
            raw_xml=xml_string,
            processing_status="pending",
        )
        self.db.add(invoice)
        await self.db.flush()

        # Parse with ParserAgent
        parser = ParserAgent(self.db)
        try:
            parsed = parser._parse_xml(xml_string)
        except ValueError:
            # If parsing fails, keep the invoice as pending for manual review
            return {
                "invoice_id": invoice.id,
                "filename": filename,
                "file_type": "xml",
                "source": "upload",
                "processing_status": "pending",
                "message": "File XML caricato ma parsing fallito. Revisione manuale necessaria.",
            }

        # Determine if attiva (emessa) or passiva (ricevuta)
        # If emittente P.IVA matches tenant's P.IVA → fattura emessa (attiva)
        parsed.get("destinatario_piva", "")
        emit_piva = parsed.get("emittente_piva", "")
        from sqlalchemy import select as sel
        from api.db.models import Tenant
        tenant_result = await self.db.execute(sel(Tenant).where(Tenant.id == tenant_id))
        tenant_obj = tenant_result.scalar_one_or_none()
        tenant_piva = tenant_obj.piva if tenant_obj else ""

        if emit_piva and tenant_piva and emit_piva.replace("IT", "") == tenant_piva.replace("IT", ""):
            invoice.type = "attiva"
        else:
            invoice.type = "passiva"

        # Update invoice with parsed data
        numero = parsed.get("numero_fattura", invoice.numero_fattura)
        piva = parsed.get("emittente_piva", invoice.emittente_piva)
        data_str = parsed.get("data_fattura")
        data_f = date.fromisoformat(data_str) if data_str else None

        # Check for dedup
        existing = await self.check_duplicate(tenant_id, numero, piva, data_f)
        if existing:
            # Remove the temp invoice we just created
            await self.db.delete(invoice)
            await self.db.flush()
            return {
                "invoice_id": existing.id,
                "filename": filename,
                "file_type": "xml",
                "source": existing.source,
                "processing_status": existing.processing_status,
                "message": f"Fattura duplicata: {numero} da {piva} gia presente (source={existing.source})",
            }

        # Update with parsed data
        invoice.numero_fattura = numero
        invoice.emittente_piva = piva
        invoice.emittente_nome = parsed.get("emittente_nome")
        if data_f:
            invoice.data_fattura = data_f
        invoice.importo_totale = parsed.get("importo_totale")
        invoice.document_type = parsed.get("tipo_documento", "TD01")
        invoice.structured_data = parsed
        invoice.processing_status = "parsed"

        # Calculate netto and iva
        if parsed.get("riepilogo"):
            invoice.importo_netto = sum(r.get("imponibile", 0) for r in parsed["riepilogo"])
            invoice.importo_iva = sum(r.get("imposta", 0) for r in parsed["riepilogo"])

        invoice.has_ritenuta = parsed.get("has_ritenuta", False)
        invoice.has_bollo = parsed.get("has_bollo", False)

        await self.db.flush()

        return {
            "invoice_id": invoice.id,
            "filename": filename,
            "file_type": "xml",
            "source": "upload",
            "processing_status": "parsed",
            "message": f"Fattura XML {numero} caricata e parsata con successo",
        }

    async def _process_non_xml_upload(
        self,
        tenant_id: uuid.UUID,
        filename: str,
        ext: str,
        file_content: bytes,
    ) -> dict:
        """Process non-XML (PDF/JPG/PNG) upload. Stores and marks for OCR."""
        invoice = Invoice(
            tenant_id=tenant_id,
            type="passiva",
            document_type="TD01",
            source="upload",
            numero_fattura=f"UPLOAD-{uuid.uuid4().hex[:8]}",
            emittente_piva="UNKNOWN",
            processing_status="pending",
            structured_data={"original_filename": filename, "file_type": ext, "ocr_pending": True},
        )
        self.db.add(invoice)
        await self.db.flush()

        return {
            "invoice_id": invoice.id,
            "filename": filename,
            "file_type": ext,
            "source": "upload",
            "processing_status": "pending",
            "message": f"File {ext.upper()} caricato. In attesa di elaborazione OCR.",
        }

    async def import_folder(self, tenant_id: uuid.UUID, folder_path: str) -> dict:
        """Import all XML invoices from a local folder.

        Scans the folder for *.xml files (excluding *metaDato* files),
        parses each one, deduplicates, and imports.
        """
        import os

        if not os.path.isdir(folder_path):
            raise ValueError(f"Cartella non trovata: {folder_path}")

        xml_files = sorted([
            f for f in os.listdir(folder_path)
            if f.endswith(".xml") and "metaDato" not in f
        ])

        if not xml_files:
            raise ValueError(f"Nessun file XML trovato in: {folder_path}")

        imported = 0
        duplicates = 0
        errors = 0
        details = []

        for filename in xml_files:
            filepath = os.path.join(folder_path, filename)
            try:
                with open(filepath, "rb") as f:
                    content = f.read()

                # Try different encodings
                try:
                    xml_string = content.decode("utf-8")
                except UnicodeDecodeError:
                    xml_string = content.decode("windows-1252")

                result = await self._process_xml_upload(tenant_id, filename, xml_string.encode("utf-8"))

                if "duplicata" in result.get("message", "").lower():
                    duplicates += 1
                    details.append({"file": filename, "status": "duplicata", "message": result["message"]})
                else:
                    imported += 1
                    details.append({"file": filename, "status": "importata", "invoice_id": str(result.get("invoice_id", ""))})

            except Exception as e:
                errors += 1
                details.append({"file": filename, "status": "errore", "message": str(e)})
                logger.error("Errore importazione %s: %s", filename, e)

        return {
            "total_files": len(xml_files),
            "imported": imported,
            "duplicates": duplicates,
            "errors": errors,
            "details": details,
        }
