from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc, case
from app.models.exam import Exam
from app.models.answer import Answer
from app.models.sheet import AnswerSheet
from app.models.question import Question
from app.models.evaluation import Evaluation
from app.models.anomaly import Anomaly
from app.models.moderation import Moderation
from app.models.user import User
from app.schemas.moderation import ModerationCreate
from app.core.errors import AppError

def get_moderation_queue(
    db: Session,
    exam_id: int,
    anomaly_type: Optional[str] = None,
    examiner_id: Optional[int] = None,
    page: int = 1,
    size: int = 50
):
    # Base query for answers in this exam that are flagged
    # An answer is in the queue if it has open anomalies.
    # The API spec says "Flagged answers with anomaly summaries".
    # Wait, does the queue only show answers with marking_status == 'flagged'?
    # Some anomalies (like UNCHECKED_ANSWER) might trigger before marking is done?
    # Actually, moderation usually happens when exam is in moderation, and answers are either flagged or marked.
    # Let's filter answers by exam_id and having open anomalies.
    
    stmt = (
        select(Answer)
        .join(AnswerSheet)
        .join(Question)
        .outerjoin(Evaluation, (Evaluation.answer_id == Answer.id) & (Evaluation.status == "submitted"))
        .join(Anomaly, Anomaly.answer_id == Answer.id)
        .where(AnswerSheet.exam_id == exam_id)
        .where(Anomaly.status == "open")
    )
    
    if anomaly_type:
        stmt = stmt.where(Anomaly.type == anomaly_type)
    if examiner_id:
        stmt = stmt.where(Anomaly.examiner_id == examiner_id)

    # We need to group by Answer to get the max severity.
    # Severity values: low, medium, high. We can map them to integers.
    severity_map = {"low": 1, "medium": 2, "high": 3}
    severity_case = case(
        (Anomaly.severity == "high", 3),
        (Anomaly.severity == "medium", 2),
        (Anomaly.severity == "low", 1),
        else_=0
    )

    # Subquery or group by? Group by is easier.
    grouped_stmt = (
        select(
            Answer.id.label("answer_id"),
            func.max(severity_case).label("max_severity")
        )
        .select_from(Answer)
        .join(AnswerSheet)
        .join(Anomaly, Anomaly.answer_id == Answer.id)
        .where(AnswerSheet.exam_id == exam_id)
        .where(Anomaly.status == "open")
    )
    
    if anomaly_type:
        grouped_stmt = grouped_stmt.where(Anomaly.type == anomaly_type)
    if examiner_id:
        grouped_stmt = grouped_stmt.where(Anomaly.examiner_id == examiner_id)
        
    grouped_stmt = grouped_stmt.group_by(Answer.id).subquery()
    
    # Now get the actual answer records ordered by max_severity desc
    total = db.scalar(select(func.count()).select_from(grouped_stmt)) or 0
    
    answers = db.scalars(
        select(Answer)
        .join(grouped_stmt, grouped_stmt.c.answer_id == Answer.id)
        .order_by(desc(grouped_stmt.c.max_severity), Answer.id)
        .offset((page - 1) * size)
        .limit(size)
    ).all()
    
    items = []
    for ans in answers:
        # Get open anomalies for this answer
        anomalies = db.scalars(
            select(Anomaly).where(Anomaly.answer_id == ans.id, Anomaly.status == "open")
        ).all()
        
        # evaluation might not exist if it's UNCHECKED_ANSWER
        eval_row = db.scalar(
            select(Evaluation).where(Evaluation.answer_id == ans.id, Evaluation.status == "submitted")
        )
        
        sheet = db.get(AnswerSheet, ans.answer_sheet_id)
        question = db.get(Question, ans.question_id)
        
        examiner = None
        if ans.assigned_examiner_id:
            user = db.get(User, ans.assigned_examiner_id)
            if user:
                examiner = {"id": user.id, "full_name": user.full_name}
        
        # Also need ai_suggested_marks. This is on the AIEvaluation if one exists.
        # But `marks` comes from `ans.final_marks` or `eval_row.marks_awarded`.
        # api-spec: marks, ai_suggested_marks.
        marks = ans.final_marks if ans.final_marks is not None else (eval_row.marks_awarded if eval_row else None)
        
        # Get latest AIEvaluation for ai_suggested_marks
        from app.models.evaluation import AIEvaluation
        ai_eval = db.scalar(
            select(AIEvaluation)
            .where(AIEvaluation.answer_id == ans.id)
            .order_by(desc(AIEvaluation.id))
            .limit(1)
        )
        ai_suggested = float(ai_eval.suggested_marks) if ai_eval and ai_eval.suggested_marks is not None else None
        
        items.append({
            "answer_id": ans.id,
            "anon_code": sheet.anon_code,
            "question_number": question.question_number,
            "examiner": examiner,
            "marks": float(marks) if marks is not None else None,
            "ai_suggested_marks": ai_suggested,
            "anomalies": [{"type": a.type, "severity": a.severity} for a in anomalies]
        })
        
    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size
    }


def moderate_answer(db: Session, answer_id: int, moderator_id: int, data: ModerationCreate):
    ans = db.get(Answer, answer_id)
    if not ans:
        raise AppError(code="NOT_FOUND", status_code=404, message="Answer not found")
        
    sheet = db.get(AnswerSheet, ans.answer_sheet_id)
    exam = db.get(Exam, sheet.exam_id)
    if exam.status != "moderation":
        raise AppError(code="EXAM_NOT_IN_MODERATION", status_code=409, message="Exam must be in moderation state")
        
    # Check if marked
    eval_row = db.scalar(
        select(Evaluation).where(Evaluation.answer_id == ans.id, Evaluation.status == "submitted")
    )
    if not eval_row:
        raise AppError(code="NOT_MARKED", status_code=409, message="Answer has no submitted evaluation")
        
    if data.decision == "overridden" and not data.reason:
        raise AppError(code="REASON_REQUIRED", status_code=422, message="Reason is required when overriding")
        
    if data.decision == "confirmed" and data.moderated_marks != float(eval_row.marks_awarded):
        raise AppError(code="VALIDATION_ERROR", status_code=422, message="Confirmed decision requires moderated_marks to match examiner marks")
        
    # Check marks range
    question = db.get(Question, ans.question_id)
    max_marks = float(question.max_marks)
    if data.moderated_marks < 0 or data.moderated_marks > max_marks:
        raise AppError(code="MARKS_OUT_OF_RANGE", status_code=422, message=f"Marks must be between 0 and {max_marks}")
        
    if data.moderated_marks * 2 % 1 != 0:
        raise AppError(code="MARKS_OUT_OF_RANGE", status_code=422, message="Marks must be in 0.5 steps")
        
    mod = Moderation(
        answer_id=ans.id,
        evaluation_id=eval_row.id,
        moderator_id=moderator_id,
        original_marks=eval_row.marks_awarded,
        moderated_marks=data.moderated_marks,
        decision=data.decision,
        reason=data.reason
    )
    db.add(mod)
    
    ans.final_marks = data.moderated_marks
    ans.final_source = "moderator"
    ans.marking_status = "moderated"
    
    # Resolve all open anomalies for this answer
    anomalies = db.scalars(
        select(Anomaly).where(Anomaly.answer_id == ans.id, Anomaly.status == "open")
    ).all()
    for a in anomalies:
        a.status = "resolved"
        a.note = f"Resolved via moderation ({data.decision})"
        
    db.commit()
    db.refresh(mod)
    return mod
