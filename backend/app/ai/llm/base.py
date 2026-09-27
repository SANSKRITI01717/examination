"""
LLM Client interface per backend-plan.md §3.
Provider-agnostic: routers/services depend only on LLMClient, not on any SDK.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


class LLMError(Exception):
    """Raised when the provider call itself fails (timeout, 5xx, auth, network)."""


@dataclass
class LLMResult:
    raw_text: str
    latency_ms: int
    model_name: str


class LLMClient(ABC):
    @abstractmethod
    def generate_json(self, system_prompt: str, user_prompt: str) -> LLMResult:
        """
        Send a system+user prompt to the model and return its raw text response.
        The caller (validator.py) is responsible for parsing/validating the JSON.
        Must raise LLMError on any provider failure — never return a partial result.
        """
