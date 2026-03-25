import uuid
from collections.abc import AsyncGenerator
from datetime import date, datetime, timedelta, UTC

import pytest
from httpx import ASGITransport, AsyncClient
import bcrypt as _bcrypt
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.db.models import (
    Base, Tenant, User, Invoice, AgentEvent, CategorizationFeedback,
    JournalEntry, JournalLine, OnboardingState, FiscalRule, ChartAccount,
    EmailConnection, NotificationConfig, NotificationLog,
    ActiveInvoice, BankAccount, BankTransaction, VatSettlement,
    FiscalDeadline, WithholdingTax, Reconciliation, StampDuty,
    Expense, ExpensePolicy, Asset, Accrual,
    CertificazioneUnica, DigitalPreservation, Payment, NormativeAlert,
    F24Document, Budget,
    Conversation, Message, AgentConfig, ConversationMemory,
    DashboardLayout,
)
from api.db.session import get_db
from api.main import app
from api.modules.auth.service import AuthService

# Use SQLite async for tests (no PostgreSQL required)
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
test_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

def _hash_pw(password: str) -> str:
    return _bcrypt.hashpw(password.encode("utf-8"), _bcrypt.gensalt()).decode("utf-8")


@pytest.fixture(autouse=True)
async def setup_db():
    """Create tables before each test, drop after."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a test DB session."""
    async with test_session_factory() as session:
        yield session


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """HTTP test client with DB override."""

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
async def auth_service(db_session: AsyncSession) -> AuthService:
    """Auth service instance for direct testing."""
    return AuthService(db_session)


@pytest.fixture
async def tenant(db_session: AsyncSession) -> Tenant:
    """Default test tenant (SRL ordinario)."""
    t = Tenant(
        name="Test SRL",
        type="srl",
        regime_fiscale="ordinario",
        piva="12345678901",
        codice_ateco="62.01.00",
    )
    db_session.add(t)
    await db_session.flush()
    return t


@pytest.fixture
async def verified_user(db_session: AsyncSession, tenant: Tenant) -> User:
    """A verified user ready to login."""
    user = User(
        email="mario.rossi@example.com",
        password_hash=_hash_pw("Password1"),
        name="Mario Rossi",
        role="owner",
        email_verified=True,
        tenant_id=tenant.id,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def unverified_user(db_session: AsyncSession, tenant: Tenant) -> User:
    """An unverified user (email not yet confirmed)."""
    user = User(
        email="luigi.bianchi@example.com",
        password_hash=_hash_pw("Password1"),
        name="Luigi Bianchi",
        role="owner",
        email_verified=False,
        verification_token="test-verification-token-123",
        tenant_id=tenant.id,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def verified_user_no_tenant(db_session: AsyncSession) -> User:
    """A verified user without a tenant (new registration, no company setup)."""
    user = User(
        email="nuova.utente@example.com",
        password_hash=_hash_pw("Password1"),
        name="Nuova Utente",
        role="owner",
        email_verified=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def tenant_with_odoo(db_session: AsyncSession) -> Tenant:
    """Tenant with Odoo DB already configured (piano conti exists)."""
    t = Tenant(
        name="Azienda Con Piano Conti SRL",
        type="srl",
        regime_fiscale="ordinario",
        piva="09876543210",
        codice_ateco="62.01.00",
        odoo_db_name="contabot_existing",
    )
    db_session.add(t)
    await db_session.flush()
    return t


@pytest.fixture
async def user_with_odoo(db_session: AsyncSession, tenant_with_odoo: Tenant) -> User:
    """A verified user whose tenant has Odoo DB (piano conti exists)."""
    user = User(
        email="paolo.conti@example.com",
        password_hash=_hash_pw("Password1"),
        name="Paolo Conti",
        role="owner",
        email_verified=True,
        tenant_id=tenant_with_odoo.id,
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def get_auth_token(client: AsyncClient, email: str, password: str) -> str:
    """Helper: login and return access token."""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    return resp.json()["access_token"]


@pytest.fixture
async def auth_headers(client: AsyncClient, verified_user: User) -> dict:
    """Auth headers with valid JWT for verified_user."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")
    return {"Authorization": f"Bearer {token}"}


# ====================================================
# Sprint 2 fixtures
# ====================================================


@pytest.fixture
def sample_fattura_xml() -> str:
    """Valid FatturaPA 1.2 XML string (TD01 - fattura)."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<p:FatturaElettronica xmlns:p="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2"
  versione="FPR12">
  <FatturaElettronicaHeader>
    <DatiTrasmissione>
      <IdTrasmittente>
        <IdPaese>IT</IdPaese>
        <IdCodice>01234567890</IdCodice>
      </IdTrasmittente>
      <FormatoTrasmissione>FPR12</FormatoTrasmissione>
    </DatiTrasmissione>
    <CedentePrestatore>
      <DatiAnagrafici>
        <IdFiscaleIVA>
          <IdPaese>IT</IdPaese>
          <IdCodice>01234567890</IdCodice>
        </IdFiscaleIVA>
        <Anagrafica>
          <Denominazione>Fornitore Alpha SRL</Denominazione>
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
        <TipoDocumento>TD01</TipoDocumento>
        <Data>2025-01-15</Data>
        <Numero>FT-2025-0001</Numero>
        <ImportoTotaleDocumento>1220.00</ImportoTotaleDocumento>
      </DatiGeneraliDocumento>
    </DatiGenerali>
    <DatiBeniServizi>
      <DettaglioLinee>
        <NumeroLinea>1</NumeroLinea>
        <Descrizione>Consulenza informatica</Descrizione>
        <Quantita>1.00</Quantita>
        <PrezzoUnitario>1000.00</PrezzoUnitario>
        <PrezzoTotale>1000.00</PrezzoTotale>
        <AliquotaIVA>22.00</AliquotaIVA>
      </DettaglioLinee>
      <DatiRiepilogo>
        <AliquotaIVA>22.00</AliquotaIVA>
        <ImponibileImporto>1000.00</ImponibileImporto>
        <Imposta>220.00</Imposta>
      </DatiRiepilogo>
    </DatiBeniServizi>
  </FatturaElettronicaBody>
</p:FatturaElettronica>"""


@pytest.fixture
def sample_nota_credito_xml() -> str:
    """Valid FatturaPA 1.2 XML string (TD04 - nota di credito)."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<p:FatturaElettronica xmlns:p="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2"
  versione="FPR12">
  <FatturaElettronicaHeader>
    <DatiTrasmissione>
      <IdTrasmittente>
        <IdPaese>IT</IdPaese>
        <IdCodice>01234567890</IdCodice>
      </IdTrasmittente>
      <FormatoTrasmissione>FPR12</FormatoTrasmissione>
    </DatiTrasmissione>
    <CedentePrestatore>
      <DatiAnagrafici>
        <IdFiscaleIVA>
          <IdPaese>IT</IdPaese>
          <IdCodice>01234567890</IdCodice>
        </IdFiscaleIVA>
        <Anagrafica>
          <Denominazione>Fornitore Alpha SRL</Denominazione>
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
        <TipoDocumento>TD04</TipoDocumento>
        <Data>2025-02-10</Data>
        <Numero>NC-2025-0001</Numero>
        <ImportoTotaleDocumento>244.00</ImportoTotaleDocumento>
      </DatiGeneraliDocumento>
    </DatiGenerali>
    <DatiBeniServizi>
      <DettaglioLinee>
        <NumeroLinea>1</NumeroLinea>
        <Descrizione>Storno parziale fattura FT-2025-0001</Descrizione>
        <Quantita>1.00</Quantita>
        <PrezzoUnitario>200.00</PrezzoUnitario>
        <PrezzoTotale>200.00</PrezzoTotale>
        <AliquotaIVA>22.00</AliquotaIVA>
      </DettaglioLinee>
      <DatiRiepilogo>
        <AliquotaIVA>22.00</AliquotaIVA>
        <ImponibileImporto>200.00</ImponibileImporto>
        <Imposta>44.00</Imposta>
      </DatiRiepilogo>
    </DatiBeniServizi>
  </FatturaElettronicaBody>
</p:FatturaElettronica>"""


@pytest.fixture
async def spid_user(db_session: AsyncSession, tenant: Tenant) -> User:
    """A verified user with SPID token connected to cassetto fiscale."""
    user = User(
        email="spid.user@example.com",
        password_hash=_hash_pw("Password1"),
        name="SPID User",
        role="owner",
        email_verified=True,
        tenant_id=tenant.id,
        spid_token="fiscoapi-token-mock",
        spid_token_expires_at=datetime.now(UTC) + timedelta(hours=24),
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def spid_auth_headers(client: AsyncClient, spid_user: User) -> dict:
    """Auth headers for a user with SPID token."""
    token = await get_auth_token(client, "spid.user@example.com", "Password1")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def invoice_in_db(db_session: AsyncSession, tenant: Tenant, sample_fattura_xml: str) -> Invoice:
    """A sample invoice in the database."""
    invoice = Invoice(
        tenant_id=tenant.id,
        type="passiva",
        document_type="TD01",
        source="cassetto_fiscale",
        numero_fattura="FT-2025-0001",
        emittente_piva="IT01234567890",
        emittente_nome="Fornitore Alpha SRL",
        data_fattura=date(2025, 1, 15),
        importo_netto=1000.0,
        importo_iva=220.0,
        importo_totale=1220.0,
        raw_xml=sample_fattura_xml,
        processing_status="pending",
    )
    db_session.add(invoice)
    await db_session.flush()
    return invoice


def create_invoice(
    tenant_id: uuid.UUID,
    numero: str = "FT-TEST-001",
    piva: str = "IT01234567890",
    nome: str = "Test Fornitore",
    importo: float = 1000.0,
    source: str = "cassetto_fiscale",
    status: str = "pending",
    doc_type: str = "TD01",
    data: date | None = None,
    category: str | None = None,
    verified: bool = False,
    raw_xml: str | None = None,
    structured_data: dict | None = None,
) -> Invoice:
    """Factory helper to create Invoice instances."""
    iva = round(importo * 0.22, 2)
    totale = round(importo + iva, 2)
    return Invoice(
        tenant_id=tenant_id,
        type="passiva",
        document_type=doc_type,
        source=source,
        numero_fattura=numero,
        emittente_piva=piva,
        emittente_nome=nome,
        data_fattura=data or date(2025, 1, 15),
        importo_netto=importo,
        importo_iva=iva,
        importo_totale=totale,
        raw_xml=raw_xml,
        structured_data=structured_data,
        processing_status=status,
        category=category,
        verified=verified,
    )


# ====================================================
# Sprint 3 fixtures
# ====================================================


@pytest.fixture
async def categorized_invoice(db_session: AsyncSession, tenant: Tenant) -> Invoice:
    """An invoice with category but not yet verified."""
    invoice = create_invoice(
        tenant_id=tenant.id,
        numero="FT-CAT-001",
        piva="IT11223344556",
        nome="Fornitore Categorizzato SRL",
        importo=500.0,
        category="Consulenze",
        verified=False,
        status="categorized",
    )
    db_session.add(invoice)
    await db_session.flush()
    return invoice


@pytest.fixture
async def verified_invoice(db_session: AsyncSession, tenant: Tenant) -> Invoice:
    """An invoice with category and verified."""
    invoice = create_invoice(
        tenant_id=tenant.id,
        numero="FT-VER-001",
        piva="IT99887766554",
        nome="Fornitore Verificato SRL",
        importo=800.0,
        category="Utenze",
        verified=True,
        status="categorized",
    )
    db_session.add(invoice)
    await db_session.flush()
    return invoice


@pytest.fixture
async def journal_entry_in_db(
    db_session: AsyncSession, tenant: Tenant, verified_invoice: Invoice,
) -> JournalEntry:
    """A sample journal entry with lines."""
    entry = JournalEntry(
        tenant_id=tenant.id,
        invoice_id=verified_invoice.id,
        description=f"Fattura {verified_invoice.numero_fattura} - {verified_invoice.emittente_nome}",
        entry_date=verified_invoice.data_fattura or date(2025, 1, 15),
        total_debit=976.0,
        total_credit=976.0,
        status="posted",
    )
    db_session.add(entry)
    await db_session.flush()

    # Add lines
    lines = [
        JournalLine(
            entry_id=entry.id,
            account_code="6120",
            account_name="Utenze",
            debit=800.0,
            credit=0.0,
            description="Costo netto",
        ),
        JournalLine(
            entry_id=entry.id,
            account_code="1120",
            account_name="Crediti IVA",
            debit=176.0,
            credit=0.0,
            description="IVA credito",
        ),
        JournalLine(
            entry_id=entry.id,
            account_code="2010",
            account_name="Debiti verso fornitori",
            debit=0.0,
            credit=976.0,
            description="Debito fornitore",
        ),
    ]
    for line in lines:
        db_session.add(line)
    await db_session.flush()

    return entry


@pytest.fixture
async def onboarding_user(db_session: AsyncSession, tenant: Tenant) -> User:
    """A user for onboarding tests."""
    user = User(
        email="onboarding.user@example.com",
        password_hash=_hash_pw("Password1"),
        name="Onboarding User",
        role="owner",
        email_verified=True,
        tenant_id=tenant.id,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def onboarding_auth_headers(client: AsyncClient, onboarding_user: User) -> dict:
    """Auth headers for onboarding user."""
    token = await get_auth_token(client, "onboarding.user@example.com", "Password1")
    return {"Authorization": f"Bearer {token}"}
