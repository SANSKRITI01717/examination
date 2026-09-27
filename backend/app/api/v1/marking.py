"""
Marking API router (M1, M2).
Contract: api-spec.md §12. Examiner only (E*): the answer must be assigned to the caller.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_role
from app.models.user import User
from app.schemas.marking import AcceptAIRequest, EvaluationResponse, SaveMarksRequest
from app.services import marking_service

router = APIRouter(tags=["Marking"])


@router.post(
    "/answers/{id}/evaluation/accept-ai",
    response_model=EvaluationResponse,
)
def accept_ai_suggestion(
    id: int,
    body: AcceptAIRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("examiner")),
):
    """M1: Accept the AI suggestion as-is (creates a submitted evaluation, source=ai_accepted)."""
    return marking_service.accept_ai(db=db, answer_id=id, user=current_user, body=body)


@router.put(
    "/answers/{id}/evaluation",
    response_model=EvaluationResponse,
)
def save_or_submit_marks(
    id: int,
    body: SaveMarksRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("examiner")),
):
    """M2: Save a draft or submit explicit marks (ai_modified or manual)."""
    return marking_service.save_or_submit(db=db, answer_id=id, user=current_user, body=body)
