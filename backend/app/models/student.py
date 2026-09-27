"""
Student model — candidates, visible to admins only (D-07).
"""
from sqlalchemy import BigInteger, Column, Index, String
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.sql import func

from app.core.db import Base


class Student(Base):
    __tablename__ = "students"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    roll_number = Column(String(50), nullable=False, unique=True)
    full_name = Column(String(150), nullable=False)
    department = Column(String(100), nullable=True)
    created_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (Index("ix_students_roll_number", "roll_number", unique=True),)
