"""
Question and Rubric API endpoints (Q3-Q4, R1-R2).
Contract: api-spec.md §5.
"""
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user, require_role
from app.models.user import User
from app.schemas.question import (
    QuestionResponse,
    QuestionUpdate,
    RubricCreate,
    RubricResponse,
)
from app.services import question_service

router = APIRouter(prefix="/questions", tags=["Questions & Rubrics"])


@router.patch("/{id}", response_model=QuestionResponse)
def update_question_endpoint(
    id: int,
    data: QuestionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Q3: Edit a question in draft status."""
    return question_service.update_question(db, id, data)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_question_endpoint(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Q4: Delete a question (draft exams only, no answers)."""
    question_service.delete_question(db, id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/{id}/rubric", response_model=RubricResponse)
def save_rubric_endpoint(
    id: int,
    data: RubricCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """R1: Create or replace a question's rubric with criteria validation."""
    return question_service.upsert_rubric(db, id, data)


@router.get("/{id}/rubric", response_model=RubricResponse)
def get_rubric_endpoint(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """R2: Read a question's rubric."""
    return question_service.get_rubric(db, id)
