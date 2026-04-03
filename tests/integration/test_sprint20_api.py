"""Sprint 20 tests — US-78 (cash flow per banca), US-79 (config fidi)."""

import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import BankAccount, BankFacility, InvoiceAdvance, Scadenza, Tenant
from api.modules.scadenzario.service import ScadenzarioService


async def _make_tenant(db: AsyncSession, piva: str) -> Tenant:
    t = Tenant(name="S20 SRL", type="srl", regime_fiscale="ordinario", piva=piva)
    db.add(t)
    await db.flush()
    return t


# ============================================================
# US-78: Cash flow per banca
# ============================================================


@pytest.mark.asyncio
async def test_ac_78_1_filtro_banca(db_session: AsyncSession):
    """AC-78.1: Cash flow separato per ogni conto bancario."""
    t = await _make_tenant(db_session, "78787878781")
    today = date.today()

    bank1 = BankAccount(
        tenant_id=t.id, iban="IT60X0542811101000000111111",
        bank_name="UniCredit", provider="manual", status="connected", balance=30000.0,
    )
    bank2 = BankAccount(
        tenant_id=t.id, iban="IT60X0542811101000000222222",
        bank_name="Intesa", provider="manual", status="connected", balance=20000.0,
    )
    db_session.add(bank1)
    db_session.add(bank2)
    await db_session.flush()

    # Incasso su bank1
    db_session.add(Scadenza(
        tenant_id=t.id, tipo="attivo", source_type="fattura",
        controparte="Cliente A", importo_lordo=5000.0, importo_netto=4098.0,
        data_scadenza=today + timedelta(days=10), stato="aperto",
        banca_appoggio_id=bank1.id,
    ))
    # Incasso su bank2
    db_session.add(Scadenza(
        tenant_id=t.id, tipo="attivo", source_type="fattura",
        controparte="Cliente B", importo_lordo=8000.0, importo_netto=6557.0,
        data_scadenza=today + timedelta(days=15), stato="aperto",
        banca_appoggio_id=bank2.id,
    ))
    await db_session.flush()

    svc = ScadenzarioService(db_session)
    result = await svc.cash_flow_per_banca(t.id, giorni=30)

    assert len(result) == 2

    uc = next(b for b in result if b["bank_name"] == "UniCredit")
    intesa = next(b for b in result if b["bank_name"] == "Intesa")

    assert uc["saldo_attuale"] == 30000.0
    assert uc["incassi_previsti"] == 5000.0
    assert uc["saldo_previsto"] == 35000.0

    assert intesa["saldo_attuale"] == 20000.0
    assert intesa["incassi_previsti"] == 8000.0
    assert intesa["saldo_previsto"] == 28000.0


@pytest.mark.asyncio
async def test_ac_78_2_incassi_su_banca_appoggio(db_session: AsyncSession):
    """AC-78.2: Incassi vanno sul conto della banca appoggio."""
    t = await _make_tenant(db_session, "78787878782")
    today = date.today()

    bank = BankAccount(
        tenant_id=t.id, iban="IT60X0542811101000000333333",
        bank_name="BancaSola", provider="manual", status="connected", balance=10000.0,
    )
    db_session.add(bank)
    await db_session.flush()

    # Scadenza WITHOUT banca_appoggio → should NOT appear in this bank's CF
    db_session.add(Scadenza(
        tenant_id=t.id, tipo="attivo", source_type="fattura",
        controparte="Senza Banca", importo_lordo=3000.0, importo_netto=2459.0,
        data_scadenza=today + timedelta(days=5), stato="aperto",
        banca_appoggio_id=None,
    ))
    # Scadenza WITH banca_appoggio
    db_session.add(Scadenza(
        tenant_id=t.id, tipo="attivo", source_type="fattura",
        controparte="Con Banca", importo_lordo=7000.0, importo_netto=5738.0,
        data_scadenza=today + timedelta(days=10), stato="aperto",
        banca_appoggio_id=bank.id,
    ))
    await db_session.flush()

    svc = ScadenzarioService(db_session)
    result = await svc.cash_flow_per_banca(t.id, giorni=30)

    assert len(result) == 1
    assert result[0]["incassi_previsti"] == 7000.0  # only the one with banca_appoggio


# ============================================================
# US-79: Configurazione fido anticipo
# ============================================================


@pytest.mark.asyncio
async def test_ac_79_1_crud_fido(db_session: AsyncSession):
    """AC-79.1: CRUD fido bancario con tutti i campi."""
    t = await _make_tenant(db_session, "79797979791")
    bank = BankAccount(
        tenant_id=t.id, iban="IT60X0542811101000000444444",
        bank_name="BancaFido", provider="manual", status="connected",
    )
    db_session.add(bank)
    await db_session.flush()

    svc = ScadenzarioService(db_session)
    result = await svc.create_fido(t.id, {
        "bank_account_id": str(bank.id),
        "tipo": "anticipo_fatture",
        "plafond": 100000.0,
        "percentuale_anticipo": 80.0,
        "tasso_interesse_annuo": 3.5,
        "commissione_presentazione_pct": 0.3,
        "commissione_incasso": 2.50,
        "commissione_insoluto": 15.0,
        "giorni_max": 120,
    })

    assert "id" in result
    assert result["message"] == "Fido creato"


@pytest.mark.asyncio
async def test_ac_79_2_plafond_utilizzato_disponibile(db_session: AsyncSession):
    """AC-79.2: Plafond totale, utilizzato (da anticipi attivi), disponibile."""
    t = await _make_tenant(db_session, "79797979792")
    bank = BankAccount(
        tenant_id=t.id, iban="IT60X0542811101000000555555",
        bank_name="BancaPlafond", provider="manual", status="connected",
    )
    db_session.add(bank)
    await db_session.flush()

    facility = BankFacility(
        tenant_id=t.id, bank_account_id=bank.id,
        tipo="anticipo_fatture", plafond=100000.0,
        percentuale_anticipo=80.0, tasso_interesse_annuo=3.0,
    )
    db_session.add(facility)
    await db_session.flush()

    # Active advance using 40000 of plafond
    db_session.add(InvoiceAdvance(
        tenant_id=t.id, facility_id=facility.id, invoice_id=uuid.uuid4(),
        importo_fattura=50000.0, importo_anticipato=40000.0,
        data_presentazione=date(2026, 3, 1),
        data_scadenza_prevista=date(2026, 5, 1),
        stato="attivo",
    ))
    await db_session.flush()

    svc = ScadenzarioService(db_session)
    fidi = await svc.list_fidi(t.id)

    assert len(fidi) == 1
    assert fidi[0]["plafond"] == 100000.0
    assert fidi[0]["utilizzato"] == 40000.0
    assert fidi[0]["disponibile"] == 60000.0


@pytest.mark.asyncio
async def test_ac_79_3_stessa_banca(db_session: AsyncSession):
    """AC-79.3: La banca del fido è la stessa banca di appoggio."""
    t = await _make_tenant(db_session, "79797979793")
    bank = BankAccount(
        tenant_id=t.id, iban="IT60X0542811101000000666666",
        bank_name="BancaUnica", provider="manual", status="connected",
    )
    db_session.add(bank)
    await db_session.flush()

    svc = ScadenzarioService(db_session)
    result = await svc.create_fido(t.id, {
        "bank_account_id": str(bank.id),
        "plafond": 50000.0,
    })

    fidi = await svc.list_fidi(t.id)
    assert fidi[0]["bank_account_id"] == str(bank.id)
    assert fidi[0]["bank_name"] == "BancaUnica"


@pytest.mark.asyncio
async def test_ac_79_4_piu_fidi_banche_diverse(db_session: AsyncSession):
    """AC-79.4: Possibilità di avere più fidi su banche diverse."""
    t = await _make_tenant(db_session, "79797979794")
    bank1 = BankAccount(
        tenant_id=t.id, iban="IT60X0542811101000000777771",
        bank_name="Banca1", provider="manual", status="connected",
    )
    bank2 = BankAccount(
        tenant_id=t.id, iban="IT60X0542811101000000777772",
        bank_name="Banca2", provider="manual", status="connected",
    )
    db_session.add(bank1)
    db_session.add(bank2)
    await db_session.flush()

    svc = ScadenzarioService(db_session)
    await svc.create_fido(t.id, {"bank_account_id": str(bank1.id), "plafond": 50000.0})
    await svc.create_fido(t.id, {"bank_account_id": str(bank2.id), "plafond": 80000.0})

    fidi = await svc.list_fidi(t.id)
    assert len(fidi) == 2
    plafonds = {f["bank_name"]: f["plafond"] for f in fidi}
    assert plafonds["Banca1"] == 50000.0
    assert plafonds["Banca2"] == 80000.0


# ============================================================
# API endpoint tests
# ============================================================


@pytest.mark.asyncio
async def test_api_cash_flow_per_banca(client, auth_headers, db_session, tenant):
    """API: GET /scadenzario/cash-flow/per-banca."""
    resp = await client.get(
        "/api/v1/scadenzario/cash-flow/per-banca?giorni=30",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_api_list_fidi(client, auth_headers, db_session, tenant):
    """API: GET /fidi."""
    resp = await client.get("/api/v1/fidi", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_api_create_fido(client, auth_headers, db_session, tenant):
    """API: POST /fidi."""
    bank = BankAccount(
        tenant_id=tenant.id, iban="IT60X0542811101000000888888",
        bank_name="APIBanca", provider="manual", status="connected",
    )
    db_session.add(bank)
    await db_session.flush()

    resp = await client.post(
        "/api/v1/fidi",
        json={
            "bank_account_id": str(bank.id),
            "plafond": 75000.0,
            "percentuale_anticipo": 80.0,
            "tasso_interesse_annuo": 4.0,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert "id" in resp.json()
