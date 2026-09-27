"""
AI Evaluation Service — standard and reference-grounded evaluator (V1, V3).
Contract: api-spec.md §10 and ai-pipeline.md §4-§9.

Reference-grounded mode attempts real Pinecone retrieval (Phase 6). If the
embedding/vector-store call fails, or nothing scores above the exam's
retrieval_min_score, evaluation gracefully falls back to standard mode with
a warning (ai-pipeline.md §6 step 4) — it never blocks the exam.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.db import SessionLocal

from app.ai.llm import LLMError, get_llm_client
from app.ai.llm.prompts import PROMPT_VERSION, SYSTEM_PROMPT, build_repair_prompt, build_user_prompt
from app.ai.llm.validator import compute_input_hash, is_stale, validate_llm_output
from app.ai.rag.base import RagError
from app.ai.rag.retriever import retrieve_chunks
from app.core.errors import AppError
from app.models.answer import Answer
from app.models.evaluation import AIEvaluation
from app.models.exam import Exam
from app.models.question import Question
from app.models.user import User


def _get_effective_text(answer: Answer) -> str:
    """Invariant 6: verified_text wins over ocr_text when present."""
    if answer.verified_text is not None and answer.verified_text.strip():
        return answer.verified_text
    return answer.ocr_text or ""


def _assert_can_evaluate(answer: Answer, exam: Exam, user: User) -> None:
    if not exam or exam.status != "evaluation":
        raise AppError(
            code="ANSWER_LOCKED",
            message="AI evaluation can only be run while exam is in evaluation state",
            status_code=409,
        )
    if user.role == "examiner" and answer.assigned_examiner_id != user.id:
        raise AppError(code="FORBIDDEN", message="Answer not assigned to you", status_code=403)
    if user.role != "admin" and answer.marking_status == "moderated":
        raise AppError(code="ANSWER_LOCKED", message="Answer is already moderated", status_code=409)


def _serialize(ai_eval: AIEvaluation, stale: bool) -> Dict[str, Any]:
    return {
        "id": ai_eval.id,
        "answer_id": ai_eval.answer_id,
        "mode_requested": ai_eval.mode_requested,
        "mode_used": ai_eval.mode_used,
        "model_name": ai_eval.model_name,
        "prompt_version": ai_eval.prompt_version,
        "suggested_marks": float(ai_eval.suggested_marks),
        "max_marks": float(ai_eval.max_marks),
        "confidence": float(ai_eval.confidence),
        "llm_confidence": float(ai_eval.llm_confidence) if ai_eval.llm_confidence is not None else None,
        "criteria": ai_eval.criteria or [],
        "overall_reason": ai_eval.overall_reason,
        "retrieval": ai_eval.retrieval,
        "warnings": ai_eval.warnings or [],
        "stale": stale,
        "created_at": ai_eval.created_at.isoformat() if ai_eval.created_at else None,
    }


def run_ai_evaluation(
    db: Session, answer_id: int, user: User, force_standard: bool = False
) -> Dict[str, Any]:
    answer = db.get(Answer, answer_id)
    if not answer:
        raise AppError(code="NOT_FOUND", message=f"Answer {answer_id} not found", status_code=404)

    exam = db.get(Exam, answer.exam_id)
    _assert_can_evaluate(answer, exam, user)

    question = db.get(Question, answer.question_id)
    rubric = question.rubric if question else None
    if not rubric or not rubric.criteria:
        raise AppError(
            code="RUBRIC_MISSING",
            message="This question has no rubric configured",
            status_code=409,
        )

    effective_text = _get_effective_text(answer)
    if not effective_text.strip():
        raise AppError(
            code="NO_TEXT_TO_EVALUATE",
            message="No OCR or verified text is available for this answer",
            status_code=409,
        )

    # Mode selection per ai-pipeline.md §6-7.
    mode_requested = "standard" if force_standard else question.evaluation_mode
    warnings: List[str] = []
    mode_used = "standard"
    reference_chunks_for_prompt: Optional[List[Dict[str, Any]]] = None
    retrieval_for_storage: Optional[List[Dict[str, Any]]] = None

    if mode_requested == "reference_grounded":
        exam_settings = exam.settings or {}
        top_k = int(exam_settings.get("retrieval_top_k", 4))
        min_score = float(exam_settings.get("retrieval_min_score", 0.50))
        try:
            chunks = retrieve_chunks(
                db=db,
                exam_id=exam.id,
                question_id=question.id,
                rubric_criteria=rubric.criteria,
                question_text=question.text,
                top_k=top_k,
                min_score=min_score,
            )
        except RagError:
            # Embedding/vector-store failure — never block the exam (ai-pipeline.md §6 step 4).
            chunks = None

        if chunks is None:
            warnings.append("REFERENCE_UNAVAILABLE")
        elif not chunks:
            warnings.append("NO_REFERENCE_FOUND")
        else:
            mode_used = "reference_grounded"
            reference_chunks_for_prompt = [
                {"title": c.title, "text": c.text} for c in chunks
            ]
            retrieval_for_storage = [
                {
                    "doc_id": c.doc_id,
                    "chunk_index": c.chunk_index,
                    "score": c.score,
                    "snippet": c.text[:280],
                }
                for c in chunks
            ]

    user_prompt = build_user_prompt(
        question_text=question.text,
        max_marks=float(question.max_marks),
        criteria=rubric.criteria,
        guidance=rubric.guidance,
        effective_text=effective_text,
        reference_chunks=reference_chunks_for_prompt,
    )

    answer.ai_status = "processing"
    db.commit()

    llm = get_llm_client()
    try:
        result = llm.generate_json(SYSTEM_PROMPT, user_prompt)
    except LLMError as exc:
        answer.ai_status = "failed"
        answer.ai_error = str(exc)
        db.commit()
        raise AppError(
            code="LLM_UNAVAILABLE", message=f"LLM provider error: {exc}", status_code=502
        )

    validation = validate_llm_output(result.raw_text, rubric.criteria)

    if not validation.ok:
        # One repair retry per ai-pipeline.md §5.
        repair_prompt = build_repair_prompt(user_prompt, validation.errors, result.raw_text)
        try:
            result = llm.generate_json(SYSTEM_PROMPT, repair_prompt)
        except LLMError as exc:
            answer.ai_status = "failed"
            answer.ai_error = str(exc)
            db.commit()
            raise AppError(
                code="LLM_UNAVAILABLE", message=f"LLM provider error on retry: {exc}", status_code=502
            )
        validation = validate_llm_output(result.raw_text, rubric.criteria)

    if not validation.ok:
        answer.ai_status = "failed"
        answer.ai_error = "AI output failed validation after repair retry: " + "; ".join(
            validation.errors
        )
        db.commit()
        raise AppError(
            code="AI_OUTPUT_INVALID",
            message="AI output did not pass validation after one repair attempt",
            status_code=422,
            details={"errors": validation.errors},
        )

    ocr_confidence = float(answer.ocr_confidence) if answer.ocr_confidence is not None else None
    if validation.llm_confidence is not None and ocr_confidence is not None:
        effective_confidence = min(validation.llm_confidence, ocr_confidence)
    elif validation.llm_confidence is not None:
        effective_confidence = validation.llm_confidence
    else:
        effective_confidence = ocr_confidence or 0.0

    low_conf_threshold = float((exam.settings or {}).get("ai_low_conf_threshold", 0.70))
    if effective_confidence < low_conf_threshold:
        warnings.append("LOW_CONFIDENCE")
    if answer.ocr_review_required:
        warnings.append("LOW_OCR_CONFIDENCE")

    input_hash = compute_input_hash(effective_text, rubric.criteria, mode_used, PROMPT_VERSION)

    ai_eval = AIEvaluation(
        answer_id=answer.id,
        mode_requested=mode_requested,
        mode_used=mode_used,
        model_name=result.model_name,
        prompt_version=PROMPT_VERSION,
        input_hash=input_hash,
        suggested_marks=validation.suggested_marks,
        max_marks=float(question.max_marks),
        confidence=round(effective_confidence, 3),
        llm_confidence=validation.llm_confidence,
        criteria=validation.criteria,
        overall_reason=validation.overall_reason,
        retrieval=retrieval_for_storage,
        warnings=warnings,
        latency_ms=result.latency_ms,
        triggered_by=user.id,
    )
    db.add(ai_eval)

    answer.ai_status = "done"
    answer.ai_error = None
    db.commit()
    db.refresh(ai_eval)

    return _serialize(ai_eval, stale=False)


def list_ai_evaluations(db: Session, answer_id: int, user: User) -> List[Dict[str, Any]]:
    answer = db.get(Answer, answer_id)
    if not answer:
        raise AppError(code="NOT_FOUND", message=f"Answer {answer_id} not found", status_code=404)

    if user.role == "examiner" and answer.assigned_examiner_id != user.id:
        raise AppError(code="FORBIDDEN", message="Answer not assigned to you", status_code=403)

    question = db.get(Question, answer.question_id)
    rubric = question.rubric if question else None
    current_criteria = rubric.criteria if rubric else []
    current_effective_text = _get_effective_text(answer)

    rows = list(
        db.scalars(
            select(AIEvaluation)
            .where(AIEvaluation.answer_id == answer_id)
            .order_by(AIEvaluation.created_at.desc())
        ).all()
    )

    results = []
    for row in rows:
        stale = is_stale(
            row.input_hash, current_effective_text, current_criteria, row.mode_used, row.prompt_version
        )
        results.append(_serialize(row, stale=stale))
    return results


def _evaluate_single_answer(answer_id: int, user_id: int) -> None:
    db = SessionLocal()
    try:
        user = db.get(User, user_id)
        if not user:
            return
        run_ai_evaluation(db, answer_id, user, force_standard=False)
    except AppError as exc:
        pass # Expected errors (e.g. LLM failure) are handled in run_ai_evaluation
    except Exception as exc:
        pass # Fallback catch for unexpected errors
    finally:
        db.close()


def batch_run_ai_evaluation(
    db: Session, exam_id: int, user: User, answer_ids: Optional[List[int]] = None, only_pending: bool = True
) -> int:
    """
    Finds answers matching the criteria and submits them to the background job runner.
    """
    from app.services.job_runner import submit_batch

    exam = db.get(Exam, exam_id)
    if not exam:
        raise AppError(code="NOT_FOUND", message="Exam not found", status_code=404)

    query = select(Answer).where(
        Answer.exam_id == exam_id,
        Answer.is_attempted == True,
        Answer.ocr_status == "done"
    )

    if answer_ids:
        query = query.where(Answer.id.in_(answer_ids))
    
    if only_pending:
        query = query.where(Answer.ai_status != "done")
        
    answers = db.scalars(query).all()
    
    if not answers:
        if answer_ids:
            raise AppError(code="NO_OCR_TEXT", message="No eligible answers found in the provided list", status_code=409)
        return 0

    valid_answer_ids = []
    for ans in answers:
        ans.ai_status = "pending"
        valid_answer_ids.append(ans.id)
        
    db.commit()

    return submit_batch(lambda a_id: _evaluate_single_answer(a_id, user.id), valid_answer_ids)
