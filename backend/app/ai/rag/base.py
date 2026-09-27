"""
RAG layer interfaces per backend-plan.md §3 and ai-pipeline.md §6.
Only reference material ever passes through these — never student answers
(invariant 4 / database-schema.md §5).
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class RagError(Exception):
    """
    Raised when the embedding provider or vector store call itself fails
    (network, auth, timeout, malformed response). Callers must treat this as
    'retrieval unavailable' and fall back to standard mode — never let it
    block or crash an evaluation (ai-pipeline.md §6 step 4).
    """


@dataclass
class EmbeddingResult:
    vector: List[float]
    model_name: str


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, text: str) -> EmbeddingResult:
        """Embed a single piece of text. Raises RagError on provider failure."""


@dataclass
class VectorRecord:
    """One chunk to upsert."""
    vector_id: str
    values: List[float]
    metadata: Dict[str, Any]


@dataclass
class RetrievedChunk:
    doc_id: int
    chunk_index: int
    score: float
    text: str
    title: str = ""


class VectorStore(ABC):
    @abstractmethod
    def upsert(self, namespace: str, records: List[VectorRecord]) -> None:
        """Insert or replace vectors in a namespace. Raises RagError on failure."""

    @abstractmethod
    def query(
        self,
        namespace: str,
        vector: List[float],
        top_k: int,
        question_id_filter: Optional[List[int]] = None,
    ) -> List[RetrievedChunk]:
        """
        Return the top_k closest vectors in the namespace, optionally filtered
        to metadata.question_id in question_id_filter (per ai-pipeline.md §6:
        "filter question_id ∈ {this question, 0}"). Raises RagError on failure.
        """

    @abstractmethod
    def delete_by_doc(self, namespace: str, doc_id: int) -> None:
        """Delete every vector belonging to one reference document (D3)."""
