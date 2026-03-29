"""Integration tests for corrispettivi telematici import (US-47)."""

import io
import os

import pytest
from httpx import AsyncClient

from tests.conftest import get_auth_token

SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<n1:DatiCorrispettivi xmlns:n1="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/corrispettivi/dati/v1.0" versione="COR10">
    <Trasmissione>
        <Progressivo>839</Progressivo>
        <Formato>COR10</Formato>
        <Dispositivo>
            <Tipo>RT</Tipo>
            <IdDispositivo>99IEB019690</IdDispositivo>
        </Dispositivo>
        <CodiceFiscaleEsercente>16877871000</CodiceFiscaleEsercente>
        <PIVAEsercente>16877871000</PIVAEsercente>
        <DataOraTrasmissione>2024-01-01T00:55:17+01:00</DataOraTrasmissione>
    </Trasmissione>
    <DataOraRilevazione>2024-01-01T00:54:39+01:00</DataOraRilevazione>
    <DatiRT>
        <Riepilogo>
            <IVA><AliquotaIVA>10.00</AliquotaIVA><Imposta>160.73</Imposta></IVA>
            <Ammontare>1607.27</Ammontare>
            <ImportoParziale>1607.27</ImportoParziale>
        </Riepilogo>
        <Riepilogo>
            <IVA><AliquotaIVA>22.00</AliquotaIVA><Imposta>0.00</Imposta></IVA>
            <Ammontare>0.00</Ammontare>
            <ImportoParziale>0.00</ImportoParziale>
        </Riepilogo>
        <Totali>
            <NumeroDocCommerciali>21</NumeroDocCommerciali>
            <PagatoContanti>373.00</PagatoContanti>
            <PagatoElettronico>1395.00</PagatoElettronico>
        </Totali>
    </DatiRT>
</n1:DatiCorrispettivi>"""


# --- AC-47.1: Parse XML COR10 → extract fields ---

@pytest.mark.asyncio
async def test_ac_47_1_parse_xml_extracts_fields(client: AsyncClient, verified_user):
    """AC-47.1: DATO un file XML COR10, QUANDO viene processato, ALLORA estrae tutti i campi."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")

    xml_file = io.BytesIO(SAMPLE_XML.encode("utf-8"))
    resp = await client.post(
        "/api/v1/corrispettivi/import-xml",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("corrispettivo.xml", xml_file, "application/xml")},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "imported"
    assert data["data"] == "2024-01-01"
    assert data["num_documenti"] == 21
    assert data["totale_incasso"] == 1768.0  # 373 + 1395
    assert data["totale_imponibile"] == 1607.27
    assert data["totale_imposta"] == 160.73
    assert data["contanti"] == 373.0
    assert data["elettronico"] == 1395.0
    assert data["corrispettivo_id"]
    assert data["journal_entry_id"]


# --- AC-47.2: Journal entry created automatically ---

@pytest.mark.asyncio
async def test_ac_47_2_journal_entry_created(client: AsyncClient, verified_user, db_session):
    """AC-47.2: DATO un corrispettivo parsato, QUANDO confermato, ALLORA crea scrittura contabile."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")

    xml_file = io.BytesIO(SAMPLE_XML.encode("utf-8"))
    resp = await client.post(
        "/api/v1/corrispettivi/import-xml",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("corr.xml", xml_file, "application/xml")},
    )

    data = resp.json()
    je_id = data["journal_entry_id"]

    # Verify journal entry in DB
    import uuid as uuid_mod
    from sqlalchemy import select
    from api.db.models import JournalEntry, JournalLine

    je_uuid = uuid_mod.UUID(je_id) if isinstance(je_id, str) else je_id
    je_result = await db_session.execute(
        select(JournalEntry).where(JournalEntry.id == je_uuid)
    )
    je = je_result.scalar_one()
    assert je.status == "posted"
    assert je.total_debit == 1768.0  # contanti + elettronico

    # Verify journal lines
    lines_result = await db_session.execute(
        select(JournalLine).where(JournalLine.entry_id == je_uuid)
    )
    lines = lines_result.scalars().all()

    # Should have: Dare Cassa (373) + Dare Banca POS (1395) + Avere Ricavi (1607.27) + Avere IVA (160.73)
    dare_total = sum(l.debit for l in lines)
    avere_total = sum(l.credit for l in lines)
    assert abs(dare_total - avere_total) < 0.01  # balanced

    dare_lines = [l for l in lines if l.debit > 0]
    assert len(dare_lines) == 2  # cassa + banca
    assert any(l.account_code == "cassa" for l in dare_lines)
    assert any(l.account_code == "banca_pos" for l in dare_lines)


# --- AC-47.3: Duplicate detection ---

@pytest.mark.asyncio
async def test_ac_47_3_duplicate_detected(client: AsyncClient, verified_user):
    """AC-47.3: DATO un corrispettivo gia importato, QUANDO reimportato, ALLORA segnala duplicato."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")

    # First import
    xml_file1 = io.BytesIO(SAMPLE_XML.encode("utf-8"))
    resp1 = await client.post(
        "/api/v1/corrispettivi/import-xml",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("corr.xml", xml_file1, "application/xml")},
    )
    assert resp1.json()["status"] == "imported"

    # Second import (same data)
    xml_file2 = io.BytesIO(SAMPLE_XML.encode("utf-8"))
    resp2 = await client.post(
        "/api/v1/corrispettivi/import-xml",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("corr.xml", xml_file2, "application/xml")},
    )
    assert resp2.json()["status"] == "duplicate"


# --- Test with real XML file from examples ---

@pytest.mark.asyncio
async def test_real_xml_file_from_examples(client: AsyncClient, verified_user):
    """Test with actual XML file from esempi_import/corrispettivi/."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")

    xml_path = os.path.join(
        os.path.dirname(__file__), "..", "..",
        "esempi_import", "corrispettivi", "2137404036_16877871000.xml"
    )
    if not os.path.exists(xml_path):
        pytest.skip("File esempio non trovato")

    with open(xml_path, "rb") as f:
        content = f.read()

    xml_file = io.BytesIO(content)
    resp = await client.post(
        "/api/v1/corrispettivi/import-xml",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("2137404036_16877871000.xml", xml_file, "application/xml")},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "imported"
    assert data["data"] == "2024-01-01"
    assert data["num_documenti"] == 21
    assert data["contanti"] == 373.0
    assert data["elettronico"] == 1395.0


# --- Edge cases ---

@pytest.mark.asyncio
async def test_non_xml_rejected(client: AsyncClient, verified_user):
    """Non-XML files are rejected."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")

    resp = await client.post(
        "/api/v1/corrispettivi/import-xml",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("test.pdf", io.BytesIO(b"not xml"), "application/pdf")},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_empty_corrispettivo_skipped(client: AsyncClient, verified_user):
    """Corrispettivo with zero incasso is skipped."""
    token = await get_auth_token(client, "mario.rossi@example.com", "Password1")

    empty_xml = SAMPLE_XML.replace(
        "<PagatoContanti>373.00</PagatoContanti>", "<PagatoContanti>0.00</PagatoContanti>"
    ).replace(
        "<PagatoElettronico>1395.00</PagatoElettronico>", "<PagatoElettronico>0.00</PagatoElettronico>"
    ).replace(
        "<Ammontare>1607.27</Ammontare>", "<Ammontare>0.00</Ammontare>"
    ).replace(
        "<Imposta>160.73</Imposta>", "<Imposta>0.00</Imposta>"
    )

    resp = await client.post(
        "/api/v1/corrispettivi/import-xml",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("empty.xml", io.BytesIO(empty_xml.encode()), "application/xml")},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "skipped"
