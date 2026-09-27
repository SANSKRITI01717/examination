"""
Result model — per-student total for an exam, computed from answers.final_marks.
"""
from sqlalchemy import BigInteger, Column, ForeignKey, Index, Numeric
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.sql import func

from app.core.db import Base
from app.models.enums import result_status


class Result(Base):
    __tablename__ = "results"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    exam_id = Column(
        BigInteger, ForeignKey("exams.id", ondelete="RESTRICT"), nullable=False
    )
    student_id = Column(
        BigInteger, ForeignKey("students.id", ondelete="RESTRICT"), nullable=False
    )
    total_marks = Column(Numeric(6, 2), nullable=False)
    max_marks = Column(Numeric(6, 2), nullable=False)
    percentage = Column(Numeric(5, 2), nullable=False)
    status = Column(
        result_status, nullable=False, default="draft", server_default="draft"
    )
    computed_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    published_at = Column(TIMESTAMP(timezone=True), nullable=True)

    __table_args__ = (
        Index("uq_results_exam_student", "exam_id", "student_id", unique=True),
    )
