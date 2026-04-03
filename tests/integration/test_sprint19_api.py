"""Sprint 19 tests — US-75 (chiusura scadenze), US-76 (insoluti), US-77 (cash flow)."""

import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import BankAccount, Scadenza, Tenant
from api.modules.scadenzario.service import ScadenzarioService


async def _make_tenant(db: AsyncSession, piva: str = "19191919191") -> Tenant:
    t = Tenant(name="Sprint19 SRL", type="srl", regime_fiscale="ordinario", piva=piva)
    db.add(t)
    await db.flush()
    return t


# ============================================================
# US-75: Chiusura automatica scadenze
# ============================================================


@pytest.mark.asyncio
async def test_ac_75_1_incasso_fattura_attiva(db_session: AsyncSession):
    """AC-75.1: Riconciliazione fattura attiva → stato 'incassato'."""
    t = await _make_tenant(db_session, "75757575751")
    sc = Scadenza(
        tenant_id=t.id, tipo="attivo", source_type="fattura",
        controparte="Cliente Alpha", importo_lordo=6100.0, importo_netto=5000.0,
        importo_iva=1100.0, data_scadenza=date(2026, 5, 1), stato="aperto",
    )
    db_session.add(sc)
    await db_session.flush()

    svc = ScadenzarioService(db_session)
    result = await svc.chiudi_scadenza(sc.id, 6100.0, date(2026, 4, 28))

    assert result["stato"] == "incassato"
    assert result["importo_pagato"] == 6100.0
    assert result["residuo"] == 0


@pytest.mark.asyncio
async def test_ac_75_2_pagamento_fattura_passiva(db_session: AsyncSession):
    """AC-75.2: Riconciliazione fattura passiva → stato 'pagato'."""
    t = await _make_tenant(db_session, "75757575752")
    sc = Scadenza(
        tenant_id=t.id, tipo="passivo", source_type="fattura",
        controparte="Fornitore Beta", importo_lordo=2440.0, importo_netto=2000.0,
        importo_iva=440.0, data_scadenza=date(2026, 4, 15), stato="aperto",
    )
    db_session.add(sc)
    await db_session.flush()

    svc = ScadenzarioService(db_session)
    result = await svc.chiudi_scadenza(sc.id, 2440.0, date(2026, 4, 14))

    assert result["stato"] == "pagato"
    assert result["residuo"] == 0


@pytest.mark.asyncio
async def test_ac_75_3_pagamento_parziale(db_session: AsyncSession):
    """AC-75.3: Importo parziale → stato 'parziale' con residuo."""
    t = await _make_tenant(db_session, "75757575753")
    sc = Scadenza(
        tenant_id=t.id, tipo="attivo", source_type="fattura",
        controparte="Cliente Parziale", importo_lordo=10000.0, importo_netto=8197.0,
        importo_iva=1803.0, data_scadenza=date(2026, 6, 1), stato="aperto",
    )
    db_session.add(sc)
    await db_session.flush()

    svc = ScadenzarioService(db_session)
    result = await svc.chiudi_scadenza(sc.id, 5000.0, date(2026, 5, 15))

    assert result["stato"] == "parziale"
    assert result["importo_pagato"] == 5000.0
    assert result["residuo"] == 5000.0


@pytest.mark.asyncio
async def test_ac_75_4_scarico_anticipo(db_session: AsyncSession):
    """AC-75.4: Se anticipata, segnala scarico anticipo."""
    t = await _make_tenant(db_session, "75757575754")
    anticipo_id = uuid.uuid4()
    sc = Scadenza(
        tenant_id=t.id, tipo="attivo", source_type="fattura",
        controparte="Cliente Anticipato", importo_lordo=5000.0, importo_netto=4098.0,
        data_scadenza=date(2026, 5, 1), stato="aperto",
        anticipata=True, anticipo_id=anticipo_id,
    )
    db_session.add(sc)
    await db_session.flush()

    svc = ScadenzarioService(db_session)
    result = await svc.chiudi_scadenza(sc.id, 5000.0, date(2026, 4, 30))

    assert result["stato"] == "incassato"
    assert result["anticipo_da_scaricare"] == str(anticipo_id)


# ============================================================
# US-76: Gestione insoluti
# ============================================================


@pytest.mark.asyncio
async def test_ac_76_1_segna_insoluto(db_session: AsyncSession):
    """AC-76.1: Pulsante 'Segna insoluto' su scadenze attive."""
    t = await _make_tenant(db_session, "76767676761")
    sc = Scadenza(
        tenant_id=t.id, tipo="attivo", source_type="fattura",
        controparte="Cliente Moroso", importo_lordo=3000.0, importo_netto=2459.0,
        data_scadenza=date(2026, 2, 1), stato="aperto",
    )
    db_session.add(sc)
    await db_session.flush()

    svc = ScadenzarioService(db_session)
    result = await svc.segna_insoluto(sc.id)

    assert result["stato"] == "insoluto"
    assert result["controparte"] == "Cliente Moroso"


@pytest.mark.asyncio
async def test_ac_76_2_insoluto_anticipata_warning(db_session: AsyncSession):
    """AC-76.2: Se anticipata, avviso riaddebito banca."""
    t = await _make_tenant(db_session, "76767676762")
    anticipo_id = uuid.uuid4()
    sc = Scadenza(
        tenant_id=t.id, tipo="attivo", source_type="fattura",
        controparte="Cliente Anticipato Moroso", importo_lordo=8000.0, importo_netto=6557.0,
        data_scadenza=date(2026, 3, 1), stato="aperto",
        anticipata=True, anticipo_id=anticipo_id,
    )
    db_session.add(sc)
    await db_session.flush()

    svc = ScadenzarioService(db_session)
    result = await svc.segna_insoluto(sc.id)

    assert result["stato"] == "insoluto"
    assert "warning" in result
    assert "riaddebiterà" in result["warning"]
    assert result["anticipo_id"] == str(anticipo_id)


@pytest.mark.asyncio
async def test_ac_76_3_insoluto_in_scadenzario(db_session: AsyncSession):
    """AC-76.3/76.4: Insoluto resta nello scadenzario con badge rosso."""
    t = await _make_tenant(db_session, "76767676763")
    sc = Scadenza(
        tenant_id=t.id, tipo="attivo", source_type="fattura",
        controparte="Cliente Insoluto", importo_lordo=4000.0, importo_netto=3279.0,
        data_scadenza=date(2026, 1, 15), stato="aperto",
    )
    db_session.add(sc)
    await db_session.flush()

    svc = ScadenzarioService(db_session)
    await svc.segna_insoluto(sc.id)

    # Should still appear in list with colore=red
    result = await svc.list_attivo(t.id)
    assert result["count"] == 1
    assert result["items"][0]["stato"] == "insoluto"
    assert result["items"][0]["colore"] == "red"


@pytest.mark.asyncio
async def test_ac_76_passivo_non_insoluto(db_session: AsyncSession):
    """AC-76: Solo scadenze attive possono essere insolute."""
    t = await _make_tenant(db_session, "76767676764")
    sc = Scadenza(
        tenant_id=t.id, tipo="passivo", source_type="fattura",
        controparte="Fornitore", importo_lordo=1000.0, importo_netto=820.0,
        data_scadenza=date(2026, 3, 1), stato="aperto",
    )
    db_session.add(sc)
    await db_session.flush()

    svc = ScadenzarioService(db_session)
    result = await svc.segna_insoluto(sc.id)
    assert "error" in result


# ============================================================
# US-77: Cash flow previsionale
# ============================================================


@pytest.mark.asyncio
async def test_ac_77_1_calcolo_cash_flow(db_session: AsyncSession):
    """AC-77.1: saldo_banca + incassi - pagamenti."""
    t = await _make_tenant(db_session, "77777777771")

    # Bank with balance
    db_session.add(BankAccount(
        tenant_id=t.id, iban="IT60X0542811101000000777777",
        bank_name="Banca Test", provider="manual", status="connected",
        balance=50000.0,
    ))

    today = date.today()
    # Incasso previsto tra 10gg
    db_session.add(Scadenza(
        tenant_id=t.id, tipo="attivo", source_type="fattura",
        controparte="Cliente", importo_lordo=10000.0, importo_netto=8197.0,
        data_scadenza=today + timedelta(days=10), stato="aperto",
    ))
    # Pagamento previsto tra 15gg
    db_session.add(Scadenza(
        tenant_id=t.id, tipo="passivo", source_type="fattura",
        controparte="Fornitore", importo_lordo=3000.0, importo_netto=2459.0,
        data_scadenza=today + timedelta(days=15), stato="aperto",
    ))
    await db_session.flush()

    svc = ScadenzarioService(db_session)
    result = await svc.cash_flow_previsionale(t.id, giorni=30)

    assert result["saldo_banca_attuale"] == 50000.0
    assert result["incassi_previsti"] == 10000.0
    assert result["pagamenti_previsti"] == 3000.0
    assert result["saldo_previsto"] == 57000.0  # 50000 + 10000 - 3000


@pytest.mark.asyncio
async def test_ac_77_2_vista_30_60_90(db_session: AsyncSession):
    """AC-77.2: Vista 30/60/90 giorni selezionabile."""
    t = await _make_tenant(db_session, "77777777772")
    today = date.today()

    # Scadenza a 45gg (within 60, not 30)
    db_session.add(Scadenza(
        tenant_id=t.id, tipo="attivo", source_type="fattura",
        controparte="Cliente Lontano", importo_lordo=5000.0, importo_netto=4098.0,
        data_scadenza=today + timedelta(days=45), stato="aperto",
    ))
    await db_session.flush()

    svc = ScadenzarioService(db_session)

    r30 = await svc.cash_flow_previsionale(t.id, giorni=30)
    r60 = await svc.cash_flow_previsionale(t.id, giorni=60)

    # 30gg: should NOT include the 45gg scadenza
    assert r30["incassi_previsti"] == 0.0
    # 60gg: should include it
    assert r60["incassi_previsti"] == 5000.0


@pytest.mark.asyncio
async def test_ac_77_3_breakdown_settimanale(db_session: AsyncSession):
    """AC-77.3: Grafico settimanale con saldo progressivo."""
    t = await _make_tenant(db_session, "77777777773")
    today = date.today()

    db_session.add(BankAccount(
        tenant_id=t.id, iban="IT60X0542811101000000777773",
        bank_name="Banca Chart", provider="manual", status="connected",
        balance=10000.0,
    ))
    db_session.add(Scadenza(
        tenant_id=t.id, tipo="attivo", source_type="fattura",
        controparte="Inc1", importo_lordo=2000.0, importo_netto=1639.0,
        data_scadenza=today + timedelta(days=7), stato="aperto",
    ))
    await db_session.flush()

    svc = ScadenzarioService(db_session)
    result = await svc.cash_flow_previsionale(t.id, giorni=30)

    assert "breakdown" in result
    assert len(result["breakdown"]) > 0
    # Last week should have progressive balance
    last_week = result["breakdown"][-1]
    assert "saldo_progressivo" in last_week


@pytest.mark.asyncio
async def test_ac_77_4_alert_soglia(db_session: AsyncSession):
    """AC-77.4: Alert se saldo previsto sotto soglia."""
    t = await _make_tenant(db_session, "77777777774")
    today = date.today()

    # Low balance bank
    db_session.add(BankAccount(
        tenant_id=t.id, iban="IT60X0542811101000000777774",
        bank_name="Banca Povera", provider="manual", status="connected",
        balance=1000.0,
    ))
    # Big payment coming
    db_session.add(Scadenza(
        tenant_id=t.id, tipo="passivo", source_type="fattura",
        controparte="Grande Fornitore", importo_lordo=5000.0, importo_netto=4098.0,
        data_scadenza=today + timedelta(days=10), stato="aperto",
    ))
    await db_session.flush()

    svc = ScadenzarioService(db_session)
    result = await svc.cash_flow_previsionale(t.id, giorni=30, soglia_alert=0.0)

    # saldo_previsto = 1000 - 5000 = -4000 < 0 (soglia)
    assert result["saldo_previsto"] == -4000.0
    assert result["alert"] is not None
    assert "sotto la soglia" in result["alert"]["messaggio"]


@pytest.mark.asyncio
async def test_ac_77_no_alert_above_soglia(db_session: AsyncSession):
    """AC-77.4: No alert se saldo sopra soglia."""
    t = await _make_tenant(db_session, "77777777775")

    db_session.add(BankAccount(
        tenant_id=t.id, iban="IT60X0542811101000000777775",
        bank_name="Banca Ricca", provider="manual", status="connected",
        balance=100000.0,
    ))
    await db_session.flush()

    svc = ScadenzarioService(db_session)
    result = await svc.cash_flow_previsionale(t.id, giorni=30, soglia_alert=5000.0)

    assert result["saldo_previsto"] == 100000.0
    assert result["alert"] is None


# ============================================================
# API endpoint tests
# ============================================================


@pytest.mark.asyncio
async def test_api_chiudi_scadenza(client, auth_headers, db_session, tenant):
    """API: POST /scadenzario/{id}/chiudi."""
    sc = Scadenza(
        tenant_id=tenant.id, tipo="attivo", source_type="fattura",
        controparte="API Client", importo_lordo=1220.0, importo_netto=1000.0,
        data_scadenza=date(2026, 5, 1), stato="aperto",
    )
    db_session.add(sc)
    await db_session.flush()

    resp = await client.post(
        f"/api/v1/scadenzario/{sc.id}/chiudi",
        json={"importo_pagato": 1220.0, "data_pagamento": "2026-04-30"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["stato"] == "incassato"


@pytest.mark.asyncio
async def test_api_segna_insoluto(client, auth_headers, db_session, tenant):
    """API: POST /scadenzario/{id}/insoluto."""
    sc = Scadenza(
        tenant_id=tenant.id, tipo="attivo", source_type="fattura",
        controparte="API Moroso", importo_lordo=3000.0, importo_netto=2459.0,
        data_scadenza=date(2026, 2, 1), stato="aperto",
    )
    db_session.add(sc)
    await db_session.flush()

    resp = await client.post(
        f"/api/v1/scadenzario/{sc.id}/insoluto",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["stato"] == "insoluto"


@pytest.mark.asyncio
async def test_api_cash_flow(client, auth_headers, db_session, tenant):
    """API: GET /scadenzario/cash-flow."""
    resp = await client.get(
        "/api/v1/scadenzario/cash-flow?giorni=30",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "saldo_banca_attuale" in data
    assert "incassi_previsti" in data
    assert "pagamenti_previsti" in data
    assert "saldo_previsto" in data
