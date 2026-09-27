"""
Marking Service — examiner decisions (M1, M2).
Contract: api-spec.md §12, database-schema.md §6 invariants 2, 3, 5, 7, 8.

Invariant 5: this service (examiner submit) and ModerationService (Phase 8) are the
ONLY writers of answers.final_marks. Nothing here runs without an explicit examiner
request, and AI output never reaches final_marks except through accept_ai(), which the
examiner triggers explicitly (rule 1 in instruction.md).
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.llm.validator import is_stale
from app.core.errors import AppError
from app.models.anomaly import Anomaly
from app.models.answer import Answer
from app.models.evaluation import AIEvaluation, Evaluation
from app.models.exam import Exam
from app.models.question import Question
from app.models.user import User
from app.schemas.marking import AcceptAIRequest, CriterionMarkInput, SaveMarksRequest
from app.services.evaluator_service import _get_effective_text

_HALF = Decimal("0.5")


# --------------------------------------------------------------------------- guards


def _load_for_marking(db: Session, answer_id: int, user: User) -> Tuple[Answer, Exam]:
    """404 / 403 / 409 ANSWER_LOCKED guards shared by M1 and M2."""
    answer = db.get(Answer, answer_id)
    if not answer:
        raise AppError(code="NOT_FOUND", message=f"Answer {answer_id} not found", status_code=404)

    if user.role != "examiner" or answer.assigned_examiner_id != user.id:
        raise AppError(code="FORBIDDEN", message="Answer not assigned to you", status_code=403)

    exam = db.get(Exam, answer.exam_id)
    if not exam or exam.status != "evaluation":
        raise AppError(
            code="ANSWER_LOCKED",
            message="Marks can only be saved while the exam is in evaluation state",
            status_code=409,
        )
    if answer.marking_status == "moderated":
        raise AppError(
            code="ANSWER_LOCKED", message="Answer is already moderated", status_code=409
        )
    return answer, exam


def _get_ai_eval(db: Session, answer: Answer, ai_evaluation_id: int) -> AIEvaluation:
    ai_eval = db.get(AIEvaluation, ai_evaluation_id)
    if not ai_eval or ai_eval.answer_id != answer.id:
        raise AppError(
            code="NOT_FOUND",
            message=f"AI evaluation {ai_evaluation_id} not found for this answer",
            status_code=404,
        )
    return ai_eval


# ------------------------------------------------------------------- mark validation


def _dec(value: Any) -> Decimal:
    return Decimal(str(value))


def _check_mark(value: Decimal, max_marks: Decimal, label: str) -> None:
    """Invariant 2: finite, 0 <= value <= max, in 0.5 steps."""
    if not value.is_finite() or value < 0 or value > max_marks:
        raise AppError(
            code="MARKS_OUT_OF_RANGE",
            message=f"{label} must be between 0 and {max_marks}",
            status_code=422,
            details={"min": 0, "max": float(max_marks), "received": str(value)},
        )
    if (value / _HALF) != (value / _HALF).to_integral_value():
        raise AppError(
            code="VALIDATION_ERROR",
            message=f"{label} must be in steps of 0.5",
            status_code=422,
            details={"received": str(value)},
        )


def _validate_marks(
    marks_awarded: float,
    criterion_marks: Optional[List[CriterionMarkInput]],
    question: Question,
) -> Tuple[Decimal, Optional[List[Dict[str, Any]]]]:
    """
    Validates the total against question.max_marks (invariant 2) and, when per-criterion
    marks are given, each criterion against the rubric plus their sum (invariant 3).
    Returns (total, normalised criterion_marks or None).
    """
    total = _dec(marks_awarded)
    _check_mark(total, _dec(question.max_marks), "marks_awarded")

    if not criterion_marks:
        return total, None

    rubric = question.rubric
    if not rubric or not rubric.criteria:
        raise AppError(
            code="RUBRIC_MISSING",
            message="This question has no rubric, so criterion_marks cannot be validated",
            status_code=409,
        )
    max_by_id = {c["id"]: _dec(c["max_marks"]) for c in rubric.criteria}

    seen = set()
    normalised: List[Dict[str, Any]] = []
    running = Decimal("0")
    for item in criterion_marks:
        if item.criterion_id not in max_by_id:
            raise AppError(
                code="VALIDATION_ERROR",
                message=f"Unknown criterion_id '{item.criterion_id}'",
                status_code=422,
            )
        if item.criterion_id in seen:
            raise AppError(
                code="VALIDATION_ERROR",
                message=f"Duplicate criterion_id '{item.criterion_id}'",
                status_code=422,
            )
        seen.add(item.criterion_id)
        awarded = _dec(item.awarded_marks)
        _check_mark(awarded, max_by_id[item.criterion_id], f"criterion '{item.criterion_id}' marks")
        running += awarded
        normalised.append({"criterion_id": item.criterion_id, "awarded_marks": float(awarded)})

    if running != total:
        raise AppError(
            code="CRITERIA_SUM_MISMATCH",
            message="criterion_marks must add up to marks_awarded",
            status_code=422,
            details={"criteria_sum": float(running), "marks_awarded": float(total)},
        )
    return total, normalised


# ----------------------------------------------------------------------- persistence


def _get_or_create_evaluation(db: Session, answer: Answer, user: User) -> Evaluation:
    """N2 may already have created a placeholder draft row (opened_at) — reuse it."""
    ev = db.scalar(select(Evaluation).where(Evaluation.answer_id == answer.id))
    if ev is None:
        ev = Evaluation(answer_id=answer.id, examiner_id=user.id, marks_awarded=0, source="manual")
        db.add(ev)
    return ev


def _marking_status_after_submit(db: Session, answer: Answer) -> str:
    """api-spec §12: 'marked', or stays 'flagged' if an open anomaly exists."""
    has_open = db.scalar(
        select(Anomaly.id)
        .where(Anomaly.answer_id == answer.id, Anomaly.status == "open")
        .limit(1)
    )
    return "flagged" if has_open is not None else "marked"


def _apply_submit_to_answer(db: Session, answer: Answer, marks: Decimal) -> None:
    answer.final_marks = marks
    answer.final_source = "examiner"
    answer.marking_status = _marking_status_after_submit(db, answer)


def _serialize(db: Session, ev: Evaluation) -> Dict[str, Any]:
    examiner = db.get(User, ev.examiner_id)
    return {
        "id": ev.id,
        "marks_awarded": float(ev.marks_awarded),
        "criterion_marks": ev.criterion_marks,
        "comment": ev.comment,
        "source": ev.source,
        "status": ev.status,
        "submitted_at": ev.submitted_at.isoformat() if ev.submitted_at else None,
        "examiner": {
            "id": examiner.id if examiner else ev.examiner_id,
            "full_name": examiner.full_name if examiner else "Examiner",
        },
    }


# --------------------------------------------------------------------------- M1 / M2


def accept_ai(db: Session, answer_id: int, user: User, body: AcceptAIRequest) -> Dict[str, Any]:
    """M1: examiner explicitly accepts an AI suggestion as-is (source = ai_accepted)."""
    answer, _exam = _load_for_marking(db, answer_id, user)
    ai_eval = _get_ai_eval(db, answer, body.ai_evaluation_id)

    # Invariant 8: unverified low-confidence OCR blocks accept-ai (manual/modified still OK).
    if answer.ocr_review_required and not answer.ocr_verified:
        raise AppError(
            code="OCR_NOT_VERIFIED",
            message="OCR text must be verified before the AI suggestion can be accepted",
            status_code=409,
        )

    question = db.get(Question, answer.question_id)
    rubric = question.rubric if question else None
    current_criteria = rubric.criteria if rubric else []

    # Invariant 7: a suggestion made for different text/rubric cannot be accepted.
    if is_stale(
        ai_eval.input_hash,
        _get_effective_text(answer),
        current_criteria,
        ai_eval.mode_used,
        ai_eval.prompt_version,
    ):
        raise AppError(
            code="AI_EVAL_STALE",
            message="The answer text or rubric changed since this AI suggestion; re-run AI evaluation",
            status_code=409,
        )

    # Defence in depth: accepted marks obey the same range rules as typed marks.
    marks = _dec(ai_eval.suggested_marks)
    _check_mark(marks, _dec(question.max_marks), "AI suggested marks")

    ev = _get_or_create_evaluation(db, answer, user)
    ev.examiner_id = user.id
    ev.ai_evaluation_id = ai_eval.id
    ev.marks_awarded = marks
    ev.criterion_marks = [
        {"criterion_id": c["criterion_id"], "awarded_marks": c["awarded_marks"]}
        for c in (ai_eval.criteria or [])
    ]
    ev.source = "ai_accepted"
    ev.status = "submitted"
    ev.submitted_at = datetime.now(timezone.utc)
    ev.active_seconds = body.active_seconds

    _apply_submit_to_answer(db, answer, marks)
    db.commit()
    db.refresh(ev)
    return _serialize(db, ev)


def save_or_submit(
    db: Session, answer_id: int, user: User, body: SaveMarksRequest
) -> Dict[str, Any]:
    """M2: save a draft or submit explicit marks (ai_modified or manual)."""
    answer, _exam = _load_for_marking(db, answer_id, user)

    if body.source == "ai_modified" and body.ai_evaluation_id is None:
        raise AppError(
            code="VALIDATION_ERROR",
            message="ai_evaluation_id is required when source is 'ai_modified'",
            status_code=422,
        )
    ai_eval = (
        _get_ai_eval(db, answer, body.ai_evaluation_id)
        if body.ai_evaluation_id is not None
        else None
    )

    question = db.get(Question, answer.question_id)
    total, criterion_marks = _validate_marks(body.marks_awarded, body.criterion_marks, question)

    ev = _get_or_create_evaluation(db, answer, user)
    if ev.status == "submitted" and not body.submit:
        # A draft save would change the evaluation but leave answers.final_marks on the old
        # value. Re-submission (submit=true) is the supported way to change submitted marks.
        raise AppError(
            code="ANSWER_LOCKED",
            message="Marks are already submitted; re-submit with submit=true to change them",
            status_code=409,
            details={"reason": "ALREADY_SUBMITTED"},
        )

    ev.examiner_id = user.id
    ev.ai_evaluation_id = ai_eval.id if ai_eval else None
    ev.marks_awarded = total
    ev.criterion_marks = criterion_marks
    ev.comment = body.comment
    ev.source = body.source
    ev.active_seconds = body.active_seconds

    if body.submit:
        ev.status = "submitted"
        ev.submitted_at = datetime.now(timezone.utc)
        _apply_submit_to_answer(db, answer, total)
    else:
        ev.status = "draft"
        ev.submitted_at = None

    db.commit()
    db.refresh(ev)
    return _serialize(db, ev)
