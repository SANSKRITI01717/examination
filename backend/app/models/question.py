"""
Question and Rubric models.
One rubric per question (1:1). Criteria stored as JSONB (D-03).
"""
from sqlalchemy import BigInteger, Column, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.db import Base
from app.models.enums import evaluation_mode


class Question(Base):
    __tablename__ = "questions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    exam_id = Column(
        BigInteger, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False
    )
    question_number = Column(String(10), nullable=False)
    text = Column(Text, nullable=False)
    max_marks = Column(Numeric(5, 2), nullable=False)
    evaluation_mode = Column(
        evaluation_mode,
        nullable=False,
        default="standard",
        server_default="standard",
    )
    display_order = Column(Integer, nullable=False, default=0)

    rubric = relationship("Rubric", uselist=False, back_populates="question", cascade="all, delete-orphan")

    __table_args__ = (
        Index("uq_questions_exam_number", "exam_id", "question_number", unique=True),
    )


class Rubric(Base):
    __tablename__ = "rubrics"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    question_id = Column(
        BigInteger,
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    # [{"id": "c1", "name": "...", "max_marks": 2, "description": "..."}]
    criteria = Column(JSONB, nullable=False, server_default="[]")
    guidance = Column(Text, nullable=True)
    updated_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    question = relationship("Question", back_populates="rubric")

