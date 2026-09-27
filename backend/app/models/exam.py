"""
Exam model — one examination and its configuration.
"""
from sqlalchemy import BigInteger, Column, Date, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.sql import func

from app.core.db import Base
from app.models.enums import exam_status

# Default exam settings as documented in database-schema.md §4 exams.settings
_DEFAULT_EXAM_SETTINGS = {
    "ocr_low_conf_threshold": 0.80,
    "ai_low_conf_threshold": 0.70,
    "ai_disagreement_ratio": 0.30,
    "too_fast_seconds": 10,
    "z_threshold": 2.5,
    "min_sample_size": 10,
    "retrieval_top_k": 4,
    "retrieval_min_score": 0.50,
}


class Exam(Base):
    __tablename__ = "exams"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    course_code = Column(String(50), nullable=False)
    exam_date = Column(Date, nullable=True)
    status = Column(
        exam_status, nullable=False, default="draft", server_default="draft"
    )
    settings = Column(JSONB, nullable=False, server_default="{}")
    created_by = Column(
        BigInteger, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (Index("ix_exams_status", "status"),)
