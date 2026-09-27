"""
AISummary model — stored AI-written narrative summaries.
Numbers come from analytics_service; the LLM only narrates them.
"""
from sqlalchemy import BigInteger, Column, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.sql import func

from app.core.db import Base
from app.models.enums import summary_scope


class AISummary(Base):
    __tablename__ = "ai_summaries"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    exam_id = Column(
        BigInteger, ForeignKey("exams.id", ondelete="RESTRICT"), nullable=False
    )
    scope = Column(summary_scope, nullable=False)
    # Set when scope = 'examiner'
    examiner_id = Column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    content = Column(Text, nullable=False)
    # The exact statistics snapshot given to the LLM — auditable
    stats = Column(JSONB, nullable=False, server_default="{}")
    model_name = Column(String(100), nullable=False)
    created_by = Column(
        BigInteger, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_ai_summaries_exam_scope_created", "exam_id", "scope", "created_at"),
    )
