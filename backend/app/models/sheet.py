"""
AnswerSheet and AnswerSheetPage models.
"""
from sqlalchemy import BigInteger, Column, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.db import Base
from app.models.enums import sheet_status


class AnswerSheet(Base):
    __tablename__ = "answer_sheets"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    exam_id = Column(
        BigInteger, ForeignKey("exams.id", ondelete="RESTRICT"), nullable=False
    )
    student_id = Column(
        BigInteger, ForeignKey("students.id", ondelete="RESTRICT"), nullable=False
    )
    # Blind marking code shown to examiners in place of student identity
    anon_code = Column(String(20), nullable=False)
    status = Column(
        sheet_status, nullable=False, default="uploaded", server_default="uploaded"
    )
    uploaded_by = Column(
        BigInteger, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    pages = relationship(
        "AnswerSheetPage", back_populates="sheet", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("uq_sheets_exam_student", "exam_id", "student_id", unique=True),
        Index("uq_sheets_exam_anon", "exam_id", "anon_code", unique=True),
    )


class AnswerSheetPage(Base):
    __tablename__ = "answer_sheet_pages"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    answer_sheet_id = Column(
        BigInteger, ForeignKey("answer_sheets.id", ondelete="CASCADE"), nullable=False
    )
    page_number = Column(Integer, nullable=False)
    # e.g. sheets/{exam_id}/{sheet_id}/page_{n}.jpg
    storage_key = Column(String(300), nullable=False)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)

    sheet = relationship("AnswerSheet", back_populates="pages")

    __table_args__ = (
        Index(
            "uq_pages_sheet_page", "answer_sheet_id", "page_number", unique=True
        ),
    )

