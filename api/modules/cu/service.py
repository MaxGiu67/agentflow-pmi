"""Service layer for Certificazione Unica (CU) annuale (US-34)."""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import CertificazioneUnica, Invoice, WithholdingTax

logger = logging.getLogger(__name__)

# INPS 4% contribution indicator keywords
INPS_KEYWORDS = [
    "ingegnere", "architetto", "geometra", "perito",
    "consulente", "professionista",
]


class CUService:
    """Business logic for Certificazione Unica generation and export."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def generate_cu(
        self,
        tenant_id: uuid.UUID,
        year: int,
    ) -> dict:
        """Generate CU for all professionals paid in the given year.

        AC-34.1: Genera CU per ogni professionista pagato (compensi lordi, ritenute, netto).
        AC-34.3: Ritenute non tutte versate -> warning.
        AC-34.4: Professionista con contributo INPS 4% -> indicato separatamente.
        """
        # Get all withholding taxes for the year
        result = await self.db.execute(
            select(WithholdingTax).where(
                WithholdingTax.tenant_id == tenant_id,
            )
        )
        all_wt = result.scalars().all()

        # Filter by year using the associated invoice date
        wt_by_year: list[WithholdingTax] = []
        invoice_cache: dict[uuid.UUID, Invoice] = {}

        for wt in all_wt:
            inv_result = await self.db.execute(
                select(Invoice).where(Invoice.id == wt.invoice_id)
            )
            inv = inv_result.scalar_one_or_none()
            if inv and inv.data_fattura and inv.data_fattura.year == year:
                wt_by_year.append(wt)
                invoice_cache[inv.id] = inv

        # Group by percettore (emittente_piva)
        percettore_data: dict[str, dict] = {}
        for wt in wt_by_year:
            inv = invoice_cache.get(wt.invoice_id)
            if not inv:
                continue
            piva = inv.emittente_piva
            if piva not in percettore_data:
                percettore_data[piva] = {
                    "percettore_piva": piva,
                    "percettore_nome": inv.emittente_nome or piva,
                    "compenso_lordo": 0.0,
                    "ritenute_operate": 0.0,
                    "netto_corrisposto": 0.0,
                    "contributo_inps": 0.0,
                    "ritenute_versate": 0.0,
                }
            data = percettore_data[piva]
            data["compenso_lordo"] += wt.imponibile_ritenuta
            data["ritenute_operate"] += wt.importo_ritenuta
            data["netto_corrisposto"] += wt.importo_netto
            if wt.status == "paid":
                data["ritenute_versate"] += wt.importo_ritenuta

        # Delete existing CU for same year before regenerating
        existing = await self.db.execute(
            select(CertificazioneUnica).where(
                CertificazioneUnica.tenant_id == tenant_id,
                CertificazioneUnica.year == year,
            )
        )
        for old_cu in existing.scalars().all():
            await self.db.delete(old_cu)
        await self.db.flush()

        # Generate CU records
        items = []
        warnings: list[str] = []

        for piva, data in percettore_data.items():
            # AC-34.4: Check INPS 4% contribution
            has_inps = self._check_inps_contribution(data["percettore_nome"])
            contributo_inps = 0.0
            if has_inps:
                contributo_inps = round(data["compenso_lordo"] * 0.04, 2)
                data["contributo_inps"] = contributo_inps

            # AC-34.3: Check if all ritenute are versate
            warning = None
            if data["ritenute_versate"] < data["ritenute_operate"]:
                non_versate = round(data["ritenute_operate"] - data["ritenute_versate"], 2)
                warning = (
                    f"Ritenute non interamente versate per {data['percettore_nome']}: "
                    f"operate {data['ritenute_operate']:.2f}, "
                    f"versate {data['ritenute_versate']:.2f}, "
                    f"mancanti {non_versate:.2f}"
                )
                warnings.append(warning)

            # Round values
            compenso_lordo = round(data["compenso_lordo"], 2)
            ritenute_operate = round(data["ritenute_operate"], 2)
            netto_corrisposto = round(data["netto_corrisposto"], 2)
            ritenute_versate = round(data["ritenute_versate"], 2)

            cu = CertificazioneUnica(
                tenant_id=tenant_id,
                year=year,
                percettore_piva=piva,
                percettore_nome=data["percettore_nome"],
                compenso_lordo=compenso_lordo,
                ritenute_operate=ritenute_operate,
                netto_corrisposto=netto_corrisposto,
                contributo_inps=contributo_inps,
                ritenute_versate=ritenute_versate,
                has_inps_separato=has_inps,
                warning=warning,
                status="generated",
            )
            self.db.add(cu)
            await self.db.flush()

            items.append({
                "id": str(cu.id),
                "tenant_id": str(cu.tenant_id),
                "year": cu.year,
                "percettore_piva": cu.percettore_piva,
                "percettore_nome": cu.percettore_nome,
                "compenso_lordo": cu.compenso_lordo,
                "ritenute_operate": cu.ritenute_operate,
                "netto_corrisposto": cu.netto_corrisposto,
                "contributo_inps": cu.contributo_inps,
                "ritenute_versate": cu.ritenute_versate,
                "has_inps_separato": cu.has_inps_separato,
                "warning": cu.warning,
                "status": cu.status,
            })

        return {
            "generated": len(items),
            "year": year,
            "warnings": warnings,
            "items": items,
        }

    async def list_cu(
        self,
        tenant_id: uuid.UUID,
        year: int,
    ) -> dict:
        """List all CU records for a year."""
        result = await self.db.execute(
            select(CertificazioneUnica).where(
                CertificazioneUnica.tenant_id == tenant_id,
                CertificazioneUnica.year == year,
            ).order_by(CertificazioneUnica.percettore_nome)
        )
        items = result.scalars().all()

        return {
            "items": [
                {
                    "id": str(cu.id),
                    "tenant_id": str(cu.tenant_id),
                    "year": cu.year,
                    "percettore_piva": cu.percettore_piva,
                    "percettore_nome": cu.percettore_nome,
                    "compenso_lordo": cu.compenso_lordo,
                    "ritenute_operate": cu.ritenute_operate,
                    "netto_corrisposto": cu.netto_corrisposto,
                    "contributo_inps": cu.contributo_inps,
                    "ritenute_versate": cu.ritenute_versate,
                    "has_inps_separato": cu.has_inps_separato,
                    "warning": cu.warning,
                    "status": cu.status,
                }
                for cu in items
            ],
            "total": len(items),
            "year": year,
        }

    async def export_cu(
        self,
        cu_id: uuid.UUID,
        tenant_id: uuid.UUID,
        format: str = "csv",
    ) -> dict:
        """Export a CU record in CSV or telematico format.

        AC-34.2: Export formato telematico/CSV.
        """
        result = await self.db.execute(
            select(CertificazioneUnica).where(
                CertificazioneUnica.id == cu_id,
                CertificazioneUnica.tenant_id == tenant_id,
            )
        )
        cu = result.scalar_one_or_none()
        if not cu:
            raise ValueError("CU non trovata")

        if format == "csv":
            content = self._export_csv(cu)
            filename = f"CU_{cu.year}_{cu.percettore_piva}.csv"
        else:
            content = self._export_telematico(cu)
            filename = f"CU_{cu.year}_{cu.percettore_piva}.txt"

        cu.status = "exported"
        await self.db.flush()

        return {
            "id": str(cu.id),
            "year": cu.year,
            "percettore_nome": cu.percettore_nome,
            "format": format,
            "content": content,
            "filename": filename,
        }

    def _export_csv(self, cu: CertificazioneUnica) -> str:
        """Export CU as CSV."""
        lines = [
            "Anno,Percettore_PIVA,Percettore_Nome,Compenso_Lordo,Ritenute_Operate,"
            "Netto_Corrisposto,Contributo_INPS,Ritenute_Versate",
            (
                f"{cu.year},{cu.percettore_piva},{cu.percettore_nome},"
                f"{cu.compenso_lordo:.2f},{cu.ritenute_operate:.2f},"
                f"{cu.netto_corrisposto:.2f},{cu.contributo_inps:.2f},"
                f"{cu.ritenute_versate:.2f}"
            ),
        ]
        return "\n".join(lines)

    def _export_telematico(self, cu: CertificazioneUnica) -> str:
        """Export CU in formato telematico (mock ministerial format)."""
        # Simplified ministerial format record
        record = (
            f"CU{cu.year}|"
            f"{cu.percettore_piva}|"
            f"{cu.percettore_nome}|"
            f"{cu.compenso_lordo:.2f}|"
            f"{cu.ritenute_operate:.2f}|"
            f"{cu.netto_corrisposto:.2f}|"
            f"{cu.contributo_inps:.2f}|"
            f"{cu.ritenute_versate:.2f}"
        )
        return record

    def _check_inps_contribution(self, nome: str) -> bool:
        """AC-34.4: Check if professional has INPS 4% contribution."""
        nome_lower = nome.lower()
        for keyword in INPS_KEYWORDS:
            if keyword in nome_lower:
                return True
        return False
