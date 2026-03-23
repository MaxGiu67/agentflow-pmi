"""Service layer for withholding tax (ritenuta d'acconto) management (US-33)."""

import logging
import uuid
import xml.etree.ElementTree as ET
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import FiscalDeadline, Invoice, WithholdingTax

logger = logging.getLogger(__name__)

# FatturaPA namespace
NS = {"p": "http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2"}

# Professional supplier indicators (for AC-33.4 warning)
PROFESSIONAL_DOC_TYPES = {"TD06"}  # parcella
PROFESSIONAL_KEYWORDS = [
    "avvocato", "notaio", "commercialista", "consulente",
    "ingegnere", "architetto", "medico", "veterinario",
    "psicologo", "dottore", "professionista", "studio",
    "geometra", "perito", "farmacista", "biologo",
]


class WithholdingTaxService:
    """Business logic for withholding tax detection and management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def detect_from_invoice(
        self,
        invoice_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> dict:
        """Detect withholding tax from invoice XML.

        AC-33.1: Recognize <DatiRitenuta> tag, calculate net amount
        AC-33.2: Create journal entry with withholding (DARE costo+IVA / AVERE fornitore+erario)
        AC-33.3: F24 deadline (code 1040, 16th of month after payment)
        AC-33.4: No tag but professional supplier -> warning
        """
        # Get invoice
        result = await self.db.execute(
            select(Invoice).where(
                Invoice.id == invoice_id,
                Invoice.tenant_id == tenant_id,
            )
        )
        invoice = result.scalar_one_or_none()
        if not invoice:
            raise ValueError("Fattura non trovata")

        # Parse XML for ritenuta data
        ritenuta_data = self._extract_ritenuta(invoice.raw_xml)

        if ritenuta_data:
            # AC-33.1: Calculate net amount
            importo_totale = invoice.importo_totale or 0.0
            importo_ritenuta = ritenuta_data["importo_ritenuta"]
            importo_netto = round(importo_totale - importo_ritenuta, 2)

            # AC-33.3: F24 due date (16th of month after payment)
            payment_date = invoice.data_fattura or date.today()
            f24_due_date = self._compute_f24_due_date(payment_date)

            # Create withholding tax record
            wt = WithholdingTax(
                tenant_id=tenant_id,
                invoice_id=invoice_id,
                tipo_ritenuta=ritenuta_data["tipo_ritenuta"],
                aliquota=ritenuta_data["aliquota"],
                causale_pagamento=ritenuta_data.get("causale_pagamento"),
                importo_ritenuta=importo_ritenuta,
                imponibile_ritenuta=ritenuta_data["imponibile_ritenuta"],
                importo_netto=importo_netto,
                f24_code="1040",
                f24_due_date=f24_due_date,
                status="detected",
            )
            self.db.add(wt)

            # Create fiscal deadline for F24
            deadline = FiscalDeadline(
                tenant_id=tenant_id,
                code="1040",
                description=(
                    f"Versamento ritenuta d'acconto - Fattura {invoice.numero_fattura} "
                    f"({invoice.emittente_nome})"
                ),
                amount=importo_ritenuta,
                due_date=f24_due_date,
                status="pending",
                source_invoice_id=invoice_id,
            )
            self.db.add(deadline)

            # Update invoice
            invoice.has_ritenuta = True
            await self.db.flush()

            # AC-33.2: Build journal entry structure
            importo_netto_beni = invoice.importo_netto or 0.0
            importo_iva = invoice.importo_iva or 0.0
            journal_entry = {
                "description": f"Fattura {invoice.numero_fattura} con ritenuta d'acconto",
                "lines": [
                    {
                        "account_code": "6100",
                        "account_name": "Costi per servizi",
                        "debit": importo_netto_beni,
                        "credit": 0.0,
                    },
                    {
                        "account_code": "1120",
                        "account_name": "IVA a credito",
                        "debit": importo_iva,
                        "credit": 0.0,
                    },
                    {
                        "account_code": "2010",
                        "account_name": "Debiti verso fornitori",
                        "debit": 0.0,
                        "credit": importo_netto,
                    },
                    {
                        "account_code": "2030",
                        "account_name": "Erario c/ritenute da versare",
                        "debit": 0.0,
                        "credit": importo_ritenuta,
                    },
                ],
            }

            return {
                "detected": True,
                "invoice_id": str(invoice_id),
                "tipo_ritenuta": ritenuta_data["tipo_ritenuta"],
                "aliquota": ritenuta_data["aliquota"],
                "causale_pagamento": ritenuta_data.get("causale_pagamento"),
                "importo_ritenuta": importo_ritenuta,
                "imponibile_ritenuta": ritenuta_data["imponibile_ritenuta"],
                "importo_netto": importo_netto,
                "f24_code": "1040",
                "f24_due_date": f24_due_date.isoformat(),
                "warning": None,
                "journal_entry": journal_entry,
            }

        # AC-33.4: No ritenuta tag but professional supplier -> warning
        warning = self._check_professional_warning(invoice)

        return {
            "detected": False,
            "invoice_id": str(invoice_id),
            "tipo_ritenuta": None,
            "aliquota": None,
            "causale_pagamento": None,
            "importo_ritenuta": None,
            "imponibile_ritenuta": None,
            "importo_netto": None,
            "f24_code": None,
            "f24_due_date": None,
            "warning": warning,
            "journal_entry": None,
        }

    async def list_withholding_taxes(
        self, tenant_id: uuid.UUID,
    ) -> dict:
        """List all withholding taxes for tenant."""
        result = await self.db.execute(
            select(WithholdingTax).where(
                WithholdingTax.tenant_id == tenant_id,
            ).order_by(WithholdingTax.created_at.desc())
        )
        items = result.scalars().all()

        return {
            "items": [
                {
                    "id": str(wt.id),
                    "tenant_id": str(wt.tenant_id),
                    "invoice_id": str(wt.invoice_id),
                    "tipo_ritenuta": wt.tipo_ritenuta,
                    "aliquota": wt.aliquota,
                    "causale_pagamento": wt.causale_pagamento,
                    "importo_ritenuta": wt.importo_ritenuta,
                    "imponibile_ritenuta": wt.imponibile_ritenuta,
                    "importo_netto": wt.importo_netto,
                    "f24_code": wt.f24_code,
                    "f24_due_date": wt.f24_due_date.isoformat() if wt.f24_due_date else None,
                    "status": wt.status,
                }
                for wt in items
            ],
            "total": len(items),
        }

    def _extract_ritenuta(self, raw_xml: str | None) -> dict | None:
        """Extract <DatiRitenuta> from FatturaPA XML.

        Returns dict with tipo_ritenuta, aliquota, importo_ritenuta,
        imponibile_ritenuta, causale_pagamento.
        """
        if not raw_xml:
            return None

        try:
            root = ET.fromstring(raw_xml)
        except ET.ParseError:
            return None

        # Find DatiRitenuta element
        ritenuta = self._find_element(root, "DatiRitenuta")
        if ritenuta is None:
            return None

        tipo = self._find_text(ritenuta, "TipoRitenuta") or "RT01"
        aliquota_str = self._find_text(ritenuta, "AliquotaRitenuta")
        importo_str = self._find_text(ritenuta, "ImportoRitenuta")
        causale = self._find_text(ritenuta, "CausalePagamento")

        if not aliquota_str or not importo_str:
            return None

        aliquota = float(aliquota_str)
        importo_ritenuta = float(importo_str)

        # Calculate imponibile from aliquota
        imponibile = round(importo_ritenuta / (aliquota / 100), 2) if aliquota else 0.0

        return {
            "tipo_ritenuta": tipo,
            "aliquota": aliquota,
            "importo_ritenuta": importo_ritenuta,
            "imponibile_ritenuta": imponibile,
            "causale_pagamento": causale,
        }

    def _check_professional_warning(self, invoice: Invoice) -> str | None:
        """AC-33.4: Check if invoice is from professional without ritenuta tag."""
        # Check document type
        if invoice.document_type in PROFESSIONAL_DOC_TYPES:
            return (
                f"Attenzione: fattura {invoice.numero_fattura} di tipo {invoice.document_type} "
                "(parcella) senza tag DatiRitenuta. Verificare se e soggetta a ritenuta d'acconto."
            )

        # Check supplier name for professional keywords
        nome = (invoice.emittente_nome or "").lower()
        for keyword in PROFESSIONAL_KEYWORDS:
            if keyword in nome:
                return (
                    f"Attenzione: fattura {invoice.numero_fattura} da '{invoice.emittente_nome}' "
                    "potrebbe essere soggetta a ritenuta d'acconto (fornitore professionista). "
                    "Verificare."
                )

        return None

    @staticmethod
    def _compute_f24_due_date(payment_date: date) -> date:
        """Compute F24 due date: 16th of the month following payment.

        AC-33.3: Code 1040, due 16th of month after payment.
        """
        if payment_date.month == 12:
            return date(payment_date.year + 1, 1, 16)
        else:
            return date(payment_date.year, payment_date.month + 1, 16)

    def _find_element(self, parent: ET.Element, tag: str) -> ET.Element | None:
        """Find element with or without namespace."""
        for ns_uri in NS.values():
            el = parent.find(f".//{{{ns_uri}}}{tag}")
            if el is not None:
                return el
        return parent.find(f".//{tag}")

    def _find_text(self, parent: ET.Element, tag: str) -> str | None:
        """Find element text with or without namespace."""
        el = self._find_element(parent, tag)
        if el is not None and el.text:
            return el.text.strip()
        return None
