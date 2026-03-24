"""LLM Adapter — multi-provider support for Anthropic (Claude) and OpenAI (GPT)."""

import logging
import os

import httpx

logger = logging.getLogger(__name__)

LLM_PROVIDERS: dict[str, dict] = {
    "anthropic": {
        "name": "Anthropic (Claude)",
        "models": [
            {"id": "claude-opus-4-6", "name": "Claude Opus 4.6", "context": 1000000, "max_output": 128000, "price_input": 5.0, "price_output": 25.0},
            {"id": "claude-sonnet-4-6", "name": "Claude Sonnet 4.6", "context": 1000000, "max_output": 64000, "price_input": 3.0, "price_output": 15.0},
            {"id": "claude-haiku-4-5-20251001", "name": "Claude Haiku 4.5", "context": 200000, "max_output": 64000, "price_input": 1.0, "price_output": 5.0},
            {"id": "claude-sonnet-4-5-20250929", "name": "Claude Sonnet 4.5", "context": 1000000, "max_output": 64000, "price_input": 3.0, "price_output": 15.0},
        ],
        "default_model": "claude-sonnet-4-6",
        "api_key_env": "ANTHROPIC_API_KEY",
        "base_url": "https://api.anthropic.com/v1/messages",
    },
    "openai": {
        "name": "OpenAI (GPT)",
        "models": [
            {"id": "gpt-5.4", "name": "GPT-5.4", "context": 1050000, "max_output": 128000, "price_input": 2.5, "price_output": 15.0},
            {"id": "gpt-5.4-mini", "name": "GPT-5.4 mini", "context": 400000, "max_output": 128000, "price_input": 0.75, "price_output": 4.5},
            {"id": "gpt-5.4-nano", "name": "GPT-5.4 nano", "context": 400000, "max_output": 128000, "price_input": 0.2, "price_output": 1.25},
            {"id": "gpt-4o", "name": "GPT-4o", "context": 128000, "max_output": 16384, "price_input": 2.5, "price_output": 10.0},
            {"id": "gpt-4o-mini", "name": "GPT-4o mini", "context": 128000, "max_output": 16384, "price_input": 0.15, "price_output": 0.6},
        ],
        "default_model": "gpt-4o-mini",
        "api_key_env": "OPENAI_API_KEY",
        "base_url": "https://api.openai.com/v1/chat/completions",
    },
}


class LLMAdapter:
    """Unified LLM adapter supporting multiple providers."""

    @staticmethod
    def get_available_providers() -> list[dict]:
        """Return list of available providers with their models."""
        result: list[dict] = []
        for provider_id, provider in LLM_PROVIDERS.items():
            api_key = os.getenv(provider["api_key_env"], "")
            result.append({
                "id": provider_id,
                "name": provider["name"],
                "configured": bool(api_key),
                "default_model": provider["default_model"],
                "models": provider["models"],
            })
        return result

    @staticmethod
    async def call(
        provider: str = "anthropic",
        model: str | None = None,
        system_prompt: str = "",
        user_message: str = "",
        max_tokens: int = 1024,
    ) -> str:
        """Call LLM and return response text."""
        provider_config = LLM_PROVIDERS.get(provider)
        if not provider_config:
            raise ValueError(f"Provider '{provider}' not supported. Available: {list(LLM_PROVIDERS.keys())}")

        if not model:
            model = provider_config["default_model"]

        # Validate model exists for this provider
        valid_model_ids = [m["id"] for m in provider_config["models"]]
        if model not in valid_model_ids:
            raise ValueError(
                f"Model '{model}' not available for provider '{provider}'. "
                f"Available: {valid_model_ids}"
            )

        api_key = os.getenv(provider_config["api_key_env"], "")
        if not api_key:
            raise ValueError(f"API key not configured for {provider} (env: {provider_config['api_key_env']})")

        if provider == "anthropic":
            return await LLMAdapter._call_anthropic(api_key, model, system_prompt, user_message, max_tokens)
        elif provider == "openai":
            return await LLMAdapter._call_openai(api_key, model, system_prompt, user_message, max_tokens)
        else:
            raise ValueError(f"Provider '{provider}' not implemented")

    @staticmethod
    async def _call_anthropic(api_key: str, model: str, system_prompt: str, user_message: str, max_tokens: int) -> str:
        """Call Anthropic Claude API."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": model,
                    "max_tokens": max_tokens,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": user_message}],
                },
            )
            resp.raise_for_status()
            data = resp.json()
            content_blocks = data.get("content", [])
            text_parts = [b["text"] for b in content_blocks if b.get("type") == "text"]
            return "\n".join(text_parts)

    @staticmethod
    async def _call_openai(api_key: str, model: str, system_prompt: str, user_message: str, max_tokens: int) -> str:
        """Call OpenAI GPT API."""
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_message})

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
