from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_role
from app.models.user import User
from app.schemas.analytics import AnalyticsOverview, ExaminerStats, QuestionStats, ExaminerProgress
from app.services import analytics_service

router = APIRouter()

@router.get("/exams/{id}/analytics/overview", response_model=AnalyticsOverview)
def get_analytics_overview(
    id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "moderator")),
):
    """AL1: Progress counters and completion %"""
    return analytics_service.get_overview(db, id)

@router.get("/exams/{id}/analytics/examiners", response_model=List[ExaminerStats])
def get_analytics_examiners(
    id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "moderator")),
):
    """AL2: Per-examiner statistics"""
    return analytics_service.get_examiner_stats(db, id)

@router.get("/exams/{id}/analytics/questions", response_model=List[QuestionStats])
def get_analytics_questions(
    id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "moderator")),
):
    """AL3: Per-question statistics"""
    return analytics_service.get_question_stats(db, id)

@router.get("/exams/{id}/analytics/my-progress", response_model=ExaminerProgress)
def get_my_progress(
    id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("examiner")),
):
    """AL4: Examiner's own workload"""
    return analytics_service.get_my_progress(db, id, user.id)
