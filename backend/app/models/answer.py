"""
Answer model — the central working row for one student's response to one question.
Holds OCR state, AI state, and marking state.
final_marks is written ONLY by MarkingService or ModerationService (invariant 5).
"""
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.db import Base
from app.models.enums import (
    ai_status,
    final_source,
    marking_status,
    ocr_status,
)


class Answer(Base):
    __tablename__ = "answers"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Denormalized for fast filtering and analytics (per schema)
    exam_id = Column(
        BigInteger, ForeignKey("exams.id", ondelete="RESTRICT"), nullable=False
    )
    answer_sheet_id = Column(
        BigInteger, ForeignKey("answer_sheets.id", ondelete="RESTRICT"), nullable=False
    )
    question_id = Column(
        BigInteger, ForeignKey("questions.id", ondelete="RESTRICT"), nullable=False
    )

    question = relationship("Question")
    sheet = relationship("AnswerSheet")

    # Page range on the sheet for this answer
    page_start = Column(Integer, nullable=True)
    page_end = Column(Integer, nullable=True)
    is_attempted = Column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    # --- OCR state ---
    ocr_status = Column(
        ocr_status, nullable=False, default="pending", server_default="pending"
    )
    ocr_text = Column(Text, nullable=True)
    ocr_confidence = Column(Numeric(4, 3), nullable=True)
    ocr_review_required = Column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    ocr_verified = Column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    verified_text = Column(Text, nullable=True)
    ocr_meta = Column(JSONB, nullable=True)

    # --- AI evaluation state ---
    ai_status = Column(
        ai_status,
        nullable=False,
        default="not_requested",
        server_default="not_requested",
    )
    ai_error = Column(Text, nullable=True)

    # --- Assignment ---
    assigned_examiner_id = Column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # --- Marking state ---
    marking_status = Column(
        marking_status, nullable=False, default="pending", server_default="pending"
    )
    # Written ONLY by MarkingService (examiner submit) or ModerationService (invariant 5)
    final_marks = Column(Numeric(5, 2), nullable=True)
    final_source = Column(final_source, nullable=True)

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
        Index("uq_answers_sheet_question", "answer_sheet_id", "question_id", unique=True),
        Index(
            "ix_answers_exam_examiner_status",
            "exam_id",
            "assigned_examiner_id",
            "marking_status",
        ),
        Index("ix_answers_exam_question", "exam_id", "question_id"),
        Index("ix_answers_exam_ocr_status", "exam_id", "ocr_status"),
        Index("ix_answers_exam_ai_status", "exam_id", "ai_status"),
    )
