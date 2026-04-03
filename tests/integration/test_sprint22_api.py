"""Sprint 22 tests — US-83 (confronto costi anticipo tra banche)."""

import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import BankAccount, BankFacility, Scadenza, Tenant
from api.modules.scadenzario.service import ScadenzarioService


@pytest.mark.asyncio
async def test_ac_83_1_tabella_confronto(db_session: AsyncSession):
    """AC-83.1: Tabella confronto per ogni banca con fido disponibile."""
    t = Tenant(name="Confronto SRL", type="srl", regime_fiscale="ordinario", piva="83838383831")
    db_session.add(t)
    await db_session.flush()

    bank1 = BankAccount(tenant_id=t.id, iban="IT60X1111111111", bank_name="BancaEconomica", provider="manual", status="connected")
    bank2 = BankAccount(tenant_id=t.id, iban="IT60X2222222222", bank_name="BancaCara", provider="manual", status="connected")
    db_session.add(bank1)
    db_session.add(bank2)
    await db_session.flush()

    db_session.add(BankFacility(
        tenant_id=t.id, bank_account_id=bank1.id, tipo="anticipo_fatture",
        plafond=200000.0, percentuale_anticipo=80.0, tasso_interesse_annuo=2.0,
        commissione_presentazione_pct=0.2,
    ))
    db_session.add(BankFacility(
        tenant_id=t.id, bank_account_id=bank2.id, tipo="anticipo_fatture",
        plafond=150000.0, percentuale_anticipo=75.0, tasso_interesse_annuo=5.0,
        commissione_presentazione_pct=0.8,
    ))
    await db_session.flush()

    sc = Scadenza(
        tenant_id=t.id, tipo="attivo", source_type="fattura",
        controparte="Cliente Confronto", importo_lordo=20000.0, importo_netto=16393.0,
        data_scadenza=date.today() + timedelta(days=90), stato="aperto",
    )
    db_session.add(sc)
    await db_session.flush()

    svc = ScadenzarioService(db_session)
    result = await svc.confronta_anticipi(sc.id)

    assert len(result) == 2


@pytest.mark.asyncio
async def test_ac_83_2_dettagli_per_banca(db_session: AsyncSession):
    """AC-83.2: Per ogni banca: anticipabile, commissione, interessi, costo totale, %."""
    t = Tenant(name="Dettagli SRL", type="srl", regime_fiscale="ordinario", piva="83838383832")
    db_session.add(t)
    await db_session.flush()

    bank = BankAccount(tenant_id=t.id, iban="IT60X3333333333", bank_name="BancaDettagli", provider="manual", status="connected")
    db_session.add(bank)
    await db_session.flush()

    db_session.add(BankFacility(
        tenant_id=t.id, bank_account_id=bank.id, tipo="anticipo_fatture",
        plafond=100000.0, percentuale_anticipo=80.0, tasso_interesse_annuo=3.65,
        commissione_presentazione_pct=0.5,
    ))
    await db_session.flush()

    sc = Scadenza(
        tenant_id=t.id, tipo="attivo", source_type="fattura",
        controparte="Cliente Det", importo_lordo=10000.0, importo_netto=8197.0,
        data_scadenza=date.today() + timedelta(days=60), stato="aperto",
    )
    db_session.add(sc)
    await db_session.flush()

    svc = ScadenzarioService(db_session)
    result = await svc.confronta_anticipi(sc.id)

    item = result[0]
    assert item["importo_anticipabile"] == 8000.0
    assert item["commissione"] == 50.0
    assert item["interessi_stimati"] > 0
    assert item["costo_totale"] > 0
    assert item["costo_pct_annuo"] > 0
    assert item["disponibile"] == 100000.0
    assert item["plafond_sufficiente"] is True


@pytest.mark.asyncio
async def test_ac_83_3_evidenzia_migliore(db_session: AsyncSession):
    """AC-83.3: Evidenzia la banca più conveniente."""
    t = Tenant(name="Migliore SRL", type="srl", regime_fiscale="ordinario", piva="83838383833")
    db_session.add(t)
    await db_session.flush()

    bank1 = BankAccount(tenant_id=t.id, iban="IT60X4444444441", bank_name="Economica", provider="manual", status="connected")
    bank2 = BankAccount(tenant_id=t.id, iban="IT60X4444444442", bank_name="Cara", provider="manual", status="connected")
    db_session.add(bank1)
    db_session.add(bank2)
    await db_session.flush()

    db_session.add(BankFacility(
        tenant_id=t.id, bank_account_id=bank1.id, tipo="anticipo_fatture",
        plafond=200000.0, percentuale_anticipo=80.0, tasso_interesse_annuo=1.5,
        commissione_presentazione_pct=0.1,
    ))
    db_session.add(BankFacility(
        tenant_id=t.id, bank_account_id=bank2.id, tipo="anticipo_fatture",
        plafond=200000.0, percentuale_anticipo=80.0, tasso_interesse_annuo=6.0,
        commissione_presentazione_pct=1.0,
    ))
    await db_session.flush()

    sc = Scadenza(
        tenant_id=t.id, tipo="attivo", source_type="fattura",
        controparte="Cliente Best", importo_lordo=10000.0, importo_netto=8197.0,
        data_scadenza=date.today() + timedelta(days=60), stato="aperto",
    )
    db_session.add(sc)
    await db_session.flush()

    svc = ScadenzarioService(db_session)
    result = await svc.confronta_anticipi(sc.id)

    # First in list should be cheapest and marked "migliore"
    assert result[0].get("migliore") is True
    assert result[0]["bank_name"] == "Economica"
    assert result[0]["costo_totale"] < result[1]["costo_totale"]


@pytest.mark.asyncio
async def test_ac_83_4_disponibilita_plafond(db_session: AsyncSession):
    """AC-83.4: Mostra disponibilità residua per ogni banca."""
    t = Tenant(name="Disp SRL", type="srl", regime_fiscale="ordinario", piva="83838383834")
    db_session.add(t)
    await db_session.flush()

    bank = BankAccount(tenant_id=t.id, iban="IT60X5555555555", bank_name="BancaDisp", provider="manual", status="connected")
    db_session.add(bank)
    await db_session.flush()

    db_session.add(BankFacility(
        tenant_id=t.id, bank_account_id=bank.id, tipo="anticipo_fatture",
        plafond=5000.0, percentuale_anticipo=80.0, tasso_interesse_annuo=3.0,
    ))
    await db_session.flush()

    # Invoice bigger than plafond → plafond_sufficiente = False
    sc = Scadenza(
        tenant_id=t.id, tipo="attivo", source_type="fattura",
        controparte="Big", importo_lordo=10000.0, importo_netto=8197.0,
        data_scadenza=date.today() + timedelta(days=30), stato="aperto",
    )
    db_session.add(sc)
    await db_session.flush()

    svc = ScadenzarioService(db_session)
    result = await svc.confronta_anticipi(sc.id)

    assert result[0]["plafond_sufficiente"] is False
    assert result[0]["disponibile"] == 5000.0
