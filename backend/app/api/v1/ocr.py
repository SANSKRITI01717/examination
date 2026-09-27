"""
OCR API router (O1-O4).
Contract: api-spec.md §8.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_role
from app.core.db import get_db
from app.models.user import User
from app.schemas.ocr import (
    AnswerOCRResponse,
    AnswerTextUpdateRequest,
    BatchOCRRequest,
    BatchOCRResponse,
    ProcessingStatusResponse,
)
from app.services.ocr_service import (
    get_processing_status,
    rerun_single_ocr,
    run_batch_ocr,
    update_answer_text,
)

router = APIRouter(tags=["OCR"])


@router.post(
    "/exams/{id}/ocr/run",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=BatchOCRResponse,
)
def trigger_batch_ocr(
    id: int,
    body: BatchOCRRequest = BatchOCRRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """
    O1: Batch OCR. Default: all pending/failed attempted answers.
    Returns 202 { "queued": count }.
    """
    queued_count = run_batch_ocr(db=db, exam_id=id, answer_ids=body.answer_ids)
    return {"queued": queued_count}


@router.post(
    "/answers/{id}/ocr",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=BatchOCRResponse,
)
def trigger_single_answer_ocr(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    O2: Re-run OCR for one answer.
    Allowed for Admin or the assigned Examiner.
    """
    rerun_single_ocr(db=db, answer_id=id, user=current_user)
    return {"queued": 1}


@router.patch(
    "/answers/{id}/text",
    response_model=AnswerOCRResponse,
)
def patch_answer_ocr_text(
    id: int,
    body: AnswerTextUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    O3: Correct OCR text and/or mark it verified.
    """
    ans = update_answer_text(
        db=db,
        answer_id=id,
        verified_text=body.verified_text,
        ocr_verified=body.ocr_verified,
        user=current_user,
    )
    return {
        "status": ans.ocr_status,
        "text": ans.ocr_text,
        "verified_text": ans.verified_text,
        "confidence": float(ans.ocr_confidence) if ans.ocr_confidence is not None else None,
        "review_required": ans.ocr_review_required,
        "verified": ans.ocr_verified,
    }


@router.get(
    "/exams/{id}/processing-status",
    response_model=ProcessingStatusResponse,
)
def get_exam_processing_status(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "moderator")),
):
    """
    O4: Progress counters for OCR, AI, reviews, and marking.
    """
    return get_processing_status(db=db, exam_id=id)
