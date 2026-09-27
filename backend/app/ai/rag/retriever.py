"""
Retrieval for reference-grounded evaluation (ai-pipeline.md §6).
Query text is built from the question + rubric only — deliberately never
the student's answer, so a wrong or off-topic answer can't steer retrieval.
"""
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.ai.rag import get_embedding_provider, get_vector_store
from app.ai.rag.base import RetrievedChunk
from app.models.reference import ReferenceDocument


def build_query_text(question_text: str, rubric_criteria: List[Dict[str, Any]]) -> str:
    parts = [question_text.strip()]
    for c in rubric_criteria:
        name = c.get("name", "")
        desc = c.get("description", "") or ""
        parts.append(f"{name}: {desc}".strip(": "))
    return "\n".join(p for p in parts if p)


def retrieve_chunks(
    db: Session,
    exam_id: int,
    question_id: int,
    rubric_criteria: List[Dict[str, Any]],
    question_text: str,
    top_k: int,
    min_score: float,
) -> List[RetrievedChunk]:
    """
    Returns chunks above min_score, newest-embedding-provider first, with
    `title` resolved from PostgreSQL (the source of truth for document
    metadata — Pinecone only stores doc_id, not titles, per database-schema.md §5).
    May raise RagError — callers must catch it and fall back to standard mode.
    """
    query_text = build_query_text(question_text, rubric_criteria)

    embedding = get_embedding_provider().embed(query_text)
    namespace = f"exam-{exam_id}"

    raw_chunks = get_vector_store().query(
        namespace=namespace,
        vector=embedding.vector,
        top_k=top_k,
        question_id_filter=[question_id, 0],
    )

    filtered = [c for c in raw_chunks if c.score >= min_score]
    if not filtered:
        return []

    doc_ids = {c.doc_id for c in filtered}
    docs = {
        d.id: d.title
        for d in db.query(ReferenceDocument).filter(ReferenceDocument.id.in_(doc_ids)).all()
    }
    for chunk in filtered:
        chunk.title = docs.get(chunk.doc_id, chunk.title or "reference")

    return filtered
