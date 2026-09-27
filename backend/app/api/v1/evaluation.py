"""
AI Evaluation API router (V1, V3).
Contract: api-spec.md §10.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user, require_role
from app.models.user import User
from app.schemas.evaluation import (
    AIEvaluationListResponse,
    AIEvaluationResponse,
    RunAIEvaluationRequest,
    BatchRunAIEvaluationRequest,
    BatchRunAIEvaluationResponse,
)
from app.services.evaluator_service import list_ai_evaluations, run_ai_evaluation, batch_run_ai_evaluation

router = APIRouter(tags=["AI Evaluation"])


@router.post(
    "/answers/{id}/ai-evaluation",
    response_model=AIEvaluationResponse,
)
def trigger_ai_evaluation(
    id: int,
    body: RunAIEvaluationRequest = RunAIEvaluationRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    V1: Run AI evaluation for one answer (synchronous). Admin or the assigned examiner.
    Mode comes from the question unless force_standard is set.
    """
    return run_ai_evaluation(
        db=db, answer_id=id, user=current_user, force_standard=body.force_standard
    )


@router.get(
    "/answers/{id}/ai-evaluations",
    response_model=AIEvaluationListResponse,
)
def get_ai_evaluation_history(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "examiner", "moderator")),
):
    """V3: History of AI suggestions for one answer, newest first."""
    items = list_ai_evaluations(db=db, answer_id=id, user=current_user)
    return {"items": items}

@router.post(
    "/exams/{id}/ai-evaluation/run",
    status_code=202,
    response_model=BatchRunAIEvaluationResponse,
)
def trigger_batch_ai_evaluation(
    id: int,
    body: BatchRunAIEvaluationRequest = BatchRunAIEvaluationRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """
    V2: Batch AI on answers with ocr_status=done and no current suggestion.
    """
    queued = batch_run_ai_evaluation(
        db=db, exam_id=id, user=current_user, answer_ids=body.answer_ids, only_pending=body.only_pending
    )
    return {"queued": queued}
