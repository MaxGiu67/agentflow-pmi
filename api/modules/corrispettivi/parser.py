"""Parser for Corrispettivi Telematici XML (COR10) from Agenzia delle Entrate (US-47).

Format: namespace http://ivaservizi.agenziaentrate.gov.it/docs/xsd/corrispettivi/dati/v1.0
Each file = 1 daily receipt summary from an electronic cash register (RT).
"""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from xml.etree import ElementTree

logger = logging.getLogger(__name__)

NS = {"n1": "http://ivaservizi.agenziaentrate.gov.it/docs/xsd/corrispettivi/dati/v1.0"}


@dataclass
class RiepilogoIVA:
    aliquota: float
    imponibile: float
    imposta: float
    natura: str | None = None  # N1-N7 for exempt


@dataclass
class CorrispettivoData:
    piva_esercente: str = ""
    cf_esercente: str = ""
    dispositivo_id: str = ""
    data_trasmissione: date | None = None
    data_rilevazione: date | None = None
    riepiloghi: list[RiepilogoIVA] = field(default_factory=list)
    totale_contanti: float = 0.0
    totale_elettronico: float = 0.0
    num_documenti: int = 0
    totale_imponibile: float = 0.0
    totale_imposta: float = 0.0
    totale_incasso: float = 0.0


def parse_corrispettivo_xml(xml_content: str) -> CorrispettivoData:
    """Parse a COR10 XML corrispettivi file."""
    root = ElementTree.fromstring(xml_content)
    data = CorrispettivoData()

    # Helper: find element trying both with and without namespace
    def _find(parent, tag):
        return parent.find(f"n1:{tag}", NS) or parent.find(tag)

    def _findtext(parent, tag, default=""):
        return parent.findtext(f"n1:{tag}", None, NS) or parent.findtext(tag, default)

    def _findall(parent, tag):
        results = parent.findall(f"n1:{tag}", NS)
        if not results:
            results = parent.findall(tag)
        return results

    # Trasmissione
    trasm = _find(root, "Trasmissione")
    if trasm is not None:
        data.piva_esercente = _findtext(trasm, "PIVAEsercente")
        data.cf_esercente = _findtext(trasm, "CodiceFiscaleEsercente")

        disp = _find(trasm, "Dispositivo")
        if disp is not None:
            data.dispositivo_id = _findtext(disp, "IdDispositivo")

        dt_str = _findtext(trasm, "DataOraTrasmissione")
        if dt_str:
            data.data_trasmissione = _parse_datetime(dt_str)

    # DataOraRilevazione
    dt_ril = _findtext(root, "DataOraRilevazione")
    if dt_ril:
        data.data_rilevazione = _parse_datetime(dt_ril)

    # DatiRT → Riepilogo (multiple) + Totali
    dati_rt = _find(root, "DatiRT")
    if dati_rt is not None:
        for riep in _findall(dati_rt, "Riepilogo"):
            iva_elem = _find(riep, "IVA")
            natura_elem = _find(riep, "Natura")

            aliquota = 0.0
            natura = None
            if iva_elem is not None:
                aliquota = float(_findtext(iva_elem, "AliquotaIVA", "0"))
                imposta = float(_findtext(iva_elem, "Imposta", "0"))
            else:
                imposta = 0.0

            if natura_elem is not None:
                natura = natura_elem.text

            ammontare = float(_findtext(riep, "Ammontare", "0"))

            if ammontare > 0 or imposta > 0:
                data.riepiloghi.append(RiepilogoIVA(
                    aliquota=aliquota,
                    imponibile=ammontare,
                    imposta=imposta,
                    natura=natura,
                ))

        totali = _find(dati_rt, "Totali")
        if totali is not None:
            data.num_documenti = int(_findtext(totali, "NumeroDocCommerciali", "0"))
            data.totale_contanti = float(_findtext(totali, "PagatoContanti", "0"))
            data.totale_elettronico = float(_findtext(totali, "PagatoElettronico", "0"))

    # Calculate totals
    data.totale_imponibile = sum(r.imponibile for r in data.riepiloghi)
    data.totale_imposta = sum(r.imposta for r in data.riepiloghi)
    data.totale_incasso = data.totale_contanti + data.totale_elettronico

    return data


def _parse_datetime(dt_str: str) -> date:
    """Parse ISO datetime string to date."""
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(dt_str[:19], fmt[:19] if "T" in dt_str else fmt).date()
        except ValueError:
            continue
    return datetime.fromisoformat(dt_str[:10]).date()
