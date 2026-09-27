"""
API routes for Moderation (MD1, MD2).
Contract: api-spec.md §13.
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_role
from app.models.user import User
from app.schemas.moderation import ModerationCreate, ModerationResponse, ModerationQueueResponse
from app.services import moderation_service

router = APIRouter()

@router.get("/exams/{id}/moderation/queue", response_model=ModerationQueueResponse)
def get_moderation_queue(
    id: int,
    anomaly_type: Optional[str] = Query(None),
    examiner_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "moderator")),
):
    """
    MD1: Flagged answers with anomaly summaries, highest severity first.
    """
    return moderation_service.get_moderation_queue(
        db=db,
        exam_id=id,
        anomaly_type=anomaly_type,
        examiner_id=examiner_id,
        page=page
    )


@router.post("/answers/{id}/moderation", response_model=ModerationResponse)
def create_moderation(
    id: int,
    data: ModerationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("moderator")),
):
    """
    MD2: Confirm or override examiner's marks. Resolves answer's open anomalies.
    """
    return moderation_service.moderate_answer(db=db, answer_id=id, moderator_id=user.id, data=data)
