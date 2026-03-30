"""ContaAgent: Registers double-entry journal entries from verified invoices."""

import logging
import uuid
from datetime import date

from sqlalchemy import select, and_

from api.agents.base_agent import BaseAgent
from api.db.models import Invoice, JournalEntry, JournalLine

logger = logging.getLogger(__name__)

# Maps invoice categories to expense account codes from piano conti SRL
ACCOUNT_MAPPINGS: dict[str, tuple[str, str]] = {
    # category → (account_code, account_name)
    "Consulenze": ("6110", "Consulenze"),
    "Utenze": ("6120", "Utenze"),
    "Acquisti materie prime": ("5010", "Acquisti materie prime"),
    "Servizi": ("5020", "Servizi"),
    "Godimento beni di terzi": ("5030", "Godimento beni di terzi"),
    "Costi del personale": ("5040", "Costi del personale"),
    "Ammortamenti": ("5050", "Ammortamenti"),
    "Oneri diversi di gestione": ("5060", "Oneri diversi di gestione"),
    "Interessi passivi": ("6020", "Interessi passivi"),
    "Materiali": ("5010", "Acquisti materie prime"),
    "Servizi IT": ("6110", "Consulenze"),
    "Affitto": ("5030", "Godimento beni di terzi"),
    "Telefonia": ("6120", "Utenze"),
    "Energia": ("6120", "Utenze"),
}

# Fixed accounts
IVA_CREDITO_CODE = "1120"
IVA_CREDITO_NAME = "Crediti IVA"
IVA_DEBITO_CODE = "2110"
IVA_DEBITO_NAME = "IVA a debito"
FORNITORI_CODE = "2010"
FORNITORI_NAME = "Debiti verso fornitori"


class ContaAgent(BaseAgent):
    """Agent that creates double-entry journal entries from verified invoices."""

    agent_name = "conta_agent"

    async def register_entry(
        self,
        invoice_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> dict:
        """Register a double-entry journal entry for an invoice.

        Returns dict with entry info or error.
        """
        # Idempotency check: already registered?
        existing = await self.db.execute(
            select(JournalEntry).where(
                and_(
                    JournalEntry.invoice_id == invoice_id,
                    JournalEntry.tenant_id == tenant_id,
                    JournalEntry.status.in_(["draft", "posted"]),
                )
            )
        )
        if existing.scalar_one_or_none():
            return {
                "status": "already_registered",
                "message": "Scrittura contabile gia registrata per questa fattura",
            }

        # Fetch invoice
        result = await self.db.execute(
            select(Invoice).where(
                and_(
                    Invoice.id == invoice_id,
                    Invoice.tenant_id == tenant_id,
                )
            )
        )
        invoice = result.scalar_one_or_none()
        if not invoice:
            raise ValueError(f"Fattura {invoice_id} non trovata")

        if not invoice.category:
            raise ValueError("Fattura non categorizzata")

        # Resolve expense account
        account_mapping = ACCOUNT_MAPPINGS.get(invoice.category)
        if not account_mapping:
            # Unknown category — create error entry
            entry = JournalEntry(
                tenant_id=tenant_id,
                invoice_id=invoice_id,
                description=f"Fattura {invoice.numero_fattura} - {invoice.emittente_nome or 'N/A'}",
                entry_date=invoice.data_fattura or date.today(),
                total_debit=0.0,
                total_credit=0.0,
                status="error",
                error_message=f"Conto contabile non trovato per categoria '{invoice.category}'. Verifica il piano dei conti.",
            )
            self.db.add(entry)
            invoice.processing_status = "error"
            await self.db.flush()

            await self.publish_event(
                "journal.entry.error",
                {
                    "invoice_id": str(invoice_id),
                    "error": "pending_accounting",
                    "category": invoice.category,
                },
                tenant_id,
            )

            return {
                "status": "error",
                "error": "pending_accounting",
                "message": f"Conto contabile non trovato per categoria '{invoice.category}'",
            }

        expense_code, expense_name = account_mapping

        # Build journal lines based on invoice data
        lines = []
        description = f"Fattura {invoice.numero_fattura} - {invoice.emittente_nome or 'N/A'}"

        importo_netto = invoice.importo_netto or 0.0
        importo_iva = invoice.importo_iva or 0.0
        importo_totale = invoice.importo_totale or 0.0

        # Check for multi-aliquota from structured_data
        iva_rates = self._extract_iva_rates(invoice)

        if iva_rates and len(iva_rates) > 1:
            # Multi-aliquota: separate IVA lines per rate
            lines = self._build_multi_aliquota_lines(
                expense_code, expense_name, iva_rates, description
            )
        else:
            # Single IVA rate
            # DARE: expense account (netto)
            lines.append(JournalLine(
                account_code=expense_code,
                account_name=expense_name,
                debit=round(importo_netto, 2),
                credit=0.0,
                description=f"Costo netto - {description}",
            ))

            # DARE: IVA credito
            if importo_iva > 0:
                lines.append(JournalLine(
                    account_code=IVA_CREDITO_CODE,
                    account_name=IVA_CREDITO_NAME,
                    debit=round(importo_iva, 2),
                    credit=0.0,
                    description=f"IVA credito - {description}",
                ))

            # AVERE: Fornitori (totale)
            lines.append(JournalLine(
                account_code=FORNITORI_CODE,
                account_name=FORNITORI_NAME,
                debit=0.0,
                credit=round(importo_totale, 2),
                description=f"Debito fornitore - {description}",
            ))

        # Check for reverse charge (TD17, TD18, TD19 or document_type indicators)
        if self._is_reverse_charge(invoice):
            lines = self._add_reverse_charge_lines(lines, importo_iva, description)

        # Calculate totals
        total_debit = round(sum(line.debit for line in lines), 2)
        total_credit = round(sum(line.credit for line in lines), 2)

        # Validate balance
        if abs(total_debit - total_credit) > 0.01:
            entry = JournalEntry(
                tenant_id=tenant_id,
                invoice_id=invoice_id,
                description=description,
                entry_date=invoice.data_fattura or date.today(),
                total_debit=total_debit,
                total_credit=total_credit,
                status="error",
                error_message=f"Sbilanciamento dare/avere: dare={total_debit}, avere={total_credit}",
            )
            self.db.add(entry)
            invoice.processing_status = "error"
            await self.db.flush()

            await self.publish_event(
                "journal.entry.error",
                {
                    "invoice_id": str(invoice_id),
                    "error": "unbalanced",
                    "total_debit": total_debit,
                    "total_credit": total_credit,
                },
                tenant_id,
            )

            return {
                "status": "error",
                "error": "unbalanced",
                "message": f"Sbilanciamento dare/avere: dare={total_debit}, avere={total_credit}",
            }

        # Create journal entry
        entry = JournalEntry(
            tenant_id=tenant_id,
            invoice_id=invoice_id,
            description=description,
            entry_date=invoice.data_fattura or date.today(),
            total_debit=total_debit,
            total_credit=total_credit,
            status="posted",
        )
        self.db.add(entry)
        await self.db.flush()

        # Create journal lines
        for line in lines:
            line.entry_id = entry.id
            self.db.add(line)

        # Update invoice status
        invoice.processing_status = "registered"
        await self.db.flush()

        # Publish event
        await self.publish_event(
            "journal.entry.created",
            {
                "entry_id": str(entry.id),
                "invoice_id": str(invoice_id),
                "total_debit": total_debit,
                "total_credit": total_credit,
                "lines_count": len(lines),
            },
            tenant_id,
        )

        return {
            "status": "posted",
            "entry_id": str(entry.id),
            "total_debit": total_debit,
            "total_credit": total_credit,
            "lines_count": len(lines),
            "message": "Scrittura contabile registrata con successo",
        }

    def _extract_iva_rates(self, invoice: Invoice) -> list[dict] | None:
        """Extract IVA rates from structured_data if available."""
        if not invoice.structured_data:
            return None

        iva_lines = invoice.structured_data.get("iva_lines")
        if not iva_lines or not isinstance(iva_lines, list):
            return None

        return iva_lines

    def _build_multi_aliquota_lines(
        self,
        expense_code: str,
        expense_name: str,
        iva_rates: list[dict],
        description: str,
    ) -> list[JournalLine]:
        """Build journal lines for multi-aliquota invoice."""
        lines = []
        total_netto = 0.0
        total_iva = 0.0
        total_importo = 0.0

        for rate_info in iva_rates:
            imponibile = rate_info.get("imponibile", 0.0)
            imposta = rate_info.get("imposta", 0.0)
            aliquota = rate_info.get("aliquota", 0.0)

            # DARE: expense for this rate portion
            lines.append(JournalLine(
                account_code=expense_code,
                account_name=expense_name,
                debit=round(imponibile, 2),
                credit=0.0,
                description=f"Costo netto (IVA {aliquota}%) - {description}",
            ))

            # DARE: IVA credito for this rate
            if imposta > 0:
                lines.append(JournalLine(
                    account_code=IVA_CREDITO_CODE,
                    account_name=IVA_CREDITO_NAME,
                    debit=round(imposta, 2),
                    credit=0.0,
                    description=f"IVA credito {aliquota}% - {description}",
                ))

            total_netto += imponibile
            total_iva += imposta
            total_importo += imponibile + imposta

        # AVERE: Fornitori (totale)
        lines.append(JournalLine(
            account_code=FORNITORI_CODE,
            account_name=FORNITORI_NAME,
            debit=0.0,
            credit=round(total_importo, 2),
            description=f"Debito fornitore - {description}",
        ))

        return lines

    def _is_reverse_charge(self, invoice: Invoice) -> bool:
        """Check if invoice requires reverse charge treatment."""
        # Reverse charge document types
        rc_types = {"TD17", "TD18", "TD19"}
        if invoice.document_type in rc_types:
            return True

        # Check structured_data for reverse charge indicator
        if invoice.structured_data and invoice.structured_data.get("reverse_charge"):
            return True

        return False

    def _add_reverse_charge_lines(
        self,
        lines: list[JournalLine],
        importo_iva: float,
        description: str,
    ) -> list[JournalLine]:
        """Add reverse charge IVA lines (double entry: credito + debito)."""
        # Add IVA debito (AVERE side already has IVA credito in DARE)
        lines.append(JournalLine(
            account_code=IVA_DEBITO_CODE,
            account_name=IVA_DEBITO_NAME,
            debit=0.0,
            credit=round(importo_iva, 2),
            description=f"IVA debito reverse charge - {description}",
        ))

        # Add matching IVA credito DARE entry for reverse charge
        lines.append(JournalLine(
            account_code=IVA_CREDITO_CODE,
            account_name=IVA_CREDITO_NAME,
            debit=round(importo_iva, 2),
            credit=0.0,
            description=f"IVA credito reverse charge - {description}",
        ))

        return lines
