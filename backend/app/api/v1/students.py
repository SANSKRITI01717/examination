"""
Student API endpoints (S1, S2).
Admin only per api-spec.md §6 and D-07.
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_role
from app.models.user import User
from app.schemas.student import StudentCreate, StudentListResponse, StudentResponse
from app.services import student_service

router = APIRouter(prefix="/students", tags=["Students"])


@router.post("", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
def create_student_endpoint(
    data: StudentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """S1: Add a new candidate."""
    return student_service.create_student(db, data)


@router.get("", response_model=StudentListResponse)
def search_students_endpoint(
    q: Optional[str] = Query(None, description="Search term for roll number or full name"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """S2: Search candidates (paginated)."""
    items, total = student_service.get_students(db, q=q, page=page, page_size=page_size)
    return StudentListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )
