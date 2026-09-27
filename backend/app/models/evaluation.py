"""
AIEvaluation and Evaluation (human) models.
AI rows are immutable (invariant 4). Human marks live in evaluations.
Both are separate tables (D-05).
"""
from sqlalchemy import (
    BigInteger,
    CHAR,
    Column,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.sql import func

from app.core.db import Base
from app.models.enums import evaluation_mode, evaluation_source, evaluation_status


class AIEvaluation(Base):
    """
    Immutable record of an AI suggestion for an answer.
    Re-runs create new rows; old rows are never updated or deleted (invariant 4).
    """
    __tablename__ = "ai_evaluations"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    answer_id = Column(
        BigInteger, ForeignKey("answers.id", ondelete="RESTRICT"), nullable=False
    )
    mode_requested = Column(evaluation_mode, nullable=False)
    mode_used = Column(evaluation_mode, nullable=False)
    model_name = Column(String(100), nullable=False)
    prompt_version = Column(String(30), nullable=False)
    # sha256(effective_text + rubric + mode + prompt_version) — used for stale detection
    input_hash = Column(CHAR(64), nullable=False)
    # Backend-computed sum of criteria; LLM total is ignored (D-04)
    suggested_marks = Column(Numeric(5, 2), nullable=False)
    max_marks = Column(Numeric(5, 2), nullable=False)
    confidence = Column(Numeric(4, 3), nullable=False)
    llm_confidence = Column(Numeric(4, 3), nullable=True)
    # [{"criterion_id","criterion","max_marks","awarded_marks","reason"}]
    criteria = Column(JSONB, nullable=False, server_default="[]")
    overall_reason = Column(Text, nullable=True)
    # [{"doc_id","chunk_index","score","snippet"}] — null for standard mode
    retrieval = Column(JSONB, nullable=True)
    # e.g. ["LOW_CONFIDENCE","LOW_OCR_CONFIDENCE","NO_REFERENCE_FOUND"]
    warnings = Column(JSONB, nullable=False, server_default="[]")
    latency_ms = Column(Integer, nullable=True)
    # null = triggered by batch job
    triggered_by = Column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_ai_evaluations_answer_created", "answer_id", "created_at"),
    )


class Evaluation(Base):
    """
    Examiner's marks for an answer. This is a human decision — never written by AI code.
    One evaluation per answer (unique constraint).
    """
    __tablename__ = "evaluations"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    answer_id = Column(
        BigInteger,
        ForeignKey("answers.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    examiner_id = Column(
        BigInteger, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    ai_evaluation_id = Column(
        BigInteger, ForeignKey("ai_evaluations.id", ondelete="SET NULL"), nullable=True
    )
    marks_awarded = Column(Numeric(5, 2), nullable=False)
    # [{"criterion_id","awarded_marks"}]
    criterion_marks = Column(JSONB, nullable=True)
    comment = Column(Text, nullable=True)
    source = Column(evaluation_source, nullable=False)
    status = Column(evaluation_status, nullable=False, default="draft", server_default="draft")
    # Timing fields for unchecked/too-fast anomaly detection
    opened_at = Column(TIMESTAMP(timezone=True), nullable=True)
    active_seconds = Column(Integer, nullable=True)
    submitted_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        Index("ix_evaluations_examiner_status", "examiner_id", "status"),
    )
