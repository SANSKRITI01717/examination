"""
Student service — business logic for candidate records (S1, S2).
"""
from typing import List, Optional, Tuple
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.student import Student
from app.schemas.student import StudentCreate


def create_student(db: Session, data: StudentCreate) -> Student:
    existing = db.scalar(
        select(Student).where(Student.roll_number == data.roll_number)
    )
    if existing:
        raise AppError(
            code="ROLL_EXISTS",
            message=f"Student with roll number '{data.roll_number}' already exists",
            status_code=409,
        )

    student = Student(
        roll_number=data.roll_number,
        full_name=data.full_name,
        department=data.department,
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


def get_students(
    db: Session,
    q: Optional[str] = None,
    page: int = 1,
    page_size: int = 25,
) -> Tuple[List[Student], int]:
    stmt = select(Student)
    if q:
        query_pattern = f"%{q}%"
        stmt = stmt.where(
            or_(
                Student.roll_number.ilike(query_pattern),
                Student.full_name.ilike(query_pattern),
            )
        )

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = list(
        db.scalars(
            stmt.order_by(Student.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return items, total


def get_student_by_id(db: Session, student_id: int) -> Student:
    student = db.get(Student, student_id)
    if not student:
        raise AppError(
            code="NOT_FOUND",
            message=f"Student with id {student_id} not found",
            status_code=404,
        )
    return student
