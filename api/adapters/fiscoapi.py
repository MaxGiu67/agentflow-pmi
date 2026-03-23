"""FiscoAPI adapter for SPID/CIE authentication and cassetto fiscale access.

In production this calls the real FiscoAPI. For testing and development,
the adapter is designed to be easily mockable.
"""

import logging
from dataclasses import dataclass
from datetime import date, timedelta

logger = logging.getLogger(__name__)


@dataclass
class SpidInitResult:
    redirect_url: str
    session_id: str


@dataclass
class SpidCallbackResult:
    access_token: str
    token_expires_in: int  # seconds
    fiscal_code: str


class FiscoAPIClient:
    """Client for FiscoAPI — SPID/CIE authentication and cassetto fiscale."""

    def __init__(self, base_url: str = "https://api.fiscoapi.com") -> None:
        self.base_url = base_url
        self._connected = True

    def set_connected(self, connected: bool) -> None:
        """Set connection status for testing."""
        self._connected = connected

    async def init_spid_auth(self, callback_url: str) -> SpidInitResult:
        """Start SPID authentication flow. Returns redirect URL for user."""
        # In production: POST to FiscoAPI to get SPID redirect URL
        logger.info("Initiating SPID auth with callback: %s", callback_url)
        return SpidInitResult(
            redirect_url=f"{self.base_url}/spid/authorize?callback={callback_url}",
            session_id="mock-session-id",
        )

    async def handle_spid_callback(self, code: str, state: str) -> SpidCallbackResult:
        """Handle SPID callback after user authenticates. Returns FiscoAPI token."""
        if code == "error" or code == "cancelled":
            raise ValueError("Autenticazione SPID annullata o fallita")

        # In production: exchange code for FiscoAPI token
        logger.info("SPID callback received with code: %s", code)
        return SpidCallbackResult(
            access_token="fiscoapi-token-mock",
            token_expires_in=3600 * 24,  # 24h
            fiscal_code="RSSMRA80A01H501U",
        )

    async def check_token_validity(self, token: str) -> bool:
        """Check if FiscoAPI token is still valid."""
        if not token:
            return False
        # In production: validate token against FiscoAPI
        return token != "expired-token"

    async def init_delegate_auth(
        self, callback_url: str, delegante_cf: str
    ) -> SpidInitResult:
        """Start delegated SPID auth (commercialista accessing client's cassetto)."""
        logger.info("Initiating delegate SPID auth for CF: %s", delegante_cf)
        return SpidInitResult(
            redirect_url=f"{self.base_url}/spid/delegate?cf={delegante_cf}&callback={callback_url}",
            session_id="mock-delegate-session",
        )

    async def sync_invoices(self, token: str, from_date: date | None = None) -> list[dict]:
        """Download invoices from cassetto fiscale. Returns list of raw invoice dicts.

        Args:
            token: FiscoAPI access token (from SPID auth)
            from_date: If None, downloads last 90 days (storico). Otherwise incremental from date.

        Returns:
            List of invoice dicts with raw data.

        Raises:
            ConnectionError: If FiscoAPI is not available.
        """
        if not self._connected:
            raise ConnectionError("FiscoAPI non raggiungibile")

        if not token or token == "expired-token":
            raise ValueError("Token FiscoAPI non valido o scaduto")

        logger.info("Syncing invoices from cassetto fiscale (from_date=%s)", from_date)

        # Mock: return sample invoices
        base_date = from_date or (date.today() - timedelta(days=90))

        # If from_date is very recent (incremental sync), return fewer invoices
        if from_date and (date.today() - from_date).days < 7:
            return self._generate_mock_invoices(base_date, count=1)

        return self._generate_mock_invoices(base_date, count=3)

    def _generate_mock_invoices(self, base_date: date, count: int = 3) -> list[dict]:
        """Generate mock invoice data for testing."""
        invoices = []
        suppliers = [
            ("IT01234567890", "Fornitore Alpha SRL"),
            ("IT09876543210", "Beta Services SpA"),
            ("IT11223344556", "Gamma Consulting"),
        ]

        for i in range(min(count, len(suppliers))):
            piva, nome = suppliers[i]
            inv_date = base_date + timedelta(days=i * 10)
            netto = round(1000.0 + i * 500, 2)
            iva = round(netto * 0.22, 2)
            totale = round(netto + iva, 2)

            xml_content = self._generate_mock_xml(
                numero=f"FT-2025-{1001 + i}",
                piva_emittente=piva,
                nome_emittente=nome,
                data=inv_date,
                importo_netto=netto,
                importo_iva=iva,
                importo_totale=totale,
                tipo_documento="TD01",
            )

            invoices.append({
                "numero_fattura": f"FT-2025-{1001 + i}",
                "emittente_piva": piva,
                "emittente_nome": nome,
                "data_fattura": inv_date.isoformat(),
                "importo_netto": netto,
                "importo_iva": iva,
                "importo_totale": totale,
                "tipo_documento": "TD01",
                "raw_xml": xml_content,
            })

        return invoices

    def _generate_mock_xml(
        self,
        numero: str,
        piva_emittente: str,
        nome_emittente: str,
        data: date,
        importo_netto: float,
        importo_iva: float,
        importo_totale: float,
        tipo_documento: str = "TD01",
    ) -> str:
        """Generate a mock FatturaPA XML string."""
        piva_clean = piva_emittente.replace("IT", "")
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<p:FatturaElettronica xmlns:p="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2"
  versione="FPR12">
  <FatturaElettronicaHeader>
    <DatiTrasmissione>
      <IdTrasmittente>
        <IdPaese>IT</IdPaese>
        <IdCodice>{piva_clean}</IdCodice>
      </IdTrasmittente>
      <FormatoTrasmissione>FPR12</FormatoTrasmissione>
    </DatiTrasmissione>
    <CedentePrestatore>
      <DatiAnagrafici>
        <IdFiscaleIVA>
          <IdPaese>IT</IdPaese>
          <IdCodice>{piva_clean}</IdCodice>
        </IdFiscaleIVA>
        <Anagrafica>
          <Denominazione>{nome_emittente}</Denominazione>
        </Anagrafica>
      </DatiAnagrafici>
    </CedentePrestatore>
    <CessionarioCommittente>
      <DatiAnagrafici>
        <IdFiscaleIVA>
          <IdPaese>IT</IdPaese>
          <IdCodice>12345678901</IdCodice>
        </IdFiscaleIVA>
        <Anagrafica>
          <Denominazione>Test SRL</Denominazione>
        </Anagrafica>
      </DatiAnagrafici>
    </CessionarioCommittente>
  </FatturaElettronicaHeader>
  <FatturaElettronicaBody>
    <DatiGenerali>
      <DatiGeneraliDocumento>
        <TipoDocumento>{tipo_documento}</TipoDocumento>
        <Data>{data.isoformat()}</Data>
        <Numero>{numero}</Numero>
        <ImportoTotaleDocumento>{importo_totale}</ImportoTotaleDocumento>
      </DatiGeneraliDocumento>
    </DatiGenerali>
    <DatiBeniServizi>
      <DettaglioLinee>
        <NumeroLinea>1</NumeroLinea>
        <Descrizione>Servizio professionale</Descrizione>
        <Quantita>1.00</Quantita>
        <PrezzoUnitario>{importo_netto}</PrezzoUnitario>
        <PrezzoTotale>{importo_netto}</PrezzoTotale>
        <AliquotaIVA>22.00</AliquotaIVA>
      </DettaglioLinee>
      <DatiRiepilogo>
        <AliquotaIVA>22.00</AliquotaIVA>
        <ImponibileImporto>{importo_netto}</ImponibileImporto>
        <Imposta>{importo_iva}</Imposta>
      </DatiRiepilogo>
    </DatiBeniServizi>
  </FatturaElettronicaBody>
</p:FatturaElettronica>"""
