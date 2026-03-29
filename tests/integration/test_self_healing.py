"""Integration tests for Self-Healing Import (US-73, US-74)."""

import pytest
from unittest.mock import AsyncMock

from api.modules.self_healing.service import SelfHealingService


# ═══════════════════════════════════════════════
# US-73: Retry con prompt adattato (Livello 1)
# ═══════════════════════════════════════════════

@pytest.mark.asyncio
async def test_ac_73_1_first_attempt_success(db_session, tenant):
    """AC-73.1: Se il primo tentativo funziona, nessun retry."""
    svc = SelfHealingService(db_session)

    extractor = AsyncMock(return_value={"mese": 3, "anno": 2025, "totale_dare": 100, "totale_avere": 100})
    validator = lambda d: d is not None and d.get("totale_dare") == d.get("totale_avere")

    result = await svc.extract_with_retry(
        tenant_id=tenant.id,
        source_type="paghe",
        raw_text="Riepilogo paghe test...",
        base_prompt="Estrai i dati...",
        extractor=extractor,
        validator=validator,
    )

    assert result["data"] is not None
    assert result["retries"] == 0
    assert result["adapted"] is False
    assert extractor.call_count == 1


@pytest.mark.asyncio
async def test_ac_73_2_retry_succeeds_on_second_attempt(db_session, tenant):
    """AC-73.2: Primo tentativo fallisce, retry con prompt adattato funziona."""
    svc = SelfHealingService(db_session)

    call_count = 0

    async def flaky_extractor(text, prompt):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ValueError("JSON non valido: missing field")
        return {"mese": 3, "anno": 2025, "totale_dare": 100, "totale_avere": 100}

    validator = lambda d: d is not None and d.get("totale_dare") == d.get("totale_avere")

    result = await svc.extract_with_retry(
        tenant_id=tenant.id,
        source_type="paghe",
        raw_text="Riepilogo paghe test...",
        base_prompt="Estrai i dati...",
        extractor=flaky_extractor,
        validator=validator,
    )

    assert result["data"] is not None
    assert result["retries"] == 1
    assert result["adapted"] is True
    assert call_count == 2


@pytest.mark.asyncio
async def test_ac_73_3_all_retries_fail(db_session, tenant):
    """AC-73.3: Tutti i tentativi falliscono → ritorna errore."""
    svc = SelfHealingService(db_session)

    extractor = AsyncMock(side_effect=ValueError("sempre errore"))
    validator = lambda d: d is not None

    result = await svc.extract_with_retry(
        tenant_id=tenant.id,
        source_type="banca",
        raw_text="Estratto conto...",
        base_prompt="Estrai movimenti...",
        extractor=extractor,
        validator=validator,
        max_retries=2,
    )

    assert result["data"] is None
    assert result["retries"] == 2
    assert "error" in result


@pytest.mark.asyncio
async def test_ac_73_4_invalid_data_triggers_retry(db_session, tenant):
    """AC-73.4: Dati estratti ma non validi → retry."""
    svc = SelfHealingService(db_session)

    call_count = 0

    async def extractor(text, prompt):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return {"totale_dare": 100, "totale_avere": 50}  # non bilanciato
        return {"totale_dare": 100, "totale_avere": 100}  # bilanciato

    validator = lambda d: d is not None and abs(d.get("totale_dare", 0) - d.get("totale_avere", 0)) < 0.1

    result = await svc.extract_with_retry(
        tenant_id=tenant.id,
        source_type="paghe",
        raw_text="test",
        base_prompt="Estrai...",
        extractor=extractor,
        validator=validator,
    )

    assert result["data"]["totale_dare"] == result["data"]["totale_avere"]
    assert result["retries"] == 1


# ═══════════════════════════════════════════════
# US-74: Meta-prompt per-tenant (Livello 2)
# ═══════════════════════════════════════════════

@pytest.mark.asyncio
async def test_ac_74_1_successful_prompt_saved(db_session, tenant):
    """AC-74.1: Prompt adattato con successo → salvato in DB per riuso."""
    svc = SelfHealingService(db_session)

    call_count = 0

    async def extractor(text, prompt):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ValueError("formato non riconosciuto")
        return {"ok": True}

    result = await svc.extract_with_retry(
        tenant_id=tenant.id,
        source_type="banca",
        raw_text="test...",
        base_prompt="Estrai...",
        extractor=extractor,
        validator=lambda d: d is not None and d.get("ok"),
    )

    assert result["adapted"] is True

    # Verify prompt was saved in DB
    from sqlalchemy import select
    from api.db.models import ImportPromptTemplate
    saved = await db_session.execute(
        select(ImportPromptTemplate).where(
            ImportPromptTemplate.tenant_id == tenant.id,
            ImportPromptTemplate.source_type == "banca",
        )
    )
    template = saved.scalar_one_or_none()
    assert template is not None
    assert template.success_count >= 1


@pytest.mark.asyncio
async def test_ac_74_2_saved_prompt_reused(db_session, tenant):
    """AC-74.2: Prompt salvato viene riutilizzato al prossimo import."""
    svc = SelfHealingService(db_session)

    # Save a prompt first
    from api.db.models import ImportPromptTemplate
    template = ImportPromptTemplate(
        tenant_id=tenant.id,
        source_type="paghe",
        format_key="auto",
        prompt_text="Prompt ottimizzato per questo tenant",
        success_count=5,
    )
    db_session.add(template)
    await db_session.flush()

    # Now extract — should use saved prompt
    prompts_received = []

    async def capture_extractor(text, prompt):
        prompts_received.append(prompt)
        return {"ok": True}

    result = await svc.extract_with_retry(
        tenant_id=tenant.id,
        source_type="paghe",
        raw_text="test",
        base_prompt="Prompt default",
        extractor=capture_extractor,
        validator=lambda d: d is not None,
    )

    assert result["prompt_used"] == "saved"
    assert prompts_received[0] == "Prompt ottimizzato per questo tenant"


@pytest.mark.asyncio
async def test_ac_74_3_prompt_adaptation_adds_rules(db_session, tenant):
    """AC-74.3: L'adattamento del prompt aggiunge regole basate sull'errore."""
    svc = SelfHealingService(db_session)

    # Test JSON error → adds JSON rule
    adapted = svc._adapt_prompt("Base prompt", "Invalid JSON response", "text")
    assert "JSON valido" in adapted

    # Test date error → adds date rule
    adapted = svc._adapt_prompt("Base prompt", "Invalid date format", "text")
    assert "YYYY-MM-DD" in adapted

    # Test bilancio error → adds balance rule
    adapted = svc._adapt_prompt("Base prompt", "Sbilanciamento dare/avere", "text")
    assert "dare DEVE essere uguale" in adapted


@pytest.mark.asyncio
async def test_ac_74_4_failure_count_tracked(db_session, tenant):
    """AC-74.4: I fallimenti vengono tracciati nel template."""
    svc = SelfHealingService(db_session)

    # Pre-save a template
    from api.db.models import ImportPromptTemplate
    template = ImportPromptTemplate(
        tenant_id=tenant.id,
        source_type="f24",
        format_key="auto",
        prompt_text="Prompt test",
        success_count=3,
        failure_count=0,
    )
    db_session.add(template)
    await db_session.flush()

    # Force failure
    extractor = AsyncMock(side_effect=ValueError("sempre errore"))
    await svc.extract_with_retry(
        tenant_id=tenant.id,
        source_type="f24",
        raw_text="test",
        base_prompt="Prompt test",
        extractor=extractor,
        validator=lambda d: d is not None,
        max_retries=1,
    )

    # Check failure count increased
    await db_session.refresh(template)
    assert template.failure_count >= 1
