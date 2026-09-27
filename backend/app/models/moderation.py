"""
Moderation model — moderator decisions. History is kept; the latest row wins.
"""
from sqlalchemy import BigInteger, Column, ForeignKey, Index, Numeric, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.sql import func

from app.core.db import Base
from app.models.enums import moderation_decision


class Moderation(Base):
    __tablename__ = "moderations"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    answer_id = Column(
        BigInteger, ForeignKey("answers.id", ondelete="RESTRICT"), nullable=False
    )
    evaluation_id = Column(
        BigInteger, ForeignKey("evaluations.id", ondelete="RESTRICT"), nullable=False
    )
    moderator_id = Column(
        BigInteger, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    original_marks = Column(Numeric(5, 2), nullable=False)
    moderated_marks = Column(Numeric(5, 2), nullable=False)
    decision = Column(moderation_decision, nullable=False)
    # Required when decision = 'overridden'
    reason = Column(Text, nullable=True)
    created_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_moderations_answer_created", "answer_id", "created_at"),
    )
