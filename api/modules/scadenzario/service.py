"""Service layer for Scadenzario, Cash Flow, Fidi, Anticipi (US-72 to US-82)."""

import logging
import uuid
from datetime import date, timedelta

from sqlalchemy import select, and_, func, extract, case
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import Invoice, Scadenza, BankAccount, Tenant

logger = logging.getLogger(__name__)

DEFAULT_GIORNI_PAGAMENTO = 30


class ScadenzarioService:
    """Business logic for payment deadlines (scadenze)."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ============================================================
    # US-72: Generazione automatica scadenze da fatture
    # ============================================================

    async def generate_from_invoice(self, invoice: Invoice) -> Scadenza | None:
        """AC-72.1/72.2: Generate a Scadenza from an invoice.

        - Fattura attiva → tipo "attivo" (credito da incassare)
        - Fattura passiva → tipo "passivo" (debito da pagare)
        - Data scadenza = data_fattura + giorni_pagamento (default 30)
        - Importi: lordo, netto, IVA separati
        - Banca appoggio = IBAN della fattura
        """
        if not invoice.data_fattura:
            return None

        # Check if scadenza already exists for this invoice
        existing = await self.db.execute(
            select(Scadenza).where(
                Scadenza.tenant_id == invoice.tenant_id,
                Scadenza.source_type == "fattura",
                Scadenza.source_id == invoice.id,
            )
        )
        if existing.scalar_one_or_none():
            return None  # Already generated

        # Determine tipo
        if invoice.type == "attiva":
            tipo = "attivo"
            controparte = self._get_cliente_nome(invoice)
        else:
            tipo = "passivo"
            controparte = invoice.emittente_nome or invoice.emittente_piva

        # AC-72.5: Default 30gg if giorni_pagamento not specified
        giorni = self._get_giorni_pagamento(invoice)
        data_scadenza = invoice.data_fattura + timedelta(days=giorni)

        # AC-72.3: Importi separati
        importo_lordo = invoice.importo_totale or 0.0
        importo_netto = invoice.importo_netto or importo_lordo
        importo_iva = invoice.importo_iva or 0.0

        # AC-72.4: Banca di appoggio
        banca_id = await self._find_banca_appoggio(invoice)

        scadenza = Scadenza(
            tenant_id=invoice.tenant_id,
            tipo=tipo,
            source_type="fattura",
            source_id=invoice.id,
            controparte=controparte,
            importo_lordo=round(importo_lordo, 2),
            importo_netto=round(importo_netto, 2),
            importo_iva=round(importo_iva, 2),
            data_scadenza=data_scadenza,
            stato="aperto",
            banca_appoggio_id=banca_id,
        )
        self.db.add(scadenza)
        await self.db.flush()
        return scadenza

    async def generate_all_missing(self, tenant_id: uuid.UUID) -> int:
        """Generate scadenze for all invoices that don't have one yet."""
        # Find invoices without a corresponding scadenza
        subq = select(Scadenza.source_id).where(
            Scadenza.tenant_id == tenant_id,
            Scadenza.source_type == "fattura",
        )
        result = await self.db.execute(
            select(Invoice).where(
                Invoice.tenant_id == tenant_id,
                Invoice.data_fattura.isnot(None),
                Invoice.id.notin_(subq),
            )
        )
        invoices = result.scalars().all()

        count = 0
        for inv in invoices:
            sc = await self.generate_from_invoice(inv)
            if sc:
                count += 1
        return count

    # ============================================================
    # US-73: Scadenzario Attivo (crediti da incassare)
    # ============================================================

    async def list_attivo(
        self,
        tenant_id: uuid.UUID,
        stato: str | None = None,
        controparte: str | None = None,
        data_da: date | None = None,
        data_a: date | None = None,
    ) -> dict:
        """AC-73.1 to AC-73.6: List active deadlines (crediti).

        Returns sorted list with colors, totals per stato.
        """
        return await self._list_scadenze(
            tenant_id, "attivo", stato, controparte, data_da, data_a,
        )

    # ============================================================
    # US-74: Scadenzario Passivo (debiti da pagare)
    # ============================================================

    async def list_passivo(
        self,
        tenant_id: uuid.UUID,
        stato: str | None = None,
        controparte: str | None = None,
        data_da: date | None = None,
        data_a: date | None = None,
    ) -> dict:
        """AC-74.1 to AC-74.5: List passive deadlines (debiti)."""
        return await self._list_scadenze(
            tenant_id, "passivo", stato, controparte, data_da, data_a,
        )

    # ============================================================
    # Shared list logic
    # ============================================================

    async def _list_scadenze(
        self,
        tenant_id: uuid.UUID,
        tipo: str,
        stato: str | None = None,
        controparte: str | None = None,
        data_da: date | None = None,
        data_a: date | None = None,
    ) -> dict:
        """Generic list with filters, colors, totals."""
        query = select(Scadenza).where(
            Scadenza.tenant_id == tenant_id,
            Scadenza.tipo == tipo,
        )

        if stato:
            query = query.where(Scadenza.stato == stato)
        if controparte:
            query = query.where(Scadenza.controparte.ilike(f"%{controparte}%"))
        if data_da:
            query = query.where(Scadenza.data_scadenza >= data_da)
        if data_a:
            query = query.where(Scadenza.data_scadenza <= data_a)

        query = query.order_by(Scadenza.data_scadenza.asc())

        result = await self.db.execute(query)
        scadenze = result.scalars().all()

        today = date.today()
        items = []
        totals: dict[str, float] = {}

        for s in scadenze:
            giorni_residui = (s.data_scadenza - today).days if s.stato == "aperto" else 0

            # AC-73.4/74.4: Color coding
            if s.stato in ("pagato", "incassato"):
                colore = "green"
            elif s.stato == "insoluto":
                colore = "red"
            elif s.stato == "aperto" and giorni_residui < 0:
                colore = "red"  # scaduta
            elif s.stato == "aperto" and giorni_residui <= 7:
                colore = "yellow"  # scade entro 7gg
            else:
                colore = "green"

            items.append({
                "id": str(s.id),
                "controparte": s.controparte,
                "source_type": s.source_type,
                "source_id": str(s.source_id) if s.source_id else None,
                "importo_lordo": s.importo_lordo,
                "importo_netto": s.importo_netto,
                "importo_iva": s.importo_iva,
                "data_scadenza": s.data_scadenza.isoformat(),
                "data_pagamento": s.data_pagamento.isoformat() if s.data_pagamento else None,
                "giorni_residui": giorni_residui,
                "stato": s.stato,
                "importo_pagato": s.importo_pagato,
                "anticipata": s.anticipata,
                "colore": colore,
            })

            # AC-73.6/74.5: Totals per stato
            key = s.stato
            totals[key] = totals.get(key, 0.0) + s.importo_lordo

        # Round totals
        totals = {k: round(v, 2) for k, v in totals.items()}

        return {
            "tipo": tipo,
            "count": len(items),
            "items": items,
            "totals": totals,
        }

    # ============================================================
    # US-75: Chiusura scadenze da movimenti banca
    # ============================================================

    async def chiudi_scadenza(
        self,
        scadenza_id: uuid.UUID,
        importo_pagato: float,
        data_pagamento: date,
    ) -> dict:
        """AC-75.1/75.2/75.3: Close a scadenza (full or partial).

        - Full payment → stato "incassato" (attivo) or "pagato" (passivo)
        - Partial → stato "parziale" with residuo
        - AC-75.4: If anticipata, return info for plafond release
        """
        result = await self.db.execute(
            select(Scadenza).where(Scadenza.id == scadenza_id)
        )
        scadenza = result.scalar_one_or_none()
        if not scadenza:
            return {"error": "Scadenza non trovata"}

        scadenza.importo_pagato = round(
            (scadenza.importo_pagato or 0.0) + importo_pagato, 2
        )
        scadenza.data_pagamento = data_pagamento

        residuo = round(scadenza.importo_lordo - scadenza.importo_pagato, 2)

        if residuo <= 0.01:
            # AC-75.1/75.2: Full payment
            scadenza.stato = "incassato" if scadenza.tipo == "attivo" else "pagato"
            scadenza.importo_pagato = scadenza.importo_lordo
        else:
            # AC-75.3: Partial payment
            scadenza.stato = "parziale"

        await self.db.flush()

        response = {
            "id": str(scadenza.id),
            "stato": scadenza.stato,
            "importo_pagato": scadenza.importo_pagato,
            "residuo": max(0, residuo),
        }

        # AC-75.4: If anticipata, signal plafond release
        if scadenza.anticipata and scadenza.anticipo_id:
            response["anticipo_da_scaricare"] = str(scadenza.anticipo_id)

        return response

    # ============================================================
    # US-76: Gestione insoluti
    # ============================================================

    async def segna_insoluto(
        self,
        scadenza_id: uuid.UUID,
    ) -> dict:
        """AC-76.1 to AC-76.4: Mark a scadenza as insoluto.

        - Only on scadenze attive scadute
        - If anticipata, warn about bank recharge
        - Badge rosso (handled by colore logic)
        - Stays in scadenzario until resolved
        """
        result = await self.db.execute(
            select(Scadenza).where(Scadenza.id == scadenza_id)
        )
        scadenza = result.scalar_one_or_none()
        if not scadenza:
            return {"error": "Scadenza non trovata"}

        if scadenza.tipo != "attivo":
            return {"error": "Solo scadenze attive possono essere segnate come insolute"}

        if scadenza.stato not in ("aperto", "parziale"):
            return {"error": f"Stato '{scadenza.stato}' non valido per insoluto"}

        scadenza.stato = "insoluto"
        await self.db.flush()

        response = {
            "id": str(scadenza.id),
            "stato": "insoluto",
            "controparte": scadenza.controparte,
        }

        # AC-76.2: If anticipata, warn
        if scadenza.anticipata:
            response["warning"] = (
                "Attenzione: questa fattura era anticipata. "
                "La banca riaddebiterà l'importo anticipato."
            )
            if scadenza.anticipo_id:
                response["anticipo_id"] = str(scadenza.anticipo_id)

        return response

    # ============================================================
    # US-77: Cash flow previsionale
    # ============================================================

    async def cash_flow_previsionale(
        self,
        tenant_id: uuid.UUID,
        giorni: int = 30,
        soglia_alert: float | None = None,
    ) -> dict:
        """AC-77.1 to AC-77.5: Cash flow from scadenzario.

        Calcolo: saldo_banca + incassi_previsti - pagamenti_previsti
        """
        today = date.today()
        data_limite = today + timedelta(days=giorni)

        # Current bank balance (sum of all connected accounts)
        from api.db.models import BankAccount
        bank_result = await self.db.execute(
            select(func.coalesce(func.sum(BankAccount.balance), 0.0)).where(
                BankAccount.tenant_id == tenant_id,
                BankAccount.status == "connected",
            )
        )
        saldo_banca = round(float(bank_result.scalar() or 0), 2)

        # Incassi previsti (scadenze attive aperte nel periodo)
        incassi_result = await self.db.execute(
            select(
                func.coalesce(func.sum(Scadenza.importo_lordo - Scadenza.importo_pagato), 0.0)
            ).where(
                Scadenza.tenant_id == tenant_id,
                Scadenza.tipo == "attivo",
                Scadenza.stato.in_(["aperto", "parziale"]),
                Scadenza.data_scadenza <= data_limite,
                Scadenza.data_scadenza >= today,
            )
        )
        incassi_previsti = round(float(incassi_result.scalar() or 0), 2)

        # Pagamenti previsti (scadenze passive aperte nel periodo)
        pagamenti_result = await self.db.execute(
            select(
                func.coalesce(func.sum(Scadenza.importo_lordo - Scadenza.importo_pagato), 0.0)
            ).where(
                Scadenza.tenant_id == tenant_id,
                Scadenza.tipo == "passivo",
                Scadenza.stato.in_(["aperto", "parziale"]),
                Scadenza.data_scadenza <= data_limite,
                Scadenza.data_scadenza >= today,
            )
        )
        pagamenti_previsti = round(float(pagamenti_result.scalar() or 0), 2)

        saldo_previsto = round(saldo_banca + incassi_previsti - pagamenti_previsti, 2)

        # AC-77.3: Daily/weekly breakdown for chart
        breakdown = await self._cash_flow_breakdown(
            tenant_id, today, data_limite, saldo_banca,
        )

        # AC-77.4: Alert
        alert = None
        if soglia_alert is not None and saldo_previsto < soglia_alert:
            alert = {
                "tipo": "liquidita_insufficiente",
                "messaggio": (
                    f"Il saldo previsto ({saldo_previsto:.2f} EUR) "
                    f"scende sotto la soglia ({soglia_alert:.2f} EUR) "
                    f"nei prossimi {giorni} giorni."
                ),
            }

        return {
            "giorni": giorni,
            "saldo_banca_attuale": saldo_banca,
            "incassi_previsti": incassi_previsti,
            "pagamenti_previsti": pagamenti_previsti,
            "saldo_previsto": saldo_previsto,
            "breakdown": breakdown,
            "alert": alert,
        }

    async def _cash_flow_breakdown(
        self,
        tenant_id: uuid.UUID,
        data_inizio: date,
        data_fine: date,
        saldo_iniziale: float,
    ) -> list[dict]:
        """Build daily cash flow breakdown for chart."""
        # Get all scadenze in period
        result = await self.db.execute(
            select(Scadenza).where(
                Scadenza.tenant_id == tenant_id,
                Scadenza.stato.in_(["aperto", "parziale"]),
                Scadenza.data_scadenza >= data_inizio,
                Scadenza.data_scadenza <= data_fine,
            ).order_by(Scadenza.data_scadenza)
        )
        scadenze = result.scalars().all()

        # Group by week
        weeks: dict[str, dict] = {}
        current = data_inizio
        while current <= data_fine:
            week_start = current - timedelta(days=current.weekday())
            week_key = week_start.isoformat()
            if week_key not in weeks:
                weeks[week_key] = {"settimana": week_key, "incassi": 0.0, "pagamenti": 0.0}
            current += timedelta(days=1)

        for s in scadenze:
            residuo = s.importo_lordo - (s.importo_pagato or 0)
            week_start = s.data_scadenza - timedelta(days=s.data_scadenza.weekday())
            week_key = week_start.isoformat()
            if week_key in weeks:
                if s.tipo == "attivo":
                    weeks[week_key]["incassi"] += residuo
                else:
                    weeks[week_key]["pagamenti"] += residuo

        # Build progressive balance
        breakdown = []
        saldo = saldo_iniziale
        for wk in sorted(weeks.values(), key=lambda w: w["settimana"]):
            saldo += wk["incassi"] - wk["pagamenti"]
            breakdown.append({
                "settimana": wk["settimana"],
                "incassi": round(wk["incassi"], 2),
                "pagamenti": round(wk["pagamenti"], 2),
                "saldo_progressivo": round(saldo, 2),
            })

        return breakdown

    # ============================================================
    # US-78: Cash flow per banca
    # ============================================================

    async def cash_flow_per_banca(
        self,
        tenant_id: uuid.UUID,
        giorni: int = 30,
    ) -> list[dict]:
        """AC-78.1 to AC-78.4: Cash flow per ogni conto bancario."""
        from api.db.models import BankAccount

        # Get all connected bank accounts
        result = await self.db.execute(
            select(BankAccount).where(
                BankAccount.tenant_id == tenant_id,
                BankAccount.status == "connected",
            )
        )
        banks = result.scalars().all()

        today = date.today()
        data_limite = today + timedelta(days=giorni)

        per_banca = []
        for bank in banks:
            saldo = bank.balance or 0.0

            # AC-78.2: Incassi su questa banca (fatture con banca_appoggio_id = bank.id)
            inc_result = await self.db.execute(
                select(
                    func.coalesce(func.sum(Scadenza.importo_lordo - Scadenza.importo_pagato), 0.0)
                ).where(
                    Scadenza.tenant_id == tenant_id,
                    Scadenza.tipo == "attivo",
                    Scadenza.stato.in_(["aperto", "parziale"]),
                    Scadenza.banca_appoggio_id == bank.id,
                    Scadenza.data_scadenza >= today,
                    Scadenza.data_scadenza <= data_limite,
                )
            )
            incassi = round(float(inc_result.scalar() or 0), 2)

            # AC-78.3: Pagamenti da questa banca (passivi senza banca specifica → split equal, or with banca)
            pag_result = await self.db.execute(
                select(
                    func.coalesce(func.sum(Scadenza.importo_lordo - Scadenza.importo_pagato), 0.0)
                ).where(
                    Scadenza.tenant_id == tenant_id,
                    Scadenza.tipo == "passivo",
                    Scadenza.stato.in_(["aperto", "parziale"]),
                    Scadenza.banca_appoggio_id == bank.id,
                    Scadenza.data_scadenza >= today,
                    Scadenza.data_scadenza <= data_limite,
                )
            )
            pagamenti = round(float(pag_result.scalar() or 0), 2)

            saldo_previsto = round(saldo + incassi - pagamenti, 2)

            per_banca.append({
                "bank_id": str(bank.id),
                "bank_name": bank.bank_name,
                "iban": bank.iban,
                "saldo_attuale": round(saldo, 2),
                "incassi_previsti": incassi,
                "pagamenti_previsti": pagamenti,
                "saldo_previsto": saldo_previsto,
            })

        return per_banca

    # ============================================================
    # US-79: CRUD Fidi Bancari
    # ============================================================

    async def list_fidi(self, tenant_id: uuid.UUID) -> list[dict]:
        """AC-79.2: List fidi with plafond/utilizzato/disponibile."""
        from api.db.models import BankFacility, InvoiceAdvance, BankAccount

        result = await self.db.execute(
            select(BankFacility).where(
                BankFacility.tenant_id == tenant_id,
                BankFacility.attivo.is_(True),
            )
        )
        facilities = result.scalars().all()

        fidi = []
        for f in facilities:
            # Get bank name
            bank_result = await self.db.execute(
                select(BankAccount.bank_name).where(BankAccount.id == f.bank_account_id)
            )
            bank_name = bank_result.scalar() or "Sconosciuta"

            # AC-79.2: Calculate utilizzato from active advances
            used_result = await self.db.execute(
                select(func.coalesce(func.sum(InvoiceAdvance.importo_anticipato), 0.0)).where(
                    InvoiceAdvance.facility_id == f.id,
                    InvoiceAdvance.stato == "attivo",
                )
            )
            utilizzato = round(float(used_result.scalar() or 0), 2)
            disponibile = round(f.plafond - utilizzato, 2)

            fidi.append({
                "id": str(f.id),
                "bank_account_id": str(f.bank_account_id),
                "bank_name": bank_name,
                "tipo": f.tipo,
                "plafond": f.plafond,
                "utilizzato": utilizzato,
                "disponibile": disponibile,
                "percentuale_anticipo": f.percentuale_anticipo,
                "tasso_interesse_annuo": f.tasso_interesse_annuo,
                "commissione_presentazione_pct": f.commissione_presentazione_pct,
                "commissione_incasso": f.commissione_incasso,
                "commissione_insoluto": f.commissione_insoluto,
                "giorni_max": f.giorni_max,
            })

        return fidi

    async def create_fido(
        self,
        tenant_id: uuid.UUID,
        data: dict,
    ) -> dict:
        """AC-79.1: Create bank facility."""
        from api.db.models import BankFacility

        facility = BankFacility(
            tenant_id=tenant_id,
            bank_account_id=uuid.UUID(data["bank_account_id"]),
            tipo=data.get("tipo", "anticipo_fatture"),
            plafond=data["plafond"],
            percentuale_anticipo=data.get("percentuale_anticipo", 80.0),
            tasso_interesse_annuo=data.get("tasso_interesse_annuo", 0.0),
            commissione_presentazione_pct=data.get("commissione_presentazione_pct", 0.0),
            commissione_incasso=data.get("commissione_incasso", 0.0),
            commissione_insoluto=data.get("commissione_insoluto", 0.0),
            giorni_max=data.get("giorni_max", 120),
        )
        self.db.add(facility)
        await self.db.flush()
        return {"id": str(facility.id), "message": "Fido creato"}

    # ============================================================
    # US-80: Anticipo fattura — Presentazione
    # ============================================================

    async def presenta_anticipo(
        self,
        scadenza_id: uuid.UUID,
    ) -> dict:
        """AC-80.1 to AC-80.7: Present an invoice for advance.

        - From scadenzario attivo, on non-anticipated invoices
        - Shows: importo anticipabile, commissione, interessi stimati, costo totale
        - Same bank as appoggio
        - Checks plafond availability
        - Optional, can be added later
        """
        from api.db.models import BankFacility, InvoiceAdvance

        result = await self.db.execute(
            select(Scadenza).where(Scadenza.id == scadenza_id)
        )
        scadenza = result.scalar_one_or_none()
        if not scadenza:
            return {"error": "Scadenza non trovata"}
        if scadenza.tipo != "attivo":
            return {"error": "Solo fatture attive possono essere anticipate"}
        if scadenza.anticipata:
            return {"error": "Fattura già anticipata"}
        if scadenza.stato not in ("aperto", "parziale"):
            return {"error": f"Stato '{scadenza.stato}' non valido per anticipo"}

        # AC-80.3: Find facility on same bank as appoggio
        if not scadenza.banca_appoggio_id:
            return {"error": "Nessuna banca di appoggio — impossibile anticipare"}

        fac_result = await self.db.execute(
            select(BankFacility).where(
                BankFacility.tenant_id == scadenza.tenant_id,
                BankFacility.bank_account_id == scadenza.banca_appoggio_id,
                BankFacility.attivo.is_(True),
            )
        )
        facility = fac_result.scalar_one_or_none()
        if not facility:
            return {"error": "Nessun fido attivo sulla banca di appoggio"}

        # AC-80.4: Check plafond
        used_result = await self.db.execute(
            select(func.coalesce(func.sum(InvoiceAdvance.importo_anticipato), 0.0)).where(
                InvoiceAdvance.facility_id == facility.id,
                InvoiceAdvance.stato == "attivo",
            )
        )
        utilizzato = float(used_result.scalar() or 0)
        disponibile = facility.plafond - utilizzato

        # AC-80.2: Calculate amounts
        importo_anticipabile = round(
            scadenza.importo_lordo * (facility.percentuale_anticipo / 100), 2
        )
        if importo_anticipabile > disponibile:
            return {
                "error": f"Plafond insufficiente: disponibile {disponibile:.2f}, richiesto {importo_anticipabile:.2f}",
                "disponibile": disponibile,
            }

        commissione = round(
            scadenza.importo_lordo * (facility.commissione_presentazione_pct / 100), 2
        )

        # Interessi stimati (giorni residui * tasso / 365)
        giorni_residui = max(0, (scadenza.data_scadenza - date.today()).days)
        interessi_stimati = round(
            importo_anticipabile * (facility.tasso_interesse_annuo / 100) * giorni_residui / 365, 2
        )
        costo_totale = round(commissione + interessi_stimati, 2)

        # AC-80.5: Create advance
        advance = InvoiceAdvance(
            tenant_id=scadenza.tenant_id,
            facility_id=facility.id,
            invoice_id=scadenza.source_id,
            importo_fattura=scadenza.importo_lordo,
            importo_anticipato=importo_anticipabile,
            commissione=commissione,
            interessi_stimati=interessi_stimati,
            data_presentazione=date.today(),
            data_scadenza_prevista=scadenza.data_scadenza,
            stato="attivo",
        )
        self.db.add(advance)
        await self.db.flush()

        # AC-80.6: Update scadenza
        scadenza.anticipata = True
        scadenza.anticipo_id = advance.id
        await self.db.flush()

        return {
            "id": str(advance.id),
            "importo_anticipato": importo_anticipabile,
            "commissione": commissione,
            "interessi_stimati": interessi_stimati,
            "costo_totale": costo_totale,
            "plafond_residuo": round(disponibile - importo_anticipabile, 2),
        }

    # ============================================================
    # US-81: Anticipo fattura — Incasso e scarico
    # ============================================================

    async def incassa_anticipo(
        self,
        anticipo_id: uuid.UUID,
        data_incasso: date,
    ) -> dict:
        """AC-81.1 to AC-81.5: Close an advance after client payment."""
        from api.db.models import InvoiceAdvance, BankFacility

        result = await self.db.execute(
            select(InvoiceAdvance).where(InvoiceAdvance.id == anticipo_id)
        )
        advance = result.scalar_one_or_none()
        if not advance:
            return {"error": "Anticipo non trovato"}
        if advance.stato != "attivo":
            return {"error": f"Anticipo in stato '{advance.stato}' — non attivo"}

        # AC-81.1: Mark as incassato
        advance.stato = "incassato"
        advance.data_chiusura = data_incasso

        # AC-81.3: Calculate effective interest
        giorni_effettivi = (data_incasso - advance.data_presentazione).days
        fac_result = await self.db.execute(
            select(BankFacility).where(BankFacility.id == advance.facility_id)
        )
        facility = fac_result.scalar_one_or_none()
        tasso = facility.tasso_interesse_annuo if facility else 0.0
        interessi_effettivi = round(
            advance.importo_anticipato * (tasso / 100) * giorni_effettivi / 365, 2
        )
        advance.interessi_effettivi = interessi_effettivi

        # AC-81.4: Total cost as oneri_finanziari
        costo_totale = round(advance.commissione + interessi_effettivi, 2)

        await self.db.flush()

        # AC-81.2/81.5: Plafond freed (calculated dynamically)
        return {
            "id": str(advance.id),
            "stato": "incassato",
            "giorni_effettivi": giorni_effettivi,
            "interessi_effettivi": interessi_effettivi,
            "costo_totale": costo_totale,
            "plafond_liberato": advance.importo_anticipato,
        }

    # ============================================================
    # US-82: Anticipo fattura — Insoluto
    # ============================================================

    async def insoluto_anticipo(
        self,
        anticipo_id: uuid.UUID,
    ) -> dict:
        """AC-82.1 to AC-82.5: Handle advance on unpaid invoice."""
        from api.db.models import InvoiceAdvance, BankFacility

        result = await self.db.execute(
            select(InvoiceAdvance).where(InvoiceAdvance.id == anticipo_id)
        )
        advance = result.scalar_one_or_none()
        if not advance:
            return {"error": "Anticipo non trovato"}

        # AC-82.1: Mark as insoluto
        advance.stato = "insoluto"
        advance.data_chiusura = date.today()

        # AC-82.3: Commissione insoluto
        fac_result = await self.db.execute(
            select(BankFacility).where(BankFacility.id == advance.facility_id)
        )
        facility = fac_result.scalar_one_or_none()
        commissione_insoluto = facility.commissione_insoluto if facility else 0.0

        await self.db.flush()

        return {
            "id": str(advance.id),
            "stato": "insoluto",
            "importo_riaddebito": advance.importo_anticipato,
            "commissione_insoluto": commissione_insoluto,
            # AC-82.4: plafond NOT freed
            "plafond_liberato": 0.0,
        }

    # ============================================================
    # US-83: Confronto costi anticipo tra banche
    # ============================================================

    async def confronta_anticipi(
        self,
        scadenza_id: uuid.UUID,
    ) -> list[dict]:
        """AC-83.1 to AC-83.4: Compare advance costs across banks."""
        from api.db.models import BankFacility, InvoiceAdvance

        result = await self.db.execute(
            select(Scadenza).where(Scadenza.id == scadenza_id)
        )
        scadenza = result.scalar_one_or_none()
        if not scadenza:
            return []

        importo = scadenza.importo_lordo
        giorni = max(0, (scadenza.data_scadenza - date.today()).days)

        # Get all active facilities for this tenant
        fac_result = await self.db.execute(
            select(BankFacility).where(
                BankFacility.tenant_id == scadenza.tenant_id,
                BankFacility.attivo.is_(True),
            )
        )
        facilities = fac_result.scalars().all()

        comparisons = []
        for fac in facilities:
            # Get bank name
            bank_result = await self.db.execute(
                select(BankAccount.bank_name).where(BankAccount.id == fac.bank_account_id)
            )
            bank_name = bank_result.scalar() or "Sconosciuta"

            # Used plafond
            used_result = await self.db.execute(
                select(func.coalesce(func.sum(InvoiceAdvance.importo_anticipato), 0.0)).where(
                    InvoiceAdvance.facility_id == fac.id,
                    InvoiceAdvance.stato == "attivo",
                )
            )
            utilizzato = float(used_result.scalar() or 0)
            disponibile = fac.plafond - utilizzato

            anticipabile = round(importo * (fac.percentuale_anticipo / 100), 2)
            commissione = round(importo * (fac.commissione_presentazione_pct / 100), 2)
            interessi = round(anticipabile * (fac.tasso_interesse_annuo / 100) * giorni / 365, 2)
            costo_totale = round(commissione + interessi, 2)
            costo_pct_annuo = round(
                (costo_totale / anticipabile * 365 / max(giorni, 1) * 100), 2
            ) if anticipabile > 0 and giorni > 0 else 0.0

            comparisons.append({
                "bank_name": bank_name,
                "facility_id": str(fac.id),
                "importo_anticipabile": anticipabile,
                "commissione": commissione,
                "interessi_stimati": interessi,
                "costo_totale": costo_totale,
                "costo_pct_annuo": costo_pct_annuo,
                "disponibile": round(disponibile, 2),
                "plafond_sufficiente": disponibile >= anticipabile,
            })

        # AC-83.3: Sort by costo_totale, highlight cheapest
        comparisons.sort(key=lambda x: x["costo_totale"])
        if comparisons:
            comparisons[0]["migliore"] = True

        return comparisons

    # ============================================================
    # Helpers
    # ============================================================

    def _get_cliente_nome(self, invoice: Invoice) -> str:
        """Extract client name from active invoice structured_data."""
        sd = invoice.structured_data or {}
        return (
            sd.get("destinatario_nome")
            or sd.get("cliente_nome")
            or "Sconosciuto"
        )

    def _get_giorni_pagamento(self, invoice: Invoice) -> int:
        """Get payment days from invoice or tenant defaults."""
        sd = invoice.structured_data or {}
        giorni = sd.get("giorni_pagamento")
        if giorni and int(giorni) > 0:
            return int(giorni)
        return DEFAULT_GIORNI_PAGAMENTO

    async def _find_banca_appoggio(self, invoice: Invoice) -> uuid.UUID | None:
        """Find bank account matching invoice IBAN."""
        sd = invoice.structured_data or {}
        iban = sd.get("iban") or sd.get("banca_iban")
        if not iban:
            return None

        result = await self.db.execute(
            select(BankAccount.id).where(
                BankAccount.tenant_id == invoice.tenant_id,
                BankAccount.iban == iban,
            ).limit(1)
        )
        return result.scalar_one_or_none()
