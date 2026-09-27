"""
Exam API endpoints (E1-E5, Q1-Q2).
Contract: api-spec.md §4, §5.
"""
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user, require_role
from app.models.user import User
from app.schemas.exam import (
    ExamCreate,
    ExamDetailResponse,
    ExamResponse,
    ExamTransitionRequest,
    ExamUpdate,
)
from app.schemas.question import QuestionCreate, QuestionResponse
from app.services import exam_service, question_service

router = APIRouter(prefix="/exams", tags=["Exams"])


@router.post("", response_model=ExamResponse, status_code=status.HTTP_201_CREATED)
def create_exam_endpoint(
    data: ExamCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """E1: Create a new exam in draft status."""
    return exam_service.create_exam(db, data, current_user.id)


@router.get("", response_model=List[ExamResponse])
def list_exams_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """E2: List exams. Admins and moderators see all; examiners see exams with assigned answers."""
    return exam_service.get_exams(db, current_user)


@router.get("/{id}", response_model=ExamDetailResponse)
def get_exam_detail_endpoint(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """E3: Get exam details with question, sheet, and answer counts."""
    exam, q_count, sheet_count, ans_count = exam_service.get_exam_detail(
        db, id, current_user
    )
    return ExamDetailResponse(
        id=exam.id,
        title=exam.title,
        course_code=exam.course_code,
        exam_date=exam.exam_date,
        status=exam.status,
        settings=exam.settings,
        created_at=exam.created_at,
        question_count=q_count,
        sheet_count=sheet_count,
        answer_count=ans_count,
    )


@router.patch("/{id}", response_model=ExamResponse)
def update_exam_endpoint(
    id: int,
    data: ExamUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """E4: Update exam details or settings."""
    return exam_service.update_exam(db, id, data)


@router.post("/{id}/transition", response_model=ExamResponse)
def transition_exam_endpoint(
    id: int,
    data: ExamTransitionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """E5: Transition exam lifecycle state (draft -> evaluation -> moderation -> completed)."""
    return exam_service.transition_exam(db, id, data.to)


@router.post("/{id}/questions", response_model=QuestionResponse, status_code=status.HTTP_201_CREATED)
def create_question_endpoint(
    id: int,
    data: QuestionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Q1: Add a question to an exam in draft status."""
    return question_service.create_question(db, id, data)


@router.get("/{id}/questions", response_model=List[QuestionResponse])
def get_questions_endpoint(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Q2: List questions with rubrics for an exam."""
    return question_service.get_questions_for_exam(db, id)
