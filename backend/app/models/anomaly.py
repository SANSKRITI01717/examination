"""
Anomaly model — statistical flags for humans to review.
Never an accusation; always a prompt to look again.
"""
from sqlalchemy import BigInteger, Column, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.sql import func

from app.core.db import Base
from app.models.enums import anomaly_severity, anomaly_status, anomaly_type


class Anomaly(Base):
    __tablename__ = "anomalies"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    exam_id = Column(
        BigInteger, ForeignKey("exams.id", ondelete="RESTRICT"), nullable=False
    )
    type = Column(anomaly_type, nullable=False)
    severity = Column(anomaly_severity, nullable=False)

    # One of the following will be set depending on the anomaly type
    answer_id = Column(
        BigInteger, ForeignKey("answers.id", ondelete="CASCADE"), nullable=True
    )
    question_id = Column(
        BigInteger, ForeignKey("questions.id", ondelete="CASCADE"), nullable=True
    )
    examiner_id = Column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # e.g. the z-score for QUESTION_OUTLIER
    score = Column(Numeric(8, 3), nullable=True)
    # Human-readable evidence: the numbers used to compute the flag
    details = Column(JSONB, nullable=False, server_default="{}")
    status = Column(
        anomaly_status, nullable=False, default="open", server_default="open"
    )
    note = Column(Text, nullable=True)
    # e.g. "TOO_FAST:answer:812" — makes re-runs idempotent
    dedupe_key = Column(String(120), nullable=False)
    detected_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    resolved_by = Column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    __table_args__ = (
        Index("uq_anomalies_exam_dedupe", "exam_id", "dedupe_key", unique=True),
        Index("ix_anomalies_exam_status_severity", "exam_id", "status", "severity"),
        Index("ix_anomalies_examiner", "examiner_id"),
    )
