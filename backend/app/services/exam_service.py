"""
Exam service — business logic for exams and lifecycle transitions.
Enforces rules from api-spec.md §4, architecture.md §5, and database-schema.md §4.
"""
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.errors import AppError
from app.models.anomaly import Anomaly
from app.models.answer import Answer
from app.models.exam import Exam, _DEFAULT_EXAM_SETTINGS
from app.models.question import Question
from app.models.reference import ReferenceDocument
from app.models.sheet import AnswerSheet
from app.models.user import User
from app.schemas.exam import ExamCreate, ExamUpdate


def validate_exam_settings(settings: Dict[str, Any]) -> None:
    """Validate settings ranges and thresholds."""
    ratio_fields = [
        "ocr_low_conf_threshold",
        "ai_low_conf_threshold",
        "ai_disagreement_ratio",
        "retrieval_min_score",
    ]
    for field in ratio_fields:
        if field in settings:
            val = settings[field]
            if not isinstance(val, (int, float)) or not (0.0 <= val <= 1.0):
                raise AppError(
                    code="INVALID_SETTINGS",
                    message=f"Setting '{field}' must be a float between 0.0 and 1.0",
                    status_code=422,
                    details={"field": field, "value": val},
                )

    positive_int_fields = ["too_fast_seconds", "min_sample_size", "retrieval_top_k"]
    for field in positive_int_fields:
        if field in settings:
            val = settings[field]
            if not isinstance(val, int) or val < 1:
                raise AppError(
                    code="INVALID_SETTINGS",
                    message=f"Setting '{field}' must be an integer >= 1",
                    status_code=422,
                    details={"field": field, "value": val},
                )

    if "z_threshold" in settings:
        val = settings["z_threshold"]
        if not isinstance(val, (int, float)) or val <= 0:
            raise AppError(
                code="INVALID_SETTINGS",
                message="Setting 'z_threshold' must be a number > 0",
                status_code=422,
                details={"field": "z_threshold", "value": val},
            )


def create_exam(db: Session, data: ExamCreate, user_id: int) -> Exam:
    merged_settings = {**_DEFAULT_EXAM_SETTINGS, **(data.settings or {})}
    validate_exam_settings(merged_settings)

    exam = Exam(
        title=data.title,
        course_code=data.course_code,
        exam_date=data.exam_date,
        status="draft",
        settings=merged_settings,
        created_by=user_id,
    )
    db.add(exam)
    db.commit()
    db.refresh(exam)
    return exam


def get_exams(db: Session, user: User) -> List[Exam]:
    if user.role in ("admin", "moderator"):
        stmt = select(Exam).order_by(Exam.created_at.desc())
        return list(db.scalars(stmt).all())

    # Examiner sees only exams with answers assigned to them
    stmt = (
        select(Exam)
        .join(Answer, Answer.exam_id == Exam.id)
        .where(Answer.assigned_examiner_id == user.id)
        .distinct()
        .order_by(Exam.created_at.desc())
    )
    return list(db.scalars(stmt).all())


def get_exam_by_id(db: Session, exam_id: int, user: User) -> Exam:
    exam = db.get(Exam, exam_id)
    if not exam:
        raise AppError(
            code="NOT_FOUND",
            message=f"Exam with id {exam_id} not found",
            status_code=404,
        )

    if user.role == "examiner":
        has_assignment = db.scalar(
            select(func.count(Answer.id)).where(
                Answer.exam_id == exam_id,
                Answer.assigned_examiner_id == user.id,
            )
        )
        if not has_assignment:
            raise AppError(
                code="FORBIDDEN",
                message="You do not have access to this exam",
                status_code=403,
            )

    return exam


def get_exam_detail(db: Session, exam_id: int, user: User) -> Tuple[Exam, int, int, int]:
    exam = get_exam_by_id(db, exam_id, user)

    q_count = db.scalar(
        select(func.count(Question.id)).where(Question.exam_id == exam_id)
    ) or 0
    sheet_count = db.scalar(
        select(func.count(AnswerSheet.id)).where(AnswerSheet.exam_id == exam_id)
    ) or 0
    ans_count = db.scalar(
        select(func.count(Answer.id)).where(Answer.exam_id == exam_id)
    ) or 0

    return exam, q_count, sheet_count, ans_count


def update_exam(db: Session, exam_id: int, data: ExamUpdate) -> Exam:
    exam = db.get(Exam, exam_id)
    if not exam:
        raise AppError(
            code="NOT_FOUND",
            message=f"Exam with id {exam_id} not found",
            status_code=404,
        )

    if data.title is not None:
        exam.title = data.title
    if data.course_code is not None:
        exam.course_code = data.course_code
    if data.exam_date is not None:
        exam.exam_date = data.exam_date
    if data.settings is not None:
        merged_settings = {**exam.settings, **data.settings}
        validate_exam_settings(merged_settings)
        exam.settings = merged_settings

    db.commit()
    db.refresh(exam)
    return exam


def transition_exam(db: Session, exam_id: int, to_status: str) -> Exam:
    exam = db.get(Exam, exam_id)
    if not exam:
        raise AppError(
            code="NOT_FOUND",
            message=f"Exam with id {exam_id} not found",
            status_code=404,
        )

    allowed_transitions = {
        "draft": ["evaluation"],
        "evaluation": ["moderation"],
        "moderation": ["completed"],
    }

    if to_status not in allowed_transitions.get(exam.status, []):
        raise AppError(
            code="INVALID_TRANSITION",
            message=f"Cannot transition exam from '{exam.status}' to '{to_status}'",
            status_code=409,
        )

    failures: List[str] = []

    if exam.status == "draft" and to_status == "evaluation":
        # 1. At least one question
        questions = list(
            db.scalars(
                select(Question)
                .where(Question.exam_id == exam_id)
                .options(joinedload(Question.rubric))
            ).all()
        )
        if not questions:
            failures.append("At least one question is required")
        else:
            for q in questions:
                # 2. Every question has a rubric
                if not q.rubric:
                    failures.append(f"Question {q.question_number} is missing a rubric")
                else:
                    # 3. Rubric criteria sum equals max_marks
                    criteria = q.rubric.criteria or []
                    criteria_sum = sum(c.get("max_marks", 0) for c in criteria)
                    if round(float(criteria_sum), 2) != round(float(q.max_marks), 2):
                        failures.append(
                            f"Question {q.question_number} rubric criteria sum ({criteria_sum}) does not match max marks ({q.max_marks})"
                        )

                # 4. Reference grounded questions must have at least 1 indexed reference document
                if q.evaluation_mode == "reference_grounded":
                    indexed_doc_count = db.scalar(
                        select(func.count(ReferenceDocument.id)).where(
                            ReferenceDocument.exam_id == exam_id,
                            ReferenceDocument.status == "indexed",
                        )
                    ) or 0
                    if indexed_doc_count == 0:
                        failures.append(
                            f"Question {q.question_number} is reference-grounded but exam has no indexed reference documents"
                        )

        # 5. At least 1 sheet mapped and answers assigned
        mapped_sheet_count = db.scalar(
            select(func.count(AnswerSheet.id)).where(
                AnswerSheet.exam_id == exam_id,
                AnswerSheet.status == "mapped",
            )
        ) or 0
        assigned_ans_count = db.scalar(
            select(func.count(Answer.id)).where(
                Answer.exam_id == exam_id,
                Answer.assigned_examiner_id.isnot(None),
            )
        ) or 0
        if mapped_sheet_count == 0 or assigned_ans_count == 0:
            failures.append(
                "At least one answer sheet must be mapped and have answers assigned to examiners"
            )

        if failures:
            raise AppError(
                code="PRECONDITION_FAILED",
                message="Exam does not meet preconditions for evaluation",
                status_code=409,
                details={"failures": failures},
            )

    elif exam.status == "evaluation" and to_status == "moderation":
        # Evaluation to moderation: unmarked answers are reported but transition is allowed.
        # Anomaly detection runs automatically when moving to moderation (hooked in Phase 7).
        pass

    elif exam.status == "moderation" and to_status == "completed":
        # 1. No attempted answers with marking_status = pending
        pending_attempted = db.scalar(
            select(func.count(Answer.id)).where(
                Answer.exam_id == exam_id,
                Answer.is_attempted.is_(True),
                Answer.marking_status == "pending",
            )
        ) or 0
        if pending_attempted > 0:
            failures.append(
                f"{pending_attempted} attempted answers still have pending marking status"
            )

        # 2. No open anomalies of severity high
        open_high_anomalies = db.scalar(
            select(func.count(Anomaly.id)).where(
                Anomaly.exam_id == exam_id,
                Anomaly.status == "open",
                Anomaly.severity == "high",
            )
        ) or 0
        if open_high_anomalies > 0:
            failures.append(
                f"{open_high_anomalies} high-severity anomalies remain open"
            )

        if failures:
            raise AppError(
                code="PRECONDITION_FAILED",
                message="Exam does not meet preconditions for completion",
                status_code=409,
                details={"failures": failures},
            )

    exam.status = to_status
    db.commit()
    db.refresh(exam)
    return exam
