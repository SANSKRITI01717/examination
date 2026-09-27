"""
Anthropic Messages API client, called directly via httpx (already a dependency)
rather than pulling in the anthropic SDK — keeps the dependency list unchanged
per instruction.md §9 (anti-overengineering: don't add a library for what one
plain HTTP call can do).
"""
import time

import httpx

from app.ai.llm.base import LLMClient, LLMError, LLMResult
from app.core.config import settings

_ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
_ANTHROPIC_VERSION = "2023-06-01"
_TIMEOUT_SECONDS = 30.0
_MAX_TOKENS = 1500


class AnthropicClient(LLMClient):
    def __init__(self) -> None:
        self.api_key = settings.ANTHROPIC_API_KEY
        self.model = settings.LLM_MODEL

    def generate_json(self, system_prompt: str, user_prompt: str) -> LLMResult:
        if not self.api_key:
            raise LLMError("ANTHROPIC_API_KEY is not configured")

        started = time.monotonic()
        try:
            response = httpx.post(
                _ANTHROPIC_API_URL,
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": _ANTHROPIC_VERSION,
                    "content-type": "application/json",
                },
                json={
                    "model": self.model,
                    "max_tokens": _MAX_TOKENS,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": user_prompt}],
                },
                timeout=_TIMEOUT_SECONDS,
            )
        except httpx.HTTPError as exc:
            raise LLMError(f"Anthropic request failed: {exc}") from exc

        latency_ms = int((time.monotonic() - started) * 1000)

        if response.status_code != 200:
            raise LLMError(
                f"Anthropic API returned {response.status_code}: {response.text[:300]}"
            )

        try:
            data = response.json()
            text_parts = [
                block.get("text", "")
                for block in data.get("content", [])
                if block.get("type") == "text"
            ]
            raw_text = "\n".join(part for part in text_parts if part)
        except (ValueError, KeyError, TypeError) as exc:
            raise LLMError(f"Could not parse Anthropic response: {exc}") from exc

        if not raw_text.strip():
            raise LLMError("Anthropic response contained no text content")

        return LLMResult(raw_text=raw_text, latency_ms=latency_ms, model_name=self.model)
