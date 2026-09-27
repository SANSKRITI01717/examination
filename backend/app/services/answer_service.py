"""
Answer Service — Workspace data retrieval and answer listings.
Contract: api-spec.md §9 (N1, N2) and architecture.md §8.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.ai.llm.validator import is_stale
from app.models.evaluation import AIEvaluation
from app.models.anomaly import Anomaly
from app.models.answer import Answer
from app.models.evaluation import Evaluation
from app.models.exam import Exam
from app.models.moderation import Moderation
from app.models.question import Question, Rubric
from app.models.sheet import AnswerSheet, AnswerSheetPage
from app.models.student import Student
from app.models.user import User


def list_answers(
    db: Session,
    current_user: User,
    exam_id: int,
    sheet_id: Optional[int] = None,
    question_id: Optional[int] = None,
    marking_status: Optional[str] = None,
    assigned_to: Optional[str] = None,
    ocr_review_required: Optional[bool] = None,
    page: int = 1,
    page_size: int = 25,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    List answers matching filters for N1.
    Examiner role strictly restricted to answers assigned to them.
    """
    exam = db.get(Exam, exam_id)
    if not exam:
        raise AppError(code="NOT_FOUND", message=f"Exam {exam_id} not found", status_code=404)

    stmt = (
        select(Answer, AnswerSheet, Question)
        .join(AnswerSheet, Answer.answer_sheet_id == AnswerSheet.id)
        .join(Question, Answer.question_id == Question.id)
        .where(Answer.exam_id == exam_id)
    )

    # Role-based scoping
    if current_user.role == "examiner":
        stmt = stmt.where(Answer.assigned_examiner_id == current_user.id)
    elif assigned_to:
        if assigned_to.lower() == "me":
            stmt = stmt.where(Answer.assigned_examiner_id == current_user.id)
        else:
            try:
                examiner_id_int = int(assigned_to)
                stmt = stmt.where(Answer.assigned_examiner_id == examiner_id_int)
            except ValueError:
                pass

    if sheet_id is not None:
        stmt = stmt.where(Answer.answer_sheet_id == sheet_id)

    if question_id is not None:
        stmt = stmt.where(Answer.question_id == question_id)

    if marking_status is not None:
        stmt = stmt.where(Answer.marking_status == marking_status)

    if ocr_review_required is not None:
        stmt = stmt.where(Answer.ocr_review_required.is_(ocr_review_required))

    # Total count query
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.scalar(count_stmt) or 0

    # Pagination & sorting
    stmt = (
        stmt.order_by(
            AnswerSheet.anon_code.asc(),
            Question.display_order.asc(),
            Answer.id.asc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    rows = db.execute(stmt).all()
    items = []
    for ans, sheet, q in rows:
        items.append(
            {
                "id": ans.id,
                "anon_code": sheet.anon_code,
                "question_number": q.question_number,
                "marking_status": ans.marking_status,
                "ocr_status": ans.ocr_status,
                "ai_status": ans.ai_status,
                "ocr_review_required": ans.ocr_review_required,
                "final_marks": float(ans.final_marks) if ans.final_marks is not None else None,
                "max_marks": float(q.max_marks),
            }
        )

    return items, total


def get_answer_detail(db: Session, answer_id: int, current_user: User) -> Dict[str, Any]:
    """
    Full workspace payload for N2.
    First call by an examiner sets evaluations.opened_at.
    """
    ans = db.get(Answer, answer_id)
    if not ans:
        raise AppError(code="NOT_FOUND", message=f"Answer {answer_id} not found", status_code=404)

    # Blind marking and permission check: examiner only accesses assigned answers
    if current_user.role == "examiner" and ans.assigned_examiner_id != current_user.id:
        raise AppError(code="FORBIDDEN", message="Answer is not assigned to you", status_code=403)

    # Track opened_at for examiners
    evaluation_record = db.scalar(
        select(Evaluation).where(Evaluation.answer_id == ans.id)
    )

    now_utc = datetime.now(timezone.utc)
    if current_user.role == "examiner":
        if evaluation_record:
            if evaluation_record.opened_at is None:
                evaluation_record.opened_at = now_utc
                db.commit()
                db.refresh(evaluation_record)
        else:
            evaluation_record = Evaluation(
                answer_id=ans.id,
                examiner_id=current_user.id,
                marks_awarded=0,
                source="manual",
                status="draft",
                opened_at=now_utc,
            )
            db.add(evaluation_record)
            db.commit()
            db.refresh(evaluation_record)

    # Fetch Question & Rubric
    question = db.get(Question, ans.question_id)
    rubric_dict = None
    if question and question.rubric:
        rubric_dict = {
            "criteria": question.rubric.criteria or [],
            "guidance": question.rubric.guidance,
        }

    # Fetch AnswerSheet & Pages
    sheet = db.get(AnswerSheet, ans.answer_sheet_id)
    page_stmt = (
        select(AnswerSheetPage)
        .where(AnswerSheetPage.answer_sheet_id == ans.answer_sheet_id)
    )
    if ans.page_start is not None and ans.page_end is not None:
        page_stmt = page_stmt.where(
            AnswerSheetPage.page_number >= ans.page_start,
            AnswerSheetPage.page_number <= ans.page_end,
        )
    page_stmt = page_stmt.order_by(AnswerSheetPage.page_number.asc())
    pages = db.scalars(page_stmt).all()

    page_items = [
        {
            "id": p.id,
            "page_number": p.page_number,
            "image_url": f"/api/v1/pages/{p.id}/image",
        }
        for p in pages
    ]

    # OCR block
    ocr_dict = {
        "status": ans.ocr_status,
        "text": ans.ocr_text,
        "verified_text": ans.verified_text,
        "confidence": float(ans.ocr_confidence) if ans.ocr_confidence is not None else None,
        "review_required": ans.ocr_review_required,
        "verified": ans.ocr_verified,
    }

    # Latest AI evaluation block
    latest_ai_eval = db.scalar(
        select(AIEvaluation)
        .where(AIEvaluation.answer_id == ans.id)
        .order_by(AIEvaluation.created_at.desc())
        .limit(1)
    )

    ai_latest = None
    if latest_ai_eval:
        current_effective_text = (
            ans.verified_text if ans.verified_text and ans.verified_text.strip() else (ans.ocr_text or "")
        )
        current_criteria = question.rubric.criteria if question and question.rubric else []
        stale = is_stale(
            latest_ai_eval.input_hash,
            current_effective_text,
            current_criteria,
            latest_ai_eval.mode_used,
            latest_ai_eval.prompt_version,
        )
        ai_latest = {
            "id": latest_ai_eval.id,
            "mode_used": latest_ai_eval.mode_used,
            "suggested_marks": float(latest_ai_eval.suggested_marks),
            "max_marks": float(latest_ai_eval.max_marks),
            "confidence": float(latest_ai_eval.confidence),
            "llm_confidence": (
                float(latest_ai_eval.llm_confidence)
                if latest_ai_eval.llm_confidence is not None
                else None
            ),
            "criteria": latest_ai_eval.criteria or [],
            "overall_reason": latest_ai_eval.overall_reason,
            "warnings": latest_ai_eval.warnings or [],
            "stale": stale,
            "created_at": (
                latest_ai_eval.created_at.isoformat()
                if latest_ai_eval.created_at
                else None
            ),
        }
        if current_user.role in ["admin", "moderator"] and latest_ai_eval.retrieval:
            ai_latest["retrieval"] = latest_ai_eval.retrieval

    ai_dict = {
        "status": ans.ai_status,
        "latest": ai_latest,
    }

    # Human Evaluation block
    eval_dict = None
    if evaluation_record and (
        evaluation_record.status == "submitted"
        or evaluation_record.submitted_at is not None
        or evaluation_record.comment is not None
        or evaluation_record.criterion_marks is not None
        or evaluation_record.active_seconds is not None
    ):
        examiner = db.get(User, evaluation_record.examiner_id)
        eval_dict = {
            "id": evaluation_record.id,
            "marks_awarded": float(evaluation_record.marks_awarded),
            "criterion_marks": evaluation_record.criterion_marks,
            "comment": evaluation_record.comment,
            "source": evaluation_record.source,
            "status": evaluation_record.status,
            "submitted_at": (
                evaluation_record.submitted_at.isoformat()
                if evaluation_record.submitted_at
                else None
            ),
            "examiner": {
                "id": examiner.id if examiner else evaluation_record.examiner_id,
                "full_name": examiner.full_name if examiner else "Examiner",
            },
        }

    # Navigation in caller's scope
    nav_stmt = (
        select(Answer.id)
        .join(AnswerSheet, Answer.answer_sheet_id == AnswerSheet.id)
        .join(Question, Answer.question_id == Question.id)
        .where(Answer.exam_id == ans.exam_id)
    )
    if current_user.role == "examiner":
        nav_stmt = nav_stmt.where(Answer.assigned_examiner_id == current_user.id)
    nav_stmt = nav_stmt.order_by(
        AnswerSheet.anon_code.asc(),
        Question.display_order.asc(),
        Answer.id.asc(),
    )
    all_scoped_ids = list(db.scalars(nav_stmt).all())

    position = 1
    prev_id = None
    next_id = None
    if ans.id in all_scoped_ids:
        idx = all_scoped_ids.index(ans.id)
        position = idx + 1
        if idx > 0:
            prev_id = all_scoped_ids[idx - 1]
        if idx < len(all_scoped_ids) - 1:
            next_id = all_scoped_ids[idx + 1]

    navigation = {
        "position": position,
        "total": len(all_scoped_ids),
        "prev_answer_id": prev_id,
        "next_answer_id": next_id,
    }

    # Role differences: anomalies and moderation returned to M and A only
    anomalies_list = None
    moderation_dict = None
    if current_user.role in ["admin", "moderator"]:
        anomalies = list(
            db.scalars(
                select(Anomaly)
                .where(Anomaly.answer_id == ans.id)
                .order_by(Anomaly.detected_at.desc())
            ).all()
        )
        anomalies_list = [
            {
                "id": a.id,
                "type": a.type,
                "severity": a.severity,
                "score": float(a.score) if a.score is not None else None,
                "details": a.details,
                "status": a.status,
                "note": a.note,
                "detected_at": a.detected_at.isoformat() if a.detected_at else None,
            }
            for a in anomalies
        ]

        latest_mod = db.scalar(
            select(Moderation)
            .where(Moderation.answer_id == ans.id)
            .order_by(Moderation.created_at.desc())
            .limit(1)
        )
        if latest_mod:
            moderator = db.get(User, latest_mod.moderator_id)
            moderation_dict = {
                "id": latest_mod.id,
                "decision": latest_mod.decision,
                "original_marks": float(latest_mod.original_marks),
                "moderated_marks": float(latest_mod.moderated_marks),
                "reason": latest_mod.reason,
                "created_at": latest_mod.created_at.isoformat() if latest_mod.created_at else None,
                "moderator": {
                    "id": moderator.id if moderator else latest_mod.moderator_id,
                    "full_name": moderator.full_name if moderator else "Moderator",
                },
            }

    # Role differences: student info returned to Admin only (strictly hidden from E and M)
    student_dict = None
    if current_user.role == "admin" and sheet:
        student = db.get(Student, sheet.student_id)
        if student:
            student_dict = {
                "id": student.id,
                "roll_number": student.roll_number,
                "full_name": student.full_name,
                "department": student.department,
            }

    return {
        "id": ans.id,
        "exam_id": ans.exam_id,
        "anon_code": sheet.anon_code if sheet else f"ANS-{ans.id}",
        "question": {
            "id": question.id,
            "question_number": question.question_number,
            "text": question.text,
            "max_marks": float(question.max_marks),
            "evaluation_mode": question.evaluation_mode,
        },
        "rubric": rubric_dict,
        "pages": page_items,
        "is_attempted": ans.is_attempted,
        "ocr": ocr_dict,
        "ai": ai_dict,
        "evaluation": eval_dict,
        "marking_status": ans.marking_status,
        "final_marks": float(ans.final_marks) if ans.final_marks is not None else None,
        "final_source": ans.final_source,
        "anomalies": anomalies_list,
        "moderation": moderation_dict,
        "navigation": navigation,
        "student": student_dict,
    }
