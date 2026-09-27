"""
OCR Service — batch processing, verification, text correction and processing status.
Contract: api-spec.md §8 (O1-O4) and architecture.md §8.
"""
from typing import Any, Dict, List, Optional
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.ocr import evaluate_ocr_confidence, get_ocr_provider, preprocess_image
from app.core.db import SessionLocal
from app.core.errors import AppError
from app.core.storage import get_storage
from app.models.answer import Answer
from app.models.exam import Exam
from app.models.question import Question
from app.models.sheet import AnswerSheet, AnswerSheetPage
from app.models.user import User
from app.services.job_runner import submit_batch, submit_job


def process_answer_ocr(answer_id: int) -> None:
    """Background worker task for processing OCR on a single answer."""
    db: Session = SessionLocal()
    try:
        ans = db.get(Answer, answer_id)
        if not ans:
            return

        exam = db.get(Exam, ans.exam_id)
        settings = exam.settings if exam else {}

        # Fetch pages belonging to this answer
        stmt = (
            select(AnswerSheetPage)
            .where(
                AnswerSheetPage.answer_sheet_id == ans.answer_sheet_id,
                AnswerSheetPage.page_number >= (ans.page_start or 1),
                AnswerSheetPage.page_number <= (ans.page_end or 1),
            )
            .order_by(AnswerSheetPage.page_number.asc())
        )
        pages = list(db.scalars(stmt).all())

        if not pages:
            ans.ocr_status = "failed"
            ans.ocr_meta = {"error": "No pages associated with this answer range"}
            db.commit()
            return

        storage = get_storage()
        provider = get_ocr_provider()

        combined_texts = []
        all_word_confidences = []

        for p in pages:
            raw_bytes = storage.get(p.storage_key)
            preprocessed_bytes = preprocess_image(raw_bytes)
            ocr_res = provider.extract_text(preprocessed_bytes)

            if ocr_res.text.strip():
                combined_texts.append(ocr_res.text.strip())

            word_confs = ocr_res.meta.get("word_confidences", [])
            all_word_confidences.extend(word_confs)

        full_text = "\n\n".join(combined_texts)
        mean_conf = (
            sum(all_word_confidences) / len(all_word_confidences)
            if all_word_confidences
            else 0.85
        )

        review_required = evaluate_ocr_confidence(
            text=full_text,
            confidence=mean_conf,
            word_confidences=all_word_confidences,
            settings=settings,
            is_attempted=ans.is_attempted,
        )

        ans.ocr_text = full_text
        ans.ocr_confidence = round(mean_conf, 3)
        ans.ocr_review_required = review_required
        ans.ocr_status = "done"
        ans.ocr_meta = {
            "word_count": len(all_word_confidences),
            "pages_processed": len(pages),
        }
        db.commit()
    except Exception as e:
        try:
            ans = db.get(Answer, answer_id)
            if ans:
                ans.ocr_status = "failed"
                ans.ocr_meta = {"error": str(e)}
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


def run_batch_ocr(
    db: Session, exam_id: int, answer_ids: Optional[List[int]] = None
) -> int:
    exam = db.get(Exam, exam_id)
    if not exam:
        raise AppError(code="NOT_FOUND", message=f"Exam {exam_id} not found", status_code=404)

    mapped_sheets_count = db.scalar(
        select(func.count(AnswerSheet.id)).where(
            AnswerSheet.exam_id == exam_id,
            AnswerSheet.status == "mapped",
        )
    ) or 0
    if mapped_sheets_count == 0:
        raise AppError(
            code="NO_MAPPED_SHEETS",
            message="Cannot run OCR: no mapped answer sheets exist for this exam",
            status_code=409,
        )

    stmt = select(Answer).where(
        Answer.exam_id == exam_id,
        Answer.is_attempted.is_(True),
        Answer.ocr_status.in_(["pending", "failed"]),
    )
    if answer_ids:
        stmt = stmt.where(Answer.id.in_(answer_ids))

    answers_to_process = list(db.scalars(stmt).all())
    if not answers_to_process:
        return 0

    target_ids = [a.id for a in answers_to_process]
    for a in answers_to_process:
        a.ocr_status = "processing"
    db.commit()

    submit_batch(process_answer_ocr, target_ids)
    return len(target_ids)


def rerun_single_ocr(db: Session, answer_id: int, user: User) -> int:
    ans = db.get(Answer, answer_id)
    if not ans:
        raise AppError(code="NOT_FOUND", message=f"Answer {answer_id} not found", status_code=404)

    exam = db.get(Exam, ans.exam_id)
    if not exam or exam.status != "evaluation":
        raise AppError(
            code="ANSWER_LOCKED",
            message="OCR can only be re-run while exam is in evaluation state",
            status_code=409,
        )

    if user.role == "examiner" and ans.assigned_examiner_id != user.id:
        raise AppError(code="FORBIDDEN", message="Answer not assigned to you", status_code=403)

    if user.role != "admin" and ans.marking_status == "moderated":
        raise AppError(code="ANSWER_LOCKED", message="Answer is already moderated", status_code=409)

    ans.ocr_status = "processing"
    db.commit()

    submit_job(process_answer_ocr, answer_id)
    return 1


def update_answer_text(
    db: Session,
    answer_id: int,
    verified_text: Optional[str],
    ocr_verified: bool,
    user: User,
) -> Answer:
    ans = db.get(Answer, answer_id)
    if not ans:
        raise AppError(code="NOT_FOUND", message=f"Answer {answer_id} not found", status_code=404)

    exam = db.get(Exam, ans.exam_id)
    if not exam or exam.status != "evaluation":
        raise AppError(
            code="ANSWER_LOCKED",
            message="OCR text can only be updated while exam is in evaluation state",
            status_code=409,
        )

    if user.role == "examiner" and ans.assigned_examiner_id != user.id:
        raise AppError(code="FORBIDDEN", message="Answer not assigned to you", status_code=403)

    if user.role != "admin" and ans.marking_status == "moderated":
        raise AppError(code="ANSWER_LOCKED", message="Answer is already moderated", status_code=409)

    if verified_text is not None:
        if not verified_text.strip():
            raise AppError(code="EMPTY_TEXT", message="Verified text cannot be empty", status_code=422)
        ans.verified_text = verified_text

    if ocr_verified:
        ans.ocr_verified = True

    db.commit()
    db.refresh(ans)
    return ans


def get_processing_status(db: Session, exam_id: int) -> Dict[str, Any]:
    exam = db.get(Exam, exam_id)
    if not exam:
        raise AppError(code="NOT_FOUND", message=f"Exam {exam_id} not found", status_code=404)

    # 1. OCR counters
    ocr_counts = dict(
        db.execute(
            select(Answer.ocr_status, func.count(Answer.id))
            .where(Answer.exam_id == exam_id)
            .group_by(Answer.ocr_status)
        ).all()
    )

    # 2. AI counters
    ai_counts = dict(
        db.execute(
            select(Answer.ai_status, func.count(Answer.id))
            .where(Answer.exam_id == exam_id)
            .group_by(Answer.ai_status)
        ).all()
    )

    # 3. Marking counters
    marking_counts = dict(
        db.execute(
            select(Answer.marking_status, func.count(Answer.id))
            .where(Answer.exam_id == exam_id)
            .group_by(Answer.marking_status)
        ).all()
    )

    # 4. Review required
    review_required = db.scalar(
        select(func.count(Answer.id)).where(
            Answer.exam_id == exam_id,
            Answer.ocr_review_required.is_(True),
            Answer.ocr_verified.is_(False),
        )
    ) or 0

    return {
        "ocr": {
            "pending": ocr_counts.get("pending", 0),
            "processing": ocr_counts.get("processing", 0),
            "done": ocr_counts.get("done", 0),
            "failed": ocr_counts.get("failed", 0),
        },
        "ai": {
            "not_requested": ai_counts.get("not_requested", 0),
            "pending": ai_counts.get("pending", 0),
            "processing": ai_counts.get("processing", 0),
            "done": ai_counts.get("done", 0),
            "failed": ai_counts.get("failed", 0),
        },
        "review_required": review_required,
        "marking": {
            "pending": marking_counts.get("pending", 0),
            "marked": marking_counts.get("marked", 0),
            "flagged": marking_counts.get("flagged", 0),
            "moderated": marking_counts.get("moderated", 0),
        },
    }
