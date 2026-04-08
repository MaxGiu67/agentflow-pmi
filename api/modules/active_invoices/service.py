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

    async def create_invoice_multiline(
        self,
        tenant_id: uuid.UUID,
        cliente: dict,
        linee: list[dict],
        data_fattura: date,
        document_type: str = "TD01",
        causale: str | None = None,
        modalita_pagamento: str | None = None,
        condizioni_pagamento: str | None = None,
        giorni_pagamento: int | None = None,
        iban: str | None = None,
        original_invoice_numero: str | None = None,
        original_invoice_date: date | None = None,
    ) -> dict:
        """Create invoice with multiple line items and full XML (US-41)."""
        result = await self.db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()
        if not tenant:
            raise ValueError("Tenant non trovato")

        year = data_fattura.year
        numero = await self._generate_numero_fattura(tenant_id, year, document_type)

        # Calculate totals from lines
        tot_netto = 0.0
        tot_iva = 0.0
        for linea in linee:
            qta = linea.get("quantita", 1.0)
            prezzo = linea.get("prezzo_unitario", 0)
            aliquota = linea.get("aliquota_iva", 22.0)
            tot_linea = round(qta * prezzo, 2)
            tot_netto += tot_linea
            tot_iva += round(tot_linea * aliquota / 100, 2)
        tot_totale = round(tot_netto + tot_iva, 2)

        # Generate full XML
        raw_xml = self._generate_fatturapa_xml_multiline(
            tenant=tenant, numero=numero, doc_type=document_type,
            cliente_piva=cliente.get("piva"),
            cliente_nome=cliente.get("denominazione", ""),
            cliente_codice_sdi=cliente.get("codice_sdi", "0000000"),
            cliente_cf=cliente.get("codice_fiscale"),
            cliente_indirizzo=cliente.get("indirizzo"),
            cliente_cap=cliente.get("cap"),
            cliente_comune=cliente.get("comune"),
            cliente_provincia=cliente.get("provincia"),
            cliente_nazione=cliente.get("nazione", "IT"),
            cliente_pec=cliente.get("pec"),
            data_fattura=data_fattura, linee=linee,
            causale=causale,
            modalita_pagamento=modalita_pagamento,
            iban=iban, giorni_pagamento=giorni_pagamento,
            original_numero=original_invoice_numero,
            original_date=original_invoice_date,
        )

        # Use first line's aliquota as the "main" one for the DB record
        main_aliquota = linee[0].get("aliquota_iva", 22.0) if linee else 22.0

        invoice = ActiveInvoice(
            tenant_id=tenant_id,
            numero_fattura=numero,
            document_type=document_type,
            cliente_piva=cliente.get("piva", ""),
            cliente_nome=cliente.get("denominazione", ""),
            cliente_codice_sdi=cliente.get("codice_sdi"),
            data_fattura=data_fattura,
            importo_netto=round(tot_netto, 2),
            aliquota_iva=main_aliquota,
            importo_iva=round(tot_iva, 2),
            importo_totale=tot_totale,
            descrizione=linee[0].get("descrizione", "") if linee else "",
            raw_xml=raw_xml,
            sdi_status="draft",
            original_invoice_numero=original_invoice_numero,
            original_invoice_date=original_invoice_date,
        )
        self.db.add(invoice)
        await self.db.flush()

        logger.info("Created multiline invoice %s (%d lines) for tenant %s", numero, len(linee), tenant_id)
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
        """Generate FatturaPA 1.2.2 XML — backward compatible single-line."""
        linee = [{"descrizione": descrizione, "quantita": 1.0, "prezzo_unitario": importo_netto, "aliquota_iva": aliquota_iva}]
        return self._generate_fatturapa_xml_multiline(
            tenant=tenant, numero=numero, doc_type=doc_type,
            cliente_piva=cliente_piva, cliente_nome=cliente_nome,
            cliente_codice_sdi=cliente_codice_sdi, cliente_cf=None,
            cliente_indirizzo=None, cliente_cap=None, cliente_comune=None,
            cliente_provincia=None, cliente_nazione="IT", cliente_pec=None,
            data_fattura=data_fattura, linee=linee,
            causale=None, modalita_pagamento=None, iban=None, giorni_pagamento=None,
            original_numero=original_numero, original_date=original_date,
        )

    def _generate_fatturapa_xml_multiline(
        self,
        tenant: Tenant,
        numero: str,
        doc_type: str,
        cliente_piva: str | None,
        cliente_nome: str,
        cliente_codice_sdi: str,
        cliente_cf: str | None,
        cliente_indirizzo: str | None,
        cliente_cap: str | None,
        cliente_comune: str | None,
        cliente_provincia: str | None,
        cliente_nazione: str,
        cliente_pec: str | None,
        data_fattura: date,
        linee: list[dict],
        causale: str | None = None,
        modalita_pagamento: str | None = None,
        iban: str | None = None,
        giorni_pagamento: int | None = None,
        original_numero: str | None = None,
        original_date: date | None = None,
    ) -> str:
        """Generate FatturaPA 1.2.2 XML with multi-line, sede, regime, payment."""
        from xml.sax.saxutils import escape

        piva = (tenant.piva or "").replace("IT", "")
        data_str = data_fattura.isoformat() if isinstance(data_fattura, date) else str(data_fattura)
        regime = getattr(tenant, "regime_fiscale_sdi", None) or "RF01"
        codice_sdi = cliente_codice_sdi or "0000000"

        # ── CedentePrestatore (emittente) ──
        cf_cedente = ""
        if getattr(tenant, "codice_fiscale", None):
            cf_cedente = f"\n          <CodiceFiscale>{tenant.codice_fiscale}</CodiceFiscale>"

        sede_cedente = ""
        if getattr(tenant, "sede_indirizzo", None):
            sede_cedente = f"""
      <Sede>
        <Indirizzo>{escape(tenant.sede_indirizzo)}</Indirizzo>
        {f'<NumeroCivico>{escape(tenant.sede_numero_civico)}</NumeroCivico>' if tenant.sede_numero_civico else ''}
        <CAP>{tenant.sede_cap or '00000'}</CAP>
        <Comune>{escape(tenant.sede_comune or '')}</Comune>
        {f'<Provincia>{tenant.sede_provincia}</Provincia>' if tenant.sede_provincia else ''}
        <Nazione>{tenant.sede_nazione or 'IT'}</Nazione>
      </Sede>"""

        rea_block = ""
        if getattr(tenant, "rea_numero", None):
            rea_block = f"""
      <IscrizioneREA>
        <Ufficio>{tenant.rea_ufficio or ''}</Ufficio>
        <NumeroREA>{tenant.rea_numero}</NumeroREA>
        {f'<CapitaleSociale>{tenant.rea_capitale_sociale:.2f}</CapitaleSociale>' if tenant.rea_capitale_sociale else ''}
        {f'<SocioUnico>{tenant.rea_socio_unico}</SocioUnico>' if tenant.rea_socio_unico else ''}
        <StatoLiquidazione>{getattr(tenant, 'rea_stato_liquidazione', 'LN') or 'LN'}</StatoLiquidazione>
      </IscrizioneREA>"""

        # ── CessionarioCommittente (cliente) ──
        id_fiscale_cliente = ""
        if cliente_piva:
            cp = cliente_piva.replace("IT", "")
            nazione_c = "IT" if not cliente_piva.startswith(("DE", "FR", "ES", "GB")) else cliente_piva[:2]
            id_fiscale_cliente = f"""
          <IdFiscaleIVA>
            <IdPaese>{nazione_c}</IdPaese>
            <IdCodice>{cp}</IdCodice>
          </IdFiscaleIVA>"""

        cf_cliente = ""
        if cliente_cf:
            cf_cliente = f"\n          <CodiceFiscale>{cliente_cf}</CodiceFiscale>"

        sede_cliente = ""
        if cliente_indirizzo:
            sede_cliente = f"""
      <Sede>
        <Indirizzo>{escape(cliente_indirizzo)}</Indirizzo>
        <CAP>{cliente_cap or '00000'}</CAP>
        <Comune>{escape(cliente_comune or '')}</Comune>
        {f'<Provincia>{cliente_provincia}</Provincia>' if cliente_provincia else ''}
        <Nazione>{cliente_nazione or 'IT'}</Nazione>
      </Sede>"""

        pec_dest = ""
        if cliente_pec and codice_sdi == "0000000":
            pec_dest = f"\n      <PECDestinatario>{cliente_pec}</PECDestinatario>"

        # ── DatiGeneraliDocumento ──
        causale_xml = ""
        if causale:
            causale_xml = f"\n        <Causale>{escape(causale[:200])}</Causale>"

        dati_collegati = ""
        if doc_type == "TD04" and original_numero:
            orig_date_str = original_date.isoformat() if original_date else data_str
            dati_collegati = f"""
      <DatiFattureCollegate>
        <IdDocumento>{original_numero}</IdDocumento>
        <Data>{orig_date_str}</Data>
      </DatiFattureCollegate>"""

        # ── DettaglioLinee (multi-line) ──
        dettaglio_xml = ""
        riepilogo: dict[str, dict] = {}  # key = "aliquota|natura"

        for i, linea in enumerate(linee, 1):
            qta = linea.get("quantita", 1.0)
            prezzo = linea.get("prezzo_unitario", 0)
            aliquota = linea.get("aliquota_iva", 22.0)
            natura = linea.get("natura")
            prezzo_totale = round(qta * prezzo, 2)
            um = linea.get("unita_misura")

            natura_xml = f"\n        <Natura>{natura}</Natura>" if natura and aliquota == 0 else ""
            um_xml = f"\n        <UnitaMisura>{um}</UnitaMisura>" if um else ""

            dettaglio_xml += f"""
      <DettaglioLinee>
        <NumeroLinea>{i}</NumeroLinea>
        <Descrizione>{escape((linea.get('descrizione') or 'Prestazione')[:1000])}</Descrizione>
        <Quantita>{qta:.2f}</Quantita>{um_xml}
        <PrezzoUnitario>{prezzo:.2f}</PrezzoUnitario>
        <PrezzoTotale>{prezzo_totale:.2f}</PrezzoTotale>
        <AliquotaIVA>{aliquota:.2f}</AliquotaIVA>{natura_xml}
      </DettaglioLinee>"""

            # Accumulate riepilogo by aliquota+natura
            key = f"{aliquota:.2f}|{natura or ''}"
            if key not in riepilogo:
                riepilogo[key] = {"aliquota": aliquota, "natura": natura, "imponibile": 0, "imposta": 0}
            riepilogo[key]["imponibile"] += prezzo_totale
            riepilogo[key]["imposta"] += round(prezzo_totale * aliquota / 100, 2)

        # ── DatiRiepilogo ──
        riepilogo_xml = ""
        for r in riepilogo.values():
            natura_r = f"\n        <Natura>{r['natura']}</Natura>" if r["natura"] and r["aliquota"] == 0 else ""
            riepilogo_xml += f"""
      <DatiRiepilogo>
        <AliquotaIVA>{r['aliquota']:.2f}</AliquotaIVA>{natura_r}
        <ImponibileImporto>{r['imponibile']:.2f}</ImponibileImporto>
        <Imposta>{r['imposta']:.2f}</Imposta>
      </DatiRiepilogo>"""

        tot_imponibile = sum(r["imponibile"] for r in riepilogo.values())
        tot_imposta = sum(r["imposta"] for r in riepilogo.values())
        importo_totale = round(tot_imponibile + tot_imposta, 2)

        # ── DatiPagamento ──
        mp = modalita_pagamento or getattr(tenant, "modalita_pagamento", None) or "MP05"
        cond = getattr(tenant, "condizioni_pagamento", None) or "TP02"
        gg = giorni_pagamento or getattr(tenant, "giorni_pagamento", None) or 30
        iban_val = iban or getattr(tenant, "iban", None)
        banca = getattr(tenant, "banca_nome", None)

        from datetime import timedelta
        scadenza = (data_fattura + timedelta(days=gg)).isoformat()

        iban_xml = f"\n        <IBAN>{iban_val}</IBAN>" if iban_val else ""
        banca_xml = f"\n        <IstitutoFinanziario>{escape(banca)}</IstitutoFinanziario>" if banca else ""
        bic_xml = ""
        if getattr(tenant, "bic", None):
            bic_xml = f"\n        <BIC>{tenant.bic}</BIC>"

        pagamento_xml = f"""
    <DatiPagamento>
      <CondizioniPagamento>{cond}</CondizioniPagamento>
      <DettaglioPagamento>
        <ModalitaPagamento>{mp}</ModalitaPagamento>
        <DataScadenzaPagamento>{scadenza}</DataScadenzaPagamento>
        <ImportoPagamento>{importo_totale:.2f}</ImportoPagamento>{iban_xml}{banca_xml}{bic_xml}
      </DettaglioPagamento>
    </DatiPagamento>"""

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
      <CodiceDestinatario>{codice_sdi}</CodiceDestinatario>{pec_dest}
    </DatiTrasmissione>
    <CedentePrestatore>
      <DatiAnagrafici>
        <IdFiscaleIVA>
          <IdPaese>IT</IdPaese>
          <IdCodice>{piva}</IdCodice>
        </IdFiscaleIVA>{cf_cedente}
        <Anagrafica>
          <Denominazione>{escape(tenant.name)}</Denominazione>
        </Anagrafica>
        <RegimeFiscale>{regime}</RegimeFiscale>
      </DatiAnagrafici>{sede_cedente}{rea_block}
    </CedentePrestatore>
    <CessionarioCommittente>
      <DatiAnagrafici>{id_fiscale_cliente}{cf_cliente}
        <Anagrafica>
          <Denominazione>{escape(cliente_nome)}</Denominazione>
        </Anagrafica>
      </DatiAnagrafici>{sede_cliente}
    </CessionarioCommittente>
  </FatturaElettronicaHeader>
  <FatturaElettronicaBody>
    <DatiGenerali>
      <DatiGeneraliDocumento>
        <TipoDocumento>{doc_type}</TipoDocumento>
        <Divisa>EUR</Divisa>
        <Data>{data_str}</Data>
        <Numero>{numero}</Numero>
        <ImportoTotaleDocumento>{importo_totale:.2f}</ImportoTotaleDocumento>{causale_xml}
      </DatiGeneraliDocumento>{dati_collegati}
    </DatiGenerali>
    <DatiBeniServizi>{dettaglio_xml}{riepilogo_xml}
    </DatiBeniServizi>{pagamento_xml}
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
