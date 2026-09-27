"""
Pydantic schemas for reference documents and RAG retrieval (D1, D2, D5).
Contract: api-spec.md §11.
"""
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ReferenceDocumentResponse(BaseModel):
    id: int
    exam_id: int
    question_id: Optional[int] = None
    title: str
    doc_type: str
    status: str
    chunk_count: int
    error: Optional[str] = None
    created_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ReferenceSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    question_id: Optional[int] = None
    top_k: int = Field(4, ge=1, le=20)


class RetrievedChunkResponse(BaseModel):
    doc_id: int
    title: str
    chunk_index: int
    score: float
    text: str


class ReferenceSearchResponse(BaseModel):
    chunks: List[RetrievedChunkResponse]
