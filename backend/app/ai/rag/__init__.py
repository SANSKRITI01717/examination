"""
RAG package exports and factories. Mirrors app.ai.ocr / app.ai.llm's pattern.
"""
from app.ai.rag.base import (
    EmbeddingProvider,
    EmbeddingResult,
    RagError,
    RetrievedChunk,
    VectorRecord,
    VectorStore,
)
from app.ai.rag.embeddings import OpenAIEmbeddingProvider
from app.ai.rag.pinecone_store import PineconeStore

_embedding_instance: EmbeddingProvider = None
_vector_store_instance: VectorStore = None


def get_embedding_provider() -> EmbeddingProvider:
    global _embedding_instance
    if _embedding_instance is None:
        _embedding_instance = OpenAIEmbeddingProvider()
    return _embedding_instance


def get_vector_store() -> VectorStore:
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = PineconeStore()
    return _vector_store_instance


__all__ = [
    "EmbeddingProvider",
    "EmbeddingResult",
    "VectorStore",
    "VectorRecord",
    "RetrievedChunk",
    "RagError",
    "get_embedding_provider",
    "get_vector_store",
]
