"""Service layer for commercialista reports (US-19)."""

import logging
import uuid
from datetime import date
from math import ceil

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import Invoice, Tenant

logger = logging.getLogger(__name__)

VALID_PERIODS = {
    "Q1": (1, 3),
    "Q2": (4, 6),
    "Q3": (7, 9),
    "Q4": (10, 12),
    "H1": (1, 6),
    "H2": (7, 12),
    "FY": (1, 12),
}

VALID_FORMATS = {"pdf", "csv"}


def parse_period(period: str, default_year: int | None = None) -> tuple[date, date, str]:
    """Parse period string like 'Q1-2026' or 'Q1'.

    Returns (start_date, end_date, normalized_period_label).
    """
    parts = period.upper().split("-")
    period_key = parts[0]

    if period_key not in VALID_PERIODS:
        raise ValueError(
            f"Periodo non valido: {period}. "
            f"Periodi ammessi: {', '.join(VALID_PERIODS.keys())} (es. Q1-2026)"
        )

    if len(parts) >= 2:
        try:
            year = int(parts[1])
        except ValueError as e:
            raise ValueError(f"Anno non valido nel periodo: {period}") from e
    elif default_year:
        year = default_year
    else:
        year = date.today().year

    start_month, end_month = VALID_PERIODS[period_key]
    import calendar
    last_day = calendar.monthrange(year, end_month)[1]

    start = date(year, start_month, 1)
    end = date(year, end_month, last_day)
    label = f"{period_key}-{year}"

    return start, end, label


class ReportService:
    """Service for generating reports for the commercialista."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def generate_report(
        self,
        tenant_id: uuid.UUID,
        period: str,
        format: str = "pdf",
    ) -> dict:
        """Generate a report for the given period and format.

        Args:
            tenant_id: The tenant to report on.
            period: Period string (Q1-2026, H1-2026, FY-2026).
            format: Output format (pdf, csv).

        Returns:
            Dict with report data.
        """
        if format not in VALID_FORMATS:
            raise ValueError(f"Formato non supportato: {format}. Formati ammessi: pdf, csv")

        start_date, end_date, label = parse_period(period)

        # Get tenant info
        tenant = await self._get_tenant(tenant_id)

        # Query invoices in period
        fatture_attive = await self._get_invoices(tenant_id, "attiva", start_date, end_date)
        fatture_passive = await self._get_invoices(tenant_id, "passiva", start_date, end_date)

        # Check for no data
        if not fatture_attive and not fatture_passive:
            return {
                "period": label,
                "period_start": start_date.isoformat(),
                "period_end": end_date.isoformat(),
                "format": format,
                "tenant_name": tenant.name,
                "tenant_piva": tenant.piva,
                "regime_fiscale": tenant.regime_fiscale,
                "total_fatture_attive": 0,
                "total_fatture_passive": 0,
                "totale_ricavi": 0.0,
                "totale_costi": 0.0,
                "totale_iva_credito": 0.0,
                "totale_iva_debito": 0.0,
                "saldo_iva": 0.0,
                "costi_per_categoria": {},
                "ricavi_per_categoria": {},
                "fatture_attive": [],
                "fatture_passive": [],
                "fatture_non_categorizzate": [],
                "has_uncategorized": False,
                "message": f"Nessuna fattura trovata per il periodo {label}",
            }

        # Compute summaries
        totale_ricavi = sum(f.importo_netto or 0 for f in fatture_attive)
        totale_costi = sum(f.importo_netto or 0 for f in fatture_passive)
        totale_iva_debito = sum(f.importo_iva or 0 for f in fatture_attive)
        totale_iva_credito = sum(f.importo_iva or 0 for f in fatture_passive)
        saldo_iva = totale_iva_debito - totale_iva_credito

        # Category breakdown
        costi_per_cat: dict[str, float] = {}
        ricavi_per_cat: dict[str, float] = {}
        non_categorizzate = []

        for f in fatture_passive:
            if f.category:
                costi_per_cat[f.category] = costi_per_cat.get(f.category, 0) + (f.importo_netto or 0)
            else:
                non_categorizzate.append(self._invoice_to_summary(f))

        for f in fatture_attive:
            if f.category:
                ricavi_per_cat[f.category] = ricavi_per_cat.get(f.category, 0) + (f.importo_netto or 0)
            else:
                non_categorizzate.append(self._invoice_to_summary(f))

        return {
            "period": label,
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
            "format": format,
            "tenant_name": tenant.name,
            "tenant_piva": tenant.piva,
            "regime_fiscale": tenant.regime_fiscale,
            "total_fatture_attive": len(fatture_attive),
            "total_fatture_passive": len(fatture_passive),
            "totale_ricavi": round(totale_ricavi, 2),
            "totale_costi": round(totale_costi, 2),
            "totale_iva_credito": round(totale_iva_credito, 2),
            "totale_iva_debito": round(totale_iva_debito, 2),
            "saldo_iva": round(saldo_iva, 2),
            "costi_per_categoria": costi_per_cat,
            "ricavi_per_categoria": ricavi_per_cat,
            "fatture_attive": [self._invoice_to_summary(f) for f in fatture_attive],
            "fatture_passive": [self._invoice_to_summary(f) for f in fatture_passive],
            "fatture_non_categorizzate": non_categorizzate,
            "has_uncategorized": len(non_categorizzate) > 0,
            "message": f"Report {format.upper()} per {label} generato con successo",
        }

    async def _get_tenant(self, tenant_id: uuid.UUID) -> Tenant:
        """Get tenant by ID."""
        result = await self.db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()
        if not tenant:
            raise ValueError("Tenant non trovato")
        return tenant

    async def _get_invoices(
        self,
        tenant_id: uuid.UUID,
        invoice_type: str,
        start_date: date,
        end_date: date,
    ) -> list[Invoice]:
        """Query invoices by type and date range."""
        result = await self.db.execute(
            select(Invoice).where(
                and_(
                    Invoice.tenant_id == tenant_id,
                    Invoice.type == invoice_type,
                    Invoice.data_fattura >= start_date,
                    Invoice.data_fattura <= end_date,
                )
            ).order_by(Invoice.data_fattura)
        )
        return list(result.scalars().all())

    def _invoice_to_summary(self, inv: Invoice) -> dict:
        """Convert Invoice to summary dict."""
        return {
            "numero_fattura": inv.numero_fattura,
            "emittente_nome": inv.emittente_nome,
            "data_fattura": inv.data_fattura.isoformat() if inv.data_fattura else None,
            "importo_netto": inv.importo_netto,
            "importo_iva": inv.importo_iva,
            "importo_totale": inv.importo_totale,
            "category": inv.category,
            "verified": inv.verified,
        }
