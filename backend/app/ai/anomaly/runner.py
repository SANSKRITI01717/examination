"""
Anomaly detection runner (Step 7.1).
"""
import logging
from typing import Optional
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models.anomaly import Anomaly
from app.models.answer import Answer
from app.models.evaluation import AIEvaluation, Evaluation
from app.models.exam import Exam
from app.models.question import Question

from .detectors import (
    detect_ai_disagreement,
    detect_examiner_deviation,
    detect_missing_marks,
    detect_question_outlier,
    detect_too_fast,
    detect_unchecked_answers,
)

logger = logging.getLogger(__name__)


def run_detectors_for_exam(exam_id: int) -> dict:
    """
    Runs all 6 MVP anomaly detectors for the given exam and upserts the results.
    Can be called directly or submitted to the background job runner.
    """
    db = SessionLocal()
    try:
        exam = db.get(Exam, exam_id)
        if not exam:
            return {}

        settings = exam.settings or {}
        too_fast_seconds = int(settings.get("too_fast_seconds", 10))
        z_threshold = float(settings.get("z_threshold", 2.5))
        min_sample_size = int(settings.get("min_sample_size", 10))
        ai_disagreement_ratio = float(settings.get("ai_disagreement_ratio", 0.30))

        # Fetch data
        questions = [
            {"id": q.id, "max_marks": q.max_marks}
            for q in db.scalars(select(Question).where(Question.exam_id == exam_id)).all()
        ]
        
        answers_db = db.scalars(select(Answer).where(Answer.exam_id == exam_id)).all()
        answers = [
            {
                "id": a.id,
                "question_id": a.question_id,
                "assigned_examiner_id": a.assigned_examiner_id,
                "is_attempted": a.is_attempted,
                "marking_status": a.marking_status,
                "final_marks": a.final_marks,
                "ocr_text": a.ocr_text,
                "verified_text": a.verified_text,
            }
            for a in answers_db
        ]

        answer_ids = [a["id"] for a in answers]
        if not answer_ids:
            return {}

        evaluations = [
            {
                "id": e.id,
                "answer_id": e.answer_id,
                "examiner_id": e.examiner_id,
                "status": e.status,
                "active_seconds": e.active_seconds,
            }
            for e in db.scalars(select(Evaluation).where(Evaluation.answer_id.in_(answer_ids))).all()
        ]

        ai_evaluations = [
            {
                "id": ai.id,
                "answer_id": ai.answer_id,
                "suggested_marks": ai.suggested_marks,
                "created_at": ai.created_at.isoformat() if ai.created_at else None,
            }
            for ai in db.scalars(select(AIEvaluation).where(AIEvaluation.answer_id.in_(answer_ids))).all()
        ]

        # Run detectors
        anomalies_data = []
        anomalies_data.extend(detect_unchecked_answers(answers, exam.status))
        anomalies_data.extend(detect_missing_marks(answers, evaluations))
        anomalies_data.extend(detect_too_fast(answers, evaluations, too_fast_seconds))
        anomalies_data.extend(detect_question_outlier(answers, z_threshold, min_sample_size))
        anomalies_data.extend(detect_examiner_deviation(answers, z_threshold, min_sample_size))
        anomalies_data.extend(detect_ai_disagreement(answers, ai_evaluations, questions, ai_disagreement_ratio))

        if not anomalies_data:
            return {"created": 0, "updated": 0, "by_type": {}}

        # Upsert
        created = 0
        updated = 0
        by_type = {}
        
        for item in anomalies_data:
            item["exam_id"] = exam_id
            
            stmt = insert(Anomaly).values(**item)
            stmt = stmt.on_conflict_do_update(
                index_elements=["exam_id", "dedupe_key"],
                set_={
                    "score": stmt.excluded.score,
                    "details": stmt.excluded.details,
                    # We do not override status or note if it was already reviewed.
                }
            )
            
            # Since on_conflict_do_update doesn't easily tell us if it inserted or updated, 
            # we just count total items. For an exact count we could do select first, 
            # but Postgres upsert is cleaner. We'll approximate or just return total.
            db.execute(stmt)
            by_type[item["type"]] = by_type.get(item["type"], 0) + 1
            updated += 1 # Simplified count

        db.commit()
        return {"created": updated, "updated": 0, "by_type": by_type}
        
    except Exception as e:
        logger.exception("Error running anomaly detectors")
        db.rollback()
        raise
    finally:
        db.close()
