"""
ReferenceDocument model — registry of files whose chunks live in Pinecone.
PostgreSQL is the source of truth; Pinecone holds the vectors only.
Student answers NEVER go into Pinecone (invariant 11).
"""
from sqlalchemy import BigInteger, Column, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.sql import func

from app.core.db import Base
from app.models.enums import doc_status, doc_type


class ReferenceDocument(Base):
    __tablename__ = "reference_documents"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    exam_id = Column(
        BigInteger, ForeignKey("exams.id", ondelete="RESTRICT"), nullable=False
    )
    # null = applies to the whole exam; non-null = applies to a specific question
    question_id = Column(
        BigInteger, ForeignKey("questions.id", ondelete="CASCADE"), nullable=True
    )
    title = Column(String(200), nullable=False)
    doc_type = Column(doc_type, nullable=False)
    storage_key = Column(String(300), nullable=False)
    mime_type = Column(String(100), nullable=False)
    status = Column(
        doc_status, nullable=False, default="uploaded", server_default="uploaded"
    )
    chunk_count = Column(Integer, nullable=False, default=0, server_default="0")
    # "exam-{exam_id}" — one namespace per exam (D-12)
    pinecone_namespace = Column(String(50), nullable=True)
    error = Column(Text, nullable=True)
    uploaded_by = Column(
        BigInteger, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_ref_docs_exam_status", "exam_id", "status"),
        Index("ix_ref_docs_question", "question_id"),
    )
