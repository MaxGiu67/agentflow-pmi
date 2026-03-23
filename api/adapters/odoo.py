"""Odoo XML-RPC / JSON-2 adapter for headless accounting operations.

In production this connects to Odoo CE 18 via XML-RPC.
For testing, the adapter is designed to be easily mockable.
"""

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class OdooAccount:
    code: str
    name: str
    account_type: str  # asset, liability, equity, income, expense


@dataclass
class OdooPianoConti:
    db_name: str
    accounts: list[OdooAccount] = field(default_factory=list)
    journals: list[str] = field(default_factory=list)
    tax_codes: list[str] = field(default_factory=list)


# Templates for different company types
PIANO_CONTI_SRL_ORDINARIO: list[OdooAccount] = [
    # Stato Patrimoniale - Attivo
    OdooAccount("1010", "Cassa", "asset"),
    OdooAccount("1020", "Banca c/c", "asset"),
    OdooAccount("1110", "Crediti verso clienti", "asset"),
    OdooAccount("1120", "Crediti IVA", "asset"),
    OdooAccount("1210", "Immobilizzazioni materiali", "asset"),
    OdooAccount("1220", "Fondo ammortamento immob. materiali", "asset"),
    OdooAccount("1310", "Immobilizzazioni immateriali", "asset"),
    # Stato Patrimoniale - Passivo
    OdooAccount("2010", "Debiti verso fornitori", "liability"),
    OdooAccount("2020", "Debiti tributari", "liability"),
    OdooAccount("2030", "Debiti vs istituti previdenziali", "liability"),
    OdooAccount("2040", "TFR", "liability"),
    OdooAccount("2110", "IVA a debito", "liability"),
    OdooAccount("2120", "Ritenute da versare", "liability"),
    # Patrimonio Netto
    OdooAccount("3010", "Capitale sociale", "equity"),
    OdooAccount("3020", "Riserva legale", "equity"),
    OdooAccount("3030", "Utile/perdita d'esercizio", "equity"),
    # Conto Economico - Ricavi
    OdooAccount("4010", "Ricavi da vendite", "income"),
    OdooAccount("4020", "Ricavi da prestazioni di servizi", "income"),
    OdooAccount("4030", "Altri ricavi", "income"),
    # Conto Economico - Costi
    OdooAccount("5010", "Acquisti materie prime", "expense"),
    OdooAccount("5020", "Servizi", "expense"),
    OdooAccount("5030", "Godimento beni di terzi", "expense"),
    OdooAccount("5040", "Costi del personale", "expense"),
    OdooAccount("5050", "Ammortamenti", "expense"),
    OdooAccount("5060", "Oneri diversi di gestione", "expense"),
    OdooAccount("6010", "Interessi attivi", "income"),
    OdooAccount("6020", "Interessi passivi", "expense"),
    OdooAccount("6110", "Consulenze", "expense"),
    OdooAccount("6120", "Utenze", "expense"),
]

PIANO_CONTI_FORFETTARIO: list[OdooAccount] = [
    # Semplificato - senza IVA
    OdooAccount("1010", "Cassa", "asset"),
    OdooAccount("1020", "Banca c/c", "asset"),
    OdooAccount("1110", "Crediti verso clienti", "asset"),
    OdooAccount("2010", "Debiti verso fornitori", "liability"),
    OdooAccount("3010", "Patrimonio netto", "equity"),
    OdooAccount("4010", "Ricavi (compensi)", "income"),
    OdooAccount("5010", "Costi deducibili", "expense"),
    OdooAccount("5020", "Contributi previdenziali", "expense"),
    OdooAccount("5030", "Imposta sostitutiva", "expense"),
]

PIANO_CONTI_GENERICO: list[OdooAccount] = [
    OdooAccount("1010", "Cassa", "asset"),
    OdooAccount("1020", "Banca c/c", "asset"),
    OdooAccount("1110", "Crediti verso clienti", "asset"),
    OdooAccount("1210", "Immobilizzazioni", "asset"),
    OdooAccount("2010", "Debiti verso fornitori", "liability"),
    OdooAccount("2020", "Debiti tributari", "liability"),
    OdooAccount("2110", "IVA a debito", "liability"),
    OdooAccount("3010", "Capitale", "equity"),
    OdooAccount("4010", "Ricavi", "income"),
    OdooAccount("5010", "Costi", "expense"),
    OdooAccount("5020", "Servizi", "expense"),
    OdooAccount("5030", "Ammortamenti", "expense"),
]


class OdooClient:
    """Client for Odoo CE 18 — headless accounting via XML-RPC/JSON-2."""

    def __init__(self, url: str = "http://localhost:8069") -> None:
        self.url = url
        self._connected = True  # Mock: always connected

    async def create_database(self, db_name: str) -> str:
        """Create a new Odoo database for a tenant."""
        if not self._connected:
            raise ConnectionError("Impossibile connettersi a Odoo")
        logger.info("Created Odoo database: %s", db_name)
        return db_name

    async def create_piano_conti(
        self,
        db_name: str,
        tipo_azienda: str,
        regime_fiscale: str,
    ) -> OdooPianoConti:
        """Create chart of accounts based on company type."""
        if not self._connected:
            raise ConnectionError("Impossibile connettersi a Odoo")

        # Select template
        if regime_fiscale == "forfettario":
            accounts = list(PIANO_CONTI_FORFETTARIO)
            tax_codes = []  # No IVA for forfettario
            journals = ["Vendite", "Acquisti", "Banca"]
        elif tipo_azienda in ("srl", "srls"):
            accounts = list(PIANO_CONTI_SRL_ORDINARIO)
            tax_codes = ["4%", "10%", "22%"]
            journals = ["Vendite", "Acquisti", "Banca", "Cassa", "Vari"]
        elif tipo_azienda == "altro":
            accounts = list(PIANO_CONTI_GENERICO)
            tax_codes = ["4%", "10%", "22%"]
            journals = ["Vendite", "Acquisti", "Banca", "Vari"]
        else:
            # piva, ditta_individuale with non-forfettario
            accounts = list(PIANO_CONTI_SRL_ORDINARIO)
            tax_codes = ["4%", "10%", "22%"]
            journals = ["Vendite", "Acquisti", "Banca", "Vari"]

        logger.info(
            "Created piano conti for %s/%s on DB %s: %d accounts, %d journals",
            tipo_azienda, regime_fiscale, db_name, len(accounts), len(journals),
        )

        return OdooPianoConti(
            db_name=db_name,
            accounts=accounts,
            journals=journals,
            tax_codes=tax_codes,
        )

    async def get_piano_conti(self, db_name: str) -> OdooPianoConti | None:
        """Get existing chart of accounts."""
        if not self._connected:
            raise ConnectionError("Impossibile connettersi a Odoo")
        # In production: fetch from Odoo
        return None

    def set_connected(self, connected: bool) -> None:
        """For testing: simulate connection failures."""
        self._connected = connected
