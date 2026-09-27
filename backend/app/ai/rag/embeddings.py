"""
OpenAI embeddings, called directly via httpx (already a dependency) rather than
adding the openai SDK — same rationale as app/ai/llm/anthropic_client.py.

NOT verified against a live API in this sandbox (no internet access when this
was written). The request/response shape matches OpenAI's documented
Embeddings endpoint as of this codebase's training data, but has not been
exercised against the real service. If it 4xx/5xx's in practice, RagError is
raised and callers fall back to standard mode (ai-pipeline.md §6 step 4) —
it fails safe, it just won't produce real retrieval until verified.
"""
import httpx

from app.ai.rag.base import EmbeddingProvider, EmbeddingResult, RagError
from app.core.config import settings

_OPENAI_EMBEDDINGS_URL = "https://api.openai.com/v1/embeddings"
_TIMEOUT_SECONDS = 20.0


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self) -> None:
        self.api_key = settings.OPENAI_API_KEY
        self.model = settings.EMBEDDING_MODEL

    def embed(self, text: str) -> EmbeddingResult:
        if not self.api_key:
            raise RagError("OPENAI_API_KEY is not configured")

        try:
            response = httpx.post(
                _OPENAI_EMBEDDINGS_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={"model": self.model, "input": text},
                timeout=_TIMEOUT_SECONDS,
            )
        except httpx.HTTPError as exc:
            raise RagError(f"Embedding request failed: {exc}") from exc

        if response.status_code != 200:
            raise RagError(
                f"Embedding API returned {response.status_code}: {response.text[:300]}"
            )

        try:
            data = response.json()
            vector = data["data"][0]["embedding"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise RagError(f"Could not parse embedding response: {exc}") from exc

        return EmbeddingResult(vector=vector, model_name=self.model)
