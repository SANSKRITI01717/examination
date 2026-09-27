"""
API routes for Anomalies (AN1, AN2, AN3).
Contract: api-spec.md A 14.
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.ai.anomaly.runner import run_detectors_for_exam
from app.core.db import get_db
from app.core.deps import get_current_user, require_role
from app.models.user import User
from app.schemas.anomaly import (
    AnomalyDetectRequest,
    AnomalyDetectResponse,
    AnomalyListResponse,
    AnomalyPatchRequest,
    AnomalyResponse,
)
from app.services.anomaly_service import list_anomalies, update_anomaly

router = APIRouter(tags=["Anomalies"])


@router.post(
    "/exams/{id}/anomalies/detect",
    response_model=AnomalyDetectResponse,
)
def detect_anomalies(
    id: int,
    body: AnomalyDetectRequest = AnomalyDetectRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "moderator")),
):
    """
    AN1: Run anomaly detectors for the given exam.
    Idempotent via dedupe_key.
    """
    # Note: we ignore body.detectors for now and run all MVPs as per runner.
    result = run_detectors_for_exam(id)
    if not result:
        from app.core.errors import AppError
        raise AppError(code="NOT_ENOUGH_DATA", message="No eligible answers found", status_code=409)
        
    return result


@router.get(
    "/exams/{id}/anomalies",
    response_model=AnomalyListResponse,
)
def get_anomalies(
    id: int,
    type: Optional[str] = Query(None, description="Filter by anomaly_type"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    status: Optional[str] = Query(None, description="Filter by status"),
    examiner_id: Optional[int] = Query(None, description="Filter by examiner"),
    question_id: Optional[int] = Query(None, description="Filter by question"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "moderator")),
):
    """
    AN2: List anomalies for an exam.
    """
    items, total = list_anomalies(
        db, id, current_user, type, severity, status, examiner_id, question_id, page, page_size
    )
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.patch(
    "/anomalies/{id}",
    response_model=AnomalyResponse,
)
def patch_anomaly(
    id: int,
    body: AnomalyPatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "moderator")),
):
    """
    AN3: Dismiss or reopen an anomaly with a note.
    """
    return update_anomaly(db, id, current_user, body.status, body.note)
