"""Sprint 18 tests — US-72 (auto scadenze), US-73 (scadenzario attivo), US-74 (scadenzario passivo).

Tests verify automatic scadenza generation from invoices and list endpoints.
"""

import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import BankAccount, Invoice, Scadenza, Tenant, User
from api.modules.scadenzario.service import ScadenzarioService
from tests.conftest import _hash_pw


async def _setup(db: AsyncSession):
    """Create tenant, user, and sample invoices."""
    tenant = Tenant(
        name="Scad18 SRL", type="srl",
        regime_fiscale="ordinario", piva="18181818181",
    )
    db.add(tenant)
    await db.flush()

    user = User(
        email="scad18@example.com",
        password_hash=_hash_pw("Password1"),
        name="Scad18 User", role="owner",
        email_verified=True, tenant_id=tenant.id,
    )
    db.add(user)

    # Fattura attiva: netto 5000, IVA 1100, totale 6100, data 2026-03-01
    inv_attiva = Invoice(
        tenant_id=tenant.id, type="attiva", document_type="TD01",
        source="sdi", numero_fattura="FA-SC18-001",
        emittente_piva="18181818181", emittente_nome="Scad18 SRL",
        data_fattura=date(2026, 3, 1),
        importo_netto=5000.0, importo_iva=1100.0, importo_totale=6100.0,
        processing_status="registered",
        structured_data={
            "destinatario_nome": "Cliente Omega SPA",
            "destinatario_piva": "77777777777",
            "giorni_pagamento": 60,
        },
    )
    db.add(inv_attiva)

    # Fattura passiva: netto 2000, IVA 440, totale 2440, data 2026-03-10
    inv_passiva = Invoice(
        tenant_id=tenant.id, type="passiva", document_type="TD01",
        source="cassetto_fiscale", numero_fattura="FP-SC18-001",
        emittente_piva="66666666666", emittente_nome="Fornitore Sigma SRL",
        data_fattura=date(2026, 3, 10),
        importo_netto=2000.0, importo_iva=440.0, importo_totale=2440.0,
        processing_status="registered",
    )
    db.add(inv_passiva)

    # Fattura senza data (should be skipped)
    inv_nodate = Invoice(
        tenant_id=tenant.id, type="passiva", document_type="TD01",
        source="upload", numero_fattura="FP-SC18-NODATE",
        emittente_piva="55555555555", emittente_nome="NoDate SRL",
        importo_netto=100.0, importo_iva=22.0, importo_totale=122.0,
        processing_status="pending",
    )
    db.add(inv_nodate)

    await db.flush()
    return tenant, user, inv_attiva, inv_passiva


# ============================================================
# US-72: Generazione automatica scadenze da fatture
# ============================================================


@pytest.mark.asyncio
async def test_ac_72_1_fattura_attiva_genera_scadenza_attivo(db_session: AsyncSession):
    """AC-72.1: Fattura attiva → scadenza tipo 'attivo' con data = data_fattura + giorni_pagamento."""
    tenant, user, inv_a, inv_p = await _setup(db_session)
    svc = ScadenzarioService(db_session)

    sc = await svc.generate_from_invoice(inv_a)

    assert sc is not None
    assert sc.tipo == "attivo"
    assert sc.source_type == "fattura"
    assert sc.source_id == inv_a.id
    assert sc.controparte == "Cliente Omega SPA"
    # data_fattura + 60 giorni (from structured_data)
    expected_date = date(2026, 3, 1) + timedelta(days=60)
    assert sc.data_scadenza == expected_date


@pytest.mark.asyncio
async def test_ac_72_2_fattura_passiva_genera_scadenza_passivo(db_session: AsyncSession):
    """AC-72.2: Fattura passiva → scadenza tipo 'passivo'."""
    tenant, user, inv_a, inv_p = await _setup(db_session)
    svc = ScadenzarioService(db_session)

    sc = await svc.generate_from_invoice(inv_p)

    assert sc is not None
    assert sc.tipo == "passivo"
    assert sc.controparte == "Fornitore Sigma SRL"


@pytest.mark.asyncio
async def test_ac_72_3_importi_separati(db_session: AsyncSession):
    """AC-72.3: Importo scadenza include lordo, netto, IVA separati."""
    tenant, user, inv_a, inv_p = await _setup(db_session)
    svc = ScadenzarioService(db_session)

    sc = await svc.generate_from_invoice(inv_a)

    assert sc.importo_lordo == 6100.0
    assert sc.importo_netto == 5000.0
    assert sc.importo_iva == 1100.0


@pytest.mark.asyncio
async def test_ac_72_4_banca_appoggio(db_session: AsyncSession):
    """AC-72.4: Banca appoggio da IBAN fattura."""
    tenant, user, inv_a, inv_p = await _setup(db_session)

    # Create bank account and set IBAN on invoice
    bank = BankAccount(
        tenant_id=tenant.id, iban="IT60X0542811101000000999999",
        bank_name="UniCredit", provider="manual", status="connected",
    )
    db_session.add(bank)
    await db_session.flush()

    inv_a.structured_data["iban"] = "IT60X0542811101000000999999"
    await db_session.flush()

    svc = ScadenzarioService(db_session)
    sc = await svc.generate_from_invoice(inv_a)

    assert sc.banca_appoggio_id == bank.id


@pytest.mark.asyncio
async def test_ac_72_5_default_30gg(db_session: AsyncSession):
    """AC-72.5: Se giorni_pagamento non specificato, default 30gg."""
    tenant, user, inv_a, inv_p = await _setup(db_session)
    svc = ScadenzarioService(db_session)

    # inv_passiva has no giorni_pagamento → default 30
    sc = await svc.generate_from_invoice(inv_p)

    expected_date = date(2026, 3, 10) + timedelta(days=30)
    assert sc.data_scadenza == expected_date


@pytest.mark.asyncio
async def test_ac_72_generate_all_missing(db_session: AsyncSession):
    """US-72: generate_all_missing creates scadenze for all invoices without one."""
    tenant, user, inv_a, inv_p = await _setup(db_session)
    svc = ScadenzarioService(db_session)

    # Should generate 2 (attiva + passiva), skip the one without date
    count = await svc.generate_all_missing(tenant.id)
    assert count == 2

    # Running again should generate 0 (idempotent)
    count2 = await svc.generate_all_missing(tenant.id)
    assert count2 == 0


# ============================================================
# US-73: Visualizzazione scadenzario attivo (crediti)
# ============================================================


@pytest.mark.asyncio
async def test_ac_73_1_lista_ordinata(db_session: AsyncSession):
    """AC-73.1: Lista scadenze attive ordinata per data scadenza."""
    tenant, user, inv_a, inv_p = await _setup(db_session)
    svc = ScadenzarioService(db_session)
    await svc.generate_all_missing(tenant.id)

    result = await svc.list_attivo(tenant.id)

    assert result["tipo"] == "attivo"
    assert result["count"] == 1
    items = result["items"]
    assert items[0]["controparte"] == "Cliente Omega SPA"


@pytest.mark.asyncio
async def test_ac_73_2_colonne_complete(db_session: AsyncSession):
    """AC-73.2: Colonne: controparte, source_type, importo, scadenza, giorni, stato."""
    tenant, user, inv_a, inv_p = await _setup(db_session)
    svc = ScadenzarioService(db_session)
    await svc.generate_all_missing(tenant.id)

    result = await svc.list_attivo(tenant.id)
    item = result["items"][0]

    assert "controparte" in item
    assert "importo_lordo" in item
    assert "importo_netto" in item
    assert "data_scadenza" in item
    assert "giorni_residui" in item
    assert "stato" in item
    assert item["importo_lordo"] == 6100.0
    assert item["importo_netto"] == 5000.0


@pytest.mark.asyncio
async def test_ac_73_3_stati(db_session: AsyncSession):
    """AC-73.3: Stati possibili funzionano."""
    tenant, user, inv_a, inv_p = await _setup(db_session)
    svc = ScadenzarioService(db_session)
    await svc.generate_all_missing(tenant.id)

    result = await svc.list_attivo(tenant.id)
    assert result["items"][0]["stato"] == "aperto"


@pytest.mark.asyncio
async def test_ac_73_4_colori(db_session: AsyncSession):
    """AC-73.4: Colore rosso se scaduta, giallo se ≤7gg, verde altrimenti."""
    tenant = Tenant(
        name="Colori SRL", type="srl",
        regime_fiscale="ordinario", piva="73737373731",
    )
    db_session.add(tenant)
    await db_session.flush()

    today = date.today()

    # Scadenza gia passata → rosso
    db_session.add(Scadenza(
        tenant_id=tenant.id, tipo="attivo", source_type="fattura",
        controparte="Scaduta SPA", importo_lordo=1000.0, importo_netto=820.0,
        data_scadenza=today - timedelta(days=5), stato="aperto",
    ))
    # Scadenza tra 3 giorni → giallo
    db_session.add(Scadenza(
        tenant_id=tenant.id, tipo="attivo", source_type="fattura",
        controparte="Urgente SPA", importo_lordo=2000.0, importo_netto=1640.0,
        data_scadenza=today + timedelta(days=3), stato="aperto",
    ))
    # Scadenza tra 30 giorni → verde
    db_session.add(Scadenza(
        tenant_id=tenant.id, tipo="attivo", source_type="fattura",
        controparte="Tranquilla SPA", importo_lordo=3000.0, importo_netto=2460.0,
        data_scadenza=today + timedelta(days=30), stato="aperto",
    ))
    await db_session.flush()

    svc = ScadenzarioService(db_session)
    result = await svc.list_attivo(tenant.id)

    items = result["items"]
    assert len(items) == 3

    scaduta = next(i for i in items if i["controparte"] == "Scaduta SPA")
    urgente = next(i for i in items if i["controparte"] == "Urgente SPA")
    tranquilla = next(i for i in items if i["controparte"] == "Tranquilla SPA")

    assert scaduta["colore"] == "red"
    assert urgente["colore"] == "yellow"
    assert tranquilla["colore"] == "green"


@pytest.mark.asyncio
async def test_ac_73_5_filtri(db_session: AsyncSession):
    """AC-73.5: Filtri per stato, controparte."""
    tenant, user, inv_a, inv_p = await _setup(db_session)
    svc = ScadenzarioService(db_session)
    await svc.generate_all_missing(tenant.id)

    # Filter by controparte
    result = await svc.list_attivo(tenant.id, controparte="Omega")
    assert result["count"] == 1

    # Filter by controparte that doesn't exist
    result = await svc.list_attivo(tenant.id, controparte="NonEsiste")
    assert result["count"] == 0


@pytest.mark.asyncio
async def test_ac_73_6_totali_per_stato(db_session: AsyncSession):
    """AC-73.6: Totale importi per stato."""
    tenant, user, inv_a, inv_p = await _setup(db_session)
    svc = ScadenzarioService(db_session)
    await svc.generate_all_missing(tenant.id)

    result = await svc.list_attivo(tenant.id)
    assert "aperto" in result["totals"]
    assert result["totals"]["aperto"] == 6100.0


# ============================================================
# US-74: Visualizzazione scadenzario passivo (debiti)
# ============================================================


@pytest.mark.asyncio
async def test_ac_74_1_lista_passivo(db_session: AsyncSession):
    """AC-74.1: Lista scadenze passive da fatture passive."""
    tenant, user, inv_a, inv_p = await _setup(db_session)
    svc = ScadenzarioService(db_session)
    await svc.generate_all_missing(tenant.id)

    result = await svc.list_passivo(tenant.id)

    assert result["tipo"] == "passivo"
    assert result["count"] == 1
    assert result["items"][0]["controparte"] == "Fornitore Sigma SRL"


@pytest.mark.asyncio
async def test_ac_74_2_colonne_passivo(db_session: AsyncSession):
    """AC-74.2: Colonne complete per passivo."""
    tenant, user, inv_a, inv_p = await _setup(db_session)
    svc = ScadenzarioService(db_session)
    await svc.generate_all_missing(tenant.id)

    result = await svc.list_passivo(tenant.id)
    item = result["items"][0]

    assert item["importo_lordo"] == 2440.0
    assert item["importo_netto"] == 2000.0
    assert item["importo_iva"] == 440.0
    assert item["stato"] == "aperto"


@pytest.mark.asyncio
async def test_ac_74_3_stati_passivo(db_session: AsyncSession):
    """AC-74.3: Stati passivo: aperto, pagato."""
    tenant = Tenant(
        name="Passivo SRL", type="srl",
        regime_fiscale="ordinario", piva="74747474741",
    )
    db_session.add(tenant)
    await db_session.flush()

    db_session.add(Scadenza(
        tenant_id=tenant.id, tipo="passivo", source_type="fattura",
        controparte="Fornitore Pagato", importo_lordo=500.0, importo_netto=410.0,
        data_scadenza=date(2026, 2, 15), stato="pagato",
        data_pagamento=date(2026, 2, 14),
    ))
    db_session.add(Scadenza(
        tenant_id=tenant.id, tipo="passivo", source_type="fattura",
        controparte="Fornitore Aperto", importo_lordo=1000.0, importo_netto=820.0,
        data_scadenza=date(2026, 4, 15), stato="aperto",
    ))
    await db_session.flush()

    svc = ScadenzarioService(db_session)
    result = await svc.list_passivo(tenant.id)
    assert result["count"] == 2

    # Filter by stato
    result_pagato = await svc.list_passivo(tenant.id, stato="pagato")
    assert result_pagato["count"] == 1
    assert result_pagato["items"][0]["controparte"] == "Fornitore Pagato"


@pytest.mark.asyncio
async def test_ac_74_5_totali_passivo(db_session: AsyncSession):
    """AC-74.5: Totale importi per stato passivo."""
    tenant, user, inv_a, inv_p = await _setup(db_session)
    svc = ScadenzarioService(db_session)
    await svc.generate_all_missing(tenant.id)

    result = await svc.list_passivo(tenant.id)
    assert result["totals"]["aperto"] == 2440.0


# ============================================================
# API endpoint tests
# ============================================================


@pytest.mark.asyncio
async def test_api_generate_scadenze(client, auth_headers, db_session, tenant):
    """API: POST /scadenzario/generate creates missing scadenze."""
    # Create an invoice first
    db_session.add(Invoice(
        tenant_id=tenant.id, type="attiva", document_type="TD01",
        source="sdi", numero_fattura="FA-API-001",
        emittente_piva="12345678901", emittente_nome="Test SRL",
        data_fattura=date(2026, 4, 1),
        importo_netto=1000.0, importo_iva=220.0, importo_totale=1220.0,
        processing_status="registered",
        structured_data={"destinatario_nome": "API Client"},
    ))
    await db_session.flush()

    resp = await client.post("/api/v1/scadenzario/generate", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["generated"] >= 1


@pytest.mark.asyncio
async def test_api_list_attivo(client, auth_headers, db_session, tenant):
    """API: GET /scadenzario/attivo returns active deadlines."""
    db_session.add(Scadenza(
        tenant_id=tenant.id, tipo="attivo", source_type="fattura",
        controparte="API Client SPA", importo_lordo=1220.0, importo_netto=1000.0,
        importo_iva=220.0, data_scadenza=date(2026, 5, 1), stato="aperto",
    ))
    await db_session.flush()

    resp = await client.get("/api/v1/scadenzario/attivo", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["tipo"] == "attivo"
    assert data["count"] == 1


@pytest.mark.asyncio
async def test_api_list_passivo(client, auth_headers, db_session, tenant):
    """API: GET /scadenzario/passivo returns passive deadlines."""
    db_session.add(Scadenza(
        tenant_id=tenant.id, tipo="passivo", source_type="fattura",
        controparte="API Fornitore", importo_lordo=2440.0, importo_netto=2000.0,
        importo_iva=440.0, data_scadenza=date(2026, 5, 15), stato="aperto",
    ))
    await db_session.flush()

    resp = await client.get("/api/v1/scadenzario/passivo", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["tipo"] == "passivo"
    assert data["count"] == 1
