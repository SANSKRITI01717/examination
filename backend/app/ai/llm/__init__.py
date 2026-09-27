"""
LLM package exports and factory. Mirrors app.ai.ocr's provider-factory pattern.
"""
from app.ai.llm.base import LLMClient, LLMError, LLMResult
from app.ai.llm.anthropic_client import AnthropicClient

_llm_instance: LLMClient = None


def get_llm_client() -> LLMClient:
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = AnthropicClient()
    return _llm_instance


__all__ = ["LLMClient", "LLMError", "LLMResult", "get_llm_client"]
