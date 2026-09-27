"""
Hugging Face LLM client, called directly via httpx (already a dependency)
against HF's OpenAI-compatible chat-completions router — no SDK added,
same pattern as anthropic_client.py.

Model choice: this defaults to "meta-llama/Llama-3.1-8B-Instruct", a widely
available free-tier-friendly instruction model on HF's Inference Providers
router as of this writing. HF's list of free-tier-available models changes
over time — if this model isn't available when you deploy, change LLM_MODEL
in your .env (no code change needed) to any other chat-capable model listed
at https://huggingface.co/models?inference_provider=all&sort=trending
"""
import time

import httpx

from app.ai.llm.base import LLMClient, LLMError, LLMResult
from app.core.config import settings

_HF_ROUTER_URL = "https://router.huggingface.co/v1/chat/completions"
_TIMEOUT_SECONDS = 60.0
_MAX_TOKENS = 1500


class HuggingFaceClient(LLMClient):
    def __init__(self) -> None:
        self.api_key = settings.HF_API_KEY
        self.model = settings.LLM_MODEL

    def generate_json(self, system_prompt: str, user_prompt: str) -> LLMResult:
        if not self.api_key:
            raise LLMError("HF_API_KEY is not configured")

        started = time.monotonic()
        try:
            response = httpx.post(
                _HF_ROUTER_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "max_tokens": _MAX_TOKENS,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                },
                timeout=_TIMEOUT_SECONDS,
            )
        except httpx.HTTPError as exc:
            raise LLMError(f"Hugging Face request failed: {exc}") from exc

        latency_ms = int((time.monotonic() - started) * 1000)

        if response.status_code != 200:
            raise LLMError(
                f"Hugging Face API returned {response.status_code}: {response.text[:300]}"
            )

        try:
            data = response.json()
            raw_text = data["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"Could not parse Hugging Face response: {exc}") from exc

        if not raw_text or not raw_text.strip():
            raise LLMError("Hugging Face response contained no text content")

        return LLMResult(raw_text=raw_text, latency_ms=latency_ms, model_name=self.model)
