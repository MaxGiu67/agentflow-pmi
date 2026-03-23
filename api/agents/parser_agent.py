"""ParserAgent: Parses XML FatturaPA invoices and extracts structured data."""

import logging
import uuid
import xml.etree.ElementTree as ET
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.agents.base_agent import BaseAgent
from api.db.models import Invoice

logger = logging.getLogger(__name__)

# FatturaPA namespace
NS = {"p": "http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2"}

# Document type mapping
DOCUMENT_TYPES = {
    "TD01": "fattura",
    "TD02": "acconto_fattura",
    "TD03": "acconto_parcella",
    "TD04": "nota_credito",
    "TD05": "nota_debito",
    "TD06": "parcella",
    "TD16": "integrazione_reverse_charge",
    "TD17": "integrazione_acquisto_servizi_estero",
    "TD20": "autofattura",
    "TD24": "fattura_differita",
    "TD25": "fattura_differita_beni",
}


class ParserAgent(BaseAgent):
    """Agent that parses FatturaPA XML invoices."""

    agent_name = "parser_agent"

    async def parse_invoice(self, invoice_id: uuid.UUID, tenant_id: uuid.UUID) -> dict:
        """Parse a single invoice XML and update the invoice record.

        Args:
            invoice_id: The invoice to parse.
            tenant_id: The tenant owning the invoice.

        Returns:
            Dict with parsed data.
        """
        result = await self.db.execute(
            select(Invoice).where(Invoice.id == invoice_id)
        )
        invoice = result.scalar_one_or_none()
        if not invoice:
            raise ValueError(f"Fattura {invoice_id} non trovata")

        if not invoice.raw_xml:
            invoice.processing_status = "error"
            await self.db.flush()
            raise ValueError("Fattura senza XML raw")

        try:
            parsed = self._parse_xml(invoice.raw_xml)
        except Exception as e:
            # Mark as parsing failed
            invoice.processing_status = "error"
            invoice.structured_data = {"error": str(e), "parse_status": "parsing_fallito"}
            await self.db.flush()

            await self.publish_event(
                "invoice.parse_failed",
                {
                    "invoice_id": str(invoice_id),
                    "error": str(e),
                },
                tenant_id,
            )
            raise ValueError(f"Parsing fallito: {e}") from e

        # Update invoice with parsed data
        invoice.document_type = parsed.get("tipo_documento", invoice.document_type)
        invoice.emittente_piva = parsed.get("emittente_piva", invoice.emittente_piva)
        invoice.emittente_nome = parsed.get("emittente_nome", invoice.emittente_nome)
        if parsed.get("data_fattura"):
            invoice.data_fattura = date.fromisoformat(parsed["data_fattura"])
        invoice.numero_fattura = parsed.get("numero_fattura", invoice.numero_fattura)
        invoice.importo_totale = parsed.get("importo_totale", invoice.importo_totale)

        # Calculate netto and iva from riepilogo
        if parsed.get("riepilogo"):
            total_netto = sum(r.get("imponibile", 0) for r in parsed["riepilogo"])
            total_iva = sum(r.get("imposta", 0) for r in parsed["riepilogo"])
            invoice.importo_netto = total_netto
            invoice.importo_iva = total_iva

        # Check for ritenuta and bollo
        invoice.has_ritenuta = parsed.get("has_ritenuta", False)
        invoice.has_bollo = parsed.get("has_bollo", False)

        # Determine type based on document type
        if parsed.get("tipo_documento") == "TD04":
            invoice.type = "passiva"  # nota di credito

        invoice.structured_data = parsed
        invoice.processing_status = "parsed"
        await self.db.flush()

        # Publish parsed event
        await self.publish_event(
            "invoice.parsed",
            {
                "invoice_id": str(invoice_id),
                "tipo_documento": parsed.get("tipo_documento"),
                "emittente": parsed.get("emittente_nome"),
                "importo_totale": parsed.get("importo_totale"),
                "num_linee": len(parsed.get("linee_dettaglio", [])),
            },
            tenant_id,
        )

        return parsed

    def _parse_xml(self, xml_string: str) -> dict:
        """Parse FatturaPA XML and extract all fields.

        Handles both namespaced and non-namespaced XML.
        """
        try:
            root = ET.fromstring(xml_string)
        except ET.ParseError as e:
            raise ValueError(f"XML malformato: {e}") from e

        # Try with namespace first, fallback to without
        parsed = {}

        # Extract header
        header = self._find_element(root, "FatturaElettronicaHeader")
        if header is not None:
            # CedentePrestatore (supplier)
            cedente = self._find_element(header, "CedentePrestatore")
            if cedente is not None:
                dati_anag = self._find_element(cedente, "DatiAnagrafici")
                if dati_anag is not None:
                    id_fiscale = self._find_element(dati_anag, "IdFiscaleIVA")
                    if id_fiscale is not None:
                        id_paese = self._find_text(id_fiscale, "IdPaese", "")
                        id_codice = self._find_text(id_fiscale, "IdCodice", "")
                        parsed["emittente_piva"] = f"{id_paese}{id_codice}"

                    anagrafica = self._find_element(dati_anag, "Anagrafica")
                    if anagrafica is not None:
                        parsed["emittente_nome"] = self._find_text(anagrafica, "Denominazione")
                        if not parsed["emittente_nome"]:
                            nome = self._find_text(anagrafica, "Nome", "")
                            cognome = self._find_text(anagrafica, "Cognome", "")
                            parsed["emittente_nome"] = f"{nome} {cognome}".strip()

            # CessionarioCommittente (buyer)
            cessionario = self._find_element(header, "CessionarioCommittente")
            if cessionario is not None:
                dati_anag = self._find_element(cessionario, "DatiAnagrafici")
                if dati_anag is not None:
                    id_fiscale = self._find_element(dati_anag, "IdFiscaleIVA")
                    if id_fiscale is not None:
                        id_paese = self._find_text(id_fiscale, "IdPaese", "")
                        id_codice = self._find_text(id_fiscale, "IdCodice", "")
                        parsed["destinatario_piva"] = f"{id_paese}{id_codice}"

                    anagrafica = self._find_element(dati_anag, "Anagrafica")
                    if anagrafica is not None:
                        parsed["destinatario_nome"] = self._find_text(anagrafica, "Denominazione")

        # Extract body
        body = self._find_element(root, "FatturaElettronicaBody")
        if body is not None:
            # DatiGenerali
            dati_generali = self._find_element(body, "DatiGenerali")
            if dati_generali is not None:
                dati_doc = self._find_element(dati_generali, "DatiGeneraliDocumento")
                if dati_doc is not None:
                    parsed["tipo_documento"] = self._find_text(dati_doc, "TipoDocumento")
                    parsed["data_fattura"] = self._find_text(dati_doc, "Data")
                    parsed["numero_fattura"] = self._find_text(dati_doc, "Numero")

                    importo_str = self._find_text(dati_doc, "ImportoTotaleDocumento")
                    if importo_str:
                        parsed["importo_totale"] = float(importo_str)

                    # Check for ritenuta
                    ritenuta = self._find_element(dati_doc, "DatiRitenuta")
                    parsed["has_ritenuta"] = ritenuta is not None

                    # Check for bollo
                    bollo = self._find_element(dati_doc, "DatiBollo")
                    parsed["has_bollo"] = bollo is not None

            # DatiBeniServizi
            dati_beni = self._find_element(body, "DatiBeniServizi")
            if dati_beni is not None:
                # DettaglioLinee
                linee = self._find_all_elements(dati_beni, "DettaglioLinee")
                parsed["linee_dettaglio"] = []
                for linea in linee:
                    linea_data = {
                        "numero_linea": self._find_text(linea, "NumeroLinea"),
                        "descrizione": self._find_text(linea, "Descrizione"),
                        "quantita": self._safe_float(self._find_text(linea, "Quantita")),
                        "prezzo_unitario": self._safe_float(self._find_text(linea, "PrezzoUnitario")),
                        "prezzo_totale": self._safe_float(self._find_text(linea, "PrezzoTotale")),
                        "aliquota_iva": self._safe_float(self._find_text(linea, "AliquotaIVA")),
                    }
                    parsed["linee_dettaglio"].append(linea_data)

                # DatiRiepilogo
                riepiloghi = self._find_all_elements(dati_beni, "DatiRiepilogo")
                parsed["riepilogo"] = []
                for riep in riepiloghi:
                    riep_data = {
                        "aliquota_iva": self._safe_float(self._find_text(riep, "AliquotaIVA")),
                        "imponibile": self._safe_float(self._find_text(riep, "ImponibileImporto")),
                        "imposta": self._safe_float(self._find_text(riep, "Imposta")),
                    }
                    parsed["riepilogo"].append(riep_data)

        # Map document type description
        tipo_doc = parsed.get("tipo_documento", "")
        parsed["tipo_documento_desc"] = DOCUMENT_TYPES.get(tipo_doc, "sconosciuto")

        return parsed

    def _find_element(self, parent: ET.Element, tag: str) -> ET.Element | None:
        """Find element with or without namespace."""
        # Try with namespace
        for ns_prefix, ns_uri in NS.items():
            el = parent.find(f".//{{{ns_uri}}}{tag}")
            if el is not None:
                return el
        # Try without namespace
        el = parent.find(f".//{tag}")
        return el

    def _find_all_elements(self, parent: ET.Element, tag: str) -> list[ET.Element]:
        """Find all elements with or without namespace."""
        for ns_prefix, ns_uri in NS.items():
            elements = parent.findall(f".//{{{ns_uri}}}{tag}")
            if elements:
                return elements
        return parent.findall(f".//{tag}")

    def _find_text(self, parent: ET.Element, tag: str, default: str | None = None) -> str | None:
        """Find element text with or without namespace."""
        el = self._find_element(parent, tag)
        if el is not None and el.text:
            return el.text.strip()
        return default

    def _safe_float(self, value: str | None) -> float | None:
        """Safely convert string to float."""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
