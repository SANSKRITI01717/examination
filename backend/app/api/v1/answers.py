"""
Answers API router (N1, N2).
Contract: api-spec.md §9.
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.db import get_db
from app.models.user import User
from app.schemas.answer import AnswerDetailResponse, AnswerListResponse
from app.services.answer_service import get_answer_detail, list_answers

router = APIRouter(tags=["Answers"])


@router.get(
    "/answers",
    response_model=AnswerListResponse,
)
def get_answers_list(
    exam_id: int = Query(..., description="Target exam ID"),
    sheet_id: Optional[int] = Query(None, description="Filter by answer sheet ID"),
    question_id: Optional[int] = Query(None, description="Filter by question ID"),
    marking_status: Optional[str] = Query(None, description="Filter by marking status"),
    assigned_to: Optional[str] = Query(None, description="Filter by assigned examiner ('me' or user ID)"),
    ocr_review_required: Optional[bool] = Query(None, description="Filter by OCR review flag"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(25, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    N1: Filterable list of answers.
    Examiners only see answers assigned to them.
    """
    items, total = list_answers(
        db=db,
        current_user=current_user,
        exam_id=exam_id,
        sheet_id=sheet_id,
        question_id=question_id,
        marking_status=marking_status,
        assigned_to=assigned_to,
        ocr_review_required=ocr_review_required,
        page=page,
        page_size=page_size,
    )
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get(
    "/answers/{id}",
    response_model=AnswerDetailResponse,
)
def get_single_answer_workspace(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    N2: Full workspace payload for an answer.
    Examiners only access answers assigned to them. First visit tracks opened_at.
    """
    return get_answer_detail(db=db, answer_id=id, current_user=current_user)
