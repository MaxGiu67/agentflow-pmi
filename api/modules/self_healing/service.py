"""Self-Healing Import Service (US-73, US-74).

Livello 1: Retry con prompt adattato all'errore specifico.
Livello 2: Meta-prompt che migliora il prompt e lo salva per riuso.

NON genera codice. Migliora i prompt LLM. Il sistema impara
dal formato del commercialista di ogni tenant.
"""

import json
import logging
import os
import uuid
from typing import Any, Callable, Awaitable

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import ImportPromptTemplate

logger = logging.getLogger(__name__)

# Meta-prompt: chiede al LLM di migliorare un prompt che ha fallito
META_PROMPT = """Un prompt LLM per estrarre dati da un PDF ha fallito.

PROMPT ORIGINALE:
---
{original_prompt}
---

ERRORE RICEVUTO:
---
{error}
---

TESTO PDF (estratto):
---
{pdf_text}
---

OUTPUT ERRATO DEL LLM (se disponibile):
---
{bad_output}
---

Riscrivi il prompt in modo che funzioni meglio per questo tipo di documento.
Il prompt deve:
1. Essere piu specifico sul formato trovato nel testo
2. Gestire il caso che ha causato l'errore
3. Mantenere lo stesso formato di output JSON
4. Essere generico abbastanza da funzionare con documenti simili

Restituisci SOLO il nuovo prompt, senza spiegazioni."""


class SelfHealingService:
    """Self-healing import with prompt adaptation and meta-learning."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Livello 1: Retry con prompt adattato ──

    async def extract_with_retry(
        self,
        tenant_id: uuid.UUID,
        source_type: str,
        raw_text: str,
        base_prompt: str,
        extractor: Callable[[str, str], Awaitable[Any]],
        validator: Callable[[Any], bool],
        max_retries: int = 2,
    ) -> dict:
        """Extract data with automatic retry and prompt adaptation.

        Args:
            tenant_id: Tenant ID for per-tenant prompt storage
            source_type: Type of import (banca, paghe, f24, bilancio)
            raw_text: Raw text extracted from PDF
            base_prompt: The default prompt template
            extractor: Async function(text, prompt) -> extracted data
            validator: Function(data) -> bool, checks if extraction is valid
            max_retries: Max number of retries with adapted prompts

        Returns:
            dict with keys: data, prompt_used, retries, adapted, source_type
        """
        # First, check for a saved optimized prompt for this tenant+source
        saved_prompt = await self._get_best_prompt(tenant_id, source_type)
        prompt_to_use = saved_prompt or base_prompt

        last_error = ""

        # Attempt 1: Use best available prompt
        try:
            data = await extractor(raw_text, prompt_to_use)
            if validator(data):
                await self._record_success(tenant_id, source_type, prompt_to_use)
                return {
                    "data": data,
                    "prompt_used": "saved" if saved_prompt else "default",
                    "retries": 0,
                    "adapted": False,
                    "source_type": source_type,
                }
            else:
                last_error = "Dati estratti non validi (validator ha rifiutato)"
        except Exception as e:
            logger.warning("Attempt 1 failed for %s: %s", source_type, e)
            last_error = str(e)
            data = None

        # Attempt 2+: Retry with adapted prompt
        for retry in range(max_retries):
            adapted_prompt = self._adapt_prompt(base_prompt, last_error, raw_text)

            try:
                data = await extractor(raw_text, adapted_prompt)
                if validator(data):
                    # Success! Save the adapted prompt for future use
                    await self._save_prompt(tenant_id, source_type, adapted_prompt)
                    return {
                        "data": data,
                        "prompt_used": "adapted",
                        "retries": retry + 1,
                        "adapted": True,
                        "source_type": source_type,
                    }
            except Exception as e:
                logger.warning("Retry %d failed for %s: %s", retry + 1, source_type, e)
                last_error = str(e)

        # All retries failed
        await self._record_failure(tenant_id, source_type, prompt_to_use)
        return {
            "data": None,
            "prompt_used": "failed",
            "retries": max_retries,
            "adapted": False,
            "error": last_error,
            "source_type": source_type,
        }

    # ── Livello 2: Meta-prompt per migliorare il prompt ──

    async def improve_prompt(
        self,
        tenant_id: uuid.UUID,
        source_type: str,
        original_prompt: str,
        error: str,
        pdf_text: str,
        bad_output: str = "",
    ) -> str:
        """Use meta-prompt to generate an improved extraction prompt.

        Calls LLM to analyze why the original prompt failed and produce
        a better version. The improved prompt is saved for future use.
        """
        meta = META_PROMPT.replace("{original_prompt}", original_prompt[:3000])
        meta = meta.replace("{error}", error[:1000])
        meta = meta.replace("{pdf_text}", pdf_text[:5000])
        meta = meta.replace("{bad_output}", bad_output[:2000])

        # Call LLM for meta-analysis
        improved_prompt = await self._call_llm_for_text(meta)

        if improved_prompt and len(improved_prompt) > 100:
            await self._save_prompt(tenant_id, source_type, improved_prompt, format_key="improved")
            logger.info("Improved prompt saved for %s tenant=%s", source_type, tenant_id)
            return improved_prompt

        return original_prompt  # fallback to original

    # ── Helpers ──

    def _adapt_prompt(self, base_prompt: str, error: str, text: str) -> str:
        """Quick prompt adaptation based on error message (Livello 1)."""
        additions = []

        if "JSON" in error or "json" in error:
            additions.append("IMPORTANTE: Restituisci SOLO JSON valido, senza commenti o testo aggiuntivo.")
        if "date" in error.lower() or "data" in error.lower():
            additions.append("ATTENZIONE: Le date devono essere in formato YYYY-MM-DD. Se la data e' in formato DD/MM/YYYY o DD.MM.YYYY, convertila.")
        if "KeyError" in error or "campo" in error.lower():
            additions.append("ATTENZIONE: Assicurati che TUTTI i campi richiesti siano presenti nel JSON, anche se con valore 0 o stringa vuota.")
        if "encoding" in error.lower() or "decode" in error.lower():
            additions.append("NOTA: Il testo potrebbe contenere caratteri speciali italiani (accenti, simboli). Gestiscili correttamente.")
        if "bilancio" in error.lower() or "dare" in error.lower() or "avere" in error.lower():
            additions.append("REGOLA: totale_dare DEVE essere uguale a totale_avere (partita doppia). Se non quadra, aggiungi una riga di arrotondamento.")

        if not additions:
            additions.append(f"NOTA: Il tentativo precedente ha dato errore: {error[:200]}. Adatta l'estrazione di conseguenza.")

        adapted = base_prompt + "\n\n" + "\n".join(additions)
        return adapted

    async def _get_best_prompt(self, tenant_id: uuid.UUID, source_type: str) -> str | None:
        """Get the best saved prompt for this tenant and source type."""
        result = await self.db.execute(
            select(ImportPromptTemplate)
            .where(
                ImportPromptTemplate.tenant_id == tenant_id,
                ImportPromptTemplate.source_type == source_type,
                ImportPromptTemplate.success_count > 0,
            )
            .order_by(ImportPromptTemplate.success_count.desc())
            .limit(1)
        )
        template = result.scalar_one_or_none()
        return template.prompt_text if template else None

    async def _save_prompt(
        self, tenant_id: uuid.UUID, source_type: str, prompt: str, format_key: str = "auto"
    ) -> None:
        """Save an optimized prompt for future reuse."""
        # Check if we already have one for this tenant+source
        existing = await self.db.execute(
            select(ImportPromptTemplate).where(
                ImportPromptTemplate.tenant_id == tenant_id,
                ImportPromptTemplate.source_type == source_type,
                ImportPromptTemplate.format_key == format_key,
            )
        )
        template = existing.scalar_one_or_none()

        if template:
            template.prompt_text = prompt
            template.success_count += 1
        else:
            template = ImportPromptTemplate(
                tenant_id=tenant_id,
                source_type=source_type,
                format_key=format_key,
                prompt_text=prompt,
                success_count=1,
            )
            self.db.add(template)

        await self.db.flush()

    async def _record_success(self, tenant_id: uuid.UUID, source_type: str, prompt: str) -> None:
        """Record a successful extraction (increment counter)."""
        existing = await self.db.execute(
            select(ImportPromptTemplate).where(
                ImportPromptTemplate.tenant_id == tenant_id,
                ImportPromptTemplate.source_type == source_type,
            ).order_by(ImportPromptTemplate.success_count.desc()).limit(1)
        )
        template = existing.scalar_one_or_none()
        if template:
            template.success_count += 1
            await self.db.flush()

    async def _record_failure(self, tenant_id: uuid.UUID, source_type: str, prompt: str) -> None:
        """Record a failed extraction."""
        existing = await self.db.execute(
            select(ImportPromptTemplate).where(
                ImportPromptTemplate.tenant_id == tenant_id,
                ImportPromptTemplate.source_type == source_type,
            ).order_by(ImportPromptTemplate.success_count.desc()).limit(1)
        )
        template = existing.scalar_one_or_none()
        if template:
            template.failure_count += 1
            await self.db.flush()

    async def _call_llm_for_text(self, prompt: str) -> str | None:
        """Call LLM and return raw text response."""
        import httpx

        anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
        openai_key = os.environ.get("OPENAI_API_KEY", "")

        if anthropic_key:
            try:
                async with httpx.AsyncClient(timeout=60) as client:
                    resp = await client.post(
                        "https://api.anthropic.com/v1/messages",
                        headers={
                            "x-api-key": anthropic_key,
                            "anthropic-version": "2023-06-01",
                            "content-type": "application/json",
                        },
                        json={
                            "model": "claude-haiku-4-5-20251001",
                            "max_tokens": 4096,
                            "messages": [{"role": "user", "content": prompt}],
                        },
                    )
                    resp.raise_for_status()
                    return resp.json()["content"][0]["text"]
            except Exception as e:
                logger.warning("Anthropic meta-prompt error: %s", e)

        if openai_key:
            try:
                async with httpx.AsyncClient(timeout=60) as client:
                    resp = await client.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers={"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"},
                        json={
                            "model": "gpt-4o-mini",
                            "messages": [{"role": "user", "content": prompt}],
                            "max_completion_tokens": 4096,
                        },
                    )
                    resp.raise_for_status()
                    return resp.json()["choices"][0]["message"]["content"]
            except Exception as e:
                logger.warning("OpenAI meta-prompt error: %s", e)

        return None
